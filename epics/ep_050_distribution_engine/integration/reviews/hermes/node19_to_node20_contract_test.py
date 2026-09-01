# epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_contract_test.py — Offline consumer-contract checks for the Node 19 to Node 20 boundary.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-16 · Initial deterministic offline checks expose consumer safety requirements before Node 20 implementation.

"""Run positive and negative consumer-contract checks without network or writes."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from urllib.parse import urlparse


def validate_for_node_20(payload: dict[str, object]) -> None:
    """Accept only a complete, approved, internally safe mock publishing input."""
    required = {
        "asset_id", "target_id", "opportunity_id", "asset_type", "headline",
        "body_content", "cta_definition", "compliance_stamp", "target_channels",
        "generated_at",
    }
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"missing top-level fields: {sorted(missing)}")
    identity_values = [payload[field] for field in (
        "asset_id", "target_id", "opportunity_id", "asset_type", "headline", "generated_at"
    )]
    if not all(isinstance(value, str) and value.strip() for value in identity_values):
        raise ValueError("identity and timestamp fields must be non-empty strings")
    datetime.fromisoformat(str(payload["generated_at"]))

    compliance = payload["compliance_stamp"]
    if not isinstance(compliance, dict) or not all(
        compliance.get(key) is True
        for key in ("approved", "disclaimer_verified", "facts_verified")
    ):
        raise ValueError("compliance stamp is not fully approved")
    datetime.fromisoformat(str(compliance.get("checked_at", "")))
    if not isinstance(compliance.get("validator_version"), str) or not compliance["validator_version"]:
        raise ValueError("validator version is required")

    body = payload["body_content"]
    if not isinstance(body, dict) or not all(isinstance(body.get(key), str) and body[key].strip()
                                             for key in ("summary", "safety_disclaimer")):
        raise ValueError("safe body content is required")
    if not isinstance(body.get("steps"), list) or not body["steps"] or not all(
        isinstance(step, str) and step.strip() for step in body["steps"]
    ):
        raise ValueError("at least one non-empty step is required")

    channels = payload["target_channels"]
    if not isinstance(channels, list) or not channels or not all(
        channel in {"search_landing", "social_post", "video_host", "local_directory"}
        for channel in channels
    ):
        raise ValueError("at least one known target channel is required")

    cta = payload["cta_definition"]
    if not isinstance(cta, dict):
        raise ValueError("CTA definition is required")
    tracking = cta.get("tracking_params")
    if not isinstance(tracking, dict) or tracking.get("asset_id") != payload["asset_id"]:
        raise ValueError("tracking asset_id must match asset_id")
    destination = cta.get("destination_url")
    parsed = urlparse(destination if isinstance(destination, str) else "")
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".test"):
        raise ValueError("destination must be an HTTPS synthetic .test URL")


def fixture() -> dict[str, object]:
    return {
        "asset_id": "ast_20260816_boiler_press_faq_01",
        "target_id": "tgt_boiler_repair_blackheath",
        "opportunity_id": "opp_20260816_boiler_press_01",
        "asset_type": "troubleshooting_guide",
        "headline": "Synthetic boiler pressure guide",
        "body_content": {"summary": "Synthetic safe summary.", "steps": ["Check gauge."], "safety_disclaimer": "Use a qualified engineer when unsafe."},
        "cta_definition": {"cta_label": "Synthetic quote request", "cta_type": "quote_request", "destination_url": "https://local-trades-directory.test/quote", "tracking_params": {"utm_source": "distribution_engine", "utm_medium": "search_landing", "utm_campaign": "synthetic", "asset_id": "ast_20260816_boiler_press_faq_01"}},
        "compliance_stamp": {"approved": True, "checked_at": "2026-08-16T19:30:00+01:00", "validator_version": "v1.0.0_node19_rule_engine", "disclaimer_verified": True, "facts_verified": True},
        "target_channels": ["search_landing"],
        "generated_at": "2026-08-16T19:29:50+01:00",
    }


def expect_reject(name: str, payload: dict[str, object]) -> None:
    try:
        validate_for_node_20(payload)
    except ValueError:
        print(f"PASS {name}: rejected")
        return
    raise AssertionError(f"FAIL {name}: unsafe payload was accepted")


def main() -> None:
    approved = fixture()
    validate_for_node_20(approved)
    print("PASS approved fixture: accepted")
    for name, mutate in (
        ("unapproved compliance", lambda value: value["compliance_stamp"].update({"approved": False})),
        ("unverified disclaimer", lambda value: value["compliance_stamp"].update({"disclaimer_verified": False})),
        ("unverified facts", lambda value: value["compliance_stamp"].update({"facts_verified": False})),
        ("unsafe destination", lambda value: value["cta_definition"].update({"destination_url": "https://real.example/quote"})),
        ("tracking lineage mismatch", lambda value: value["cta_definition"]["tracking_params"].update({"asset_id": "ast_other"})),
        ("empty channels", lambda value: value.update({"target_channels": []})),
    ):
        candidate = deepcopy(approved)
        mutate(candidate)
        expect_reject(name, candidate)
    print("PASS 7/7 offline consumer checks; no network or external action performed")


if __name__ == "__main__":
    main()
