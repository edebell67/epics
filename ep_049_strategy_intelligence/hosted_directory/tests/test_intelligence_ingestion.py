# VERSION HISTORY
# v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to
#   epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision.
#   No test-logic changes.
from datetime import datetime,timezone,timedelta
from app.intelligence.ingestion import AllowlistedAdapterRegistry,EvidenceIngestionStore


def evidence(watermark=None,value=1):
    return {"source_type":"backtest","source_key":"DNA_1","source_version":"v1","source_watermark":watermark or datetime.now(timezone.utc),"partition":"backtest","payload":{"return":value}}


def test_replay_is_idempotent_and_lineage_separates_partitions():
    store=EvidenceIngestionStore();first=store.ingest(evidence());second=store.ingest(evidence(store.current("backtest","DNA_1","backtest").source_watermark))
    assert first["state"]=="CURRENT" and second["state"]=="IDEMPOTENT_REPLAY" and len(store.lineage())==1


def test_invalid_or_stale_sources_quarantine_without_changing_current():
    store=EvidenceIngestionStore();now=datetime.now(timezone.utc);store.ingest(evidence(now,2))
    stale=store.ingest(evidence(now-timedelta(days=1),99));invalid=store.ingest({"source_type":"shell","payload":{"x":float("nan")}})
    assert stale["state"]==invalid["state"]=="QUARANTINED"
    assert store.current("backtest","DNA_1","backtest").payload["return"]==2 and len(store.quarantine())==2


def test_only_registered_adapters_can_emit_evidence():
    store=EvidenceIngestionStore();registry=AllowlistedAdapterRegistry(store);registry.register("json",lambda source:source)
    assert registry.ingest("json",[evidence()])[0]["state"]=="CURRENT"
    try:registry.ingest("python",[])
    except ValueError as exc:assert "allowlisted" in str(exc)
    else:raise AssertionError("unregistered adapter executed")
