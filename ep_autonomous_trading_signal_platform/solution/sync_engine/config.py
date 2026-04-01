from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "sync_config.json"


@dataclass(frozen=True)
class SyncTargetConfig:
    name: str
    enabled: bool
    interval_seconds: int
    source_schema: Path
    target_table: str
    publishable_fields: tuple[str, ...]
    excluded_internal_fields: tuple[str, ...]


@dataclass(frozen=True)
class SyncConfig:
    config_version: int
    default_interval_seconds: int
    targets: tuple[SyncTargetConfig, ...]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _load_schema_properties(schema_path: Path) -> set[str]:
    schema = _read_json(schema_path)
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(f"Schema at {schema_path} is missing an object 'properties' block")
    return set(properties.keys())


def _build_target(name: str, payload: dict[str, Any], default_interval_seconds: int) -> SyncTargetConfig:
    interval_seconds = int(payload.get("interval_seconds", default_interval_seconds))
    if interval_seconds <= 0:
        raise ValueError(f"Target '{name}' must use a positive interval_seconds")

    source_schema = (REPO_ROOT / str(payload["source_schema"])).resolve()
    if not source_schema.exists():
        raise FileNotFoundError(f"Target '{name}' references missing schema: {source_schema}")

    publishable_fields = tuple(payload["publishable_fields"])
    if not publishable_fields:
        raise ValueError(f"Target '{name}' must declare at least one publishable field")

    allowed_fields = _load_schema_properties(source_schema)
    invalid_fields = sorted(set(publishable_fields) - allowed_fields)
    if invalid_fields:
        raise ValueError(
            f"Target '{name}' includes fields not present in {source_schema.name}: {', '.join(invalid_fields)}"
        )

    excluded_internal_fields = tuple(payload.get("excluded_internal_fields", ()))

    return SyncTargetConfig(
        name=name,
        enabled=bool(payload.get("enabled", True)),
        interval_seconds=interval_seconds,
        source_schema=source_schema,
        target_table=str(payload["target_table"]),
        publishable_fields=publishable_fields,
        excluded_internal_fields=excluded_internal_fields,
    )


def load_sync_config(config_path: Path | None = None) -> SyncConfig:
    resolved_path = (config_path or DEFAULT_CONFIG_PATH).resolve()
    payload = _read_json(resolved_path)

    config_version = int(payload["config_version"])
    default_interval_seconds = int(payload["default_interval_seconds"])
    if default_interval_seconds <= 0:
        raise ValueError("default_interval_seconds must be positive")

    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, dict) or not raw_targets:
        raise ValueError("targets must be a non-empty object")

    targets = tuple(
        _build_target(name=name, payload=target_payload, default_interval_seconds=default_interval_seconds)
        for name, target_payload in raw_targets.items()
    )

    return SyncConfig(
        config_version=config_version,
        default_interval_seconds=default_interval_seconds,
        targets=targets,
    )
