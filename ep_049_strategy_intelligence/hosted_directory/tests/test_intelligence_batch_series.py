# VERSION HISTORY
# v2.0.0 (2026-09-04) - EP049 is now a standalone Postgres/memory-only service (see
#   app/main.py's own version history) with no SQL Server fallback path to monkeypatch
#   local_strategies()/local_equity_curves() against. Rewritten against the repository-
#   backed path instead: all_profiles() is TTL-cached (intelligence_profile_cache_seconds),
#   so two searches in a row should return identical, correct results without a second
#   repository round trip - verified here by asserting the cached object identity is
#   reused (app.state.profile_cache["profiles"] unchanged) rather than by call-counting
#   a now-nonexistent local_strategies() call.
# v1.1.0 - Ensures discovery caches one batch curve load.
# v1.0.0 - Ensures discovery builds every profile from one batch curve load.
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from app.config import Settings
from app.contracts import Snapshot, Strategy, snapshot_hash
from app.intelligence.profile import build_profile
from app.main import create_app
from app.repository import MemoryRepository


def _snapshot():
    summary = Strategy(strategy_id="DNA_1", total_trades=2, wins=2, losses=0, breakevens=0, total_net_return=3, win_rate=1.0, profit_factor=None, max_drawdown_money=0, evidence_start="2024-01-01T00:00:00Z", evidence_end="2025-01-02T00:00:00Z", quality_state="COLLECTING")
    series = [{"strategy_id": "DNA_1", "trade_id": "t1", "trade_number": 1, "observed_at": "2024-01-01T00:00:00Z", "net_return": 1, "cumulative_net_return": 1, "drawdown": 0},
              {"strategy_id": "DNA_1", "trade_id": "t2", "trade_number": 2, "observed_at": "2025-01-02T00:00:00Z", "net_return": 2, "cumulative_net_return": 3, "drawdown": 0}]
    curve = [{"trade_number": row["trade_number"], "opened_at": row["observed_at"], "closed_at": row["observed_at"], "net_return": row["net_return"], "equity": row["cumulative_net_return"], "drawdown": row["drawdown"]} for row in series]
    profile = build_profile(summary.model_dump(mode="json"), curve)
    now = datetime.now(timezone.utc)
    digest = snapshot_hash([summary], [profile], series)
    return Snapshot(snapshot_id="dna-batch-series", source_watermark=now, generated_at=now, item_count=1, sha256=digest, items=[summary], intelligence_profiles=[profile], return_series=series)


def test_discovery_reuses_the_cached_profile_pool_across_requests():
    repository = MemoryRepository(); repository.promote(_snapshot())
    app = create_app(repository=repository, settings=Settings(data_backend="memory"))
    client = TestClient(app)
    response = client.post("/api/intelligence/query/search", json={"plan": {"asset_class": "FX"}})
    assert response.status_code == 200 and response.json()["total"] == 1
    cached_after_first = app.state.profile_cache["profiles"]
    second = client.post("/api/intelligence/query/search", json={"plan": {"asset_class": "FX"}})
    assert second.status_code == 200 and second.json()["total"] == 1
    assert app.state.profile_cache["profiles"] is cached_after_first
