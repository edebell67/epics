from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Protocol

from .config import SyncTargetConfig, load_sync_config


DEFAULT_SOURCE_SYSTEM = "local_trading_system"
DEFAULT_TIMEFRAME = "sync"


@dataclass(frozen=True)
class StrategyRecord:
    strategy_name: str
    asset: str
    timeframe: str
    description: str | None = None


@dataclass(frozen=True)
class PublishableSignalRecord:
    signal_id: uuid.UUID
    signal_timestamp: datetime
    asset: str
    direction: str
    entry: Decimal
    tp: Decimal
    sl: Decimal
    confidence: Decimal | None
    strategy: StrategyRecord
    source_system: str
    published_at: datetime


class SignalSyncRepository(Protocol):
    def ensure_strategy(self, strategy: StrategyRecord) -> uuid.UUID: ...

    def upsert_signal(self, signal: PublishableSignalRecord, strategy_id: uuid.UUID) -> None: ...


def _require_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    joined = ", ".join(keys)
    raise ValueError(f"Missing required source field. Expected one of: {joined}")


def _normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Signal timestamp must be a non-empty datetime string")

    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _normalize_decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive conversion branch
        raise ValueError(f"Invalid decimal for {field_name}: {value!r}") from exc


def _normalize_direction(value: Any) -> str:
    direction = str(value).strip().lower()
    if direction not in {"buy", "sell"}:
        raise ValueError(f"Unsupported direction: {value!r}")
    return direction


def _normalize_confidence(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None

    confidence = Decimal(str(value))
    if confidence < 0:
        raise ValueError("confidence must be non-negative")
    if confidence <= 1:
        confidence *= Decimal("100")
    if confidence > 100:
        raise ValueError("confidence must not exceed 100")
    return confidence.quantize(Decimal("0.01"))


def _normalize_uuid(value: Any, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{field_name} must be a valid UUID string") from exc


def build_strategy_record(source_row: dict[str, Any]) -> StrategyRecord:
    strategy_name = str(_require_value(source_row, "strategy", "strategy_name", "model")).strip()
    asset = str(_require_value(source_row, "asset", "product", "pair")).strip().upper()
    timeframe = str(source_row.get("timeframe") or DEFAULT_TIMEFRAME).strip()

    description = source_row.get("description")
    if description is not None:
        description = str(description).strip() or None

    return StrategyRecord(
        strategy_name=strategy_name,
        asset=asset,
        timeframe=timeframe,
        description=description,
    )


def build_publishable_signal(source_row: dict[str, Any], source_system: str = DEFAULT_SOURCE_SYSTEM) -> PublishableSignalRecord:
    strategy = build_strategy_record(source_row)
    signal_id = _normalize_uuid(_require_value(source_row, "signal_id", "guid"), "signal_id")
    signal_timestamp = _normalize_timestamp(_require_value(source_row, "timestamp", "created", "last_update"))
    published_at = _normalize_timestamp(source_row.get("published_at") or signal_timestamp)

    return PublishableSignalRecord(
        signal_id=signal_id,
        signal_timestamp=signal_timestamp,
        asset=str(_require_value(source_row, "asset", "product", "pair")).strip().upper(),
        direction=_normalize_direction(_require_value(source_row, "direction", "signal")),
        entry=_normalize_decimal(_require_value(source_row, "entry", "entry_price"), "entry"),
        tp=_normalize_decimal(_require_value(source_row, "tp", "target_profit"), "tp"),
        sl=_normalize_decimal(_require_value(source_row, "sl", "target_loss"), "sl"),
        confidence=_normalize_confidence(source_row.get("confidence")),
        strategy=strategy,
        source_system=str(source_row.get("source_system") or source_system).strip() or DEFAULT_SOURCE_SYSTEM,
        published_at=published_at,
    )


class PostgresSignalSyncRepository:
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

    def upsert_signal(self, signal: PublishableSignalRecord, strategy_id: uuid.UUID) -> None:
        import psycopg2

        with psycopg2.connect(self._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO signals (
                        signal_id,
                        strategy_id,
                        signal_timestamp,
                        asset,
                        direction,
                        entry,
                        tp,
                        sl,
                        confidence,
                        source_system,
                        published_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (signal_id)
                    DO UPDATE SET
                        strategy_id = EXCLUDED.strategy_id,
                        signal_timestamp = EXCLUDED.signal_timestamp,
                        asset = EXCLUDED.asset,
                        direction = EXCLUDED.direction,
                        entry = EXCLUDED.entry,
                        tp = EXCLUDED.tp,
                        sl = EXCLUDED.sl,
                        confidence = EXCLUDED.confidence,
                        source_system = EXCLUDED.source_system,
                        published_at = EXCLUDED.published_at
                    """,
                    (
                        str(signal.signal_id),
                        str(strategy_id),
                        signal.signal_timestamp,
                        signal.asset,
                        signal.direction,
                        signal.entry,
                        signal.tp,
                        signal.sl,
                        signal.confidence,
                        signal.source_system,
                        signal.published_at,
                    ),
                )
            connection.commit()


class SignalSyncService:
    def __init__(
        self,
        repository: SignalSyncRepository,
        target_config: SyncTargetConfig | None = None,
        source_system: str = DEFAULT_SOURCE_SYSTEM,
    ) -> None:
        self._repository = repository
        self._target_config = target_config or _load_signal_target_config()
        self._source_system = source_system

    def sync(self, source_rows: Iterable[dict[str, Any]]) -> int:
        if not self._target_config.enabled:
            return 0

        synced = 0
        for source_row in source_rows:
            signal = build_publishable_signal(source_row, source_system=self._source_system)
            strategy_id = self._repository.ensure_strategy(signal.strategy)
            self._repository.upsert_signal(signal, strategy_id)
            synced += 1
        return synced


def _build_postgres_dsn() -> str:
    host = os.getenv("ONLINE_DB_HOST") or os.getenv("DB_HOST", "localhost")
    port = os.getenv("ONLINE_DB_PORT") or os.getenv("DB_PORT", "5432")
    dbname = os.getenv("ONLINE_DB_NAME") or os.getenv("DB_NAME", "postgres")
    user = os.getenv("ONLINE_DB_USER") or os.getenv("DB_USER", "postgres")
    password = os.getenv("ONLINE_DB_PASSWORD") or os.getenv("DB_PASSWORD", "admin6093")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def _load_signal_target_config() -> SyncTargetConfig:
    config = load_sync_config()
    for target in config.targets:
        if target.name == "signals":
            return target
    raise ValueError("signals target is missing from sync configuration")
