# epics/ep_050_distribution_engine/implementation/node_23/social_distribution.py
# EP050 Node 23 — Social Distribution Package Builder & Native Adapter.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial channel-native social distribution package builder supporting thread splitting, hashtags, and social platform formatting.

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
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

SOCIAL_DISTRIBUTION_VERSION = "social_distribution_v1.0.0"
SUPPORTED_NETWORKS = frozenset({"x_twitter", "linkedin", "facebook", "threads", "instagram"})


class SocialDistributionValidationError(ValueError):
    """Raised when a candidate cannot produce a valid channel-native social package."""


def derive_social_package_id(plan_id: str, network: str) -> str:
    key = f"{plan_id}:{network}"
    return "sdp_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _format_posts_for_network(network: str, text: str, cta_url: str, tags: list[str]) -> list[str]:
    tag_str = " ".join(f"#{t.strip('#')}" for t in tags)
    full_text = f"{text}\n\n{tag_str}\n{cta_url}".strip()

    if network == "x_twitter":
        # 280-char chunking
        if len(full_text) <= 280:
            return [full_text]
        # Split into thread
        chunks = []
        words = full_text.split()
        cur = []
        for w in words:
            if len(" ".join(cur + [w])) <= 260:
                cur.append(w)
            else:
                chunks.append(" ".join(cur))
                cur = [w]
        if cur:
            chunks.append(" ".join(cur))
        return [f"{c} ({i+1}/{len(chunks)})" for i, c in enumerate(chunks)]
    return [full_text]


def build_social_distribution_package(
    package: Mapping[str, Any] | Any,
    *,
    network: str = "linkedin",
    hashtags: list[str] | None = None,
    media_attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a channel-native social distribution payload from an approved asset package."""
    plan = build_mock_publication_plan(package)
    network = network.lower().strip()
    if network not in SUPPORTED_NETWORKS:
        raise SocialDistributionValidationError(
            f"network must be one of {sorted(SUPPORTED_NETWORKS)}, got {network!r}"
        )

    asset = validate_approved_asset_package(package)
    body = asset.get("content_payload", {}).get("body") or asset.get("content_payload", {}).get("summary") or "Helpful Service Guide"
    cta_url = plan["cta"]["destination_url"]
    tags = list(hashtags or ["localbusiness", "homeadvice", "service"])

    posts = _format_posts_for_network(network, body, cta_url, tags)

    return {
        "schema_version": "1.0.0",
        "social_package_id": derive_social_package_id(plan["publication_plan_id"], network),
        "publication_plan_id": plan["publication_plan_id"],
        "asset_id": plan["asset_id"],
        "target_id": plan["target_id"],
        "opportunity_id": plan["opportunity_id"],
        "network": network,
        "social_payload": {
            "posts": posts,
            "hashtags": tags,
            "media_attachments": list(media_attachments or []),
            "link_preview": {
                "title": asset.get("content_payload", {}).get("title") or "Resource",
                "url": cta_url,
            },
        },
        "scheduled_at": plan["scheduled_at"],
        "external_action": bool(os.getenv("EP050_LIVE_PUBLISH_ENABLED") == "1"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
