# epics/ep_050_distribution_engine/implementation/node_29/test_lead_qualification.py
# EP050 Node 29 — Lead Qualification Test Suite.

from __future__ import annotations

import pytest
from lead_qualification import (
    LeadQualificationValidationError,
    evaluate_lead_qualification,
    derive_qualification_id,
)

SAMPLE_ATTRIBUTION = {
    "schema_version": "1.0.0",
    "attribution_id": "atr_99f381c8b91a",
    "lead_id": "slc_7c125740bf85",
    "target_id": "tgt_boiler_repair_blackheath",
    "opportunity_id": "opp_diagnostic_quote_001",
    "confidence_score": 0.95,
}


def test_qualify_valid_high_urgency_lead():
    res = evaluate_lead_qualification(SAMPLE_ATTRIBUTION, urgency_level="high")
    assert res["schema_version"] == "1.0.0"
    assert res["is_qualified"] is True
    assert res["qualification_id"].startswith("qlf_")
    assert res["qualification_score"] >= 0.70
    assert res["disposition"] == "approved_for_routing"


def test_disqualify_lead_outside_geography():
    res = evaluate_lead_qualification(SAMPLE_ATTRIBUTION, geo_eligible=False)
    assert res["is_qualified"] is False
    assert res["disposition"] == "rejected_disqualified"


def test_invalid_attribution_record_rejected():
    with pytest.raises(LeadQualificationValidationError, match="Valid Node 28 attribution record"):
        evaluate_lead_qualification({"attribution_id": "invalid_id"})
