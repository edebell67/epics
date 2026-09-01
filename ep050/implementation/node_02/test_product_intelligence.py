# epics/ep_050_distribution_engine/implementation/node_02/test_product_intelligence.py
# EP050 Node 02 — Product Intelligence test suite.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-16 · Initial unit/contract/integration/regression suite for Node 02.
#
# All tests run fully offline against temp fixture files (pytest tmp_path).
# No network call, no production datastore, no external side effect.

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
from registration import TargetRegistry  # noqa: E402

from product_intelligence import (
    ConflictError,
    ProductIntelligenceRegistry,
    UnknownTargetError,
    ValidationError,
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
    evidence_sources=["EP050 master spec worked example (boiler pressure)"],
)


@pytest.fixture
def target_registry(tmp_path):
    registry = TargetRegistry(tmp_path / "node_01_targets.json")
    registry.register(**SYNTHETIC_TARGET)
    return registry


@pytest.fixture
def registry(tmp_path, target_registry):
    return ProductIntelligenceRegistry(tmp_path / "node_02_product_intelligence.json", target_registry)


def _payload(target_id: str) -> dict:
    return dict(SYNTHETIC_PRODUCT, target_id=target_id)


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.problem == SYNTHETIC_PRODUCT["problem"]
    assert record.features == SYNTHETIC_PRODUCT["features"]
    assert record.recorded_at  # non-empty ISO timestamp


def test_evidence_sources_defaults_to_empty_list_when_omitted(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    del payload["evidence_sources"]
    record = registry.register(**payload)
    assert record.evidence_sources == []


# --- Node01->02 contract/integration test (target lineage) ------------------

def test_unregistered_target_is_rejected_fail_closed(registry):
    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_nonexistent_target"))


def test_registered_target_from_real_node_01_registry_is_accepted(tmp_path):
    target_storage = tmp_path / "node_01_targets.json"
    target_registry = TargetRegistry(target_storage)
    registered_target = target_registry.register(**SYNTHETIC_TARGET)

    product_registry = ProductIntelligenceRegistry(tmp_path / "node_02.json", target_registry)
    record = product_registry.register(**_payload(registered_target.target_id))
    assert record.target_id == registered_target.target_id


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize(
    "missing_field",
    ["target_id", "problem", "solution", "features", "benefits", "differentiators", "commercial_model", "customer_outcome"],
)
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = _payload("tgt_boiler_repair_blackheath")
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_empty_string_required_field_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["problem"] = "   "
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid enum/type failures ----------------------------------------------

def test_features_wrong_type_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["features"] = "same-day callout"  # should be a list
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_features_empty_list_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["features"] = []
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_features_list_with_non_string_item_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["features"] = ["Same-day callout", 42]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_evidence_sources_wrong_type_is_rejected(registry):
    payload = _payload("tgt_boiler_repair_blackheath")
    payload["evidence_sources"] = "not a list"
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
    conflicting["commercial_model"] = "Subscription-based annual boiler cover."
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    stored = registry.get("tgt_boiler_repair_blackheath")
    assert stored.commercial_model == SYNTHETIC_PRODUCT["commercial_model"]


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(tmp_path, target_registry):
    storage_path = tmp_path / "node_02_product_intelligence.json"
    registry_a = ProductIntelligenceRegistry(storage_path, target_registry)
    registered = registry_a.register(**_payload("tgt_boiler_repair_blackheath"))

    registry_b = ProductIntelligenceRegistry(storage_path, target_registry)
    fetched = registry_b.get(registered.target_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 02 registration must not open any network socket")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    assert record.target_id == "tgt_boiler_repair_blackheath"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(tmp_path, target_registry):
    storage_path = tmp_path / "node_02_product_intelligence.json"
    registry = ProductIntelligenceRegistry(storage_path, target_registry)

    record = registry.register(**_payload("tgt_boiler_repair_blackheath"))
    registry.register(**_payload("tgt_boiler_repair_blackheath"))  # idempotent
    assert len(registry.list()) == 1

    fetched = registry.get(record.target_id)
    assert fetched.target_id == record.target_id

    with pytest.raises(ConflictError):
        conflicting = _payload("tgt_boiler_repair_blackheath")
        conflicting["problem"] = "A different, conflicting problem statement."
        registry.register(**conflicting)

    with pytest.raises(ValidationError):
        registry.register(**dict(_payload("tgt_boiler_repair_blackheath"), problem=""))

    with pytest.raises(UnknownTargetError):
        registry.register(**_payload("tgt_never_registered"))

    assert registry.get("tgt_nonexistent") is None
