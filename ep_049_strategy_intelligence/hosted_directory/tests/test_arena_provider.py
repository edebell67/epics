# VERSION HISTORY
# v1.1.0 · 2026-09-04 · Relocated from epics/ep_051_strategy_directory/hosted_directory/ to
#   epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision.
#   Updated test_windowed_query_on_non_sqlserver_backend_reports_503 to
#   test_windowed_query_works_on_repository_backed_non_sqlserver_backend - basis_profiles()
#   gained a repository-backed (Postgres/memory) path earlier this session, so windowed
#   queries on those backends now succeed (200), not 503.
# v1.0.0 · 2026-09-03 · Covers the EP052 Arena intelligence provider contract:
# auth, ranking, exact-retry idempotency, request_id conflict, unknown-kind fallback.
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.contracts import Snapshot, Strategy, snapshot_hash
from app.intelligence.profile import build_profile
from app.main import create_app
from app.repository import MemoryRepository

TOKEN = "test-service-token-at-least-32-characters-long"


def _point(strategy_id, number, value, equity, drawdown):
    return {"strategy_id": strategy_id, "trade_id": f"t{number}", "trade_number": number,
            "opened_at": f"2026-08-{number:02d}T08:00:00Z", "observed_at": f"2026-08-{number:02d}T09:00:00Z",
            "net_return": value, "cumulative_net_return": equity, "drawdown": drawdown}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("EP052_INTELLIGENCE_TOKEN", TOKEN)
    strategies = []
    profiles = []
    series = []
    for strategy_id, values in (("DNA_1", [2, -1, 3]), ("DNA_2", [1, -2, 4])):
        equity = peak = 0
        maximum_drawdown = 0
        for value in values:
            equity += value
            peak = max(peak, equity)
            maximum_drawdown = min(maximum_drawdown, equity - peak)
        summary = Strategy(strategy_id=strategy_id, total_trades=3, wins=2, losses=1, breakevens=0,
                            total_net_return=sum(values), win_rate=2 / 3,
                            profit_factor=sum(v for v in values if v > 0) / abs(sum(v for v in values if v < 0)),
                            max_drawdown_money=maximum_drawdown, evidence_start="2026-08-01T08:00:00Z",
                            evidence_end="2026-08-03T09:00:00Z", quality_state="COLLECTING")
        strategies.append(summary)
        equity = peak = 0
        curve = []
        for number, value in enumerate(values, 1):
            equity += value
            peak = max(peak, equity)
            item = _point(strategy_id, number, value, equity, equity - peak)
            series.append(item)
            curve.append({"trade_number": number, "opened_at": item["opened_at"], "closed_at": item["observed_at"],
                          "net_return": value, "equity": equity, "drawdown": item["drawdown"]})
        profiles.append(build_profile(summary.model_dump(mode="json"), curve))
    digest = snapshot_hash(strategies, profiles, series)
    now = datetime.now(timezone.utc)
    snapshot = Snapshot(snapshot_id="arena-provider-test", source_watermark=now, generated_at=now, item_count=2,
                         sha256=digest, items=strategies, intelligence_profiles=profiles, return_series=series)
    repository = MemoryRepository()
    repository.promote(snapshot)
    app = create_app(repository=repository, settings=Settings(data_backend="memory", ep052_intelligence_token=TOKEN,
                      arena_deliveries_path=str(tmp_path / "arena_intelligence_deliveries.sqlite")))
    return TestClient(app)


def headers(agent_id=None):
    return {"Authorization": f"Bearer {TOKEN}", "X-EP052-Agent-ID": str(agent_id or uuid4())}


def test_missing_credential_is_rejected(client):
    response = client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "quality"})
    assert response.status_code == 401


def test_missing_agent_id_is_rejected(client):
    response = client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "quality"},
                            headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 422


def test_empty_universe_returns_an_empty_result_not_an_error(tmp_path):
    """No promoted snapshot -> all_profiles() legitimately returns [] (a
    valid empty answer), distinct from a misconfigured/unavailable backend
    (basis_profiles() returning None), which is the actual 503 case."""
    app = create_app(repository=MemoryRepository(), settings=Settings(data_backend="memory", ep052_intelligence_token=TOKEN,
                      arena_deliveries_path=str(tmp_path / "d.sqlite")))
    response = TestClient(app).post("/v1/queries", json={"request_id": str(uuid4()), "kind": "quality"}, headers=headers())
    assert response.status_code == 200
    assert response.json()["strategy_ids"] == []


def test_windowed_query_works_on_repository_backed_non_sqlserver_backend(tmp_path):
    """basis_profiles() (the windowed rebuild) now has a repository-backed
    path for memory/postgres too (see basis_profiles() in app/main.py) -
    a window_start/window_end on a memory/postgres backend should succeed,
    not fail closed with 503, as it did before that path existed."""
    app = create_app(repository=MemoryRepository(), settings=Settings(data_backend="memory", ep052_intelligence_token=TOKEN,
                      arena_deliveries_path=str(tmp_path / "d.sqlite")))
    response = TestClient(app).post("/v1/queries", json={
        "request_id": str(uuid4()), "kind": "quality",
        "window_start": "2026-08-01T00:00:00Z", "window_end": "2026-08-02T00:00:00Z",
    }, headers=headers())
    assert response.status_code == 200
    assert response.json()["strategy_ids"] == []


def test_ranks_by_requested_kind_not_randomly(client):
    """DNA_1 nets +4 across [2,-1,3]; DNA_2 nets +3 across [1,-2,4]. Ranking
    by net_return must put DNA_1 first - proves this is real ranking, not
    secrets.SystemRandom().sample() like the placeholder it replaces."""
    response = client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "top_performers", "limit": 2}, headers=headers())
    assert response.status_code == 200
    assert response.json()["strategy_ids"] == ["DNA_1", "DNA_2"]


def test_result_is_subset_of_requested_strategy_ids(client):
    response = client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "quality",
                                                  "strategy_ids": ["DNA_2"], "limit": 5}, headers=headers())
    assert response.status_code == 200
    assert response.json()["strategy_ids"] == ["DNA_2"]


def test_unrecognized_kind_falls_back_instead_of_erroring(client):
    response = client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "moon_phase_alignment"}, headers=headers())
    assert response.status_code == 200
    assert "not a recognized ranking" in response.json()["notice"]


def test_exact_retry_replays_the_same_delivery(client):
    request_id = str(uuid4())
    agent = headers()
    first = client.post("/v1/queries", json={"request_id": request_id, "kind": "quality"}, headers=agent)
    second = client.post("/v1/queries", json={"request_id": request_id, "kind": "quality"}, headers=agent)
    assert first.status_code == second.status_code
    if first.status_code == 200:
        assert first.json()["delivery_id"] == second.json()["delivery_id"]


def test_changed_content_on_same_request_id_conflicts(client):
    request_id = str(uuid4())
    agent = headers()
    client.post("/v1/queries", json={"request_id": request_id, "kind": "quality"}, headers=agent)
    conflict = client.post("/v1/queries", json={"request_id": request_id, "kind": "top_performers"}, headers=agent)
    assert conflict.status_code == 409


def test_kinds_endpoint_is_public_and_lists_the_vocabulary(client):
    response = client.get("/v1/kinds")
    assert response.status_code == 200
    body = response.json()
    names = {row["kind"] for row in body["kinds"]}
    assert {"top_performers", "high_win_rate", "low_drawdown", "quality"} <= names
    assert body["default_fallback_kind"] == "quality"


def test_kinds_fallback_rate_reflects_actual_queries(client):
    agent = headers()
    client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "quality"}, headers=agent)
    client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "not_a_real_kind"}, headers=agent)
    body = client.get("/v1/kinds").json()
    assert body["total_queries_observed"] >= 2
    assert body["fallback_rate_all_time"] > 0


def test_observability_requires_service_token(client):
    response = client.get("/v1/observability/agents")
    assert response.status_code == 401


def test_observability_reports_per_agent_activity(client):
    agent_id = str(uuid4())
    agent = headers(agent_id)
    client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "quality"}, headers=agent)
    client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "top_performers"}, headers=agent)
    response = client.get("/v1/observability/agents", params={"agent_id": agent_id}, headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    rows = response.json()["agents"]
    assert len(rows) == 1
    assert rows[0]["agent_id"] == agent_id
    assert rows[0]["query_count"] == 2


def test_anomalous_volume_is_logged(client, caplog):
    agent = headers()
    with caplog.at_level("WARNING", logger="arena_provider"):
        for _ in range(35):
            client.post("/v1/queries", json={"request_id": str(uuid4()), "kind": "quality"}, headers=agent)
    assert any("intelligence queries in the last" in message for message in caplog.messages)
