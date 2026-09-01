# epics/ep_050_distribution_engine/implementation/node_37/distribution_knowledge_base.py
# EP050 Node 37 — Distribution Knowledge Base Store.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial persistent, queryable distribution knowledge base capturing validated historical learnings and regression-resistant patterns.

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

KB_VERSION = "distribution_knowledge_base_v1.0.0"


class KnowledgeBaseValidationError(ValueError):
    """Raised when an allocation record or learning entry fails validation."""


def derive_knowledge_entry_id(allocation_id: str, topic: str) -> str:
    key = f"{allocation_id}:{topic}"
    return "dkb_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def record_distribution_knowledge(
    allocation_record: Mapping[str, Any],
    *,
    learning_summary: str,
    key_success_factors: list[str],
    recommended_rules: list[str],
) -> dict[str, Any]:
    """Persist an actionable intelligence record to the long-term knowledge base.

    Every argument is REQUIRED and has no default. Until 2026-08-19 this function defaulted
    learning_summary to a specific fabricated performance claim -- "yield 12.5x ROAS in South
    London" -- that no campaign had ever earned, plus boiler/plumbing-specific default success
    factors and rules ("certified engineer badge", "plumbing emergency niches"). A knowledge base
    exists to record what genuinely happened; a plausible-sounding invented default is the single
    worst place in this codebase for one to live, since every unattributed caller would silently
    write a fabricated business result into permanent "knowledge". Callers must supply real,
    observed values -- there is no safe default to fall back to.
    """
    if not isinstance(allocation_record, Mapping):
        raise KnowledgeBaseValidationError("allocation_record must be an object")

    alloc_id = str(allocation_record.get("allocation_id") or "")
    if not alloc_id.startswith("eal_"):
        raise KnowledgeBaseValidationError("Valid Node 36 allocation record with eal_ prefix is required")

    if not isinstance(learning_summary, str) or not learning_summary.strip():
        raise KnowledgeBaseValidationError("learning_summary is required and must be a non-empty string")
    if not isinstance(key_success_factors, list) or not key_success_factors:
        raise KnowledgeBaseValidationError("key_success_factors is required and must be a non-empty list")
    if not isinstance(recommended_rules, list) or not recommended_rules:
        raise KnowledgeBaseValidationError("recommended_rules is required and must be a non-empty list")

    factors = key_success_factors
    rules = recommended_rules

    return {
        "schema_version": "1.0.0",
        "knowledge_entry_id": derive_knowledge_entry_id(alloc_id, "distribution_learning"),
        "allocation_id": alloc_id,
        "opportunity_id": allocation_record.get("opportunity_id"),
        "learning_summary": learning_summary.strip(),
        "key_success_factors": factors,
        "recommended_rules": rules,
        "provenance": {
            "source_node": "Node 37",
            "lifecycle_complete": True,
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        },
    }
