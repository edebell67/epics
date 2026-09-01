# epics/ep_050_distribution_engine/implementation/node_15/test_campaign_cluster_generation.py
# EP050 Node 15 — Campaign / Cluster Generation test suite.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds coverage for generate_and_register_from_live_signals() (real Node05
# signals through the real Node11-14 chain producing an identical cluster_id to the manual path,
# empty-target lineage error, idempotency, no-network-call assertion).
# v1.0.0 · 2026-08-17 · Initial unit/contract/negative/boundary/determinism/idempotency/conflict/
# persistence/no-network/regression suite for Node 15.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no live data collection, no production datastore, no external side effect.
# Member bundles are built by calling the REAL Node 11-14 functions (not mocked).

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
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from intent_classification import classify_demand_signal  # noqa: E402
from opportunity_scoring import score_demand_opportunity  # noqa: E402
from demand_path_discovery import discover_demand_path  # noqa: E402
from channel_placement_selection import select_channel_placements  # noqa: E402

from campaign_cluster_generation import (
    CampaignClusterRegistry,
    ConflictError,
    LineageError,
    ValidationError,
)

TROUBLESHOOTING_QUERY = "boiler pressure dropped to zero no hot water"
INFORMATIONAL_QUERY = "general information about home heating systems and options"

CUSTOM_SINGLE_CANDIDATE = [
    {
        "channel_name": "paid_search",
        "placement_type": "google_search_exact_match",
        "raw_scores": {"audience_match": 0.99, "intent_relevance": 0.99, "format_viability": 0.99, "cost_efficiency": 0.99},
        "recommended_format": "callout_extension_ad_24_7_emergency",
        "rationale": "Test-only forced channel override to prove cross-cluster channel boundary.",
    }
]


def _build_member(
    signal_id: str,
    raw_query: str,
    target_id: str = "tgt_boiler_repair_blackheath",
    locality: str = "Blackheath",
    region: str = "London",
    country: str = "UK",
    candidate_channels=None,
) -> dict:
    payload = {
        "signal_id": signal_id,
        "target_id": target_id,
        "raw_query": raw_query,
        "topic": "boiler_pressure_loss",
        "source_type": "manual_curation",
        "observed_at": "2026-08-17T00:00:00+00:00",
        "geography": {"locality": locality, "region": region, "country": country},
        "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
    }
    classification = classify_demand_signal(payload)
    opportunity = score_demand_opportunity(classification)
    path = discover_demand_path(opportunity)
    selection = select_channel_placements(path, candidate_channels=candidate_channels)
    return {
        "classification": classification.to_dict(),
        "opportunity": opportunity.to_dict(),
        "path": path.to_dict(),
        "selection": selection.to_dict(),
    }


@pytest.fixture
def registry(tmp_path):
    return CampaignClusterRegistry(tmp_path / "node_15_clusters.json")


# --- One-item and multi-item clustering --------------------------------------

def test_single_member_forms_one_item_cluster(registry):
    member = _build_member("sig_solo", TROUBLESHOOTING_QUERY)
    clusters = registry.generate_and_register([member])
    assert len(clusters) == 1
    assert clusters[0].member_count == 1
    assert clusters[0].members[0].signal_id == "sig_solo"


def test_two_members_with_same_traits_merge_into_one_cluster(registry):
    member_a = _build_member("sig_a", TROUBLESHOOTING_QUERY)
    member_b = _build_member("sig_b", TROUBLESHOOTING_QUERY, target_id="tgt_boiler_repair_blackheath_2")
    clusters = registry.generate_and_register([member_a, member_b])
    assert len(clusters) == 1
    assert clusters[0].member_count == 2
    signal_ids = {m.signal_id for m in clusters[0].members}
    assert signal_ids == {"sig_a", "sig_b"}


# --- Boundary: clustering respects all three trait dimensions ----------------

def test_members_differing_by_locality_form_separate_clusters(registry):
    member_a = _build_member("sig_locality_a", TROUBLESHOOTING_QUERY, locality="Blackheath")
    member_b = _build_member("sig_locality_b", TROUBLESHOOTING_QUERY, locality="Greenwich")
    clusters = registry.generate_and_register([member_a, member_b])
    assert len(clusters) == 2


def test_members_differing_by_primary_intent_form_separate_clusters(registry):
    member_a = _build_member("sig_intent_a", TROUBLESHOOTING_QUERY)
    member_b = _build_member("sig_intent_b", INFORMATIONAL_QUERY)
    clusters = registry.generate_and_register([member_a, member_b])
    assert len(clusters) == 2
    themes = {c.theme.split("_")[0] for c in clusters}
    assert themes == {"troubleshooting", "informational"}


def test_members_differing_by_primary_channel_form_separate_clusters(registry):
    member_a = _build_member("sig_channel_a", TROUBLESHOOTING_QUERY)
    member_b = _build_member("sig_channel_b", TROUBLESHOOTING_QUERY, candidate_channels=CUSTOM_SINGLE_CANDIDATE)
    clusters = registry.generate_and_register([member_a, member_b])
    assert len(clusters) == 2
    channels = {c.shared_traits["primary_channel"] for c in clusters}
    assert channels == {"local_search_maps", "paid_search"}


# --- Negative / validation ----------------------------------------------------

def test_empty_members_list_is_rejected(registry):
    with pytest.raises(ValidationError):
        registry.generate_and_register([])


def test_duplicate_signal_id_within_same_run_is_rejected(registry):
    member = _build_member("sig_dup", TROUBLESHOOTING_QUERY)
    with pytest.raises(ValidationError):
        registry.generate_and_register([member, member])


def test_missing_lineage_bundle_key_is_rejected(registry):
    member = _build_member("sig_missing_key", TROUBLESHOOTING_QUERY)
    del member["path"]
    with pytest.raises(LineageError):
        registry.generate_and_register([member])


def test_mismatched_lineage_across_subrecords_is_rejected(registry):
    member = _build_member("sig_mismatch", TROUBLESHOOTING_QUERY)
    member["opportunity"] = dict(member["opportunity"], classification_id="cls_tampered_mismatch")
    with pytest.raises(LineageError):
        registry.generate_and_register([member])


def test_demand_opportunity_score_out_of_range_is_rejected(registry):
    member = _build_member("sig_bad_score_high", TROUBLESHOOTING_QUERY)
    member["opportunity"] = dict(member["opportunity"], demand_opportunity_score=150.0)
    with pytest.raises(ValidationError):
        registry.generate_and_register([member])


def test_demand_opportunity_score_non_numeric_is_rejected(registry):
    member = _build_member("sig_bad_score_type", TROUBLESHOOTING_QUERY)
    member["opportunity"] = dict(member["opportunity"], demand_opportunity_score="high")
    with pytest.raises(ValidationError):
        registry.generate_and_register([member])


# --- Prohibited PII rejection (caller-supplied campaign_context) -------------

def test_campaign_context_email_is_rejected(registry):
    member = _build_member("sig_pii_email", TROUBLESHOOTING_QUERY)
    with pytest.raises(ValidationError, match="email"):
        registry.generate_and_register([member], campaign_context="Contact jane.doe@example.com for approval")


def test_campaign_context_phone_is_rejected(registry):
    member = _build_member("sig_pii_phone", TROUBLESHOOTING_QUERY)
    with pytest.raises(ValidationError, match="phone"):
        registry.generate_and_register([member], campaign_context="Call 020 7946 0958 to approve")


# --- Determinism ---------------------------------------------------------------

def test_determinism_same_members_produce_same_cluster_id_across_registries(tmp_path):
    member_a = _build_member("sig_det_a", TROUBLESHOOTING_QUERY)
    member_b = _build_member("sig_det_b", TROUBLESHOOTING_QUERY, target_id="tgt_boiler_repair_blackheath_2")

    registry_1 = CampaignClusterRegistry(tmp_path / "run1.json")
    clusters_1 = registry_1.generate_and_register([member_a, member_b])

    registry_2 = CampaignClusterRegistry(tmp_path / "run2.json")
    clusters_2 = registry_2.generate_and_register([member_a, member_b])

    assert clusters_1[0].cluster_id == clusters_2[0].cluster_id
    assert clusters_1[0].cluster_score == clusters_2[0].cluster_score


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_rerun_is_idempotent_and_does_not_duplicate(registry):
    member = _build_member("sig_idempotent", TROUBLESHOOTING_QUERY)
    first = registry.generate_and_register([member])
    second = registry.generate_and_register([member])
    assert first[0].cluster_id == second[0].cluster_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_stored_cluster_is_rejected(tmp_path):
    # Simulates a legitimate persisted-state conflict (e.g. concurrent external edit) by
    # tampering the stored record directly, since cluster_id is a pure function of member
    # content and cannot be forced to conflict through the public API alone.
    storage_path = tmp_path / "node_15_conflict.json"
    registry = CampaignClusterRegistry(storage_path)
    member = _build_member("sig_conflict", TROUBLESHOOTING_QUERY)
    clusters = registry.generate_and_register([member])
    cluster_id = clusters[0].cluster_id

    data = json.loads(storage_path.read_text(encoding="utf-8"))
    data[cluster_id]["cluster_score"] = 999.0
    storage_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ConflictError):
        registry.generate_and_register([member])


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(tmp_path):
    storage_path = tmp_path / "node_15_persist.json"
    member = _build_member("sig_persist", TROUBLESHOOTING_QUERY)

    registry_a = CampaignClusterRegistry(storage_path)
    registered = registry_a.generate_and_register([member])[0]

    registry_b = CampaignClusterRegistry(storage_path)
    fetched = registry_b.get(registered.cluster_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 15 clustering must not open any network socket or perform live data collection")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    member = _build_member("sig_no_network", TROUBLESHOOTING_QUERY)
    clusters = registry.generate_and_register([member])
    assert clusters[0].members[0].signal_id == "sig_no_network"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(tmp_path):
    storage_path = tmp_path / "node_15_regression.json"
    registry = CampaignClusterRegistry(storage_path)

    member_a = _build_member("sig_reg_a", TROUBLESHOOTING_QUERY)
    member_b = _build_member("sig_reg_b", TROUBLESHOOTING_QUERY, target_id="tgt_boiler_repair_blackheath_2")
    member_c = _build_member("sig_reg_c", INFORMATIONAL_QUERY)

    clusters = registry.generate_and_register([member_a, member_b, member_c])
    assert len(clusters) == 2  # troubleshooting cluster (2 members) + informational cluster (1 member)
    assert len(registry.list()) == 2

    registry.generate_and_register([member_a, member_b, member_c])  # idempotent rerun
    assert len(registry.list()) == 2

    with pytest.raises(ValidationError):
        registry.generate_and_register([member_a, member_a])

    with pytest.raises(LineageError):
        broken = dict(member_a)
        del broken["selection"]
        registry.generate_and_register([broken])

    with pytest.raises(ValidationError):
        registry.generate_and_register([member_a], campaign_context="reach me at jane.doe@example.com")

    assert registry.get("cluster_nonexistent") is None


# --- Automated live ingestion (generate_and_register_from_live_signals) ----

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


def _register_signal(demand_signal_registry, signal_id: str, raw_query: str) -> None:
    demand_signal_registry.register(
        signal_id=signal_id, target_id="tgt_boiler_repair_blackheath", raw_query=raw_query,
        topic="boiler_pressure_loss", source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
    )


def test_generate_from_live_signals_builds_members_without_manual_assembly(registry, demand_signal_registry):
    _register_signal(demand_signal_registry, "sig_live_a", TROUBLESHOOTING_QUERY)
    _register_signal(demand_signal_registry, "sig_live_b", TROUBLESHOOTING_QUERY)

    clusters = registry.generate_and_register_from_live_signals("tgt_boiler_repair_blackheath", demand_signal_registry)

    assert len(clusters) == 1
    assert clusters[0].member_count == 2
    signal_ids = {m.signal_id for m in clusters[0].members}
    assert signal_ids == {"sig_live_a", "sig_live_b"}
    # Cross-check against the manual path: same real signals through the same real Node11-14
    # chain must produce an identical cluster_id (same rule, same deterministic hash).
    manual_member_a = _build_member("sig_live_a", TROUBLESHOOTING_QUERY)
    manual_member_b = _build_member("sig_live_b", TROUBLESHOOTING_QUERY)
    manual_clusters = CampaignClusterRegistry(registry.storage_path.with_name("manual_cross_check.json"))
    manual_result = manual_clusters.generate_and_register([manual_member_a, manual_member_b])
    assert manual_result[0].cluster_id == clusters[0].cluster_id


def test_generate_from_live_signals_target_with_no_signals_raises_lineage_error(registry, demand_signal_registry):
    with pytest.raises(LineageError):
        registry.generate_and_register_from_live_signals("tgt_boiler_repair_blackheath", demand_signal_registry)
    assert registry.list() == []


def test_generate_from_live_signals_is_idempotent(registry, demand_signal_registry):
    _register_signal(demand_signal_registry, "sig_idem", TROUBLESHOOTING_QUERY)
    first = registry.generate_and_register_from_live_signals("tgt_boiler_repair_blackheath", demand_signal_registry)
    second = registry.generate_and_register_from_live_signals("tgt_boiler_repair_blackheath", demand_signal_registry)
    assert first[0].cluster_id == second[0].cluster_id
    assert len(registry.list()) == 1


def test_generate_from_live_signals_makes_no_network_call(registry, demand_signal_registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 15 live-signal clustering must not open any network socket")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    _register_signal(demand_signal_registry, "sig_nonet", TROUBLESHOOTING_QUERY)
    clusters = registry.generate_and_register_from_live_signals("tgt_boiler_repair_blackheath", demand_signal_registry)
    assert len(clusters) == 1
