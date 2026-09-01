# epics/ep_050_distribution_engine/implementation/node_31/test_lead_lifecycle_tracker.py
# EP050 Node 31 — Lead Lifecycle Tracker Test Suite.

from __future__ import annotations

import pytest
from lead_lifecycle_tracker import (
    LeadLifecycleValidationError,
    transition_lead_lifecycle,
    derive_lifecycle_entry_id,
)

SAMPLE_ROUTING = {
    "schema_version": "1.0.0",
    "routing_id": "lrd_99a8b7c6d5e4",
    "qualification_id": "qlf_11a2b3c4d5e6",
    "lead_id": "slc_7c125740bf85",
    "target_id": "tgt_boiler_repair_blackheath",
    "allocated_provider": {"provider_id": "tech_london_south_01"},
}


def test_valid_lifecycle_progression_to_revenue():
    # 1. Lead Created -> Qualified
    s1 = transition_lead_lifecycle(None, routing_record=SAMPLE_ROUTING, new_status="qualified")
    assert s1["current_status"] == "qualified"

    # 2. Qualified -> Routed / Dispatched
    s2 = transition_lead_lifecycle(s1, routing_record=SAMPLE_ROUTING, new_status="routed_dispatched")
    assert s2["current_status"] == "routed_dispatched"

    # 3. Routed -> Contacted
    s3 = transition_lead_lifecycle(s2, routing_record=SAMPLE_ROUTING, new_status="contacted")
    assert s3["current_status"] == "contacted"

    # 4. Contacted -> Appointment Booked
    s4 = transition_lead_lifecycle(s3, routing_record=SAMPLE_ROUTING, new_status="appointment_booked")
    assert s4["current_status"] == "appointment_booked"

    # 5. Booked -> Job Completed Won
    s5 = transition_lead_lifecycle(s4, routing_record=SAMPLE_ROUTING, new_status="job_completed_won")
    assert s5["current_status"] == "job_completed_won"

    # 6. Won -> Revenue Realized (£240.00)
    s6 = transition_lead_lifecycle(s5, routing_record=SAMPLE_ROUTING, new_status="revenue_realized", revenue_amount_gbp=240.0)
    assert s6["current_status"] == "revenue_realized"
    assert s6["total_realized_revenue_gbp"] == 240.0
    assert len(s6["transition_history"]) == 6


def test_invalid_lifecycle_transition_raises():
    s1 = transition_lead_lifecycle(None, routing_record=SAMPLE_ROUTING, new_status="qualified")
    with pytest.raises(LeadLifecycleValidationError, match="Invalid transition"):
        # Skipping to revenue directly is prohibited
        transition_lead_lifecycle(s1, routing_record=SAMPLE_ROUTING, new_status="revenue_realized")
