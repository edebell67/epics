# epics/ep_050_distribution_engine/implementation/node_30/test_lead_routing.py
# EP050 Node 30 — Lead Routing Test Suite.

from __future__ import annotations

import pytest
from lead_routing import (
    LeadRoutingValidationError,
    route_qualified_lead,
    derive_routing_id,
)

SAMPLE_QUALIFICATION = {
    "schema_version": "1.0.0",
    "qualification_id": "qlf_11a2b3c4d5e6",
    "attribution_id": "atr_99f381c8b91a",
    "lead_id": "slc_7c125740bf85",
    "target_id": "tgt_boiler_repair_blackheath",
    "opportunity_id": "opp_diagnostic_quote_001",
    "is_qualified": True,
    "qualification_score": 0.85,
}


def test_route_qualified_lead_optimal_capacity():
    res = route_qualified_lead(SAMPLE_QUALIFICATION)
    assert res["schema_version"] == "1.0.0"
    assert res["routing_id"].startswith("lrd_")
    assert "allocated_provider" in res
    assert res["dispatch_status"] == "allocated_pending_handover"


def test_disqualified_lead_cannot_be_routed():
    disqualified = dict(SAMPLE_QUALIFICATION, is_qualified=False)
    with pytest.raises(LeadRoutingValidationError, match="Disqualified leads cannot be routed"):
        route_qualified_lead(disqualified)


def test_preferred_provider_routing():
    res = route_qualified_lead(SAMPLE_QUALIFICATION, preferred_provider_id="tech_london_south_01")
    assert res["allocated_provider"]["provider_id"] == "tech_london_south_01"
