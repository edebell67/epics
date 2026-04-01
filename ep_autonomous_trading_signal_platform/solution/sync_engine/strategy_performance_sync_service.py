from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Protocol

from .config import SyncTargetConfig, load_sync_config
from .signal_sync_service import (
    DEFAULT_SOURCE_SYSTEM,
    StrategyRecord,
    _build_postgres_dsn,
    _normalize_decimal,
    _normalize_timestamp,
    _normalize_uuid,
    build_strategy_record,
)


@dataclass(frozen=True)
class PublishableStrategyPerformanceRecord:
    strategy_performance_id: uuid.UUID
    strategy: StrategyRecord
    performance_date: date
    asset: str
    timeframe: str
    win_rate: Decimal
    profit_factor: Decimal
    drawdown: Decimal
    trade_count: int
    total_profit_loss: Decimal | None
    avg_profit_loss: Decimal | None
    source_system: str


class StrategyPerformanceSyncRepository(Protocol):
    def ensure_strategy(self, strategy: StrategyRecord) -> uuid.UUID: ...

    def upsert_strategy_performance(
        self,
        strategy_performance: PublishableStrategyPerformanceRecord,
        strategy_id: uuid.UUID,
    ) -> None: ...


def _require_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    joined = ", ".join(keys)
    raise ValueError(f"Missing required source field. Expected one of: {joined}")


def _normalize_count(value: Any, field_name: str) -> int:
    try:
        normalized = int(value)
    except Exception as exc:  # pragma: no cover - defensive conversion branch
        raise ValueError(f"Invalid integer for {field_name}: {value!r}") from exc
    if normalized < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return normalized


def _normalize_performance_date(source_row: dict[str, Any]) -> date:
    raw_value = _require_value(
        source_row,
        "performance_date",
        "report_date",
        "as_of",
        "snapshot_date",
        "date",
        "timestamp",
        "created",
        "last_update",
    )
    if isinstance(raw_value, date) and not hasattr(raw_value, "hour"):
        return raw_value
    return _normalize_timestamp(raw_value).date()


def build_publishable_strategy_performance(
    source_row: dict[str, Any],
    source_system: str = DEFAULT_SOURCE_SYSTEM,
) -> PublishableStrategyPerformanceRecord:
    strategy = build_strategy_record(source_row)

    total_profit_loss = source_row.get("total_profit_loss")
    avg_profit_loss = source_row.get("avg_profit_loss")

    return PublishableStrategyPerformanceRecord(
        strategy_performance_id=_normalize_uuid(
            _require_value(source_row, "strategy_performance_id", "summary_id", "guid", "strategy_id"),
            "strategy_performance_id",
        ),
        strategy=strategy,
        performance_date=_normalize_performance_date(source_row),
        asset=str(_require_value(source_row, "asset", "product", "pair")).strip().upper(),
        timeframe=str(source_row.get("timeframe") or strategy.timeframe).strip(),
        win_rate=_normalize_decimal(_require_value(source_row, "win_rate", "profitable_percent", "wr"), "win_rate"),
        profit_factor=_normalize_decimal(_require_value(source_row, "profit_factor"), "profit_factor"),
        drawdown=_normalize_decimal(_require_value(source_row, "drawdown", "dd"), "drawdown"),
        trade_count=_normalize_count(_require_value(source_row, "trade_count", "total_trade_count"), "trade_count"),
        total_profit_loss=None
        if total_profit_loss in (None, "")
        else _normalize_decimal(total_profit_loss, "total_profit_loss"),
        avg_profit_loss=None
        if avg_profit_loss in (None, "")
        else _normalize_decimal(avg_profit_loss, "avg_profit_loss"),
        source_system=str(source_row.get("source_system") or source_system).strip() or DEFAULT_SOURCE_SYSTEM,
    )


class PostgresStrategyPerformanceSyncRepository:
    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or _build_postgres_dsn()

    def ensure_strategy(self, strategy: StrategyRecord) -> uuid.UUID:
        import psycopg2

        with psycopg2.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO strategies (strategy_name, asset, timeframe, description)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (strategy_name, asset, timeframe)
                    DO UPDATE SET
                        description = COALESCE(EXCLUDED.description, strategies.description),
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING strategy_id
                    """,
                    (strategy.strategy_name, strategy.asset, strategy.timeframe, strategy.description),
                )
                strategy_id = cursor.fetchone()[0]
            connection.commit()
        return _normalize_uuid(strategy_id, "strategy_id")

    def upsert_strategy_performance(
        self,
        strategy_performance: PublishableStrategyPerformanceRecord,
        strategy_id: uuid.UUID,
    ) -> None:
        import psycopg2

        with psycopg2.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO strategy_performance (
                        strategy_performance_id,
                        strategy_id,
                        performance_date,
                        asset,
                        timeframe,
                        win_rate,
                        profit_factor,
                        drawdown,
                        trade_count,
                        total_profit_loss,
                        avg_profit_loss,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (strategy_id, performance_date)
                    DO UPDATE SET
                        asset = EXCLUDED.asset,
                        timeframe = EXCLUDED.timeframe,
                        win_rate = EXCLUDED.win_rate,
                        profit_factor = EXCLUDED.profit_factor,
                        drawdown = EXCLUDED.drawdown,
                        trade_count = EXCLUDED.trade_count,
                        total_profit_loss = COALESCE(EXCLUDED.total_profit_loss, strategy_performance.total_profit_loss),
                        avg_profit_loss = COALESCE(EXCLUDED.avg_profit_loss, strategy_performance.avg_profit_loss),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        str(strategy_performance.strategy_performance_id),
                        str(strategy_id),
                        strategy_performance.performance_date,
                        strategy_performance.asset,
                        strategy_performance.timeframe,
                        strategy_performance.win_rate,
                        strategy_performance.profit_factor,
                        strategy_performance.drawdown,
                        strategy_performance.trade_count,
                        strategy_performance.total_profit_loss,
                        strategy_performance.avg_profit_loss,
                    ),
                )
            connection.commit()


class StrategyPerformanceSyncService:
    def __init__(
        self,
        repository: StrategyPerformanceSyncRepository,
        target_config: SyncTargetConfig | None = None,
        source_system: str = DEFAULT_SOURCE_SYSTEM,
    ) -> None:
        self._repository = repository
        self._target_config = target_config or _load_strategy_performance_target_config()
        self._source_system = source_system

    def sync(self, source_rows: Iterable[dict[str, Any]]) -> int:
        if not self._target_config.enabled:
            return 0

        synced = 0
        for source_row in source_rows:
            strategy_performance = build_publishable_strategy_performance(
                source_row,
                source_system=self._source_system,
            )
            strategy_id = self._repository.ensure_strategy(strategy_performance.strategy)
            self._repository.upsert_strategy_performance(strategy_performance, strategy_id)
            synced += 1
        return synced


def _load_strategy_performance_target_config() -> SyncTargetConfig:
    config = load_sync_config()
    for target in config.targets:
        if target.name == "strategy_performance":
            return target
    raise ValueError("strategy_performance target is missing from sync configuration")
