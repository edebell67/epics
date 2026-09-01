# epics/ep_050_distribution_engine/implementation/node_08/test_competitor_intelligence.py
# EP050 Node 08 — Competitor Intelligence test suite.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds coverage for register_from_live_source() (disabled-by-default with a
#                        blocked-socket assertion, mocked-fetch producing a verifiable record with
#                        the topic-keyword-normalization bug fixed, fetch-error propagation writing
#                        nothing).
# v1.0.0 · 2026-08-17 · Initial unit/contract/integration/regression suite for Node 08.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no live competitor research/browsing, no production datastore, no external side effect.

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
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from social_video_discovery import SocialVideoSignalRegistry  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from live_fetch import LiveFetchDisabledError, LiveFetchRequestError  # noqa: E402

import competitor_intelligence  # noqa: E402
from competitor_intelligence import (
    CompetitorSignalRegistry,
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
    signal_id="sig_seed_for_node08", raw_query="boiler pressure dropped to zero no hot water",
    topic="boiler_pressure_loss", source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
)
SYNTHETIC_QUESTION = dict(
    question_id="q_seed_for_node08", question_text="Why does my boiler pressure keep dropping overnight?",
    topic="boiler_pressure_loss", pain_point="Recurring pressure loss with no obvious cause",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    intent_cues=["troubleshooting"], source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
    evidence="Manually curated from the EP050 master spec's worked example.",
)
SYNTHETIC_SOCIAL_VIDEO = dict(
    signal_id="sv_seed_for_node08", platform="youtube", format="short_video",
    topic="boiler_pressure_loss", theme="overnight_pressure_drop_diagnosis",
    intent_cues=["troubleshooting"], geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    observed_metrics={"synthetic_views": 4200}, observed_at="2026-08-17T00:00:00+00:00",
    source_type="manual_curation", evidence="Manually curated theme.",
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
def registry(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry,
):
    return CompetitorSignalRegistry(
        tmp_path / "node_08_signals.json",
        target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry,
    )


def _payload(signal_id: str, target_id: str = "tgt_boiler_repair_blackheath") -> dict:
    return dict(
        signal_id=signal_id,
        target_id=target_id,
        competitor_name="Synthetic Rival Plumbing Co",
        channel="google_search",
        topic="boiler_pressure_loss",
        query="boiler pressure loss repair blackheath",
        attention_source="organic_search",
        relevance_score=0.72,
        competition_indicator="medium",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        observed_at="2026-08-17T00:00:00+00:00",
        source_type="manual_curation",
        evidence="Manually curated competitor observation consistent with the EP050 master spec's worked example.",
        metadata={"note": "synthetic fixture only"},
    )


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**_payload("cp_node08_test_01"))
    assert record.signal_id == "cp_node08_test_01"
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.recorded_at


def test_metadata_defaults_to_empty_dict_when_omitted(registry):
    payload = _payload("cp_node08_test_02")
    del payload["metadata"]
    record = registry.register(**payload)
    assert record.metadata == {}


# --- Node01-07->08 seven-way contract/integration test ------------------------

def test_unregistered_target_is_rejected_fail_closed(registry):
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("cp_x", target_id="tgt_never_registered"))


def test_target_missing_node_07_is_rejected_fail_closed(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry,
):
    empty_social_registry = SocialVideoSignalRegistry(
        tmp_path / "node_07_empty.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry,
    )
    registry = CompetitorSignalRegistry(
        tmp_path / "node_08.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, empty_social_registry,
    )
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("cp_x"))


def test_registered_target_with_all_seven_real_upstream_registries_is_accepted(tmp_path):
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
    record = competitor_registry.register(**_payload("cp_full_chain", target_id=target.target_id))
    assert record.target_id == target.target_id


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize(
    "missing_field",
    ["signal_id", "target_id", "competitor_name", "channel", "topic", "query", "attention_source",
     "relevance_score", "competition_indicator", "geography", "observed_at", "source_type", "evidence"],
)
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = _payload("cp_missing_field")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid enum/type failures ----------------------------------------------

def test_source_type_outside_offline_mvp_boundary_is_rejected(registry):
    payload = _payload("cp_bad_source")
    payload["source_type"] = "live_api"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_competition_indicator_invalid_enum_is_rejected(registry):
    payload = _payload("cp_bad_indicator")
    payload["competition_indicator"] = "extreme"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_relevance_score_out_of_range_is_rejected(registry):
    payload = _payload("cp_bad_score_high")
    payload["relevance_score"] = 1.5
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_relevance_score_non_numeric_is_rejected(registry):
    payload = _payload("cp_bad_score_type")
    payload["relevance_score"] = "high"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_invalid_observed_at_format_is_rejected(registry):
    payload = _payload("cp_bad_date")
    payload["observed_at"] = "not-a-date"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_geography_wrong_type_is_rejected(registry):
    payload = _payload("cp_bad_geo")
    payload["geography"] = "Blackheath, London, UK"
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Prohibited PII rejection -------------------------------------------------

def test_email_in_competitor_name_is_rejected(registry):
    payload = _payload("cp_pii_email")
    payload["competitor_name"] = "Contact us at jane.doe@example.com Plumbing"
    with pytest.raises(ValidationError, match="email"):
        registry.register(**payload)


def test_phone_in_query_is_rejected(registry):
    payload = _payload("cp_pii_phone")
    payload["query"] = "call 020 7946 0958 boiler repair"
    with pytest.raises(ValidationError, match="phone"):
        registry.register(**payload)


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_reregistration_is_idempotent_and_does_not_duplicate(registry):
    first = registry.register(**_payload("cp_idempotent"))
    second = registry.register(**_payload("cp_idempotent"))
    assert first.signal_id == second.signal_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_duplicate_same_signal_different_content_is_rejected(registry):
    registry.register(**_payload("cp_conflict"))
    conflicting = _payload("cp_conflict")
    conflicting["competition_indicator"] = "high"
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    stored = registry.get("cp_conflict")
    assert stored.competition_indicator == "medium"


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry,
):
    storage_path = tmp_path / "node_08_signals.json"
    registry_a = CompetitorSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry,
    )
    registered = registry_a.register(**_payload("cp_persist"))

    registry_b = CompetitorSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry,
    )
    fetched = registry_b.get(registered.signal_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 08 registration must not open any network socket or perform live research")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**_payload("cp_no_network"))
    assert record.signal_id == "cp_no_network"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry,
):
    storage_path = tmp_path / "node_08_signals.json"
    registry = CompetitorSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry,
    )

    record = registry.register(**_payload("cp_regression"))
    registry.register(**_payload("cp_regression"))  # idempotent
    assert len(registry.list()) == 1
    assert len(registry.list_for_target("tgt_boiler_repair_blackheath")) == 1

    fetched = registry.get(record.signal_id)
    assert fetched.signal_id == record.signal_id

    with pytest.raises(ConflictError):
        conflicting = _payload("cp_regression")
        conflicting["relevance_score"] = 0.1
        registry.register(**conflicting)

    with pytest.raises(ValidationError):
        registry.register(**dict(_payload("cp_regression_2"), source_type="live_api"))

    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("cp_x", target_id="tgt_never_registered"))

    assert registry.get("cp_nonexistent") is None


# --- Automated live ingestion (register_from_live_source) ------------------

_FAKE_HTML = (
    "<html><head><title>Rival Plumbing Co | Boiler Pressure Loss Specialists</title></head>"
    "<body><h1>Boiler pressure loss?</h1><p>We fix boiler pressure loss same day. "
    "Boiler pressure loss diagnosis included. Call our boiler pressure loss team now.</p></body></html>"
)


def test_register_from_live_source_disabled_by_default_raises_and_opens_no_socket(registry, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("live fetch must not open any socket while disabled by default")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    with pytest.raises(LiveFetchDisabledError):
        registry.register_from_live_source(
            signal_id="cp_live_disabled",
            target_id="tgt_boiler_repair_blackheath",
            competitor_url="https://rival-plumbing.example.test/boiler-pressure",
            topic="boiler_pressure_loss",
            query="boiler pressure loss repair blackheath",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_register_from_live_source_with_mocked_fetch_produces_valid_verifiable_record(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setattr(competitor_intelligence, "http_get_text", lambda url, **kw: (_FAKE_HTML, 200))

    record = registry.register_from_live_source(
        signal_id="cp_live_ok",
        target_id="tgt_boiler_repair_blackheath",
        competitor_url="https://rival-plumbing.example.test/boiler-pressure",
        topic="boiler_pressure_loss",
        query="boiler pressure loss repair blackheath",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    )

    assert record.source_type == "web_fetch"
    assert record.competitor_name == "Rival Plumbing Co | Boiler Pressure Loss Specialists"
    assert record.attention_source == "web_fetch:rival-plumbing.example.test"
    assert record.relevance_score > 0  # "boiler" appears repeatedly in the fetched text
    assert record.competition_indicator in {"low", "medium", "high"}
    receipt = record.metadata["fetch_receipt"]
    assert receipt["endpoint"] == "https://rival-plumbing.example.test/boiler-pressure"
    assert receipt["http_status"] == 200
    assert receipt["item_count"] == 1
    assert "boiler pressure loss" in record.metadata["fetched_text_excerpt"].lower()


def test_register_from_live_source_fetch_error_propagates_and_writes_nothing(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")

    def _raise(*args, **kwargs):
        raise LiveFetchRequestError("HTTP 500 fetching https://rival-plumbing.example.test/boiler-pressure: boom")

    monkeypatch.setattr(competitor_intelligence, "http_get_text", _raise)

    with pytest.raises(LiveFetchRequestError):
        registry.register_from_live_source(
            signal_id="cp_live_error",
            target_id="tgt_boiler_repair_blackheath",
            competitor_url="https://rival-plumbing.example.test/boiler-pressure",
            topic="boiler_pressure_loss",
            query="boiler pressure loss repair blackheath",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []
