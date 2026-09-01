# epics/ep_050_distribution_engine/implementation/operational_console_claude/test_discovery_engine.py — Discovery 00A–00F domain tests.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-21 · Covers persistence, evidence gates, rejection, validation and idempotent signal import.

from datetime import datetime, timezone

import pytest

from discovery_engine import DiscoveryError, DiscoveryStore, SCHEMA


def brief():
    return {"audience": "Independent landlords", "geography": "London", "problem_territory": "Property compliance administration", "commercial_model": "Subscription app", "constraints": "UK only"}


def signals():
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"source_url": "https://forum.example/a", "source_type": "forum", "observed_at": now, "problem_statement": "Urgent compliance deadline creates costly delays and fines", "payment_cues": ["pay subscription"], "urgency_cues": ["urgent deadline"]},
        {"source_url": "https://reviews.example/b", "source_type": "review", "observed_at": now, "problem_statement": "Landlords pay a fee to track certificates and avoid penalties", "payment_cues": ["paid fee"], "urgency_cues": ["penalty risk"]},
        {"source_url": "https://questions.example/c", "source_type": "question", "observed_at": now, "problem_statement": "Missed certificate renewals cost landlords time and money", "payment_cues": ["cost"], "urgency_cues": ["missed renewal"]},
    ]


def validations():
    now = datetime.now(timezone.utc).isoformat()
    return [{"commitment_type": "qualified_waitlist", "count": 2, "source_url": "https://validation.example/experiment/1", "observed_at": now}]


def test_create_persists_stage_00a(tmp_path):
    store = DiscoveryStore(tmp_path)
    record = store.create(brief())
    assert record["stage"] == "00A"
    assert store.load(record["discovery_id"])["brief"]["audience"] == "Independent landlords"


def test_signal_import_is_source_gated_and_idempotent(tmp_path):
    store = DiscoveryStore(tmp_path);record = store.create(brief())
    store.add_signals(record["discovery_id"], signals())
    result = store.add_signals(record["discovery_id"], signals())
    assert len(result["signals"]) == 3
    with pytest.raises(DiscoveryError):
        store.add_signals(record["discovery_id"], [{"source_url": "file:///claim", "observed_at": "now", "problem_statement": "Untraceable evidence"}])


def test_weak_evidence_rejects_without_contract(tmp_path):
    store = DiscoveryStore(tmp_path);record = store.create(brief())
    store.add_signals(record["discovery_id"], signals()[:1])
    result = store.evaluate(record["discovery_id"])
    assert result["state"] == "rejected_criteria_miss"
    assert result["contract"] is None


def test_strong_problem_waits_for_real_commitment(tmp_path):
    store = DiscoveryStore(tmp_path);record = store.create(brief())
    store.add_signals(record["discovery_id"], signals())
    result = store.evaluate(record["discovery_id"])
    assert result["state"] == "awaiting_validation"
    assert result["offer"]["claims_status"] == "hypothesis_only"


def test_validated_evidence_emits_canonical_contract(tmp_path):
    store = DiscoveryStore(tmp_path);record = store.create(brief())
    store.add_signals(record["discovery_id"], signals());store.add_validation(record["discovery_id"], validations())
    result = store.evaluate(record["discovery_id"])
    assert result["state"] == "validated_ready_to_merge"
    assert result["contract"]["schema"] == SCHEMA
    assert result["contract"]["originating_branch"] == "discovery"
    assert len(result["contract"]["real_demand_evidence"]) == 3
