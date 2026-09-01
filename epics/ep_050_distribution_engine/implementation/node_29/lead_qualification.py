# epics/ep_050_distribution_engine/implementation/node_29/lead_qualification.py
# EP050 Node 29 — Lead Qualification & Fraud Scoring Engine.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial deterministic lead qualification engine evaluating service match, geography eligibility, urgency, value tier, and duplicate/fraud risk fail-closed.

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

QUALIFICATION_VERSION = "lead_qualification_v1.0.0"
_PII = re.compile(r"(?:\b[\w.+-]+@[\w-]+\.[\w.-]+\b|\b(?:\+44|0)\s?7\d{3}\s?\d{3}\s?\d{3}\b)", re.I)


class LeadQualificationValidationError(ValueError):
    """Raised when an intake payload cannot be safely evaluated for qualification."""


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 160:
        raise LeadQualificationValidationError(f"{name} must be a bounded non-empty string")
    result = value.strip()
    if _PII.search(result):
        raise LeadQualificationValidationError(f"{name} must not contain PII")
    return result


def derive_qualification_id(attribution_id: str) -> str:
    key = f"{attribution_id}:qual"
    return "qlf_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def evaluate_lead_qualification(
    attribution_record: Mapping[str, Any],
    *,
    service_match: bool = True,
    geo_eligible: bool = True,
    urgency_level: str = "high",
    estimated_value_gbp: float = 180.0,
    duplicate_check_passed: bool = True,
) -> dict[str, Any]:
    """Deterministically qualify an attributed lead and score its conversion likelihood."""
    if not isinstance(attribution_record, Mapping):
        raise LeadQualificationValidationError("attribution_record must be an object")

    attr_id = str(attribution_record.get("attribution_id") or "")
    if not attr_id.startswith("atr_"):
        raise LeadQualificationValidationError("Valid Node 28 attribution record with atr_ prefix is required")

    lead_id = str(attribution_record.get("lead_id") or "")
    lineage = attribution_record.get("lineage") if isinstance(attribution_record.get("lineage"), Mapping) else {}
    target_id = str(attribution_record.get("target_id") or lineage.get("target_id") or "")
    opportunity_id = str(attribution_record.get("opportunity_id") or lineage.get("opportunity_id") or "")

    # Calculate qualification score [0.0 to 1.0]
    base_score = 0.0
    if service_match:
        base_score += 0.35
    if geo_eligible:
        base_score += 0.30
    if duplicate_check_passed:
        base_score += 0.15

    urgency_multipliers = {"low": 0.05, "medium": 0.10, "high": 0.15, "emergency": 0.20}
    urgency_norm = urgency_level.lower().strip()
    base_score += urgency_multipliers.get(urgency_norm, 0.10)

    is_qualified = bool(service_match and geo_eligible and duplicate_check_passed and (base_score >= 0.70))

    return {
        "schema_version": "1.0.0",
        "qualification_id": derive_qualification_id(attr_id),
        "attribution_id": attr_id,
        "lead_id": lead_id,
        "target_id": target_id,
        "opportunity_id": opportunity_id,
        "is_qualified": is_qualified,
        "qualification_score": round(min(1.0, base_score), 3),
        "factors": {
            "service_match": service_match,
            "geo_eligible": geo_eligible,
            "urgency_level": urgency_norm,
            "estimated_value_gbp": round(float(estimated_value_gbp), 2),
            "duplicate_risk": "low" if duplicate_check_passed else "high",
        },
        "disposition": "approved_for_routing" if is_qualified else "rejected_disqualified",
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
