"""
EP050 Node 19: Quality & Compliance Review - Test & Verification Suite

Validates:
1. Positive compliance verification and package generation conforming to Canonical Contract v1.1.0
2. Full jsonschema validation against canonical approved_asset_package_schema
3. Negative test matrix: missing disclaimer, unverified facts, PII injection, external_action violations
4. Stable, reproducible deterministic check IDs (chk_ + hash)
5. JSON serialization roundtrip
6. 100% offline execution with socket block
7. Full multi-node live pipeline integration across Nodes 01 through 19

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial complete test suite for Node 19 Quality & Compliance Review.
"""

import os
import sys
import json
import socket
import tempfile
from pathlib import Path
import pytest
import jsonschema

from quality_compliance import (
    evaluate_asset_compliance,
    ComplianceCheckResult,
    ApprovedAssetPackage,
    VALIDATOR_VERSION
)

# Upstream module imports for integration test
BASE_IMPL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_IMPL / "node_01"))
sys.path.insert(0, str(BASE_IMPL / "node_02"))
sys.path.insert(0, str(BASE_IMPL / "node_03"))
sys.path.insert(0, str(BASE_IMPL / "node_04"))
sys.path.insert(0, str(BASE_IMPL / "node_05"))
sys.path.insert(0, str(BASE_IMPL / "node_11"))
sys.path.insert(0, str(BASE_IMPL / "node_12"))
sys.path.insert(0, str(BASE_IMPL / "node_13"))
sys.path.insert(0, str(BASE_IMPL / "node_14"))
sys.path.insert(0, str(BASE_IMPL / "node_16"))
sys.path.insert(0, str(BASE_IMPL / "node_17"))

from registration import TargetRegistry
from product_intelligence import ProductIntelligenceRegistry
from audience_definition import AudienceSegmentRegistry
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES
from search_demand_discovery import DemandSignalRegistry
from intent_classification import classify_demand_signal
from opportunity_scoring import score_demand_opportunity
from demand_path_discovery import discover_demand_path
from channel_placement_selection import select_channel_placements
from canonical_knowledge_store import CanonicalKnowledgeStore
from content_utility_factory import generate_asset_payload

BASE_EPIC = Path(__file__).resolve().parents[2]
CONTRACT_SCHEMA_PATH = BASE_EPIC / "integration" / "canonical_contracts" / "20260817_node19_to_node20_canonical_contract_v1_1.json"


@pytest.fixture(autouse=True)
def assert_no_network(monkeypatch):
    """Enforces 100% offline execution by blocking socket creation."""
    def _blocked_socket(*args, **kwargs):
        raise RuntimeError("Network socket creation is prohibited during EP050 tests.")
    monkeypatch.setattr(socket, "socket", _blocked_socket)


@pytest.fixture
def canonical_subschema():
    with open(CONTRACT_SCHEMA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["approved_asset_package_schema"]


@pytest.fixture
def valid_asset_dict():
    return {
        "asset_id": "asset_boiler_001",
        "target_id": "target_service_market_boiler_repair_london_blackheath",
        "signal_id": "sig_20260816_boiler_press_01",
        "classification_id": "cls_sig_20260816_boiler_press_01_cb340deaf8fe",
        "opportunity_id": "opp_test_boiler_01",
        "path_id": "path_test_boiler_01",
        "selection_id": "sel_test_boiler_01",
        "title": "Emergency Boiler Repair Blackheath | Fast Local Service",
        "body_content": "Local Emergency Heating Support.\n- Standard pressure is 1.0 to 1.5 bar.\nFixed fee callouts.",
        "safety_disclaimer": "SAFETY MANDATE: Gas Safe Register compliance is legally required for all combustion chamber inspections.",
        "call_to_action": "Call vetted local engineer now for same-day diagnostic inspection.",
        "fact_ids": ["fact_boiler_press_01"],
        "metadata": {
            "channel": "search_landing",
            "placement_type": "diagnostic_landing_page",
            "format": "troubleshooting_guide",
            "intent_category": "troubleshooting",
            "template_id": "tpl_search_guide",
            "template_version": "1.0.0",
            "external_action": False
        },
        "created_at": "2026-08-16T20:55:00Z"
    }


def test_positive_evaluation_and_schema_conformance(valid_asset_dict, canonical_subschema):
    """Verifies that a compliant asset is approved and passes Canonical Contract v1.1.0 schema."""
    chk, pkg = evaluate_asset_compliance(valid_asset_dict)

    assert chk.approved is True
    assert chk.disclaimer_verified is True
    assert chk.facts_verified is True
    assert len(chk.reasons) == 0
    assert pkg is not None
    assert pkg.schema_version == "1.1.0"
    assert pkg.asset_id == valid_asset_dict["asset_id"]

    # Strict jsonschema Draft 2020-12 validation against canonical schema
    jsonschema.validate(instance=pkg.to_dict(), schema=canonical_subschema)


def test_missing_disclaimer_rejected(valid_asset_dict):
    """Verifies that missing or unverified disclaimer fails approval."""
    corrupt = valid_asset_dict.copy()
    corrupt["safety_disclaimer"] = "Check the boiler pressure."
    chk, pkg = evaluate_asset_compliance(corrupt)

    assert chk.approved is False
    assert pkg is None
    assert any("Safety disclaimer" in r for r in chk.reasons)


def test_unverified_fact_in_knowledge_store_rejected(valid_asset_dict):
    """Verifies that facts missing from CanonicalKnowledgeStore fail approval."""
    store = CanonicalKnowledgeStore()
    # Store is empty, fact_boiler_press_01 does not exist
    chk, pkg = evaluate_asset_compliance(valid_asset_dict, knowledge_store=store)

    assert chk.approved is False
    assert chk.facts_verified is False
    assert pkg is None
    assert any("not found in CanonicalKnowledgeStore" in r for r in chk.reasons)


def test_prohibited_pii_rejected(valid_asset_dict):
    """Verifies that email or phone in content triggers rejection."""
    corrupt = valid_asset_dict.copy()
    corrupt["body_content"] = "Contact us at support@gasboilerfix.co.uk for help."
    chk, pkg = evaluate_asset_compliance(corrupt)

    assert chk.approved is False
    assert pkg is None
    assert any("PII detected" in r for r in chk.reasons)


def test_external_action_violation_rejected(valid_asset_dict):
    """Verifies that external_action=True triggers immediate rejection."""
    corrupt = valid_asset_dict.copy()
    corrupt["metadata"] = corrupt["metadata"].copy()
    corrupt["metadata"]["external_action"] = True
    chk, pkg = evaluate_asset_compliance(corrupt)

    assert chk.approved is False
    assert pkg is None
    assert any("offline safety boundary" in r for r in chk.reasons)


def test_determinism_and_serialization(valid_asset_dict):
    """Verifies deterministic check ID calculation and JSON serialization."""
    chk1, pkg1 = evaluate_asset_compliance(valid_asset_dict)
    chk2, pkg2 = evaluate_asset_compliance(valid_asset_dict)

    assert chk1.check_id == chk2.check_id
    assert json.loads(chk1.to_json())["check_id"] == chk1.check_id
    assert json.loads(pkg1.to_json())["asset_id"] == pkg1.asset_id


def test_nodes01_to_19_full_pipeline_live_integration(canonical_subschema):
    """
    Real unmocked multi-node integration test: executes full registry chain across
    Nodes 01 -> 02 -> 03 -> 04 -> 05 -> 11 -> 12 -> 13 -> 14 -> 16 -> 17 -> 19 with non-mocked data.
    """
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        t_reg = TargetRegistry(tmp / "targets.json")
        prod_reg = ProductIntelligenceRegistry(tmp / "prods.json", target_registry=t_reg)
        aud_reg = AudienceSegmentRegistry(tmp / "auds.json", target_registry=t_reg, product_registry=prod_reg)
        conv_reg = ConversionDefinitionRegistry(tmp / "convs.json", target_registry=t_reg, product_registry=prod_reg, audience_registry=aud_reg)
        sig_reg = DemandSignalRegistry(tmp / "sigs.json", target_registry=t_reg, product_registry=prod_reg, audience_registry=aud_reg, conversion_registry=conv_reg)
        k_store = CanonicalKnowledgeStore(tmp / "facts.json", target_registry=t_reg, product_registry=prod_reg)

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
            features=["Same-day callout", "Fixed diagnostic fee"],
            benefits=["Hot water restored quickly"],
            differentiators=["Local Blackheath coverage"],
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

        cls_res = classify_demand_signal(sig.to_dict())
        opp = score_demand_opportunity(cls_res)
        path_rec = discover_demand_path(opp)
        sel = select_channel_placements(path_rec)

        fact1 = k_store.register_fact(
            target_id=target.target_id,
            topic="boiler_pressure_nominal",
            claim="Standard combi boilers operate at 1.0 to 1.5 bar cold pressure.",
            verification_source="Worcester Bosch User Guide 2025",
            is_safety_critical=True,
            safety_guidance="SAFETY: Gas Safe Register compliance mandatory for internal repairs."
        )

        asset = generate_asset_payload(
            selection_input=sel,
            facts=[fact1],
            intent_input=cls_res
        )

        # Evaluate compliance with live knowledge store
        chk, pkg = evaluate_asset_compliance(asset, knowledge_store=k_store)

        assert chk.approved is True
        assert chk.disclaimer_verified is True
        assert chk.facts_verified is True
        assert pkg is not None

        # Validate with canonical contract schema
        jsonschema.validate(instance=pkg.to_dict(), schema=canonical_subschema)
