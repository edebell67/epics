# epics/ep_050_distribution_engine/implementation/node_31/lead_lifecycle_tracker.py
# EP050 Node 31 — Lead Lifecycle State Machine & Revenue Tracker.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial deterministic lead lifecycle state tracker managing transitions from intake to revenue realization with attribution lineage.

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

LIFECYCLE_VERSION = "lead_lifecycle_v1.0.0"

VALID_STATUS_TRANSITIONS = {
    "lead_created": {"qualified", "disqualified"},
    "qualified": {"routed_dispatched", "rejected"},
    "routed_dispatched": {"contacted", "unreachable"},
    "contacted": {"appointment_booked", "lost_not_interested"},
    "appointment_booked": {"job_completed_won", "cancelled_lost"},
    "job_completed_won": {"revenue_realized"},
    "revenue_realized": set(),
}


class LeadLifecycleValidationError(ValueError):
    """Raised when an invalid lifecycle state transition or malformed payload is encountered."""


def derive_lifecycle_entry_id(routing_id: str, new_status: str) -> str:
    key = f"{routing_id}:{new_status}"
    return "lce_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def transition_lead_lifecycle(
    current_lifecycle_record: Mapping[str, Any] | None,
    *,
    routing_record: Mapping[str, Any],
    new_status: str,
    outcome_reason: str = "normal_progression",
    revenue_amount_gbp: float | None = None,
) -> dict[str, Any]:
    """Execute a valid deterministic lifecycle state transition for a lead."""
    if not isinstance(routing_record, Mapping):
        raise LeadLifecycleValidationError("routing_record must be an object")

    routing_id = str(routing_record.get("routing_id") or "")
    if not routing_id.startswith("lrd_"):
        raise LeadLifecycleValidationError("Valid Node 30 routing record with lrd_ prefix is required")

    lead_id = str(routing_record.get("lead_id") or "")
    target_id = str(routing_record.get("target_id") or "")

    current_status = "lead_created"
    history = []
    if current_lifecycle_record is not None:
        current_status = current_lifecycle_record.get("current_status", "lead_created")
        history = list(current_lifecycle_record.get("transition_history", []))

    valid_next = VALID_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in valid_next and current_status != new_status:
        raise LeadLifecycleValidationError(
            f"Invalid transition from {current_status!r} to {new_status!r}; allowed: {sorted(valid_next)}"
        )

    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    entry = {
        "from_status": current_status,
        "to_status": new_status,
        "reason": outcome_reason,
        "revenue_gbp": round(float(revenue_amount_gbp), 2) if revenue_amount_gbp is not None else 0.0,
        "timestamp": timestamp,
    }
    history.append(entry)

    total_rev = sum(h.get("revenue_gbp", 0.0) for h in history)

    return {
        "schema_version": "1.0.0",
        "lifecycle_entry_id": derive_lifecycle_entry_id(routing_id, new_status),
        "routing_id": routing_id,
        "lead_id": lead_id,
        "target_id": target_id,
        "current_status": new_status,
        "total_realized_revenue_gbp": round(total_rev, 2),
        "transition_history": history,
        "updated_at": timestamp,
    }
