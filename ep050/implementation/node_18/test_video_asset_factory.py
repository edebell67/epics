# epics/ep_050_distribution_engine/implementation/node_18/test_video_asset_factory.py
# EP050 Node 18 — Video Asset Factory test suite.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds coverage for generate_and_register_from_live_chain() (real chain
# re-derivation matching the manual path's deterministic video_asset_id, unknown cluster_id/
# signal_id lineage errors, no-facts-registered lineage error, no-network-call assertion).
# v1.0.0 · 2026-08-17 · Initial unit/contract/negative/boundary/determinism/idempotency/conflict/
# persistence/no-network/regression suite for Node 18.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no actual video rendering, no paid media/LLM APIs, no external side effect.
# Every upstream record is built by calling the REAL Node 11/13/14/15/16/17 functions (not mocked).

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_02"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_03"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_04"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_05"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_11"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_12"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_13"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_14"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_15"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_16"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_17"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from intent_classification import classify_demand_signal  # noqa: E402
from opportunity_scoring import score_demand_opportunity  # noqa: E402
from demand_path_discovery import discover_demand_path  # noqa: E402
from channel_placement_selection import select_channel_placements  # noqa: E402
from campaign_cluster_generation import CampaignClusterRegistry  # noqa: E402
from canonical_knowledge_store import CanonicalKnowledgeStore  # noqa: E402
from content_utility_factory import generate_asset_payload  # noqa: E402

from video_asset_factory import (
    VideoAssetRegistry,
    ConflictError,
    LineageError,
    ValidationError,
)

TROUBLESHOOTING_QUERY = "boiler pressure dropped to zero no hot water"


def _build_pipeline(signal_id: str, target_id: str = "tgt_boiler_repair_blackheath") -> dict:
    payload = {
        "signal_id": signal_id,
        "target_id": target_id,
        "raw_query": TROUBLESHOOTING_QUERY,
        "topic": "boiler_pressure_loss",
        "source_type": "manual_curation",
        "observed_at": "2026-08-17T00:00:00+00:00",
        "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
    }
    classification = classify_demand_signal(payload)
    opportunity = score_demand_opportunity(classification)
    path = discover_demand_path(opportunity)
    selection = select_channel_placements(path)

    facts_store = CanonicalKnowledgeStore()
    fact_1 = facts_store.register_fact(
        target_id=target_id,
        topic="boiler_pressure",
        claim="Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
        verification_source="manufacturer_manual_fixture",
        is_safety_critical=True,
        safety_guidance="Do not attempt gas work without Gas Safe registration.",
    )
    fact_2 = facts_store.register_fact(
        target_id=target_id,
        topic="boiler_pressure",
        claim="A pressure reading of zero indicates a significant water loss requiring investigation.",
        verification_source="manufacturer_manual_fixture",
    )
    facts = [fact_1, fact_2]

    asset = generate_asset_payload(selection, facts=facts, intent_input=classification)

    return {
        "classification": classification,
        "opportunity": opportunity,
        "path": path,
        "selection": selection,
        "facts": facts,
        "asset": asset,
    }


def _build_cluster(tmp_path: Path, pipeline: dict, name: str = "cluster") -> dict:
    cluster_registry = CampaignClusterRegistry(tmp_path / f"{name}.json")
    member_bundle = {
        "classification": pipeline["classification"].to_dict(),
        "opportunity": pipeline["opportunity"].to_dict(),
        "path": pipeline["path"].to_dict(),
        "selection": pipeline["selection"].to_dict(),
    }
    clusters = cluster_registry.generate_and_register([member_bundle])
    return clusters[0]


@pytest.fixture
def pipeline(tmp_path):
    return _build_pipeline("sig_node18_base")


@pytest.fixture
def cluster(tmp_path, pipeline):
    return _build_cluster(tmp_path, pipeline)


@pytest.fixture
def registry(tmp_path):
    return VideoAssetRegistry(tmp_path / "node_18_videos.json")


# --- Positive registration / real upstream integration -----------------------

def test_positive_registration_with_real_upstream_chain(registry, pipeline, cluster):
    record = registry.generate_and_register(
        classification=pipeline["classification"],
        selection=pipeline["selection"],
        facts=pipeline["facts"],
        asset=pipeline["asset"],
        cluster=cluster,
    )
    assert record.video_asset_id.startswith("vid_")
    assert record.external_action is False
    assert len(record.storyboard) == 4  # hook + 2 facts + cta
    assert record.total_duration_seconds == pytest.approx(3.0 + 4.0 + 4.0 + 5.0)
    assert record.safety_disclaimer == pipeline["asset"].safety_disclaimer
    # The video's own CTA/title are deliberately locality-neutral (2026-08-20, direct user
    # instruction: "video will not contain a reference to a town or city") -- unlike Node 17's
    # asset.call_to_action, which correctly DOES name the locality for maps/search placements.
    # A rendered video must stay reusable across every locality its applicability tag covers.
    assert record.call_to_action != pipeline["asset"].call_to_action
    assert "Blackheath" not in record.call_to_action
    assert "London" not in record.call_to_action
    assert record.call_to_action == "Enquire about Boiler Repair."
    assert all("Blackheath" not in s.voiceover_text and "London" not in s.voiceover_text for s in record.storyboard)


def test_default_shot_list_matches_storyboard_length(registry, pipeline, cluster):
    record = registry.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    assert len(record.shot_list) == len(record.storyboard)


# --- Lineage / negative ---------------------------------------------------

def test_mismatched_classification_id_is_rejected(registry, pipeline, cluster):
    tampered_asset = pipeline["asset"].to_dict()
    tampered_asset["classification_id"] = "cls_tampered"
    with pytest.raises(LineageError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=tampered_asset, cluster=cluster,
        )


def test_mismatched_selection_id_is_rejected(registry, pipeline, cluster):
    tampered_asset = pipeline["asset"].to_dict()
    tampered_asset["selection_id"] = "sel_tampered"
    with pytest.raises(LineageError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=tampered_asset, cluster=cluster,
        )


def test_fact_not_in_asset_fact_ids_is_rejected(registry, pipeline, cluster):
    facts_store = CanonicalKnowledgeStore()
    foreign_fact = facts_store.register_fact(
        target_id="tgt_boiler_repair_blackheath", topic="unrelated",
        claim="An unrelated fact never approved into this asset.", verification_source="fixture",
    )
    with pytest.raises(LineageError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=[foreign_fact], asset=pipeline["asset"], cluster=cluster,
        )


def test_asset_missing_fact_ids_is_rejected(registry, pipeline, cluster):
    tampered_asset = pipeline["asset"].to_dict()
    tampered_asset["fact_ids"] = []
    with pytest.raises(LineageError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=tampered_asset, cluster=cluster,
        )


def test_asset_not_a_cluster_member_is_rejected(registry, tmp_path, pipeline):
    other_pipeline = _build_pipeline("sig_node18_other", target_id="tgt_boiler_repair_blackheath_2")
    other_cluster = _build_cluster(tmp_path, other_pipeline, name="other_cluster")
    with pytest.raises(LineageError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=other_cluster,
        )


def test_external_action_not_false_is_rejected(registry, pipeline, cluster):
    tampered_asset = pipeline["asset"].to_dict()
    tampered_asset["metadata"] = dict(tampered_asset["metadata"], external_action=True)
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=tampered_asset, cluster=cluster,
        )


def test_missing_safety_disclaimer_is_rejected(registry, pipeline, cluster):
    tampered_asset = pipeline["asset"].to_dict()
    tampered_asset["safety_disclaimer"] = ""
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=tampered_asset, cluster=cluster,
        )


def test_missing_call_to_action_is_rejected(registry, pipeline, cluster):
    tampered_asset = pipeline["asset"].to_dict()
    tampered_asset["call_to_action"] = ""
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=tampered_asset, cluster=cluster,
        )


# --- Scene / storyboard validation -------------------------------------------

def test_empty_custom_scenes_is_rejected(registry, pipeline, cluster):
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=[],
        )


def test_custom_scene_missing_field_is_rejected(registry, pipeline, cluster):
    bad_scene = [{"scene_index": 1, "shot_type": "hook", "duration_seconds": 15.0}]
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=bad_scene,
        )


def test_custom_scene_wrong_index_order_is_rejected(registry, pipeline, cluster):
    bad_scene = [{
        "scene_index": 2, "shot_type": "hook", "duration_seconds": 15.0,
        "visual_description": "desc", "voiceover_text": "voice", "source_fact_ids": [],
    }]
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=bad_scene,
        )


def test_custom_scene_non_positive_duration_is_rejected(registry, pipeline, cluster):
    bad_scene = [{
        "scene_index": 1, "shot_type": "hook", "duration_seconds": 0,
        "visual_description": "desc", "voiceover_text": "voice", "source_fact_ids": [],
    }]
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=bad_scene,
        )


def test_custom_scene_unapproved_fact_id_is_rejected(registry, pipeline, cluster):
    bad_scene = [{
        "scene_index": 1, "shot_type": "hook", "duration_seconds": 15.0,
        "visual_description": "desc", "voiceover_text": "voice", "source_fact_ids": ["fact_not_approved"],
    }]
    with pytest.raises(LineageError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=bad_scene,
        )


def test_custom_scene_email_pii_is_rejected(registry, pipeline, cluster):
    bad_scene = [{
        "scene_index": 1, "shot_type": "hook", "duration_seconds": 15.0,
        "visual_description": "desc", "voiceover_text": "Email jane.doe@example.com for a quote",
        "source_fact_ids": [],
    }]
    with pytest.raises(ValidationError, match="email"):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=bad_scene,
        )


def test_custom_scene_phone_pii_is_rejected(registry, pipeline, cluster):
    bad_scene = [{
        "scene_index": 1, "shot_type": "hook", "duration_seconds": 15.0,
        "visual_description": "Call 020 7946 0958 now", "voiceover_text": "voice",
        "source_fact_ids": [],
    }]
    with pytest.raises(ValidationError, match="phone"):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=bad_scene,
        )


def test_total_duration_too_short_is_rejected(registry, pipeline, cluster):
    short_scene = [{
        "scene_index": 1, "shot_type": "hook", "duration_seconds": 1.0,
        "visual_description": "desc", "voiceover_text": "voice", "source_fact_ids": [],
    }]
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=short_scene,
        )


def test_total_duration_too_long_is_rejected(registry, pipeline, cluster):
    long_scenes = [
        {
            "scene_index": i + 1, "shot_type": "filler", "duration_seconds": 5.0,
            "visual_description": f"filler scene {i + 1}", "voiceover_text": "voice", "source_fact_ids": [],
        }
        for i in range(40)  # 40 * 5.0s = 200s > MAX_TOTAL_DURATION_SECONDS
    ]
    with pytest.raises(ValidationError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster, custom_scenes=long_scenes,
        )


# --- Determinism ---------------------------------------------------------------

def test_determinism_same_inputs_produce_same_video_asset_id(tmp_path, pipeline, cluster):
    registry_1 = VideoAssetRegistry(tmp_path / "run1.json")
    record_1 = registry_1.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    registry_2 = VideoAssetRegistry(tmp_path / "run2.json")
    record_2 = registry_2.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    assert record_1.video_asset_id == record_2.video_asset_id
    assert record_1.total_duration_seconds == record_2.total_duration_seconds


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_rerun_is_idempotent_and_does_not_duplicate(registry, pipeline, cluster):
    first = registry.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    second = registry.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    assert first.video_asset_id == second.video_asset_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_stored_video_is_rejected(tmp_path, pipeline, cluster):
    # Simulates a legitimate persisted-state conflict by tampering the stored record directly,
    # since video_asset_id is a pure function of (cluster_id, asset_id, template_version) and
    # cannot be forced to conflict through the public API alone.
    storage_path = tmp_path / "node_18_conflict.json"
    registry = VideoAssetRegistry(storage_path)
    record = registry.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    data = json.loads(storage_path.read_text(encoding="utf-8"))
    data[record.video_asset_id]["total_duration_seconds"] = 999.0
    storage_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ConflictError):
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
        )


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(tmp_path, pipeline, cluster):
    storage_path = tmp_path / "node_18_persist.json"
    registry_a = VideoAssetRegistry(storage_path)
    registered = registry_a.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    registry_b = VideoAssetRegistry(storage_path)
    fetched = registry_b.get(registered.video_asset_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- Automated live ingestion (generate_and_register_from_live_chain) ------

SYNTHETIC_TARGET = dict(
    target_type="service_market", service="boiler_repair", market="domestic_plumbing",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
)
SYNTHETIC_PRODUCT = dict(
    problem="Homeowners lose boiler pressure and hot water with no clear diagnosis path.",
    solution="A vetted local boiler-repair callout that diagnoses and restores pressure same-day.",
    features=["Same-day callout"], benefits=["Hot water restored quickly"],
    differentiators=["Local coverage"], commercial_model="Fixed diagnostic fee.",
    customer_outcome="Working boiler within 24 hours.",
)
SYNTHETIC_SEGMENT = dict(
    segment_name="Blackheath homeowner, boiler pressure loss", needs=["Restore hot water quickly"],
    pains=["No heating or hot water"], urgency="high",
    eligibility_geography={"locality": "Blackheath", "region": "London", "country": "UK"},
)
MASTER_SPEC_TRANSITIONS = [
    ["visit", "engage"], ["engage", "tool_use"], ["tool_use", "enquiry"], ["enquiry", "lead"],
    ["lead", "qualified_lead"], ["qualified_lead", "booking"], ["booking", "sale"], ["sale", "revenue"],
]
SYNTHETIC_CONVERSION = dict(
    stages=MASTER_SPEC_STAGES, allowed_transitions=MASTER_SPEC_TRANSITIONS,
    success_stage_id="sale", success_criteria="A lead reaches the sale stage with a recorded outcome.",
)


@pytest.fixture
def demand_signal_registry(tmp_path):
    target_registry = TargetRegistry(tmp_path / "node_01.json")
    target_registry.register(**SYNTHETIC_TARGET)
    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    product_registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_PRODUCT)
    audience_registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    audience_registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_SEGMENT)
    conversion_registry = ConversionDefinitionRegistry(
        tmp_path / "node_04.json", target_registry, product_registry, audience_registry
    )
    conversion_registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_CONVERSION)
    return DemandSignalRegistry(
        tmp_path / "node_05.json", target_registry, product_registry, audience_registry, conversion_registry
    )


@pytest.fixture
def knowledge_store():
    store = CanonicalKnowledgeStore()
    store.register_fact(
        target_id="tgt_boiler_repair_blackheath", topic="boiler_pressure",
        claim="Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
        verification_source="manufacturer_manual_fixture", is_safety_critical=True,
        safety_guidance="Do not attempt gas work without Gas Safe registration.",
    )
    store.register_fact(
        target_id="tgt_boiler_repair_blackheath", topic="boiler_pressure",
        claim="A pressure reading of zero indicates a significant water loss requiring investigation.",
        verification_source="manufacturer_manual_fixture",
    )
    return store


@pytest.fixture
def live_cluster(tmp_path, demand_signal_registry):
    demand_signal_registry.register(
        signal_id="sig_node18_live", target_id="tgt_boiler_repair_blackheath", raw_query=TROUBLESHOOTING_QUERY,
        topic="boiler_pressure_loss", source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
    )
    cluster_registry = CampaignClusterRegistry(tmp_path / "node_15_live.json")
    clusters = cluster_registry.generate_and_register_from_live_signals(
        "tgt_boiler_repair_blackheath", demand_signal_registry
    )
    return cluster_registry, clusters[0]


def test_generate_from_live_chain_matches_manual_path(registry, demand_signal_registry, knowledge_store, live_cluster):
    cluster_registry, cluster = live_cluster

    record = registry.generate_and_register_from_live_chain(
        cluster_id=cluster.cluster_id, target_id="tgt_boiler_repair_blackheath", signal_id="sig_node18_live",
        demand_signal_registry=demand_signal_registry, cluster_registry=cluster_registry, knowledge_store=knowledge_store,
    )

    assert record.video_asset_id.startswith("vid_")
    assert record.cluster_id == cluster.cluster_id
    assert record.external_action is False
    assert record.safety_disclaimer
    assert record.call_to_action
    assert len(record.storyboard) == 4  # hook + 2 facts + cta, same as the manual-path fixture

    # Cross-check: the manual pipeline fixture (_build_pipeline) drives the exact same real
    # Node11-14 chain over the same signal_id/query, so the deterministic video_asset_id must match.
    manual_pipeline = _build_pipeline("sig_node18_live")
    manual_cluster = _build_cluster(Path(registry.storage_path).parent, manual_pipeline, name="manual_cross_check_18")
    manual_registry = VideoAssetRegistry(Path(registry.storage_path).with_name("manual_cross_check_18_videos.json"))
    manual_record = manual_registry.generate_and_register(
        classification=manual_pipeline["classification"], selection=manual_pipeline["selection"],
        facts=manual_pipeline["facts"], asset=manual_pipeline["asset"], cluster=manual_cluster,
    )
    assert manual_record.video_asset_id == record.video_asset_id


def test_generate_from_live_chain_unknown_cluster_id_raises_lineage_error(
    registry, demand_signal_registry, knowledge_store, live_cluster
):
    cluster_registry, _cluster = live_cluster
    with pytest.raises(LineageError):
        registry.generate_and_register_from_live_chain(
            cluster_id="cluster_never_registered", target_id="tgt_boiler_repair_blackheath",
            signal_id="sig_node18_live", demand_signal_registry=demand_signal_registry,
            cluster_registry=cluster_registry, knowledge_store=knowledge_store,
        )


def test_generate_from_live_chain_unknown_signal_id_raises_lineage_error(
    registry, demand_signal_registry, knowledge_store, live_cluster
):
    cluster_registry, cluster = live_cluster
    with pytest.raises(LineageError):
        registry.generate_and_register_from_live_chain(
            cluster_id=cluster.cluster_id, target_id="tgt_boiler_repair_blackheath",
            signal_id="sig_never_registered", demand_signal_registry=demand_signal_registry,
            cluster_registry=cluster_registry, knowledge_store=knowledge_store,
        )


def test_generate_from_live_chain_no_facts_raises_lineage_error(registry, demand_signal_registry, live_cluster):
    cluster_registry, cluster = live_cluster
    empty_knowledge_store = CanonicalKnowledgeStore()
    with pytest.raises(LineageError):
        registry.generate_and_register_from_live_chain(
            cluster_id=cluster.cluster_id, target_id="tgt_boiler_repair_blackheath",
            signal_id="sig_node18_live", demand_signal_registry=demand_signal_registry,
            cluster_registry=cluster_registry, knowledge_store=empty_knowledge_store,
        )


def test_generate_from_live_chain_makes_no_network_call(
    registry, demand_signal_registry, knowledge_store, live_cluster, monkeypatch
):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 18 live-chain generation must not open any network socket")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    cluster_registry, cluster = live_cluster
    record = registry.generate_and_register_from_live_chain(
        cluster_id=cluster.cluster_id, target_id="tgt_boiler_repair_blackheath", signal_id="sig_node18_live",
        demand_signal_registry=demand_signal_registry, cluster_registry=cluster_registry, knowledge_store=knowledge_store,
    )
    assert record.video_asset_id.startswith("vid_")


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, pipeline, cluster, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 18 must not open any network socket or perform live rendering/upload")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    assert record.external_action is False


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(tmp_path, pipeline, cluster):
    storage_path = tmp_path / "node_18_regression.json"
    registry = VideoAssetRegistry(storage_path)

    record = registry.generate_and_register(
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    registry.generate_and_register(  # idempotent
        classification=pipeline["classification"], selection=pipeline["selection"],
        facts=pipeline["facts"], asset=pipeline["asset"], cluster=cluster,
    )
    assert len(registry.list()) == 1

    fetched = registry.get(record.video_asset_id)
    assert fetched.video_asset_id == record.video_asset_id

    with pytest.raises(ValidationError):
        tampered_asset = pipeline["asset"].to_dict()
        tampered_asset["safety_disclaimer"] = ""
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=tampered_asset, cluster=cluster,
        )

    with pytest.raises(LineageError):
        tampered_asset = pipeline["asset"].to_dict()
        tampered_asset["classification_id"] = "cls_tampered_regression"
        registry.generate_and_register(
            classification=pipeline["classification"], selection=pipeline["selection"],
            facts=pipeline["facts"], asset=tampered_asset, cluster=cluster,
        )

    assert registry.get("vid_nonexistent") is None
