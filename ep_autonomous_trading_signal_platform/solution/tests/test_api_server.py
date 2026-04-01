import json
from pathlib import Path
import shutil
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import api_server
import sync_engine.config as sync_config_module
from api_server import app


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "OK"
    assert payload["service"] == "api_server"
    assert "timestamp" in payload


def test_latest_signals_endpoint_returns_latest_rows_from_repository() -> None:
    class FakeSignalRepository:
        def __init__(self) -> None:
            self.last_limit: int | None = None
            self.history_limit: int | None = None
            self.history_offset: int | None = None

        def fetch_latest_signals(self, limit: int = 20) -> list[dict[str, object]]:
            self.last_limit = limit
            return [
                {
                    "signal_id": "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
                    "timestamp": datetime(2026, 3, 9, 18, 0, tzinfo=timezone.utc),
                    "asset": "GBPUSD",
                    "direction": "buy",
                    "entry": Decimal("1.2745"),
                    "tp": Decimal("1.2795"),
                    "sl": Decimal("1.2710"),
                    "strategy": "breakout_r1",
                    "confidence": Decimal("82.50"),
                }
            ]

        def fetch_signal_history(self, limit: int = 100, offset: int = 0) -> list[dict[str, object]]:
            self.history_limit = limit
            self.history_offset = offset
            return [
                {
                    "signal_id": "history-1",
                    "timestamp": datetime(2026, 3, 9, 17, 0, tzinfo=timezone.utc),
                    "asset": "EURUSD",
                    "direction": "sell",
                    "entry": Decimal("1.0825"),
                    "tp": Decimal("1.0790"),
                    "sl": Decimal("1.0850"),
                    "strategy": "breakout_r2",
                    "confidence": Decimal("67.25"),
                },
                {
                    "signal_id": "history-2",
                    "timestamp": datetime(2026, 3, 9, 16, 30, tzinfo=timezone.utc),
                    "asset": "GBPUSD",
                    "direction": "buy",
                    "entry": Decimal("1.2745"),
                    "tp": Decimal("1.2795"),
                    "sl": Decimal("1.2710"),
                    "strategy": "breakout_r1",
                    "confidence": Decimal("82.50"),
                },
            ]

    repository = FakeSignalRepository()
    app.state.signal_repository = repository

    try:
        response = client.get("/signals/latest", params={"limit": 5})
    finally:
        del app.state.signal_repository

    assert response.status_code == 200
    assert repository.last_limit == 5

    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["signal_id"] == "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8"
    assert payload[0]["asset"] == "GBPUSD"
    assert payload[0]["direction"] == "buy"
    assert payload[0]["strategy"] == "breakout_r1"
    assert payload[0]["confidence"] == 82.5


def test_signal_history_endpoint_returns_history_rows_from_repository() -> None:
    class FakeSignalRepository:
        def __init__(self) -> None:
            self.last_limit: int | None = None
            self.history_limit: int | None = None
            self.history_offset: int | None = None

        def fetch_latest_signals(self, limit: int = 20) -> list[dict[str, object]]:
            self.last_limit = limit
            return []

        def fetch_signal_history(self, limit: int = 100, offset: int = 0) -> list[dict[str, object]]:
            self.history_limit = limit
            self.history_offset = offset
            return [
                {
                    "signal_id": "history-1",
                    "timestamp": datetime(2026, 3, 9, 17, 0, tzinfo=timezone.utc),
                    "asset": "EURUSD",
                    "direction": "sell",
                    "entry": Decimal("1.0825"),
                    "tp": Decimal("1.0790"),
                    "sl": Decimal("1.0850"),
                    "strategy": "breakout_r2",
                    "confidence": Decimal("67.25"),
                },
                {
                    "signal_id": "history-2",
                    "timestamp": datetime(2026, 3, 9, 16, 30, tzinfo=timezone.utc),
                    "asset": "GBPUSD",
                    "direction": "buy",
                    "entry": Decimal("1.2745"),
                    "tp": Decimal("1.2795"),
                    "sl": Decimal("1.2710"),
                    "strategy": "breakout_r1",
                    "confidence": Decimal("82.50"),
                },
            ]

    repository = FakeSignalRepository()
    app.state.signal_repository = repository

    try:
        response = client.get("/signals/history", params={"limit": 2, "offset": 1})
    finally:
        del app.state.signal_repository

    assert response.status_code == 200
    assert repository.history_limit == 2
    assert repository.history_offset == 1

    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["signal_id"] == "history-1"
    assert payload[0]["asset"] == "EURUSD"
    assert payload[0]["direction"] == "sell"
    assert payload[0]["strategy"] == "breakout_r2"
    assert payload[0]["confidence"] == 67.25


def test_strategies_endpoint_returns_latest_strategy_rows_from_repository() -> None:
    class FakeStrategyRepository:
        def __init__(self) -> None:
            self.last_limit: int | None = None

        def fetch_latest_strategies(self, limit: int = 20) -> list[dict[str, object]]:
            self.last_limit = limit
            return [
                {
                    "strategy_id": "11111111-1111-1111-1111-111111111111",
                    "strategy_name": "breakout_r1",
                    "asset": "GBPUSD",
                    "timeframe": "1d",
                    "win_rate": Decimal("63.4"),
                    "profit_factor": Decimal("1.82"),
                    "drawdown": Decimal("0.047"),
                    "trade_count": 142,
                },
                {
                    "strategy_id": "22222222-2222-2222-2222-222222222222",
                    "strategy_name": "breakout_r2",
                    "asset": "EURUSD",
                    "timeframe": "4h",
                    "win_rate": Decimal("55.5"),
                    "profit_factor": Decimal("1.11"),
                    "drawdown": Decimal("0.032"),
                    "trade_count": 12,
                },
            ]

    repository = FakeStrategyRepository()
    app.state.strategy_repository = repository

    try:
        response = client.get("/strategies", params={"limit": 2})
    finally:
        del app.state.strategy_repository

    assert response.status_code == 200
    assert repository.last_limit == 2

    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["strategy_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload[0]["strategy_name"] == "breakout_r1"
    assert payload[0]["asset"] == "GBPUSD"
    assert payload[0]["timeframe"] == "1d"
    assert payload[0]["win_rate"] == 63.4
    assert payload[0]["profit_factor"] == 1.82
    assert payload[0]["drawdown"] == 0.047
    assert payload[0]["trade_count"] == 142


def test_trade_results_endpoint_returns_closed_trade_rows_from_repository() -> None:
    class FakeTradeResultRepository:
        def __init__(self) -> None:
            self.last_limit: int | None = None

        def fetch_trade_results(self, limit: int = 20) -> list[dict[str, object]]:
            self.last_limit = limit
            return [
                {
                    "trade_id": "33333333-3333-3333-3333-333333333333",
                    "signal_id": "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb",
                    "strategy_id": "11111111-1111-1111-1111-111111111111",
                    "open_time": datetime(2026, 3, 9, 16, 0, tzinfo=timezone.utc),
                    "close_time": datetime(2026, 3, 9, 16, 45, tzinfo=timezone.utc),
                    "entry_price": Decimal("1.2745"),
                    "exit_price": Decimal("1.2795"),
                    "profit_loss": Decimal("0.0050"),
                },
                {
                    "trade_id": "44444444-4444-4444-4444-444444444444",
                    "signal_id": "cccccccc-1111-2222-3333-dddddddddddd",
                    "strategy_id": "22222222-2222-2222-2222-222222222222",
                    "open_time": datetime(2026, 3, 9, 17, 0, tzinfo=timezone.utc),
                    "close_time": datetime(2026, 3, 9, 17, 10, tzinfo=timezone.utc),
                    "entry_price": Decimal("1.2800"),
                    "exit_price": Decimal("1.2780"),
                    "profit_loss": Decimal("-0.0020"),
                },
            ]

    repository = FakeTradeResultRepository()
    app.state.trade_result_repository = repository

    try:
        response = client.get("/trade-results", params={"limit": 2})
    finally:
        del app.state.trade_result_repository

    assert response.status_code == 200
    assert repository.last_limit == 2

    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["trade_id"] == "33333333-3333-3333-3333-333333333333"
    assert payload[0]["signal_id"] == "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
    assert payload[0]["strategy_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload[0]["entry_price"] == 1.2745
    assert payload[0]["exit_price"] == 1.2795
    assert payload[0]["profit_loss"] == 0.005


def test_monitoring_summary_returns_expected_cards(monkeypatch) -> None:
    tmp_path = Path("C:/Users/edebe/eds/tests/_tmp_api_server") / uuid4().hex
    tmp_path.mkdir(parents=True, exist_ok=True)

    signals_path = tmp_path / "signals.csv"
    signals_path.write_text(
        "signal_id,timestamp,asset\nsig-1,2026-03-09T18:00:00Z,GBPUSD\nsig-2,2026-03-09T18:05:00Z,EURUSD\n",
        encoding="utf-8",
    )

    queue_path = tmp_path / "content_queue.json"
    queue_path.write_text(
        json.dumps(
            [
                {
                    "queue_id": "one",
                    "platform": "x",
                    "content_type": "signal_alert",
                    "content": "post 1",
                    "status": "dispatched",
                    "created_at": "2026-03-09T18:00:00+00:00",
                    "dispatched_at": "2026-03-09T18:02:00+00:00",
                    "payload": {},
                },
                {
                    "queue_id": "two",
                    "platform": "x",
                    "content_type": "signal_alert",
                    "content": "post 2",
                    "status": "pending",
                    "created_at": "2026-03-09T18:03:00+00:00",
                    "dispatched_at": None,
                    "payload": {},
                },
            ]
        ),
        encoding="utf-8",
    )

    config_path = tmp_path / "sync_config.json"
    schema_path = tmp_path / "signal_schema.json"
    schema_path.write_text(json.dumps({"properties": {"signal_id": {}, "timestamp": {}}}), encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "config_version": 1,
                "default_interval_seconds": 300,
                "targets": {
                        "signals": {
                            "enabled": True,
                            "interval_seconds": 60,
                            "source_schema": str(schema_path),
                            "target_table": "signals",
                            "publishable_fields": ["signal_id", "timestamp"],
                            "excluded_internal_fields": [],
                        }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(api_server, "SIGNALS_FILE_PATH", signals_path)
    monkeypatch.setattr(api_server, "POSTS_QUEUE_PATH", queue_path)
    monkeypatch.setattr(api_server, "DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr(api_server, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sync_config_module, "REPO_ROOT", tmp_path)

    try:
        response = client.get("/monitoring/summary")
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_health"]["status"] == "ok"
    assert len(payload["cards"]) == 4
    assert payload["signals_generated"]["count"] == 2
    assert payload["posts_published"]["published"] == 1
    assert payload["posts_published"]["pending"] == 1
    assert payload["sync_status"]["enabled_targets"] == 1


def test_system_dashboard_page_renders() -> None:
    response = client.get("/dashboard/system")

    assert response.status_code == 200
    assert "System Monitoring Dashboard" in response.text
    assert "/monitoring/summary" in response.text
