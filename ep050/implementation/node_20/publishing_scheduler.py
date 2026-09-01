# epics/ep_050_distribution_engine/implementation/node_20/publishing_scheduler.py — Offline-only canonical Node 19 mock-plan consumer.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Retains canonical validation consumer for consolidated current-code regression reconciliation; no external behavior added.
# v1.0.0 · 2026-08-17 · Initial offline-only Node 20 mock-plan consumer.

"""EP050 Node 20: offline-only mock publication-plan consumer.

Consumes a canonical Node 19 approved asset package and returns an in-memory,
non-executing publication plan.  It has no adapter, queue, credential, socket,
or time-triggering capability.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


class PublicationPlanValidationError(ValueError):
    """Raised when a package cannot safely become a local mock plan."""


class PublicationPlanConflictError(ValueError):
    """Raised if an existing plan ID maps to a different immutable record."""


_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "integration/canonical_contracts/20260817_node19_to_node20_canonical_contract_v1_1.json"
)


def load_canonical_contract() -> dict[str, Any]:
    """Load the local promoted contract; no network access is performed."""
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


def _as_mapping(package: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(package, Mapping):
        return deepcopy(dict(package))
    to_dict = getattr(package, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, Mapping):
            return deepcopy(dict(value))
    raise PublicationPlanValidationError("package must be a mapping or Node 19 package with to_dict()")


def _validate(schema: Mapping[str, Any], value: Mapping[str, Any]) -> None:
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    except ValidationError as error:
        raise PublicationPlanValidationError(error.message) from error


def _require_iso8601(name: str, value: Any) -> None:
    if not isinstance(value, str):
        raise PublicationPlanValidationError(f"{name} must be ISO-8601 date-time")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PublicationPlanValidationError(f"{name} must be ISO-8601 date-time") from error


def validate_approved_asset_package(package: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Validate canonical schema plus semantic lineage and timestamp gates."""
    payload = _as_mapping(package)
    contract = load_canonical_contract()
    _validate(contract["approved_asset_package_schema"], payload)
    for name, value in (
        ("generated_at", payload["generated_at"]),
        ("compliance_stamp.checked_at", payload["compliance_stamp"]["checked_at"]),
        ("schedule_request.scheduled_at", payload["schedule_request"]["scheduled_at"]),
    ):
        _require_iso8601(name, value)
    if payload["cta_definition"]["tracking_params"]["asset_id"] != payload["asset_id"]:
        raise PublicationPlanValidationError("tracking asset_id must equal asset_id")
    if payload["schedule_request"]["channel"] not in payload["target_channels"]:
        raise PublicationPlanValidationError("schedule channel must be a declared target channel")
    return payload


def derive_publication_plan_id(payload: Mapping[str, Any]) -> str:
    """Create the canonical SHA-256 plan ID from the five-field idempotency key."""
    key = {
        "asset_id": payload["asset_id"],
        "channel": payload["schedule_request"]["channel"],
        "destination_url": payload["cta_definition"]["destination_url"],
        "audience": payload["schedule_request"]["audience"],
        "scheduled_at": payload["schedule_request"]["scheduled_at"],
    }
    encoded = json.dumps(key, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "mpp_" + hashlib.sha256(encoded).hexdigest()


def build_mock_publication_plan(package: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Create a schema-valid, non-executing local publication-plan record."""
    payload = validate_approved_asset_package(package)
    plan = {
        "schema_version": payload["schema_version"],
        "publication_plan_id": derive_publication_plan_id(payload),
        "asset_id": payload["asset_id"],
        "target_id": payload["target_id"],
        "opportunity_id": payload["opportunity_id"],
        "channel": payload["schedule_request"]["channel"],
        "audience": payload["schedule_request"]["audience"],
        "scheduled_at": payload["schedule_request"]["scheduled_at"],
        "cta": {
            "label": payload["cta_definition"]["cta_label"],
            "type": payload["cta_definition"]["cta_type"],
            "destination_url": payload["cta_definition"]["destination_url"],
            "tracking_params": deepcopy(payload["cta_definition"]["tracking_params"]),
        },
        "approval_state": "approved",
        "external_action": False,
    }
    _validate(load_canonical_contract()["mock_publication_plan_schema"], plan)
    return plan


@dataclass
class InMemoryMockPublicationRepository:
    """Idempotent local-only repository; intentionally not durable or dispatch-capable."""

    _plans: dict[str, dict[str, Any]] = field(default_factory=dict)

    def store(self, plan: Mapping[str, Any]) -> dict[str, Any]:
        plan_copy = deepcopy(dict(plan))
        plan_id = plan_copy["publication_plan_id"]
        existing = self._plans.get(plan_id)
        if existing is not None:
            if existing != plan_copy:
                raise PublicationPlanConflictError(f"conflicting record for {plan_id}")
            return deepcopy(existing)
        self._plans[plan_id] = plan_copy
        return deepcopy(plan_copy)


def create_mock_publication_plan(
    package: Mapping[str, Any] | Any,
    repository: InMemoryMockPublicationRepository | None = None,
) -> dict[str, Any]:
    """Validate, project, and retain only an in-memory mock plan."""
    plan = build_mock_publication_plan(package)
    return (repository or InMemoryMockPublicationRepository()).store(plan)
