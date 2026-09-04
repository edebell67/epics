# Version history:
# 2026-09-04 v1.1.0 - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to
#   epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision.
#   No test-logic changes.
# 2026-09-04 v1.0.0 - Postgres/repository-backed coverage for the four
#   query endpoints (timetravel, timetravel/series, top-performers,
#   time-window) that previously 501'd unconditionally off SQL Server -
#   built for the EP049/EP052 hosted deployment release gate. Uses
#   MemoryRepository as the same repository-interface double the existing
#   hosted-parity tests use (test_intelligence_security_and_hosted_parity.py),
#   since PostgresRepository itself needs a live database.

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.config import Settings
from app.contracts import Snapshot, Strategy, snapshot_hash
from app.intelligence.profile import build_profile
from app.main import create_app
from app.repository import MemoryRepository


def _point(strategy_id, number, opened_at, observed_at, net_return, equity, drawdown, alt_net_return=None):
    return {"strategy_id": strategy_id, "trade_id": f"{strategy_id}-{number}", "trade_number": number,
            "opened_at": opened_at, "observed_at": observed_at, "net_return": net_return,
            "alt_net_return": alt_net_return, "cumulative_net_return": equity, "drawdown": drawdown}


def _build_two_strategy_snapshot():
    # DNA_W: wins every trade, on both the as-of day (08-01) and the
    # forward day (08-02), and again "today" (08-02) inside a tight window.
    # DNA_L: loses every trade on the same days - a losing baseline/other
    # candidate so top-performers/time-window/timetravel all have something
    # to exclude, not just one strategy trivially "winning" by default.
    strategies = []
    profiles = []
    series = []
    for strategy_id, day1_values, day2_values in (
        ("DNA_W", [3.0, 2.0], [5.0, 1.0]),
        ("DNA_L", [-1.0, -2.0], [-3.0, -0.5]),
    ):
        equity = peak = 0.0
        curve = []
        number = 0
        for day, values, hours in (
            ("2026-08-01", day1_values, (8, 9)),
            ("2026-08-02", day2_values, (8, 9)),
        ):
            for value, hour in zip(values, hours):
                number += 1
                opened = f"{day}T{hour-1:02d}:30:00Z"
                observed = f"{day}T{hour:02d}:00:00Z"
                equity += value
                peak = max(peak, equity)
                item = _point(strategy_id, number, opened, observed, value, equity, equity - peak, alt_net_return=-value)
                series.append(item)
                curve.append({"trade_number": number, "opened_at": opened, "closed_at": observed,
                               "net_return": value, "alt_net_return": -value, "equity": equity, "drawdown": equity - peak})
        total = len(curve)
        wins = sum(1 for c in curve if c["net_return"] > 0)
        summary = Strategy(strategy_id=strategy_id, total_trades=total, wins=wins, losses=total - wins, breakevens=0,
                            total_net_return=equity, win_rate=wins / total, profit_factor=None,
                            max_drawdown_money=min(c["drawdown"] for c in curve),
                            evidence_start=curve[0]["opened_at"], evidence_end=curve[-1]["closed_at"],
                            quality_state="COLLECTING")
        strategies.append(summary)
        profiles.append(build_profile(summary.model_dump(mode="json"), curve))
    digest = snapshot_hash(strategies, profiles, series)
    now = datetime.now(timezone.utc)
    return Snapshot(snapshot_id="dna-repo-query-endpoints", source_watermark=now, generated_at=now,
                     item_count=2, sha256=digest, items=strategies, intelligence_profiles=profiles, return_series=series)


def _client():
    repository = MemoryRepository()
    repository.promote(_build_two_strategy_snapshot())
    return TestClient(create_app(repository=repository, settings=Settings(data_backend="memory")))


def test_top_performers_works_on_repository_backend_and_ranks_by_window_return():
    client = _client()
    response = client.post("/api/intelligence/query/top-performers", json={"lookback_hours": 4, "min_trade_count": 1, "top_n": 5})
    assert response.status_code == 200
    body = response.json()
    ids = [row["strategy_id"] for row in body["items"]]
    assert ids[0] == "DNA_W"
    assert "DNA_L" in ids
    assert body["time_basis"] == "UTC, as published in directory_return_series"


def test_top_performers_min_trade_count_gates_on_today_not_the_window():
    client = _client()
    # "Today" on the repository backend is the calendar date of the latest
    # published trade (08-02, 2 trades per strategy) - a min_trade_count
    # above that excludes everyone even with a huge lookback window, and
    # exactly at that count admits both, proving the gate reads the whole
    # day's trades rather than just what falls inside the window.
    excluded = client.post("/api/intelligence/query/top-performers", json={"lookback_hours": 8760, "min_trade_count": 3, "top_n": 5})
    assert excluded.status_code == 200 and excluded.json()["items"] == []
    admitted = client.post("/api/intelligence/query/top-performers", json={"lookback_hours": 8760, "min_trade_count": 2, "top_n": 5})
    assert admitted.status_code == 200
    ids = {row["strategy_id"] for row in admitted.json()["items"]}
    assert ids == {"DNA_W", "DNA_L"}


def test_time_window_filters_by_clock_time_and_win_rate():
    client = _client()
    response = client.post("/api/intelligence/query/time-window", json={"before": "09:30", "min_trade_count": 1, "min_win_rate": 1.0})
    assert response.status_code == 200
    body = response.json()
    ids = [row["strategy_id"] for row in body["items"]]
    assert ids == ["DNA_W"]
    assert body["time_basis"] == "UTC, as published in directory_return_series"


def test_timetravel_query_measures_forward_performance_on_repository_backend():
    client = _client()
    response = client.post("/api/intelligence/query/timetravel", json={
        "plan": {"min_win_rate": 1.0}, "as_of": "2026-08-01", "forward_to": "2026-08-02",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["matched_at_as_of"]["strategy_ids"] == ["DNA_W"]
    assert body["forward_performance"]["matched"]["mean_forward_net_return"] > 0


def test_timetravel_series_runs_day_by_day_on_repository_backend():
    client = _client()
    response = client.post("/api/intelligence/query/timetravel/series", json={
        "plan": {"min_win_rate": 1.0}, "as_of_from": "2026-08-01", "as_of_to": "2026-08-01", "forward_days": 1,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["days_evaluated"] == 1
    assert body["series"][0]["matched_count"] == 1
