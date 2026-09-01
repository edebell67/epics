"""
EP050 Node 13: Demand Path Discovery

Responsible for taking validated DemandOpportunityRecord outputs from Node 12
and mapping out deterministic, actionable multi-touchpoint customer demand journeys.

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial deterministic implementation of Demand Path Discovery with full lineage preservation and offline enclosure.
"""

from __future__ import annotations

import os
import sys
import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

# Upstream paths for Node 11 and Node 12 imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_11_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_11"))
NODE_12_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_12"))

if NODE_11_DIR not in sys.path:
    sys.path.insert(0, NODE_11_DIR)
if NODE_12_DIR not in sys.path:
    sys.path.insert(0, NODE_12_DIR)

try:
    from opportunity_scoring import DemandOpportunityRecord
except ImportError:
    DemandOpportunityRecord = None  # type: ignore


class ValidationError(ValueError):
    """Raised when input validation fails on contract schema or bounds."""
    pass


class LineageError(ValueError):
    """Raised when required upstream lineage identifiers are missing or corrupt."""
    pass


@dataclass(frozen=True)
class DemandPathStage:
    """Represents an individual ordered touchpoint or stage along the customer demand path."""
    stage_index: int
    stage_name: str
    channel: str
    information_sought: str
    influenceable_touchpoint: str
    intent_level: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DemandPathRecord:
    """Immutable output container for an identified customer demand path."""
    path_id: str
    path_name: str
    target_id: str
    signal_id: str
    classification_id: str
    opportunity_id: str
    stages: List[DemandPathStage]
    commercial_intent_emergence_stage: int
    path_hypothesis: str
    evidence_sources: List[str]
    created_at: str
    # Carried through from Node 11/12 so downstream nodes describe THIS campaign rather than
    # falling back to literals. Node 14's default channel rationale reads geography from here;
    # without it the record dead-ended the context and Node 14 had nothing real to use.
    geography: Optional[Dict[str, Any]] = None
    service_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "path_name": self.path_name,
            "target_id": self.target_id,
            "signal_id": self.signal_id,
            "classification_id": self.classification_id,
            "opportunity_id": self.opportunity_id,
            "stages": [s.to_dict() for s in self.stages],
            "commercial_intent_emergence_stage": self.commercial_intent_emergence_stage,
            "path_hypothesis": self.path_hypothesis,
            "evidence_sources": list(self.evidence_sources),
            "created_at": self.created_at,
            "geography": dict(self.geography) if self.geography else None,
            "service_context": dict(self.service_context) if self.service_context else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _compute_deterministic_path_id(
    target_id: str,
    signal_id: str,
    classification_id: str,
    opportunity_id: str,
    path_name: str
) -> str:
    """Generates a reproducible, stable hash-based path ID."""
    token = f"{target_id}:{signal_id}:{classification_id}:{opportunity_id}:{path_name}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"path_{digest}"


def _service_phrase(service_context: Optional[Dict[str, Any]]) -> str:
    """'boiler_repair' -> 'boiler repair'. Presentation only; adds no words of its own."""
    name = str((service_context or {}).get("service_name") or "").replace("_", " ").strip()
    return " ".join(name.split())


def _place_phrase(geography: Optional[Dict[str, Any]]) -> str:
    """'Greenwich, London' from real geography; empty string when it is genuinely unknown."""
    geo = geography or {}
    parts = [str(geo.get(k) or "").strip() for k in ("locality", "region")]
    return ", ".join(dict.fromkeys(p for p in parts if p))


def _get_default_stages_for_intent(
    primary_intent: str,
    service_context: Optional[Dict[str, Any]] = None,
    geography: Optional[Dict[str, Any]] = None,
) -> List[DemandPathStage]:
    """Deterministic path stages for the primary intent, described in terms of THIS campaign.

    The stage sequence (how many stages, their channels and intent levels, where commercial intent
    emerges) is the real modelled logic and is intent-driven. What each stage's buyer is *seeking*
    is campaign-specific, so it is composed from the real service and geography carried down from
    Node 11/12 -- never asserted.

    Until 2026-08-19 these strings were literals describing one campaign: "Identify cause of boiler
    pressure loss...", "Evaluate DIY repressurising...", "Find local Gas Safe certified emergency
    boiler engineer in Blackheath", "24/7 emergency boiler engineer near me". Every campaign
    received them regardless of its town or vertical, so a Greenwich campaign's own demand path
    told it to find an engineer in Blackheath, and any non-boiler vertical got a boiler journey.
    Node 14 then selected channels from that text, so the error propagated into placement choice
    and from there into the rendered assets.
    """
    intent_lower = str(primary_intent).lower()
    service = _service_phrase(service_context)
    place = _place_phrase(geography)
    # Read as "... in Greenwich, London" only when the place is genuinely known.
    at_place = f" in {place}" if place else ""
    # Fall back to a neutral noun only if no service resolved -- never to a specific trade.
    subject = service or "the service"

    if "troubleshooting" in intent_lower:
        return [
            DemandPathStage(
                stage_index=1,
                stage_name="Problem Diagnosis",
                channel="organic_search",
                information_sought=f"Identify the underlying problem and check symptoms relating to {subject}",
                influenceable_touchpoint="Diagnostic guides, walkthroughs and symptom check tools",
                intent_level="informational"
            ),
            DemandPathStage(
                stage_index=2,
                stage_name="Solution Evaluation",
                channel="search_engine_results",
                information_sought=f"Evaluate self-service options against engaging a professional for {subject}",
                influenceable_touchpoint="Step-by-step guides with safety warnings and professional-callout triggers",
                intent_level="commercial_investigation"
            ),
            DemandPathStage(
                stage_index=3,
                stage_name="Service Selection",
                channel="local_search_maps",
                information_sought=f"Find a suitably qualified local provider of {subject}{at_place}",
                influenceable_touchpoint="Local business listings with availability and verified reviews",
                intent_level="emergency_service"
            ),
            DemandPathStage(
                stage_index=4,
                stage_name="Conversion Action",
                channel="landing_page_direct",
                information_sought=f"Arrange {subject} and confirm availability and price",
                influenceable_touchpoint="Direct contact CTA and booking form",
                intent_level="conversion"
            ),
        ]
    elif "emergency" in intent_lower:
        return [
            DemandPathStage(
                stage_index=1,
                stage_name="Immediate Distress",
                channel="mobile_search",
                information_sought=f"Find an available provider of {subject}{at_place} right now",
                influenceable_touchpoint="Click-to-call search ad with stated response time",
                intent_level="emergency_service"
            ),
            DemandPathStage(
                stage_index=2,
                stage_name="Direct Booking",
                channel="phone_call",
                information_sought="Confirm attendance time and booking",
                influenceable_touchpoint="Direct phone connection to the provider",
                intent_level="conversion"
            ),
        ]
    else:
        return [
            DemandPathStage(
                stage_index=1,
                stage_name="Information Discovery",
                channel="search_engine",
                information_sought=f"Understand what {subject} involves and what it typically costs",
                influenceable_touchpoint="Comparison overview and pricing guidance",
                intent_level="informational"
            ),
            DemandPathStage(
                stage_index=2,
                stage_name="Commercial Request",
                channel="website_form",
                information_sought=f"Request a formal quote for {subject}{at_place}",
                influenceable_touchpoint="Transparent quote request form",
                intent_level="commercial_request"
            ),
        ]


def discover_demand_path(
    opportunity_input: Union[DemandOpportunityRecord, Dict[str, Any]],
    custom_stages: Optional[List[Union[DemandPathStage, Dict[str, Any]]]] = None,
    path_name: Optional[str] = None,
    path_hypothesis: Optional[str] = None
) -> DemandPathRecord:
    """
    Discovers and constructs a validated DemandPathRecord from an upstream Opportunity Record.
    """
    # 1. Normalize input to dictionary
    if isinstance(opportunity_input, dict):
        raw = opportunity_input
    elif hasattr(opportunity_input, "to_dict"):
        raw = opportunity_input.to_dict()
    else:
        raise ValidationError("Input must be a DemandOpportunityRecord instance or valid dictionary.")

    # 2. Enforce upstream lineage presence (Fail-Closed)
    for req_field in ("target_id", "signal_id", "classification_id", "opportunity_id"):
        if not raw.get(req_field) or not str(raw[req_field]).strip():
            raise LineageError(f"Missing mandatory upstream lineage field '{req_field}'.")

    target_id = str(raw["target_id"]).strip()
    signal_id = str(raw["signal_id"]).strip()
    classification_id = str(raw["classification_id"]).strip()
    opportunity_id = str(raw["opportunity_id"]).strip()

    # 3. Determine Path Name
    if not path_name:
        path_name = f"path_{raw.get('target_id', 'target')}_{raw.get('primary_intent', 'journey')}"

    # 4. Resolve and Validate Stages
    resolved_stages: List[DemandPathStage] = []
    if custom_stages is not None:
        if not isinstance(custom_stages, list) or len(custom_stages) == 0:
            raise ValidationError("custom_stages must be a non-empty list of stages.")
        for idx, s in enumerate(custom_stages, start=1):
            if isinstance(s, DemandPathStage):
                stage_obj = s
            elif isinstance(s, dict):
                for sub_req in ("stage_index", "stage_name", "channel", "information_sought", "influenceable_touchpoint", "intent_level"):
                    if sub_req not in s:
                        raise ValidationError(f"Custom stage dictionary missing required field '{sub_req}'.")
                stage_obj = DemandPathStage(
                    stage_index=int(s["stage_index"]),
                    stage_name=str(s["stage_name"]),
                    channel=str(s["channel"]),
                    information_sought=str(s["information_sought"]),
                    influenceable_touchpoint=str(s["influenceable_touchpoint"]),
                    intent_level=str(s["intent_level"])
                )
            else:
                raise ValidationError(f"Invalid stage object type at index {idx}: {type(s)}.")
            resolved_stages.append(stage_obj)
    else:
        # Default stages based on primary_intent, described in terms of THIS campaign's real
        # service and geography (both carried down from Node 11 via the Node 12 opportunity).
        primary_intent = str(raw.get("primary_intent", "troubleshooting"))
        resolved_stages = _get_default_stages_for_intent(
            primary_intent,
            service_context=raw.get("service_context"),
            geography=raw.get("geography"),
        )

    # 5. Validate stage sequence integrity
    if not resolved_stages:
        raise ValidationError("Demand path must contain at least one stage.")

    for i, stg in enumerate(resolved_stages, start=1):
        if stg.stage_index != i:
            raise ValidationError(f"Invalid stage order: expected stage_index {i}, but got {stg.stage_index}.")
        if not stg.stage_name.strip() or not stg.channel.strip() or not stg.information_sought.strip():
            raise ValidationError(f"Stage {i} contains empty string attributes.")

    # 6. Commercial intent emergence stage
    # By default, emergence happens where intent becomes commercial/emergency/conversion
    emergence_stage = 2 if len(resolved_stages) >= 2 else 1
    for stg in resolved_stages:
        if stg.intent_level in ("commercial_investigation", "emergency_service", "commercial_request", "conversion"):
            emergence_stage = stg.stage_index
            break

    # 7. Path Hypothesis
    if not path_hypothesis:
        path_hypothesis = (
            f"Customer transitions through {len(resolved_stages)} touchpoints starting from {resolved_stages[0].channel} "
            f"with commercial intent emergence at stage {emergence_stage} ({resolved_stages[emergence_stage-1].stage_name})."
        )

    # 8. Compute Deterministic Path ID
    path_id = _compute_deterministic_path_id(target_id, signal_id, classification_id, opportunity_id, path_name)

    created_at = datetime.now(timezone.utc).isoformat()
    evidence_sources = [f"opportunity:{opportunity_id}", f"signal:{signal_id}", f"classification:{classification_id}"]

    return DemandPathRecord(
        path_id=path_id,
        path_name=path_name,
        target_id=target_id,
        signal_id=signal_id,
        classification_id=classification_id,
        opportunity_id=opportunity_id,
        stages=resolved_stages,
        commercial_intent_emergence_stage=emergence_stage,
        path_hypothesis=path_hypothesis,
        evidence_sources=evidence_sources,
        created_at=created_at,
        geography=raw.get("geography"),
        service_context=raw.get("service_context"),
    )
