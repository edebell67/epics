# epics/ep_050_distribution_engine/implementation/node_36/test_effort_allocation.py
# EP050 Node 36 — Effort Allocation Test Suite.

from __future__ import annotations

import pytest
from effort_allocation import (
    EffortAllocationValidationError,
    plan_effort_allocation,
    derive_allocation_id,
)

SAMPLE_AMPLIFICATION = {
    "schema_version": "1.0.0",
    "amplification_id": "amp_54c3b2a19876",
    "opportunity_id": "opp_diagnostic_quote_001",
    "channel": "search_landing",
}


def test_plan_effort_allocation_success():
    res = plan_effort_allocation(SAMPLE_AMPLIFICATION)
    assert res["schema_version"] == "1.0.0"
    assert res["allocation_id"].startswith("eal_")
    assert res["effort_budget"]["allocated_capacity_units"] > 0
    assert res["status"] == "approved_for_knowledge_logging"


def test_invalid_amplification_record_raises():
    with pytest.raises(EffortAllocationValidationError):
        plan_effort_allocation({"amplification_id": "invalid_plan"})
