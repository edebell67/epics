# epics/ep_050_distribution_engine/implementation/node_18/alternate_asset_factory.py
# EP050 Node 18 (sibling) — Alternate (non-video) Asset Factory.
#
# Node 18's own video_asset_factory.py unconditionally renders every Node 17 AssetPayload as a
# video, regardless of what Node 14 (Channel Placement Selection) actually recommended -- a real
# gap found and confirmed 2026-08-18 (video_asset_factory.py never reads asset.metadata.format at
# all). Node 14 already recommends four real formats, none of them video:
#   verified_local_listing_with_emergency_hours, step_by_step_troubleshooting_guide,
#   callout_extension_ad_24_7_emergency, community_recommendation_post
#
# This module is Node 18's sibling, not a replacement: it registers the SAME real, already-
# validated Node 17 AssetPayload (title/body_content/disclaimer/CTA/full lineage, no PII, fact-
# traceable -- generate_asset_payload() already enforces all of that) as the final asset for these
# four formats, instead of forcing it through a video-specific renderer it was never meant for.
# It reuses Node 17's own validation rather than re-deriving it; this module's own job is narrower:
# verify the asset is a real member of the cluster it's claimed for (the same check Node 18 makes),
# and structure the same real content appropriately per format -- never inventing a new claim that
# isn't already present in the real AssetPayload (no fabricated business hours, no invented facts).
#
# community_recommendation_post is deliberately marked requires_human_review=True: a business
# voice posting into a community space needs a human to confirm tone/appropriateness before use,
# matching the existing Node 24 finding on record (2026-08-18 board finding: Node 24 built with
# human-in-the-loop review gating "by design", not an oversight).
#
# Fail-closed, deterministic, no network access, no publishing, no credentials. external_action is
# a literal False guarantee, same as every other node in this project.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-19 · Initial version.

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AlternateAssetFactoryError(RuntimeError):
    """Base error for this module."""


class ValidationError(AlternateAssetFactoryError):
    """Raised when required fields are missing, malformed, or an unknown format is requested."""


class LineageError(AlternateAssetFactoryError):
    """Raised when the supplied asset/cluster lineage doesn't check out."""


class ConflictError(AlternateAssetFactoryError):
    """Raised when re-registering an existing alternate_asset_id with different field values."""


# The four real formats Node 14 already recommends that are not video. Any other format
# (including an eventual real "video" recommendation, if Node 14 ever adds one) stays on Node 18's
# own video_asset_factory.py -- this module never claims to handle formats it wasn't built for.
ALLOWED_FORMATS = (
    "verified_local_listing_with_emergency_hours",
    "step_by_step_troubleshooting_guide",
    "callout_extension_ad_24_7_emergency",
    "community_recommendation_post",
)

FORMATS_REQUIRING_HUMAN_REVIEW = ("community_recommendation_post",)

_AD_HEADLINE_MAX = 30
_AD_DESCRIPTION_MAX = 90


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise ValidationError(f"Input must be a dict or have a to_dict() method, got: {type(value).__name__}")


def _compute_deterministic_id(cluster_id: str, asset_id: str, asset_format: str) -> str:
    token = f"{cluster_id}:{asset_id}:{asset_format}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"alt_{digest}"


def _build_listing_content(asset_d: dict[str, Any]) -> dict[str, Any]:
    """A verified local listing: the real title/body as headline/summary, plus an honest
    availability note -- never a fabricated specific hours claim, since no node in this pipeline
    registers real business hours anywhere."""
    return {
        "headline": asset_d["title"],
        "summary": asset_d["body_content"],
        "availability_note": "Contact for current availability -- see call to action.",
        "verified_badge": True,
    }


def _build_guide_content(asset_d: dict[str, Any]) -> dict[str, Any]:
    """A step-by-step guide: the real body_content split into ordered steps on paragraph
    boundaries -- the same real fact-derived text Node 17 already produced, just restructured."""
    paragraphs = [p.strip() for p in str(asset_d["body_content"]).split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [str(asset_d["body_content"]).strip()]
    return {
        "title": asset_d["title"],
        "steps": [{"step_number": i + 1, "text": p} for i, p in enumerate(paragraphs)],
    }


def _build_ad_content(asset_d: dict[str, Any]) -> dict[str, Any]:
    """A callout-extension ad: the real title/body truncated to real ad-copy length limits --
    truncation only, never new copy invented."""
    return {
        "headline": str(asset_d["title"])[:_AD_HEADLINE_MAX],
        "description": str(asset_d["body_content"])[:_AD_DESCRIPTION_MAX],
        "callout_extensions": [asset_d["call_to_action"]],
    }


def _build_community_post_content(asset_d: dict[str, Any]) -> dict[str, Any]:
    """A community recommendation post: the real body_content plus an explicit disclosure that
    it's posted on behalf of the business -- required transparency, not decorative."""
    return {
        "body": asset_d["body_content"],
        "disclosure": "Posted on behalf of the business this content is about.",
    }


_FORMAT_BUILDERS = {
    "verified_local_listing_with_emergency_hours": _build_listing_content,
    "step_by_step_troubleshooting_guide": _build_guide_content,
    "callout_extension_ad_24_7_emergency": _build_ad_content,
    "community_recommendation_post": _build_community_post_content,
}


@dataclass(frozen=True)
class AlternateAssetRecord:
    alternate_asset_id: str
    format: str
    cluster_id: str
    asset_id: str
    target_id: str
    signal_id: str
    classification_id: str
    opportunity_id: str
    path_id: str
    selection_id: str
    content: dict[str, Any]
    call_to_action: str
    safety_disclaimer: str
    fact_ids: list[str]
    external_action: bool
    requires_human_review: bool
    created_at: str
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AlternateAssetRegistry:
    """Local, JSON-file-backed, fixture-only registry -- same idempotent/conflict persistence
    pattern as every other node registry in this project (Node 18's video registry included)."""

    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, dict[str, Any]]:
        raw = self.storage_path.read_text(encoding="utf-8")
        return json.loads(raw) if raw.strip() else {}

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        temp_path = self.storage_path.with_suffix(f".tmp{id(self)}")
        temp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self.storage_path)

    def generate_and_register(self, *, asset: Any, cluster: Any) -> AlternateAssetRecord:
        asset_d = _to_dict(asset)
        cluster_d = _to_dict(cluster)

        asset_format = str((asset_d.get("metadata") or {}).get("format", "")).strip()
        if asset_format not in ALLOWED_FORMATS:
            raise ValidationError(
                f"asset.metadata.format must be one of {ALLOWED_FORMATS} for this factory, got: {asset_format!r} "
                "-- a video-shaped format belongs to node_18/video_asset_factory.py instead"
            )

        # Exact lineage: generate_asset_payload() (Node 17) already enforces this before an
        # AssetPayload can even exist -- this is a defensive re-check, not the primary gate.
        for req_field in ("target_id", "signal_id", "classification_id", "opportunity_id", "path_id", "selection_id"):
            if not asset_d.get(req_field):
                raise LineageError(f"Node 17 asset is missing mandatory lineage field {req_field!r}")

        cluster_member_selection_ids = {m.get("selection_id") for m in (cluster_d.get("members") or [])}
        if str(asset_d["selection_id"]) not in cluster_member_selection_ids:
            raise LineageError(
                "This asset's selection_id is not a member of the supplied Node15 cluster "
                "(the asset must belong to the campaign cluster it is generated for)"
            )

        metadata = asset_d.get("metadata") or {}
        if metadata.get("external_action") not in (False, "false"):
            raise ValidationError("Node17 asset metadata.external_action must be literal False")

        safety_disclaimer = str(asset_d.get("safety_disclaimer", "")).strip()
        call_to_action = str(asset_d.get("call_to_action", "")).strip()
        if not safety_disclaimer:
            raise ValidationError("Node17 asset is missing a mandatory safety_disclaimer")
        if not call_to_action:
            raise ValidationError("Node17 asset is missing a mandatory call_to_action")

        fact_ids = asset_d.get("fact_ids") or []
        if not fact_ids:
            raise LineageError("Node17 asset has no fact_ids; cannot verify factual lineage")

        cluster_id = str(cluster_d.get("cluster_id", "")).strip()
        asset_id = str(asset_d.get("asset_id", "")).strip()
        if not cluster_id or not asset_id:
            raise LineageError("cluster_id and asset_id are both required to derive a stable alternate_asset_id")

        content = _FORMAT_BUILDERS[asset_format](asset_d)
        alternate_asset_id = _compute_deterministic_id(cluster_id, asset_id, asset_format)

        candidate = AlternateAssetRecord(
            alternate_asset_id=alternate_asset_id,
            format=asset_format,
            cluster_id=cluster_id,
            asset_id=asset_id,
            target_id=str(asset_d["target_id"]),
            signal_id=str(asset_d["signal_id"]),
            classification_id=str(asset_d["classification_id"]),
            opportunity_id=str(asset_d["opportunity_id"]),
            path_id=str(asset_d["path_id"]),
            selection_id=str(asset_d["selection_id"]),
            content=content,
            call_to_action=call_to_action,
            safety_disclaimer=safety_disclaimer,
            fact_ids=list(fact_ids),
            external_action=False,
            requires_human_review=asset_format in FORMATS_REQUIRING_HUMAN_REVIEW,
            created_at=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        )
        return self._persist(candidate)

    def _persist(self, candidate: AlternateAssetRecord) -> AlternateAssetRecord:
        data = self._load()
        existing = data.get(candidate.alternate_asset_id)
        if existing is not None:
            non_identity_fields = ("created_at", "recorded_at")
            comparable_existing = {k: v for k, v in existing.items() if k not in non_identity_fields}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k not in non_identity_fields}
            if comparable_existing == comparable_candidate:
                return self._record_from_dict(existing)  # idempotent
            raise ConflictError(
                f"alternate_asset_id {candidate.alternate_asset_id!r} already registered with different field "
                "values; conflicting duplicate registrations are rejected fail-closed"
            )
        data[candidate.alternate_asset_id] = candidate.to_dict()
        self._save(data)
        return candidate

    @staticmethod
    def _record_from_dict(data: dict[str, Any]) -> AlternateAssetRecord:
        return AlternateAssetRecord(**data)

    def get(self, alternate_asset_id: str) -> AlternateAssetRecord | None:
        data = self._load()
        record = data.get(alternate_asset_id)
        return self._record_from_dict(record) if record is not None else None

    def list(self) -> list[AlternateAssetRecord]:
        return [self._record_from_dict(r) for r in self._load().values()]
