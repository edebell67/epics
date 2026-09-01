"""
EP050 Node 11 — Intent Classification Test Suite

Unit, schema contract, determinism, fail-closed negative, lineage preservation,
and offline no-network tests for Node 11 Intent Classification.

VERSION HISTORY
- v1.1.0 · 2026-08-17 · Adds automated source types to test schema validation and verifies automated signal classification.
- v1.0.0 · 2026-08-16 · Initial complete test suite for Node 11.
"""

import json
import socket
from copy import deepcopy
import pytest
from jsonschema import validate, ValidationError as JsonSchemaValidationError

from intent_classification import (
    IntentCategory,
    UrgencyLevel,
    ValidationError,
    ContractViolationError,
    classify_demand_signal,
)


# Stage 2 -> Stage 3 Contract Schema v1.1.0 (with automated source types)
STAGE2_STAGE3_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "DemandSignalPayload",
    "type": "object",
    "required": [
        "signal_id",
        "target_id",
        "raw_query",
        "topic",
        "source_type",
        "observed_at",
        "geography",
        "service_context"
    ],
    "properties": {
        "signal_id": {"type": "string"},
        "target_id": {"type": "string"},
        "raw_query": {"type": "string"},
        "topic": {"type": "string"},
        "source_type": {
            "type": "string",
            "enum": [
                "manual_curation",
                "synthetic_fixture",
                "search_query",
                "gmb_insights",
                "crm_activity",
                "autosuggest_feed",
                "live_api",
            ]
        },
        "observed_at": {"type": "string"},
        "geography": {
            "type": "object",
            "required": ["locality", "region", "country"],
            "properties": {
                "locality": {"type": "string"},
                "region": {"type": "string"},
                "country": {"type": "string"}
            }
        },
        "service_context": {
            "type": "object",
            "required": ["service_name", "market_segment"],
            "properties": {
                "service_name": {"type": "string"},
                "market_segment": {"type": "string"}
            }
        },
        "metadata": {"type": "object"}
    }
}

# Synthetic Boiler Repair MVP Fixture
SEED_FIXTURE = {
    "signal_id": "sig_20260816_boiler_press_01",
    "target_id": "tgt_boiler_repair_blackheath",
    "raw_query": "boiler pressure dropped to zero no hot water how to fix",
    "topic": "boiler_pressure_loss",
    "source_type": "manual_curation",
    "observed_at": "2026-08-16T19:00:00+01:00",
    "geography": {
        "locality": "Blackheath",
        "region": "London",
        "country": "UK"
    },
    "service_context": {
        "service_name": "boiler_repair",
        "market_segment": "domestic_plumbing"
    },
    "metadata": {
        "urgency_hint": "high",
        "curated_by": "claude_node05_mvp"
    }
}


def test_positive_classification_seed_fixture():
    """Validates classification of the synthetic seed boiler repair fixture."""
    res = classify_demand_signal(SEED_FIXTURE, execution_time="2026-08-16T23:00:00+00:00")
    assert res.signal_id == "sig_20260816_boiler_press_01"
    assert res.target_id == "tgt_boiler_repair_blackheath"
    assert res.primary_intent == IntentCategory.TROUBLESHOOTING
    assert IntentCategory.URGENT_EMERGENCY in res.secondary_intents
    assert res.urgency_level == UrgencyLevel.HIGH
    assert res.troubleshooting_score >= 0.5
    assert res.geography["locality"] == "Blackheath"
    assert res.service_context["service_name"] == "boiler_repair"
    assert res.source_type == "manual_curation"
    assert res.classification_id.startswith("cls_sig_20260816_boiler_press_01_")


def test_live_emergency_electrician_local_search_is_commercial_and_critical():
    """Regression: the real Catford campaign must not be rejected as informational."""
    payload = deepcopy(SEED_FIXTURE)
    payload.update({
        "signal_id": "sig_live_emergency_electrician_catford",
        "target_id": "tgt_emergency_electrician_catford",
        "raw_query": "emergency electrician catford UK",
        "topic": "emergency_electrician",
        "source_type": "search_query",
        "geography": {"locality": "catford", "region": "London", "country": "UK"},
        "service_context": {
            "service_name": "emergency_electrician",
            "market_segment": "domestic_electrical_services",
        },
        "metadata": {},
    })

    res = classify_demand_signal(payload, execution_time="2026-08-21T17:00:00+01:00")

    assert res.primary_intent == IntentCategory.URGENT_EMERGENCY
    assert res.urgency_level == UrgencyLevel.CRITICAL
    assert res.commercial_intent_score >= 0.6
    assert "matched_local_service_search:service+locality" in res.rule_trace


def test_general_service_explanation_without_locality_remains_informational():
    """The local-service rule must not turn educational interest into buying intent."""
    payload = deepcopy(SEED_FIXTURE)
    payload.update({
        "signal_id": "sig_electrician_explainer",
        "raw_query": "what does an electrician do",
        "topic": "electrician_explainer",
        "source_type": "search_query",
        "geography": {"locality": "catford", "region": "London", "country": "UK"},
        "service_context": {
            "service_name": "electrician_service",
            "market_segment": "domestic_electrical_services",
        },
        "metadata": {},
    })

    res = classify_demand_signal(payload, execution_time="2026-08-21T17:00:00+01:00")

    assert res.primary_intent == IntentCategory.INFORMATIONAL
    assert res.commercial_intent_score == 0.0


def test_contract_schema_conformance():
    """Validates that the test fixture strictly conforms to the JSON Schema contract."""
    # Should not raise
    validate(instance=SEED_FIXTURE, schema=STAGE2_STAGE3_SCHEMA)


def test_deterministic_reproducibility():
    """Validates that running classification multiple times produces bitwise-identical output."""
    res1 = classify_demand_signal(SEED_FIXTURE, execution_time="2026-08-16T23:00:00+00:00")
    res2 = classify_demand_signal(SEED_FIXTURE, execution_time="2026-08-16T23:00:00+00:00")
    assert res1.to_dict() == res2.to_dict()
    assert res1.classification_id == res2.classification_id
    assert res1.commercial_intent_score == res2.commercial_intent_score
    assert res1.troubleshooting_score == res2.troubleshooting_score


@pytest.mark.parametrize("missing_key", [
    "signal_id", "target_id", "raw_query", "topic",
    "source_type", "observed_at", "geography", "service_context"
])
def test_missing_required_fields_rejected_fail_closed(missing_key):
    """Validates that omitting any required field fails closed with ValidationError."""
    payload = deepcopy(SEED_FIXTURE)
    del payload[missing_key]
    with pytest.raises(ValidationError, match=f"Missing required field: '{missing_key}'"):
        classify_demand_signal(payload)


@pytest.mark.parametrize("missing_geo_key", ["locality", "region", "country"])
def test_missing_geography_subfield_rejected(missing_geo_key):
    """Validates that omitting geography sub-fields fails closed."""
    payload = deepcopy(SEED_FIXTURE)
    del payload["geography"][missing_geo_key]
    with pytest.raises(ValidationError, match=f"geography.{missing_geo_key} must be a non-empty string"):
        classify_demand_signal(payload)


@pytest.mark.parametrize("missing_svc_key", ["service_name", "market_segment"])
def test_missing_service_context_subfield_rejected(missing_svc_key):
    """Validates that omitting service_context sub-fields fails closed."""
    payload = deepcopy(SEED_FIXTURE)
    del payload["service_context"][missing_svc_key]
    with pytest.raises(ValidationError, match=f"service_context.{missing_svc_key} must be a non-empty string"):
        classify_demand_signal(payload)


def test_invalid_source_type_enum_rejected():
    """Validates that unrecognized source_type is rejected by contract gate."""
    payload = deepcopy(SEED_FIXTURE)
    payload["source_type"] = "unapproved_third_party"
    with pytest.raises(ContractViolationError, match="Invalid source_type 'unapproved_third_party'"):
        classify_demand_signal(payload)


def test_automated_source_types_accepted():
    """Validates that all automated live source types are classified successfully."""
    for source in ("search_query", "gmb_insights", "crm_activity", "autosuggest_feed", "live_api"):
        payload = deepcopy(SEED_FIXTURE)
        payload["source_type"] = source
        res = classify_demand_signal(payload)
        assert res.source_type == source
        assert res.classification_id.startswith("cls_")


def test_invalid_date_format_rejected():
    """Validates that non-ISO date formats are rejected fail-closed."""
    payload = deepcopy(SEED_FIXTURE)
    payload["observed_at"] = "invalid-date-string"
    with pytest.raises(ValidationError, match="Invalid ISO 8601 date format"):
        classify_demand_signal(payload)


def test_non_dict_payload_rejected():
    """Validates that passing non-dict payloads raises ValidationError."""
    with pytest.raises(ValidationError, match="Payload must be a dict"):
        classify_demand_signal(["not", "a", "dict"])  # type: ignore


def test_lineage_preservation():
    """Validates that origin IDs and contextual lineage are preserved un-mutated."""
    res = classify_demand_signal(SEED_FIXTURE)
    assert res.signal_id == SEED_FIXTURE["signal_id"]
    assert res.target_id == SEED_FIXTURE["target_id"]
    assert res.geography == SEED_FIXTURE["geography"]
    assert res.service_context == SEED_FIXTURE["service_context"]
    assert res.source_type == SEED_FIXTURE["source_type"]


def test_json_serialization_roundtrip():
    """Validates serialization to JSON string and dictionary."""
    res = classify_demand_signal(SEED_FIXTURE)
    json_str = res.to_json()
    parsed = json.loads(json_str)
    assert parsed["classification_id"] == res.classification_id
    assert parsed["primary_intent"] == "troubleshooting"
    assert "matched_troubleshooting_keywords" in str(parsed["rule_trace"])


def test_offline_no_network_assertion(monkeypatch):
    """Validates that the entire classification process makes zero socket or network calls."""
    def guarded_socket(*args, **kwargs):
        raise RuntimeError("Network access attempted during offline classification test!")

    monkeypatch.setattr(socket, "socket", guarded_socket)
    # Must complete cleanly without invoking socket
    res = classify_demand_signal(SEED_FIXTURE)
    assert res.primary_intent == IntentCategory.TROUBLESHOOTING


def test_nodes01_to_05_upstream_live_integration():
    """
    Real upstream integration test: executes full registry chain across Nodes 01, 02, 03, 04, and 05,
    then feeds the resulting live DemandSignalRecord directly into Node 11.
    """
    import sys
    import tempfile
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_02"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_03"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_04"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_05"))

    from registration import TargetRegistry
    from product_intelligence import ProductIntelligenceRegistry
    from audience_definition import AudienceSegmentRegistry
    from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES
    from search_demand_discovery import DemandSignalRegistry

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

        # Directly classify the Node 05 output record
        res = classify_demand_signal(sig.to_dict())
        assert res.classification_id.startswith("cls_sig_20260816_boiler_press_01_")
        assert res.primary_intent == IntentCategory.TROUBLESHOOTING
        assert res.urgency_level == UrgencyLevel.HIGH
        assert res.target_id == target.target_id
        assert res.signal_id == sig.signal_id

