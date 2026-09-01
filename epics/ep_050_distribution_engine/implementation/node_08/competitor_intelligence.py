# epics/ep_050_distribution_engine/implementation/node_08/competitor_intelligence.py
# EP050 Node 08 — Competitor Intelligence.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds automated live ingestion: register_from_live_source() performs a
#   real, read-only HTTP fetch of a caller-supplied competitor URL and derives competitor_name/
#   relevance_score/competition_indicator deterministically from the fetched page -- no human
#   types signal content. Gated fail-closed behind EP050_LIVE_FETCH_ENABLED=1 (default off);
#   no credential required since this is a single public-page GET. Every live record carries a
#   verifiable fetch_receipt (real endpoint/status/timestamp) in metadata. Satisfies the
#   user-mandated CORE REQUIREMENT (2026-08-17) that Nodes 05-10 be genuinely automated.
# v1.0.0 · 2026-08-17 · Initial deterministic, offline, fixture-only competitor intelligence registry.
#
# Scope: EP050 Node 08 only, per allocation 20260817T054639708_codex_732b65de.
# The manual/fixture register() path is unchanged and remains fail-closed, deterministic, with
# no network access. The new register_from_live_source() path performs exactly one read-only
# HTTP GET per call, off by default, and writes through the same validated register() contract.
# Every record must reference a target_id registered by Node 01, described by Node 02,
# segmented by Node 03, defined by Node 04, with a demand signal from Node 05, a question from
# Node 06, and a social/video signal from Node 07 (seven-way exact lineage per the allocation).

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_07"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from social_video_discovery import SocialVideoSignalRegistry  # noqa: E402
from live_fetch import FetchReceipt, http_get_text, make_receipt, require_live_fetch_enabled  # noqa: E402

# manual_curation/synthetic_fixture remain for offline fixture use; web_fetch is the one live
# source type this node supports, backed by register_from_live_source() below -- not an
# unverified label, every web_fetch record carries a real fetch_receipt.
ALLOWED_SOURCE_TYPES = frozenset({"manual_curation", "synthetic_fixture", "web_fetch"})
ALLOWED_COMPETITION_INDICATORS = frozenset({"low", "medium", "high"})
REQUIRED_GEOGRAPHY_FIELDS = ("locality", "region", "country")

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s\-.]?){7,}\d")


class CompetitorIntelligenceError(RuntimeError):
    """Base class for Node 08 failures. Fail-closed: never partially writes."""


class ValidationError(CompetitorIntelligenceError):
    """Raised when required fields are missing, malformed, or contain prohibited PII."""


class UnknownTargetError(CompetitorIntelligenceError):
    """Raised when the referenced target_id is not registered/described/segmented/defined/
    signaled/questioned/observed upstream."""


class ConflictError(CompetitorIntelligenceError):
    """Raised when a signal_id already exists with different field values."""


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


def _validate_geography(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"geography must be an object, got: {type(value).__name__}")
    for key in REQUIRED_GEOGRAPHY_FIELDS:
        subvalue = value.get(key)
        if not isinstance(subvalue, str) or not subvalue.strip():
            raise ValidationError(f"geography.{key} is required and must be a non-empty string")


def _validate_relevance_score(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"relevance_score must be numeric, got: {value!r}")
    if not (0.0 <= float(value) <= 1.0):
        raise ValidationError(f"relevance_score must be between 0.0 and 1.0 inclusive, got: {value!r}")


_TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_PATTERN = re.compile(r"<[^>]+>")


def _strip_html(raw_html: str) -> str:
    text = _TAG_PATTERN.sub(" ", raw_html)
    return re.sub(r"\s+", " ", text).strip()


def _extract_title(raw_html: str, fallback: str) -> str:
    match = _TITLE_PATTERN.search(raw_html)
    if match:
        title = _strip_html(match.group(1))
        if title:
            return title
    return fallback


def fetch_competitor_page(url: str) -> tuple[str, str, FetchReceipt]:
    """Live, read-only GET of a single competitor URL. Fail-closed if live fetch is disabled.

    Returns (title, visible_text, receipt). No credential is required -- this fetches one
    public page exactly as a browser would, no authentication, no bulk crawling.
    """
    require_live_fetch_enabled()
    raw_html, status = http_get_text(url)
    visible_text = _strip_html(raw_html)
    domain = urllib.parse.urlparse(url).netloc or url
    title = _extract_title(raw_html, fallback=domain)
    receipt = make_receipt(endpoint=url, http_status=status, item_count=1)
    return title, visible_text, receipt


def _derive_relevance_and_competition(topic: str, visible_text: str) -> tuple[float, str]:
    """Deterministic heuristic derived from the live-fetched page text, not caller judgment.

    relevance_score is the (capped) frequency of the topic's first keyword in the fetched
    text; competition_indicator is a fixed threshold mapping of that same score. Crude but
    fully automated and reproducible from the fetch itself.
    """
    normalized_topic = topic.strip().replace("_", " ").replace("-", " ")
    keyword = normalized_topic.split()[0].lower() if normalized_topic.split() else ""
    keyword_hits = visible_text.lower().count(keyword) if keyword else 0
    relevance_score = round(min(1.0, keyword_hits / 5), 4)
    if relevance_score < 0.34:
        competition_indicator = "low"
    elif relevance_score < 0.67:
        competition_indicator = "medium"
    else:
        competition_indicator = "high"
    return relevance_score, competition_indicator


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
    competitor_name: str,
    channel: str,
    topic: str,
    query: str,
    attention_source: str,
    relevance_score: float,
    competition_indicator: str,
    geography: dict[str, Any],
    observed_at: str,
    source_type: str,
    evidence: str,
    metadata: dict[str, Any] | None,
) -> None:
    _validate_non_empty_string("signal_id", signal_id)
    _validate_non_empty_string("target_id", target_id)
    _validate_non_empty_string("competitor_name", competitor_name, check_pii=True)
    _validate_non_empty_string("channel", channel)
    _validate_non_empty_string("topic", topic, check_pii=True)
    _validate_non_empty_string("query", query, check_pii=True)
    _validate_non_empty_string("attention_source", attention_source)
    _validate_relevance_score(relevance_score)
    if not isinstance(competition_indicator, str) or competition_indicator not in ALLOWED_COMPETITION_INDICATORS:
        raise ValidationError(
            f"competition_indicator must be one of {sorted(ALLOWED_COMPETITION_INDICATORS)}, "
            f"got: {competition_indicator!r}"
        )
    _validate_geography(geography)
    _validate_observed_at(observed_at)
    if not isinstance(source_type, str) or source_type not in ALLOWED_SOURCE_TYPES:
        raise ValidationError(
            f"source_type must be one of {sorted(ALLOWED_SOURCE_TYPES)} (offline MVP boundary), got: {source_type!r}"
        )
    _validate_non_empty_string("evidence", evidence)
    if metadata is not None and not isinstance(metadata, dict):
        raise ValidationError(f"metadata must be an object or None, got: {type(metadata).__name__}")


@dataclass(frozen=True)
class CompetitorSignalRecord:
    signal_id: str
    target_id: str
    competitor_name: str
    channel: str
    topic: str
    query: str
    attention_source: str
    relevance_score: float
    competition_indicator: str
    geography: dict[str, str]
    observed_at: str
    source_type: str
    evidence: str
    metadata: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CompetitorSignalRegistry:
    """Local, JSON-file-backed, fixture-only Node 08 registry. No network I/O, no live research.

    Requires the referenced target_id to exist in all seven upstream registries: Node 01
    (TargetRegistry), Node 02 (ProductIntelligenceRegistry), Node 03 (AudienceSegmentRegistry,
    via list_for_target), Node 04 (ConversionDefinitionRegistry), Node 05 (DemandSignalRegistry,
    via list_for_target), Node 06 (QuestionRegistry, via list_for_target), Node 07
    (SocialVideoSignalRegistry, via list_for_target) -- exact lineage per the allocation.
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
        social_video_registry: SocialVideoSignalRegistry,
    ):
        self.storage_path = Path(storage_path)
        self.target_registry = target_registry
        self.product_registry = product_registry
        self.audience_registry = audience_registry
        self.conversion_registry = conversion_registry
        self.demand_signal_registry = demand_signal_registry
        self.question_registry = question_registry
        self.social_video_registry = social_video_registry
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
        competitor_name: str | None = None,
        channel: str | None = None,
        topic: str | None = None,
        query: str | None = None,
        attention_source: str | None = None,
        relevance_score: float | None = None,
        competition_indicator: str | None = None,
        geography: dict[str, str] | None = None,
        observed_at: str | None = None,
        source_type: str | None = None,
        evidence: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CompetitorSignalRecord:
        validate_fields(
            signal_id=signal_id, target_id=target_id, competitor_name=competitor_name, channel=channel,
            topic=topic, query=query, attention_source=attention_source, relevance_score=relevance_score,
            competition_indicator=competition_indicator, geography=geography, observed_at=observed_at,
            source_type=source_type, evidence=evidence, metadata=metadata,
        )

        # Node01-07->08 seven-way contract/integration checks, fail-closed.
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
        if not self.social_video_registry.list_for_target(target_id):
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 07 social/video signal")

        candidate = CompetitorSignalRecord(
            signal_id=signal_id, target_id=target_id, competitor_name=competitor_name, channel=channel,
            topic=topic, query=query, attention_source=attention_source, relevance_score=float(relevance_score),
            competition_indicator=competition_indicator, geography=dict(geography), observed_at=observed_at,
            source_type=source_type, evidence=evidence, metadata=dict(metadata) if metadata else {},
        )

        data = self._load()
        existing = data.get(signal_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "recorded_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "recorded_at"}
            if comparable_existing == comparable_candidate:
                return CompetitorSignalRecord(**existing)  # idempotent
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
        competitor_url: str,
        topic: str,
        query: str,
        geography: dict[str, str],
        channel: str = "website",
        competitor_name: str | None = None,
        observed_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CompetitorSignalRecord:
        """Automated ingestion path: performs one real HTTP GET of competitor_url and derives
        competitor_name/relevance_score/competition_indicator deterministically from the fetched
        page -- no human types the signal content. Fail-closed via fetch_competitor_page() if
        live fetch is disabled. Writes through the same validated register() contract used by
        manual/fixture records, so every existing invariant (PII screen, lineage, idempotency,
        conflict detection) is enforced unchanged.
        """
        title, visible_text, receipt = fetch_competitor_page(competitor_url)
        relevance_score, competition_indicator = _derive_relevance_and_competition(topic, visible_text)
        live_metadata = dict(metadata) if metadata else {}
        live_metadata["fetch_receipt"] = receipt.to_dict()
        live_metadata["fetched_text_excerpt"] = visible_text[:500]
        return self.register(
            signal_id=signal_id,
            target_id=target_id,
            competitor_name=competitor_name or title,
            channel=channel,
            topic=topic,
            query=query,
            attention_source=f"web_fetch:{urllib.parse.urlparse(competitor_url).netloc}",
            relevance_score=relevance_score,
            competition_indicator=competition_indicator,
            geography=geography,
            observed_at=observed_at or datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            source_type="web_fetch",
            evidence=(
                f"Automated live fetch of {competitor_url} (HTTP {receipt.http_status}); "
                "see metadata.fetch_receipt for independent verification."
            ),
            metadata=live_metadata,
        )

    def get(self, signal_id: str) -> CompetitorSignalRecord | None:
        data = self._load()
        record = data.get(signal_id)
        return CompetitorSignalRecord(**record) if record is not None else None

    def list(self) -> list[CompetitorSignalRecord]:
        return [CompetitorSignalRecord(**record) for record in self._load().values()]

    def list_for_target(self, target_id: str) -> list[CompetitorSignalRecord]:
        return [record for record in self.list() if record.target_id == target_id]
