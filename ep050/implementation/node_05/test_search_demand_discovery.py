# epics/ep_050_distribution_engine/implementation/node_05/test_search_demand_discovery.py
# EP050 Node 05 — Search Demand Discovery test suite.
#
# VERSION HISTORY
# v1.2.0 · 2026-08-18 · Adds test_fetch_search_demand_captures_link_field_for_downstream_competitor_derivation
#                        covering fetch_search_demand()'s new `link` capture (v1.3.0), plus link
#                        values in _FAKE_CSE_RESPONSE fixture items.
# v1.1.0 · 2026-08-17 · Adds coverage for register_from_live_source() (disabled-by-default with a
#                        blocked-socket assertion, missing-credential, mocked-fetch) and replaces
#                        test_automated_source_types_are_accepted with a split pair proving only
#                        search_query is now accepted and the four previously-unbacked labels
#                        (gmb_insights/crm_activity/autosuggest_feed/live_api) are rejected again.
# v1.0.0 · 2026-08-17 · Initial unit/contract/integration/regression suite for Node 05, including a
#                        real cross-owner contract-compatibility test against Gemini's live Node 11.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no live scraping, no production datastore, no external side effect.

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_02"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_03"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_04"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_11"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry, MASTER_SPEC_STAGES  # noqa: E402
import intent_classification as node11  # noqa: E402 (Gemini-owned, read-only import)
import live_fetch  # noqa: E402
from live_fetch import LiveFetchDisabledError, LiveFetchRequestError, MissingCredentialError  # noqa: E402

import search_demand_discovery  # noqa: E402
from search_demand_discovery import (
    ConflictError,
    DemandSignalRegistry,
    UnknownTargetError,
    ValidationError,
)

SYNTHETIC_TARGET = dict(
    target_type="service_market",
    service="boiler_repair",
    market="domestic_plumbing",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
)

SYNTHETIC_PRODUCT = dict(
    problem="Homeowners lose boiler pressure and hot water with no clear diagnosis path.",
    solution="A vetted local boiler-repair callout that diagnoses and restores pressure same-day.",
    features=["Same-day callout"],
    benefits=["Hot water restored quickly"],
    differentiators=["Local coverage"],
    commercial_model="Fixed diagnostic fee.",
    customer_outcome="Working boiler within 24 hours.",
)

SYNTHETIC_SEGMENT = dict(
    segment_name="Blackheath homeowner, boiler pressure loss",
    needs=["Restore hot water quickly"],
    pains=["No heating or hot water"],
    urgency="high",
    eligibility_geography={"locality": "Blackheath", "region": "London", "country": "UK"},
)

MASTER_SPEC_TRANSITIONS = [
    ["visit", "engage"], ["engage", "tool_use"], ["tool_use", "enquiry"], ["enquiry", "lead"],
    ["lead", "qualified_lead"], ["qualified_lead", "booking"], ["booking", "sale"], ["sale", "revenue"],
]

SYNTHETIC_CONVERSION = dict(
    stages=MASTER_SPEC_STAGES,
    allowed_transitions=MASTER_SPEC_TRANSITIONS,
    success_stage_id="sale",
    success_criteria="A lead reaches the sale stage with a recorded, attributable outcome.",
)


@pytest.fixture
def target_registry(tmp_path):
    registry = TargetRegistry(tmp_path / "node_01_targets.json")
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
def registry(tmp_path, target_registry, product_registry, audience_registry, conversion_registry):
    return DemandSignalRegistry(
        tmp_path / "node_05_demand_signals.json",
        target_registry, product_registry, audience_registry, conversion_registry,
    )


def _payload(signal_id: str, target_id: str = "tgt_boiler_repair_blackheath") -> dict:
    return dict(
        signal_id=signal_id,
        target_id=target_id,
        raw_query="boiler pressure dropped to zero no hot water how to fix",
        topic="boiler_pressure_loss",
        source_type="manual_curation",
        observed_at="2026-08-17T00:00:00+00:00",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        metadata={"urgency_hint": "high"},
    )


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**_payload("sig_node05_test_01"))
    assert record.signal_id == "sig_node05_test_01"
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.recorded_at


def test_metadata_defaults_to_empty_dict_when_omitted(registry):
    payload = _payload("sig_node05_test_02")
    del payload["metadata"]
    record = registry.register(**payload)
    assert record.metadata == {}


# --- Node01+02+03+04->05 contract/integration test ---------------------------

def test_unregistered_target_is_rejected_fail_closed(registry):
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("sig_x", target_id="tgt_never_registered"))


def test_target_missing_node_04_is_rejected_fail_closed(tmp_path, target_registry, product_registry, audience_registry):
    empty_conversion_registry = ConversionDefinitionRegistry(
        tmp_path / "node_04_empty.json", target_registry, product_registry, audience_registry
    )
    registry = DemandSignalRegistry(
        tmp_path / "node_05.json", target_registry, product_registry, audience_registry, empty_conversion_registry
    )
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("sig_x"))


def test_registered_target_with_all_four_real_upstream_registries_is_accepted(tmp_path):
    target_registry = TargetRegistry(tmp_path / "node_01.json")
    target = target_registry.register(**SYNTHETIC_TARGET)
    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    product_registry.register(target_id=target.target_id, **SYNTHETIC_PRODUCT)
    audience_registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    audience_registry.register(target_id=target.target_id, **SYNTHETIC_SEGMENT)
    conversion_registry = ConversionDefinitionRegistry(tmp_path / "node_04.json", target_registry, product_registry, audience_registry)
    conversion_registry.register(target_id=target.target_id, **SYNTHETIC_CONVERSION)
    demand_registry = DemandSignalRegistry(
        tmp_path / "node_05.json", target_registry, product_registry, audience_registry, conversion_registry
    )
    record = demand_registry.register(**_payload("sig_full_chain", target_id=target.target_id))
    assert record.target_id == target.target_id


# --- Cross-owner contract compatibility (real, not assumed) ------------------

def test_produced_signal_is_accepted_by_the_real_node_11_classifier(registry):
    """Proves Node 05's output actually conforms to the frozen contract Node 11 already validates."""
    record = registry.register(**_payload("sig_contract_compat"))
    result = node11.classify_demand_signal(record.to_contract_payload())
    assert result.target_id == record.target_id
    assert result.signal_id == record.signal_id


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize(
    "missing_field",
    ["signal_id", "target_id", "raw_query", "topic", "source_type", "observed_at", "geography", "service_context"],
)
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = _payload("sig_missing_field")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid enum/type failures ----------------------------------------------

def test_source_type_outside_allowed_boundary_is_rejected(registry):
    payload = _payload("sig_bad_source")
    payload["source_type"] = "invalid_unknown_source"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_search_query_source_type_is_accepted(registry):
    # search_query is the one live source type this node backs with a real connector
    # (register_from_live_source, tested below); manual writes may also claim it directly.
    payload = _payload("sig_auto_search_query")
    payload["source_type"] = "search_query"
    rec = registry.register(**payload)
    assert rec.source_type == "search_query"


def test_unbacked_live_source_labels_are_rejected(registry):
    # gmb_insights/crm_activity/autosuggest_feed/live_api were added in a prior pass with no
    # connector behind them (schema-only widening, flagged and reverted -- board event
    # 20260817T162311314) and must stay rejected until a real connector backs each one.
    for source in ("gmb_insights", "crm_activity", "autosuggest_feed", "live_api"):
        payload = _payload(f"sig_unbacked_{source}")
        payload["source_type"] = source
        with pytest.raises(ValidationError):
            registry.register(**payload)


def test_invalid_observed_at_format_is_rejected(registry):
    payload = _payload("sig_bad_date")
    payload["observed_at"] = "not-a-date"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_geography_wrong_type_is_rejected(registry):
    payload = _payload("sig_bad_geo")
    payload["geography"] = "Blackheath, London, UK"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_service_context_missing_subfield_is_rejected(registry):
    payload = _payload("sig_bad_svc")
    payload["service_context"] = {"service_name": "boiler_repair"}  # missing market_segment
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Prohibited PII rejection -------------------------------------------------

def test_email_in_raw_query_is_rejected(registry):
    payload = _payload("sig_pii_email")
    payload["raw_query"] = "email me at jane.doe@example.com about the boiler"
    with pytest.raises(ValidationError, match="email"):
        registry.register(**payload)


def test_phone_in_topic_is_rejected(registry):
    payload = _payload("sig_pii_phone")
    payload["topic"] = "call 020 7946 0958 for boiler help"
    with pytest.raises(ValidationError, match="phone"):
        registry.register(**payload)


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_reregistration_is_idempotent_and_does_not_duplicate(registry):
    first = registry.register(**_payload("sig_idempotent"))
    second = registry.register(**_payload("sig_idempotent"))
    assert first.signal_id == second.signal_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_duplicate_same_signal_different_content_is_rejected(registry):
    registry.register(**_payload("sig_conflict"))
    conflicting = _payload("sig_conflict")
    conflicting["topic"] = "a_completely_different_topic"
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    stored = registry.get("sig_conflict")
    assert stored.topic == "boiler_pressure_loss"


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry
):
    storage_path = tmp_path / "node_05_demand_signals.json"
    registry_a = DemandSignalRegistry(storage_path, target_registry, product_registry, audience_registry, conversion_registry)
    registered = registry_a.register(**_payload("sig_persist"))

    registry_b = DemandSignalRegistry(storage_path, target_registry, product_registry, audience_registry, conversion_registry)
    fetched = registry_b.get(registered.signal_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- Automated live ingestion (register_from_live_source) ------------------

# Shaped exactly like a real Firecrawl POST /v2/search response, verified against the live API
# on 2026-08-19: top-level {success, data, creditsUsed, id}, with data.web[] carrying
# {url, title, description, position}. Note the field names differ from the Google response this
# replaced (description/url vs snippet/link) -- that mapping is what fetch_search_demand does.
_FAKE_FIRECRAWL_RESPONSE = {
    "success": True,
    "creditsUsed": 2,
    "id": "fake-job-id",
    "data": {
        "web": [
            {
                "title": "Boiler pressure keeps dropping - how to fix it",
                "description": "Common causes...",
                "url": "https://example-plumbing-co.test/blog/boiler-pressure",
                "position": 1,
            },
            {
                "title": "Emergency boiler pressure loss repair",
                "description": "Same-day callout...",
                "url": "https://rival-heating.test/emergency-repair",
                "position": 2,
            },
        ]
    },
}


def test_register_from_live_source_disabled_by_default_raises_and_opens_no_socket(registry, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)

    def _blocked_socket(*args, **kwargs):
        raise AssertionError("live fetch must not open any socket while disabled by default")

    monkeypatch.setattr(socket, "socket", _blocked_socket)

    with pytest.raises(LiveFetchDisabledError):
        registry.register_from_live_source(
            signal_id="sig_live_disabled",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
            service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        )
    assert registry.list() == []


def test_register_from_live_source_missing_credential_raises(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.delenv("EP050_FIRECRAWL_API_KEY", raising=False)
    # Also neutralise the Firecrawl CLI credentials fallback, otherwise this machine's real
    # stored credential would satisfy the lookup and the fail-closed path would never be exercised.
    monkeypatch.setattr(live_fetch, "FIRECRAWL_CLI_CREDENTIALS_PATH", Path("does-not-exist-in-tests.json"))

    with pytest.raises(MissingCredentialError):
        registry.register_from_live_source(
            signal_id="sig_live_no_cred",
            target_id="tgt_boiler_repair_blackheath",
            topic="boiler_pressure_loss",
            geography={"locality": "Blackheath", "region": "London", "country": "UK"},
            service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        )
    assert registry.list() == []


def test_register_from_live_source_with_mocked_fetch_produces_valid_verifiable_record(registry, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(
        search_demand_discovery, "http_post_json", lambda url, **kw: (_FAKE_FIRECRAWL_RESPONSE, 200)
    )

    record = registry.register_from_live_source(
        signal_id="sig_live_ok",
        target_id="tgt_boiler_repair_blackheath",
        topic="boiler_pressure_loss",
        geography={"locality": "Blackheath", "region": "London", "country": "UK"},
        service_context={"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
    )

    assert record.source_type == "search_query"
    # Full geography, not locality alone -- see build_search_query's docstring for the real bug this prevents.
    assert record.raw_query == "boiler pressure loss Blackheath London UK"
    receipt = record.metadata["fetch_receipt"]
    assert receipt["http_status"] == 200
    assert receipt["item_count"] == 2
    summary = record.metadata["search_result_summary"]
    assert summary["total_results"] == "2"
    assert len(summary["top_results"]) == 2


def test_fetch_search_demand_captures_link_field_for_downstream_competitor_derivation(monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(
        search_demand_discovery, "http_post_json", lambda url, **kw: (_FAKE_FIRECRAWL_RESPONSE, 200)
    )

    result, receipt = search_demand_discovery.fetch_search_demand(
        "boiler_pressure_loss", {"locality": "Blackheath", "region": "London", "country": "UK"}
    )

    # Firecrawl calls these `url`/`description`; downstream (target_parameter_derivation, and the
    # console's demand gate) still expects `link`/`snippet`, so the mapping must hold.
    assert result["top_results"][0]["link"] == "https://example-plumbing-co.test/blog/boiler-pressure"
    assert result["top_results"][1]["link"] == "https://rival-heating.test/emergency-repair"
    assert result["top_results"][0]["snippet"] == "Common causes..."
    assert receipt.item_count == 2
    assert result["provider"] == "firecrawl"
    assert result["credits_used"] == 2


def test_fetch_search_demand_rejects_unsuccessful_response_fail_closed(monkeypatch):
    """A non-success payload must raise, never yield an empty-but-valid-looking demand signal.

    This matters because an empty top_results would read downstream as 'searched, found nothing'
    (stopped_no_demand) rather than 'the search never worked' (parked) -- two very different
    real-world conclusions about a market.
    """
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(
        search_demand_discovery,
        "http_post_json",
        lambda url, **kw: ({"success": False, "error": "quota exceeded"}, 200),
    )

    with pytest.raises(LiveFetchRequestError):
        search_demand_discovery.fetch_search_demand(
            "boiler_pressure_loss", {"locality": "Blackheath", "region": "London", "country": "UK"}
        )


def test_fetch_search_demand_rejects_unexpected_data_shape_fail_closed(monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(
        search_demand_discovery,
        "http_post_json",
        lambda url, **kw: ({"success": True, "data": {"web": "not-a-list"}}, 200),
    )

    with pytest.raises(LiveFetchRequestError):
        search_demand_discovery.fetch_search_demand(
            "boiler_pressure_loss", {"locality": "Blackheath", "region": "London", "country": "UK"}
        )


@pytest.mark.parametrize(
    "geography,expected",
    [
        ({"locality": "Greenwich", "region": "London", "country": "UK"}, "boiler repair Greenwich London UK"),
        # Region/country missing: degrade gracefully rather than emitting empty tokens.
        ({"locality": "Greenwich"}, "boiler repair Greenwich"),
        ({"locality": "Greenwich", "region": "", "country": None}, "boiler repair Greenwich"),
        # Duplicate values must not be repeated ("London London").
        ({"locality": "London", "region": "London", "country": "UK"}, "boiler repair London UK"),
    ],
)
def test_build_search_query_carries_full_geography(geography, expected):
    """Locality alone silently returns the wrong country's market -- proven live against the real
    provider, where 'restore hot water quickly Greenwich' returned Greenwich, CONNECTICUT results
    despite UK geo-targeting parameters being set."""
    assert search_demand_discovery.build_search_query("boiler_repair", geography) == expected


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 05 registration must not open any network socket or perform live scraping")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**_payload("sig_no_network"))
    assert record.signal_id == "sig_no_network"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(
    tmp_path, target_registry, product_registry, audience_registry, conversion_registry
):
    storage_path = tmp_path / "node_05_demand_signals.json"
    registry = DemandSignalRegistry(storage_path, target_registry, product_registry, audience_registry, conversion_registry)

    record = registry.register(**_payload("sig_regression"))
    registry.register(**_payload("sig_regression"))  # idempotent
    assert len(registry.list()) == 1
    assert len(registry.list_for_target("tgt_boiler_repair_blackheath")) == 1

    fetched = registry.get(record.signal_id)
    assert fetched.signal_id == record.signal_id

    with pytest.raises(ConflictError):
        conflicting = _payload("sig_regression")
        conflicting["raw_query"] = "a materially different raw query text"
        registry.register(**conflicting)

    with pytest.raises(ValidationError):
        registry.register(**dict(_payload("sig_regression_2"), source_type="forum_question"))

    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("sig_x", target_id="tgt_never_registered"))

    assert registry.get("sig_nonexistent") is None

    # Confirm the persisted signal is still contract-compatible with the real Node 11 classifier.
    result = node11.classify_demand_signal(record.to_contract_payload())
    assert result.signal_id == record.signal_id
