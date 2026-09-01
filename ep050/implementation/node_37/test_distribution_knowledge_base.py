# epics/ep_050_distribution_engine/implementation/node_37/test_distribution_knowledge_base.py
# EP050 Node 37 — Distribution Knowledge Base Test Suite.

from __future__ import annotations

import pytest
from distribution_knowledge_base import (
    KnowledgeBaseValidationError,
    record_distribution_knowledge,
    derive_knowledge_entry_id,
)

SAMPLE_ALLOCATION = {
    "schema_version": "1.0.0",
    "allocation_id": "eal_887766554433",
    "opportunity_id": "opp_diagnostic_quote_001",
    "channel_focus": "search_landing",
}


REAL_SUMMARY = "Test-supplied observed learning summary for regression coverage."
REAL_FACTORS = ["Test-supplied factor one", "Test-supplied factor two"]
REAL_RULES = ["Test-supplied rule one"]


def test_record_distribution_knowledge_success():
    res = record_distribution_knowledge(
        SAMPLE_ALLOCATION,
        learning_summary=REAL_SUMMARY,
        key_success_factors=REAL_FACTORS,
        recommended_rules=REAL_RULES,
    )
    assert res["schema_version"] == "1.0.0"
    assert res["knowledge_entry_id"].startswith("dkb_")
    assert res["learning_summary"] == REAL_SUMMARY
    assert res["key_success_factors"] == REAL_FACTORS
    assert res["recommended_rules"] == REAL_RULES
    assert res["provenance"]["lifecycle_complete"] is True


def test_invalid_allocation_record_raises():
    with pytest.raises(KnowledgeBaseValidationError):
        record_distribution_knowledge(
            {"allocation_id": "bad_alloc"},
            learning_summary=REAL_SUMMARY,
            key_success_factors=REAL_FACTORS,
            recommended_rules=REAL_RULES,
        )


def test_missing_learning_summary_raises():
    with pytest.raises(KnowledgeBaseValidationError):
        record_distribution_knowledge(
            SAMPLE_ALLOCATION, learning_summary="", key_success_factors=REAL_FACTORS, recommended_rules=REAL_RULES
        )


def test_missing_key_success_factors_raises():
    with pytest.raises(KnowledgeBaseValidationError):
        record_distribution_knowledge(
            SAMPLE_ALLOCATION, learning_summary=REAL_SUMMARY, key_success_factors=[], recommended_rules=REAL_RULES
        )


def test_missing_recommended_rules_raises():
    with pytest.raises(KnowledgeBaseValidationError):
        record_distribution_knowledge(
            SAMPLE_ALLOCATION, learning_summary=REAL_SUMMARY, key_success_factors=REAL_FACTORS, recommended_rules=[]
        )
