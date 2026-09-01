# epics/ep_050_distribution_engine/implementation/node_04/test_conversion_definition.py
# EP050 Node 04 — Conversion Definition test suite.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial unit/contract/integration/regression suite for Node 04.
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_03"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402

from conversion_definition import (
    MASTER_SPEC_STAGES,
    ConflictError,
    ConversionDefinitionRegistry,
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
    ["visit", "engage"],
    ["engage", "tool_use"],
    ["tool_use", "enquiry"],
    ["enquiry", "lead"],
    ["lead", "qualified_lead"],
    ["qualified_lead", "booking"],
    ["booking", "sale"],
    ["sale", "revenue"],
]


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
def audience_registry(tmp_path, target_registry, product_registry):
    registry = AudienceSegmentRegistry(tmp_path / "node_03_audience_segments.json", target_registry, product_registry)
    registry.register(target_id="tgt_boiler_repair_blackheath", **SYNTHETIC_SEGMENT)
    return registry


@pytest.fixture
def registry(tmp_path, target_registry, product_registry, audience_registry):
    return ConversionDefinitionRegistry(
        tmp_path / "node_04_conversion_definitions.json", target_registry, product_registry, audience_registry
    )


def _payload(target_id: str) -> dict:
    return dict(
        target_id=target_id,
        stages=MASTER_SPEC_STAGES,
        allowed_transitions=MASTER_SPEC_TRANSITIONS,
        success_stage_id="sale",
        success_criteria="A lead reaches the sale stage with a recorded, attributable outcome.",
    )


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert len(record.stages) == 9
    assert record.success_stage_id == "sale"
    assert record.recorded_at


# --- Node01+Node02+Node03->04 contract/integration test ----------------------

def test_target_not_in_node_01_is_rejected_fail_closed(registry):
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_never_registered"))


def test_target_missing_node_02_is_rejected_fail_closed(tmp_path, target_registry):
    target_registry.register(
        target_type="service_market", service="drain_clearance", market="domestic_plumbing",
        geography={"locality": "Lewisham", "region": "London", "country": "UK"},
    )
    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    audience_registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    registry = ConversionDefinitionRegistry(tmp_path / "node_04.json", target_registry, product_registry, audience_registry)
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_drain_clearance_lewisham"))


def test_target_missing_node_03_is_rejected_fail_closed(tmp_path, target_registry, product_registry):
    audience_registry = AudienceSegmentRegistry(tmp_path / "node_03_empty.json", target_registry, product_registry)
    registry = ConversionDefinitionRegistry(
        tmp_path / "node_04.json", target_registry, product_registry, audience_registry
    )
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_boiler_repair_blackheath"))


def test_registered_target_with_all_three_real_upstream_registries_is_accepted(tmp_path):
    target_registry = TargetRegistry(tmp_path / "node_01.json")
    target = target_registry.register(**SYNTHETIC_TARGET)
    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    product_registry.register(target_id=target.target_id, **SYNTHETIC_PRODUCT)
    audience_registry = AudienceSegmentRegistry(tmp_path / "node_03.json", target_registry, product_registry)
    audience_registry.register(target_id=target.target_id, **SYNTHETIC_SEGMENT)
    conversion_registry = ConversionDefinitionRegistry(
        tmp_path / "node_04.json", target_registry, product_registry, audience_registry
    )
    record = conversion_registry.register(**_payload(target.target_id))
    assert record.target_id == target.target_id


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize(
    "missing_field", ["target_id", "stages", "allowed_transitions", "success_stage_id", "success_criteria"]
)
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = _payload("tgt_boiler_repair_blackheath")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid stages ------------------------------------------------------------

def test_duplicate_stage_id_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["stages"] = [
        {"stage_id": "visit", "label": "Visit", "order": 1},
        {"stage_id": "visit", "label": "Visit again", "order": 2},
    ]
    payload["allowed_transitions"] = [["visit", "visit"]]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_duplicate_order_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["stages"] = [
        {"stage_id": "visit", "label": "Visit", "order": 1},
        {"stage_id": "engage", "label": "Engage", "order": 1},
    ]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_order_gap_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["stages"] = [
        {"stage_id": "visit", "label": "Visit", "order": 1},
        {"stage_id": "engage", "label": "Engage", "order": 3},
    ]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_non_positive_order_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["stages"] = [{"stage_id": "visit", "label": "Visit", "order": 0}]
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid transitions -------------------------------------------------------

def test_transition_referencing_unknown_stage_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["allowed_transitions"] = [["visit", "nonexistent_stage"]]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_backward_transition_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["allowed_transitions"] = [["engage", "visit"]]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_self_transition_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["allowed_transitions"] = [["visit", "visit"]]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_duplicate_transition_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["allowed_transitions"] = [["visit", "engage"], ["visit", "engage"]]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_success_stage_id_not_in_stages_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["success_stage_id"] = "not_a_real_stage"
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_reregistration_is_idempotent_and_does_not_duplicate(registry):
    first = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    second = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    assert first.target_id == second.target_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_duplicate_same_target_different_content_is_rejected(registry):
    registry.register(**_payload("tgt_boiler_repair_blackheath"))
    conflicting = _payload("tgt_boiler_repair_blackheath")
    conflicting["success_stage_id"] = "revenue"
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    stored = registry.get("tgt_boiler_repair_blackheath")
    assert stored.success_stage_id == "sale"


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(tmp_path, target_registry, product_registry, audience_registry):
    storage_path = tmp_path / "node_04_conversion_definitions.json"
    registry_a = ConversionDefinitionRegistry(storage_path, target_registry, product_registry, audience_registry)
    registered = registry_a.register(**_payload("tgt_boiler_repair_blackheath"))

    registry_b = ConversionDefinitionRegistry(storage_path, target_registry, product_registry, audience_registry)
    fetched = registry_b.get(registered.target_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 04 registration must not open any network socket")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    assert record.target_id == "tgt_boiler_repair_blackheath"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(tmp_path, target_registry, product_registry, audience_registry):
    storage_path = tmp_path / "node_04_conversion_definitions.json"
    registry = ConversionDefinitionRegistry(storage_path, target_registry, product_registry, audience_registry)

    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    registry.register(**_payload("tgt_boiler_repair_blackheath"))  # idempotent
    assert len(registry.list()) == 1

    fetched = registry.get(record.target_id)
    assert fetched.target_id == record.target_id

    with pytest.raises(ConflictError):
        conflicting = _payload("tgt_boiler_repair_blackheath")
        conflicting["success_criteria"] = "A different, conflicting success criteria statement."
        registry.register(**conflicting)

    with pytest.raises(ValidationError):
        registry.register(**dict(_payload("tgt_boiler_repair_blackheath"), success_stage_id=""))

    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_never_registered"))

    assert registry.get("tgt_nonexistent") is None
