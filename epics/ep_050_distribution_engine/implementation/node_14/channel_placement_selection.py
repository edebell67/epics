"""
EP050 Node 14: Channel / Placement Selection

Scores and ranks candidate distribution channels and placements for each customer
demand path based on multi-factor fit (Audience Match, Intent Relevance, Format Viability, Cost Efficiency).

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial deterministic implementation of Channel/Placement Selection with explainable scoring, ranking, and full upstream lineage preservation.
"""

from __future__ import annotations

import os
import sys
import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_13_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_13"))

if NODE_13_DIR not in sys.path:
    sys.path.insert(0, NODE_13_DIR)

try:
    from demand_path_discovery import DemandPathRecord, DemandPathStage
except ImportError:
    DemandPathRecord = None  # type: ignore
    DemandPathStage = None  # type: ignore


class ValidationError(ValueError):
    """Raised when input validation fails on contract schema or bounds."""
    pass


class LineageError(ValueError):
    """Raised when required upstream lineage identifiers are missing or corrupt."""
    pass


DEFAULT_WEIGHTS: Dict[str, float] = {
    "audience_match": 30.0,
    "intent_relevance": 30.0,
    "format_viability": 20.0,
    "cost_efficiency": 20.0,
}


@dataclass(frozen=True)
class ChannelScoreBreakdown:
    """Captures explainable 4-factor scoring components normalized between 0.0 and 1.0."""
    audience_match: float
    intent_relevance: float
    format_viability: float
    cost_efficiency: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RankedPlacementOption:
    """Represents a scored candidate placement option."""
    rank: int
    channel_name: str
    placement_type: str
    channel_fit_score: float
    score_breakdown: ChannelScoreBreakdown
    recommended_format: str
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "channel_name": self.channel_name,
            "placement_type": self.placement_type,
            "channel_fit_score": round(self.channel_fit_score, 2),
            "score_breakdown": self.score_breakdown.to_dict(),
            "recommended_format": self.recommended_format,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ChannelSelectionRecord:
    """Immutable output container for selected and ranked channel placements."""
    selection_id: str
    strategy_name: str
    target_id: str
    signal_id: str
    classification_id: str
    opportunity_id: str
    path_id: str
    ranked_placements: List[RankedPlacementOption]
    primary_channel: str
    evidence_sources: List[str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "strategy_name": self.strategy_name,
            "target_id": self.target_id,
            "signal_id": self.signal_id,
            "classification_id": self.classification_id,
            "opportunity_id": self.opportunity_id,
            "path_id": self.path_id,
            "ranked_placements": [p.to_dict() for p in self.ranked_placements],
            "primary_channel": self.primary_channel,
            "evidence_sources": list(self.evidence_sources),
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _compute_deterministic_selection_id(
    target_id: str,
    signal_id: str,
    classification_id: str,
    opportunity_id: str,
    path_id: str,
    strategy_name: str
) -> str:
    """Generates a reproducible, stable hash-based selection ID."""
    token = f"{target_id}:{signal_id}:{classification_id}:{opportunity_id}:{path_id}:{strategy_name}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"sel_{digest}"


def _get_default_candidate_channels(geography: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Returns canonical candidate distribution channels for emergency/troubleshooting services.

    Channel names, placement types, scores and formats are genuine modelling constants -- they
    describe channels, not a campaign. Only the human-readable rationale referenced a specific
    place, and it named "Blackheath" for every campaign regardless of where it actually ran; that
    now reflects the campaign's real geography, or omits the place when it is unknown.
    """
    geo = geography or {}
    place = ", ".join(dict.fromkeys(
        p for p in (str(geo.get("locality") or "").strip(), str(geo.get("region") or "").strip()) if p
    ))
    local_rationale = (
        f"High geographic concentration in {place} with direct click-to-call intent."
        if place else
        "High geographic concentration in the target area with direct click-to-call intent."
    )
    return [
        {
            "channel_name": "local_search_maps",
            "placement_type": "google_maps_local_pack",
            "raw_scores": {"audience_match": 0.95, "intent_relevance": 0.95, "format_viability": 0.90, "cost_efficiency": 0.90},
            "recommended_format": "verified_local_listing_with_emergency_hours",
            "rationale": local_rationale
        },
        {
            "channel_name": "organic_search",
            "placement_type": "diagnostic_landing_page",
            "raw_scores": {"audience_match": 0.90, "intent_relevance": 0.90, "format_viability": 0.85, "cost_efficiency": 0.95},
            "recommended_format": "step_by_step_troubleshooting_guide",
            "rationale": "Captures top-of-funnel problem queries with zero marginal media cost."
        },
        {
            "channel_name": "paid_search",
            "placement_type": "google_search_exact_match",
            "raw_scores": {"audience_match": 0.95, "intent_relevance": 0.90, "format_viability": 0.85, "cost_efficiency": 0.70},
            "recommended_format": "callout_extension_ad_24_7_emergency",
            "rationale": "Guarantees top placement for emergency terms with fixed CPA cap."
        },
        {
            "channel_name": "social_community",
            "placement_type": "neighbourhood_discussion_board",
            "raw_scores": {"audience_match": 0.80, "intent_relevance": 0.60, "format_viability": 0.75, "cost_efficiency": 0.85},
            "recommended_format": "community_recommendation_post",
            "rationale": "Builds local trust and word-of-mouth referral authority."
        }
    ]


def select_channel_placements(
    path_input: Union[DemandPathRecord, Dict[str, Any]],
    candidate_channels: Optional[List[Dict[str, Any]]] = None,
    weights: Optional[Dict[str, float]] = None,
    strategy_name: Optional[str] = None
) -> ChannelSelectionRecord:
    """
    Evaluates, scores, and ranks candidate placement options for a given DemandPathRecord.
    """
    # 1. Normalize input to dictionary
    if isinstance(path_input, dict):
        raw = path_input
    elif hasattr(path_input, "to_dict"):
        raw = path_input.to_dict()
    else:
        raise ValidationError("Input must be a DemandPathRecord instance or valid dictionary.")

    # 2. Enforce upstream lineage presence (Fail-Closed)
    for req_field in ("target_id", "signal_id", "classification_id", "opportunity_id", "path_id"):
        if not raw.get(req_field) or not str(raw[req_field]).strip():
            raise LineageError(f"Missing mandatory upstream lineage field '{req_field}'.")

    target_id = str(raw["target_id"]).strip()
    signal_id = str(raw["signal_id"]).strip()
    classification_id = str(raw["classification_id"]).strip()
    opportunity_id = str(raw["opportunity_id"]).strip()
    path_id = str(raw["path_id"]).strip()

    # 3. Strategy name
    if not strategy_name:
        strategy_name = f"strategy_{target_id}_omnichannel"

    # 4. Resolve weights
    active_weights = weights if weights is not None else DEFAULT_WEIGHTS
    for k in ("audience_match", "intent_relevance", "format_viability", "cost_efficiency"):
        if k not in active_weights or active_weights[k] < 0:
            raise ValidationError(f"Invalid or negative weight for component '{k}'.")

    weight_sum = sum(active_weights.values())
    if not (99.9 <= weight_sum <= 100.1):
        raise ValidationError(f"Component weights must sum to 100.0 (got {weight_sum}).")

    # 5. Resolve candidate channels
    # The path record carries the campaign's real geography down from Node 11/12, so the default
    # channels' rationale can describe this campaign rather than a hardcoded town.
    candidates = (
        candidate_channels if candidate_channels is not None
        else _get_default_candidate_channels(geography=raw.get("geography"))
    )
    if not candidates:
        raise ValidationError("Candidate channels list cannot be empty.")

    # 6. Score and rank placements
    scored_list = []
    for cand in candidates:
        for req_key in ("channel_name", "placement_type", "raw_scores", "recommended_format", "rationale"):
            if req_key not in cand:
                raise ValidationError(f"Candidate channel missing required attribute '{req_key}'.")

        raw_sc = cand["raw_scores"]
        for sub_k in ("audience_match", "intent_relevance", "format_viability", "cost_efficiency"):
            val = float(raw_sc.get(sub_k, 0.0))
            if not (0.0 <= val <= 1.0):
                raise ValidationError(f"Raw score for '{sub_k}' must be in range [0.0, 1.0], got {val}.")

        sb = ChannelScoreBreakdown(
            audience_match=float(raw_sc["audience_match"]),
            intent_relevance=float(raw_sc["intent_relevance"]),
            format_viability=float(raw_sc["format_viability"]),
            cost_efficiency=float(raw_sc["cost_efficiency"])
        )

        # Weighted calculation
        total_fit = (
            (sb.audience_match * active_weights["audience_match"]) +
            (sb.intent_relevance * active_weights["intent_relevance"]) +
            (sb.format_viability * active_weights["format_viability"]) +
            (sb.cost_efficiency * active_weights["cost_efficiency"])
        )

        scored_list.append({
            "channel_name": str(cand["channel_name"]),
            "placement_type": str(cand["placement_type"]),
            "channel_fit_score": total_fit,
            "score_breakdown": sb,
            "recommended_format": str(cand["recommended_format"]),
            "rationale": str(cand["rationale"])
        })

    # Sort descending by score
    scored_list.sort(key=lambda x: x["channel_fit_score"], reverse=True)

    ranked_options = [
        RankedPlacementOption(
            rank=idx,
            channel_name=item["channel_name"],
            placement_type=item["placement_type"],
            channel_fit_score=item["channel_fit_score"],
            score_breakdown=item["score_breakdown"],
            recommended_format=item["recommended_format"],
            rationale=item["rationale"]
        )
        for idx, item in enumerate(scored_list, start=1)
    ]

    primary_channel = ranked_options[0].channel_name if ranked_options else "none"
    selection_id = _compute_deterministic_selection_id(target_id, signal_id, classification_id, opportunity_id, path_id, strategy_name)
    created_at = datetime.now(timezone.utc).isoformat()
    evidence_sources = [f"path:{path_id}", f"opportunity:{opportunity_id}", f"signal:{signal_id}"]

    return ChannelSelectionRecord(
        selection_id=selection_id,
        strategy_name=strategy_name,
        target_id=target_id,
        signal_id=signal_id,
        classification_id=classification_id,
        opportunity_id=opportunity_id,
        path_id=path_id,
        ranked_placements=ranked_options,
        primary_channel=primary_channel,
        evidence_sources=evidence_sources,
        created_at=created_at
    )
