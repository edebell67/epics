# epics/ep_050_distribution_engine/implementation/node_33/test_outcome_feedback.py
# EP050 Node 33 — Outcome Feedback Test Suite.

from __future__ import annotations

import pytest
from outcome_feedback import (
    OutcomeFeedbackValidationError,
    ingest_outcome_feedback,
    derive_feedback_id,
)


def test_ingest_outcome_feedback_success():
    res = ingest_outcome_feedback(
        lead_id="slc_7c125740bf85",
        target_id="tgt_boiler_repair_blackheath",
        feedback_source="crm_sync",
        job_status="completed_satisfied",
        customer_rating=5,
        actual_invoice_gbp=220.0,
    )
    assert res["schema_version"] == "1.0.0"
    assert res["feedback_id"].startswith("ofb_")
    assert res["outcome"]["customer_rating"] == 5
    assert res["outcome"]["actual_invoice_gbp"] == 220.0


def test_unsupported_feedback_source_rejected():
    with pytest.raises(OutcomeFeedbackValidationError, match="feedback_source must be one of"):
        ingest_outcome_feedback(
            lead_id="slc_1",
            target_id="tgt_1",
            feedback_source="unverified_twitter_dm",
        )
