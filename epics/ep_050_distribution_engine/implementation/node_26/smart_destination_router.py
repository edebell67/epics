"""EP050 Node 26: deterministic, offline-only Smart Destination Router.

This module produces inert local route recommendations. It has no HTTP client,
network adapter, lead-capture facility, or URL execution capability.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from search_distribution import (
    SearchDistributionValidationError,
    build_search_distribution_package,
)

ROUTER_VERSION = "smart_destination_router_v1.0.0"
_DEFERRED_NODES = frozenset({"22", "23", "24", "25"})
_PII = re.compile(r"(?:\b[\w.+-]+@[\w-]+\.[\w.-]+\b|\b(?:\+44|0)\s?7\d{3}\s?\d{3}\s?\d{3}\b)", re.I)
# A "rule" is a pre-approved POLICY shape (which intent/channel/destination-path/cta_type
# combinations are allowed to route at all) -- it is deliberately NOT scoped to any specific
# business. topic/geography/service are real per-campaign values (see build_route_recommendation)
# and must never appear here: this tuple originally pinned topic="safe boiler pressure guide",
# geography="blackheath", service="boiler_repair" as literal match requirements, which meant
# _matching_rule rejected every real campaign except the one that happened to be Blackheath boiler
# repair -- "no approved routing rule matches this context and destination" for anything else,
# including the four real Greenwich/Lewisham/Charlton/Eltham campaigns this system exists to run.
_RULES = ({
    "rule_id": "diagnostic_quote_search_v1",
    "intent": "diagnostic_quote",
    "channel": "search_landing",
    "destination_path": "/book",
    "cta_type": "lead_intake",
},)


class DestinationRoutingValidationError(ValueError):
    """Raised when a route candidate is unsafe, incomplete, or unapproved."""


class DestinationRoutingConflictError(ValueError):
    """Raised when a stable route ID maps to a different local record."""


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DestinationRoutingValidationError(f"{name} must be a mapping")
    return deepcopy(dict(value))


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DestinationRoutingValidationError(f"{name} must be a non-empty string")
    value = value.strip()
    if _PII.search(value):
        raise DestinationRoutingValidationError(f"{name} must not contain PII")
    return value


def _test_url(value: Any) -> str:
    value = _text(value, "destination_url")
    parsed = urlparse(value)
    if (parsed.scheme, parsed.hostname) == ("https", None) or parsed.scheme != "https" or not parsed.hostname:
        raise DestinationRoutingValidationError("destination_url must be an HTTPS .test URL")
    if not parsed.hostname.endswith(".test") or parsed.username or parsed.password or parsed.port:
        raise DestinationRoutingValidationError("destination_url must be an HTTPS .test URL without credentials or port")
    return value


def _validate_deferred_context(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    context = _mapping(value, "deferred_channel_context")
    if set(context) - _DEFERRED_NODES:
        raise DestinationRoutingValidationError("deferred_channel_context may name only Nodes 22-25")
    for node, state in context.items():
        if state != "deferred":
            raise DestinationRoutingValidationError("Nodes 22-25 must be explicitly deferred, never completed")
    return context


def _matching_rule(context: Mapping[str, Any], destination_url: str, cta_type: str) -> Mapping[str, str]:
    # Matches on POLICY fields only (intent/channel/destination-path/cta_type). topic/geography/
    # service are real campaign data, asserted non-empty and PII-screened by _text() at the call
    # site, but never gated against a rule literal -- see _RULES for why.
    for rule in _RULES:
        if all(context[field] == rule[field] for field in ("intent", "channel")):
            parsed = urlparse(destination_url)
            if parsed.path == rule["destination_path"] and cta_type == rule["cta_type"]:
                return rule
    raise DestinationRoutingValidationError("no approved routing rule matches this context and destination")


def build_route_recommendation(
    publication_plan: Mapping[str, Any],
    approved_asset_package: Mapping[str, Any],
    search_package: Mapping[str, Any],
    routing_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a local, deterministic destination recommendation; never execute it."""
    plan = _mapping(publication_plan, "publication_plan")
    approved = _mapping(approved_asset_package, "approved_asset_package")
    supplied_search = _mapping(search_package, "search_package")
    context = _mapping(routing_context, "routing_context")
    if context.get("external_action") is not False:
        raise DestinationRoutingValidationError("routing_context.external_action must be literally false")
    _validate_deferred_context(context.get("deferred_channel_context"))
    try:
        expected_search = build_search_distribution_package(plan, approved)
    except SearchDistributionValidationError as error:
        raise DestinationRoutingValidationError(str(error)) from error
    if supplied_search != expected_search:
        raise DestinationRoutingValidationError("search_package must exactly match validated Node 21 output")
    manifest = expected_search["manifest"]
    for field in ("topic", "intent", "geography", "service", "channel"):
        context[field] = _text(context.get(field), f"routing_context.{field}").lower()
    if context["channel"] != plan["channel"] or context["channel"] != "search_landing":
        raise DestinationRoutingValidationError("routing context channel must match validated Node 20/21 search lineage")
    for field in ("asset_id", "target_id", "opportunity_id"):
        if context.get(field) != plan.get(field) or context.get(field) != manifest.get(field):
            raise DestinationRoutingValidationError(f"routing context {field} lineage is broken")
    if context["asset_id"] != approved.get("asset_id"):
        raise DestinationRoutingValidationError("routing context asset lineage is broken")
    destination_url = _test_url(plan.get("cta", {}).get("destination_url"))
    if destination_url != manifest.get("cta", {}).get("destination_url"):
        raise DestinationRoutingValidationError("Node 20/21 destination lineage is broken")
    rule = _matching_rule(context, destination_url, plan.get("cta", {}).get("type"))
    key = {
        "router_version": ROUTER_VERSION, "rule_id": rule["rule_id"],
        "search_distribution_id": manifest["search_distribution_id"],
        "context": {name: context[name] for name in ("topic", "intent", "geography", "service", "channel")},
    }
    route_id = "sdr_" + hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "1.0.0", "route_id": route_id, "router_version": ROUTER_VERSION,
        "rule_id": rule["rule_id"], "rule_explanation": "Approved diagnostic-quote search context maps to the inherited allowlisted .test booking destination.",
        "destination": {"url": destination_url, "eligible": True, "cta_label": plan["cta"]["label"], "cta_type": plan["cta"]["type"]},
        "lineage": {"publication_plan_id": plan["publication_plan_id"], "search_distribution_id": manifest["search_distribution_id"], "asset_id": plan["asset_id"], "target_id": plan["target_id"], "opportunity_id": plan["opportunity_id"]},
        "routing_context": {name: context[name] for name in ("topic", "intent", "geography", "service", "channel")},
        "approval_state": "approved", "compliance_verified": True, "external_action": False,
    }


@dataclass
class LocalDestinationRouteRepository:
    """Conflict-protected local storage for inert route recommendations."""
    root: Path
    _routes: dict[str, dict[str, Any]] = field(default_factory=dict)

    def store(self, route: Mapping[str, Any]) -> dict[str, Any]:
        candidate = _mapping(route, "route")
        route_id = candidate.get("route_id")
        if not isinstance(route_id, str) or not route_id.startswith("sdr_"):
            raise DestinationRoutingValidationError("route requires a stable route_id")
        if candidate.get("external_action") is not False or candidate.get("destination", {}).get("eligible") is not True:
            raise DestinationRoutingValidationError("only eligible non-executing routes may be stored")
        existing = self._routes.get(route_id)
        if existing is not None:
            if existing != candidate:
                raise DestinationRoutingConflictError(f"conflicting record for {route_id}")
            return deepcopy(existing)
        path = self.root / f"{route_id}.json"
        if path.exists():
            stored = json.loads(path.read_text(encoding="utf-8"))
            if stored != candidate:
                raise DestinationRoutingConflictError(f"conflicting persisted record for {route_id}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(candidate, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        self._routes[route_id] = deepcopy(candidate)
        return deepcopy(candidate)
