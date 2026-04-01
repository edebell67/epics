from __future__ import annotations

import uuid
from datetime import timezone
from decimal import Decimal

from sync_engine.signal_sync_service import (
    DEFAULT_TIMEFRAME,
    SignalSyncService,
    StrategyRecord,
    build_publishable_signal,
    build_strategy_record,
)


class FakeSignalSyncRepository:
    def __init__(self) -> None:
        self.strategies: list[StrategyRecord] = []
        self.signals: list[tuple[object, uuid.UUID]] = []
        self.strategy_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    def ensure_strategy(self, strategy: StrategyRecord) -> uuid.UUID:
        self.strategies.append(strategy)
        return self.strategy_id

    def upsert_signal(self, signal: object, strategy_id: uuid.UUID) -> None:
        self.signals.append((signal, strategy_id))


def test_build_strategy_record_uses_defaults_from_source_shape() -> None:
    strategy = build_strategy_record(
        {
            "strategy_name": "breakout_r1",
            "product": "gbpusd",
        }
    )

    assert strategy == StrategyRecord(
        strategy_name="breakout_r1",
        asset="GBPUSD",
        timeframe=DEFAULT_TIMEFRAME,
        description=None,
    )


def test_build_publishable_signal_maps_local_fields_to_online_shape() -> None:
    signal = build_publishable_signal(
        {
            "guid": "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
            "created": "2026-03-09T16:00:00Z",
            "product": "gbpusd",
            "signal": "BUY",
            "entry_price": "1.2745",
            "target_profit": "1.2795",
            "target_loss": "1.2710",
            "strategy_name": "breakout_r1",
            "confidence": "0.82",
        }
    )

    assert signal.signal_id == uuid.UUID("2f2c8e36-4de8-4a67-8ce7-1212f54b22f8")
    assert signal.signal_timestamp.isoformat() == "2026-03-09T16:00:00+00:00"
    assert signal.signal_timestamp.tzinfo == timezone.utc
    assert signal.asset == "GBPUSD"
    assert signal.direction == "buy"
    assert signal.entry == Decimal("1.2745")
    assert signal.tp == Decimal("1.2795")
    assert signal.sl == Decimal("1.2710")
    assert signal.confidence == Decimal("82.00")
    assert signal.strategy.strategy_name == "breakout_r1"
    assert signal.source_system == "local_trading_system"


def test_signal_sync_service_upserts_strategy_then_signal() -> None:
    repository = FakeSignalSyncRepository()
    service = SignalSyncService(repository=repository)

    synced = service.sync(
        [
            {
                "guid": "2f2c8e36-4de8-4a67-8ce7-1212f54b22f8",
                "created": "2026-03-09T16:00:00Z",
                "product": "gbpusd",
                "signal": "sell",
                "entry_price": "1.2745",
                "target_profit": "1.2695",
                "target_loss": "1.2790",
                "strategy_name": "breakout_r1",
                "confidence": 55,
            }
        ]
    )

    assert synced == 1
    assert repository.strategies == [
        StrategyRecord(
            strategy_name="breakout_r1",
            asset="GBPUSD",
            timeframe=DEFAULT_TIMEFRAME,
            description=None,
        )
    ]
    assert len(repository.signals) == 1
    signal, strategy_id = repository.signals[0]
    assert signal.direction == "sell"
    assert signal.confidence == Decimal("55.00")
    assert strategy_id == repository.strategy_id
