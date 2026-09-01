# epics/ep_050_distribution_engine/implementation/node_09/test_community_intelligence.py
# EP050 Node 09 — Community Intelligence test suite.
#
# VERSION HISTORY
# v1.2.0 · 2026-08-18 · Adds coverage for discover_subreddit() (disabled-by-default, missing-credential,
#                        subscriber-count ranking, no-results fail-closed) and a regression guard that
#                        it and fetch_community_signal() share one _fetch_reddit_access_token() helper.
# v1.1.0 · 2026-08-17 · Adds coverage for register_from_live_source() (disabled-by-default with a
#                        blocked-socket assertion, missing-credential, mocked OAuth-token-then-
#                        search fetch producing a verifiable record, no-live-results fail-closed).
# v1.0.0 · 2026-08-17 · Initial unit/contract/integration/regression suite for Node 09.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no live community/forum/Reddit access or browsing, no production datastore, no external side effect.

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from social_video_discovery import SocialVideoSignalRegistry  # noqa: E402
from competitor_intelligence import CompetitorSignalRegistry  # noqa: E402
from live_fetch import LiveFetchDisabledError, LiveFetchRequestError, MissingCredentialError  # noqa: E402

import community_intelligence  # noqa: E402
from community_intelligence import (
    CommunitySignalRegistry,
    ConflictError,
    NoLiveResultsError,
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
    signal_id="sig_seed_for_node09", raw_query="boiler pressure dropped to zero no hot water",
    topic="boiler_pressure_loss", source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
)
SYNTHETIC_QUESTION = dict(
    question_id="q_seed_for_node09", question_text="Why does my boiler pressure keep dropping overnight?",
    topic="boiler_pressure_loss", pain_point="Recurring pressure loss with no obvious cause",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    intent_cues=["troubleshooting"], source_type="manual_curation", observed_at="2026-08-17T00:00:00+00:00",
    evidence="Manually curated from the EP050 master spec's worked example.",
)
SYNTHETIC_SOCIAL_VIDEO = dict(
    signal_id="sv_seed_for_node09", platform="youtube", format="short_video",
    topic="boiler_pressure_loss", theme="overnight_pressure_drop_diagnosis",
    intent_cues=["troubleshooting"], geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    observed_metrics={"synthetic_views": 4200}, observed_at="2026-08-17T00:00:00+00:00",
    source_type="manual_curation", evidence="Manually curated theme.",
)
SYNTHETIC_COMPETITOR = dict(
    signal_id="cp_seed_for_node09", competitor_name="Synthetic Rival Plumbing Co", channel="google_search",
    topic="boiler_pressure_loss", query="boiler pressure loss repair blackheath",
    attention_source="organic_search", relevance_score=0.72, competition_indicator="medium",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    observed_at="2026-08-17T00:00:00+00:00", source_type="manual_curation",
    evidence="Manually curated competitor observation consistent with the EP050 master spec's worked example.",
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
def registry(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry, competitor_registry,
):
    return CommunitySignalRegistry(
        tmp_path / "node_09_signals.json",
        target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry, competitor_registry,
    )


def _payload(signal_id: str, target_id: str = "tgt_boiler_repair_blackheath") -> dict:
    return dict(
        signal_id=signal_id,
        target_id=target_id,
        community_source="r/DIYUK",
        topic="boiler_pressure_loss",
        question="Boiler pressure keeps dropping overnight, anyone else had this?",
        pain_point="Recurring pressure loss with no obvious cause, worried about a hidden leak",
        intent_cues=["troubleshooting", "seeking_recommendation"],
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        observed_metrics={"synthetic_upvotes": 58, "synthetic_comments": 23},
        observed_at="2026-08-17T00:00:00+00:00",
        source_type="manual_curation",
        evidence="Manually curated community thread theme consistent with the EP050 master spec's worked example.",
        metadata={"note": "synthetic fixture only"},
    )


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**_payload("cm_node09_test_01"))
    assert record.signal_id == "cm_node09_test_01"
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.recorded_at


def test_metadata_defaults_to_empty_dict_when_omitted(registry):
    payload = _payload("cm_node09_test_02")
    del payload["metadata"]
    record = registry.register(**payload)
    assert record.metadata == {}


# --- Node01-08->09 eight-way contract/integration test ------------------------

def test_unregistered_target_is_rejected_fail_closed(registry):
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("cm_x", target_id="tgt_never_registered"))


def test_target_missing_node_08_is_rejected_fail_closed(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry,
):
    empty_competitor_registry = CompetitorSignalRegistry(
        tmp_path / "node_08_empty.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry,
    )
    registry = CommunitySignalRegistry(
        tmp_path / "node_09.json", target_registry, product_registry, audience_registry,
        conversion_registry, demand_signal_registry, question_registry, social_video_registry,
        empty_competitor_registry,
    )
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("cm_x"))


def test_registered_target_with_all_eight_real_upstream_registries_is_accepted(tmp_path):
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
        conversion_registry, demand_signal_registry, question_registry, social_video_registry,
        competitor_registry,
    )
    record = community_registry.register(**_payload("cm_full_chain", target_id=target.target_id))
    assert record.target_id == target.target_id


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize(
    "missing_field",
    ["signal_id", "target_id", "community_source", "topic", "question", "pain_point", "intent_cues",
     "geography", "observed_metrics", "observed_at", "source_type", "evidence"],
)
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = _payload("cm_missing_field")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid enum/type failures ----------------------------------------------

def test_source_type_outside_offline_mvp_boundary_is_rejected(registry):
    payload = _payload("cm_bad_source")
    payload["source_type"] = "live_api"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_intent_cues_wrong_type_is_rejected(registry):
    payload = _payload("cm_bad_cues")
    payload["intent_cues"] = "troubleshooting"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_observed_metrics_negative_value_is_rejected(registry):
    payload = _payload("cm_bad_metrics_negative")
    payload["observed_metrics"] = {"synthetic_upvotes": -5}
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_observed_metrics_non_numeric_value_is_rejected(registry):
    payload = _payload("cm_bad_metrics_type")
    payload["observed_metrics"] = {"synthetic_upvotes": "many"}
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_observed_metrics_empty_dict_is_rejected(registry):
    payload = _payload("cm_bad_metrics_empty")
    payload["observed_metrics"] = {}
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_invalid_observed_at_format_is_rejected(registry):
    payload = _payload("cm_bad_date")
    payload["observed_at"] = "not-a-date"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_geography_wrong_type_is_rejected(registry):
    payload = _payload("cm_bad_geo")
    payload["geography"] = "Blackheath, London, UK"
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Prohibited PII rejection -------------------------------------------------

def test_email_in_question_is_rejected(registry):
    payload = _payload("cm_pii_email")
    payload["question"] = "Email me at jane.doe@example.com if you've had this too"
    with pytest.raises(ValidationError, match="email"):
        registry.register(**payload)


def test_phone_in_pain_point_is_rejected(registry):
    payload = _payload("cm_pii_phone")
    payload["pain_point"] = "Call 020 7946 0958 if you know a fix"
    with pytest.raises(ValidationError, match="phone"):
        registry.register(**payload)


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_reregistration_is_idempotent_and_does_not_duplicate(registry):
    first = registry.register(**_payload("cm_idempotent"))
    second = registry.register(**_payload("cm_idempotent"))
    assert first.signal_id == second.signal_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_duplicate_same_signal_different_content_is_rejected(registry):
    registry.register(**_payload("cm_conflict"))
    conflicting = _payload("cm_conflict")
    conflicting["community_source"] = "r/PlumbingUK"
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    stored = registry.get("cm_conflict")
    assert stored.community_source == "r/DIYUK"


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry, competitor_registry,
):
    storage_path = tmp_path / "node_09_signals.json"
    registry_a = CommunitySignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry, competitor_registry,
    )
    registered = registry_a.register(**_payload("cm_persist"))

    registry_b = CommunitySignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry, competitor_registry,
    )
    fetched = registry_b.get(registered.signal_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- Automated live ingestion (register_from_live_source) ------------------

_FAKE_TOKEN_RESPONSE = {"access_token": "fake-token", "token_type": "bearer", "expires_in": 3600}
_FAKE_SEARCH_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Anyone else had boiler pressure keep dropping overnight?",
                    "selftext": "Refilled twice this week, still drops to zero by morning. Help?",
                    "permalink": "/r/DIYUK/comments/abc123/boiler_pressure/",
                    "score": 42,
                    "num_comments": 17,
                }
            }
        ]
    }
}


def test_register_from_live_source_disabled_by_default_raises_and_opens_no_socket(registry, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("live fetch must not open any socket while disabled by default")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    with pytest.raises(LiveFetchDisabledError):
        registry.register_from_live_source(
            signal_id="cm_live_disabled",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            subreddit="DIYUK",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_register_from_live_source_missing_credential_raises(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.delenv("EP050_REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("EP050_REDDIT_CLIENT_SECRET", raising=False)

    with pytest.raises(MissingCredentialError):
        registry.register_from_live_source(
            signal_id="cm_live_no_cred",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            subreddit="DIYUK",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_register_from_live_source_with_mocked_fetch_produces_valid_verifiable_record(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(community_intelligence, "http_post_form", lambda url, **kw: (_FAKE_TOKEN_RESPONSE, 200))
    monkeypatch.setattr(community_intelligence, "http_get_json", lambda url, **kw: (_FAKE_SEARCH_RESPONSE, 200))

    record = registry.register_from_live_source(
        signal_id="cm_live_ok",
        target_id="tgt_boiler_repair_blackheath",
        topic="boiler_pressure_loss",
        subreddit="DIYUK",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    )

    assert record.source_type == "community_api"
    assert record.community_source == "r/DIYUK"
    assert record.question == "Anyone else had boiler pressure keep dropping overnight?"
    assert "Refilled twice" in record.pain_point
    assert record.observed_metrics == {"score": 42, "num_comments": 17}
    receipt = record.metadata["fetch_receipt"]
    assert receipt["http_status"] == 200
    assert receipt["item_count"] == 1
    assert record.metadata["permalink"] == "https://www.reddit.com/r/DIYUK/comments/abc123/boiler_pressure/"


def test_register_from_live_source_no_results_raises_and_writes_nothing(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(community_intelligence, "http_post_form", lambda url, **kw: (_FAKE_TOKEN_RESPONSE, 200))
    monkeypatch.setattr(
        community_intelligence, "http_get_json", lambda url, **kw: ({"data": {"children": []}}, 200)
    )

    with pytest.raises(NoLiveResultsError):
        registry.register_from_live_source(
            signal_id="cm_live_empty",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            subreddit="DIYUK",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


# --- Automated live ingestion via Firecrawl (register_from_firecrawl_search) ----------------
# Built 2026-08-19: the Reddit OAuth path above has real code but has NEVER run for real --
# EP050_REDDIT_CLIENT_ID/SECRET were never set. Reddit's no-auth public JSON endpoints (tested
# live the same day) now return a genuine HTTP 403 -- Reddit's own policy, not fixable here.
# Firecrawl, already authenticated for this project, searching site:reddit.com works today.

# Shaped exactly like the real Firecrawl response captured live 2026-08-19 for
# "site:reddit.com boiler broken no heat Greenwich London UK".
_FAKE_FIRECRAWL_COMMUNITY_RESPONSE = {
    "success": True,
    "data": {
        "web": [
            {
                "title": "Unexpected Heating Charges from Landlord – Seeking Advice",
                "description": "Standing charges: ... Additional fixed charges: ... (a reserve for major repairs and upgrades, e.g., boiler replacements) ...",
                "url": "https://www.reddit.com/r/TenantsInTheUK/comments/1jiu7g3/unexpected_heating_charges_from_landlord_seeking/",
                "position": 1,
            },
            {
                "title": "Boiler broke and no heating for over 24h. What are my rights?",
                "description": "You are entitled to them fixing the boiler in a reasonable timeframe...",
                "url": "https://www.reddit.com/r/LegalAdviceUK/comments/10ffnen/boiler_broke_and_no_heating_for_over_24h_what/",
                "position": 2,
            },
        ]
    },
}


def test_register_from_firecrawl_search_disabled_by_default_raises_and_opens_no_socket(registry, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("live fetch must not open any socket while disabled by default")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    with pytest.raises(LiveFetchDisabledError):
        registry.register_from_firecrawl_search(
            signal_id="cm_fc_disabled",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_register_from_firecrawl_search_missing_credential_raises(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.delenv("EP050_FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr(
        community_intelligence, "FIRECRAWL_CLI_CREDENTIALS_PATH", Path("does-not-exist-in-tests.json"),
        raising=False,
    )
    import live_fetch
    monkeypatch.setattr(live_fetch, "FIRECRAWL_CLI_CREDENTIALS_PATH", Path("does-not-exist-in-tests.json"))

    with pytest.raises(MissingCredentialError):
        registry.register_from_firecrawl_search(
            signal_id="cm_fc_no_cred",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_register_from_firecrawl_search_with_mocked_fetch_produces_valid_verifiable_record(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(
        community_intelligence, "http_post_json",
        lambda url, **kw: (_FAKE_FIRECRAWL_COMMUNITY_RESPONSE, 200),
    )

    record = registry.register_from_firecrawl_search(
        signal_id="cm_fc_ok",
        target_id="tgt_boiler_repair_blackheath",
        topic="boiler broken no heat",
        geography={"locality": "Greenwich", "region": "London", "country": "UK"},
    )

    assert record.source_type == "community_search"
    assert record.community_source == "r/TenantsInTheUK"  # from the real result's URL, not guessed
    assert "Unexpected Heating Charges" in record.question
    assert record.observed_metrics == {"result_rank": 1, "matching_threads_returned": 2}
    receipt = record.metadata["fetch_receipt"]
    assert receipt["http_status"] == 200
    assert receipt["item_count"] == 2
    assert "reddit.com" in record.metadata["source_url"]
    # Full geography in the query -- proven necessary live: locality alone matched an r/nyc
    # thread; region+country correctly narrowed it to UK results.
    assert "Greenwich London UK" in record.metadata["search_query"]


def test_register_from_firecrawl_search_no_results_raises_and_writes_nothing(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(
        community_intelligence, "http_post_json",
        lambda url, **kw: ({"success": True, "data": {"web": []}}, 200),
    )

    with pytest.raises(NoLiveResultsError):
        registry.register_from_firecrawl_search(
            signal_id="cm_fc_empty",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_register_from_firecrawl_search_rejects_unsuccessful_response_fail_closed(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(
        community_intelligence, "http_post_json",
        lambda url, **kw: ({"success": False}, 200),
    )

    with pytest.raises(LiveFetchRequestError):
        registry.register_from_firecrawl_search(
            signal_id="cm_fc_unsuccessful",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        )
    assert registry.list() == []


def test_fetch_community_signal_via_firecrawl_carries_full_geography_in_query():
    """Locality alone silently returns the wrong country's community -- proven live: a query with
    only 'Greenwich' matched r/nyc. Region+country must be appended, same fix as Node 05."""
    from unittest.mock import patch
    import os

    os.environ["EP050_LIVE_FETCH_ENABLED"] = "1"
    os.environ["EP050_FIRECRAWL_API_KEY"] = "test-key"
    try:
        captured = {}

        def _capture(url, *, body, headers):
            captured["query"] = body["query"]
            return {"success": True, "data": {"web": [{"title": "x", "description": "y", "url": "https://reddit.com/r/test/z", "position": 1}]}}, 200

        with patch.object(community_intelligence, "http_post_json", _capture):
            community_intelligence.fetch_community_signal_via_firecrawl(
                "boiler_repair", {"locality": "Greenwich", "region": "London", "country": "UK"}
            )
        assert "Greenwich" in captured["query"]
        assert "London" in captured["query"]
        assert "UK" in captured["query"]
    finally:
        os.environ.pop("EP050_LIVE_FETCH_ENABLED", None)
        os.environ.pop("EP050_FIRECRAWL_API_KEY", None)


# --- discover_subreddit() — derives `subreddit` instead of a human supplying it -------------

_FAKE_SUBREDDIT_SEARCH_RESPONSE = {
    "data": {
        "children": [
            {"data": {"display_name": "DIYUK", "subscribers": 450000}},
            {"data": {"display_name": "Plumbing", "subscribers": 12000}},
        ]
    }
}


def test_discover_subreddit_disabled_by_default_raises_and_opens_no_socket(monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("live fetch must not open any socket while disabled by default")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    with pytest.raises(LiveFetchDisabledError):
        community_intelligence.discover_subreddit("boiler_pressure_loss")


def test_discover_subreddit_missing_credential_raises(monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.delenv("EP050_REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("EP050_REDDIT_CLIENT_SECRET", raising=False)

    with pytest.raises(MissingCredentialError):
        community_intelligence.discover_subreddit("boiler_pressure_loss")


def test_discover_subreddit_ranks_by_subscriber_count_and_returns_top_match(monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(community_intelligence, "http_post_form", lambda url, **kw: (_FAKE_TOKEN_RESPONSE, 200))
    monkeypatch.setattr(
        community_intelligence, "http_get_json", lambda url, **kw: (_FAKE_SUBREDDIT_SEARCH_RESPONSE, 200)
    )

    subreddit, receipt = community_intelligence.discover_subreddit("boiler_pressure_loss")

    assert subreddit == "DIYUK"
    assert receipt.item_count == 2
    assert receipt.http_status == 200


def test_discover_subreddit_no_results_raises(monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(community_intelligence, "http_post_form", lambda url, **kw: (_FAKE_TOKEN_RESPONSE, 200))
    monkeypatch.setattr(
        community_intelligence, "http_get_json", lambda url, **kw: ({"data": {"children": []}}, 200)
    )

    with pytest.raises(NoLiveResultsError):
        community_intelligence.discover_subreddit("boiler_pressure_loss")


def test_discover_subreddit_and_fetch_community_signal_share_one_token_helper(monkeypatch):
    """Regression guard for the v1.2.0 refactor: both live entry points must go through
    _fetch_reddit_access_token() so there is exactly one OAuth exchange implementation."""
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("EP050_REDDIT_CLIENT_SECRET", "test-client-secret")
    token_calls = []

    def _record_token_call(url, **kw):
        token_calls.append(url)
        return _FAKE_TOKEN_RESPONSE, 200

    monkeypatch.setattr(community_intelligence, "http_post_form", _record_token_call)
    monkeypatch.setattr(
        community_intelligence, "http_get_json", lambda url, **kw: (_FAKE_SUBREDDIT_SEARCH_RESPONSE, 200)
    )

    subreddit, _ = community_intelligence.discover_subreddit("boiler_pressure_loss")

    assert subreddit == "DIYUK"
    assert len(token_calls) == 1
    assert token_calls[0] == community_intelligence.REDDIT_TOKEN_ENDPOINT


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 09 registration must not open any network socket or perform live community access")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**_payload("cm_no_network"))
    assert record.signal_id == "cm_no_network"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry,
    demand_signal_registry, question_registry, social_video_registry, competitor_registry,
):
    storage_path = tmp_path / "node_09_signals.json"
    registry = CommunitySignalRegistry(
        storage_path, target_registry, product_registry, audience_registry, conversion_registry,
        demand_signal_registry, question_registry, social_video_registry, competitor_registry,
    )

    record = registry.register(**_payload("cm_regression"))
    registry.register(**_payload("cm_regression"))  # idempotent
    assert len(registry.list()) == 1
    assert len(registry.list_for_target("tgt_boiler_repair_blackheath")) == 1

    fetched = registry.get(record.signal_id)
    assert fetched.signal_id == record.signal_id

    with pytest.raises(ConflictError):
        conflicting = _payload("cm_regression")
        conflicting["observed_metrics"] = {"synthetic_upvotes": 1}
        registry.register(**conflicting)

    with pytest.raises(ValidationError):
        registry.register(**dict(_payload("cm_regression_2"), source_type="live_api"))

    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("cm_x", target_id="tgt_never_registered"))

    assert registry.get("cm_nonexistent") is None
