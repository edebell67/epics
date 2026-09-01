# epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_candidate_v1_1_test.py — Offline tests for the Hermes consumer-corrected Node 19-to-20 contract candidate.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-16 · Adds strict ISO-8601 consumer timestamp checks after format-only validation accepted an invalid value.
# v1.0.0 · 2026-08-16 · Initial deterministic, no-network validation of candidate v1.1.0.

"""Exercise the proposed schemas and consumer semantics without implementing Node 20."""

from __future__ import annotations

import hashlib
import json
import socket
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "proposals/hermes/20260816_node19_to_node20_consumer_contract_candidate_v1_1.json"


def load_contract() -> dict[str, Any]:
    """Return the local candidate document; this function has no network behavior."""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def validate(schema: dict[str, Any], value: dict[str, Any]) -> None:
    """Raise ValueError rather than exposing JSON Schema implementation exceptions."""
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    except ValidationError as error:
        raise ValueError(error.message) from error


def plan_id(payload: dict[str, Any]) -> str:
    """Derive the proposed stable identifier from the documented five-field key."""
    key = {
        "asset_id": payload["asset_id"],
        "channel": payload["schedule_request"]["channel"],
        "destination_url": payload["cta_definition"]["destination_url"],
        "audience": payload["schedule_request"]["audience"],
        "scheduled_at": payload["schedule_request"]["scheduled_at"],
    }
    encoded = json.dumps(key, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "mpp_" + hashlib.sha256(encoded).hexdigest()


def validate_input(payload: dict[str, Any], contract: dict[str, Any]) -> None:
    """Apply strict schema plus the two cross-field consumer gates."""
    validate(contract["approved_asset_package_schema"], payload)
    for timestamp_name, timestamp_value in (
        ("generated_at", payload["generated_at"]),
        ("compliance_stamp.checked_at", payload["compliance_stamp"]["checked_at"]),
        ("schedule_request.scheduled_at", payload["schedule_request"]["scheduled_at"]),
    ):
        try:
            datetime.fromisoformat(timestamp_value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{timestamp_name} must be ISO-8601 date-time") from error
    if payload["cta_definition"]["tracking_params"]["asset_id"] != payload["asset_id"]:
        raise ValueError("tracking asset_id must equal asset_id")
    if payload["schedule_request"]["channel"] not in payload["target_channels"]:
        raise ValueError("schedule channel must be a declared target channel")


def build_mock_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Project a validated fixture into the proposed non-executing consumer output."""
    return {
        "schema_version": payload["schema_version"],
        "publication_plan_id": plan_id(payload),
        "asset_id": payload["asset_id"],
        "target_id": payload["target_id"],
        "opportunity_id": payload["opportunity_id"],
        "channel": payload["schedule_request"]["channel"],
        "audience": payload["schedule_request"]["audience"],
        "scheduled_at": payload["schedule_request"]["scheduled_at"],
        "cta": {
            "label": payload["cta_definition"]["cta_label"],
            "type": payload["cta_definition"]["cta_type"],
            "destination_url": payload["cta_definition"]["destination_url"],
            "tracking_params": payload["cta_definition"]["tracking_params"],
        },
        "approval_state": "approved",
        "external_action": False,
    }


def fixture() -> dict[str, Any]:
    """Return a fully synthetic approved asset package."""
    return {
        "schema_version": "1.1.0-candidate",
        "asset_id": "ast_20260816_boiler_press_faq_01",
        "target_id": "tgt_boiler_repair_blackheath",
        "opportunity_id": "opp_20260816_boiler_press_01",
        "asset_type": "troubleshooting_guide",
        "headline": "Synthetic boiler pressure guide",
        "body_content": {"summary": "Synthetic safe summary.", "steps": ["Check gauge."], "safety_disclaimer": "Use a qualified engineer when unsafe."},
        "cta_definition": {"cta_label": "Synthetic quote request", "cta_type": "quote_request", "destination_url": "https://local-trades-directory.test/quote", "tracking_params": {"utm_source": "distribution_engine", "utm_medium": "search_landing", "utm_campaign": "synthetic", "asset_id": "ast_20260816_boiler_press_faq_01"}},
        "compliance_stamp": {"approved": True, "checked_at": "2026-08-16T19:30:00+01:00", "validator_version": "v1.1.0_candidate", "disclaimer_verified": True, "facts_verified": True},
        "target_channels": ["search_landing"],
        "schedule_request": {"channel": "search_landing", "audience": "synthetic homeowners", "scheduled_at": "2026-08-17T09:00:00+01:00"},
        "generated_at": "2026-08-16T19:29:50+01:00",
    }


def expect_reject(name: str, candidate: dict[str, Any], contract: dict[str, Any]) -> None:
    try:
        validate_input(candidate, contract)
    except ValueError:
        print(f"PASS {name}: rejected")
        return
    raise AssertionError(f"FAIL {name}: unsafe candidate was accepted")


def assert_no_network() -> None:
    """Prove validation does not attempt socket resolution or connection."""
    original = socket.socket
    socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network attempted"))
    try:
        contract = load_contract()
        candidate = fixture()
        validate_input(candidate, contract)
        validate(contract["mock_publication_plan_schema"], build_mock_plan(candidate))
    finally:
        socket.socket = original
    print("PASS no-network assertion")


def main() -> None:
    contract = load_contract()
    good = fixture()
    validate_input(good, contract)
    first_plan = build_mock_plan(good)
    validate(contract["mock_publication_plan_schema"], first_plan)
    assert first_plan == build_mock_plan(deepcopy(good))
    print("PASS approved fixture and stable idempotent mock plan")
    cases = []
    for name, mutate in (
        ("unapproved compliance", lambda x: x["compliance_stamp"].update({"approved": False})),
        ("unverified disclaimer", lambda x: x["compliance_stamp"].update({"disclaimer_verified": False})),
        ("unverified facts", lambda x: x["compliance_stamp"].update({"facts_verified": False})),
        ("unsafe destination", lambda x: x["cta_definition"].update({"destination_url": "https://real.example/quote"})),
        ("tracking lineage mismatch", lambda x: x["cta_definition"]["tracking_params"].update({"asset_id": "ast_other"})),
        ("empty headline", lambda x: x.update({"headline": ""})),
        ("invalid generated timestamp", lambda x: x.update({"generated_at": "not-a-time"})),
        ("undeclared schedule channel", lambda x: x["schedule_request"].update({"channel": "social_post"})),
        ("unexpected top-level property", lambda x: x.update({"adapter": "publish"})),
    ):
        candidate = deepcopy(good)
        mutate(candidate)
        cases.append((name, candidate))
    for name, candidate in cases:
        expect_reject(name, candidate, contract)
    external_plan = deepcopy(first_plan)
    external_plan["external_action"] = True
    try:
        validate(contract["mock_publication_plan_schema"], external_plan)
    except ValueError:
        print("PASS external action output: rejected")
    else:
        raise AssertionError("FAIL external action output: accepted")
    assert_no_network()
    print("PASS 12/12 offline candidate contract checks; no Node 20 implementation or external action performed")


if __name__ == "__main__":
    main()
