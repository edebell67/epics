"""EP050 Node 27: deterministic, offline-only structured lead capture."""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

CAPTURE_VERSION = "structured_lead_capture_v1.0.0"
_PII = re.compile(r"(?:\b[\w.+-]+@[\w-]+\.[\w.-]+\b|\b(?:\+44|0)\s?7\d{3}\s?\d{3}\s?\d{3}\b)", re.I)
_ALLOWED = frozenset({"session_id", "source", "consent"})


class LeadCaptureValidationError(ValueError):
    """Raised when an intake cannot safely form an inert local lead record."""


class LeadCaptureConflictError(LeadCaptureValidationError):
    """Raised when a stable lead identifier maps to different content."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LeadCaptureValidationError(f"{name} must be an object")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 160:
        raise LeadCaptureValidationError(f"{name} must be a bounded non-empty string")
    if _PII.search(value):
        raise LeadCaptureValidationError(f"{name} must not contain PII")
    return value.strip()


def _contains_pii(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PII.search(value))
    if isinstance(value, Mapping):
        return any(_contains_pii(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_pii(item) for item in value)
    return False


def _validate_route(route: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _mapping(route, "node_26_route")
    if candidate.get("external_action") is not False:
        raise LeadCaptureValidationError("Node 26 route must be non-executing")
    if candidate.get("schema_version") != "1.0.0" or not str(candidate.get("route_id", "")).startswith("sdr_"):
        raise LeadCaptureValidationError("a valid Node 26 route is required")
    destination = _mapping(candidate.get("destination"), "route.destination")
    parsed = urlparse(_text(destination.get("url"), "route.destination.url"))
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".test") or parsed.username or parsed.password or parsed.port:
        raise LeadCaptureValidationError("route destination must be credential-free HTTPS .test")
    if destination.get("eligible") is not True:
        raise LeadCaptureValidationError("route destination must be eligible")
    lineage = _mapping(candidate.get("lineage"), "route.lineage")
    for name in ("publication_plan_id", "search_distribution_id", "asset_id", "target_id", "opportunity_id"):
        _text(lineage.get(name), f"route.lineage.{name}")
    context = _mapping(candidate.get("routing_context"), "route.routing_context")
    channel = _text(context.get("channel"), "route.routing_context.channel")
    if _contains_pii(candidate):
        raise LeadCaptureValidationError("Node 26 route must not contain PII")
    return {"route_id": candidate["route_id"], "destination_url": destination["url"], "cta_type": _text(destination.get("cta_type"), "route.destination.cta_type"), "cta_label": _text(destination.get("cta_label"), "route.destination.cta_label"), "channel": channel, "lineage": {name: lineage[name] for name in lineage}}


def build_structured_lead_record(node_26_route: Mapping[str, Any], intake: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic, PII-free, local-only lead record; never contact or route."""
    route = _validate_route(node_26_route)
    supplied = _mapping(intake, "intake")
    if set(supplied) != _ALLOWED or _contains_pii(supplied):
        raise LeadCaptureValidationError("intake must use only the approved PII-free schema")
    if supplied.get("source") != route["channel"]:
        raise LeadCaptureValidationError("intake source must match Node 26 channel lineage")
    session_id = _text(supplied.get("session_id"), "intake.session_id")
    consent = _mapping(supplied.get("consent"), "intake.consent")
    if set(consent) != {"granted", "timestamp", "version", "basis"} or consent.get("granted") is not True:
        raise LeadCaptureValidationError("explicit granted consent is required")
    timestamp = _text(consent.get("timestamp"), "consent.timestamp")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp):
        raise LeadCaptureValidationError("consent.timestamp must be a UTC ISO-8601 timestamp")
    normalized_consent = {"granted": True, "timestamp": timestamp, "version": _text(consent.get("version"), "consent.version"), "basis": _text(consent.get("basis"), "consent.basis")}
    key = {"capture_version": CAPTURE_VERSION, "route_id": route["route_id"], "session_id": session_id, "source": route["channel"], "consent": normalized_consent}
    lead_id = "slc_" + hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema_version": "1.0.0", "lead_id": lead_id, "capture_version": CAPTURE_VERSION, "session_id": session_id, "source": route["channel"], "consent": normalized_consent, "acquisition": {"route_id": route["route_id"], "destination_url": route["destination_url"], "cta_type": route["cta_type"], "cta_label": route["cta_label"], "channel": route["channel"], **route["lineage"]}, "external_action": False}


@dataclass
class LocalLeadCaptureRepository:
    """Conflict-protected local persistence for inert structured lead fixtures."""
    root: Path
    _records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def store(self, record: Mapping[str, Any]) -> dict[str, Any]:
        candidate = deepcopy(dict(_mapping(record, "record")))
        lead_id = candidate.get("lead_id")
        if not isinstance(lead_id, str) or not lead_id.startswith("slc_") or candidate.get("external_action") is not False:
            raise LeadCaptureValidationError("only non-executing stable lead records may be stored")
        if _contains_pii(candidate):
            raise LeadCaptureValidationError("lead record must not contain PII")
        existing = self._records.get(lead_id)
        if existing is not None:
            if existing != candidate:
                raise LeadCaptureConflictError(f"conflicting record for {lead_id}")
            return deepcopy(existing)
        path = self.root / f"{lead_id}.json"
        if path.exists():
            stored = json.loads(path.read_text(encoding="utf-8"))
            if stored != candidate:
                raise LeadCaptureConflictError(f"conflicting persisted record for {lead_id}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(candidate, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        self._records[lead_id] = deepcopy(candidate)
        return deepcopy(candidate)
