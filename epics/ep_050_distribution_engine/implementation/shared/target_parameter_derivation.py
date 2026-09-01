# epics/ep_050_distribution_engine/implementation/shared/target_parameter_derivation.py
# EP050 shared — derives the caller-supplied parameters Phase 2's live fetch functions need
# (geography, topic, competitor_url) from data already captured in Phase 1 registration and
# Node 05's own live results, instead of a human typing them in per call.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-18 · Initial version. Closes three of the four parameter gaps identified for
#   full Phase 2 automation: geography (direct from Node 01), topic (from Node 03's needs/pains),
#   competitor_url (from Node 05's own live search results, once fetch_search_demand() started
#   capturing `link`, v1.3.0). The fourth gap, `subreddit`, requires a live external lookup and
#   lives in node_09/community_intelligence.py as discover_subreddit() instead, since it needs
#   Node 09's own Reddit OAuth flow and is not derivable offline from any registry data.
#
# Pure functions only: derive_geography/derive_topic_candidates/derive_primary_topic read
# already-registered Phase 1 records and do not touch the network. derive_competitor_url reads
# an already-fetched Node 05 result and does not touch the network either — it is the caller's
# responsibility to have obtained that result via a real fetch_search_demand() call.

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Mapping

REQUIRED_GEOGRAPHY_FIELDS = ("locality", "region", "country")


class DerivationError(ValueError):
    """Raised when a parameter cannot be safely derived from the supplied record(s)."""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return slug


def derive_geography(target_record: Mapping[str, Any]) -> dict[str, str]:
    """Geography for a target is already captured at registration (Node 01) — this is a
    validated passthrough, not a guess, so Node 05's fetch_search_demand() never needs a human
    to retype it."""
    if not isinstance(target_record, Mapping):
        raise DerivationError("target_record must be an object (Node 01 TargetRecord shape)")
    geography = target_record.get("geography")
    if not isinstance(geography, Mapping):
        raise DerivationError("target_record.geography must be an object (Node 01 shape)")
    result: dict[str, str] = {}
    for key in REQUIRED_GEOGRAPHY_FIELDS:
        value = geography.get(key)
        if not isinstance(value, str) or not value.strip():
            raise DerivationError(f"target_record.geography.{key} is required and must be a non-empty string")
        result[key] = value
    return result


def derive_topic_candidates(audience_record: Mapping[str, Any]) -> list[str]:
    """Topics are exactly what Node 03 already captured as real customer language: `needs` and
    `pains`. Slugified and deduped, in needs-then-pains order (active demand ranks above a
    problem statement)."""
    if not isinstance(audience_record, Mapping):
        raise DerivationError("audience_record must be an object (Node 03 AudienceSegmentRecord shape)")
    needs = audience_record.get("needs")
    pains = audience_record.get("pains")
    if not isinstance(needs, list) or not isinstance(pains, list):
        raise DerivationError("audience_record must contain 'needs' and 'pains' lists (Node 03 shape)")

    candidates: list[str] = []
    seen: set[str] = set()
    for phrase in (*needs, *pains):
        if not isinstance(phrase, str) or not phrase.strip():
            continue
        slug = _slugify(phrase)
        if slug and slug not in seen:
            seen.add(slug)
            candidates.append(slug)

    if not candidates:
        raise DerivationError("No topic candidates could be derived from empty/blank needs and pains")
    return candidates


def derive_primary_topic(audience_record: Mapping[str, Any]) -> str:
    """The single highest-priority topic — first of derive_topic_candidates(), deterministic."""
    return derive_topic_candidates(audience_record)[0]


def derive_competitor_url(
    search_demand_result: Mapping[str, Any], *, exclude_domains: list[str] | None = None
) -> str:
    """Derives Node 08's `competitor_url` from Node 05's own live search results (the `link`
    field fetch_search_demand() started capturing in v1.3.0) instead of a human supplying it.
    Returns the first result whose domain isn't in exclude_domains (e.g. the target's own
    domain, so a business is never flagged as its own competitor)."""
    if not isinstance(search_demand_result, Mapping):
        raise DerivationError("search_demand_result must be an object (fetch_search_demand() result shape)")
    top_results = search_demand_result.get("top_results")
    if not isinstance(top_results, list) or not top_results:
        raise DerivationError(
            "search_demand_result.top_results is empty; no live search results to derive a competitor_url from"
        )

    excluded = {d.strip().lower().lstrip("www.") for d in (exclude_domains or []) if isinstance(d, str)}
    for item in top_results:
        if not isinstance(item, Mapping):
            continue
        link = item.get("link")
        if not isinstance(link, str) or not link.strip():
            continue
        domain = urllib.parse.urlparse(link).netloc.lower().lstrip("www.")
        if domain and domain not in excluded:
            return link

    raise DerivationError(
        "No usable competitor_url found in search_demand_result.top_results "
        "(all results were missing a link or matched an excluded domain)"
    )
