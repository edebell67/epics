"""Allowlisted, replay-safe intelligence evidence ingestion with lineage and quarantine.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to
epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
import json,math
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator

SourceType=Literal["strategy_definition","backtest","live_result","market_series","closed_trade"]


class SourceEvidence(BaseModel):
    model_config=ConfigDict(extra="forbid")
    source_type:SourceType
    source_key:str=Field(min_length=1,max_length=200)
    source_version:str=Field(min_length=1,max_length=80)
    source_watermark:datetime
    partition:Literal["definition","backtest","live","market","trade"]
    payload:dict[str,Any]

    @field_validator("source_watermark")
    @classmethod
    def aware(cls,value):
        if value.tzinfo is None or value.utcoffset() is None:raise ValueError("source watermark must include a timezone")
        return value.astimezone(timezone.utc)
    @field_validator("payload")
    @classmethod
    def finite_payload(cls,value):
        def check(item):
            if isinstance(item,float) and not math.isfinite(item):raise ValueError("payload numbers must be finite")
            if isinstance(item,dict):
                for nested in item.values():check(nested)
            elif isinstance(item,list):
                for nested in item:check(nested)
        check(value);return value

    @property
    def digest(self):
        body=json.dumps(self.model_dump(mode="json"),sort_keys=True,separators=(",",":"));return sha256(body.encode()).hexdigest()


class EvidenceIngestionStore:
    """Reference adapter target; production rows map one-for-one to intelligence_source_evidence."""
    def __init__(self):self._current={};self._seen={};self._quarantine=[];self._lineage=[]
    def ingest(self,record):
        try:evidence=SourceEvidence.model_validate(record)
        except Exception as exc:
            self._quarantine.append({"record":deepcopy(record),"reason":str(exc),"received_at":datetime.now(timezone.utc).isoformat()});return {"state":"QUARANTINED","reason":str(exc)}
        key=(evidence.source_type,evidence.source_key,evidence.source_version,evidence.digest)
        if key in self._seen:return {"state":"IDEMPOTENT_REPLAY","evidence_id":self._seen[key]}
        current_key=(evidence.source_type,evidence.source_key,evidence.partition);current=self._current.get(current_key)
        if current and current.source_watermark>evidence.source_watermark:
            reason="stale source watermark";self._quarantine.append({"record":evidence.model_dump(mode="json"),"reason":reason,"received_at":datetime.now(timezone.utc).isoformat()});return {"state":"QUARANTINED","reason":reason}
        evidence_id=sha256(("|".join(map(str,key))).encode()).hexdigest()[:32];self._seen[key]=evidence_id;self._current[current_key]=evidence
        self._lineage.append({"evidence_id":evidence_id,"source_type":evidence.source_type,"source_key":evidence.source_key,"source_version":evidence.source_version,"partition":evidence.partition,"watermark":evidence.source_watermark.isoformat(),"sha256":evidence.digest})
        return {"state":"CURRENT","evidence_id":evidence_id,"sha256":evidence.digest}
    def current(self,source_type,source_key,partition):return deepcopy(self._current.get((source_type,source_key,partition)))
    def lineage(self):return deepcopy(self._lineage)
    def quarantine(self):return deepcopy(self._quarantine)


class AllowlistedAdapterRegistry:
    def __init__(self,store):self.store=store;self._adapters={}
    def register(self,name,adapter):
        if not name or name in self._adapters:raise ValueError("adapter name must be unique")
        self._adapters[name]=adapter
    def ingest(self,name,source):
        if name not in self._adapters:raise ValueError("adapter is not allowlisted")
        return [self.store.ingest(record) for record in self._adapters[name](source)]


class SourceEnvelope(BaseModel):
    """Batch adapter envelope retained as the stable ingestion boundary."""
    model_config=ConfigDict(extra="forbid")
    source_id:str=Field(min_length=1,max_length=200)
    source_type:Literal["strategy_definitions","backtests","live_results","market_series","closed_trades"]
    schema_version:str=Field(min_length=1,max_length=40)
    watermark:str=Field(min_length=1,max_length=200)
    generated_at:datetime
    records:list[dict[str,Any]]=Field(max_length=250_000)
    sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    def calculated_hash(self):return sha256(json.dumps(self.records,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


class IngestionLedger:
    """Replay-safe batch ledger whose quarantine never mutates accepted current state."""
    def __init__(self):self.accepted={};self.quarantined=[]
    def ingest(self,envelope):
        item=SourceEnvelope.model_validate(envelope);key=(item.source_id,item.source_type,item.schema_version,item.watermark)
        if item.sha256!=item.calculated_hash():self.quarantined.append({"key":key,"reason":"sha256 mismatch"});return {"status":"quarantined","reason":"sha256 mismatch"}
        if key in self.accepted:return {"status":"idempotent","sha256":item.sha256}
        self.accepted[key]=item;return {"status":"accepted","sha256":item.sha256,"records":len(item.records)}
