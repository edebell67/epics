# epics/ep_050_distribution_engine/implementation/node_03/test_audience_definition.py
# EP050 Node 03 — Audience Definition test suite.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-16 · Initial unit/contract/integration/regression suite for Node 03.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no production datastore, no external side effect.

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_02"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402

from audience_definition import (
    AudienceSegmentRegistry,
    ConflictError,
    UnknownTargetError,
    ValidationError,
    derive_segment_id,
)

SYNTHETIC_TARGET = dict(
    target_type="service_market",
    service="boiler_repair",
    market="domestic_plumbing",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    app_id="ep047_trades_directory",
    status="active",
)

SYNTHETIC_PRODUCT = dict(
    problem="Homeowners lose boiler pressure and hot water with no clear diagnosis path.",
    solution="A vetted local boiler-repair callout that diagnoses and restores pressure same-day.",
    features=["Same-day callout", "Fixed diagnostic fee", "Vetted local engineers"],
    benefits=["Hot water restored quickly", "No guesswork on cause", "Transparent pricing"],
    differentiators=["Local Blackheath coverage", "Vetted-only engineer network"],
    commercial_model="Fixed diagnostic fee plus quoted repair cost.",
    customer_outcome="Working boiler and restored hot water within 24 hours.",
)

SYNTHETIC_SEGMENT = dict(
    segment_name="Blackheath homeowner, boiler pressure loss",
    needs=["Restore hot water quickly", "Understand the cause of pressure loss"],
    pains=["No heating or hot water", "Uncertainty over callout cost"],
    urgency="high",
    eligibility_geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    exclusions=["Commercial/industrial boiler systems"],
    evidence_sources=["EP050 master spec worked example (boiler pressure)"],
)


@pytest.fixture
def target_registry(tmp_path):
    registry = TargetRegistry(tmp_path / "node_01_targets.json")
    registry.register(**SYNTHETIC_TARGET)
    return registry


@pytest.fixture
def product_registry(tmp_path, target_registry):
    registry = ProductIntelligenceRegistry(tmp_path / "node_02_product_intelligence.json", target_registry)
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_PRODUCT)
    return registry


@pytest.fixture
def registry(tmp_path, target_registry, product_registry):
    return AudienceSegmentRegistry(
        tmp_path / "node_03_audience_segments.json", target_registry, product_registry
    )


def _payload(target_id: str) -> dict:
    return dict(SYNTHETIC_SEGMENT, target_id=target_id)


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    assert record.segment_id == "tgt_boiler_repair_blackheath__seg_blackheath_homeowner_boiler_pressure_loss"
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.urgency == "high"
    assert record.recorded_at


def test_derive_segment_id_is_deterministic():
    args = ("tgt_boiler_repair_blackheath", "Blackheath homeowner, boiler pressure loss")
    assert derive_segment_id(*args) == derive_segment_id(*args)


def test_optional_fields_default_to_empty_list_when_omitted(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    del payload["exclusions"]
    del payload["evidence_sources"]
    record = registry.register(**payload)
    assert record.exclusions == []
    assert record.evidence_sources == []


# --- Node01+Node02->03 contract/integration test ------------------------------

def test_target_not_in_node_01_is_rejected_fail_closed(registry):
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_never_registered"))


def test_target_in_node_01_but_missing_node_02_is_rejected_fail_closed(tmp_path, target_registry):
    # A second target is registered in Node 01 but never given a Node 02 product intelligence record.
    target_registry.register(
        target_type="service_market",
        service="drain_clearance",
        market="domestic_plumbing",
        geography={"locality": "Lewisham", "region": "London", "country": "UK"},
    )
    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_drain_clearance_lewisham"))


def test_registered_target_with_real_node_01_and_node_02_registries_is_accepted(tmp_path):
    target_registry = TargetRegistry(tmp_path / "node_01.json")
    registered_target = target_registry.register(**SYNTHETIC_TARGET)
    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    product_registry.register(target_id=registered_target.target_id, **SYNTHETIC_PRODUCT)
    audience_registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    record = audience_registry.register(**_payload(registered_target.target_id))
    assert record.target_id == registered_target.target_id


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize(
    "missing_field", ["target_id", "segment_name", "needs", "pains", "urgency", "eligibility_geography"]
)
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = _payload("tgt_boiler_repair_blackheath")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_missing_geography_subfield_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["eligibility_geography"] = {"locality": "Blackheath", "region": "London"}  # missing country
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid enum/type failures ----------------------------------------------

def test_invalid_urgency_enum_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["urgency"] = "asap"
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_needs_wrong_type_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["needs"] = "restore hot water"  # should be a list
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_needs_empty_list_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["needs"] = []
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_eligibility_geography_wrong_type_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["eligibility_geography"] = "Blackheath, London, UK"
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Prohibited PII rejection -------------------------------------------------

def test_email_address_in_needs_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["needs"] = ["Contact homeowner at jane.doe@example.com for follow-up"]
    with pytest.raises(ValidationError, match="email"):
        registry.register(**payload)


def test_phone_number_in_pains_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["pains"] = ["Call the customer on 020 7946 0958 to confirm"]
    with pytest.raises(ValidationError, match="phone"):
        registry.register(**payload)


def test_email_address_in_segment_name_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["segment_name"] = "Contact via jane.doe@example.com"
    with pytest.raises(ValidationError, match="email"):
        registry.register(**payload)


def test_phone_number_in_exclusions_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["exclusions"] = ["Excluded: reach out to +44 20 7946 0958"]
    with pytest.raises(ValidationError, match="phone"):
        registry.register(**payload)


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_reregistration_is_idempotent_and_does_not_duplicate(registry):
    first = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    second = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    assert first.segment_id == second.segment_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_duplicate_same_segment_different_content_is_rejected(registry):
    registry.register(**_payload("tgt_boiler_repair_blackheath"))
    conflicting = _payload("tgt_boiler_repair_blackheath")
    conflicting["urgency"] = "emergency"
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    stored = registry.get(derive_segment_id("tgt_boiler_repair_blackheath", SYNTHETIC_SEGMENT["segment_name"]))
    assert stored.urgency == "high"


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(tmp_path, target_registry, product_registry):
    storage_path = tmp_path / "node_03_audience_segments.json"
    registry_a = AudienceSegmentRegistry(storage_path, target_registry, product_registry)
    registered = registry_a.register(**_payload("tgt_boiler_repair_blackheath"))

    registry_b = AudienceSegmentRegistry(storage_path, target_registry, product_registry)
    fetched = registry_b.get(registered.segment_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 03 registration must not open any network socket")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    assert record.target_id == "tgt_boiler_repair_blackheath"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(tmp_path, target_registry, product_registry):
    storage_path = tmp_path / "node_03_audience_segments.json"
    registry = AudienceSegmentRegistry(storage_path, target_registry, product_registry)

    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    registry.register(**_payload("tgt_boiler_repair_blackheath"))  # idempotent
    assert len(registry.list()) == 1
    assert len(registry.list_for_target("tgt_boiler_repair_blackheath")) == 1

    fetched = registry.get(record.segment_id)
    assert fetched.segment_id == record.segment_id

    with pytest.raises(ConflictError):
        conflicting = _payload("tgt_boiler_repair_blackheath")
        conflicting["needs"] = ["A materially different need"]
        registry.register(**conflicting)

    with pytest.raises(ValidationError):
        registry.register(**dict(_payload("tgt_boiler_repair_blackheath"), urgency="invalid"))

    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_never_registered"))

    assert registry.get("tgt_nonexistent__seg_missing") is None
