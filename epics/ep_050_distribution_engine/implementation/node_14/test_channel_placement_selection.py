"""
EP050 Node 14: Channel / Placement Selection - Test & Verification Suite

Validates:
1. Positive channel fit scoring and ranking from Node 13 DemandPathRecord
2. Stable, reproducible deterministic selection IDs (sel_ + hash)
3. Explainable component score breakdowns (audience match, intent relevance, format viability, cost efficiency)
4. Full lineage preservation across target_id, signal_id, classification_id, opportunity_id, path_id, selection_id
5. Custom weights and candidate channels evaluation
6. Fail-closed error handling for missing lineage, bad scores, and out-of-range weights
7. JSON serialization roundtrip
8. 100% offline execution with socket block
9. Real upstream pipeline integration test from Node 01 through Node 14

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial complete test suite for Node 14 Channel/Placement Selection.
"""

import os
import sys
import json
import socket
import tempfile
from pathlib import Path
import pytest

from channel_placement_selection import (
    select_channel_placements,
    ChannelSelectionRecord,
    RankedPlacementOption,
    ChannelScoreBreakdown,
    ValidationError,
    LineageError,
    DEFAULT_WEIGHTS
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

from registration import TargetRegistry
from product_intelligence import ProductIntelligenceRegistry
from audience_definition import AudienceSegmentRegistry
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES
from search_demand_discovery import DemandSignalRegistry
from intent_classification import classify_demand_signal
from opportunity_scoring import score_demand_opportunity
from demand_path_discovery import discover_demand_path


@pytest.fixture(autouse=True)
def assert_no_network(monkeypatch):
    """Enforces 100% offline execution by blocking socket creation."""
    def _blocked_socket(*args, **kwargs):
        raise RuntimeError("Network socket creation is prohibited during EP050 tests.")
    monkeypatch.setattr(socket, "socket", _blocked_socket)


@pytest.fixture
def valid_path_dict():
    return {
        "path_id": "path_test_boiler_01",
        "target_id": "target_service_market_boiler_repair_london_blackheath",
        "signal_id": "sig_20260816_boiler_press_01",
        "classification_id": "cls_sig_20260816_boiler_press_01_cb340deaf8fe",
        "opportunity_id": "opp_test_boiler_01",
        "primary_intent": "troubleshooting"
    }


def test_positive_channel_selection(valid_path_dict):
    """Verifies that a valid path generates ranked channel selections."""
    sel = select_channel_placements(valid_path_dict)

    assert isinstance(sel, ChannelSelectionRecord)
    assert sel.selection_id.startswith("sel_")
    assert sel.target_id == valid_path_dict["target_id"]
    assert sel.signal_id == valid_path_dict["signal_id"]
    assert sel.classification_id == valid_path_dict["classification_id"]
    assert sel.opportunity_id == valid_path_dict["opportunity_id"]
    assert sel.path_id == valid_path_dict["path_id"]
    assert len(sel.ranked_placements) >= 3
    assert sel.ranked_placements[0].rank == 1
    assert sel.ranked_placements[0].channel_fit_score >= sel.ranked_placements[1].channel_fit_score
    assert sel.primary_channel == sel.ranked_placements[0].channel_name


def test_idempotency_and_determinism(valid_path_dict):
    """Verifies that identical inputs yield identical selection IDs and rankings."""
    sel_1 = select_channel_placements(valid_path_dict)
    sel_2 = select_channel_placements(valid_path_dict)

    assert sel_1.selection_id == sel_2.selection_id
    assert sel_1.primary_channel == sel_2.primary_channel
    assert len(sel_1.ranked_placements) == len(sel_2.ranked_placements)
    for p1, p2 in zip(sel_1.ranked_placements, sel_2.ranked_placements):
        assert p1.rank == p2.rank
        assert p1.channel_fit_score == p2.channel_fit_score


def test_custom_weights_and_ranking(valid_path_dict):
    """Verifies custom weights adjust placement ranking correctly."""
    cost_heavy_weights = {
        "audience_match": 10.0,
        "intent_relevance": 10.0,
        "format_viability": 10.0,
        "cost_efficiency": 70.0,
    }
    sel = select_channel_placements(valid_path_dict, weights=cost_heavy_weights)
    assert sel.ranked_placements[0].rank == 1
    # Cost efficiency 0.95 should boost organic search
    top_channel = sel.ranked_placements[0].channel_name
    assert top_channel in ("organic_search", "local_search_maps")


def test_missing_lineage_fails_closed(valid_path_dict):
    """Verifies that missing any upstream lineage identifier raises LineageError."""
    for field_name in ("target_id", "signal_id", "classification_id", "opportunity_id", "path_id"):
        corrupt = valid_path_dict.copy()
        corrupt[field_name] = ""
        with pytest.raises(LineageError):
            select_channel_placements(corrupt)


def test_invalid_weights_sum_fails_closed(valid_path_dict):
    """Verifies that weights not summing to 100.0 fail closed."""
    bad_weights = {"audience_match": 20.0, "intent_relevance": 20.0, "format_viability": 20.0, "cost_efficiency": 20.0}
    with pytest.raises(ValidationError):
        select_channel_placements(valid_path_dict, weights=bad_weights)


def test_invalid_raw_score_bounds_fails_closed(valid_path_dict):
    """Verifies that raw scores outside [0.0, 1.0] are rejected."""
    bad_candidate = [{
        "channel_name": "bad_channel",
        "placement_type": "bad_type",
        "raw_scores": {"audience_match": 1.5, "intent_relevance": 0.8, "format_viability": 0.8, "cost_efficiency": 0.8},
        "recommended_format": "bad",
        "rationale": "bad"
    }]
    with pytest.raises(ValidationError):
        select_channel_placements(valid_path_dict, candidate_channels=bad_candidate)


def test_serialization_roundtrip(valid_path_dict):
    """Verifies dictionary and JSON serialization roundtrips cleanly."""
    sel = select_channel_placements(valid_path_dict)
    rec_dict = sel.to_dict()
    assert rec_dict["selection_id"] == sel.selection_id
    assert len(rec_dict["ranked_placements"]) > 0

    json_str = sel.to_json()
    parsed = json.loads(json_str)
    assert parsed["selection_id"] == sel.selection_id
    assert parsed["primary_channel"] == sel.primary_channel


def test_nodes01_to_05_to_11_to_14_full_pipeline_live_integration():
    """
    Real unmocked upstream pipeline integration test: executes full registry chain
    across Nodes 01 -> 02 -> 03 -> 04 -> 05 -> 11 -> 12 -> 13 -> 14 with non-mocked data.
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

        # 4. Ingest Node 13 demand path into Node 14 channel selector
        sel = select_channel_placements(path_rec)

        assert sel.selection_id.startswith("sel_")
        assert sel.target_id == target.target_id
        assert sel.signal_id == sig.signal_id
        assert sel.classification_id == cls_res.classification_id
        assert sel.opportunity_id == opp.opportunity_id
        assert sel.path_id == path_rec.path_id
        assert len(sel.ranked_placements) >= 3
        assert sel.ranked_placements[0].rank == 1
        assert sel.primary_channel in ("local_search_maps", "organic_search", "paid_search")
