from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Protocol

from .config import SyncTargetConfig, load_sync_config
from .signal_sync_service import (
    DEFAULT_SOURCE_SYSTEM,
    _build_postgres_dsn,
    _normalize_decimal,
    _normalize_timestamp,
    _normalize_uuid,
)


@dataclass(frozen=True)
class PublishableTradeResultRecord:
    trade_result_id: uuid.UUID
    signal_id: uuid.UUID
    strategy_id: uuid.UUID
    trade_open_time: datetime
    trade_close_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    profit_loss: Decimal
    source_system: str


class TradeResultSyncRepository(Protocol):
    def upsert_trade_result(self, trade_result: PublishableTradeResultRecord) -> None: ...


def _require_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    joined = ", ".join(keys)
    raise ValueError(f"Missing required source field. Expected one of: {joined}")


def build_publishable_trade_result(
    source_row: dict[str, Any], source_system: str = DEFAULT_SOURCE_SYSTEM
) -> PublishableTradeResultRecord:
    close_time = _require_value(
        source_row,
        "close_time",
        "last_update",
        "int_profit_time",
        "max_net_return_time",
        "min_net_return_time",
    )

    return PublishableTradeResultRecord(
        trade_result_id=_normalize_uuid(_require_value(source_row, "trade_id", "guid"), "trade_id"),
        signal_id=_normalize_uuid(_require_value(source_row, "signal_id"), "signal_id"),
        strategy_id=_normalize_uuid(_require_value(source_row, "strategy_id"), "strategy_id"),
        trade_open_time=_normalize_timestamp(_require_value(source_row, "open_time", "created")),
        trade_close_time=_normalize_timestamp(close_time),
        entry_price=_normalize_decimal(_require_value(source_row, "entry_price"), "entry_price"),
        exit_price=_normalize_decimal(_require_value(source_row, "exit_price", "latest_price"), "exit_price"),
        profit_loss=_normalize_decimal(_require_value(source_row, "profit_loss", "net_return"), "profit_loss"),
        source_system=str(source_row.get("source_system") or source_system).strip() or DEFAULT_SOURCE_SYSTEM,
    )


class PostgresTradeResultSyncRepository:
    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or _build_postgres_dsn()

    def upsert_trade_result(self, trade_result: PublishableTradeResultRecord) -> None:
        import psycopg2

        with psycopg2.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO trade_results (
                        trade_result_id,
                        signal_id,
                        strategy_id,
                        trade_open_time,
                        trade_close_time,
                        entry_price,
                        exit_price,
                        profit_loss,
                        status,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'closed', CURRENT_TIMESTAMP)
                    ON CONFLICT (trade_result_id)
                    DO UPDATE SET
                        signal_id = EXCLUDED.signal_id,
                        strategy_id = EXCLUDED.strategy_id,
                        trade_open_time = EXCLUDED.trade_open_time,
                        trade_close_time = EXCLUDED.trade_close_time,
                        entry_price = EXCLUDED.entry_price,
                        exit_price = EXCLUDED.exit_price,
                        profit_loss = EXCLUDED.profit_loss,
                        status = 'closed',
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        str(trade_result.trade_result_id),
                        str(trade_result.signal_id),
                        str(trade_result.strategy_id),
                        trade_result.trade_open_time,
                        trade_result.trade_close_time,
                        trade_result.entry_price,
                        trade_result.exit_price,
                        trade_result.profit_loss,
                    ),
                )
            connection.commit()


class TradeResultSyncService:
    def __init__(
        self,
        repository: TradeResultSyncRepository,
        target_config: SyncTargetConfig | None = None,
        source_system: str = DEFAULT_SOURCE_SYSTEM,
    ) -> None:
        self._repository = repository
        self._target_config = target_config or _load_trade_results_target_config()
        self._source_system = source_system

    def sync(self, source_rows: Iterable[dict[str, Any]]) -> int:
        if not self._target_config.enabled:
            return 0

        synced = 0
        for source_row in source_rows:
            trade_result = build_publishable_trade_result(source_row, source_system=self._source_system)
            self._repository.upsert_trade_result(trade_result)
            synced += 1
        return synced


def _load_trade_results_target_config() -> SyncTargetConfig:
    config = load_sync_config()
    for target in config.targets:
        if target.name == "trade_results":
            return target
    raise ValueError("trade_results target is missing from sync configuration")
