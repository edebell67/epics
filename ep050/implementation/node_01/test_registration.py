# epics/ep_050_distribution_engine/implementation/node_01/test_registration.py
# EP050 Node 01 — App / Service Registration test suite.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-16 · Initial unit/contract/regression suite for Node 01 registration.
#
# All tests run fully offline against a temp fixture file (pytest tmp_path).
# No network call, no production datastore, no external side effect.

from __future__ import annotations

import socket

import pytest

from registration import (
    ConflictError,
    TargetRegistry,
    ValidationError,
    derive_target_id,
    slugify,
)

SYNTHETIC_TARGET = dict(
    target_type="service_market",
    service="boiler_repair",
    market="domestic_plumbing",
    geography={"locality": "Blackheath", "region": "London", "country": "UK"},
    app_id="ep047_trades_directory",
    status="active",
)


@pytest.fixture
def registry(tmp_path):
    return TargetRegistry(tmp_path / "node_01_targets.json")


# --- Positive registration -------------------------------------------------

def test_positive_registration_returns_expected_record(registry):
    record = registry.register(**SYNTHETIC_TARGET)
    assert record.target_id == "tgt_boiler_repair_blackheath"
    assert record.target_type == "service_market"
    assert record.service == "boiler_repair"
    assert record.market == "domestic_plumbing"
    assert record.status == "active"
    assert record.registered_at  # non-empty ISO timestamp


# --- Deterministic / stable identity ----------------------------------------

def test_derive_target_id_matches_downstream_contract_fixture():
    # Must match the target_id already published in the Node 05->11 contract
    # seed fixture (integration/proposals/gemini/20260816_node10_to_node11_contract_proposal_v1.md).
    target_id = derive_target_id("boiler_repair", {"locality": "Blackheath", "region": "London", "country": "UK"})
    assert target_id == "tgt_boiler_repair_blackheath"


def test_derive_target_id_is_deterministic_across_calls():
    args = ("boiler_repair", {"locality": "Blackheath", "region": "London", "country": "UK"})
    assert derive_target_id(*args) == derive_target_id(*args)


def test_slugify_normalizes_case_and_punctuation():
    assert slugify("Boiler Repair!") == "boiler_repair"
    assert slugify("  Blackheath ") == "blackheath"


# --- Required-field failures -------------------------------------------------

@pytest.mark.parametrize("missing_field", ["target_type", "service", "market", "geography"])
def test_missing_required_field_is_rejected(registry, missing_field):
    payload = dict(SYNTHETIC_TARGET)
    del payload[missing_field]
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_missing_geography_subfield_is_rejected(registry):
    payload = dict(SYNTHETIC_TARGET)
    payload["geography"] = {"locality": "Blackheath", "region": "London"}  # missing country
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Invalid enum/type failures ----------------------------------------------

def test_invalid_target_type_format_is_rejected(registry):
    payload = dict(SYNTHETIC_TARGET, target_type="Service-Market!")
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_invalid_status_enum_is_rejected(registry):
    payload = dict(SYNTHETIC_TARGET, status="deleted_forever")
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_geography_wrong_type_is_rejected(registry):
    payload = dict(SYNTHETIC_TARGET, geography="Blackheath, London, UK")
    with pytest.raises(ValidationError):
        registry.register(**payload)


def test_app_id_wrong_type_is_rejected(registry):
    payload = dict(SYNTHETIC_TARGET, app_id=12345)
    with pytest.raises(ValidationError):
        registry.register(**payload)


# --- Duplicate idempotency ----------------------------------------------------

def test_identical_reregistration_is_idempotent_and_does_not_duplicate(registry):
    first = registry.register(**SYNTHETIC_TARGET)
    second = registry.register(**SYNTHETIC_TARGET)
    assert first.target_id == second.target_id
    assert len(registry.list()) == 1


# --- Conflicting duplicate rejection -----------------------------------------

def test_conflicting_duplicate_same_id_different_fields_is_rejected(registry):
    registry.register(**SYNTHETIC_TARGET)
    conflicting = dict(SYNTHETIC_TARGET, market="commercial_plumbing")  # same target_id, different market
    with pytest.raises(ConflictError):
        registry.register(**conflicting)
    # The original record must remain unmodified.
    stored = registry.get("tgt_boiler_repair_blackheath")
    assert stored.market == "domestic_plumbing"


# --- Serialization / persistence (local fixture-only storage) ---------------

def test_persistence_round_trip_via_new_registry_instance(tmp_path):
    storage_path = tmp_path / "node_01_targets.json"
    registry_a = TargetRegistry(storage_path)
    registered = registry_a.register(**SYNTHETIC_TARGET)

    registry_b = TargetRegistry(storage_path)  # simulate a fresh process reopening the same fixture file
    fetched = registry_b.get(registered.target_id)
    assert fetched is not None
    assert fetched.to_dict() == registered.to_dict()


def test_storage_file_is_local_json_not_a_database_connection(tmp_path):
    storage_path = tmp_path / "node_01_targets.json"
    registry = TargetRegistry(storage_path)
    registry.register(**SYNTHETIC_TARGET)
    assert storage_path.exists()
    assert storage_path.suffix == ".json"


# --- No-network / no-external-side-effect assertion --------------------------

def test_registration_makes_no_network_call(registry, monkeypatch):
    def _blocked_socket(*args, **kwargs):
        raise AssertionError("Node 01 registration must not open any network socket")

    monkeypatch.setattr(socket, "socket", _blocked_socket)
    record = registry.register(**SYNTHETIC_TARGET)
    assert record.target_id == "tgt_boiler_repair_blackheath"


# --- Regression suite: full lifecycle in one pass ----------------------------

def test_full_lifecycle_regression(tmp_path):
    storage_path = tmp_path / "node_01_targets.json"
    registry = TargetRegistry(storage_path)

    # Register, re-register idempotently, list, get, and confirm conflict rejection all in one pass.
    record = registry.register(**SYNTHETIC_TARGET)
    registry.register(**SYNTHETIC_TARGET)  # idempotent
    assert len(registry.list()) == 1

    fetched = registry.get(record.target_id)
    assert fetched.target_id == record.target_id

    with pytest.raises(ConflictError):
        registry.register(**dict(SYNTHETIC_TARGET, product="emergency_callout"))

    with pytest.raises(ValidationError):
        registry.register(**dict(SYNTHETIC_TARGET, service=""))

    assert registry.get("tgt_nonexistent_target") is None
