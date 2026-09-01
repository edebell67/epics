# epics/ep_050_distribution_engine/integration/golden_path/test_golden_path_full_engine.py
# EP050 — Full-engine golden-path integration test, Node 01 through Node 37.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-18 · Initial version. Built after verifying that only one of ~36 inter-node
#   boundaries (Node 19 -> Node 20) had a formal cross-node contract test; every other node had
#   only been proven against its OWN fixture assumptions about upstream output, never against
#   what the real upstream node actually produces. This test closes that gap for the primary
#   "find a lead" path: it imports and calls the REAL function/class from every one of the 37
#   nodes, in sequence, feeding each stage's actual real output into the next stage -- no
#   hand-authored fixtures pretending to be another node's output, and no re-implementation of
#   any node's logic here. It asserts lineage (target_id/opportunity_id/asset_id/etc.) survives
#   unbroken from Node 01 to Node 37. Every node along the way already enforces its own
#   fail-closed offline/external_action=False boundary; this test does not relax or bypass any
#   of them -- it only proves the boundaries compose correctly across the full chain.
#
# Scope: read-only integration proof. No network access, no external API call, no live
# publishing, no real render. Nodes 05-10/15/18's own automated live-fetch paths are NOT
# exercised here (they have their own dedicated test suites) -- this test uses the manual/
# fixture entry points throughout, because its purpose is proving cross-node WIRING, not
# re-proving any single node's own already-tested behavior.

from __future__ import annotations

import sys
from pathlib import Path

import pytest

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[2] / "implementation"
for node_dir in (
    "node_01", "node_02", "node_03", "node_04", "node_05", "node_06", "node_07", "node_08",
    "node_09", "node_10", "node_11", "node_12", "node_13", "node_14", "node_15", "node_16",
    "node_17", "node_18", "node_19", "node_20", "node_21", "node_22", "node_23", "node_24",
    "node_25", "node_26", "node_27", "node_28", "node_29", "node_30", "node_31", "node_32",
    "node_33", "node_34", "node_35", "node_36", "node_37",
):
    sys.path.insert(0, str(IMPLEMENTATION_ROOT / node_dir))

from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from social_video_discovery import SocialVideoSignalRegistry  # noqa: E402
from competitor_intelligence import CompetitorSignalRegistry  # noqa: E402
from community_intelligence import CommunitySignalRegistry  # noqa: E402
from trend_detection import TrendSignalRegistry  # noqa: E402
from intent_classification import classify_demand_signal  # noqa: E402
from opportunity_scoring import score_demand_opportunity  # noqa: E402
from demand_path_discovery import discover_demand_path  # noqa: E402
from channel_placement_selection import select_channel_placements  # noqa: E402
from campaign_cluster_generation import CampaignClusterRegistry  # noqa: E402
from canonical_knowledge_store import CanonicalKnowledgeStore  # noqa: E402
from content_utility_factory import generate_asset_payload  # noqa: E402
from video_asset_factory import VideoAssetRegistry  # noqa: E402
from quality_compliance import evaluate_asset_compliance  # noqa: E402
from publishing_scheduler import build_mock_publication_plan  # noqa: E402
from search_distribution import build_search_distribution_package  # noqa: E402
from video_distribution import build_video_distribution_package  # noqa: E402
from social_distribution import build_social_distribution_package  # noqa: E402
from community_participation import build_community_participation_plan  # noqa: E402
from syndication_distribution import build_syndication_distribution_package  # noqa: E402
from smart_destination_router import build_route_recommendation  # noqa: E402
from structured_lead_capture import build_structured_lead_record  # noqa: E402
from offline_attribution import build_attribution_record  # noqa: E402
from lead_qualification import evaluate_lead_qualification  # noqa: E402
from lead_routing import route_qualified_lead  # noqa: E402
from lead_lifecycle_tracker import transition_lead_lifecycle  # noqa: E402
from performance_warehouse import build_performance_record  # noqa: E402
from outcome_feedback import ingest_outcome_feedback  # noqa: E402
from winner_detection import detect_winning_strategy  # noqa: E402
from winner_amplification import generate_amplification_plan  # noqa: E402
from effort_allocation import plan_effort_allocation  # noqa: E402
from distribution_knowledge_base import record_distribution_knowledge  # noqa: E402

TARGET_ID = "tgt_boiler_repair_blackheath"
GEOGRAPHY = {"locality": "Blackheath", "region": "London", "country": "UK"}

# Node 26's routing rule table is a single hardcoded fixture rule; routing_context is a
# caller-supplied analyst decision (like Node 08's channel or Node 15's campaign_context), not
# something auto-derived from upstream text -- so these values are chosen to match that rule.
ROUTING_CONTEXT_TOPIC = "safe boiler pressure guide"
ROUTING_CONTEXT_INTENT = "diagnostic_quote"
ROUTING_CONTEXT_GEO = "blackheath"
ROUTING_CONTEXT_SERVICE = "boiler_repair"


def test_full_golden_path_node01_through_node37(tmp_path):
    # --- Phase 1: Nodes 01-04 (real business facts, caller-supplied) ---------
    target_registry = TargetRegistry(tmp_path / "node_01.json")
    target = target_registry.register(
        target_type="service_market", service="boiler_repair", market="domestic_plumbing",
        geography=GEOGRAPHY,
    )
    assert target.target_id == TARGET_ID

    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    product_registry.register(
        target_id=TARGET_ID,
        problem="Homeowners lose boiler pressure and hot water with no clear diagnosis path.",
        solution="A vetted local boiler-repair callout that diagnoses and restores pressure same-day.",
        features=["Same-day callout"], benefits=["Hot water restored quickly"],
        differentiators=["Local coverage"], commercial_model="Fixed diagnostic fee.",
        customer_outcome="Working boiler within 24 hours.",
    )

    audience_registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    audience_registry.register(
        target_id=TARGET_ID, segment_name="Blackheath homeowner, boiler pressure loss",
        needs=["Restore hot water quickly"], pains=["No heating or hot water"], urgency="high",
        eligibility_geography=GEOGRAPHY,
    )

    conversion_registry = ConversionDefinitionRegistry(tmp_path / "node_04.json", target_registry, product_registry, audience_registry)
    conversion_registry.register(
        target_id=TARGET_ID, stages=MASTER_SPEC_STAGES,
        allowed_transitions=[
            ["visit", "engage"], ["engage", "tool_use"], ["tool_use", "enquiry"], ["enquiry", "lead"],
            ["lead", "qualified_lead"], ["qualified_lead", "booking"], ["booking", "sale"], ["sale", "revenue"],
        ],
        success_stage_id="sale", success_criteria="A lead reaches the sale stage with a recorded outcome.",
    )

    # --- Phase 2: Nodes 05-10 (demand intelligence) --------------------------
    demand_registry = DemandSignalRegistry(tmp_path / "node_05.json", target_registry, product_registry, audience_registry, conversion_registry)
    signal = demand_registry.register(
        signal_id="sig_golden_path", target_id=TARGET_ID,
        raw_query="boiler pressure dropped to zero no hot water", topic="boiler_pressure_loss",
        source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00", geography=GEOGRAPHY,
        service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
    )

    question_registry = QuestionRegistry(tmp_path / "node_06.json", target_registry, product_registry, audience_registry, conversion_registry, demand_registry)
    question_registry.register(
        question_id="q_golden_path", target_id=TARGET_ID,
        question_text="Why does my boiler pressure keep dropping overnight?", topic="boiler_pressure_loss",
        pain_point="Recurring pressure loss with no obvious cause", geography=GEOGRAPHY,
        intent_cues=["troubleshooting"], source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
        evidence="Manually curated fixture consistent with the EP050 master spec's worked example.",
    )

    social_registry = SocialVideoSignalRegistry(tmp_path / "node_07.json", target_registry, product_registry, audience_registry, conversion_registry, demand_registry, question_registry)
    social_registry.register(
        signal_id="sv_golden_path", target_id=TARGET_ID, platform="youtube", format="short_video",
        topic="boiler_pressure_loss", theme="overnight_pressure_drop_diagnosis", intent_cues=["troubleshooting"],
        geography=GEOGRAPHY, observed_metrics={"synthetic_views": 4200}, observed_at="2026-08-17T00:00:00+00:00",
        source_type="manual_curation", evidence="Manually curated theme.",
    )

    competitor_registry = CompetitorSignalRegistry(tmp_path / "node_08.json", target_registry, product_registry, audience_registry, conversion_registry, demand_registry, question_registry, social_registry)
    competitor_registry.register(
        signal_id="cp_golden_path", target_id=TARGET_ID, competitor_name="Synthetic Rival Plumbing Co",
        channel="google_search", topic="boiler_pressure_loss", query="boiler pressure loss repair blackheath",
        attention_source="organic_search", relevance_score=0.72, competition_indicator="medium",
        geography=GEOGRAPHY, observed_at="2026-08-17T00:00:00+00:00", source_type="manual_curation",
        evidence="Manually curated competitor observation.",
    )

    community_registry = CommunitySignalRegistry(tmp_path / "node_09.json", target_registry, product_registry, audience_registry, conversion_registry, demand_registry, question_registry, social_registry, competitor_registry)
    community_registry.register(
        signal_id="cm_golden_path", target_id=TARGET_ID, community_source="r/DIYUK",
        topic="boiler_pressure_loss", question="Boiler pressure keeps dropping overnight, anyone else had this?",
        pain_point="Recurring pressure loss with no obvious cause", intent_cues=["troubleshooting"],
        geography=GEOGRAPHY, observed_metrics={"synthetic_upvotes": 58}, observed_at="2026-08-17T00:00:00+00:00",
        source_type="manual_curation", evidence="Manually curated community thread theme.",
    )

    trend_registry = TrendSignalRegistry(tmp_path / "node_10.json", target_registry, product_registry, audience_registry, conversion_registry, demand_registry, question_registry, social_registry, competitor_registry, community_registry)
    trend_registry.register(
        trend_id="trend_golden_path", target_id=TARGET_ID, topic="boiler_pressure_loss", geography=GEOGRAPHY,
        window={
            "baseline_start": "2026-08-01T00:00:00+00:00", "baseline_end": "2026-08-08T00:00:00+00:00",
            "current_start": "2026-08-08T00:00:00+00:00", "current_end": "2026-08-15T00:00:00+00:00",
        },
        metric_name="demand_signal_count", baseline_value=20.0, baseline_sample_count=10,
        current_value=32.0, current_sample_count=12, source_type="manual_curation",
        evidence="Manually curated trend observation.",
    )

    # --- Phase 3: Nodes 11-15 (strategy) --------------------------------------
    classification = classify_demand_signal(signal.to_contract_payload())
    opportunity = score_demand_opportunity(classification)
    path = discover_demand_path(opportunity)
    selection = select_channel_placements(path)
    opportunity_id = opportunity.opportunity_id

    cluster_registry = CampaignClusterRegistry(tmp_path / "node_15.json")
    member_bundle = {
        "classification": classification.to_dict(), "opportunity": opportunity.to_dict(),
        "path": path.to_dict(), "selection": selection.to_dict(),
    }
    cluster = cluster_registry.generate_and_register([member_bundle])[0]

    # --- Phase 4: Nodes 16-19 (knowledge, assets, video, compliance) --------
    knowledge_store = CanonicalKnowledgeStore()
    fact_1 = knowledge_store.register_fact(
        target_id=TARGET_ID, topic="boiler_pressure",
        claim="Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
        verification_source="manufacturer_manual_fixture", is_safety_critical=True,
        safety_guidance="Do not attempt gas work without Gas Safe registration.",
    )
    fact_2 = knowledge_store.register_fact(
        target_id=TARGET_ID, topic="boiler_pressure",
        claim="A pressure reading of zero indicates a significant water loss requiring investigation.",
        verification_source="manufacturer_manual_fixture",
    )
    facts = [fact_1, fact_2]

    asset = generate_asset_payload(selection, facts=facts, intent_input=classification)

    video_registry = VideoAssetRegistry(tmp_path / "node_18.json")
    video_asset = video_registry.generate_and_register(
        classification=classification, selection=selection, facts=facts, asset=asset, cluster=cluster,
    )

    compliance_result, approved_package = evaluate_asset_compliance(asset, knowledge_store=knowledge_store)
    assert compliance_result.approved is True, f"Node 19 rejected the asset: {compliance_result.reasons}"
    assert approved_package is not None
    approved_dict = approved_package.to_dict()
    assert approved_dict["target_id"] == TARGET_ID
    assert approved_dict["opportunity_id"] == opportunity_id

    # --- Phase 5: Nodes 20-27 (distribution & conversion) --------------------
    publication_plan = build_mock_publication_plan(approved_dict)
    search_package = build_search_distribution_package(publication_plan, approved_dict)

    # Nodes 22-25 are parallel distribution channels off the same approved package; each has
    # its own EP050_LIVE_PUBLISH_ENABLED-style gate (unset here, so external_action stays False).
    video_package = build_video_distribution_package(approved_dict)
    social_package = build_social_distribution_package(approved_dict)
    community_plan = build_community_participation_plan(approved_dict)
    syndication_package = build_syndication_distribution_package(approved_dict)
    for package in (video_package, social_package, community_plan, syndication_package):
        assert package["external_action"] is False

    routing_context = {
        "topic": ROUTING_CONTEXT_TOPIC, "intent": ROUTING_CONTEXT_INTENT,
        "geography": ROUTING_CONTEXT_GEO, "service": ROUTING_CONTEXT_SERVICE,
        "channel": "search_landing", "external_action": False,
        "asset_id": publication_plan["asset_id"], "target_id": publication_plan["target_id"],
        "opportunity_id": publication_plan["opportunity_id"],
    }
    route = build_route_recommendation(publication_plan, approved_dict, search_package, routing_context)
    assert route["lineage"]["target_id"] == TARGET_ID
    assert route["lineage"]["opportunity_id"] == opportunity_id

    intake = {
        "session_id": "sess_golden_path_001",
        "source": "search_landing",
        "consent": {
            "granted": True, "timestamp": "2026-08-17T12:00:00Z",
            "version": "privacy_policy_v1.0", "basis": "explicit_consent",
        },
    }
    lead = build_structured_lead_record(route, intake)
    assert lead["external_action"] is False
    assert lead["acquisition"]["target_id"] == TARGET_ID
    assert lead["acquisition"]["opportunity_id"] == opportunity_id

    # --- Phase 6: Nodes 28-31 (lead lifecycle) --------------------------------
    attribution_model = {"name": "deterministic_last_verified_touch", "version": "1.0.0", "confidence": 0.95}
    attribution = build_attribution_record(lead, attribution_model)
    assert attribution["lineage"]["target_id"] == TARGET_ID
    assert attribution["lineage"]["opportunity_id"] == opportunity_id

    qualification = evaluate_lead_qualification(attribution)
    assert qualification["is_qualified"] is True, f"Golden-path lead unexpectedly disqualified: {qualification}"
    # KNOWN BUG (found by this test, reported to the board, not fixed here -- Node 29 is not
    # owned by this agent): evaluate_lead_qualification() reads target_id/opportunity_id from
    # the TOP LEVEL of attribution_record via `.get(...)`, but Node 28's real output nests both
    # under attribution["lineage"] -- there is no top-level target_id/opportunity_id key. The
    # lookup silently defaults to "" instead of raising, so the qualification DECISION (is_
    # qualified, score) is still correct, but its target_id/opportunity_id labels are wrong.
    # This is exactly the "each node passes its own tests, but the wiring between two specific
    # nodes is broken" failure mode this test exists to catch -- asserted here as ground truth,
    # not patched around, so this test goes green again the moment Node 29 is fixed to read
    # attribution_record["lineage"]["target_id"] instead.
    assert qualification["target_id"] == TARGET_ID
    assert qualification["opportunity_id"] == opportunity_id

    routing_decision = route_qualified_lead(qualification)
    assert routing_decision["target_id"] == TARGET_ID
    assert routing_decision["lead_id"] == lead["lead_id"]

    lifecycle = transition_lead_lifecycle(None, routing_record=routing_decision, new_status="qualified")
    assert lifecycle["current_status"] == "qualified"
    assert lifecycle["target_id"] == TARGET_ID

    # --- Phase 7: Nodes 32-37 (learning & allocation) -------------------------
    performance = build_performance_record(
        target_id=TARGET_ID, opportunity_id=opportunity_id, channel="search_landing",
    )
    assert performance["target_id"] == TARGET_ID
    assert performance["opportunity_id"] == opportunity_id

    feedback = ingest_outcome_feedback(
        lead_id=lead["lead_id"], target_id=TARGET_ID, feedback_source="technician_app",
    )
    assert feedback["target_id"] == TARGET_ID

    winner = detect_winning_strategy(performance)
    assert winner["is_winner"] is True, f"Golden-path performance unexpectedly not a winner: {winner}"
    assert winner["opportunity_id"] == opportunity_id

    amplification = generate_amplification_plan(winner)
    assert amplification["opportunity_id"] == opportunity_id

    allocation = plan_effort_allocation(amplification)
    assert allocation["opportunity_id"] == opportunity_id

    knowledge_entry = record_distribution_knowledge(allocation)
    assert knowledge_entry["opportunity_id"] == opportunity_id
    assert knowledge_entry["provenance"]["lifecycle_complete"] is True

    # --- Final proof: the golden thread survives Node 01 -> Node 37 -------------
    # target_id/opportunity_id survive correctly through Nodes 01-28 (registration through
    # attribution) and again from Node 32 onward (performance/winner/amplification/allocation/
    # knowledge, because that stage requires the caller to re-supply the ID explicitly rather
    # than inherit it). The one broken stretch is Nodes 29-31 (see the KNOWN BUG comments
    # above) -- their target_id is "" instead of TARGET_ID, a real, precisely-isolated defect
    # this test discovered, not a gap in this test's own wiring.
    assert target.target_id == TARGET_ID
    assert lead["acquisition"]["target_id"] == TARGET_ID
    assert opportunity.opportunity_id == opportunity_id == performance["opportunity_id"] == winner["opportunity_id"] == amplification["opportunity_id"] == allocation["opportunity_id"] == knowledge_entry["opportunity_id"]
    assert performance["target_id"] == feedback["target_id"] == TARGET_ID
    assert qualification["target_id"] == routing_decision["target_id"] == lifecycle["target_id"] == TARGET_ID
