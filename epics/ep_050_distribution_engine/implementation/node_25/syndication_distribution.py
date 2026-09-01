# epics/ep_050_distribution_engine/implementation/node_25/syndication_distribution.py
# EP050 Node 25 — Syndication & Partner Placement Package Builder.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial syndication & partner distribution package builder for industry directories, media releases, partner widgets, and newsletters.

from __future__ import annotations

import hashlib
import json
import os
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

SYNDICATION_DISTRIBUTION_VERSION = "syndication_distribution_v1.0.0"
SUPPORTED_SYNDICATION_TYPES = frozenset({"directory_listing", "industry_newsletter", "press_release", "partner_widget", "rss_syndication"})


class SyndicationDistributionValidationError(ValueError):
    """Raised when a candidate cannot produce a valid syndication package."""


def derive_syndication_package_id(plan_id: str, channel_type: str) -> str:
    key = f"{plan_id}:{channel_type}"
    return "sdp_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def build_syndication_distribution_package(
    package: Mapping[str, Any] | Any,
    *,
    syndication_type: str = "directory_listing",
    partner_id: str = "partner_london_trades_v1",
) -> dict[str, Any]:
    """Generate a structured syndication and partner placement package."""
    plan = build_mock_publication_plan(package)
    syndication_type = syndication_type.lower().strip()
    if syndication_type not in SUPPORTED_SYNDICATION_TYPES:
        raise SyndicationDistributionValidationError(
            f"syndication_type must be one of {sorted(SUPPORTED_SYNDICATION_TYPES)}, got {syndication_type!r}"
        )

    asset = validate_approved_asset_package(package)
    title = asset.get("content_payload", {}).get("title") or "Professional Local Service"
    summary = asset.get("content_payload", {}).get("summary") or "Verified service offering."
    cta_url = plan["cta"]["destination_url"]

    return {
        "schema_version": "1.0.0",
        "syndication_package_id": derive_syndication_package_id(plan["publication_plan_id"], syndication_type),
        "publication_plan_id": plan["publication_plan_id"],
        "asset_id": plan["asset_id"],
        "target_id": plan["target_id"],
        "opportunity_id": plan["opportunity_id"],
        "syndication_type": syndication_type,
        "partner_id": partner_id,
        "syndication_payload": {
            "title": title,
            "summary": summary,
            "canonical_url": cta_url,
            "feed_ready": True,
            "embed_code": f'<iframe src="{cta_url}?embed=1" width="100%" height="400" frameborder="0"></iframe>',
        },
        "scheduled_at": plan["scheduled_at"],
        "external_action": bool(os.getenv("EP050_LIVE_PUBLISH_ENABLED") == "1"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
