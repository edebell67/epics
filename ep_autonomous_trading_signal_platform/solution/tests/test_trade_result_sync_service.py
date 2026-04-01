from __future__ import annotations

import uuid
from datetime import timezone
from decimal import Decimal

from sync_engine.trade_result_sync_service import (
    TradeResultSyncService,
    build_publishable_trade_result,
)


class FakeTradeResultSyncRepository:
    def __init__(self) -> None:
        self.trade_results: list[object] = []

    def upsert_trade_result(self, trade_result: object) -> None:
        self.trade_results.append(trade_result)


def test_build_publishable_trade_result_maps_local_fields_to_online_shape() -> None:
    trade_result = build_publishable_trade_result(
        {
            "guid": "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
            "signal_id": "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb",
            "strategy_id": "11111111-1111-1111-1111-111111111111",
            "created": "2026-03-09T16:00:00Z",
            "last_update": "2026-03-09T16:45:00Z",
            "entry_price": "1.2745",
            "latest_price": "1.2795",
            "net_return": "0.0050",
        }
    )

    assert trade_result.trade_result_id == uuid.UUID("2f2c8e36-4de8-4a67-8ce7-1212f54b22f8")
    assert trade_result.signal_id == uuid.UUID("aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb")
    assert trade_result.strategy_id == uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert trade_result.trade_open_time.isoformat() == "2026-03-09T16:00:00+00:00"
    assert trade_result.trade_open_time.tzinfo == timezone.utc
    assert trade_result.trade_close_time.isoformat() == "2026-03-09T16:45:00+00:00"
    assert trade_result.entry_price == Decimal("1.2745")
    assert trade_result.exit_price == Decimal("1.2795")
    assert trade_result.profit_loss == Decimal("0.0050")
    assert trade_result.source_system == "local_trading_system"


def test_build_publishable_trade_result_uses_close_time_fallbacks() -> None:
    trade_result = build_publishable_trade_result(
        {
            "trade_id": "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
            "signal_id": "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb",
            "strategy_id": "11111111-1111-1111-1111-111111111111",
            "open_time": "2026-03-09T16:00:00Z",
            "int_profit_time": "2026-03-09T16:30:00Z",
            "entry_price": "1.2745",
            "exit_price": "1.2710",
            "profit_loss": "-0.0035",
        }
    )

    assert trade_result.trade_close_time.isoformat() == "2026-03-09T16:30:00+00:00"
    assert trade_result.exit_price == Decimal("1.2710")
    assert trade_result.profit_loss == Decimal("-0.0035")


def test_trade_result_sync_service_upserts_each_closed_trade() -> None:
    repository = FakeTradeResultSyncRepository()
    service = TradeResultSyncService(repository=repository)

    synced = service.sync(
        [
            {
                "guid": "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
                "signal_id": "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb",
                "strategy_id": "11111111-1111-1111-1111-111111111111",
                "created": "2026-03-09T16:00:00Z",
                "last_update": "2026-03-09T16:45:00Z",
                "entry_price": "1.2745",
                "latest_price": "1.2795",
                "net_return": "0.0050",
            },
            {
                "trade_id": "7f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
                "signal_id": "cccccccc-1111-2222-3333-dddddddddddd",
                "strategy_id": "22222222-2222-2222-2222-222222222222",
                "open_time": "2026-03-09T17:00:00Z",
                "close_time": "2026-03-09T17:10:00Z",
                "entry_price": "1.2800",
                "exit_price": "1.2780",
                "profit_loss": "-0.0020",
            },
        ]
    )

    assert synced == 2
    assert len(repository.trade_results) == 2
    assert repository.trade_results[0].profit_loss == Decimal("0.0050")
    assert repository.trade_results[1].trade_result_id == uuid.UUID("7f2c8e36-4de8-4a67-8ce7-1212f54b22f8")
