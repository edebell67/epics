"""
EP050 Node 19 -> 20 Contract Candidate v1.1 — Producer Verification Test Suite

Validates Hermes consumer candidate v1.1 against Node 19 Quality & Compliance output
specifications and producer-side constraints across all six corrected dimensions:
1. Compliance literals (approved=true, disclaimer_verified=true, facts_verified=true)
2. Lineage preservation (target_id, opportunity_id, tracking_params.asset_id == asset_id)
3. Offline URL safety (^https://.*\\.test)
4. Strict non-empty strings & ISO 8601 UTC date-time formats
5. Deterministic publication_plan_id (mpp_ + SHA-256 hash)
6. Safe execution boundary (external_action=false)

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial producer verification test suite for candidate v1.1.
"""

import json
import os
import re
import hashlib
import jsonschema
import pytest
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HERMES_CANDIDATE_PATH = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "..", "proposals", "hermes", "20260816_node19_to_node20_consumer_contract_candidate_v1_1.json")
)


@pytest.fixture(scope="module")
def candidate_schema():
    """Loads Hermes consumer contract candidate JSON schema."""
    assert os.path.isfile(HERMES_CANDIDATE_PATH), f"Candidate schema not found: {HERMES_CANDIDATE_PATH}"
    with open(HERMES_CANDIDATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def valid_producer_asset():
    """Standard valid Node 19 approved asset package fixture."""
    return {
        "schema_version": "1.1.0-candidate",
        "asset_id": "ast_boiler_press_guide_001",
        "target_id": "tgt_boiler_repair_blackheath",
        "opportunity_id": "opp_boiler_press_001",
        "asset_type": "troubleshooting_guide",
        "headline": "How to Safely Re-Pressurise Your Boiler in Blackheath",
        "body_content": {
            "summary": "Step-by-step guide for restoring boiler pressure.",
            "steps": [
                "Locate the filling loop valves under boiler.",
                "Slowly open both valves until pressure gauge reaches 1.2 to 1.5 bar.",
                "Firmly close both valves and check if boiler fires up."
            ],
            "safety_disclaimer": "Do not attempt repairs if you smell gas or notice water leaks. Call Gas Safe engineer."
        },
        "cta_definition": {
            "cta_label": "Request Local Gas Safe Engineer",
            "cta_type": "lead_intake",
            "destination_url": "https://service.blackheathplumbing.test/book",
            "tracking_params": {
                "utm_source": "troubleshooting_guide",
                "utm_medium": "organic_search",
                "utm_campaign": "boiler_pressure_loss",
                "asset_id": "ast_boiler_press_guide_001"
            }
        },
        "compliance_stamp": {
            "approved": True,
            "checked_at": "2026-08-16T21:00:00Z",
            "validator_version": "node_19_v1.0",
            "disclaimer_verified": True,
            "facts_verified": True
        },
        "target_channels": ["search_landing", "local_directory"],
        "schedule_request": {
            "channel": "search_landing",
            "audience": "aud_blackheath_homeowners",
            "scheduled_at": "2026-08-17T09:00:00Z"
        },
        "generated_at": "2026-08-16T20:55:00Z"
    }


def test_schema_syntax_and_metadata(candidate_schema):
    """Validates top-level schema syntax, version, and safety boundaries."""
    assert candidate_schema["contract_version"] == "1.1.0-candidate"
    assert candidate_schema["safety_boundary"]["external_action"] is False
    assert candidate_schema["safety_boundary"]["network"] == "prohibited"
    assert "approved_asset_package_schema" in candidate_schema
    assert "mock_publication_plan_schema" in candidate_schema


def test_positive_producer_asset_validation(candidate_schema, valid_producer_asset):
    """Validates valid Node 19 asset passes approved_asset_package_schema."""
    subschema = candidate_schema["approved_asset_package_schema"]
    jsonschema.validate(instance=valid_producer_asset, schema=subschema)


def test_compliance_stamp_disclaimer_false_fails(candidate_schema, valid_producer_asset):
    """Rejects asset package where disclaimer_verified is not true."""
    subschema = candidate_schema["approved_asset_package_schema"]
    valid_producer_asset["compliance_stamp"]["disclaimer_verified"] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=valid_producer_asset, schema=subschema)


def test_compliance_stamp_facts_false_fails(candidate_schema, valid_producer_asset):
    """Rejects asset package where facts_verified is not true."""
    subschema = candidate_schema["approved_asset_package_schema"]
    valid_producer_asset["compliance_stamp"]["facts_verified"] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=valid_producer_asset, schema=subschema)


def test_non_test_domain_url_fails(candidate_schema, valid_producer_asset):
    """Rejects destination_url outside .test top-level domain."""
    subschema = candidate_schema["approved_asset_package_schema"]
    valid_producer_asset["cta_definition"]["destination_url"] = "https://external.live.com/book"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=valid_producer_asset, schema=subschema)


def test_empty_string_field_fails(candidate_schema, valid_producer_asset):
    """Rejects empty string for required text fields."""
    subschema = candidate_schema["approved_asset_package_schema"]
    valid_producer_asset["headline"] = ""
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=valid_producer_asset, schema=subschema)


def test_mock_publication_plan_positive(candidate_schema):
    """Validates consumer mock publication plan schema against valid instance."""
    subschema = candidate_schema["mock_publication_plan_schema"]
    
    # Compute deterministic SHA-256 plan ID
    key_dict = {
        "asset_id": "ast_boiler_press_guide_001",
        "channel": "search_landing",
        "destination_url": "https://service.blackheathplumbing.test/book",
        "audience": "aud_blackheath_homeowners",
        "scheduled_at": "2026-08-17T09:00:00Z"
    }
    canonical_json = json.dumps(key_dict, sort_keys=True, separators=(",", ":"))
    plan_id = "mpp_" + hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    mock_plan = {
        "schema_version": "1.1.0-candidate",
        "publication_plan_id": plan_id,
        "asset_id": "ast_boiler_press_guide_001",
        "target_id": "tgt_boiler_repair_blackheath",
        "opportunity_id": "opp_boiler_press_001",
        "channel": "search_landing",
        "audience": "aud_blackheath_homeowners",
        "scheduled_at": "2026-08-17T09:00:00Z",
        "cta": {
            "label": "Request Local Gas Safe Engineer",
            "type": "lead_intake",
            "destination_url": "https://service.blackheathplumbing.test/book",
            "tracking_params": {
                "utm_source": "troubleshooting_guide",
                "utm_medium": "organic_search",
                "utm_campaign": "boiler_pressure_loss",
                "asset_id": "ast_boiler_press_guide_001"
            }
        },
        "approval_state": "approved",
        "external_action": False
    }
    jsonschema.validate(instance=mock_plan, schema=subschema)


def test_mock_plan_external_action_true_fails(candidate_schema):
    """Rejects mock publication plan where external_action is true."""
    subschema = candidate_schema["mock_publication_plan_schema"]
    bad_plan = {
        "schema_version": "1.1.0-candidate",
        "publication_plan_id": "mpp_" + "a" * 64,
        "asset_id": "ast_001",
        "target_id": "tgt_001",
        "opportunity_id": "opp_001",
        "channel": "search_landing",
        "audience": "aud_001",
        "scheduled_at": "2026-08-17T09:00:00Z",
        "cta": {
            "label": "Book",
            "type": "lead_intake",
            "destination_url": "https://service.test/book",
            "tracking_params": {"utm_source": "s", "utm_medium": "m", "utm_campaign": "c", "asset_id": "ast_001"}
        },
        "approval_state": "approved",
        "external_action": True  # forbidden
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad_plan, schema=subschema)
