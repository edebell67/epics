"""
EP050 Node 12: Opportunity Scoring — Test & Verification Suite

Validates:
1. Deterministic Demand Opportunity Score (DOS v1.0) calculation
2. Priority tiering (TIER_1_IMMEDIATE to TIER_4_LOW)
3. Direct integration with Node 11 IntentClassificationResult (non-mocked)
4. Full lineage preservation (target_id, signal_id, classification_id)
5. Explainable component score breakdown
6. Fail-closed validation for missing lineage, bad inputs, and invalid weights
7. Idempotency & determinism of opportunity_id
8. Serialization / JSON round-trip
9. Offline execution assertion (no sockets)

VERSION HISTORY
- v1.0.1 · 2026-09-01 · Normalizes release whitespace so the canonical package passes staged integrity checks; test behavior is unchanged.
- v1.0.0 · 2026-08-17 · Initial complete test suite for Node 12 Opportunity Scoring.
"""

import json
import socket
import pytest
from opportunity_scoring import (
    score_demand_opportunity,
    DemandOpportunityRecord,
    ComponentScoreBreakdown,
    ValidationError,
    LineageError,
    DEFAULT_WEIGHTS
)

# Import Node 11 directly for real upstream integration test
from intent_classification import classify_demand_signal, IntentClassificationResult


@pytest.fixture(autouse=True)
def assert_no_network(monkeypatch):
    """Enforces 100% offline execution by blocking socket creation."""
    def _blocked_socket(*args, **kwargs):
        raise RuntimeError("Network socket creation is prohibited during EP050 tests.")
    monkeypatch.setattr(socket, "socket", _blocked_socket)


@pytest.fixture
def valid_classification_dict():
    return {
        "classification_id": "cls_sig_boiler_001_abc12345",
        "target_id": "tgt_boiler_repair_blackheath",
        "signal_id": "sig_20260816_boiler_press_01",
        "primary_intent": "troubleshooting",
        "secondary_intents": ["emergency_service"],
        "urgency_level": "high",
        "troubleshooting_score": 1.0,
        "commercial_score": 0.0,
        "geography": {
            "locality": "Blackheath",
            "region": "London",
            "country": "UK"
        },
        "service_context": {
            "service_name": "boiler_repair",
            "market_segment": "domestic_plumbing"
        }
    }


def test_positive_opportunity_scoring(valid_classification_dict):
    """Validates positive DOS score calculation and Tier 1 assignment."""
    record = score_demand_opportunity(valid_classification_dict)

    assert isinstance(record, DemandOpportunityRecord)
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.signal_id == "sig_20260816_boiler_press_01"
    assert record.classification_id == "cls_sig_boiler_001_abc12345"
    assert record.opportunity_id.startswith("opp_")
    assert record.formula_version == "DOS_v1.0"

    # High urgency (1.0 * 35) + Troubleshooting (1.0 * 30) + Service (1.0 * 20) + Geo (1.0 * 15) = 100.0
    assert record.demand_opportunity_score == 100.0
    assert record.priority_tier == "TIER_1_IMMEDIATE"

    # Verify component breakdown
    b = record.component_breakdown
    assert b.urgency_component == 35.0
    assert b.intent_viability_component == 30.0
    assert b.service_alignment_component == 20.0
    assert b.geographic_alignment_component == 15.0


def test_real_node11_to_node12_integration():
    """Real upstream integration test: passes raw signal to Node 11, then to Node 12."""
    raw_signal = {
        "signal_id": "sig_20260816_boiler_press_01",
        "target_id": "tgt_boiler_repair_blackheath",
        "raw_query": "boiler pressure dropped to zero no hot water how to fix",
        "topic": "boiler_pressure_loss",
        "source_type": "manual_curation",
        "observed_at": "2026-08-16T19:00:00+01:00",
        "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        "metadata": {"urgency_hint": "high"}
    }

    # 1. Execute Node 11
    classification = classify_demand_signal(raw_signal)
    assert isinstance(classification, IntentClassificationResult)
    assert classification.primary_intent == "troubleshooting"

    # 2. Execute Node 12 consuming Node 11 object directly
    opp = score_demand_opportunity(classification)
    assert isinstance(opp, DemandOpportunityRecord)
    assert opp.target_id == raw_signal["target_id"]
    assert opp.signal_id == raw_signal["signal_id"]
    assert opp.classification_id == classification.classification_id
    assert opp.priority_tier == "TIER_1_IMMEDIATE"
    assert opp.demand_opportunity_score >= 80.0


def test_priority_tier_transitions(valid_classification_dict):
    """Verifies priority tier classifications for various urgency and intent levels."""
    # Medium urgency + informational intent -> Moderate Tier
    valid_classification_dict["urgency_level"] = "medium"
    valid_classification_dict["primary_intent"] = "informational"
    record = score_demand_opportunity(valid_classification_dict)
    assert record.priority_tier in ("TIER_2_HIGH", "TIER_3_MODERATE")
    assert 45.0 <= record.demand_opportunity_score < 80.0

    # Low urgency + general curiosity + missing geo -> Low Tier
    valid_classification_dict["urgency_level"] = "low"
    valid_classification_dict["primary_intent"] = "navigational"
    valid_classification_dict["geography"] = {}
    valid_classification_dict["service_context"] = {}
    record_low = score_demand_opportunity(valid_classification_dict)
    assert record_low.priority_tier == "TIER_4_LOW"
    assert record_low.demand_opportunity_score < 45.0


def test_critical_urgent_emergency_is_a_top_viability_opportunity(valid_classification_dict):
    """Node 12 accepts the complete urgency and intent vocabulary emitted by Node 11."""
    valid_classification_dict["urgency_level"] = "critical"
    valid_classification_dict["primary_intent"] = "urgent_emergency"

    record = score_demand_opportunity(valid_classification_dict)

    assert record.priority_tier == "TIER_1_IMMEDIATE"
    assert record.demand_opportunity_score >= 80.0


def test_idempotency_and_determinism(valid_classification_dict):
    """Verifies identical inputs produce identical opportunity_id and scores."""
    record1 = score_demand_opportunity(valid_classification_dict)
    record2 = score_demand_opportunity(valid_classification_dict)

    assert record1.opportunity_id == record2.opportunity_id
    assert record1.demand_opportunity_score == record2.demand_opportunity_score
    assert record1.priority_tier == record2.priority_tier


def test_missing_lineage_fails_closed(valid_classification_dict):
    """Rejects classification inputs missing target_id, signal_id, or classification_id."""
    # Missing target_id
    bad_dict = dict(valid_classification_dict)
    del bad_dict["target_id"]
    with pytest.raises(LineageError):
        score_demand_opportunity(bad_dict)

    # Missing signal_id
    bad_dict = dict(valid_classification_dict)
    del bad_dict["signal_id"]
    with pytest.raises(LineageError):
        score_demand_opportunity(bad_dict)

    # Missing classification_id
    bad_dict = dict(valid_classification_dict)
    del bad_dict["classification_id"]
    with pytest.raises(LineageError):
        score_demand_opportunity(bad_dict)


def test_invalid_urgency_level_fails(valid_classification_dict):
    """Rejects unknown urgency_level."""
    valid_classification_dict["urgency_level"] = "super_critical_unknown"
    with pytest.raises(ValidationError):
        score_demand_opportunity(valid_classification_dict)


def test_invalid_custom_weights_fail(valid_classification_dict):
    """Rejects weights that do not sum to 100.0 or contain negative values."""
    # Sum != 100
    with pytest.raises(ValidationError):
        score_demand_opportunity(valid_classification_dict, weights={"urgency": 50.0, "intent_viability": 30.0, "service_alignment": 20.0, "geographic_alignment": 10.0})

    # Negative weight
    with pytest.raises(ValidationError):
        score_demand_opportunity(valid_classification_dict, weights={"urgency": -10.0, "intent_viability": 60.0, "service_alignment": 30.0, "geographic_alignment": 20.0})


def test_serialization_round_trip(valid_classification_dict):
    """Verifies DemandOpportunityRecord can be serialized to dict and JSON."""
    record = score_demand_opportunity(valid_classification_dict)
    rec_dict = record.to_dict()

    assert rec_dict["opportunity_id"] == record.opportunity_id
    assert rec_dict["demand_opportunity_score"] == record.demand_opportunity_score
    assert isinstance(rec_dict["component_breakdown"], dict)

    # Ensure JSON serializable
    json_str = json.dumps(rec_dict)
    assert len(json_str) > 100
    parsed = json.loads(json_str)
    assert parsed["opportunity_id"] == record.opportunity_id


def test_nodes01_to_05_to_11_to_12_full_pipeline_live_integration():
    """
    Real upstream integration test: executes full registry chain across
    Nodes 01 -> 02 -> 03 -> 04 -> 05 -> 11 -> 12 with live non-mocked data.
    """
    import sys
    import tempfile
    from pathlib import Path

    base_impl = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(base_impl / "node_01"))
    sys.path.insert(0, str(base_impl / "node_02"))
    sys.path.insert(0, str(base_impl / "node_03"))
    sys.path.insert(0, str(base_impl / "node_04"))
    sys.path.insert(0, str(base_impl / "node_05"))
    sys.path.insert(0, str(base_impl / "node_11"))

    from registration import TargetRegistry
    from product_intelligence import ProductIntelligenceRegistry
    from audience_definition import AudienceSegmentRegistry
    from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES
    from search_demand_discovery import DemandSignalRegistry
    from intent_classification import classify_demand_signal

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        t_reg = TargetRegistry(tmp / "targets.json")
        prod_reg = ProductIntelligenceRegistry(tmp / "prods.json", target_registry=t_reg)
        aud_reg = AudienceSegmentRegistry(tmp / "auds.json", target_registry=t_reg, product_registry=prod_reg)
        conv_reg = ConversionDefinitionRegistry(tmp / "convs.json", target_registry=t_reg, product_registry=prod_reg, audience_registry=aud_reg)
        sig_reg = DemandSignalRegistry(tmp / "sigs.json", target_registry=t_reg, product_registry=prod_reg, audience_registry=aud_reg, conversion_registry=conv_reg)

        target = t_reg.register(
            target_type="service_market",
            service="boiler_repair",
            market="domestic_plumbing",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"}
        )

        prod = prod_reg.register(
            target_id=target.target_id,
            problem="Homeowners lose boiler pressure and hot water with no clear diagnosis path.",
            solution="A vetted local boiler-repair callout that diagnoses and restores pressure same-day.",
            features=["Same-day callout"],
            benefits=["Hot water restored quickly"],
            differentiators=["Local coverage"],
            commercial_model="Fixed diagnostic fee.",
            customer_outcome="Working boiler within 24 hours."
        )

        aud = aud_reg.register(
            target_id=target.target_id,
            segment_name="Blackheath homeowner, boiler pressure loss",
            needs=["Restore hot water quickly"],
            pains=["No heating or hot water"],
            urgency="high",
            eligibility_geography={"locality": "Blackheath", "region": "London", "country": "UK"}
        )

        conv = conv_reg.register(
            target_id=target.target_id,
            stages=MASTER_SPEC_STAGES,
            allowed_transitions=[
                ["visit", "engage"], ["engage", "tool_use"], ["tool_use", "enquiry"], ["enquiry", "lead"],
                ["lead", "qualified_lead"], ["qualified_lead", "booking"], ["booking", "sale"], ["sale", "revenue"]
            ],
            success_stage_id="sale",
            success_criteria="A lead reaches the sale stage with a recorded, attributable outcome."
        )

        sig = sig_reg.register(
            signal_id="sig_20260816_boiler_press_01",
            target_id=target.target_id,
            raw_query="boiler pressure dropped to zero no hot water how to fix",
            topic="boiler_pressure_loss",
            source_type="manual_curation",
            observed_at="2026-08-16T19:00:00+01:00",
            geography={"country": "UK", "region": "London", "locality": "Blackheath"},
            service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
            metadata={"urgency_hint": "high"}
        )

        # Ingest Node 05 signal into Node 11 classifier
        cls_res = classify_demand_signal(sig.to_dict())
        assert cls_res.signal_id == sig.signal_id
        assert cls_res.target_id == target.target_id

        # Ingest Node 11 classification into Node 12 opportunity scorer
        opp = score_demand_opportunity(cls_res)
        assert opp.opportunity_id.startswith("opp_")
        assert opp.signal_id == sig.signal_id
        assert opp.target_id == target.target_id
        assert opp.classification_id == cls_res.classification_id
        assert opp.priority_tier == "TIER_1_IMMEDIATE"
        assert opp.demand_opportunity_score >= 80.0
