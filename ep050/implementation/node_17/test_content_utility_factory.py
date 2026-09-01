"""
EP050 Node 17: Content & Utility Factory - Test & Verification Suite

Validates:
1. Positive asset generation combining Node 16 facts, Node 11 intent, Node 14 channels, and Node 04 conversion CTAs
2. Stable, reproducible deterministic asset IDs (asset_ + hash)
3. Mandatory safety disclaimers embedded in all rendered assets
4. Guaranteed external_action=False metadata field
5. Strict factual lineage enforcement (requires valid CanonicalFactRecord list)
6. Upstream targeting lineage preservation across 7 tiers
7. Prohibited PII screening (emails and phone numbers)
8. JSON serialization roundtrip
9. 100% offline execution with socket block
10. Real upstream pipeline integration test from Node 01 through Node 17

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial complete test suite for Node 17 Content & Utility Factory.
"""

import os
import sys
import json
import socket
import tempfile
from pathlib import Path
import pytest

from content_utility_factory import (
    generate_asset_payload,
    AssetPayload,
    AssetMetadata,
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
sys.path.insert(0, str(BASE_IMPL / "node_13"))
sys.path.insert(0, str(BASE_IMPL / "node_14"))
sys.path.insert(0, str(BASE_IMPL / "node_16"))

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


@pytest.fixture(autouse=True)
def assert_no_network(monkeypatch):
    """Enforces 100% offline execution by blocking socket creation."""
    def _blocked_socket(*args, **kwargs):
        raise RuntimeError("Network socket creation is prohibited during EP050 tests.")
    monkeypatch.setattr(socket, "socket", _blocked_socket)


@pytest.fixture
def valid_selection_dict():
    return {
        "selection_id": "sel_test_boiler_01",
        "target_id": "target_service_market_boiler_repair_london_blackheath",
        "signal_id": "sig_20260816_boiler_press_01",
        "classification_id": "cls_sig_20260816_boiler_press_01_cb340deaf8fe",
        "opportunity_id": "opp_test_boiler_01",
        "path_id": "path_test_boiler_01",
        "primary_channel": "local_search_maps",
        "ranked_placements": [
            {
                "rank": 1,
                "channel_name": "local_search_maps",
                "placement_type": "google_maps_local_pack",
                "channel_fit_score": 93.0,
                "recommended_format": "verified_local_listing",
                "rationale": "High geographic concentration in Blackheath."
            }
        ]
    }


@pytest.fixture
def valid_facts_list():
    return [
        {
            "fact_id": "fact_boiler_press_01",
            "topic": "boiler_pressure_normal_range",
            "claim": "Standard domestic combi boiler pressure should remain between 1.0 and 1.5 bar when cold.",
            "is_safety_critical": True,
            "safety_guidance": "Homeowners must not attempt to dismantle internal combustion chambers."
        }
    ]


@pytest.fixture
def valid_classification():
    """A real Node 11 classification, which is what every production caller passes.

    It carries the geography and service_context that Node 17 derives its copy from. Node 17 used
    to hardcode "Blackheath"/"SE3"/"boiler", so these tests could omit it; now that the copy is
    derived, omitting it is a fail-closed error rather than a silent wrong-town asset.
    """
    return {
        "primary_intent": "troubleshooting",
        "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
    }


def test_positive_asset_generation(valid_selection_dict, valid_facts_list, valid_classification):
    """Verifies that valid selection and facts generate a compliant AssetPayload."""
    asset = generate_asset_payload(valid_selection_dict, valid_facts_list, intent_input=valid_classification)

    assert isinstance(asset, AssetPayload)
    assert asset.asset_id.startswith("asset_")
    assert asset.target_id == valid_selection_dict["target_id"]
    assert asset.selection_id == valid_selection_dict["selection_id"]
    assert len(asset.fact_ids) == 1
    assert "fact_boiler_press_01" in asset.fact_ids
    assert "SAFETY" in asset.safety_disclaimer
    assert "Homeowners must not attempt" in asset.safety_disclaimer
    assert asset.metadata.external_action is False


def test_determinism_and_idempotency(valid_selection_dict, valid_facts_list, valid_classification):
    """Verifies identical inputs produce identical asset IDs and contents."""
    a1 = generate_asset_payload(valid_selection_dict, valid_facts_list, intent_input=valid_classification)
    a2 = generate_asset_payload(valid_selection_dict, valid_facts_list, intent_input=valid_classification)

    assert a1.asset_id == a2.asset_id
    assert a1.title == a2.title
    assert a1.body_content == a2.body_content
    assert a1.safety_disclaimer == a2.safety_disclaimer


def test_copy_follows_the_campaigns_real_locality_not_a_hardcoded_one(
    valid_selection_dict, valid_facts_list, valid_classification
):
    """THE replication bug: a Greenwich campaign must not advertise Blackheath.

    Node 17 hardcoded "Blackheath"/"SE3" into every title, body and CTA. That was correct only for
    the one original campaign; every replicated candidate -- which is the whole scaling model --
    rendered ad copy naming the wrong town while all upstream nodes correctly carried the right one.
    """
    greenwich = dict(valid_classification)
    greenwich["geography"] = {"locality": "Greenwich", "region": "London", "country": "UK"}

    asset = generate_asset_payload(valid_selection_dict, valid_facts_list, intent_input=greenwich)

    rendered = " ".join([asset.title, asset.body_content, asset.call_to_action])
    assert "Greenwich" in rendered
    assert "Blackheath" not in rendered, "copy must never name a locality the campaign is not targeting"
    assert "SE3" not in rendered, "postcode districts are not derivable from any real pipeline data"


def test_copy_follows_the_campaigns_real_service_for_an_unrelated_vertical(
    valid_selection_dict, valid_facts_list
):
    """The engine is meant to run unrelated verticals side by side, not just boilers.

    Hardcoded gas/boiler wording made every asset nonsense for any other market.
    """
    trading = {
        "primary_intent": "informational",
        "geography": {"locality": "Manchester", "region": "England", "country": "UK"},
        "service_context": {"service_name": "option_trading_stocks", "market_segment": "retail_investing"},
    }
    # Facts must match the vertical too -- they are caller-supplied real data from Node 16, so a
    # boiler fact here would be the test's own artefact rather than a template leak.
    trading_facts = [{
        "fact_id": "fact_option_expiry_01",
        "topic": "option_expiry",
        "claim": "Exchange-listed equity options in the US expire on the third Friday of the expiry month.",
        "is_safety_critical": False,
        "safety_guidance": None,
    }]

    asset = generate_asset_payload(valid_selection_dict, trading_facts, intent_input=trading)

    rendered = " ".join([asset.title, asset.body_content, asset.call_to_action])
    assert "Option Trading Stocks" in asset.title
    assert "Manchester" in rendered
    for leaked in ("boiler", "Boiler", "Gas Safe", "heating", "engineer"):
        assert leaked not in rendered, f"{leaked!r} leaked into an unrelated vertical's copy"


def test_asset_without_a_resolvable_service_fails_closed(valid_selection_dict, valid_facts_list):
    """Refuse to render rather than invent a subject for the advert."""
    with pytest.raises(ValidationError):
        generate_asset_payload(valid_selection_dict, valid_facts_list, intent_input={"primary_intent": "x"})


def test_unknown_geography_omits_the_place_rather_than_inventing_one(
    valid_selection_dict, valid_facts_list
):
    """If locality genuinely is not known, the copy must carry no geographic claim at all."""
    no_geo = {
        "primary_intent": "troubleshooting",
        "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
    }

    asset = generate_asset_payload(valid_selection_dict, valid_facts_list, intent_input=no_geo)

    rendered = " ".join([asset.title, asset.body_content, asset.call_to_action])
    assert "Boiler Repair" in asset.title
    for placeholder in ("Blackheath", "None", "N/A", "{", "}"):
        assert placeholder not in rendered


def test_default_cta_claims_nothing_the_pipeline_cannot_evidence(
    valid_selection_dict, valid_facts_list, valid_classification
):
    """The old default CTA asserted "vetted", "fixed-fee" and "same-day" -- none registered as
    facts anywhere in the pipeline, i.e. fabricated business claims baked into every asset."""
    asset = generate_asset_payload(valid_selection_dict, valid_facts_list, intent_input=valid_classification)

    for unevidenced in ("vetted", "fixed-fee", "same-day", "24/7", "Fixed diagnostic pricing"):
        assert unevidenced.lower() not in asset.call_to_action.lower()


def test_missing_facts_fails_closed(valid_selection_dict):
    """Verifies that generating an asset without verified facts fails closed."""
    with pytest.raises(LineageError):
        generate_asset_payload(valid_selection_dict, facts=[])


def test_missing_lineage_fails_closed(valid_selection_dict, valid_facts_list):
    """Verifies that missing any upstream lineage identifier fails closed."""
    for req_field in ("target_id", "signal_id", "classification_id", "opportunity_id", "path_id", "selection_id"):
        corrupt = valid_selection_dict.copy()
        corrupt[req_field] = ""
        with pytest.raises(LineageError):
            generate_asset_payload(corrupt, valid_facts_list)


def test_prohibited_pii_screening(valid_selection_dict, valid_facts_list):
    """Verifies that CTA or content with PII is rejected."""
    with pytest.raises(ValidationError):
        generate_asset_payload(
            valid_selection_dict,
            valid_facts_list,
            custom_cta="Email us at booking@boilercompany.co.uk immediately."
        )


def test_serialization_roundtrip(valid_selection_dict, valid_facts_list, valid_classification):
    """Verifies JSON roundtrip serialization."""
    asset = generate_asset_payload(valid_selection_dict, valid_facts_list, intent_input=valid_classification)
    d = asset.to_dict()
    assert d["asset_id"] == asset.asset_id
    assert d["metadata"]["external_action"] is False

    json_str = asset.to_json()
    parsed = json.loads(json_str)
    assert parsed["asset_id"] == asset.asset_id
    assert parsed["metadata"]["external_action"] is False


def test_nodes01_to_17_full_pipeline_live_integration():
    """
    Real unmocked multi-node integration test: executes full registry chain across
    Nodes 01 -> 02 -> 03 -> 04 -> 05 -> 11 -> 12 -> 13 -> 14 -> 16 -> 17 with non-mocked data.
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

        # 1. Classify (Node 11)
        cls_res = classify_demand_signal(sig.to_dict())

        # 2. Score Opportunity (Node 12)
        opp = score_demand_opportunity(cls_res)

        # 3. Discover Demand Path (Node 13)
        path_rec = discover_demand_path(opp)

        # 4. Select Channel & Placements (Node 14)
        sel = select_channel_placements(path_rec)

        # 5. Register verified canonical knowledge (Node 16)
        fact1 = k_store.register_fact(
            target_id=target.target_id,
            topic="boiler_pressure_nominal",
            claim="Standard combi boilers operate at 1.0 to 1.5 bar cold pressure.",
            verification_source="Worcester Bosch User Guide 2025",
            is_safety_critical=True,
            safety_guidance="Do not attempt to open sealed casing if pressure exceeds 3.0 bar."
        )

        # 6. Generate Asset Payload (Node 17)
        asset = generate_asset_payload(
            selection_input=sel,
            facts=[fact1],
            intent_input=cls_res
        )

        assert asset.asset_id.startswith("asset_")
        assert asset.target_id == target.target_id
        assert asset.signal_id == sig.signal_id
        assert asset.classification_id == cls_res.classification_id
        assert asset.opportunity_id == opp.opportunity_id
        assert asset.path_id == path_rec.path_id
        assert asset.selection_id == sel.selection_id
        assert fact1.fact_id in asset.fact_ids
        assert "SAFETY" in asset.safety_disclaimer
        assert asset.metadata.external_action is False
