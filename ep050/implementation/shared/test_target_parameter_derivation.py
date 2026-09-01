# epics/ep_050_distribution_engine/implementation/shared/test_target_parameter_derivation.py
# EP050 shared — target_parameter_derivation test suite.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-18 · Initial unit suite for derive_geography/derive_topic_candidates/
#   derive_primary_topic/derive_competitor_url.
#
# All tests are fully offline/pure — no network, no filesystem, no fixture registries.

from __future__ import annotations

import pytest

from target_parameter_derivation import (
    DerivationError,
    derive_competitor_url,
    derive_geography,
    derive_primary_topic,
    derive_topic_candidates,
)

_TARGET_RECORD = {
    "target_id": "tgt_boiler_repair_blackheath",
    "service": "boiler_repair",
    "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
}

_AUDIENCE_RECORD = {
    "segment_id": "tgt_boiler_repair_blackheath__seg_homeowners",
    "needs": ["Restore hot water quickly", "Understand the cause of pressure loss"],
    "pains": ["No heating or hot water", "Uncertainty over callout cost"],
}

_SEARCH_DEMAND_RESULT = {
    "query": "boiler pressure loss Blackheath",
    "total_results": "18400",
    "top_results": [
        {"title": "A", "snippet": "...", "link": "https://our-own-site.test/blog/boiler-pressure"},
        {"title": "B", "snippet": "...", "link": "https://rival-heating.test/emergency-repair"},
        {"title": "C", "snippet": "...", "link": None},
    ],
}


# --- derive_geography ---------------------------------------------------------

def test_derive_geography_returns_node01_geography_unchanged():
    assert derive_geography(_TARGET_RECORD) == {"locality": "Blackheath", "region": "London", "country": "UK"}


def test_derive_geography_rejects_non_mapping_target_record():
    with pytest.raises(DerivationError):
        derive_geography("not-a-record")  # type: ignore[arg-type]


def test_derive_geography_rejects_missing_geography_field():
    with pytest.raises(DerivationError):
        derive_geography({"target_id": "tgt_x", "service": "boiler_repair"})


def test_derive_geography_rejects_incomplete_geography():
    with pytest.raises(DerivationError):
        derive_geography({"geography": {"locality": "Blackheath"}})


# --- derive_topic_candidates / derive_primary_topic ----------------------------

def test_derive_topic_candidates_slugifies_needs_then_pains_deduped():
    candidates = derive_topic_candidates(_AUDIENCE_RECORD)
    assert candidates == [
        "restore_hot_water_quickly",
        "understand_the_cause_of_pressure_loss",
        "no_heating_or_hot_water",
        "uncertainty_over_callout_cost",
    ]


def test_derive_primary_topic_returns_first_need():
    assert derive_primary_topic(_AUDIENCE_RECORD) == "restore_hot_water_quickly"


def test_derive_topic_candidates_dedupes_identical_slugs():
    record = {"needs": ["Fix boiler pressure!"], "pains": ["fix boiler pressure"]}
    assert derive_topic_candidates(record) == ["fix_boiler_pressure"]


def test_derive_topic_candidates_rejects_empty_needs_and_pains():
    with pytest.raises(DerivationError):
        derive_topic_candidates({"needs": [], "pains": []})


def test_derive_topic_candidates_rejects_missing_lists():
    with pytest.raises(DerivationError):
        derive_topic_candidates({"needs": ["x"]})


# --- derive_competitor_url -----------------------------------------------------

def test_derive_competitor_url_returns_first_link_when_no_exclusions():
    assert derive_competitor_url(_SEARCH_DEMAND_RESULT) == "https://our-own-site.test/blog/boiler-pressure"


def test_derive_competitor_url_skips_excluded_domain():
    url = derive_competitor_url(_SEARCH_DEMAND_RESULT, exclude_domains=["our-own-site.test"])
    assert url == "https://rival-heating.test/emergency-repair"


def test_derive_competitor_url_skips_results_missing_a_link():
    result = {"top_results": [{"link": None}, {"link": "https://rival-heating.test/x"}]}
    assert derive_competitor_url(result) == "https://rival-heating.test/x"


def test_derive_competitor_url_rejects_empty_top_results():
    with pytest.raises(DerivationError):
        derive_competitor_url({"top_results": []})


def test_derive_competitor_url_rejects_when_all_results_excluded():
    with pytest.raises(DerivationError):
        derive_competitor_url(_SEARCH_DEMAND_RESULT, exclude_domains=["our-own-site.test", "rival-heating.test"])


def test_derive_competitor_url_rejects_non_mapping_result():
    with pytest.raises(DerivationError):
        derive_competitor_url("not-a-result")  # type: ignore[arg-type]
