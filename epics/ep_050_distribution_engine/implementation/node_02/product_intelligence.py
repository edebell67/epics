# epics/ep_050_distribution_engine/implementation/node_02/product_intelligence.py
# EP050 Node 02 — Product Intelligence.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-16 · Initial deterministic, offline, fixture-only product intelligence registry.
#
# Scope: EP050 Node 02 only, per allocation 20260816T232500118_codex_343bbaf9.
# Fail-closed, deterministic, no network access, no production datastore access.
# Every record must reference a target_id already registered by Node 01 (contract dependency).

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
from registration import TargetRegistry  # noqa: E402


class ProductIntelligenceError(RuntimeError):
    """Base class for Node 02 failures. Fail-closed: never partially writes."""


class ValidationError(ProductIntelligenceError):
    """Raised when required fields are missing or malformed."""


class UnknownTargetError(ProductIntelligenceError):
    """Raised when the referenced target_id is not registered in the Node 01 registry."""


class ConflictError(ProductIntelligenceError):
    """Raised when a target_id already has a product intelligence record with different content."""


REQUIRED_LIST_FIELDS = ("features", "benefits", "differentiators")
REQUIRED_TEXT_FIELDS = ("problem", "solution", "commercial_model", "customer_outcome")


def _validate_non_empty_string(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is required and must be a non-empty string, got: {value!r}")


def _validate_non_empty_string_list(name: str, value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{name} is required and must be a non-empty list, got: {value!r}")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{name}[{index}] must be a non-empty string, got: {item!r}")


def validate_fields(
    *,
    target_id: str,
    problem: str,
    solution: str,
    features: list[str],
    benefits: list[str],
    differentiators: list[str],
    commercial_model: str,
    customer_outcome: str,
    evidence_sources: list[str] | None,
) -> None:
    _validate_non_empty_string("target_id", target_id)
    _validate_non_empty_string("problem", problem)
    _validate_non_empty_string("solution", solution)
    _validate_non_empty_string_list("features", features)
    _validate_non_empty_string_list("benefits", benefits)
    _validate_non_empty_string_list("differentiators", differentiators)
    _validate_non_empty_string("commercial_model", commercial_model)
    _validate_non_empty_string("customer_outcome", customer_outcome)
    if evidence_sources is not None:
        if not isinstance(evidence_sources, list):
            raise ValidationError(f"evidence_sources must be a list or None, got: {type(evidence_sources).__name__}")
        for index, item in enumerate(evidence_sources):
            if not isinstance(item, str) or not item.strip():
                raise ValidationError(f"evidence_sources[{index}] must be a non-empty string, got: {item!r}")


@dataclass(frozen=True)
class ProductIntelligenceRecord:
    target_id: str
    problem: str
    solution: str
    features: list[str]
    benefits: list[str]
    differentiators: list[str]
    commercial_model: str
    customer_outcome: str
    evidence_sources: list[str] = field(default_factory=list)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProductIntelligenceRegistry:
    """Local, JSON-file-backed, fixture-only Node 02 registry. No network I/O.

    One product-intelligence record per target_id (target_id is the natural key),
    mirroring Node 01's idempotent/conflict pattern.
    """

    def __init__(self, storage_path: Path, target_registry: TargetRegistry):
        self.storage_path = Path(storage_path)
        self.target_registry = target_registry
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
        problem: str | None = None,
        solution: str | None = None,
        features: list[str] | None = None,
        benefits: list[str] | None = None,
        differentiators: list[str] | None = None,
        commercial_model: str | None = None,
        customer_outcome: str | None = None,
        evidence_sources: list[str] | None = None,
    ) -> ProductIntelligenceRecord:
        validate_fields(
            target_id=target_id,
            problem=problem,
            solution=solution,
            features=features,
            benefits=benefits,
            differentiators=differentiators,
            commercial_model=commercial_model,
            customer_outcome=customer_outcome,
            evidence_sources=evidence_sources,
        )

        # Node01->02 contract/integration check: target must already be registered, fail-closed.
        if self.target_registry.get(target_id) is None:
            raise UnknownTargetError(
                f"target_id {target_id!r} is not registered in the Node 01 registry; "
                "Node 02 cannot describe a product for an unregistered target"
            )

        candidate = ProductIntelligenceRecord(
            target_id=target_id,
            problem=problem,
            solution=solution,
            features=list(features),
            benefits=list(benefits),
            differentiators=list(differentiators),
            commercial_model=commercial_model,
            customer_outcome=customer_outcome,
            evidence_sources=list(evidence_sources) if evidence_sources else [],
        )

        data = self._load()
        existing = data.get(target_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "recorded_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "recorded_at"}
            if comparable_existing == comparable_candidate:
                return ProductIntelligenceRecord(**existing)  # idempotent: identical re-registration
            raise ConflictError(
                f"target_id {target_id!r} already has a product intelligence record with different "
                "content; conflicting duplicate registrations are rejected fail-closed"
            )

        data[target_id] = candidate.to_dict()
        self._save(data)
        return candidate

    def get(self, target_id: str) -> ProductIntelligenceRecord | None:
        data = self._load()
        record = data.get(target_id)
        return ProductIntelligenceRecord(**record) if record is not None else None

    def list(self) -> list[ProductIntelligenceRecord]:
        return [ProductIntelligenceRecord(**record) for record in self._load().values()]
