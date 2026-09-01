"""
EP050 Node 13: Demand Path Discovery - Test & Verification Suite

Validates:
1. Positive demand path generation from Node 12 DemandOpportunityRecord
2. Stable, reproducible deterministic path IDs (path_ + hash)
3. Stage sequence integrity and commercial intent emergence detection
4. Full lineage preservation across target_id, signal_id, classification_id, opportunity_id, path_id
5. Custom stages definition and validation
6. Fail-closed error handling for missing lineage and malformed stages
7. JSON serialization roundtrip
8. 100% offline execution with socket block
9. Real upstream pipeline integration test from Node 01 through Node 13

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial complete test suite for Node 13 Demand Path Discovery.
"""

import os
import sys
import json
import socket
import tempfile
from pathlib import Path
import pytest

from demand_path_discovery import (
    discover_demand_path,
    DemandPathRecord,
    DemandPathStage,
    ValidationError,
    LineageError
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

from registration import TargetRegistry
from product_intelligence import ProductIntelligenceRegistry
from audience_definition import AudienceSegmentRegistry
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES
from search_demand_discovery import DemandSignalRegistry
from intent_classification import classify_demand_signal
from opportunity_scoring import score_demand_opportunity


@pytest.fixture(autouse=True)
def assert_no_network(monkeypatch):
    """Enforces 100% offline execution by blocking socket creation."""
    def _blocked_socket(*args, **kwargs):
        raise RuntimeError("Network socket creation is prohibited during EP050 tests.")
    monkeypatch.setattr(socket, "socket", _blocked_socket)


@pytest.fixture
def valid_opportunity_dict():
    return {
        "opportunity_id": "opp_test_boiler_01",
        "target_id": "target_service_market_boiler_repair_london_blackheath",
        "signal_id": "sig_20260816_boiler_press_01",
        "classification_id": "cls_sig_20260816_boiler_press_01_cb340deaf8fe",
        "demand_opportunity_score": 100.0,
        "priority_tier": "TIER_1_IMMEDIATE",
        "primary_intent": "troubleshooting"
    }


def test_positive_demand_path_generation(valid_opportunity_dict):
    """Verifies that a valid opportunity record generates a compliant DemandPathRecord."""
    path_rec = discover_demand_path(valid_opportunity_dict)

    assert isinstance(path_rec, DemandPathRecord)
    assert path_rec.path_id.startswith("path_")
    assert path_rec.target_id == valid_opportunity_dict["target_id"]
    assert path_rec.signal_id == valid_opportunity_dict["signal_id"]
    assert path_rec.classification_id == valid_opportunity_dict["classification_id"]
    assert path_rec.opportunity_id == valid_opportunity_dict["opportunity_id"]
    assert len(path_rec.stages) == 4
    assert path_rec.commercial_intent_emergence_stage == 2
    assert "troubleshooting" in path_rec.path_name


def test_idempotency_and_determinism(valid_opportunity_dict):
    """Verifies that identical inputs yield identical path IDs."""
    path_1 = discover_demand_path(valid_opportunity_dict)
    path_2 = discover_demand_path(valid_opportunity_dict)

    assert path_1.path_id == path_2.path_id
    assert path_1.commercial_intent_emergence_stage == path_2.commercial_intent_emergence_stage
    assert len(path_1.stages) == len(path_2.stages)


def test_custom_stages_and_emergence():
    """Verifies custom stage creation, order validation, and emergence detection."""
    opp = {
        "opportunity_id": "opp_custom_01",
        "target_id": "target_01",
        "signal_id": "sig_01",
        "classification_id": "cls_01",
        "primary_intent": "quote_request"
    }
    custom_stages = [
        DemandPathStage(
            stage_index=1,
            stage_name="Ad Impression",
            channel="paid_search",
            information_sought="Boiler repair discount voucher",
            influenceable_touchpoint="Special offer banner",
            intent_level="informational"
        ),
        DemandPathStage(
            stage_index=2,
            stage_name="Quote Submission",
            channel="quote_engine",
            information_sought="Fixed price estimate",
            influenceable_touchpoint="Instant quote generator",
            intent_level="commercial_request"
        )
    ]
    path_rec = discover_demand_path(opp, custom_stages=custom_stages)
    assert len(path_rec.stages) == 2
    assert path_rec.commercial_intent_emergence_stage == 2


def test_missing_lineage_fails_closed(valid_opportunity_dict):
    """Verifies that missing any upstream lineage identifier raises LineageError."""
    for field_name in ("target_id", "signal_id", "classification_id", "opportunity_id"):
        corrupt = valid_opportunity_dict.copy()
        corrupt[field_name] = ""
        with pytest.raises(LineageError):
            discover_demand_path(corrupt)


def test_disordered_stages_fails_closed(valid_opportunity_dict):
    """Verifies that invalid or non-sequential stage indices fail closed."""
    # Gap in sequence (1, 3)
    bad_stages = [
        {"stage_index": 1, "stage_name": "S1", "channel": "C1", "information_sought": "I1", "influenceable_touchpoint": "T1", "intent_level": "informational"},
        {"stage_index": 3, "stage_name": "S3", "channel": "C3", "information_sought": "I3", "influenceable_touchpoint": "T3", "intent_level": "conversion"}
    ]
    with pytest.raises(ValidationError):
        discover_demand_path(valid_opportunity_dict, custom_stages=bad_stages)


def test_serialization_roundtrip(valid_opportunity_dict):
    """Verifies dictionary and JSON serialization roundtrips cleanly."""
    path_rec = discover_demand_path(valid_opportunity_dict)
    rec_dict = path_rec.to_dict()
    assert rec_dict["path_id"] == path_rec.path_id
    assert len(rec_dict["stages"]) == 4

    json_str = path_rec.to_json()
    parsed = json.loads(json_str)
    assert parsed["path_id"] == path_rec.path_id
    assert parsed["commercial_intent_emergence_stage"] == path_rec.commercial_intent_emergence_stage


def test_nodes01_to_05_to_11_to_12_to_13_full_pipeline_live_integration():
    """
    Real unmocked upstream pipeline integration test: executes full registry chain
    across Nodes 01 -> 02 -> 03 -> 04 -> 05 -> 11 -> 12 -> 13 with non-mocked data.
    """
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

        # 1. Ingest Node 05 signal into Node 11 classifier
        cls_res = classify_demand_signal(sig.to_dict())

        # 2. Ingest Node 11 classification into Node 12 opportunity scorer
        opp = score_demand_opportunity(cls_res)

        # 3. Ingest Node 12 opportunity into Node 13 demand path discoverer
        path_rec = discover_demand_path(opp)

        assert path_rec.path_id.startswith("path_")
        assert path_rec.target_id == target.target_id
        assert path_rec.signal_id == sig.signal_id
        assert path_rec.classification_id == cls_res.classification_id
        assert path_rec.opportunity_id == opp.opportunity_id
        assert len(path_rec.stages) == 4
        assert path_rec.commercial_intent_emergence_stage == 2
        assert path_rec.stages[0].channel == "organic_search"
        assert path_rec.stages[-1].intent_level == "conversion"
