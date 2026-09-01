# epics/ep_050_distribution_engine/implementation/node_04/conversion_definition.py
# EP050 Node 04 — Conversion Definition.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial deterministic, offline, fixture-only conversion/funnel definition registry.
#
# Scope: EP050 Node 04 only, per allocation 20260817T000604746_codex_02584543.
# Fail-closed, deterministic, no network access, no production datastore access.
# Every record must reference a target_id registered by Node 01, described by Node 02,
# and with at least one audience segment defined by Node 03 (exact target/product/audience lineage).

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_02"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_03"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402

# The master spec's own worked funnel (§9 Node 04): Visit -> Engage -> Tool use -> Enquiry ->
# Lead -> Qualified lead -> Booking -> Sale -> Revenue. Used as the confirmed default fixture.
MASTER_SPEC_STAGES = [
    {"stage_id": "visit", "label": "Visit", "order": 1},
    {"stage_id": "engage", "label": "Engage", "order": 2},
    {"stage_id": "tool_use", "label": "Tool use", "order": 3},
    {"stage_id": "enquiry", "label": "Enquiry", "order": 4},
    {"stage_id": "lead", "label": "Lead", "order": 5},
    {"stage_id": "qualified_lead", "label": "Qualified lead", "order": 6},
    {"stage_id": "booking", "label": "Booking", "order": 7},
    {"stage_id": "sale", "label": "Sale", "order": 8},
    {"stage_id": "revenue", "label": "Revenue", "order": 9},
]


class ConversionDefinitionError(RuntimeError):
    """Base class for Node 04 failures. Fail-closed: never partially writes."""


class ValidationError(ConversionDefinitionError):
    """Raised when required fields are missing or malformed."""


class UnknownTargetError(ConversionDefinitionError):
    """Raised when the referenced target_id is not registered/described/segmented upstream."""


class ConflictError(ConversionDefinitionError):
    """Raised when a target_id already has a conversion definition with different content."""


def _validate_non_empty_string(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is required and must be a non-empty string, got: {value!r}")


def _validate_stages(stages: Any) -> dict[str, int]:
    if not isinstance(stages, list) or not stages:
        raise ValidationError(f"stages is required and must be a non-empty list, got: {stages!r}")
    order_by_id: dict[str, int] = {}
    seen_orders: set[int] = set()
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            raise ValidationError(f"stages[{index}] must be an object, got: {type(stage).__name__}")
        stage_id = stage.get("stage_id")
        label = stage.get("label")
        order = stage.get("order")
        if not isinstance(stage_id, str) or not stage_id.strip():
            raise ValidationError(f"stages[{index}].stage_id must be a non-empty string")
        if not isinstance(label, str) or not label.strip():
            raise ValidationError(f"stages[{index}].label must be a non-empty string")
        if isinstance(order, bool) or not isinstance(order, int) or order <= 0:
            raise ValidationError(f"stages[{index}].order must be a positive integer")
        if stage_id in order_by_id:
            raise ValidationError(f"Duplicate stage_id in stages: {stage_id!r}")
        if order in seen_orders:
            raise ValidationError(f"Duplicate order in stages: {order!r}")
        order_by_id[stage_id] = order
        seen_orders.add(order)
    expected_orders = set(range(1, len(stages) + 1))
    if seen_orders != expected_orders:
        raise ValidationError(
            f"stages.order values must be exactly 1..{len(stages)} with no gaps or duplicates, "
            f"got: {sorted(seen_orders)}"
        )
    return order_by_id


def _validate_allowed_transitions(allowed_transitions: Any, order_by_id: dict[str, int]) -> None:
    if not isinstance(allowed_transitions, list) or not allowed_transitions:
        raise ValidationError("allowed_transitions is required and must be a non-empty list")
    seen_pairs: set[tuple[str, str]] = set()
    for index, transition in enumerate(allowed_transitions):
        if (
            not isinstance(transition, (list, tuple))
            or len(transition) != 2
            or not all(isinstance(x, str) for x in transition)
        ):
            raise ValidationError(f"allowed_transitions[{index}] must be a 2-item [from_stage_id, to_stage_id] list")
        from_id, to_id = transition
        if from_id not in order_by_id:
            raise ValidationError(f"allowed_transitions[{index}] references unknown from_stage_id: {from_id!r}")
        if to_id not in order_by_id:
            raise ValidationError(f"allowed_transitions[{index}] references unknown to_stage_id: {to_id!r}")
        if order_by_id[to_id] <= order_by_id[from_id]:
            raise ValidationError(
                f"allowed_transitions[{index}] must move forward in stage order "
                f"({from_id}[{order_by_id[from_id]}] -> {to_id}[{order_by_id[to_id]}])"
            )
        pair = (from_id, to_id)
        if pair in seen_pairs:
            raise ValidationError(f"Duplicate transition in allowed_transitions: {pair!r}")
        seen_pairs.add(pair)


def validate_fields(
    *,
    target_id: str,
    stages: list[dict[str, Any]],
    allowed_transitions: list[list[str]],
    success_stage_id: str,
    success_criteria: str,
) -> None:
    _validate_non_empty_string("target_id", target_id)
    order_by_id = _validate_stages(stages)
    _validate_allowed_transitions(allowed_transitions, order_by_id)
    _validate_non_empty_string("success_stage_id", success_stage_id)
    if success_stage_id not in order_by_id:
        raise ValidationError(f"success_stage_id {success_stage_id!r} is not one of the declared stages")
    _validate_non_empty_string("success_criteria", success_criteria)


@dataclass(frozen=True)
class ConversionDefinitionRecord:
    target_id: str
    stages: list[dict[str, Any]]
    allowed_transitions: list[list[str]]
    success_stage_id: str
    success_criteria: str
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConversionDefinitionRegistry:
    """Local, JSON-file-backed, fixture-only Node 04 registry. No network I/O.

    Requires the referenced target_id to exist in the Node 01 TargetRegistry, be described
    in the Node 02 ProductIntelligenceRegistry, and have at least one Node 03 audience segment
    (real, non-mocked, exact target/product/audience lineage per the allocation).
    """

    def __init__(
        self,
        storage_path: Path,
        target_registry: TargetRegistry,
        product_registry: ProductIntelligenceRegistry,
        audience_registry: AudienceSegmentRegistry,
    ):
        self.storage_path = Path(storage_path)
        self.target_registry = target_registry
        self.product_registry = product_registry
        self.audience_registry = audience_registry
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
        stages: list[dict[str, Any]] | None = None,
        allowed_transitions: list[list[str]] | None = None,
        success_stage_id: str | None = None,
        success_criteria: str | None = None,
    ) -> ConversionDefinitionRecord:
        validate_fields(
            target_id=target_id,
            stages=stages,
            allowed_transitions=allowed_transitions,
            success_stage_id=success_stage_id,
            success_criteria=success_criteria,
        )

        # Node01+Node02+Node03->04 contract/integration checks: all three must exist, fail-closed.
        if self.target_registry.get(target_id) is None:
            raise UnknownTargetError(
                f"target_id {target_id!r} is not registered in the Node 01 registry; "
                "Node 04 cannot define conversion for an unregistered target"
            )
        if self.product_registry.get(target_id) is None:
            raise UnknownTargetError(
                f"target_id {target_id!r} has no Node 02 product intelligence record; "
                "Node 04 requires product context before defining conversion"
            )
        if not self.audience_registry.list_for_target(target_id):
            raise UnknownTargetError(
                f"target_id {target_id!r} has no Node 03 audience segment; "
                "Node 04 requires at least one defined audience before defining conversion"
            )

        candidate = ConversionDefinitionRecord(
            target_id=target_id,
            stages=[dict(stage) for stage in stages],
            allowed_transitions=[list(t) for t in allowed_transitions],
            success_stage_id=success_stage_id,
            success_criteria=success_criteria,
        )

        data = self._load()
        existing = data.get(target_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "recorded_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "recorded_at"}
            if comparable_existing == comparable_candidate:
                return ConversionDefinitionRecord(**existing)  # idempotent
            raise ConflictError(
                f"target_id {target_id!r} already has a conversion definition with different "
                "content; conflicting duplicate registrations are rejected fail-closed"
            )

        data[target_id] = candidate.to_dict()
        self._save(data)
        return candidate

    def get(self, target_id: str) -> ConversionDefinitionRecord | None:
        data = self._load()
        record = data.get(target_id)
        return ConversionDefinitionRecord(**record) if record is not None else None

    def list(self) -> list[ConversionDefinitionRecord]:
        return [ConversionDefinitionRecord(**record) for record in self._load().values()]
