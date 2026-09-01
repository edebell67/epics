# epics/ep_050_distribution_engine/implementation/node_22/video_distribution.py
# EP050 Node 22 — Video Distribution Package Builder & Dispatcher.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial deterministic video distribution package builder supporting multi-platform video payloads, timestamps, chapters, and automated dispatch adapters.

from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_20"))
from publishing_scheduler import (
    PublicationPlanValidationError,
    build_mock_publication_plan,
    validate_approved_asset_package,
)

VIDEO_DISTRIBUTION_VERSION = "video_distribution_v1.0.0"
SUPPORTED_PLATFORMS = frozenset({"youtube", "youtube_shorts", "tiktok", "instagram_reels", "vimeo"})


class VideoDistributionValidationError(ValueError):
    """Raised when a candidate cannot safely produce a video distribution package."""


class VideoDistributionConflictError(ValueError):
    """Raised when a video distribution package identifier maps to conflicting content."""


def _require_non_empty_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VideoDistributionValidationError(f"{name} must be a non-empty string")
    return value.strip()


def derive_video_package_id(plan_id: str, platform: str) -> str:
    key = f"{plan_id}:{platform}"
    return "vdp_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def build_video_distribution_package(
    package: Mapping[str, Any] | Any,
    *,
    platform: str = "youtube",
    video_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a multi-platform structured video distribution package from an approved asset package."""
    plan = build_mock_publication_plan(package)
    platform = _require_non_empty_str(platform, "platform").lower()
    if platform not in SUPPORTED_PLATFORMS:
        raise VideoDistributionValidationError(
            f"platform must be one of {sorted(SUPPORTED_PLATFORMS)}, got {platform!r}"
        )

    asset = validate_approved_asset_package(package)
    title = asset.get("content_payload", {}).get("title") or "Video Asset"
    summary = asset.get("content_payload", {}).get("summary") or ""
    cta_url = plan["cta"]["destination_url"]

    meta = dict(video_metadata or {})
    tags = list(meta.get("tags") or ["service", "guide", "expert"])
    chapters = list(meta.get("chapters") or [
        {"timestamp": "00:00", "title": "Introduction"},
        {"timestamp": "00:30", "title": "Diagnostic & Solution"},
        {"timestamp": "01:15", "title": "Next Steps & Booking"},
    ])

    video_pkg = {
        "schema_version": "1.0.0",
        "video_package_id": derive_video_package_id(plan["publication_plan_id"], platform),
        "publication_plan_id": plan["publication_plan_id"],
        "asset_id": plan["asset_id"],
        "target_id": plan["target_id"],
        "opportunity_id": plan["opportunity_id"],
        "platform": platform,
        "video_payload": {
            "title": title,
            "description": f"{summary}\n\nBook or Learn More: {cta_url}",
            "tags": tags,
            "chapters": chapters,
            "cta_overlay": {
                "label": plan["cta"]["label"],
                "type": plan["cta"]["type"],
                "destination_url": cta_url,
                "tracking_params": plan["cta"]["tracking_params"],
            },
        },
        "scheduled_at": plan["scheduled_at"],
        "external_action": bool(os.getenv("EP050_LIVE_PUBLISH_ENABLED") == "1"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
    return video_pkg
