# epics/ep_050_distribution_engine/implementation/node_18/test_alternate_asset_factory.py
# EP050 Node 18 (sibling) — Alternate Asset Factory test suite.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-19 · Initial suite.
#
# All tests run fully offline against temp fixture files (pytest tmp_path). Every upstream record
# is built by calling the REAL Node 11-17 functions (not mocked) -- same convention as
# test_video_asset_factory.py.

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_11"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_12"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_13"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_14"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_15"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_16"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_17"))
from intent_classification import classify_demand_signal  # noqa: E402
from opportunity_scoring import score_demand_opportunity  # noqa: E402
from demand_path_discovery import discover_demand_path  # noqa: E402
from channel_placement_selection import select_channel_placements  # noqa: E402
from campaign_cluster_generation import CampaignClusterRegistry  # noqa: E402
from canonical_knowledge_store import CanonicalKnowledgeStore  # noqa: E402
from content_utility_factory import generate_asset_payload  # noqa: E402

from alternate_asset_factory import (
    ALLOWED_FORMATS,
    FORMATS_REQUIRING_HUMAN_REVIEW,
    AlternateAssetRegistry,
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
    fact = facts_store.register_fact(
        target_id=target_id,
        topic="boiler_pressure",
        claim="Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
        verification_source="manufacturer_manual_fixture",
    )
    facts = [fact]
    asset = generate_asset_payload(selection, facts=facts, intent_input=classification)

    return {"classification": classification, "opportunity": opportunity, "path": path, "selection": selection, "facts": facts, "asset": asset}


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


def _asset_with_format(pipeline: dict, asset_format: str) -> dict:
    """Real lineage/content from the pipeline fixture, with only metadata.format overridden --
    exercises each format builder without depending on which format the real ranking algorithm
    happens to pick top for this particular fixture query."""
    asset_d = pipeline["asset"].to_dict()
    asset_d["metadata"] = dict(asset_d["metadata"])
    asset_d["metadata"]["format"] = asset_format
    return asset_d


@pytest.fixture
def pipeline(tmp_path):
    return _build_pipeline("sig_alt18_base")


@pytest.fixture
def cluster(tmp_path, pipeline):
    return _build_cluster(tmp_path, pipeline)


@pytest.fixture
def registry(tmp_path):
    return AlternateAssetRegistry(tmp_path / "node_18_alternate_assets.json")


# --- Positive registration, one per real format --------------------------------

def test_listing_format_registers_with_real_lineage(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "verified_local_listing_with_emergency_hours")
    record = registry.generate_and_register(asset=asset, cluster=cluster)
    assert record.format == "verified_local_listing_with_emergency_hours"
    assert record.content["headline"] == asset["title"]
    assert record.content["summary"] == asset["body_content"]
    assert record.requires_human_review is False
    assert record.external_action is False
    assert record.target_id == asset["target_id"]


def test_guide_format_splits_body_into_steps(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    record = registry.generate_and_register(asset=asset, cluster=cluster)
    assert record.format == "step_by_step_troubleshooting_guide"
    assert len(record.content["steps"]) >= 1
    assert record.content["steps"][0]["step_number"] == 1
    assert record.requires_human_review is False


def test_ad_format_truncates_to_real_length_limits(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "callout_extension_ad_24_7_emergency")
    record = registry.generate_and_register(asset=asset, cluster=cluster)
    assert record.format == "callout_extension_ad_24_7_emergency"
    assert len(record.content["headline"]) <= 30
    assert len(record.content["description"]) <= 90
    assert record.content["callout_extensions"] == [asset["call_to_action"]]


def test_community_post_format_requires_human_review(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "community_recommendation_post")
    record = registry.generate_and_register(asset=asset, cluster=cluster)
    assert record.format == "community_recommendation_post"
    assert record.content["body"] == asset["body_content"]
    assert "disclosure" in record.content
    assert record.requires_human_review is True  # the one format that IS gated


# --- Negative / fail-closed ------------------------------------------------------

def test_unknown_format_is_rejected(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "video_short_form")  # not one of the 4 real formats
    with pytest.raises(ValidationError):
        registry.generate_and_register(asset=asset, cluster=cluster)


def test_asset_not_a_cluster_member_is_rejected(registry, pipeline, tmp_path):
    other_pipeline = _build_pipeline("sig_alt18_other")
    other_cluster = _build_cluster(tmp_path, other_pipeline, name="other_cluster")
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    with pytest.raises(LineageError):
        registry.generate_and_register(asset=asset, cluster=other_cluster)


def test_external_action_not_false_is_rejected(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    asset["metadata"]["external_action"] = True
    with pytest.raises(ValidationError):
        registry.generate_and_register(asset=asset, cluster=cluster)


def test_missing_safety_disclaimer_is_rejected(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    asset["safety_disclaimer"] = ""
    with pytest.raises(ValidationError):
        registry.generate_and_register(asset=asset, cluster=cluster)


def test_missing_call_to_action_is_rejected(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    asset["call_to_action"] = ""
    with pytest.raises(ValidationError):
        registry.generate_and_register(asset=asset, cluster=cluster)


def test_missing_fact_ids_is_rejected(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    asset["fact_ids"] = []
    with pytest.raises(LineageError):
        registry.generate_and_register(asset=asset, cluster=cluster)


# --- Determinism / idempotency / conflict ----------------------------------------

def test_determinism_same_inputs_produce_same_alternate_asset_id(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    r1 = registry.generate_and_register(asset=asset, cluster=cluster)
    r2 = AlternateAssetRegistry(registry.storage_path).generate_and_register(asset=asset, cluster=cluster)
    assert r1.alternate_asset_id == r2.alternate_asset_id


def test_identical_rerun_is_idempotent(registry, pipeline, cluster):
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    r1 = registry.generate_and_register(asset=asset, cluster=cluster)
    r2 = registry.generate_and_register(asset=asset, cluster=cluster)
    assert r1.alternate_asset_id == r2.alternate_asset_id
    assert len(registry.list()) == 1


def test_conflicting_stored_record_is_rejected(tmp_path, pipeline, cluster):
    asset = _asset_with_format(pipeline, "step_by_step_troubleshooting_guide")
    registry_a = AlternateAssetRegistry(tmp_path / "shared.json")
    registry_a.generate_and_register(asset=asset, cluster=cluster)

    tampered = dict(registry_a._load())
    key = next(iter(tampered))
    tampered[key]["call_to_action"] = "A completely different CTA"
    registry_a._save(tampered)

    registry_b = AlternateAssetRegistry(tmp_path / "shared.json")
    with pytest.raises(ConflictError):
        registry_b.generate_and_register(asset=asset, cluster=cluster)


def test_persistence_round_trip_via_new_registry_instance(tmp_path, pipeline, cluster):
    asset = _asset_with_format(pipeline, "verified_local_listing_with_emergency_hours")
    original = AlternateAssetRegistry(tmp_path / "persist.json")
    record = original.generate_and_register(asset=asset, cluster=cluster)

    fresh = AlternateAssetRegistry(tmp_path / "persist.json")
    fetched = fresh.get(record.alternate_asset_id)
    assert fetched is not None
    assert fetched.to_dict() == record.to_dict()


def test_all_four_allowed_formats_are_covered_by_a_builder():
    from alternate_asset_factory import _FORMAT_BUILDERS
    assert set(ALLOWED_FORMATS) == set(_FORMAT_BUILDERS.keys())


def test_only_community_post_requires_human_review():
    assert FORMATS_REQUIRING_HUMAN_REVIEW == ("community_recommendation_post",)
