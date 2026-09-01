# epics/ep_050_distribution_engine/implementation/node_34/winner_detection.py
# EP050 Node 34 — Winner Detection & ROI Intelligence Engine.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial quantitative winner detection classifying high-performing strategy/channel/topic combinations.

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

WINNER_DETECTION_VERSION = "winner_detection_v1.0.0"


class WinnerDetectionValidationError(ValueError):
    """Raised when performance data is insufficient or invalid for winner detection."""


def derive_winner_id(performance_record_id: str) -> str:
    key = f"{performance_record_id}:win"
    return "wnr_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def detect_winning_strategy(
    performance_record: Mapping[str, Any],
    *,
    min_roas_threshold: float = 4.0,
    min_conv_rate_threshold: float = 0.03,
) -> dict[str, Any]:
    """Analyze performance record against statistical ROI and conversion thresholds."""
    if not isinstance(performance_record, Mapping):
        raise WinnerDetectionValidationError("performance_record must be an object")

    pwr_id = str(performance_record.get("performance_record_id") or "")
    if not pwr_id.startswith("pwr_"):
        raise WinnerDetectionValidationError("Valid Node 32 performance record with pwr_ prefix is required")

    metrics = performance_record.get("metrics", {})
    roas = float(metrics.get("return_on_ad_spend", 0.0))
    conv_rate = float(metrics.get("conversion_rate", 0.0))
    leads = int(metrics.get("leads_captured", 0))

    is_winner = bool(roas >= min_roas_threshold and conv_rate >= min_conv_rate_threshold and leads >= 3)
    confidence = round(min(0.99, (roas / 10.0) * 0.5 + (conv_rate / 0.10) * 0.5), 3) if is_winner else 0.0

    return {
        "schema_version": "1.0.0",
        "winner_id": derive_winner_id(pwr_id),
        "performance_record_id": pwr_id,
        "opportunity_id": performance_record.get("opportunity_id"),
        "channel": performance_record.get("channel"),
        "is_winner": is_winner,
        "performance_assessment": {
            "roas": roas,
            "conversion_rate": conv_rate,
            "confidence_score": confidence,
            "winner_tier": "gold" if roas >= 10.0 else "silver" if is_winner else "underperforming",
        },
        "recommendation": "amplify_and_scale" if is_winner else "maintain_or_refine",
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
