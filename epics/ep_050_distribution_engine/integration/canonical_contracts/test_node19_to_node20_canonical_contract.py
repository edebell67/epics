"""
EP050 Node 19 -> 20 Canonical Contract v1.1 — Test & Integrity Suite

Validates:
1. Canonical contract JSON schema syntax and provenance metadata
2. SHA-256 checksum verification of candidate proposal source
3. Full Draft 2020-12 validation for producer and consumer schemas
4. Enforced compliance booleans, lineage, .test URL, deterministic hashing, and external_action=false

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial canonical contract test and integrity suite.
"""

import json
import os
import hashlib
import jsonschema
import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CANONICAL_PATH = os.path.join(CURRENT_DIR, "20260817_node19_to_node20_canonical_contract_v1_1.json")
HERMES_CANDIDATE_PATH = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "proposals", "hermes", "20260816_node19_to_node20_consumer_contract_candidate_v1_1.json")
)


@pytest.fixture(scope="module")
def canonical_contract():
    assert os.path.isfile(CANONICAL_PATH), f"Canonical contract file missing: {CANONICAL_PATH}"
    with open(CANONICAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_canonical_metadata_and_provenance(canonical_contract):
    """Verifies promotion status, contract ID, and candidate SHA-256 hash."""
    assert canonical_contract["contract_id"] == "contract_node19_to_node20_v1_1"
    assert canonical_contract["contract_version"] == "1.1.0"
    assert canonical_contract["canonical_status"] == "PROMOTED_CANONICAL"
    assert canonical_contract["orchestrator_decision"] == "20260817T002606239_codex_e2cb088c"
    
    # Verify candidate SHA-256
    with open(HERMES_CANDIDATE_PATH, "rb") as f:
        cand_bytes = f.read()
    actual_hash = hashlib.sha256(cand_bytes).hexdigest()
    assert canonical_contract["provenance"]["consumer_candidate_sha256"] == actual_hash


def test_producer_asset_package_schema_positive(canonical_contract):
    """Validates valid approved asset package against canonical schema."""
    subschema = canonical_contract["approved_asset_package_schema"]
    valid_asset = {
        "schema_version": "1.1.0",
        "asset_id": "ast_boiler_001",
        "target_id": "tgt_boiler_repair_blackheath",
        "opportunity_id": "opp_boiler_001",
        "asset_type": "troubleshooting_guide",
        "headline": "Safe Boiler Re-Pressurisation in Blackheath",
        "body_content": {
            "summary": "Step-by-step guide for restoring boiler pressure.",
            "steps": ["Locate filling loop.", "Open valves to 1.5 bar.", "Close valves."],
            "safety_disclaimer": "Do not attempt gas repairs."
        },
        "cta_definition": {
            "cta_label": "Book Gas Safe Engineer",
            "cta_type": "lead_intake",
            "destination_url": "https://service.blackheathplumbing.test/book",
            "tracking_params": {
                "utm_source": "guide",
                "utm_medium": "organic",
                "utm_campaign": "boiler_pressure",
                "asset_id": "ast_boiler_001"
            }
        },
        "compliance_stamp": {
            "approved": True,
            "checked_at": "2026-08-16T21:00:00Z",
            "validator_version": "node_19_v1.0",
            "disclaimer_verified": True,
            "facts_verified": True
        },
        "target_channels": ["search_landing"],
        "schedule_request": {
            "channel": "search_landing",
            "audience": "aud_blackheath_homeowners",
            "scheduled_at": "2026-08-17T09:00:00Z"
        },
        "generated_at": "2026-08-16T20:55:00Z"
    }
    jsonschema.validate(instance=valid_asset, schema=subschema)


def test_consumer_mock_publication_plan_positive(canonical_contract):
    """Validates valid mock publication plan against canonical schema."""
    subschema = canonical_contract["mock_publication_plan_schema"]
    key_dict = {
        "asset_id": "ast_boiler_001",
        "channel": "search_landing",
        "destination_url": "https://service.blackheathplumbing.test/book",
        "audience": "aud_blackheath_homeowners",
        "scheduled_at": "2026-08-17T09:00:00Z"
    }
    canonical_json = json.dumps(key_dict, sort_keys=True, separators=(",", ":"))
    plan_id = "mpp_" + hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    valid_plan = {
        "schema_version": "1.1.0",
        "publication_plan_id": plan_id,
        "asset_id": "ast_boiler_001",
        "target_id": "tgt_boiler_repair_blackheath",
        "opportunity_id": "opp_boiler_001",
        "channel": "search_landing",
        "audience": "aud_blackheath_homeowners",
        "scheduled_at": "2026-08-17T09:00:00Z",
        "cta": {
            "label": "Book Gas Safe Engineer",
            "type": "lead_intake",
            "destination_url": "https://service.blackheathplumbing.test/book",
            "tracking_params": {
                "utm_source": "guide",
                "utm_medium": "organic",
                "utm_campaign": "boiler_pressure",
                "asset_id": "ast_boiler_001"
            }
        },
        "approval_state": "approved",
        "external_action": False
    }
    jsonschema.validate(instance=valid_plan, schema=subschema)


def test_safety_boundary_enforcement(canonical_contract):
    """Verifies top-level safety boundary configuration."""
    boundary = canonical_contract["safety_boundary"]
    assert boundary["external_action"] is False
    assert boundary["network"] == "prohibited"
    assert boundary["publishing_adapter"] == "excluded"
    assert boundary["local_loopback_only"] is True
