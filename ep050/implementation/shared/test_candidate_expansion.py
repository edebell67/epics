# epics/ep_050_distribution_engine/implementation/shared/test_candidate_expansion.py
# EP050 shared — candidate_expansion test suite.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-18 · Initial unit suite for derive_adjacent_geo_candidates/
#   derive_adjacent_service_candidates/derive_one_hop_candidates.
#
# All tests are fully offline/pure — no network, no filesystem, no fixture registries.

from __future__ import annotations

import pytest

from candidate_expansion import (
    DerivationError,
    derive_adjacent_geo_candidates,
    derive_adjacent_service_candidates,
    derive_one_hop_candidates,
)

_TARGET_RECORD = {
    "target_id": "tgt_boiler_repair_blackheath",
    "target_type": "local_service_business",
    "service": "boiler_repair",
    "market": "residential_homeowners",
    "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
}


# --- derive_adjacent_geo_candidates ---------------------------------------------------------

def test_geo_candidates_keep_service_and_market_unchanged():
    candidates = derive_adjacent_geo_candidates(_TARGET_RECORD)
    assert candidates
    for c in candidates:
        assert c["service"] == "boiler_repair"
        assert c["market"] == "residential_homeowners"
        assert c["target_type"] == "local_service_business"


def test_geo_candidates_vary_only_locality():
    candidates = derive_adjacent_geo_candidates(_TARGET_RECORD)
    localities = {c["geography"]["locality"] for c in candidates}
    assert "Blackheath" not in localities
    assert "Lewisham" in localities
    for c in candidates:
        assert c["geography"]["region"] == "London"
        assert c["geography"]["country"] == "UK"


def test_geo_candidates_unknown_locality_is_rejected():
    record = {**_TARGET_RECORD, "geography": {**_TARGET_RECORD["geography"], "locality": "Nowhereville"}}
    with pytest.raises(DerivationError):
        derive_adjacent_geo_candidates(record)


def test_geo_candidates_missing_service_is_rejected():
    record = dict(_TARGET_RECORD)
    del record["service"]
    with pytest.raises(DerivationError):
        derive_adjacent_geo_candidates(record)


# --- derive_adjacent_service_candidates ---------------------------------------------------------

def test_service_candidates_keep_geography_and_market_unchanged():
    candidates = derive_adjacent_service_candidates(_TARGET_RECORD)
    assert candidates
    for c in candidates:
        assert c["geography"] == _TARGET_RECORD["geography"]
        assert c["market"] == "residential_homeowners"


def test_service_candidates_vary_only_service():
    candidates = derive_adjacent_service_candidates(_TARGET_RECORD)
    services = {c["service"] for c in candidates}
    assert "boiler_repair" not in services
    assert "boiler_service" in services


def test_service_candidates_unknown_service_is_rejected():
    record = {**_TARGET_RECORD, "service": "underfloor_heating_design"}
    with pytest.raises(DerivationError):
        derive_adjacent_service_candidates(record)


def test_service_candidates_missing_geography_is_rejected():
    record = dict(_TARGET_RECORD)
    del record["geography"]
    with pytest.raises(DerivationError):
        derive_adjacent_service_candidates(record)


# --- derive_one_hop_candidates ---------------------------------------------------------

def test_one_hop_candidates_combines_both_axes_without_compound_jumps():
    candidates = derive_one_hop_candidates(_TARGET_RECORD)
    geo_only = derive_adjacent_geo_candidates(_TARGET_RECORD)
    service_only = derive_adjacent_service_candidates(_TARGET_RECORD)
    assert len(candidates) == len(geo_only) + len(service_only)
    for c in candidates:
        changed_service = c["service"] != _TARGET_RECORD["service"]
        changed_geo = c["geography"]["locality"] != _TARGET_RECORD["geography"]["locality"]
        assert changed_service != changed_geo  # exactly one axis changed, never both, never neither


def test_one_hop_candidates_returns_whatever_axis_is_curated_when_the_other_is_not():
    record = {**_TARGET_RECORD, "service": "underfloor_heating_design"}  # no curated service adjacency
    candidates = derive_one_hop_candidates(record)
    assert candidates  # geo axis still yields real candidates
    assert all(c["service"] == "underfloor_heating_design" for c in candidates)


def test_one_hop_candidates_empty_when_neither_axis_is_curated():
    record = {
        "target_type": "local_service_business",
        "service": "underfloor_heating_design",
        "market": "residential_homeowners",
        "geography": {"locality": "Nowhereville", "region": "Nowhere", "country": "UK"},
    }
    assert derive_one_hop_candidates(record) == []
