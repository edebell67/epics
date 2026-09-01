# epics/ep_050_distribution_engine/implementation/node_01/registration.py
# EP050 Node 01 — App / Service Registration.
#
# VERSION HISTORY
# v1.0.1 · 2026-08-16 · Made register() required params keyword-optional (default None) so a missing
#                        field raises the domain ValidationError instead of a raw Python TypeError.
# v1.0.0 · 2026-08-16 · Initial deterministic, offline, fixture-only target registration.
#
# Scope: EP050 Node 01 only, per allocation 20260816T224936081_codex_bfdc1572.
# Fail-closed, deterministic, no network access, no production datastore access.
# Storage is always a local JSON file supplied by the caller (fixture/temp only).

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TARGET_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ALLOWED_STATUSES = frozenset({"active", "paused", "archived"})
REQUIRED_GEOGRAPHY_FIELDS = ("locality", "region", "country")


class RegistrationError(RuntimeError):
    """Base class for Node 01 registration failures. Fail-closed: never partially writes."""


class ValidationError(RegistrationError):
    """Raised when required fields are missing or malformed."""


class ConflictError(RegistrationError):
    """Raised when a derived target_id already exists with different field values."""


def slugify(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Expected a non-empty string, got: {value!r}")
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not slug:
        raise ValidationError(f"Value slugifies to empty string: {value!r}")
    return slug


def derive_target_id(service: str, geography: dict[str, Any]) -> str:
    """Deterministic identity: tgt_<service>_<locality>. Same inputs always produce the same id."""
    if not isinstance(geography, dict):
        raise ValidationError(f"geography must be an object, got: {type(geography).__name__}")
    locality = geography.get("locality")
    if not isinstance(locality, str) or not locality.strip():
        raise ValidationError("geography.locality is required and must be a non-empty string")
    return f"tgt_{slugify(service)}_{slugify(locality)}"


@dataclass(frozen=True)
class TargetRecord:
    target_id: str
    target_type: str
    service: str
    market: str
    geography: dict[str, str]
    app_id: str | None = None
    product: str | None = None
    domain: str | None = None
    status: str = "active"
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_fields(
    *,
    target_type: str,
    service: str,
    market: str,
    geography: dict[str, Any],
    app_id: str | None,
    product: str | None,
    domain: str | None,
    status: str,
) -> None:
    if not isinstance(target_type, str) or not TARGET_TYPE_PATTERN.match(target_type):
        raise ValidationError(
            f"target_type must be a lowercase snake_case string matching {TARGET_TYPE_PATTERN.pattern!r}, "
            f"got: {target_type!r}"
        )
    if not isinstance(service, str) or not service.strip():
        raise ValidationError(f"service is required and must be a non-empty string, got: {service!r}")
    if not isinstance(market, str) or not market.strip():
        raise ValidationError(f"market is required and must be a non-empty string, got: {market!r}")
    if not isinstance(geography, dict):
        raise ValidationError(f"geography must be an object, got: {type(geography).__name__}")
    for key in REQUIRED_GEOGRAPHY_FIELDS:
        value = geography.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"geography.{key} is required and must be a non-empty string, got: {value!r}")
    for name, value in (("app_id", app_id), ("product", product), ("domain", domain)):
        if value is not None and not isinstance(value, str):
            raise ValidationError(f"{name} must be a string or None, got: {type(value).__name__}")
    if not isinstance(status, str) or status not in ALLOWED_STATUSES:
        raise ValidationError(f"status must be one of {sorted(ALLOWED_STATUSES)}, got: {status!r}")


class TargetRegistry:
    """Local, JSON-file-backed, fixture-only Node 01 target registry. No network I/O."""

    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, dict[str, Any]]:
        raw = self.storage_path.read_text(encoding="utf-8")
        return json.loads(raw) if raw.strip() else {}

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        temp_path = self.storage_path.with_suffix(f".tmp{id(self)}")
        temp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self.storage_path)

    def register(
        self,
        *,
        target_type: str | None = None,
        service: str | None = None,
        market: str | None = None,
        geography: dict[str, str] | None = None,
        app_id: str | None = None,
        product: str | None = None,
        domain: str | None = None,
        status: str = "active",
    ) -> TargetRecord:
        validate_fields(
            target_type=target_type,
            service=service,
            market=market,
            geography=geography,
            app_id=app_id,
            product=product,
            domain=domain,
            status=status,
        )
        target_id = derive_target_id(service, geography)
        candidate = TargetRecord(
            target_id=target_id,
            target_type=target_type,
            service=service,
            market=market,
            geography=dict(geography),
            app_id=app_id,
            product=product,
            domain=domain,
            status=status,
        )

        data = self._load()
        existing = data.get(target_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "registered_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "registered_at"}
            if comparable_existing == comparable_candidate:
                return TargetRecord(**existing)  # idempotent: identical re-registration, no write
            raise ConflictError(
                f"target_id {target_id!r} already registered with different field values; "
                "conflicting duplicate registrations are rejected fail-closed"
            )

        data[target_id] = candidate.to_dict()
        self._save(data)
        return candidate

    def get(self, target_id: str) -> TargetRecord | None:
        data = self._load()
        record = data.get(target_id)
        return TargetRecord(**record) if record is not None else None

    def list(self) -> list[TargetRecord]:
        return [TargetRecord(**record) for record in self._load().values()]
