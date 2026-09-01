# epics/ep_050_distribution_engine/implementation/node_03/audience_definition.py
# EP050 Node 03 — Audience Definition.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-16 · Initial deterministic, offline, fixture-only, privacy-safe audience segment registry.
#
# Scope: EP050 Node 03 only, per allocation 20260816T234617397_codex_0c8c6179.
# Fail-closed, deterministic, no network access, no production datastore access.
# Every record must reference a target_id already registered by Node 01 AND described by Node 02.
# Free-text fields are screened for prohibited PII patterns (email, phone) and rejected fail-closed.

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_02"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402

ALLOWED_URGENCY = frozenset({"low", "medium", "high", "emergency"})
REQUIRED_GEOGRAPHY_FIELDS = ("locality", "region", "country")

# Fail-closed PII screen: reject obvious email addresses and phone-number-like sequences
# in any free-text field. This is intentionally conservative (may over-reject) since the
# node must never persist prohibited PII.
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s\-.]?){7,}\d")


class AudienceDefinitionError(RuntimeError):
    """Base class for Node 03 failures. Fail-closed: never partially writes."""


class ValidationError(AudienceDefinitionError):
    """Raised when required fields are missing, malformed, or contain prohibited PII."""


class UnknownTargetError(AudienceDefinitionError):
    """Raised when the referenced target_id is not registered (Node 01) or described (Node 02)."""


class ConflictError(AudienceDefinitionError):
    """Raised when a segment_id already exists with different field values."""


def slugify(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Expected a non-empty string, got: {value!r}")
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not slug:
        raise ValidationError(f"Value slugifies to empty string: {value!r}")
    return slug


def derive_segment_id(target_id: str, segment_name: str) -> str:
    """Deterministic identity: <target_id>__seg_<segment_name>. Same inputs always produce the same id."""
    if not isinstance(target_id, str) or not target_id.strip():
        raise ValidationError(f"target_id is required and must be a non-empty string, got: {target_id!r}")
    return f"{target_id}__seg_{slugify(segment_name)}"


def _check_no_pii(name: str, value: str) -> None:
    if EMAIL_PATTERN.search(value):
        raise ValidationError(f"{name} appears to contain an email address; prohibited PII rejected fail-closed")
    if PHONE_PATTERN.search(value):
        raise ValidationError(f"{name} appears to contain a phone number; prohibited PII rejected fail-closed")


def _validate_non_empty_string(name: str, value: Any, *, check_pii: bool = True) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is required and must be a non-empty string, got: {value!r}")
    if check_pii:
        _check_no_pii(name, value)


def _validate_non_empty_string_list(name: str, value: Any, *, check_pii: bool = True) -> None:
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{name} is required and must be a non-empty list, got: {value!r}")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{name}[{index}] must be a non-empty string, got: {item!r}")
        if check_pii:
            _check_no_pii(f"{name}[{index}]", item)


def _validate_optional_string_list(name: str, value: Any, *, check_pii: bool = True) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise ValidationError(f"{name} must be a list or None, got: {type(value).__name__}")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{name}[{index}] must be a non-empty string, got: {item!r}")
        if check_pii:
            _check_no_pii(f"{name}[{index}]", item)


def _validate_geography(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"eligibility_geography must be an object, got: {type(value).__name__}")
    for key in REQUIRED_GEOGRAPHY_FIELDS:
        subvalue = value.get(key)
        if not isinstance(subvalue, str) or not subvalue.strip():
            raise ValidationError(f"eligibility_geography.{key} is required and must be a non-empty string")


def validate_fields(
    *,
    target_id: str,
    segment_name: str,
    needs: list[str],
    pains: list[str],
    urgency: str,
    eligibility_geography: dict[str, Any],
    exclusions: list[str] | None,
    evidence_sources: list[str] | None,
) -> None:
    _validate_non_empty_string("target_id", target_id, check_pii=False)
    _validate_non_empty_string("segment_name", segment_name)
    _validate_non_empty_string_list("needs", needs)
    _validate_non_empty_string_list("pains", pains)
    if not isinstance(urgency, str) or urgency not in ALLOWED_URGENCY:
        raise ValidationError(f"urgency must be one of {sorted(ALLOWED_URGENCY)}, got: {urgency!r}")
    _validate_geography(eligibility_geography)
    _validate_optional_string_list("exclusions", exclusions)
    _validate_optional_string_list("evidence_sources", evidence_sources)


@dataclass(frozen=True)
class AudienceSegmentRecord:
    segment_id: str
    target_id: str
    segment_name: str
    needs: list[str]
    pains: list[str]
    urgency: str
    eligibility_geography: dict[str, str]
    exclusions: list[str] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AudienceSegmentRegistry:
    """Local, JSON-file-backed, fixture-only Node 03 registry. No network I/O.

    Requires the referenced target_id to exist in BOTH the Node 01 TargetRegistry
    and the Node 02 ProductIntelligenceRegistry (real, not mocked, lineage checks).
    """

    def __init__(
        self,
        storage_path: Path,
        target_registry: TargetRegistry,
        product_registry: ProductIntelligenceRegistry,
    ):
        self.storage_path = Path(storage_path)
        self.target_registry = target_registry
        self.product_registry = product_registry
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
        target_id: str | None = None,
        segment_name: str | None = None,
        needs: list[str] | None = None,
        pains: list[str] | None = None,
        urgency: str | None = None,
        eligibility_geography: dict[str, str] | None = None,
        exclusions: list[str] | None = None,
        evidence_sources: list[str] | None = None,
    ) -> AudienceSegmentRecord:
        validate_fields(
            target_id=target_id,
            segment_name=segment_name,
            needs=needs,
            pains=pains,
            urgency=urgency,
            eligibility_geography=eligibility_geography,
            exclusions=exclusions,
            evidence_sources=evidence_sources,
        )

        # Node01+Node02->03 contract/integration checks: both must exist, fail-closed.
        if self.target_registry.get(target_id) is None:
            raise UnknownTargetError(
                f"target_id {target_id!r} is not registered in the Node 01 registry; "
                "Node 03 cannot define an audience for an unregistered target"
            )
        if self.product_registry.get(target_id) is None:
            raise UnknownTargetError(
                f"target_id {target_id!r} has no Node 02 product intelligence record; "
                "Node 03 requires product context before defining an audience"
            )

        segment_id = derive_segment_id(target_id, segment_name)
        candidate = AudienceSegmentRecord(
            segment_id=segment_id,
            target_id=target_id,
            segment_name=segment_name,
            needs=list(needs),
            pains=list(pains),
            urgency=urgency,
            eligibility_geography=dict(eligibility_geography),
            exclusions=list(exclusions) if exclusions else [],
            evidence_sources=list(evidence_sources) if evidence_sources else [],
        )

        data = self._load()
        existing = data.get(segment_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "recorded_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "recorded_at"}
            if comparable_existing == comparable_candidate:
                return AudienceSegmentRecord(**existing)  # idempotent
            raise ConflictError(
                f"segment_id {segment_id!r} already registered with different field values; "
                "conflicting duplicate registrations are rejected fail-closed"
            )

        data[segment_id] = candidate.to_dict()
        self._save(data)
        return candidate

    def get(self, segment_id: str) -> AudienceSegmentRecord | None:
        data = self._load()
        record = data.get(segment_id)
        return AudienceSegmentRecord(**record) if record is not None else None

    def list(self) -> list[AudienceSegmentRecord]:
        return [AudienceSegmentRecord(**record) for record in self._load().values()]

    def list_for_target(self, target_id: str) -> list[AudienceSegmentRecord]:
        return [record for record in self.list() if record.target_id == target_id]
