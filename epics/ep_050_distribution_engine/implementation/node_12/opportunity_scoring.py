"""
EP050 Node 12: Opportunity Scoring (DOS - Demand Opportunity Score)

Consumes Node 11 Intent Classification outputs and computes deterministic
Demand Opportunity Score (DOS v1.0), priority tiering, component breakdown,
and preserved target/signal lineage.

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial deterministic implementation of Node 12 Opportunity Scoring.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

# Add node_11 directory to path for direct import
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_11_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_11"))
if NODE_11_DIR not in sys.path:
    sys.path.insert(0, NODE_11_DIR)

try:
    from intent_classification import IntentClassificationResult
except ImportError:
    IntentClassificationResult = None  # type: ignore


class ValidationError(Exception):
    """Raised when scoring input validation fails."""
    pass


class LineageError(Exception):
    """Raised when upstream target/signal lineage is missing or malformed."""
    pass


# Default Canonical Scoring Weights (Must sum to 100.0)
DEFAULT_WEIGHTS = {
    "urgency": 35.0,
    "intent_viability": 30.0,
    "service_alignment": 20.0,
    "geographic_alignment": 15.0
}

# Priority Tier Thresholds
TIER_1_THRESHOLD = 80.0
TIER_2_THRESHOLD = 65.0
TIER_3_THRESHOLD = 45.0


@dataclass(frozen=True)
class ComponentScoreBreakdown:
    """Explainable breakdown of the individual components in DOS."""
    urgency_component: float
    intent_viability_component: float
    service_alignment_component: float
    geographic_alignment_component: float
    raw_urgency_factor: float
    raw_intent_factor: float
    raw_service_factor: float
    raw_geographic_factor: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class DemandOpportunityRecord:
    """Immutable output record produced by Node 12 Opportunity Scoring."""
    opportunity_id: str
    target_id: str
    signal_id: str
    classification_id: str
    demand_opportunity_score: float
    priority_tier: str
    formula_version: str
    component_breakdown: ComponentScoreBreakdown
    scored_at: str
    geography: Dict[str, str]
    service_context: Dict[str, str]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["component_breakdown"] = self.component_breakdown.to_dict()
        return data


def _compute_deterministic_opportunity_id(
    target_id: str, signal_id: str, classification_id: str, formula_version: str
) -> str:
    """Computes deterministic opportunity ID based on upstream lineage and formula version."""
    key = f"{target_id}:{signal_id}:{classification_id}:{formula_version}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"opp_{digest}"


def score_demand_opportunity(
    classification_input: Union[IntentClassificationResult, Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None
) -> DemandOpportunityRecord:
    """
    Computes deterministic Demand Opportunity Score (DOS v1.0) and priority tiering.

    Formula:
      DOS = (UrgencyFactor * W_urgency) +
            (IntentFactor * W_intent) +
            (ServiceFactor * W_service) +
            (GeographicFactor * W_geo)

    Priority Tiers:
      - TIER_1_IMMEDIATE: DOS >= 80.0
      - TIER_2_HIGH:      65.0 <= DOS < 80.0
      - TIER_3_MODERATE:  45.0 <= DOS < 65.0
      - TIER_4_LOW:       DOS < 45.0
    """
    # 1. Normalize and validate input
    if IntentClassificationResult is not None and isinstance(classification_input, IntentClassificationResult):
        data = classification_input.to_dict()
    elif isinstance(classification_input, dict):
        data = classification_input
    else:
        raise ValidationError(f"Invalid classification input type: {type(classification_input).__name__}")

    # 2. Extract and validate required lineage fields
    target_id = str(data.get("target_id", "")).strip()
    signal_id = str(data.get("signal_id", "")).strip()
    classification_id = str(data.get("classification_id", "")).strip()
    primary_intent = str(data.get("primary_intent", "")).strip()
    urgency_level = str(data.get("urgency_level", "")).strip().lower()

    if not target_id:
        raise LineageError("Missing required upstream 'target_id' in classification input.")
    if not signal_id:
        raise LineageError("Missing required upstream 'signal_id' in classification input.")
    if not classification_id:
        raise LineageError("Missing required upstream 'classification_id' in classification input.")
    if not primary_intent:
        raise ValidationError("Missing required 'primary_intent' in classification input.")
    if not urgency_level:
        raise ValidationError("Missing required 'urgency_level' in classification input.")

    geography = data.get("geography", {})
    if not isinstance(geography, dict):
        raise ValidationError("Field 'geography' must be a dictionary.")

    service_context = data.get("service_context", {})
    if not isinstance(service_context, dict):
        raise ValidationError("Field 'service_context' must be a dictionary.")

    # 3. Validate scoring weights
    active_weights = dict(DEFAULT_WEIGHTS)
    if weights is not None:
        for k, v in weights.items():
            if k not in active_weights:
                raise ValidationError(f"Unknown weight parameter: {k}")
            if not isinstance(v, (int, float)) or v < 0:
                raise ValidationError(f"Weight '{k}' must be a non-negative number.")
            active_weights[k] = float(v)

    total_weight = sum(active_weights.values())
    if abs(total_weight - 100.0) > 0.001:
        raise ValidationError(f"Sum of scoring weights must equal 100.0 (got {total_weight}).")

    # 4. Compute Raw Normalized Factors (0.0 to 1.0)
    # Urgency Factor
    if urgency_level in ("critical", "high"):
        raw_urgency_factor = 1.0
    elif urgency_level == "medium":
        raw_urgency_factor = 0.65
    elif urgency_level == "low":
        raw_urgency_factor = 0.30
    else:
        raise ValidationError(f"Invalid urgency_level '{urgency_level}'. Must be 'critical', 'high', 'medium', or 'low'.")

    # Intent Viability Factor
    # Commercial/troubleshooting high conversion intents receive top weight
    if primary_intent in ("troubleshooting", "quote_request", "emergency_service", "urgent_emergency", "commercial_investigation"):
        raw_intent_factor = 1.0
    elif primary_intent in ("comparison", "service_inquiry"):
        raw_intent_factor = 0.75
    elif primary_intent in ("informational", "general_curiosity"):
        raw_intent_factor = 0.40
    elif primary_intent in ("navigational", "out_of_scope"):
        raw_intent_factor = 0.10
    else:
        raw_intent_factor = 0.50

    # Service Alignment Factor
    service_name = str(service_context.get("service_name", "")).strip()
    market_segment = str(service_context.get("market_segment", "")).strip()
    if service_name and market_segment:
        raw_service_factor = 1.0
    elif service_name or market_segment:
        raw_service_factor = 0.60
    else:
        raw_service_factor = 0.20

    # Geographic Alignment Factor
    locality = str(geography.get("locality", "")).strip()
    region = str(geography.get("region", "")).strip()
    country = str(geography.get("country", "")).strip()
    if locality and (region or country):
        raw_geographic_factor = 1.0
    elif locality or region:
        raw_geographic_factor = 0.70
    elif country:
        raw_geographic_factor = 0.40
    else:
        raw_geographic_factor = 0.10

    # 5. Compute Weighted Components
    urgency_component = round(raw_urgency_factor * active_weights["urgency"], 2)
    intent_component = round(raw_intent_factor * active_weights["intent_viability"], 2)
    service_component = round(raw_service_factor * active_weights["service_alignment"], 2)
    geo_component = round(raw_geographic_factor * active_weights["geographic_alignment"], 2)

    total_dos = round(urgency_component + intent_component + service_component + geo_component, 2)
    total_dos = max(0.0, min(100.0, total_dos))

    # 6. Assign Priority Tier
    if total_dos >= TIER_1_THRESHOLD:
        priority_tier = "TIER_1_IMMEDIATE"
    elif total_dos >= TIER_2_THRESHOLD:
        priority_tier = "TIER_2_HIGH"
    elif total_dos >= TIER_3_THRESHOLD:
        priority_tier = "TIER_3_MODERATE"
    else:
        priority_tier = "TIER_4_LOW"

    breakdown = ComponentScoreBreakdown(
        urgency_component=urgency_component,
        intent_viability_component=intent_component,
        service_alignment_component=service_component,
        geographic_alignment_component=geo_component,
        raw_urgency_factor=raw_urgency_factor,
        raw_intent_factor=raw_intent_factor,
        raw_service_factor=raw_service_factor,
        raw_geographic_factor=raw_geographic_factor
    )

    formula_version = "DOS_v1.0"
    opportunity_id = _compute_deterministic_opportunity_id(
        target_id=target_id,
        signal_id=signal_id,
        classification_id=classification_id,
        formula_version=formula_version
    )

    scored_at = datetime.now(timezone.utc).isoformat()

    provenance = {
        "producer_node": "Node 12 (Opportunity Scoring)",
        "upstream_nodes": ["Node 01", "Node 05", "Node 11"],
        "scoring_weights": active_weights,
        "classification_id": classification_id
    }

    return DemandOpportunityRecord(
        opportunity_id=opportunity_id,
        target_id=target_id,
        signal_id=signal_id,
        classification_id=classification_id,
        demand_opportunity_score=total_dos,
        priority_tier=priority_tier,
        formula_version=formula_version,
        component_breakdown=breakdown,
        scored_at=scored_at,
        geography=geography,
        service_context=service_context,
        provenance=provenance
    )
