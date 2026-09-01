# epics/ep_050_distribution_engine/implementation/node_09/community_intelligence.py
# EP050 Node 09 — Community Intelligence.
#
# VERSION HISTORY
# v1.3.0 · 2026-08-19 · Adds a second live path, register_from_firecrawl_search(), because the
#   existing OAuth path (community_api) has never once run for real: EP050_REDDIT_CLIENT_ID/
#   SECRET were never set. User recalled successfully querying Reddit communities before via a
#   different mechanism; the no-auth public JSON path that mechanism likely used
#   (skills/distribution_engine/platforms/reddit/skills/reddit_evidence_mining_public.py) was
#   tested live 2026-08-19 and now returns a genuine HTTP 403 (Reddit's own anti-bot policy, not
#   fixable here). Firecrawl (already authenticated for this project) searching
#   `site:reddit.com {topic}` works today, verified live against real UK trades queries, and needs
#   no Reddit app registration at all. New source_type "community_search" distinguishes this from
#   the dormant OAuth path. Both remain strictly read-only.
# v1.2.0 · 2026-08-18 · Adds discover_subreddit(topic) -- live Reddit subreddit-search lookup
#   (ranked by subscriber count) that derives a real `subreddit` instead of a human supplying
#   one. Factored the OAuth client_credentials exchange out of fetch_community_signal() into
#   shared helper _fetch_reddit_access_token() so both live calls reuse one token flow. Closes
#   the last of the four caller-supplied-parameter gaps for Phase 2 automation (geography,
#   topic, competitor_url via shared/target_parameter_derivation.py; subreddit here).
# v1.1.0 · 2026-08-17 · Adds automated live ingestion: register_from_live_source() performs a
#   real, read-only Reddit search (official OAuth API, client_credentials grant) within a
#   caller-supplied subreddit and derives question/pain_point/observed_metrics from the live
#   response -- no human types signal content. Gated fail-closed behind
#   EP050_LIVE_FETCH_ENABLED=1 (default off) plus EP050_REDDIT_CLIENT_ID/
#   EP050_REDDIT_CLIENT_SECRET (a user-registered "script" app, never entered by an agent).
#   Search/read only -- posting, voting, commenting, and any account interaction remain
#   permanently absent from this module's capability, unchanged from v1.0.0. Every live record
#   carries a verifiable fetch_receipt. Satisfies the user-mandated CORE REQUIREMENT
#   (2026-08-17) that Nodes 05-10 be genuinely automated.
# v1.0.0 · 2026-08-17 · Initial deterministic, offline, fixture-only community intelligence registry.
#
# Scope: EP050 Node 09 only, per allocation 20260817T060634552_codex_dab2cc0c.
# The manual/fixture register() path is unchanged: fail-closed, deterministic, no network access.
# Intelligence-only per the master spec: "not automated spam" -- this module has no posting
# or outreach capability of any kind, live or offline, only read/search and normalization.
# Every record must reference a target_id registered by Node 01, described by Node 02,
# segmented by Node 03, defined by Node 04, with a demand signal from Node 05, a question
# from Node 06, a social/video signal from Node 07, and a competitor signal from Node 08
# (eight-way exact lineage per the allocation).

from __future__ import annotations

import base64
import json
import os
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_08"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
from registration import TargetRegistry  # noqa: E402
from product_intelligence import ProductIntelligenceRegistry  # noqa: E402
from audience_definition import AudienceSegmentRegistry  # noqa: E402
from conversion_definition import ConversionDefinitionRegistry  # noqa: E402
from search_demand_discovery import DemandSignalRegistry  # noqa: E402
from question_discovery import QuestionRegistry  # noqa: E402
from social_video_discovery import SocialVideoSignalRegistry  # noqa: E402
from competitor_intelligence import CompetitorSignalRegistry  # noqa: E402
from live_fetch import (  # noqa: E402
    FetchReceipt, LiveFetchRequestError, http_get_json, http_post_form, http_post_json, make_receipt,
    require_credential, require_live_fetch_enabled, resolve_firecrawl_credentials,
)

# manual_curation/synthetic_fixture remain for offline fixture use. community_api is the Reddit
# OAuth live path (register_from_live_source()) -- built and tested 2026-08-17, but has never had
# real credentials: EP050_REDDIT_CLIENT_ID/SECRET were never set. community_search is the Firecrawl
# path added 2026-08-19 (register_from_firecrawl_search()): a real, working alternative that needs
# no Reddit app registration at all, added after the user recalled successfully querying Reddit
# communities via a different mechanism and asked for it to be tied into the workflow properly.
# Both are strictly read-only -- there is no write/post/comment/vote path anywhere in this module.
ALLOWED_SOURCE_TYPES = frozenset({"manual_curation", "synthetic_fixture", "community_api", "community_search"})
REQUIRED_GEOGRAPHY_FIELDS = ("locality", "region", "country")

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s\-.]?){7,}\d")


class CommunityIntelligenceError(RuntimeError):
    """Base class for Node 09 failures. Fail-closed: never partially writes."""


class ValidationError(CommunityIntelligenceError):
    """Raised when required fields are missing, malformed, or contain prohibited PII."""


class UnknownTargetError(CommunityIntelligenceError):
    """Raised when the referenced target_id is not registered/described/segmented/defined/
    signaled/questioned/observed/compared upstream."""


class ConflictError(CommunityIntelligenceError):
    """Raised when a signal_id already exists with different field values."""


class NoLiveResultsError(CommunityIntelligenceError):
    """Raised when a live fetch succeeded but returned no thread to register."""


REDDIT_CLIENT_ID_ENV = "EP050_REDDIT_CLIENT_ID"
REDDIT_CLIENT_SECRET_ENV = "EP050_REDDIT_CLIENT_SECRET"
REDDIT_USER_AGENT_ENV = "EP050_REDDIT_USER_AGENT"
REDDIT_TOKEN_ENDPOINT = "https://www.reddit.com/api/v1/access_token"
REDDIT_OAUTH_BASE = "https://oauth.reddit.com"
_DEFAULT_USER_AGENT = "EP050-DistributionEngine/1.0 (automated demand-intelligence read-only fetch)"
_INTENT_KEYWORDS = {
    "how": "troubleshooting", "why": "diagnostic_inquiry", "fix": "seeking_repair",
    "anyone else": "seeking_validation", "recommend": "seeking_recommendation", "help": "seeking_help",
}


def _derive_intent_cues(text: str) -> list[str]:
    lowered = text.lower()
    cues = sorted({label for keyword, label in _INTENT_KEYWORDS.items() if keyword in lowered})
    return cues or ["general_discussion"]


def _fetch_reddit_access_token() -> tuple[str, str]:
    """Shared OAuth client_credentials exchange used by both fetch_community_signal() and
    discover_subreddit(). Read-only scope; no posting/voting/commenting capability anywhere."""
    client_id = require_credential(REDDIT_CLIENT_ID_ENV)
    client_secret = require_credential(REDDIT_CLIENT_SECRET_ENV)
    user_agent = os.environ.get(REDDIT_USER_AGENT_ENV) or _DEFAULT_USER_AGENT

    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    token_payload, _ = http_post_form(
        REDDIT_TOKEN_ENDPOINT,
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {basic_auth}", "User-Agent": user_agent},
    )
    access_token = token_payload.get("access_token")
    if not access_token:
        raise LiveFetchRequestError("Reddit token endpoint did not return an access_token")
    return access_token, user_agent


def discover_subreddit(topic: str) -> tuple[str, FetchReceipt]:
    """Live discovery of the most relevant subreddit for a topic via Reddit's subreddit-search
    endpoint, ranked by subscriber count. Closes the last of the four caller-supplied-parameter
    gaps for Phase 2 automation: fetch_community_signal() needs a `subreddit`, and this derives
    one from a real Reddit query instead of a human picking it.

    Requires EP050_LIVE_FETCH_ENABLED=1, EP050_REDDIT_CLIENT_ID and EP050_REDDIT_CLIENT_SECRET.
    Read-only: uses the same client_credentials grant as fetch_community_signal(), no elevated
    scope. Raises NoLiveResultsError if no subreddit matches the query.
    """
    require_live_fetch_enabled()
    access_token, user_agent = _fetch_reddit_access_token()
    query = topic.replace("_", " ").strip()
    params = urllib.parse.urlencode({"q": query, "limit": 5})
    url = f"{REDDIT_OAUTH_BASE}/subreddits/search?{params}"
    payload, status = http_get_json(url, headers={"Authorization": f"Bearer {access_token}", "User-Agent": user_agent})
    children = (payload.get("data") or {}).get("children") or []
    if not children:
        raise NoLiveResultsError(f"Reddit subreddit search returned no matches for topic {topic!r}")
    ranked = sorted(children, key=lambda c: int((c.get("data") or {}).get("subscribers") or 0), reverse=True)
    top = ranked[0].get("data", {})
    display_name = top.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        raise LiveFetchRequestError("Reddit subreddit search result missing display_name")
    receipt = make_receipt(endpoint=url.split("?")[0], http_status=status, item_count=len(children))
    return display_name, receipt


def fetch_community_signal(topic: str, subreddit: str) -> tuple[dict[str, Any], FetchReceipt]:
    """Live, read-only Reddit search within a single subreddit via the official OAuth API.

    Requires EP050_LIVE_FETCH_ENABLED=1, EP050_REDDIT_CLIENT_ID and EP050_REDDIT_CLIENT_SECRET
    (a user-registered Reddit "script" app; credentials are always user-supplied, never
    entered by an agent). Strictly read-only: search only. No posting, voting, commenting, or
    account interaction of any kind is implemented anywhere in this module.
    """
    require_live_fetch_enabled()
    access_token, user_agent = _fetch_reddit_access_token()

    query = topic.replace("_", " ").strip()
    search_params = urllib.parse.urlencode({"q": query, "restrict_sr": "1", "sort": "relevance", "limit": 5})
    search_url = f"{REDDIT_OAUTH_BASE}/r/{subreddit}/search?{search_params}"
    search_payload, status = http_get_json(
        search_url, headers={"Authorization": f"Bearer {access_token}", "User-Agent": user_agent}
    )
    children = (search_payload.get("data") or {}).get("children") or []
    if not children:
        raise NoLiveResultsError(f"Reddit search returned no threads for topic {topic!r} in r/{subreddit}")
    top = children[0].get("data", {})
    receipt = make_receipt(endpoint=search_url.split("?")[0], http_status=status, item_count=len(children))
    result = {
        "title": top.get("title", "") or "",
        "selftext": top.get("selftext", "") or "",
        "permalink": top.get("permalink", "") or "",
        "score": int(top.get("score", 0) or 0),
        "num_comments": int(top.get("num_comments", 0) or 0),
    }
    return result, receipt


FIRECRAWL_SEARCH_PATH = "/v2/search"
FIRECRAWL_RESULT_LIMIT = 10


def _subreddit_from_url(url: str) -> str | None:
    """Extract 'r/SubredditName' from a real reddit.com thread URL. Returns None if the URL
    isn't a recognisable Reddit thread link -- never guesses a subreddit that isn't really there."""
    match = re.search(r"reddit\.com/r/([A-Za-z0-9_]+)/", url or "")
    return f"r/{match.group(1)}" if match else None


def fetch_community_signal_via_firecrawl(
    topic: str, geography: dict[str, str] | None = None
) -> tuple[dict[str, Any], FetchReceipt]:
    """Live, read-only discovery of real Reddit discussion via Firecrawl web search restricted to
    reddit.com, instead of Reddit's own API. Built 2026-08-19 because Reddit's OAuth path
    (fetch_community_signal(), community_api source_type) has real code but has NEVER had
    credentials configured -- EP050_REDDIT_CLIENT_ID/SECRET were never set, so it has never once
    run for real. Reddit's public no-auth JSON endpoints (the mechanism the user recalled using
    successfully before) were also tested live 2026-08-19 and returned a genuine HTTP 403 --
    Reddit's own anti-bot restriction, not something fixable here.

    This path needs no Reddit app registration at all: it searches the open web (via Firecrawl,
    already authenticated for this project) for `site:reddit.com {topic}`, which surfaces real,
    public Reddit threads exactly as they'd appear in ordinary search results. Verified live
    2026-08-19 against real UK trades queries -- returned genuine threads like "Boiler broke and
    no heating for over 24h. What [are my rights]" (r/LegalAdviceUK) and "No heat and landlord
    doesn't care. What can I do?" -- real people, real language, real pain points.

    Requires EP050_LIVE_FETCH_ENABLED=1 plus a Firecrawl credential (see
    resolve_firecrawl_credentials). Read-only: only ever issues a search request, never posts,
    votes, comments, or interacts with any account -- same permanent capability boundary as the
    OAuth path.
    """
    require_live_fetch_enabled()
    api_key, api_url = resolve_firecrawl_credentials()
    # Full geography, not locality alone -- proven necessary live 2026-08-19: a query appending
    # only "Greenwich" returned an r/nyc thread as the top result (Greenwich is ambiguous across
    # countries, same real failure mode already found and fixed in Node 05's build_search_query).
    query_parts = [f"site:reddit.com {topic.replace('_', ' ').strip()}"]
    if geography:
        for field in ("locality", "region", "country"):
            value = (geography.get(field) or "").strip()
            if value and value.lower() not in " ".join(query_parts).lower():
                query_parts.append(value)
    query = " ".join(query_parts)

    endpoint = f"{api_url.rstrip('/')}{FIRECRAWL_SEARCH_PATH}"
    body: dict[str, Any] = {"query": query, "limit": FIRECRAWL_RESULT_LIMIT, "sources": ["web"]}
    payload, status = http_post_json(endpoint, body=body, headers={"Authorization": f"Bearer {api_key}"})

    if not isinstance(payload, dict) or not payload.get("success"):
        raise LiveFetchRequestError(
            f"Firecrawl search did not report success for query {query!r}; refusing to derive a "
            "community signal from an unsuccessful response (fail-closed)"
        )
    data = payload.get("data")
    items = (data.get("web") if isinstance(data, dict) else data) or []
    if not isinstance(items, list):
        raise LiveFetchRequestError(
            f"Firecrawl search returned an unexpected data shape for query {query!r}: "
            f"{type(items).__name__}; refusing to guess at it (fail-closed)"
        )
    if not items:
        raise NoLiveResultsError(f"Firecrawl search returned no Reddit threads for topic {topic!r}")

    top = items[0]
    receipt = make_receipt(endpoint=endpoint, http_status=status, item_count=len(items))
    result = {
        "title": top.get("title") or "",
        "snippet": top.get("description") or "",
        "url": top.get("url") or "",
        "query": query,
        "result_rank": top.get("position"),
        "matching_threads_returned": len(items),
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
    community_source: str,
    topic: str,
    question: str,
    pain_point: str,
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
    _validate_non_empty_string("community_source", community_source, check_pii=True)
    _validate_non_empty_string("topic", topic, check_pii=True)
    _validate_non_empty_string("question", question, check_pii=True)
    _validate_non_empty_string("pain_point", pain_point, check_pii=True)
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
class CommunitySignalRecord:
    signal_id: str
    target_id: str
    community_source: str
    topic: str
    question: str
    pain_point: str
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


class CommunitySignalRegistry:
    """Local, JSON-file-backed, fixture-only Node 09 registry. No network I/O, no live community access.

    Requires the referenced target_id to exist in all eight upstream registries: Node 01
    (TargetRegistry), Node 02 (ProductIntelligenceRegistry), Node 03 (AudienceSegmentRegistry,
    via list_for_target), Node 04 (ConversionDefinitionRegistry), Node 05 (DemandSignalRegistry,
    via list_for_target), Node 06 (QuestionRegistry, via list_for_target), Node 07
    (SocialVideoSignalRegistry, via list_for_target), Node 08 (CompetitorSignalRegistry, via
    list_for_target) -- exact lineage per the allocation.
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
        community_source: str | None = None,
        topic: str | None = None,
        question: str | None = None,
        pain_point: str | None = None,
        intent_cues: list[str] | None = None,
        geography: dict[str, str] | None = None,
        observed_metrics: dict[str, Any] | None = None,
        observed_at: str | None = None,
        source_type: str | None = None,
        evidence: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CommunitySignalRecord:
        validate_fields(
            signal_id=signal_id, target_id=target_id, community_source=community_source, topic=topic,
            question=question, pain_point=pain_point, intent_cues=intent_cues, geography=geography,
            observed_metrics=observed_metrics, observed_at=observed_at, source_type=source_type,
            evidence=evidence, metadata=metadata,
        )

        # Node01-08->09 eight-way contract/integration checks, fail-closed.
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

        candidate = CommunitySignalRecord(
            signal_id=signal_id, target_id=target_id, community_source=community_source, topic=topic,
            question=question, pain_point=pain_point, intent_cues=list(intent_cues), geography=dict(geography),
            observed_metrics=dict(observed_metrics), observed_at=observed_at, source_type=source_type,
            evidence=evidence, metadata=dict(metadata) if metadata else {},
        )

        data = self._load()
        existing = data.get(signal_id)
        if existing is not None:
            comparable_existing = {k: v for k, v in existing.items() if k != "recorded_at"}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k != "recorded_at"}
            if comparable_existing == comparable_candidate:
                return CommunitySignalRecord(**existing)  # idempotent
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
        subreddit: str,
        geography: dict[str, str],
        observed_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CommunitySignalRecord:
        """Automated ingestion path: performs one real, read-only Reddit search and derives
        question/pain_point/observed_metrics from the live thread -- no human types the signal
        content. Read-only: this method (and this module) has no posting/reply/vote capability.
        Writes through the same validated register() contract, so the PII screen, lineage, and
        idempotency/conflict checks all apply unchanged to live-fetched text as well.
        """
        result, receipt = fetch_community_signal(topic, subreddit)
        title = result["title"]
        intent_cues = _derive_intent_cues(f"{title} {result['selftext']}")
        pain_point = (result["selftext"].strip() or title)[:300]
        live_metadata = dict(metadata) if metadata else {}
        live_metadata["fetch_receipt"] = receipt.to_dict()
        live_metadata["permalink"] = (
            f"https://www.reddit.com{result['permalink']}" if result["permalink"] else None
        )
        return self.register(
            signal_id=signal_id,
            target_id=target_id,
            community_source=f"r/{subreddit}",
            topic=topic,
            question=title,
            pain_point=pain_point,
            intent_cues=intent_cues,
            geography=geography,
            observed_metrics={"score": result["score"], "num_comments": result["num_comments"]},
            observed_at=observed_at or datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            source_type="community_api",
            evidence=(
                f"Automated live read from r/{subreddit} via the Reddit OAuth API "
                f"(HTTP {receipt.http_status}, read-only -- no posting capability exists); "
                "see metadata.fetch_receipt for independent verification."
            ),
            metadata=live_metadata,
        )

    def register_from_firecrawl_search(
        self,
        *,
        signal_id: str,
        target_id: str,
        topic: str,
        geography: dict[str, str],
        observed_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CommunitySignalRecord:
        """Automated ingestion path using Firecrawl (see fetch_community_signal_via_firecrawl for
        why this exists alongside the never-credentialed Reddit OAuth path). Derives
        question/pain_point/observed_metrics/community_source from the live search result -- no
        human types the signal content. Writes through the same validated register() contract as
        every other path, so PII screening, lineage, and idempotency/conflict checks apply
        unchanged."""
        result, receipt = fetch_community_signal_via_firecrawl(topic, geography)
        title = result["title"]
        intent_cues = _derive_intent_cues(f"{title} {result['snippet']}")
        pain_point = (result["snippet"].strip() or title)[:300]
        community_source = _subreddit_from_url(result["url"]) or "reddit.com"
        live_metadata = dict(metadata) if metadata else {}
        live_metadata["fetch_receipt"] = receipt.to_dict()
        live_metadata["source_url"] = result["url"] or None
        live_metadata["search_query"] = result["query"]
        return self.register(
            signal_id=signal_id,
            target_id=target_id,
            community_source=community_source,
            topic=topic,
            question=title,
            pain_point=pain_point,
            intent_cues=intent_cues,
            geography=geography,
            observed_metrics={
                "result_rank": result["result_rank"] or 0,
                "matching_threads_returned": result["matching_threads_returned"],
            },
            observed_at=observed_at or datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            source_type="community_search",
            evidence=(
                f"Automated live read via Firecrawl web search restricted to site:reddit.com "
                f"(HTTP {receipt.http_status}, read-only -- no Reddit API/OAuth involved, no "
                "posting capability exists); see metadata.fetch_receipt for independent verification."
            ),
            metadata=live_metadata,
        )

    def get(self, signal_id: str) -> CommunitySignalRecord | None:
        data = self._load()
        record = data.get(signal_id)
        return CommunitySignalRecord(**record) if record is not None else None

    def list(self) -> list[CommunitySignalRecord]:
        return [CommunitySignalRecord(**record) for record in self._load().values()]

    def list_for_target(self, target_id: str) -> list[CommunitySignalRecord]:
        return [record for record in self.list() if record.target_id == target_id]
