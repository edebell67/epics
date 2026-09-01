# epics/ep_050_distribution_engine/implementation/node_07/social_video_discovery.py
# EP050 Node 07 — Social / Video Discovery.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds automated live ingestion: register_from_live_source() queries the
#   real YouTube Data API v3 (search.list + videos.list) and derives theme/format/
#   observed_metrics from the live response -- no human types signal content. Gated fail-closed
#   behind EP050_LIVE_FETCH_ENABLED=1 (default off) plus EP050_YOUTUBE_API_KEY (user-supplied).
#   Every live record carries a verifiable fetch_receipt. Satisfies the user-mandated CORE
#   REQUIREMENT (2026-08-17) that Nodes 05-10 be genuinely automated.
# v1.0.0 · 2026-08-17 · Initial deterministic, offline, fixture-only social/video theme discovery registry.
#
# Scope: EP050 Node 07 only, per allocation 20260817T052644427_codex_7bef37f7.
# The manual/fixture register() path is unchanged: fail-closed, deterministic, no network access.
# The new register_from_live_source() path performs exactly two read-only HTTPS GETs per call
# (search, then statistics for the top result), off by default, and writes through the same
# validated register() contract. Every record must reference a target_id registered by
# Node 01, described by Node 02, segmented by Node 03, defined by Node 04, with a demand
# signal from Node 05, and a question from Node 06 (six-way exact lineage per the allocation).

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_01"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_02"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_03"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_04"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_05"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_06"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from live_fetch import FetchReceipt, http_get_json, make_receipt, require_credential, require_live_fetch_enabled  # noqa: E402

# manual_curation/synthetic_fixture remain for offline fixture use; video_api is the one live
# source type this node supports, backed by register_from_live_source() below.
ALLOWED_SOURCE_TYPES = frozenset({"manual_curation", "synthetic_fixture", "video_api"})
REQUIRED_GEOGRAPHY_FIELDS = ("locality", "region", "country")

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s\-.]?){7,}\d")


class SocialVideoDiscoveryError(RuntimeError):
    """Base class for Node 07 failures. Fail-closed: never partially writes."""


class ValidationError(SocialVideoDiscoveryError):
    """Raised when required fields are missing, malformed, or contain prohibited PII."""


class UnknownTargetError(SocialVideoDiscoveryError):
    """Raised when the referenced target_id is not registered/described/segmented/defined/signaled/questioned upstream."""


class ConflictError(SocialVideoDiscoveryError):
    """Raised when a signal_id already exists with different field values."""


class NoLiveResultsError(SocialVideoDiscoveryError):
    """Raised when a live fetch succeeded but returned no item to register."""


YOUTUBE_API_KEY_ENV = "EP050_YOUTUBE_API_KEY"
YOUTUBE_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
_ISO8601_DURATION_PATTERN = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
_INTENT_KEYWORDS = {
    "how": "troubleshooting", "why": "diagnostic_inquiry", "fix": "seeking_repair",
    "repair": "seeking_repair", "diy": "seeking_diy_solution", "vs": "comparison_shopping",
}


def _parse_duration_seconds(duration: str) -> int:
    match = _ISO8601_DURATION_PATTERN.match(duration or "")
    if not match:
        return 0
    hours, minutes, seconds = (int(group) if group else 0 for group in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def _derive_intent_cues(title: str) -> list[str]:
    lowered = title.lower()
    cues = sorted({label for keyword, label in _INTENT_KEYWORDS.items() if keyword in lowered})
    return cues or ["general_interest"]


def fetch_social_video_theme(topic: str) -> tuple[dict[str, Any], FetchReceipt]:
    """Live YouTube Data API v3 search for the top video about topic, plus its real statistics.

    Requires EP050_LIVE_FETCH_ENABLED=1 and EP050_YOUTUBE_API_KEY (user-supplied). Performs
    exactly two read-only HTTPS GETs: search.list then videos.list for the top result.
    """
    require_live_fetch_enabled()
    api_key = require_credential(YOUTUBE_API_KEY_ENV)
    query = topic.replace("_", " ").strip()
    search_params = urllib.parse.urlencode(
        {"part": "snippet", "q": query, "type": "video", "maxResults": 5, "key": api_key}
    )
    search_payload, search_status = http_get_json(f"{YOUTUBE_SEARCH_ENDPOINT}?{search_params}")
    items = search_payload.get("items") or []
    if not items:
        raise NoLiveResultsError(f"YouTube search returned no videos for topic {topic!r}")
    top = items[0]
    video_id = top["id"]["videoId"]
    video_title = top["snippet"]["title"]

    videos_params = urllib.parse.urlencode({"part": "statistics,contentDetails", "id": video_id, "key": api_key})
    videos_payload, _ = http_get_json(f"{YOUTUBE_VIDEOS_ENDPOINT}?{videos_params}")
    video_items = videos_payload.get("items") or []
    stats = video_items[0].get("statistics", {}) if video_items else {}
    duration = video_items[0].get("contentDetails", {}).get("duration", "PT0S") if video_items else "PT0S"

    receipt = make_receipt(endpoint=YOUTUBE_SEARCH_ENDPOINT, http_status=search_status, item_count=len(items))
    result = {
        "title": video_title,
        "video_id": video_id,
        "duration_seconds": _parse_duration_seconds(duration),
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
    }
    return result, receipt


def _check_no_pii(name: str, value: str) -> None:
    if EMAIL_PATTERN.search(value):
        raise ValidationError(f"{name} appears to contain an email address; prohibited PII rejected fail-closed")
    if PHONE_PATTERN.search(value):
        raise ValidationError(f"{name} appears to contain a phone number; prohibited PII rejected fail-closed")


def _validate_non_empty_string(name: str, value: Any, *, check_pii: bool = False) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is required and must be a non-empty string, got: {value!r}")
    if check_pii:
        _check_no_pii(name, value)


def _validate_non_empty_string_list(name: str, value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{name} is required and must be a non-empty list, got: {value!r}")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{name}[{index}] must be a non-empty string, got: {item!r}")


def _validate_geography(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"geography must be an object, got: {type(value).__name__}")
    for key in REQUIRED_GEOGRAPHY_FIELDS:
        subvalue = value.get(key)
        if not isinstance(subvalue, str) or not subvalue.strip():
            raise ValidationError(f"geography.{key} is required and must be a non-empty string")


def _validate_observed_metrics(value: Any) -> None:
    if not isinstance(value, dict) or not value:
        raise ValidationError("observed_metrics is required and must be a non-empty object")
    for key, metric in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValidationError("observed_metrics keys must be non-empty strings")
        if isinstance(metric, bool) or not isinstance(metric, (int, float)):
            raise ValidationError(f"observed_metrics[{key!r}] must be numeric, got: {metric!r}")
        if metric < 0:
            raise ValidationError(f"observed_metrics[{key!r}] must be non-negative, got: {metric!r}")


def _validate_observed_at(value: Any) -> None:
    if not isinstance(value, str):
        raise ValidationError("observed_at must be an ISO 8601 string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO 8601 date format for observed_at: {value!r}") from exc


def validate_fields(
    *,
    signal_id: str,
    target_id: str,
    platform: str,
    format: str,  # noqa: A002 - matches the allocation's own field name
    topic: str,
    theme: str,
    intent_cues: list[str],
    geography: dict[str, Any],
    observed_metrics: dict[str, Any],
    observed_at: str,
    source_type: str,
    evidence: str,
    metadata: dict[str, Any] | None,
) -> None:
    _validate_non_empty_string("signal_id", signal_id)
    _validate_non_empty_string("target_id", target_id)
    _validate_non_empty_string("platform", platform, check_pii=True)
    _validate_non_empty_string("format", format)
    _validate_non_empty_string("topic", topic, check_pii=True)
    _validate_non_empty_string("theme", theme, check_pii=True)
    _validate_non_empty_string_list("intent_cues", intent_cues)
    _validate_geography(geography)
    _validate_observed_metrics(observed_metrics)
    _validate_observed_at(observed_at)
    if not isinstance(source_type, str) or source_type not in ALLOWED_SOURCE_TYPES:
        raise ValidationError(
            f"source_type must be one of {sorted(ALLOWED_SOURCE_TYPES)} (offline MVP boundary), got: {source_type!r}"
        )
    _validate_non_empty_string("evidence", evidence)
    if metadata is not None and not isinstance(metadata, dict):
        raise ValidationError(f"metadata must be an object or None, got: {type(metadata).__name__}")


@dataclass(frozen=True)
class SocialVideoSignalRecord:
    signal_id: str
    target_id: str
    platform: str
    format: str
    topic: str
    theme: str
    intent_cues: list[str]
    geography: dict[str, str]
    observed_metrics: dict[str, Any]
    observed_at: str
    source_type: str
    evidence: str
    metadata: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SocialVideoSignalRegistry:
    """Local, JSON-file-backed, fixture-only Node 07 registry. No network I/O, no live browsing.

    Requires the referenced target_id to exist in all six upstream registries: Node 01
    (TargetRegistry), Node 02 (ProductIntelligenceRegistry), Node 03 (AudienceSegmentRegistry,
    via list_for_target), Node 04 (ConversionDefinitionRegistry), Node 05 (DemandSignalRegistry,
    via list_for_target), Node 06 (QuestionRegistry, via list_for_target) -- exact lineage per
    the allocation.
    """

    def __init__(
        self,
        storage_path: Path,
        target_registry: TargetRegistry,
        product_registry: ProductIntelligenceRegistry,
        audience_registry: AudienceSegmentRegistry,
        conversion_registry: ConversionDefinitionRegistry,
        demand_signal_registry: DemandSignalRegistry,
        question_registry: QuestionRegistry,
    ):
        self.storage_path = Path(storage_path)
        self.target_registry = target_registry
        self.product_registry = product_registry
        self.audience_registry = audience_registry
        self.conversion_registry = conversion_registry
        self.demand_signal_registry = demand_signal_registry
        self.question_registry = question_registry
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

    def register(
        self,
        *,
        signal_id: str | None = None,
        target_id: str | None = None,
        platform: str | None = None,
        format: str | None = None,  # noqa: A002
        topic: str | None = None,
        theme: str | None = None,
        intent_cues: list[str] | None = None,
        geography: dict[str, str] | None = None,
        observed_metrics: dict[str, Any] | None = None,
        observed_at: str | None = None,
        source_type: str | None = None,
        evidence: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SocialVideoSignalRecord:
        validate_fields(
            signal_id=signal_id, target_id=target_id, platform=platform, format=format, topic=topic,
            theme=theme, intent_cues=intent_cues, geography=geography, observed_metrics=observed_metrics,
            observed_at=observed_at, source_type=source_type, evidence=evidence, metadata=metadata,
        )

        # Node01-06->07 six-way contract/integration checks, fail-closed.
        if self.target_registry.get(target_id) is None:
            raise UnknownTargetError(f"target_id {target_id!r} is not registered in the Node 01 registry")
        if self.product_registry.get(target_id) is None:
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 02 product intelligence record")
        if not self.audience_registry.list_for_target(target_id):
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 03 audience segment")
        if self.conversion_registry.get(target_id) is None:
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 04 conversion definition")
        if not self.demand_signal_registry.list_for_target(target_id):
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 05 demand signal")
        if not self.question_registry.list_for_target(target_id):
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 06 question")

        candidate = SocialVideoSignalRecord(
            signal_id=signal_id, target_id=target_id, platform=platform, format=format, topic=topic,
            theme=theme, intent_cues=list(intent_cues), geography=dict(geography),
            observed_metrics=dict(observed_metrics), observed_at=observed_at, source_type=source_type,
            evidence=evidence, metadata=dict(metadata) if metadata else {},
        )

        data = self._load()
        existing = data.get(signal_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "recorded_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "recorded_at"}
            if comparable_existing == comparable_candidate:
                return SocialVideoSignalRecord(**existing)  # idempotent
            raise ConflictError(
                f"signal_id {signal_id!r} already registered with different field values; "
                "conflicting duplicate registrations are rejected fail-closed"
            )

        data[signal_id] = candidate.to_dict()
        self._save(data)
        return candidate

    def register_from_live_source(
        self,
        *,
        signal_id: str,
        target_id: str,
        topic: str,
        geography: dict[str, str],
        observed_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SocialVideoSignalRecord:
        """Automated ingestion path: performs real YouTube Data API calls and derives
        theme/format/observed_metrics/intent_cues from the live response -- no human types the
        signal content. Writes through the same validated register() contract.
        """
        result, receipt = fetch_social_video_theme(topic)
        intent_cues = _derive_intent_cues(result["title"])
        live_metadata = dict(metadata) if metadata else {}
        live_metadata["fetch_receipt"] = receipt.to_dict()
        live_metadata["video_id"] = result["video_id"]
        return self.register(
            signal_id=signal_id,
            target_id=target_id,
            platform="youtube",
            format="short_video" if result["duration_seconds"] and result["duration_seconds"] <= 60 else "long_video",
            topic=topic,
            theme=result["title"],
            intent_cues=intent_cues,
            geography=geography,
            observed_metrics={
                "view_count": result["view_count"],
                "like_count": result["like_count"],
                "comment_count": result["comment_count"],
            },
            observed_at=observed_at or datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            source_type="video_api",
            evidence=(
                f"Automated live fetch from the YouTube Data API (HTTP {receipt.http_status}, "
                f"video {result['video_id']}); see metadata.fetch_receipt for independent verification."
            ),
            metadata=live_metadata,
        )

    def get(self, signal_id: str) -> SocialVideoSignalRecord | None:
        data = self._load()
        record = data.get(signal_id)
        return SocialVideoSignalRecord(**record) if record is not None else None

    def list(self) -> list[SocialVideoSignalRecord]:
        return [SocialVideoSignalRecord(**record) for record in self._load().values()]

    def list_for_target(self, target_id: str) -> list[SocialVideoSignalRecord]:
        return [record for record in self.list() if record.target_id == target_id]
