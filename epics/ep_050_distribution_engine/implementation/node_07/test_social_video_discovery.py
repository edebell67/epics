# epics/ep_050_distribution_engine/implementation/node_07/test_social_video_discovery.py
# EP050 Node 07 — Social / Video Discovery test suite.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds coverage for register_from_live_source() (disabled-by-default with a
#                        blocked-socket assertion, missing-credential, mocked two-call fetch
#                        producing a verifiable record, no-live-results fail-closed).
# v1.0.0 · 2026-08-17 · Initial unit/contract/integration/regression suite for Node 07.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no live browsing/scraping, no production datastore, no external side effect.

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from live_fetch import LiveFetchDisabledError, MissingCredentialError  # noqa: E402

import social_video_discovery  # noqa: E402
from social_video_discovery import (
    ConflictError,
    NoLiveResultsError,
    SocialVideoSignalRegistry,
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
    signal_id="sig_seed_for_node07", raw_query="boiler pressure dropped to zero no hot water",
    topic="boiler_pressure_loss", source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
)
SYNTHETIC_QUESTION = dict(
    question_id="q_seed_for_node07", question_text="Why does my boiler pressure keep dropping overnight?",
    topic="boiler_pressure_loss", pain_point="Recurring pressure loss with no obvious cause",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    intent_cues=["troubleshooting"], source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
    evidence="Manually curated from the EP050 master spec's worked example.",
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
def registry(tmp_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry, question_registry):
    return SocialVideoSignalRegistry(
        tmp_path / "node_07_signals.json",
        target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry, question_registry,
    )


def _payload(signal_id: str, target_id: str = "tgt_boiler_repair_blackheath") -> dict:
    return dict(
        signal_id=signal_id,
        target_id=target_id,
        platform="youtube",
        format="short_video",
        topic="boiler_pressure_loss",
        theme="overnight_pressure_drop_diagnosis",
        intent_cues=["troubleshooting", "how_to"],
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        observed_metrics={"synthetic_views": 4200, "synthetic_engagement_rate": 0.08},
        observed_at="2026-08-17T00:00:00+00:00",
        source_type="manual_curation",
        evidence="Manually curated theme consistent with the EP050 master spec's worked example.",
        metadata={"format_note": "60s explainer"},
    )


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**_payload("sv_node07_test_01"))
    assert record.signal_id == "sv_node07_test_01"
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.recorded_at


def test_metadata_defaults_to_empty_dict_when_omitted(registry):
    payload = _payload("sv_node07_test_02")
    del payload["metadata"]
    record = registry.register(**payload)
    assert record.metadata == {}


# --- Node01-06->07 six-way contract/integration test --------------------------

def test_unregistered_target_is_rejected_fail_closed(registry):
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("sv_x", target_id="tgt_never_registered"))


def test_target_missing_node_06_is_rejected_fail_closed(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry
):
    empty_question_registry = QuestionRegistry(
        tmp_path / "node_06_empty.json", target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry
    )
    registry = SocialVideoSignalRegistry(
        tmp_path / "node_07.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, empty_question_registry,
    )
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("sv_x"))


def test_registered_target_with_all_six_real_upstream_registries_is_accepted(tmp_path):
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
    social_registry = SocialVideoSignalRegistry(
        tmp_path / "node_07.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry,
    )
    record = social_registry.register(**_payload("sv_full_chain", target_id=target.target_id))
    assert record.target_id == target.target_id


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize(
    "missing_field",
    ["signal_id", "target_id", "platform", "format", "topic", "theme", "intent_cues", "geography",
     "observed_metrics", "observed_at", "source_type", "evidence"],
)
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = _payload("sv_missing_field")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid enum/type failures ----------------------------------------------

def test_source_type_outside_offline_mvp_boundary_is_rejected(registry):
    payload = _payload("sv_bad_source")
    payload["source_type"] = "live_api"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_invalid_observed_at_format_is_rejected(registry):
    payload = _payload("sv_bad_date")
    payload["observed_at"] = "not-a-date"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_observed_metrics_empty_is_rejected(registry):
    payload = _payload("sv_bad_metrics_empty")
    payload["observed_metrics"] = {}
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_observed_metrics_non_numeric_is_rejected(registry):
    payload = _payload("sv_bad_metrics_type")
    payload["observed_metrics"] = {"synthetic_views": "a lot"}
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_observed_metrics_negative_is_rejected(registry):
    payload = _payload("sv_bad_metrics_negative")
    payload["observed_metrics"] = {"synthetic_views": -5}
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_geography_wrong_type_is_rejected(registry):
    payload = _payload("sv_bad_geo")
    payload["geography"] = "Blackheath, London, UK"
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Prohibited PII rejection -------------------------------------------------

def test_email_in_theme_is_rejected(registry):
    payload = _payload("sv_pii_email")
    payload["theme"] = "contact jane.doe@example.com for details"
    with pytest.raises(ValidationError, match="email"):
        registry.register(**payload)


def test_phone_in_topic_is_rejected(registry):
    payload = _payload("sv_pii_phone")
    payload["topic"] = "call 020 7946 0958 for boiler help"
    with pytest.raises(ValidationError, match="phone"):
        registry.register(**payload)


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_reregistration_is_idempotent_and_does_not_duplicate(registry):
    first = registry.register(**_payload("sv_idempotent"))
    second = registry.register(**_payload("sv_idempotent"))
    assert first.signal_id == second.signal_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_duplicate_same_signal_different_content_is_rejected(registry):
    registry.register(**_payload("sv_conflict"))
    conflicting = _payload("sv_conflict")
    conflicting["platform"] = "tiktok"
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    stored = registry.get("sv_conflict")
    assert stored.platform == "youtube"


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry, question_registry
):
    storage_path = tmp_path / "node_07_signals.json"
    registry_a = SocialVideoSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry, question_registry
    )
    registered = registry_a.register(**_payload("sv_persist"))

    registry_b = SocialVideoSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry, question_registry
    )
    fetched = registry_b.get(registered.signal_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- Automated live ingestion (register_from_live_source) ------------------

_FAKE_SEARCH_RESPONSE = {
    "items": [{"id": {"videoId": "abc123"}, "snippet": {"title": "How to fix boiler pressure loss - DIY guide"}}]
}
_FAKE_VIDEOS_RESPONSE = {
    "items": [{
        "statistics": {"viewCount": "15000", "likeCount": "900", "commentCount": "120"},
        "contentDetails": {"duration": "PT8M12S"},
    }]
}


def test_register_from_live_source_disabled_by_default_raises_and_opens_no_socket(registry, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("live fetch must not open any socket while disabled by default")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    with pytest.raises(LiveFetchDisabledError):
        registry.register_from_live_source(
            signal_id="sv_live_disabled",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_register_from_live_source_missing_credential_raises(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.delenv("EP050_YOUTUBE_API_KEY", raising=False)

    with pytest.raises(MissingCredentialError):
        registry.register_from_live_source(
            signal_id="sv_live_no_cred",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_register_from_live_source_with_mocked_fetch_produces_valid_verifiable_record(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_YOUTUBE_API_KEY", "test-key")
    responses = iter([(_FAKE_SEARCH_RESPONSE, 200), (_FAKE_VIDEOS_RESPONSE, 200)])
    monkeypatch.setattr(social_video_discovery, "http_get_json", lambda url, **kw: next(responses))

    record = registry.register_from_live_source(
        signal_id="sv_live_ok",
        target_id="tgt_boiler_repair_blackheath",
        topic="boiler_pressure_loss",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    )

    assert record.source_type == "video_api"
    assert record.platform == "youtube"
    assert record.format == "long_video"  # 8m12s > 60s
    assert record.theme == "How to fix boiler pressure loss - DIY guide"
    assert record.observed_metrics == {"view_count": 15000, "like_count": 900, "comment_count": 120}
    assert "seeking_repair" in record.intent_cues or "troubleshooting" in record.intent_cues
    assert record.metadata["fetch_receipt"]["item_count"] == 1
    assert record.metadata["video_id"] == "abc123"


def test_register_from_live_source_no_results_raises_and_writes_nothing(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr(social_video_discovery, "http_get_json", lambda url, **kw: ({"items": []}, 200))

    with pytest.raises(NoLiveResultsError):
        registry.register_from_live_source(
            signal_id="sv_live_empty",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 07 registration must not open any network socket or perform live browsing")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**_payload("sv_no_network"))
    assert record.signal_id == "sv_no_network"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry, question_registry
):
    storage_path = tmp_path / "node_07_signals.json"
    registry = SocialVideoSignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry, demand_signal_registry, question_registry
    )

    record = registry.register(**_payload("sv_regression"))
    registry.register(**_payload("sv_regression"))  # idempotent
    assert len(registry.list()) == 1
    assert len(registry.list_for_target("tgt_boiler_repair_blackheath")) == 1

    fetched = registry.get(record.signal_id)
    assert fetched.signal_id == record.signal_id

    with pytest.raises(ConflictError):
        conflicting = _payload("sv_regression")
        conflicting["theme"] = "a materially different theme"
        registry.register(**conflicting)

    with pytest.raises(ValidationError):
        registry.register(**dict(_payload("sv_regression_2"), source_type="live_api"))

    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("sv_x", target_id="tgt_never_registered"))

    assert registry.get("sv_nonexistent") is None
