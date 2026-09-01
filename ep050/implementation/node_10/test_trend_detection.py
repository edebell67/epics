# epics/ep_050_distribution_engine/implementation/node_10/test_trend_detection.py
# EP050 Node 10 — Trend Detection test suite.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds coverage for register_from_live_aggregation() (real counting from
#                        seeded Node05 signals across baseline/current windows, empty-window
#                        fail-closed via the existing minimum-sample-count check, no-network-call
#                        assertion).
# v1.0.0 · 2026-08-17 · Initial unit/contract/integration/regression suite for Node 10.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no live monitoring/browsing, no production datastore, no external side effect.

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_02"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_03"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_04"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_05"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_06"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_07"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_08"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_09"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from social_video_discovery import SocialVideoSignalRegistry  # noqa: E402
from competitor_intelligence import CompetitorSignalRegistry  # noqa: E402
from community_intelligence import CommunitySignalRegistry  # noqa: E402

from trend_detection import (
    TrendSignalRegistry,
    ConflictError,
    UnknownTargetError,
    ValidationError,
)

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
SYNTHETIC_SIGNAL = dict(
    signal_id="sig_seed_for_node10", raw_query="boiler pressure dropped to zero no hot water",
    topic="boiler_pressure_loss", source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
)
SYNTHETIC_QUESTION = dict(
    question_id="q_seed_for_node10", question_text="Why does my boiler pressure keep dropping overnight?",
    topic="boiler_pressure_loss", pain_point="Recurring pressure loss with no obvious cause",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    intent_cues=["troubleshooting"], source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
    evidence="Manually curated from the EP050 master spec's worked example.",
)
SYNTHETIC_SOCIAL_VIDEO = dict(
    signal_id="sv_seed_for_node10", platform="youtube", format="short_video",
    topic="boiler_pressure_loss", theme="overnight_pressure_drop_diagnosis",
    intent_cues=["troubleshooting"], geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    observed_metrics={"synthetic_views": 4200}, observed_at="2026-08-17T00:00:00+00:00",
    source_type="manual_curation", evidence="Manually curated theme.",
)
SYNTHETIC_COMPETITOR = dict(
    signal_id="cp_seed_for_node10", competitor_name="Synthetic Rival Plumbing Co", channel="google_search",
    topic="boiler_pressure_loss", query="boiler pressure loss repair blackheath",
    attention_source="organic_search", relevance_score=0.72, competition_indicator="medium",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    observed_at="2026-08-17T00:00:00+00:00", source_type="manual_curation",
    evidence="Manually curated competitor observation consistent with the EP050 master spec's worked example.",
)
SYNTHETIC_COMMUNITY = dict(
    signal_id="cm_seed_for_node10", community_source="r/DIYUK", topic="boiler_pressure_loss",
    question="Boiler pressure keeps dropping overnight, anyone else had this?",
    pain_point="Recurring pressure loss with no obvious cause, worried about a hidden leak",
    intent_cues=["troubleshooting", "seeking_recommendation"],
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    observed_metrics={"synthetic_upvotes": 58, "synthetic_comments": 23},
    observed_at="2026-08-17T00:00:00+00:00", source_type="manual_curation",
    evidence="Manually curated community thread theme consistent with the EP050 master spec's worked example.",
)


@pytest.fixture
def target_registry(tmp_path):
    registry = TargetRegistry(tmp_path / "node_01.json")
    registry.register(**SYNTHETIC_TARGET)
    return registry


@pytest.fixture
def product_registry(tmp_path, target_registry):
    registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_PRODUCT)
    return registry


@pytest.fixture
def audience_registry(tmp_path, target_registry, product_registry):
    registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_SEGMENT)
    return registry


@pytest.fixture
def conversion_registry(tmp_path, target_registry, product_registry, audience_registry):
    registry = ConversionDefinitionRegistry(tmp_path / "node_04.json", target_registry, product_registry, audience_registry)
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_CONVERSION)
    return registry


@pytest.fixture
def demand_signal_registry(tmp_path, target_registry, product_registry, audience_registry, conversion_registry):
    registry = DemandSignalRegistry(tmp_path / "node_05.json", target_registry, product_registry, audience_registry, conversion_registry)
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_SIGNAL)
    return registry


@pytest.fixture
def question_registry(tmp_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry):
    registry = QuestionRegistry(
        tmp_path / "node_06.json", target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry
    )
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_QUESTION)
    return registry


@pytest.fixture
def social_video_registry(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry, question_registry
):
    registry = SocialVideoSignalRegistry(
        tmp_path / "node_07.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry,
    )
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_SOCIAL_VIDEO)
    return registry


@pytest.fixture
def competitor_registry(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry,
):
    registry = CompetitorSignalRegistry(
        tmp_path / "node_08.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry,
    )
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_COMPETITOR)
    return registry


@pytest.fixture
def community_registry(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry, competitor_registry,
):
    registry = CommunitySignalRegistry(
        tmp_path / "node_09.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry, competitor_registry,
    )
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_COMMUNITY)
    return registry


@pytest.fixture
def registry(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry, competitor_registry, community_registry,
):
    return TrendSignalRegistry(
        tmp_path / "node_10_signals.json",
        target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry, competitor_registry, community_registry,
    )


def _payload(trend_id: str, target_id: str = "tgt_boiler_repair_blackheath") -> dict:
    return dict(
        trend_id=trend_id,
        target_id=target_id,
        topic="boiler_pressure_loss",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        window={
            "baseline_start": "2026-08-01T00:00:00+00:00",
            "baseline_end": "2026-08-08T00:00:00+00:00",
            "current_start": "2026-08-08T00:00:00+00:00",
            "current_end": "2026-08-15T00:00:00+00:00",
        },
        metric_name="demand_signal_count",
        baseline_value=20.0,
        baseline_sample_count=10,
        current_value=32.0,
        current_sample_count=12,
        source_type="manual_curation",
        evidence="Manually curated trend observation consistent with the EP050 master spec's worked example.",
        metadata={"note": "synthetic fixture only"},
    )


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**_payload("trend_node10_test_01"))
    assert record.trend_id == "trend_node10_test_01"
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.recorded_at


def test_metadata_defaults_to_empty_dict_when_omitted(registry):
    payload = _payload("trend_node10_test_02")
    del payload["metadata"]
    record = registry.register(**payload)
    assert record.metadata == {}


# --- Derived trend computation ------------------------------------------------

def test_velocity_direction_spike_and_confidence_computed_correctly(registry):
    record = registry.register(**_payload("trend_computed_up"))
    assert record.velocity == pytest.approx(0.6)
    assert record.direction == "up"
    assert record.spike_flag is True
    assert record.confidence == pytest.approx(1.0)


def test_downward_trend_direction_computed(registry):
    payload = _payload("trend_computed_down")
    payload["baseline_value"] = 20.0
    payload["current_value"] = 12.0
    record = registry.register(**payload)
    assert record.velocity == pytest.approx(-0.4)
    assert record.direction == "down"


def test_flat_trend_within_deadband_is_not_up_or_down(registry):
    payload = _payload("trend_computed_flat")
    payload["baseline_value"] = 20.0
    payload["current_value"] = 20.1
    record = registry.register(**payload)
    assert record.direction == "flat"
    assert record.spike_flag is False


def test_confidence_scales_with_minimum_sample_count(registry):
    payload = _payload("trend_low_confidence")
    payload["baseline_sample_count"] = 3
    payload["current_sample_count"] = 5
    record = registry.register(**payload)
    assert record.confidence == pytest.approx(0.3)


def test_zero_baseline_value_is_rejected(registry):
    payload = _payload("trend_zero_baseline")
    payload["baseline_value"] = 0.0
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Node01-09->10 nine-way contract/integration test --------------------------

def test_unregistered_target_is_rejected_fail_closed(registry):
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("trend_x", target_id="tgt_never_registered"))


def test_target_missing_node_09_is_rejected_fail_closed(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry, competitor_registry,
):
    empty_community_registry = CommunitySignalRegistry(
        tmp_path / "node_09_empty.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry, competitor_registry,
    )
    registry = TrendSignalRegistry(
        tmp_path / "node_10.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry,
        competitor_registry, empty_community_registry,
    )
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("trend_x"))


def test_registered_target_with_all_nine_real_upstream_registries_is_accepted(tmp_path):
    target_registry = TargetRegistry(tmp_path / "node_01.json")
    target = target_registry.register(**SYNTHETIC_TARGET)
    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    product_registry.register(target_id=target.target_id, **SYNTHETIC_PRODUCT)
    audience_registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    audience_registry.register(target_id=target.target_id, **SYNTHETIC_SEGMENT)
    conversion_registry = ConversionDefinitionRegistry(tmp_path / "node_04.json", target_registry, product_registry, audience_registry)
    conversion_registry.register(target_id=target.target_id, **SYNTHETIC_CONVERSION)
    demand_signal_registry = DemandSignalRegistry(tmp_path / "node_05.json", target_registry, product_registry, audience_registry, conversion_registry)
    demand_signal_registry.register(target_id=target.target_id, **SYNTHETIC_SIGNAL)
    question_registry = QuestionRegistry(
        tmp_path / "node_06.json", target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry
    )
    question_registry.register(target_id=target.target_id, **SYNTHETIC_QUESTION)
    social_video_registry = SocialVideoSignalRegistry(
        tmp_path / "node_07.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry,
    )
    social_video_registry.register(target_id=target.target_id, **SYNTHETIC_SOCIAL_VIDEO)
    competitor_registry = CompetitorSignalRegistry(
        tmp_path / "node_08.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry,
    )
    competitor_registry.register(target_id=target.target_id, **SYNTHETIC_COMPETITOR)
    community_registry = CommunitySignalRegistry(
        tmp_path / "node_09.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry, competitor_registry,
    )
    community_registry.register(target_id=target.target_id, **SYNTHETIC_COMMUNITY)
    trend_registry = TrendSignalRegistry(
        tmp_path / "node_10.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry,
        competitor_registry, community_registry,
    )
    record = trend_registry.register(**_payload("trend_full_chain", target_id=target.target_id))
    assert record.target_id == target.target_id


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize(
    "missing_field",
    ["trend_id", "target_id", "topic", "geography", "window", "metric_name", "baseline_value",
     "baseline_sample_count", "current_value", "current_sample_count", "source_type", "evidence"],
)
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = _payload("trend_missing_field")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid enum/type failures ----------------------------------------------

def test_source_type_outside_offline_mvp_boundary_is_rejected(registry):
    payload = _payload("trend_bad_source")
    payload["source_type"] = "live_api"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_geography_wrong_type_is_rejected(registry):
    payload = _payload("trend_bad_geo")
    payload["geography"] = "Blackheath, London, UK"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_window_non_monotonic_is_rejected(registry):
    payload = _payload("trend_bad_window")
    payload["window"] = {
        "baseline_start": "2026-08-08T00:00:00+00:00",
        "baseline_end": "2026-08-01T00:00:00+00:00",
        "current_start": "2026-08-08T00:00:00+00:00",
        "current_end": "2026-08-15T00:00:00+00:00",
    }
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_window_overlapping_baseline_and_current_is_rejected(registry):
    payload = _payload("trend_overlap_window")
    payload["window"] = {
        "baseline_start": "2026-08-01T00:00:00+00:00",
        "baseline_end": "2026-08-10T00:00:00+00:00",
        "current_start": "2026-08-08T00:00:00+00:00",
        "current_end": "2026-08-15T00:00:00+00:00",
    }
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_window_missing_key_is_rejected(registry):
    payload = _payload("trend_window_missing_key")
    payload["window"] = {"baseline_start": "2026-08-01T00:00:00+00:00"}
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_baseline_value_negative_is_rejected(registry):
    payload = _payload("trend_negative_baseline")
    payload["baseline_value"] = -5.0
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_current_value_non_numeric_is_rejected(registry):
    payload = _payload("trend_bad_current_type")
    payload["current_value"] = "thirty-two"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_sample_count_below_minimum_is_rejected(registry):
    payload = _payload("trend_insufficient_samples")
    payload["baseline_sample_count"] = 1
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_sample_count_non_integer_is_rejected(registry):
    payload = _payload("trend_bad_sample_type")
    payload["current_sample_count"] = 5.5
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Prohibited PII rejection -------------------------------------------------

def test_email_in_topic_is_rejected(registry):
    payload = _payload("trend_pii_email")
    payload["topic"] = "Email us at jane.doe@example.com about boiler pressure"
    with pytest.raises(ValidationError, match="email"):
        registry.register(**payload)


def test_phone_in_metric_name_is_rejected(registry):
    payload = _payload("trend_pii_phone")
    payload["metric_name"] = "call 020 7946 0958 demand count"
    with pytest.raises(ValidationError, match="phone"):
        registry.register(**payload)


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_reregistration_is_idempotent_and_does_not_duplicate(registry):
    first = registry.register(**_payload("trend_idempotent"))
    second = registry.register(**_payload("trend_idempotent"))
    assert first.trend_id == second.trend_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_duplicate_same_trend_different_content_is_rejected(registry):
    registry.register(**_payload("trend_conflict"))
    conflicting = _payload("trend_conflict")
    conflicting["current_value"] = 999.0
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    stored = registry.get("trend_conflict")
    assert stored.current_value == pytest.approx(32.0)


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry, competitor_registry, community_registry,
):
    storage_path = tmp_path / "node_10_signals.json"
    registry_a = TrendSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry, competitor_registry, community_registry,
    )
    registered = registry_a.register(**_payload("trend_persist"))

    registry_b = TrendSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry, competitor_registry, community_registry,
    )
    fetched = registry_b.get(registered.trend_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 10 registration must not open any network socket or perform live monitoring")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**_payload("trend_no_network"))
    assert record.trend_id == "trend_no_network"


# --- Automated live ingestion (register_from_live_aggregation) -------------

_AGGREGATION_WINDOW = {
    "baseline_start": "2026-08-01T00:00:00+00:00",
    "baseline_end": "2026-08-08T00:00:00+00:00",
    "current_start": "2026-08-08T00:00:00+00:00",
    "current_end": "2026-08-15T00:00:00+00:00",
}


def test_register_from_live_aggregation_counts_real_upstream_signals(registry, demand_signal_registry):
    # The shared seed fixtures all sit at observed_at=2026-08-17, outside this window, so the
    # windows start clean; add real Node 05 signals inside each half of the window.
    for i in range(3):
        demand_signal_registry.register(
            signal_id=f"sig_baseline_{i}", target_id="tgt_boiler_repair_blackheath",
            raw_query=f"boiler pressure baseline query {i}", topic="boiler_pressure_loss",
            source_type="manual_curation", observed_at="2026-08-02T00:00:00+00:00",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
            service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        )
    for i in range(5):
        demand_signal_registry.register(
            signal_id=f"sig_current_{i}", target_id="tgt_boiler_repair_blackheath",
            raw_query=f"boiler pressure current query {i}", topic="boiler_pressure_loss",
            source_type="manual_curation", observed_at="2026-08-10T00:00:00+00:00",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
            service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        )

    record = registry.register_from_live_aggregation(
        trend_id="trend_auto_01",
        target_id="tgt_boiler_repair_blackheath",
        topic="boiler_pressure_loss",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        window=_AGGREGATION_WINDOW,
    )

    assert record.source_type == "auto_aggregated"
    assert record.baseline_sample_count == 3
    assert record.current_sample_count == 5
    assert record.baseline_value == 3.0
    assert record.current_value == 5.0
    assert record.direction == "up"
    receipt = record.metadata["aggregation_receipt"]
    assert receipt["baseline_records_counted"] == 3
    assert receipt["current_records_counted"] == 5
    assert receipt["upstream_node_count"] == 5


def test_register_from_live_aggregation_with_no_real_signals_in_window_fails_closed(registry):
    # No extra signals seeded inside _AGGREGATION_WINDOW: baseline/current counts are both 0,
    # below MIN_SAMPLE_COUNT -- must reject exactly as a manually-entered under-sampled trend would.
    with pytest.raises(ValidationError):
        registry.register_from_live_aggregation(
            trend_id="trend_auto_empty",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
            window=_AGGREGATION_WINDOW,
        )
    assert registry.get("trend_auto_empty") is None


def test_register_from_live_aggregation_makes_no_network_call(registry, demand_signal_registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 10 aggregation must never open a network socket")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    for i in range(3):
        demand_signal_registry.register(
            signal_id=f"sig_nonet_{i}", target_id="tgt_boiler_repair_blackheath",
            raw_query=f"boiler pressure query {i}", topic="boiler_pressure_loss",
            source_type="manual_curation", observed_at="2026-08-02T00:00:00+00:00",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
            service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        )
        demand_signal_registry.register(
            signal_id=f"sig_nonet_cur_{i}", target_id="tgt_boiler_repair_blackheath",
            raw_query=f"boiler pressure current query {i}", topic="boiler_pressure_loss",
            source_type="manual_curation", observed_at="2026-08-10T00:00:00+00:00",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
            service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        )
    record = registry.register_from_live_aggregation(
        trend_id="trend_auto_no_network",
        target_id="tgt_boiler_repair_blackheath",
        topic="boiler_pressure_loss",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        window=_AGGREGATION_WINDOW,
    )
    assert record.trend_id == "trend_auto_no_network"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry, competitor_registry, community_registry,
):
    storage_path = tmp_path / "node_10_signals.json"
    registry = TrendSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry, competitor_registry, community_registry,
    )

    record = registry.register(**_payload("trend_regression"))
    registry.register(**_payload("trend_regression"))  # idempotent
    assert len(registry.list()) == 1
    assert len(registry.list_for_target("tgt_boiler_repair_blackheath")) == 1

    fetched = registry.get(record.trend_id)
    assert fetched.trend_id == record.trend_id

    with pytest.raises(ConflictError):
        conflicting = _payload("trend_regression")
        conflicting["current_value"] = 1.0
        registry.register(**conflicting)

    with pytest.raises(ValidationError):
        registry.register(**dict(_payload("trend_regression_2"), source_type="live_api"))

    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("trend_x", target_id="tgt_never_registered"))

    assert registry.get("trend_nonexistent") is None
