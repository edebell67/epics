# epics/ep_050_distribution_engine/implementation/node_10/trend_detection.py
# EP050 Node 10 — Trend Detection.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds automated live ingestion: register_from_live_aggregation() computes
#   baseline_value/current_value and their sample counts by counting real Node05-09 signals
#   whose observed_at falls in each half of the caller-supplied window -- not manually-entered
#   numbers. No network access is needed for this node; automation here means "derived from the
#   real upstream chain," exactly as this node's own contract always specified. Satisfies the
#   user-mandated CORE REQUIREMENT (2026-08-17) that Nodes 05-10 be genuinely automated.
# v1.0.0 · 2026-08-17 · Initial deterministic, offline, fixture-only trend detection registry.
#
# Scope: EP050 Node 10 only, per allocation 20260817T062636269_codex_ea5e04ff.
# Fail-closed, deterministic, no network access, no live monitoring, browsing, scraping,
# APIs, or credentials; no production datastore access. This is the final node in Claude's
# originally-allocated Nodes 01-10 range.
#
# Every record must reference a target_id registered by Node 01, described by Node 02,
# segmented by Node 03, defined by Node 04, with a demand signal from Node 05, a question
# from Node 06, a social/video signal from Node 07, a competitor signal from Node 08, and
# a community signal from Node 09 (nine-way exact lineage per the allocation).
#
# Trend metrics (velocity, direction, spike_flag, confidence) are DERIVED deterministically
# by this module from the caller-supplied baseline/current observations, not accepted as
# free-form input -- computing the trend from upstream signals is this node's own job.

from __future__ import annotations

import json
import re
import sys
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_08"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_09"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from social_video_discovery import SocialVideoSignalRegistry  # noqa: E402
from competitor_intelligence import CompetitorSignalRegistry  # noqa: E402
from community_intelligence import CommunitySignalRegistry  # noqa: E402

# manual_curation/synthetic_fixture remain for offline fixture use; auto_aggregated is the one
# live source type this node supports, backed by register_from_live_aggregation() below -- the
# baseline/current values are counted from real Node05-09 records, not typed by a caller.
ALLOWED_SOURCE_TYPES = frozenset({"manual_curation", "synthetic_fixture", "auto_aggregated"})
REQUIRED_GEOGRAPHY_FIELDS = ("locality", "region", "country")

# Deterministic trend-classification thresholds. Documented here because they are load-bearing
# for direction/spike_flag/confidence outputs and any change must be a version-history event.
FLAT_VELOCITY_DEADBAND = 0.01  # |velocity| below this is classified "flat", not up/down.
SPIKE_VELOCITY_THRESHOLD = 0.5  # |velocity| at/above this sets spike_flag=True.
MIN_SAMPLE_COUNT = 3  # Below this, a window is statistically too thin to claim a trend.
CONFIDENT_SAMPLE_COUNT = 10  # Sample count at/above which confidence saturates at 1.0.

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s\-.]?){7,}\d")


class TrendDetectionError(RuntimeError):
    """Base class for Node 10 failures. Fail-closed: never partially writes."""


class ValidationError(TrendDetectionError):
    """Raised when required fields are missing, malformed, insufficient, or contain prohibited PII."""


class UnknownTargetError(TrendDetectionError):
    """Raised when the referenced target_id is not registered/described/segmented/defined/
    signaled/questioned/observed/compared/discussed upstream."""


class ConflictError(TrendDetectionError):
    """Raised when a trend_id already exists with different field values."""


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


def _parse_iso8601(name: str, value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be an ISO 8601 string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO 8601 date format for {name}: {value!r}") from exc


def _validate_window(value: Any) -> tuple[datetime, datetime, datetime, datetime]:
    if not isinstance(value, dict):
        raise ValidationError(f"window must be an object, got: {type(value).__name__}")
    required_keys = ("baseline_start", "baseline_end", "current_start", "current_end")
    for key in required_keys:
        if key not in value:
            raise ValidationError(f"window.{key} is required")
    baseline_start = _parse_iso8601("window.baseline_start", value["baseline_start"])
    baseline_end = _parse_iso8601("window.baseline_end", value["baseline_end"])
    current_start = _parse_iso8601("window.current_start", value["current_start"])
    current_end = _parse_iso8601("window.current_end", value["current_end"])
    if not (baseline_start < baseline_end <= current_start < current_end):
        raise ValidationError(
            "window must satisfy baseline_start < baseline_end <= current_start < current_end "
            f"(non-monotonic or overlapping window), got: {value!r}"
        )
    return baseline_start, baseline_end, current_start, current_end


def _validate_non_negative_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be numeric, got: {value!r}")
    if value < 0:
        raise ValidationError(f"{name} must be non-negative, got: {value!r}")
    return float(value)


def _validate_positive_sample_count(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer, got: {value!r}")
    if value < MIN_SAMPLE_COUNT:
        raise ValidationError(
            f"{name} must be at least {MIN_SAMPLE_COUNT} (insufficient samples to claim a trend), got: {value!r}"
        )
    return value


def _compute_trend(baseline_value: float, current_value: float, baseline_samples: int, current_samples: int) -> dict[str, Any]:
    if baseline_value <= 0:
        raise ValidationError(
            "baseline_value must be greater than zero to compute a velocity "
            f"(undefined trend basis), got: {baseline_value!r}"
        )
    velocity = (current_value - baseline_value) / baseline_value
    if abs(velocity) < FLAT_VELOCITY_DEADBAND:
        direction = "flat"
    elif velocity > 0:
        direction = "up"
    else:
        direction = "down"
    spike_flag = abs(velocity) >= SPIKE_VELOCITY_THRESHOLD
    confidence = round(min(1.0, min(baseline_samples, current_samples) / CONFIDENT_SAMPLE_COUNT), 4)
    return {
        "velocity": round(velocity, 6),
        "direction": direction,
        "spike_flag": spike_flag,
        "confidence": confidence,
    }


def validate_fields(
    *,
    trend_id: str,
    target_id: str,
    topic: str,
    geography: dict[str, Any],
    window: dict[str, Any],
    metric_name: str,
    baseline_value: Any,
    baseline_sample_count: Any,
    current_value: Any,
    current_sample_count: Any,
    source_type: str,
    evidence: str,
    metadata: dict[str, Any] | None,
) -> None:
    _validate_non_empty_string("trend_id", trend_id)
    _validate_non_empty_string("target_id", target_id)
    _validate_non_empty_string("topic", topic, check_pii=True)
    _validate_geography(geography)
    _validate_window(window)
    _validate_non_empty_string("metric_name", metric_name, check_pii=True)
    _validate_non_negative_number("baseline_value", baseline_value)
    _validate_positive_sample_count("baseline_sample_count", baseline_sample_count)
    _validate_non_negative_number("current_value", current_value)
    _validate_positive_sample_count("current_sample_count", current_sample_count)
    if not isinstance(source_type, str) or source_type not in ALLOWED_SOURCE_TYPES:
        raise ValidationError(
            f"source_type must be one of {sorted(ALLOWED_SOURCE_TYPES)} (offline MVP boundary), got: {source_type!r}"
        )
    _validate_non_empty_string("evidence", evidence)
    if metadata is not None and not isinstance(metadata, dict):
        raise ValidationError(f"metadata must be an object or None, got: {type(metadata).__name__}")


@dataclass(frozen=True)
class TrendSignalRecord:
    trend_id: str
    target_id: str
    topic: str
    geography: dict[str, str]
    window: dict[str, str]
    metric_name: str
    baseline_value: float
    baseline_sample_count: int
    current_value: float
    current_sample_count: int
    velocity: float
    direction: str
    spike_flag: bool
    confidence: float
    source_type: str
    evidence: str
    metadata: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TrendSignalRegistry:
    """Local, JSON-file-backed, fixture-only Node 10 registry. No network I/O, no live monitoring.

    Requires the referenced target_id to exist in all nine upstream registries: Node 01
    (TargetRegistry), Node 02 (ProductIntelligenceRegistry), Node 03 (AudienceSegmentRegistry,
    via list_for_target), Node 04 (ConversionDefinitionRegistry), Node 05 (DemandSignalRegistry,
    via list_for_target), Node 06 (QuestionRegistry, via list_for_target), Node 07
    (SocialVideoSignalRegistry, via list_for_target), Node 08 (CompetitorSignalRegistry, via
    list_for_target), Node 09 (CommunitySignalRegistry, via list_for_target) -- exact lineage
    per the allocation.

    velocity/direction/spike_flag/confidence are computed deterministically from
    baseline_value/current_value/baseline_sample_count/current_sample_count -- they are not
    caller-supplied inputs.
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
        competitor_registry: CompetitorSignalRegistry,
        community_registry: CommunitySignalRegistry,
    ):
        self.storage_path = Path(storage_path)
        self.target_registry = target_registry
        self.product_registry = product_registry
        self.audience_registry = audience_registry
        self.conversion_registry = conversion_registry
        self.demand_signal_registry = demand_signal_registry
        self.question_registry = question_registry
        self.social_video_registry = social_video_registry
        self.competitor_registry = competitor_registry
        self.community_registry = community_registry
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
        trend_id: str | None = None,
        target_id: str | None = None,
        topic: str | None = None,
        geography: dict[str, str] | None = None,
        window: dict[str, str] | None = None,
        metric_name: str | None = None,
        baseline_value: Any = None,
        baseline_sample_count: Any = None,
        current_value: Any = None,
        current_sample_count: Any = None,
        source_type: str | None = None,
        evidence: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TrendSignalRecord:
        validate_fields(
            trend_id=trend_id, target_id=target_id, topic=topic, geography=geography, window=window,
            metric_name=metric_name, baseline_value=baseline_value, baseline_sample_count=baseline_sample_count,
            current_value=current_value, current_sample_count=current_sample_count, source_type=source_type,
            evidence=evidence, metadata=metadata,
        )

        # Node01-09->10 nine-way contract/integration checks, fail-closed.
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
        if not self.competitor_registry.list_for_target(target_id):
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 08 competitor signal")
        if not self.community_registry.list_for_target(target_id):
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 09 community signal")

        baseline_value_f = _validate_non_negative_number("baseline_value", baseline_value)
        current_value_f = _validate_non_negative_number("current_value", current_value)
        trend = _compute_trend(baseline_value_f, current_value_f, baseline_sample_count, current_sample_count)

        candidate = TrendSignalRecord(
            trend_id=trend_id, target_id=target_id, topic=topic, geography=dict(geography), window=dict(window),
            metric_name=metric_name, baseline_value=baseline_value_f, baseline_sample_count=baseline_sample_count,
            current_value=current_value_f, current_sample_count=current_sample_count,
            velocity=trend["velocity"], direction=trend["direction"], spike_flag=trend["spike_flag"],
            confidence=trend["confidence"], source_type=source_type, evidence=evidence,
            metadata=dict(metadata) if metadata else {},
        )

        data = self._load()
        existing = data.get(trend_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "recorded_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "recorded_at"}
            if comparable_existing == comparable_candidate:
                return TrendSignalRecord(**existing)  # idempotent
            raise ConflictError(
                f"trend_id {trend_id!r} already registered with different field values; "
                "conflicting duplicate registrations are rejected fail-closed"
            )

        data[trend_id] = candidate.to_dict()
        self._save(data)
        return candidate

    def register_from_live_aggregation(
        self,
        *,
        trend_id: str,
        target_id: str,
        topic: str,
        geography: dict[str, str],
        window: dict[str, str],
        metric_name: str = "combined_demand_signal_count",
        evidence: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TrendSignalRecord:
        """Automated ingestion path: counts real Node05-09 signals for target_id whose
        observed_at falls inside each half of `window`, using those counts as
        baseline_value/current_value and their own sample counts -- not caller-supplied
        numbers. Writes through the same validated register() contract, so velocity/direction/
        spike_flag/confidence are still computed by _compute_trend() from real data, and the
        existing minimum-sample-count fail-closed check still applies (too few real signals in
        a window is rejected, exactly as it would be for a manually-entered trend).
        """
        baseline_start, baseline_end, current_start, current_end = _validate_window(window)

        upstream_registries = (
            self.demand_signal_registry, self.question_registry, self.social_video_registry,
            self.competitor_registry, self.community_registry,
        )
        all_records: list[Any] = []
        for upstream in upstream_registries:
            all_records.extend(upstream.list_for_target(target_id))

        def _count_in_window(start: datetime, end: datetime) -> int:
            count = 0
            for record in all_records:
                observed = _parse_iso8601("observed_at", record.observed_at)
                if start <= observed < end:
                    count += 1
            return count

        baseline_count = _count_in_window(baseline_start, baseline_end)
        current_count = _count_in_window(current_start, current_end)

        live_metadata = dict(metadata) if metadata else {}
        live_metadata["aggregation_receipt"] = {
            "computed_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "upstream_node_count": len(upstream_registries),
            "total_records_scanned": len(all_records),
            "baseline_records_counted": baseline_count,
            "current_records_counted": current_count,
        }

        return self.register(
            trend_id=trend_id, target_id=target_id, topic=topic, geography=geography, window=window,
            metric_name=metric_name, baseline_value=float(baseline_count), baseline_sample_count=baseline_count,
            current_value=float(current_count), current_sample_count=current_count,
            source_type="auto_aggregated",
            evidence=evidence or (
                f"Automatically aggregated from {len(all_records)} real Node05-09 signals for "
                f"{target_id!r}: {baseline_count} counted in the baseline window, {current_count} "
                "counted in the current window. See metadata.aggregation_receipt for detail."
            ),
            metadata=live_metadata,
        )

    def get(self, trend_id: str) -> TrendSignalRecord | None:
        data = self._load()
        record = data.get(trend_id)
        return TrendSignalRecord(**record) if record is not None else None

    def list(self) -> list[TrendSignalRecord]:
        return [TrendSignalRecord(**record) for record in self._load().values()]

    def list_for_target(self, target_id: str) -> list[TrendSignalRecord]:
        return [record for record in self.list() if record.target_id == target_id]
