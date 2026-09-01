# epics/ep_050_distribution_engine/implementation/node_35/winner_amplification.py
# EP050 Node 35 — Winner Amplification & Scale Generator.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial winner amplification generator producing systematic expansion variants across adjacent geos, topics, and channels.

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

AMPLIFICATION_VERSION = "winner_amplification_v1.0.0"


class WinnerAmplificationValidationError(ValueError):
    """Raised when an unapproved or invalid winner candidate is submitted for amplification."""


def derive_amplification_id(winner_id: str) -> str:
    key = f"{winner_id}:amp"
    return "amp_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def generate_amplification_plan(
    winner_record: Mapping[str, Any],
    *,
    adjacent_geos: list[str] | None = None,
    additional_formats: list[str] | None = None,
) -> dict[str, Any]:
    """Create actionable scaling variants for an established winning strategy."""
    if not isinstance(winner_record, Mapping):
        raise WinnerAmplificationValidationError("winner_record must be an object")

    winner_id = str(winner_record.get("winner_id") or "")
    if not winner_id.startswith("wnr_"):
        raise WinnerAmplificationValidationError("Valid Node 34 winner record with wnr_ prefix is required")

    if winner_record.get("is_winner") is not True:
        raise WinnerAmplificationValidationError("Cannot amplify a non-winning strategy")

    # formats describes generic ASSET-FORMAT categories, not any business or place, so a fixed
    # menu is legitimate (same class as Node 14's channel candidates). adjacent_geos has no such
    # default: "Greenwich"/"Lewisham"/"Bromley"/"Dulwich" were an invented town list that would
    # have been suggested for amplifying ANY winner regardless of what market it actually won in
    # -- the real curated adjacency for this business already exists in
    # shared/candidate_expansion.py's GEO_ADJACENCY (used by Node 01's own candidate clustering)
    # and must not be duplicated or second-guessed here. If the caller has no real adjacent
    # geography to offer, the geographic_expansion variant is omitted rather than invented.
    formats = additional_formats or ["short_video", "faq_schema", "local_directory_push"]

    expansion_variants = [
        {"dimension": "format_diversification", "formats": formats, "action": "generate_native_asset_variants"},
    ]
    if adjacent_geos:
        expansion_variants.insert(0, {
            "dimension": "geographic_expansion", "target_markets": adjacent_geos,
            "action": "deploy_localized_landing_pages",
        })

    return {
        "schema_version": "1.0.0",
        "amplification_id": derive_amplification_id(winner_id),
        "winner_id": winner_id,
        "opportunity_id": winner_record.get("opportunity_id"),
        "channel": winner_record.get("channel"),
        "expansion_variants": expansion_variants,
        "guardrails": {
            "max_daily_budget_multiplier": 2.5,
            "geo_radius_limit_miles": 15,
            "compliance_pre_approval_required": True,
        },
        "status": "ready_for_effort_allocation",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
