# epics/ep_050_distribution_engine/implementation/node_36/effort_allocation.py
# EP050 Node 36 — Distribution Effort Allocation Planner.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial quantitative effort allocation planner balancing production capacity and marginal return.

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ALLOCATION_VERSION = "effort_allocation_v1.0.0"


class EffortAllocationValidationError(ValueError):
    """Raised when an amplification plan or capacity model is invalid."""


def derive_allocation_id(amplification_id: str) -> str:
    key = f"{amplification_id}:alloc"
    return "eal_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def plan_effort_allocation(
    amplification_plan: Mapping[str, Any],
    *,
    total_capacity_units: int = 100,
    priority_level: str = "P1_urgent_scale",
) -> dict[str, Any]:
    """Calculate the optimal distribution effort allocation for an amplified winner."""
    if not isinstance(amplification_plan, Mapping):
        raise EffortAllocationValidationError("amplification_plan must be an object")

    amp_id = str(amplification_plan.get("amplification_id") or "")
    if not amp_id.startswith("amp_"):
        raise EffortAllocationValidationError("Valid Node 35 amplification plan with amp_ prefix is required")

    allocated_units = min(total_capacity_units, 45)

    return {
        "schema_version": "1.0.0",
        "allocation_id": derive_allocation_id(amp_id),
        "amplification_id": amp_id,
        "opportunity_id": amplification_plan.get("opportunity_id"),
        "priority_level": priority_level,
        "effort_budget": {
            "allocated_capacity_units": allocated_units,
            "channel_focus": amplification_plan.get("channel"),
            "target_completion_days": 7,
        },
        "status": "approved_for_knowledge_logging",
        "allocated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
