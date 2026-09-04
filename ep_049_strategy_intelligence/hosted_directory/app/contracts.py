"""Public and ingestion contracts.

Version history:
- 1.3.0 (2026-09-04): Vendored into EP049 (copy of EP051's app/contracts.py)
  so EP049 can deploy on its own Render rootDir without depending on EP051's
  filesystem path. Not auto-synced with EP051's copy.
- 1.2.1 (2026-08-31): Reverts an open_trades/open_net_return addition to
  Strategy made and deployed-locally-only within hours of each other on
  2026-08-31. Adding them broke hosted sync for ~4.5 hours: Strategy.model_
  validate() sets undeclared-but-present dict keys to their default (None)
  rather than omitting them, so even though export_snapshot.py stripped
  the raw dict first, the resulting Strategy objects still serialized
  "open_trades": null / "open_net_return": null - changing this snapshot's
  sha256 in a way the currently-deployed (older) hosted server's own
  reconciliation couldn't reproduce, failing every /finalize with 422.
  Local/Arena open-position display never needed this field on Strategy at
  all - it reads app.repository.local_open_trade_summary()'s plain dict
  output directly (see arena/server.py), bypassing this contract entirely.
  If/when hosted has genuinely caught up and this is worth re-adding to
  the shared contract, coordinate the local commit and the hosted deploy
  in the same session, not sequentially.
- 1.2.0 (2026-08-28): Adds SnapshotEnvelope/SnapshotBatch for the staged, batched
  ingestion path (see PUB-04 in the EP051 data-sync workflow doc) - replaces
  a single large POST /internal/snapshots body with begin/batch/finalize
  calls that build one staged snapshot across several small requests. The
  full-snapshot Snapshot contract and its verified() reconciliation are
  unchanged; finalize reassembles one from the staged rows and runs the
  exact same check before promoting.
- 1.1.0 (2026-08-24): Adds the source product name to public strategy evidence.
- 1.0.0 (2026-08-23): Stable strategy and snapshot contracts.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from .intelligence.models import StrategyIntelligenceProfile

MAX_SNAPSHOT_ITEMS = 2000
MAX_RETURN_SERIES_POINTS = 250_000


class Strategy(BaseModel):
    strategy_id: str = Field(pattern=r"^DNA_[A-Za-z0-9]+$")
    descriptive_name: str | None = Field(default=None, max_length=200)
    product_name: str | None = Field(default=None, max_length=500)
    market: str = Field(default="FX", min_length=1, max_length=40)
    status: str = Field(default="active", min_length=1, max_length=40)
    total_trades: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    breakevens: int = Field(ge=0)
    total_net_return: float
    win_rate: float = Field(ge=0, le=1)
    profit_factor: float | None = Field(default=None, ge=0)
    max_drawdown_money: float | None = None
    evidence_start: datetime | None = None
    evidence_end: datetime | None = None
    quality_state: Literal["VALID", "COLLECTING", "STALE"] = "VALID"

    @field_validator("strategy_id")
    @classmethod
    def canonical_id(cls, value: str) -> str:
        if value.endswith(("_B", "_S")):
            raise ValueError("direction suffix is not canonical")
        return value

    @field_validator("total_net_return","win_rate","profit_factor","max_drawdown_money")
    @classmethod
    def finite_numbers(cls,value):
        if value is not None and not math.isfinite(float(value)):raise ValueError("strategy numeric evidence must be finite")
        return value


class IntelligenceReturnPoint(BaseModel):
    strategy_id: str = Field(pattern=r"^DNA_[A-Za-z0-9]+$")
    trade_id: str = Field(min_length=1,max_length=128)
    trade_number: int = Field(ge=1)
    opened_at: datetime|None = None
    observed_at: datetime
    net_return: float
    cumulative_net_return: float
    drawdown: float
    # Optional - absent on snapshots published before this field existed.
    # Lets the hosted trade-ledger view show what the local SQL Server view
    # always could (entry/exit price, product, signal), not just net_return.
    product: str | None = Field(default=None, max_length=500)
    signal: str | None = Field(default=None, max_length=10)
    entry_price: float | None = None
    exit_price: float | None = None
    # Optional - absent on snapshots published before these fields existed.
    # alt_net_return mirrors local's own /trades ledger; rank_position/
    # total_strategies is this trade's rank among every exported strategy's
    # cumulative net_return at this same instant, precomputed once at
    # export time (see sync/export_snapshot.py) - hosted has no live SQL
    # Server access to compute this per-request the way local's
    # /rank-journey endpoint does, so this is necessarily an all-time
    # ranking over the exported population, not local's current-day one.
    alt_net_return: float | None = None
    rank_position: int | None = None
    total_strategies: int | None = None

    @field_validator("net_return","cumulative_net_return","drawdown")
    @classmethod
    def finite_numbers(cls,value):
        if not math.isfinite(float(value)):raise ValueError("return-series evidence must be finite")
        return value


class Snapshot(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    methodology_version: str = Field(default="1.0.0", min_length=1, max_length=80)
    snapshot_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    source_watermark: datetime
    generated_at: datetime
    item_count: int = Field(ge=0, le=MAX_SNAPSHOT_ITEMS)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    items: list[Strategy] = Field(max_length=MAX_SNAPSHOT_ITEMS)
    intelligence_profiles: list[StrategyIntelligenceProfile] = Field(default_factory=list,max_length=MAX_SNAPSHOT_ITEMS)
    return_series: list[IntelligenceReturnPoint] = Field(default_factory=list,max_length=MAX_RETURN_SERIES_POINTS)

    @field_validator("source_watermark", "generated_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        return _aware_timestamp(value)

    @field_validator("items")
    @classmethod
    def unique_ids(cls, items: list[Strategy]) -> list[Strategy]:
        ids = [item.strategy_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("strategy IDs must be unique")
        return items

    def verified(self) -> "Snapshot":
        if self.item_count != len(self.items):
            raise ValueError("item_count does not match items")
        item_ids={item.strategy_id for item in self.items}
        profile_ids=[profile.identity.strategy_id for profile in self.intelligence_profiles]
        if len(profile_ids)!=len(set(profile_ids)):raise ValueError("intelligence profile IDs must be unique")
        if any(strategy_id not in item_ids for strategy_id in profile_ids):raise ValueError("intelligence profile has no directory strategy")
        if any(point.strategy_id not in item_ids for point in self.return_series):raise ValueError("return point has no directory strategy")
        point_keys=[(point.strategy_id,point.observed_at,point.trade_id) for point in self.return_series]
        if len(point_keys)!=len(set(point_keys)):raise ValueError("return-series keys must be unique")
        profiles={profile.identity.strategy_id:profile for profile in self.intelligence_profiles};grouped={}
        for point in self.return_series:
            if point.opened_at and point.opened_at>point.observed_at:raise ValueError("return point opens after it is observed")
            grouped.setdefault(point.strategy_id,[]).append(point)
        for strategy_id,points in grouped.items():
            equity=peak=0.0
            wins=losses=breakevens=0;gross_profit=gross_loss=0.0
            for number,point in enumerate(sorted(points,key=lambda value:(value.observed_at,value.trade_id)),1):
                equity+=point.net_return;peak=max(peak,equity);drawdown=equity-peak
                if point.net_return>0:wins+=1;gross_profit+=point.net_return
                elif point.net_return<0:losses+=1;gross_loss+=abs(point.net_return)
                else:breakevens+=1
                if point.trade_number!=number or not math.isclose(point.cumulative_net_return,equity,abs_tol=1e-6) or not math.isclose(point.drawdown,drawdown,abs_tol=1e-6):raise ValueError("return series does not reconcile")
            profile=profiles.get(strategy_id)
            if profile and (profile.evidence.trade_count!=len(points) or not math.isclose(profile.metrics.total_return.value or 0,equity,abs_tol=1e-6)):raise ValueError("profile does not reconcile to return series")
            strategy=next(item for item in self.items if item.strategy_id==strategy_id);ordered=sorted(points,key=lambda value:(value.observed_at,value.trade_id));maximum_drawdown=min(point.drawdown for point in points);profit_factor=None if gross_loss==0 else gross_profit/gross_loss
            if strategy.total_trades!=len(points) or (strategy.wins,strategy.losses,strategy.breakevens)!=(wins,losses,breakevens):raise ValueError("strategy counts do not reconcile to return series")
            if not math.isclose(strategy.total_net_return,equity,abs_tol=1e-6) or not math.isclose(strategy.win_rate,wins/len(points),abs_tol=1e-6):raise ValueError("strategy performance does not reconcile to return series")
            if strategy.max_drawdown_money is not None and not math.isclose(strategy.max_drawdown_money,maximum_drawdown,abs_tol=1e-6):raise ValueError("strategy drawdown does not reconcile to return series")
            if strategy.profit_factor is not None and (profit_factor is None or not math.isclose(strategy.profit_factor,profit_factor,abs_tol=1e-6)):raise ValueError("strategy profit factor does not reconcile to return series")
            evidence_start=min((point.opened_at or point.observed_at) for point in points)
            if strategy.evidence_start and strategy.evidence_start!=evidence_start:raise ValueError("strategy evidence start does not reconcile to return series")
            if strategy.evidence_end and strategy.evidence_end!=ordered[-1].observed_at:raise ValueError("strategy evidence end does not reconcile to return series")
        if self.sha256 != snapshot_hash(self.items,self.intelligence_profiles,self.return_series):
            raise ValueError("snapshot hash mismatch")
        return self


def _aware_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(timezone.utc)


class SnapshotEnvelope(BaseModel):
    """Declares a snapshot's identity/counts before any rows arrive. Posted
    to POST /internal/snapshots/{snapshot_id}/begin to start a staged
    snapshot that /batch calls then fill in and /finalize reconciles."""
    schema_version: Literal["1.0.0"] = "1.0.0"
    methodology_version: str = Field(default="1.0.0", min_length=1, max_length=80)
    snapshot_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    source_watermark: datetime
    generated_at: datetime
    item_count: int = Field(ge=0, le=MAX_SNAPSHOT_ITEMS)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("source_watermark", "generated_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        return _aware_timestamp(value)


class SnapshotBatch(BaseModel):
    """One chunk of a staged snapshot's rows. batch_index makes each batch
    POST idempotent (Idempotency-Key = '{snapshot_id}:{batch_index}') so a
    retried batch never double-inserts."""
    batch_index: int = Field(ge=0)
    items: list[Strategy] = Field(default_factory=list, max_length=MAX_SNAPSHOT_ITEMS)
    intelligence_profiles: list[StrategyIntelligenceProfile] = Field(default_factory=list, max_length=MAX_SNAPSHOT_ITEMS)
    return_series: list[IntelligenceReturnPoint] = Field(default_factory=list, max_length=MAX_RETURN_SERIES_POINTS)


def _json_default(value):
    if isinstance(value, (datetime,)):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


def snapshot_hash(items: list[Strategy] | list[dict],profiles=None,return_series=None) -> str:
    normalized = [Strategy.model_validate(x).model_dump(mode="json") for x in items]
    normalized.sort(key=lambda x: x["strategy_id"])
    profile_rows=[StrategyIntelligenceProfile.model_validate(x).model_dump(mode="json") for x in (profiles or [])]
    profile_rows.sort(key=lambda x:x["identity"]["strategy_id"])
    series_rows=[IntelligenceReturnPoint.model_validate(x).model_dump(mode="json") for x in (return_series or [])]
    series_rows.sort(key=lambda x:(x["strategy_id"],x["observed_at"],x["trade_id"]))
    body = json.dumps({"items":normalized,"profiles":profile_rows,"return_series":series_rows}, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
