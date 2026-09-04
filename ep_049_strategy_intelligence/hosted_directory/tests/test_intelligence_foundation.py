# VERSION HISTORY
# v1.1.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to
#   epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision.
#   No test-logic changes.
# v1.1.0 · 2026-08-24 · Adds capital-aware and expanded metric registry coverage.
# v1.0.0 · 2026-08-24 · Golden foundation metrics, ingestion and profile contract tests.
from datetime import datetime, timezone
import hashlib, json
from fastapi.testclient import TestClient
from app.config import Settings
from app.contracts import Snapshot, Strategy, snapshot_hash
from app.intelligence.ingestion import IngestionLedger, SourceEnvelope
from app.intelligence.metrics import calculate, evidence_confidence
from app.intelligence.profile import build_profile
from app.main import create_app
from app.repository import MemoryRepository


def test_metric_engine_golden_values_and_drawdown():
    times=[datetime(2024,1,1,tzinfo=timezone.utc),datetime(2024,7,1,tzinfo=timezone.utc),datetime(2025,1,1,tzinfo=timezone.utc)]
    result=calculate([100,-40,60],times)
    assert result["total_return"]==120
    assert result["max_drawdown"]==-40
    assert result["win_rate"]==2/3
    assert result["profit_factor"]==4
    assert round(result["expectancy"],6)==40
    assert result["trades_per_year"] is not None
    capitalized=calculate([100,-40,60],times,starting_capital=1000)
    assert capitalized["cagr"] is not None and capitalized["value_at_risk_95"]==-40


def test_evidence_confidence_is_bounded_and_monotonic():
    assert 0 <= evidence_confidence(0,0) < evidence_confidence(50,1) < evidence_confidence(200,3) == 1


def test_ingestion_is_verified_idempotent_and_quarantines_tampering():
    records=[{"strategy_id":"DNA_1","return":2.5}]
    digest=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    envelope=SourceEnvelope(source_id="fixture.closed",source_type="closed_trades",schema_version="1",watermark="1",
      generated_at=datetime.now(timezone.utc),records=records,sha256=digest)
    ledger=IngestionLedger(); assert ledger.ingest(envelope)["status"]=="accepted"; assert ledger.ingest(envelope)["status"]=="idempotent"
    bad=envelope.model_copy(update={"watermark":"2","sha256":"0"*64}); assert ledger.ingest(bad)["status"]=="quarantined"


def test_profile_contains_classification_metrics_evidence_and_provenance():
    summary={"strategy_id":"DNA_102001","descriptive_name":"Test","product_name":"EURUSD, GBPUSD","market":"FX"}
    points=[{"closed_at":"2024-01-01T00:00:00+00:00","net_return":10},{"closed_at":"2025-01-01T00:00:00+00:00","net_return":-2}]
    profile=build_profile(summary,points)
    assert profile.classification.instruments==["EURUSD","GBPUSD"]
    assert profile.metrics.total_return.value==8
    assert profile.methodology["outcome"]=="signed net_return"


def test_intelligence_profile_api_uses_server_computation():
    # v2.0.0 (2026-09-04): EP049 is now Postgres/memory-only (no SQL Server
    # fallback to monkeypatch local_strategies/local_equity_curve against) -
    # exercises the same behavior via a real MemoryRepository instead.
    summary=Strategy(strategy_id="DNA_102001",total_trades=1,wins=1,losses=0,breakevens=0,total_net_return=5,win_rate=1.0,profit_factor=None,max_drawdown_money=0,evidence_start="2024-01-01T00:00:00Z",evidence_end="2024-01-01T00:00:00Z",quality_state="COLLECTING")
    curve=[{"trade_number":1,"opened_at":"2024-01-01T00:00:00+00:00","closed_at":"2024-01-01T00:00:00+00:00","net_return":5,"equity":5,"drawdown":0}]
    profile=build_profile(summary.model_dump(mode="json"),curve)
    series=[{"strategy_id":"DNA_102001","trade_id":"t1","trade_number":1,"observed_at":"2024-01-01T00:00:00Z","net_return":5,"cumulative_net_return":5,"drawdown":0}]
    digest=snapshot_hash([summary],[profile],series);now=datetime.now(timezone.utc)
    snapshot=Snapshot(snapshot_id="dna-profile-api",source_watermark=now,generated_at=now,item_count=1,sha256=digest,items=[summary],intelligence_profiles=[profile],return_series=series)
    repository=MemoryRepository();repository.promote(snapshot)
    settings=Settings(data_backend="memory")
    client=TestClient(create_app(repository=repository,settings=settings)); response=client.get("/api/intelligence/strategies/DNA_102001")
    assert response.status_code==200
    assert response.json()["identity"]["strategy_id"]=="DNA_102001"
    assert response.json()["metrics"]["total_return"]["value"]==5
    registry=client.get("/api/intelligence/metric-registry").json(); assert len(registry["metrics"])==14
    sparse=client.get("/api/intelligence/strategies/DNA_102001",params={"fields":"identity,evidence"})
    assert set(sparse.json())=={"identity","evidence"}
