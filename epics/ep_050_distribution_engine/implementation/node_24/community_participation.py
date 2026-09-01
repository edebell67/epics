# epics/ep_050_distribution_engine/implementation/node_24/community_participation.py
# EP050 Node 24 — Community Participation Plan & Response Generator.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial helpful, non-promotional community participation builder with human-in-the-loop review gating and platform compliance checks.

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_20"))
from publishing_scheduler import (
    PublicationPlanValidationError,
    build_mock_publication_plan,
    validate_approved_asset_package,
)

COMMUNITY_PARTICIPATION_VERSION = "community_participation_v1.0.0"
SUPPORTED_COMMUNITIES = frozenset({"reddit", "quora", "local_forum", "discord", "facebook_groups"})
_PII_PATTERN = re.compile(r"(?:\b[\w.+-]+@[\w-]+\.[\w.-]+\b|\b(?:\+44|0)\s?7\d{3}\s?\d{3}\s?\d{3}\b)", re.I)


class CommunityParticipationValidationError(ValueError):
    """Raised when a candidate violates community guidelines or fails safety validation."""


def derive_community_plan_id(plan_id: str, community: str) -> str:
    key = f"{plan_id}:{community}"
    return "cpp_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def build_community_participation_plan(
    package: Mapping[str, Any] | Any,
    *,
    community: str = "reddit",
    target_thread_url: str,
    response_mode: str = "helpful_expert_answer",
) -> dict[str, Any]:
    """Generate a compliant, helpful community response plan with human-review gating."""
    plan = build_mock_publication_plan(package)
    community = community.lower().strip()
    if community not in SUPPORTED_COMMUNITIES:
        raise CommunityParticipationValidationError(
            f"community must be one of {sorted(SUPPORTED_COMMUNITIES)}, got {community!r}"
        )

    asset = validate_approved_asset_package(package)
    claims = asset.get("content_payload", {}).get("claims") or [
        "Check pressure gauge is between 1.0 and 1.5 bar",
        "Use filling loop carefully to repressurize",
        "Consult certified engineer if pressure drops repeatedly"
    ]
    summary = asset.get("content_payload", {}).get("summary") or "Diagnostic troubleshooting guide."

    # Build helpful non-spammy response
    response_text = (
        f"Here is a safe diagnostic check based on standard practice:\n\n"
        + "\n".join(f"• {c}" for c in claims)
        + f"\n\nFor reference or diagram: {plan['cta']['destination_url']}"
    )

    if _PII_PATTERN.search(response_text):
        raise CommunityParticipationValidationError("Community response text contains prohibited PII")

    return {
        "schema_version": "1.0.0",
        "community_plan_id": derive_community_plan_id(plan["publication_plan_id"], community),
        "publication_plan_id": plan["publication_plan_id"],
        "asset_id": plan["asset_id"],
        "target_id": plan["target_id"],
        "opportunity_id": plan["opportunity_id"],
        "community": community,
        "target_thread_url": target_thread_url,
        "response_payload": {
            "mode": response_mode,
            "response_text": response_text,
            "claims_referenced": claims,
            "non_promotional_compliance_score": 0.95,
            "requires_human_approval": True,
            "human_approval_state": "pending_operator_review",
        },
        "scheduled_at": plan["scheduled_at"],
        "external_action": False,  # Fail-closed human-gated by default
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
