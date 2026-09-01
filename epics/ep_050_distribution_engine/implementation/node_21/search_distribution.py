# epics/ep_050_distribution_engine/implementation/node_21/search_distribution.py — Deterministic offline-only Search Distribution package builder.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial local manifest renderer and fail-closed Node 19→20→21 lineage validator; prevents publishing and indexing actions.

"""EP050 Node 21: generate local, non-dispatched search-distribution artifacts.

This module has no HTTP client, CMS adapter, credential reader, queue, or indexing
integration. It only validates local Node 19/20 data and writes review fixtures.
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

from publishing_scheduler import (
    PublicationPlanValidationError,
    build_mock_publication_plan,
    validate_approved_asset_package,
)


class SearchDistributionValidationError(ValueError):
    """Raised when a candidate cannot safely produce an offline search package."""


class SearchDistributionConflictError(ValueError):
    """Raised when a package identifier resolves to different local content."""


_REQUIRED_ARTIFACTS = (
    "article.md",
    "landing-page.md",
    "faq.json",
    "structured-data.json",
    "internal-link-plan.json",
    "sitemap-indexing-support.json",
    "localized-page-plan.json",
    "manifest.json",
)


def _as_mapping(value: Mapping[str, Any] | Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SearchDistributionValidationError(f"{name} must be a mapping")
    return deepcopy(dict(value))


def _require_test_url(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise SearchDistributionValidationError(f"{field_name} must be an HTTPS .test URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".test"):
        raise SearchDistributionValidationError(f"{field_name} must be an HTTPS .test URL")
    if parsed.username or parsed.password or parsed.port:
        raise SearchDistributionValidationError(f"{field_name} must not contain credentials or a port")
    return value


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise SearchDistributionValidationError("headline must yield a non-empty URL slug")
    return slug


def validate_search_distribution_inputs(
    publication_plan: Mapping[str, Any] | Any,
    approved_asset_package: Mapping[str, Any] | Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate exact Node 20 projection plus approved Node 19 asset semantics."""
    plan = _as_mapping(publication_plan, "publication_plan")
    try:
        approved = validate_approved_asset_package(approved_asset_package)
        expected_plan = build_mock_publication_plan(approved)
    except PublicationPlanValidationError as error:
        raise SearchDistributionValidationError(str(error)) from error
    if plan != expected_plan:
        raise SearchDistributionValidationError("publication_plan must exactly match approved Node 20 projection")
    if plan.get("external_action") is not False:
        raise SearchDistributionValidationError("external_action must be literally false")
    if plan.get("approval_state") != "approved":
        raise SearchDistributionValidationError("publication_plan approval_state must be approved")
    if plan.get("channel") != "search_landing":
        raise SearchDistributionValidationError("publication_plan channel must be search_landing")
    destination = _require_test_url(plan.get("cta", {}).get("destination_url"), "cta.destination_url")
    if not all(approved["compliance_stamp"].get(key) is True for key in ("approved", "disclaimer_verified", "facts_verified")):
        raise SearchDistributionValidationError("approved package requires complete approval, disclaimer, and facts")
    if not str(approved["body_content"].get("safety_disclaimer", "")).strip():
        raise SearchDistributionValidationError("approved package safety disclaimer is required")
    if not str(plan.get("cta", {}).get("label", "")).strip():
        raise SearchDistributionValidationError("CTA label is required")
    if plan["cta"]["tracking_params"] != approved["cta_definition"]["tracking_params"]:
        raise SearchDistributionValidationError("CTA tracking lineage is broken")
    _require_test_url(destination, "cta.destination_url")
    return plan, approved


def derive_search_distribution_id(plan: Mapping[str, Any]) -> str:
    """Derive stable ID from immutable Node 20 plan identity and tracking lineage."""
    key = {
        "publication_plan_id": plan["publication_plan_id"],
        "asset_id": plan["asset_id"],
        "destination_url": plan["cta"]["destination_url"],
        "tracking_params": plan["cta"]["tracking_params"],
    }
    encoded = json.dumps(key, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sdp_" + hashlib.sha256(encoded).hexdigest()


def build_search_distribution_package(
    publication_plan: Mapping[str, Any] | Any,
    approved_asset_package: Mapping[str, Any] | Any,
) -> dict[str, Any]:
    """Build every required local artifact payload deterministically, without dispatch."""
    plan, approved = validate_search_distribution_inputs(publication_plan, approved_asset_package)
    distribution_id = derive_search_distribution_id(plan)
    base = plan["cta"]["destination_url"].rstrip("/")
    slug = _slug(approved["headline"])
    landing_url = f"{base}/search/{slug}"
    localized_url = f"{base}/en-gb/search/{slug}"
    for name, url in (("landing_url", landing_url), ("localized_url", localized_url)):
        _require_test_url(url, name)
    summary = approved["body_content"]["summary"]
    disclaimer = approved["body_content"]["safety_disclaimer"]
    cta = plan["cta"]
    artifacts: dict[str, Any] = {
        "article.md": f"# {approved['headline']}\n\n{summary}\n\n{disclaimer}\n\n[{cta['label']}]({cta['destination_url']})\n",
        "landing-page.md": f"# {approved['headline']}\n\n{summary}\n\n{disclaimer}\n\nCTA: [{cta['label']}]({cta['destination_url']})\n",
        "faq.json": {"questions": [{"question": f"What should I know about {approved['headline']}?", "answer": summary}]},
        "structured-data.json": {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": f"What should I know about {approved['headline']}?", "acceptedAnswer": {"@type": "Answer", "text": summary}}]},
        "internal-link-plan.json": {"source": landing_url, "links": [{"href": cta["destination_url"], "anchor": cta["label"]}]},
        "sitemap-indexing-support.json": {"url": landing_url, "sitemap_entry": True, "indexing_request": False, "external_action": False},
        "localized-page-plan.json": {"locale": "en-GB", "source_url": landing_url, "localized_url": localized_url, "external_action": False},
    }
    manifest = {
        "schema_version": "1.0.0",
        "search_distribution_id": distribution_id,
        "publication_plan_id": plan["publication_plan_id"],
        "asset_id": plan["asset_id"],
        "target_id": plan["target_id"],
        "opportunity_id": plan["opportunity_id"],
        "landing_url": landing_url,
        "cta": deepcopy(cta),
        "approval_state": "approved",
        "external_action": False,
        "artifacts": list(_REQUIRED_ARTIFACTS),
    }
    artifacts["manifest.json"] = manifest
    return {"manifest": manifest, "artifacts": artifacts}


@dataclass
class LocalSearchDistributionRepository:
    """Idempotently persists rendered artifacts under a caller-selected local directory."""

    root: Path
    _packages: dict[str, dict[str, Any]] = field(default_factory=dict)

    def store(self, package: Mapping[str, Any]) -> dict[str, Any]:
        candidate = _as_mapping(package, "package")
        manifest = _as_mapping(candidate.get("manifest"), "package.manifest")
        artifacts = _as_mapping(candidate.get("artifacts"), "package.artifacts")
        package_id = manifest.get("search_distribution_id")
        if not isinstance(package_id, str) or not package_id.startswith("sdp_"):
            raise SearchDistributionValidationError("package manifest requires search_distribution_id")
        if tuple(sorted(artifacts)) != tuple(sorted(_REQUIRED_ARTIFACTS)):
            raise SearchDistributionValidationError("package must contain each required search artifact exactly once")
        if manifest.get("external_action") is not False or artifacts["sitemap-indexing-support.json"].get("indexing_request") is not False:
            raise SearchDistributionValidationError("package must not request an external action or indexing")
        existing = self._packages.get(package_id)
        if existing is not None:
            if existing != candidate:
                raise SearchDistributionConflictError(f"conflicting record for {package_id}")
            return deepcopy(existing)
        target = self.root / package_id
        if target.exists():
            existing_manifest = target / "manifest.json"
            if not existing_manifest.exists() or json.loads(existing_manifest.read_text(encoding="utf-8")) != manifest:
                raise SearchDistributionConflictError(f"conflicting persisted record for {package_id}")
        else:
            target.mkdir(parents=True)
            for name, content in artifacts.items():
                path = target / name
                if isinstance(content, str):
                    path.write_text(content, encoding="utf-8")
                else:
                    path.write_text(json.dumps(content, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        self._packages[package_id] = deepcopy(candidate)
        return deepcopy(candidate)
