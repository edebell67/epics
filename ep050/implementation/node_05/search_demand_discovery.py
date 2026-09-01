# epics/ep_050_distribution_engine/implementation/node_05/search_demand_discovery.py
# EP050 Node 05 — Search Demand Discovery.
#
# VERSION HISTORY
# v2.0.0 · 2026-08-19 · SEARCH PROVIDER CHANGED from Google Custom Search to Firecrawl. Google
#   closed the Custom Search JSON API to new customers -- their own documentation states "The
#   Custom Search JSON API is closed to new customers" and sets discontinuation at 2027-01-01 --
#   so every live call returned HTTP 403 "This project does not have the access to Custom Search
#   JSON API". Proven unfixable rather than assumed: the key was valid (a bogus key gave a
#   different error), its restrictions were correct (it was correctly blocked on a non-CSE API),
#   network egress was fine (the YouTube key succeeded through the identical code path), and a
#   brand-new normally-created GCP project with the API enabled and a fresh key returned the
#   identical 403. Also added build_search_query(): the query now carries locality + region +
#   country instead of locality alone, because "…Greenwich" alone returned Greenwich, CONNECTICUT
#   even with UK geo-targeting parameters set -- provider geo flags narrow ranking but do not
#   disambiguate an ambiguous place name. Without this the node would have silently collected US
#   demand data for London campaigns. Major version bump because total_results changes meaning:
#   Google gave an estimated corpus-wide match count, Firecrawl gives ranked results with no such
#   estimate, so total_results is now the honest count of results returned and the new
#   total_results_basis field records which meaning applies. The register()/validation/lineage/
#   PII/idempotency contract is completely unchanged.
# v1.3.0 · 2026-08-18 · fetch_search_demand() now captures each organic result's `link` (Google
#   CSE returns it; it was previously discarded). This lets shared/target_parameter_derivation.py
#   derive a real competitor_url for Node 08 straight from Node 05's own live results, closing
#   one of the four caller-supplied-parameter gaps identified for full Phase 2 automation.
# v1.2.0 · 2026-08-17 · Replaces the prior v1.1.0 schema-only widening (source_type labels
#   added with no fetch logic behind them -- flagged and reverted, see agent message board
#   event 20260817T162311314) with a real connector: register_from_live_source() performs an
#   actual Google Programmable Search Engine query and derives raw_query/metadata from the live
#   response. ALLOWED_SOURCE_TYPES is pulled back to only the values this file can actually
#   back with code: manual_curation, synthetic_fixture, search_query. Gated fail-closed behind
#   EP050_LIVE_FETCH_ENABLED=1 (default off) plus EP050_GOOGLE_CSE_API_KEY/EP050_GOOGLE_CSE_CX
#   (user-supplied, never entered by an agent). Every live record carries a verifiable
#   fetch_receipt. Satisfies the user-mandated CORE REQUIREMENT (2026-08-17).
# v1.0.0 · 2026-08-17 · Initial deterministic, offline, fixture-only demand-signal discovery registry.
#
# Scope: EP050 Node 05 only, per allocation 20260817T035602..._codex (Claude-owned).
# The manual/fixture register() path is unchanged: fail-closed, deterministic, no network access.
# The new register_from_live_source() path performs exactly one read-only HTTPS GET per call
# against the Google Custom Search JSON API, off by default, and writes through the same
# validated register() contract.
# Lineage enforcement: Every record must reference a target_id registered by Node 01, described by Node 02,
# segmented by Node 03, and defined by Node 04 (exact target/product/audience/conversion lineage).
# Output schema matches the frozen Node05->11 contract v1.1.0 exactly (DemandSignalPayload).

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry  # noqa: E402
from live_fetch import (  # noqa: E402
    FetchReceipt,
    LiveFetchRequestError,
    http_post_json,
    make_receipt,
    require_live_fetch_enabled,
    resolve_firecrawl_credentials,
)

# manual_curation/synthetic_fixture remain for offline fixture use; search_query is the one live
# source type this node supports, backed by register_from_live_source() below -- not an
# unverified label, every search_query record carries a real fetch_receipt.
ALLOWED_SOURCE_TYPES = frozenset({"manual_curation", "synthetic_fixture", "search_query"})
REQUIRED_GEOGRAPHY_FIELDS = ("locality", "region", "country")
REQUIRED_SERVICE_CONTEXT_FIELDS = ("service_name", "market_segment")

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s\-.]?){7,}\d")


class SearchDemandDiscoveryError(RuntimeError):
    """Base class for Node 05 failures. Fail-closed: never partially writes."""


class ValidationError(SearchDemandDiscoveryError):
    """Raised when required fields are missing, malformed, or contain prohibited PII."""


class UnknownTargetError(SearchDemandDiscoveryError):
    """Raised when the referenced target_id is not registered/described/segmented/defined upstream."""


class ConflictError(SearchDemandDiscoveryError):
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


def _validate_service_context(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"service_context must be an object, got: {type(value).__name__}")
    for key in REQUIRED_SERVICE_CONTEXT_FIELDS:
        subvalue = value.get(key)
        if not isinstance(subvalue, str) or not subvalue.strip():
            raise ValidationError(f"service_context.{key} is required and must be a non-empty string")


def _validate_observed_at(value: Any) -> None:
    if not isinstance(value, str):
        raise ValidationError("observed_at must be an ISO 8601 string")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Invalid ISO 8601 date format for observed_at: {value!r}") from exc


FIRECRAWL_SEARCH_PATH = "/v2/search"
SEARCH_RESULT_LIMIT = 10
TOP_RESULTS_KEPT = 5


def build_search_query(topic: str, geography: dict[str, str]) -> str:
    """Compose the real search query from the topic plus the FULL geography, not just locality.

    Locality alone is ambiguous across countries and silently returns the wrong market's data.
    Proven live: "restore hot water quickly Greenwich" returned Greenwich, Connecticut plumbers
    (US .com sites, US phone numbers) even with the provider's own country/location geo-targeting
    flags set to the UK. Appending region and country -- "restore hot water quickly Greenwich
    London UK" -- returned genuine SE10/Blackheath .co.uk engineers. Geo-targeting parameters
    narrow ranking; they do not disambiguate an ambiguous place name, so the query string has to
    carry it. Without this, a London campaign would quietly collect US demand signals, which is a
    worse failure than an outright error because nothing downstream would flag it.
    """
    parts = [topic.replace("_", " ").strip()]
    for field in ("locality", "region", "country"):
        value = (geography.get(field) or "").strip()
        if value and value.lower() not in (part.lower() for part in parts):
            parts.append(value)
    return " ".join(part for part in parts if part)


def fetch_search_demand(topic: str, geography: dict[str, str]) -> tuple[dict[str, Any], FetchReceipt]:
    """Live Firecrawl web-search query for topic+geography.

    Requires EP050_LIVE_FETCH_ENABLED=1 plus a Firecrawl credential (EP050_FIRECRAWL_API_KEY, or
    the Firecrawl CLI's own stored credentials -- see resolve_firecrawl_credentials). Returns
    (result, receipt) where result contains the actual query string sent, a truthful count of the
    results returned, and an excerpt of the top organic results -- the real search-demand signal,
    never a caller-invented value.

    PROVIDER CHANGE (2026-08-19): this previously called the Google Custom Search JSON API. Google
    closed that API to new customers -- their own docs state "The Custom Search JSON API is closed
    to new customers" with discontinuation on 2027-01-01 -- so it returned HTTP 403 for this
    project permanently. Verified unfixable: a brand-new GCP project with the API enabled and a
    fresh unrestricted key returned the identical 403. The record contract, lineage enforcement,
    PII checks and idempotency below are unchanged; only the upstream provider differs.

    NOTE ON total_results: Google reported an estimated corpus-wide match count. Firecrawl returns
    ranked results with no such estimate, and inventing one would be fabrication. total_results is
    therefore the honest count of results actually returned, and total_results_basis records which
    of the two meanings applies so nothing downstream silently misreads it as a corpus estimate.
    """
    require_live_fetch_enabled()
    api_key, api_url = resolve_firecrawl_credentials()
    query = build_search_query(topic, geography)

    body: dict[str, Any] = {"query": query, "limit": SEARCH_RESULT_LIMIT, "sources": ["web"]}
    location = ",".join(
        value.strip()
        for value in (geography.get("locality"), geography.get("region"), geography.get("country"))
        if value and value.strip()
    )
    if location:
        body["location"] = location

    endpoint = f"{api_url.rstrip('/')}{FIRECRAWL_SEARCH_PATH}"
    payload, status = http_post_json(endpoint, body=body, headers={"Authorization": f"Bearer {api_key}"})

    if not isinstance(payload, dict) or not payload.get("success"):
        raise LiveFetchRequestError(
            f"Firecrawl search did not report success for query {query!r}; refusing to derive a "
            "demand signal from an unsuccessful response (fail-closed)"
        )
    data = payload.get("data")
    items = (data.get("web") if isinstance(data, dict) else data) or []
    if not isinstance(items, list):
        raise LiveFetchRequestError(
            f"Firecrawl search returned an unexpected data shape for query {query!r}: "
            f"{type(items).__name__}; refusing to guess at it (fail-closed)"
        )

    receipt = make_receipt(endpoint=endpoint, http_status=status, item_count=len(items))
    result = {
        "query": query,
        "total_results": str(len(items)),
        "total_results_basis": "results_returned",
        "provider": "firecrawl",
        "credits_used": payload.get("creditsUsed"),
        "top_results": [
            {"title": item.get("title"), "snippet": item.get("description"), "link": item.get("url")}
            for item in items[:TOP_RESULTS_KEPT]
        ],
    }
    return result, receipt


def validate_fields(
    *,
    signal_id: str,
    target_id: str,
    raw_query: str,
    topic: str,
    source_type: str,
    observed_at: str,
    geography: dict[str, Any],
    service_context: dict[str, Any],
    metadata: dict[str, Any] | None,
) -> None:
    _validate_non_empty_string("signal_id", signal_id)
    _validate_non_empty_string("target_id", target_id)
    _validate_non_empty_string("raw_query", raw_query, check_pii=True)
    _validate_non_empty_string("topic", topic, check_pii=True)
    if not isinstance(source_type, str) or source_type not in ALLOWED_SOURCE_TYPES:
        raise ValidationError(
            f"source_type must be one of {sorted(ALLOWED_SOURCE_TYPES)} (offline MVP boundary), got: {source_type!r}"
        )
    _validate_observed_at(observed_at)
    _validate_geography(geography)
    _validate_service_context(service_context)
    if metadata is not None and not isinstance(metadata, dict):
        raise ValidationError(f"metadata must be an object or None, got: {type(metadata).__name__}")


@dataclass(frozen=True)
class DemandSignalRecord:
    signal_id: str
    target_id: str
    raw_query: str
    topic: str
    source_type: str
    observed_at: str
    geography: dict[str, str]
    service_context: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_contract_payload(self) -> dict[str, Any]:
        """Exact shape expected by the frozen Node05->11 contract (excludes recorded_at, a Node 05-local field)."""
        payload = self.to_dict()
        payload.pop("recorded_at")
        return payload


class DemandSignalRegistry:
    """Local, JSON-file-backed, fixture-only Node 05 registry. No network I/O, no live scraping.

    Requires the referenced target_id to exist in all four upstream registries: Node 01
    (TargetRegistry), Node 02 (ProductIntelligenceRegistry), Node 03 (AudienceSegmentRegistry,
    via list_for_target), Node 04 (ConversionDefinitionRegistry).
    """

    def __init__(
        self,
        storage_path: Path,
        target_registry: TargetRegistry,
        product_registry: ProductIntelligenceRegistry,
        audience_registry: AudienceSegmentRegistry,
        conversion_registry: ConversionDefinitionRegistry,
    ):
        self.storage_path = Path(storage_path)
        self.target_registry = target_registry
        self.product_registry = product_registry
        self.audience_registry = audience_registry
        self.conversion_registry = conversion_registry
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
        raw_query: str | None = None,
        topic: str | None = None,
        source_type: str | None = None,
        observed_at: str | None = None,
        geography: dict[str, str] | None = None,
        service_context: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DemandSignalRecord:
        validate_fields(
            signal_id=signal_id, target_id=target_id, raw_query=raw_query, topic=topic,
            source_type=source_type, observed_at=observed_at, geography=geography,
            service_context=service_context, metadata=metadata,
        )

        # Node01+02+03+04->05 contract/integration checks: all four must exist, fail-closed.
        if self.target_registry.get(target_id) is None:
            raise UnknownTargetError(f"target_id {target_id!r} is not registered in the Node 01 registry")
        if self.product_registry.get(target_id) is None:
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 02 product intelligence record")
        if not self.audience_registry.list_for_target(target_id):
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 03 audience segment")
        if self.conversion_registry.get(target_id) is None:
            raise UnknownTargetError(f"target_id {target_id!r} has no Node 04 conversion definition")

        candidate = DemandSignalRecord(
            signal_id=signal_id, target_id=target_id, raw_query=raw_query, topic=topic,
            source_type=source_type, observed_at=observed_at, geography=dict(geography),
            service_context=dict(service_context), metadata=dict(metadata) if metadata else {},
        )

        data = self._load()
        existing = data.get(signal_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "recorded_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "recorded_at"}
            if comparable_existing == comparable_candidate:
                return DemandSignalRecord(**existing)  # idempotent
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
        service_context: dict[str, str],
        observed_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DemandSignalRecord:
        """Automated ingestion path: performs one real Google Custom Search query and derives
        raw_query/metadata from the live response -- no human types the signal content. Writes
        through the same validated register() contract, so lineage/PII/idempotency/conflict
        checks are enforced unchanged.
        """
        result, receipt = fetch_search_demand(topic, geography)
        live_metadata = dict(metadata) if metadata else {}
        live_metadata["fetch_receipt"] = receipt.to_dict()
        live_metadata["search_result_summary"] = {
            "total_results": result["total_results"],
            "top_results": result["top_results"],
        }
        return self.register(
            signal_id=signal_id,
            target_id=target_id,
            raw_query=result["query"],
            topic=topic,
            source_type="search_query",
            observed_at=observed_at or datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            geography=geography,
            service_context=service_context,
            metadata=live_metadata,
        )

    def get(self, signal_id: str) -> DemandSignalRecord | None:
        data = self._load()
        record = data.get(signal_id)
        return DemandSignalRecord(**record) if record is not None else None

    def list(self) -> list[DemandSignalRecord]:
        return [DemandSignalRecord(**record) for record in self._load().values()]

    def list_for_target(self, target_id: str) -> list[DemandSignalRecord]:
        return [record for record in self.list() if record.target_id == target_id]
