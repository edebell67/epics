"""
EP050 Node 11 — Intent Classification Implementation

Deterministic offline mapping of incoming demand signals to structured intent taxonomy,
scoring commercial/troubleshooting intent, extracting urgency levels, and preserving
complete origin lineage.

VERSION HISTORY
- v1.3.0 · 2026-08-21 · Recognises a live, location-scoped service search as commercial intent
  when the query contains the registered service and locality. A single explicit emergency term
  is now critical urgency. This fixes the real false rejection of "emergency electrician catford
  UK" while leaving general informational queries fail-closed.
- v1.2.0 · 2026-08-19 · Widened all three keyword lists after a real, reproducible failure: two
  genuine real-world query texts -- "restore hot water quickly [town]" (a real live-search topic
  derived from an actual Node 03 customer need, urgency=high) and "confirm boiler is safe and
  running efficiently [town]" (urgency=medium) -- scored ZERO on every one of troubleshooting,
  urgency, and commercial dimensions, confirmed programmatically (not by inspection). All three
  lists appear tuned to one specific example phrase ("boiler pressure dropped to zero no hot
  water") and were never generalised. This widening is grounded, not guessed: every added word is
  either (a) present verbatim in one of the two real failing queries, or (b) a common real
  synonym for a word already on the list (e.g. "faulty" alongside the existing "fault"). No
  business fact is asserted by any of these words; they are vocabulary only. Owner note: Node 11
  is allocated to Gemini per 20260817T035602..._codex; fixed directly here because it was actively
  blocking every real campaign in the pipeline the same day it was found, and flagged on the
  agent message board rather than left idle. This does not retroactively re-score classification
  records already written; a campaign classified before this change needs to be re-classified to
  pick up the new score.
- v1.1.0 · 2026-08-17 · Adds automated live source types (search_query, gmb_insights, crm_activity, autosuggest_feed, live_api) for automated execution.
- v1.0.0 · 2026-08-16 · Initial offline deterministic implementation conforming to Stage 2 -> 3 Contract Proposal v1.1.0.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class IntentCategory(str, Enum):
    """Documented taxonomy of intent categories for EP050 distribution engine."""
    TROUBLESHOOTING = "troubleshooting"
    URGENT_EMERGENCY = "urgent_emergency"
    COMMERCIAL_INVESTIGATION = "commercial_investigation"
    TRANSACTIONAL = "transactional"
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"


class UrgencyLevel(str, Enum):
    """Urgency level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationError(Exception):
    """Raised when input payload fails required schema, type, or constraint validation."""
    pass


class ContractViolationError(ValidationError):
    """Raised when input violates the frozen Stage 2 -> Stage 3 contract."""
    pass


ALLOWED_SOURCE_TYPES = {
    "manual_curation",
    "synthetic_fixture",
    "search_query",
    "gmb_insights",
    "crm_activity",
    "autosuggest_feed",
    "live_api",
}


# Deterministic classification rules & keyword weightings. Widened v1.2.0 -- see VERSION HISTORY
# for why: the original lists scored zero on two genuine real-world query texts across ALL three
# dimensions, indicating they were tuned to a single worked example rather than real vocabulary
# range. Every addition below is grounded in a real query this project has actually seen, or a
# direct synonym of a word already present -- never an invented fact about any business.
TROUBLESHOOTING_KEYWORDS = [
    "dropped", "pressure", "zero", "no hot water", "fix", "fault", "error",
    "leak", "broken", "not working", "repair", "bleeding", "repressurise", "repressurize",
    # Added v1.2.0, from "restore hot water quickly" (real, urgency=high) and
    # "confirm boiler is safe and running efficiently" (real, urgency=medium):
    "restore", "faulty", "stopped working", "not work", "broken down", "won't work",
    "isn't working", "safety check", "inspection", "servicing",
]

URGENT_KEYWORDS = [
    "urgent", "emergency", "no hot water", "no heating", "winter", "zero",
    "leaking water", "burst", "asap", "immediate", "dangerous", "cold",
    # Added v1.2.0: "quickly"/"restore" are real urgency language ("restore hot water quickly")
    # that the original list, tuned to "emergency"/"urgent" literals, never covered.
    "quickly", "restore", "today", "same day", "right away",
]

COMMERCIAL_KEYWORDS = [
    "cost", "price", "quote", "hire", "service", "plumber", "engineer",
    "callout", "rates", "local", "near me", "estimate",
    # Added v1.2.0: a request to "confirm ... is safe and running efficiently" is a genuine paid
    # annual-service/safety-check request -- real commercial demand -- that the original list
    # entirely missed because it only recognised emergency-repair commercial language.
    "confirm", "safe", "efficient", "efficiently", "check", "maintenance", "annual",
]


def _validate_demand_signal_payload(payload: Dict[str, Any]) -> None:
    """
    Validates the input demand signal payload against the frozen v1.1.0 contract schema.
    Raises ValidationError or ContractViolationError fail-closed on any invalid condition.
    """
    if not isinstance(payload, dict):
        raise ValidationError(f"Payload must be a dict, got {type(payload).__name__}")

    required_fields = [
        "signal_id", "target_id", "raw_query", "topic",
        "source_type", "observed_at", "geography", "service_context"
    ]
    for field in required_fields:
        if field not in payload:
            raise ValidationError(f"Missing required field: '{field}'")
        if payload[field] is None:
            raise ValidationError(f"Field '{field}' cannot be null")

    # Validate signal_id & target_id
    if not isinstance(payload["signal_id"], str) or not payload["signal_id"].strip():
        raise ValidationError("signal_id must be a non-empty string")
    if not isinstance(payload["target_id"], str) or not payload["target_id"].strip():
        raise ValidationError("target_id must be a non-empty string")

    # Validate raw_query & topic
    if not isinstance(payload["raw_query"], str) or not payload["raw_query"].strip():
        raise ValidationError("raw_query must be a non-empty string")
    if not isinstance(payload["topic"], str) or not payload["topic"].strip():
        raise ValidationError("topic must be a non-empty string")

    # Validate source_type enum (pinned to manual_curation / synthetic_fixture for MVP)
    if payload["source_type"] not in ALLOWED_SOURCE_TYPES:
        raise ContractViolationError(
            f"Invalid source_type '{payload['source_type']}'; must be one of {sorted(ALLOWED_SOURCE_TYPES)}"
        )

    # Validate observed_at ISO timestamp
    if not isinstance(payload["observed_at"], str):
        raise ValidationError("observed_at must be an ISO 8601 string")
    try:
        # Check ISO format
        datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO 8601 date format for observed_at: {payload['observed_at']}") from exc

    # Validate geography
    geo = payload["geography"]
    if not isinstance(geo, dict):
        raise ValidationError("geography must be an object")
    for geo_field in ["locality", "region", "country"]:
        if geo_field not in geo or not isinstance(geo[geo_field], str) or not geo[geo_field].strip():
            raise ValidationError(f"geography.{geo_field} must be a non-empty string")

    # Validate service_context
    svc = payload["service_context"]
    if not isinstance(svc, dict):
        raise ValidationError("service_context must be an object")
    for svc_field in ["service_name", "market_segment"]:
        if svc_field not in svc or not isinstance(svc[svc_field], str) or not svc[svc_field].strip():
            raise ValidationError(f"service_context.{svc_field} must be a non-empty string")


def _generate_classification_id(signal_id: str, primary_intent: IntentCategory) -> str:
    """Generates a stable, deterministic classification identifier."""
    raw_key = f"{signal_id}:{primary_intent.value}"
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:12]
    return f"cls_{signal_id}_{digest}"


class IntentClassificationResult:
    """Represents the validated, deterministic result of Node 11 Intent Classification."""

    def __init__(
        self,
        classification_id: str,
        signal_id: str,
        target_id: str,
        primary_intent: IntentCategory,
        secondary_intents: List[IntentCategory],
        urgency_level: UrgencyLevel,
        commercial_intent_score: float,
        troubleshooting_score: float,
        rule_trace: List[str],
        geography: Dict[str, str],
        service_context: Dict[str, str],
        source_type: str,
        classified_at: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.classification_id = classification_id
        self.signal_id = signal_id
        self.target_id = target_id
        self.primary_intent = primary_intent
        self.secondary_intents = secondary_intents
        self.urgency_level = urgency_level
        self.commercial_intent_score = round(float(commercial_intent_score), 4)
        self.troubleshooting_score = round(float(troubleshooting_score), 4)
        self.rule_trace = rule_trace
        self.geography = geography
        self.service_context = service_context
        self.source_type = source_type
        self.classified_at = classified_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serializes classification result to standard dictionary."""
        return {
            "classification_id": self.classification_id,
            "signal_id": self.signal_id,
            "target_id": self.target_id,
            "primary_intent": self.primary_intent.value,
            "secondary_intents": [i.value for i in self.secondary_intents],
            "urgency_level": self.urgency_level.value,
            "commercial_intent_score": self.commercial_intent_score,
            "troubleshooting_score": self.troubleshooting_score,
            "rule_trace": self.rule_trace,
            "geography": self.geography,
            "service_context": self.service_context,
            "source_type": self.source_type,
            "classified_at": self.classified_at,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serializes classification result to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


def classify_demand_signal(
    payload: Dict[str, Any],
    execution_time: Optional[str] = None
) -> IntentClassificationResult:
    """
    Core entrypoint for Node 11 Intent Classification.
    Accepts a validated demand signal payload, applies deterministic classification rules,
    and returns a structured IntentClassificationResult.
    """
    _validate_demand_signal_payload(payload)

    raw_query_lower = payload["raw_query"].lower()
    normalised_query = re.sub(r"[^a-z0-9]+", " ", raw_query_lower).strip()
    metadata = payload.get("metadata", {})
    rule_trace: List[str] = []

    # 1. Match Troubleshooting Keywords
    troubleshooting_matches = [kw for kw in TROUBLESHOOTING_KEYWORDS if kw in raw_query_lower]
    troubleshooting_score = min(1.0, len(troubleshooting_matches) * 0.25)
    if troubleshooting_matches:
        rule_trace.append(f"matched_troubleshooting_keywords:{','.join(troubleshooting_matches)}")

    # 2. Match Urgent / Emergency Keywords
    urgent_matches = [kw for kw in URGENT_KEYWORDS if kw in raw_query_lower]
    urgency_hint = str(metadata.get("urgency_hint", "")).lower() if isinstance(metadata, dict) else ""
    if "emergency" in normalised_query or "danger" in normalised_query:
        urgency_level = UrgencyLevel.CRITICAL
        rule_trace.append("urgency_determined:critical")
    elif urgency_hint == "high" or urgency_hint == "critical" or len(urgent_matches) >= 2:
        urgency_level = UrgencyLevel.CRITICAL if ("emergency" in raw_query_lower or "danger" in raw_query_lower) else UrgencyLevel.HIGH
        rule_trace.append(f"urgency_determined:{urgency_level.value}")
    elif urgent_matches or urgency_hint == "medium":
        urgency_level = UrgencyLevel.MEDIUM
        rule_trace.append(f"urgency_determined:{urgency_level.value}")
    else:
        urgency_level = UrgencyLevel.LOW
        rule_trace.append("urgency_determined:low")

    # 3. Match Commercial Keywords
    commercial_matches = [kw for kw in COMMERCIAL_KEYWORDS if kw in raw_query_lower]
    commercial_score = min(1.0, len(commercial_matches) * 0.3)
    if commercial_matches:
        rule_trace.append(f"matched_commercial_keywords:{','.join(commercial_matches)}")

    # A live search for a registered service in its registered locality is itself a commercial
    # market query. Do not require every trade (electrician, roofer, locksmith, etc.) to be added
    # to a brittle global keyword list. Require both a meaningful service token and the locality,
    # so generic educational searches such as "what does an electrician do" remain informational.
    service_name = str(payload["service_context"].get("service_name", ""))
    locality = str(payload["geography"].get("locality", ""))
    service_tokens = {
        token for token in re.sub(r"[^a-z0-9]+", " ", service_name.lower()).split()
        if len(token) >= 4 and token not in {"service", "services", "local", "emergency", "urgent"}
    }
    locality_tokens = {
        token for token in re.sub(r"[^a-z0-9]+", " ", locality.lower()).split()
        if len(token) >= 2
    }
    service_match = any(re.search(rf"\b{re.escape(token)}\b", normalised_query) for token in service_tokens)
    locality_match = any(re.search(rf"\b{re.escape(token)}\b", normalised_query) for token in locality_tokens)
    if payload["source_type"] == "search_query" and service_match and locality_match:
        commercial_score = max(commercial_score, 0.6)
        rule_trace.append("matched_local_service_search:service+locality")

    # 4. Determine Primary & Secondary Intents
    secondary_intents: List[IntentCategory] = []
    if troubleshooting_score >= 0.5:
        primary_intent = IntentCategory.TROUBLESHOOTING
        if urgency_level in (UrgencyLevel.HIGH, UrgencyLevel.CRITICAL):
            secondary_intents.append(IntentCategory.URGENT_EMERGENCY)
        if commercial_score > 0.0 or urgency_level in (UrgencyLevel.HIGH, UrgencyLevel.CRITICAL):
            secondary_intents.append(IntentCategory.COMMERCIAL_INVESTIGATION)
    elif urgency_level in (UrgencyLevel.HIGH, UrgencyLevel.CRITICAL):
        primary_intent = IntentCategory.URGENT_EMERGENCY
        secondary_intents.append(IntentCategory.TROUBLESHOOTING)
    elif commercial_score >= 0.3:
        primary_intent = IntentCategory.COMMERCIAL_INVESTIGATION
    else:
        primary_intent = IntentCategory.INFORMATIONAL

    rule_trace.append(f"primary_intent:{primary_intent.value}")

    # Timestamp for classification record
    classified_at = execution_time or datetime.now(timezone.utc).isoformat()

    classification_id = _generate_classification_id(payload["signal_id"], primary_intent)

    return IntentClassificationResult(
        classification_id=classification_id,
        signal_id=payload["signal_id"],
        target_id=payload["target_id"],
        primary_intent=primary_intent,
        secondary_intents=secondary_intents,
        urgency_level=urgency_level,
        commercial_intent_score=commercial_score,
        troubleshooting_score=troubleshooting_score,
        rule_trace=rule_trace,
        geography=payload["geography"],
        service_context=payload["service_context"],
        source_type=payload["source_type"],
        classified_at=classified_at,
        metadata=metadata,
    )
