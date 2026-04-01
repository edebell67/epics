from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sync_engine.signal_sync_service import DEFAULT_TIMEFRAME, StrategyRecord
from sync_engine.strategy_performance_sync_service import (
    StrategyPerformanceSyncService,
    build_publishable_strategy_performance,
)


class FakeStrategyPerformanceSyncRepository:
    def __init__(self) -> None:
        self.strategies: list[StrategyRecord] = []
        self.strategy_performance_rows: list[tuple[object, uuid.UUID]] = []
        self.strategy_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    def ensure_strategy(self, strategy: StrategyRecord) -> uuid.UUID:
        self.strategies.append(strategy)
        return self.strategy_id

    def upsert_strategy_performance(self, strategy_performance: object, strategy_id: uuid.UUID) -> None:
        self.strategy_performance_rows.append((strategy_performance, strategy_id))


def test_build_publishable_strategy_performance_maps_local_fields_to_online_shape() -> None:
    strategy_performance = build_publishable_strategy_performance(
        {
            "strategy_id": "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
            "strategy_name": "breakout_r1",
            "product": "gbpusd",
            "timeframe": "1d",
            "performance_date": "2026-03-09",
            "win_rate": "63.4",
            "profit_factor": "1.82",
            "drawdown": "0.047",
            "trade_count": 142,
            "total_profit_loss": "0.1540",
            "avg_profit_loss": "0.0011",
        }
    )

    assert strategy_performance.strategy_performance_id == uuid.UUID(
        "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8"
    )
    assert strategy_performance.strategy == StrategyRecord(
        strategy_name="breakout_r1",
        asset="GBPUSD",
        timeframe="1d",
        description=None,
    )
    assert strategy_performance.performance_date == date(2026, 3, 9)
    assert strategy_performance.asset == "GBPUSD"
    assert strategy_performance.win_rate == Decimal("63.4")
    assert strategy_performance.profit_factor == Decimal("1.82")
    assert strategy_performance.drawdown == Decimal("0.047")
    assert strategy_performance.trade_count == 142
    assert strategy_performance.total_profit_loss == Decimal("0.1540")
    assert strategy_performance.avg_profit_loss == Decimal("0.0011")
    assert strategy_performance.source_system == "local_trading_system"


def test_build_publishable_strategy_performance_uses_fallback_fields() -> None:
    strategy_performance = build_publishable_strategy_performance(
        {
            "guid": "7f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
            "model": "breakout_r2",
            "pair": "eurusd",
            "created": "2026-03-09T16:00:00Z",
            "wr": "55.5",
            "profit_factor": "1.11",
            "dd": "0.032",
            "total_trade_count": "12",
        }
    )

    assert strategy_performance.strategy_performance_id == uuid.UUID(
        "7f2c8e36-4de8-4a67-8ce7-1212f54b22f8"
    )
    assert strategy_performance.strategy == StrategyRecord(
        strategy_name="breakout_r2",
        asset="EURUSD",
        timeframe=DEFAULT_TIMEFRAME,
        description=None,
    )
    assert strategy_performance.performance_date == date(2026, 3, 9)
    assert strategy_performance.asset == "EURUSD"
    assert strategy_performance.timeframe == DEFAULT_TIMEFRAME
    assert strategy_performance.trade_count == 12
    assert strategy_performance.total_profit_loss is None
    assert strategy_performance.avg_profit_loss is None


def test_strategy_performance_sync_service_upserts_strategy_then_performance() -> None:
    repository = FakeStrategyPerformanceSyncRepository()
    service = StrategyPerformanceSyncService(repository=repository)

    synced = service.sync(
        [
            {
                "strategy_id": "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
                "strategy_name": "breakout_r1",
                "asset": "gbpusd",
                "timeframe": "1d",
                "report_date": "2026-03-09",
                "profitable_percent": "63.4",
                "profit_factor": "1.82",
                "drawdown": "0.047",
                "trade_count": 142,
            }
        ]
    )

    assert synced == 1
    assert repository.strategies == [
        StrategyRecord(
            strategy_name="breakout_r1",
            asset="GBPUSD",
            timeframe="1d",
            description=None,
        )
    ]
    assert len(repository.strategy_performance_rows) == 1
    strategy_performance, strategy_id = repository.strategy_performance_rows[0]
    assert strategy_performance.performance_date == date(2026, 3, 9)
    assert strategy_performance.win_rate == Decimal("63.4")
    assert strategy_id == repository.strategy_id
