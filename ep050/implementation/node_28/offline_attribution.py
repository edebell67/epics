"""EP050 Node 28: deterministic, offline-only attribution records."""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

ATTRIBUTION_VERSION = "offline_attribution_v1.0.0"
_MODEL_NAME = "deterministic_last_verified_touch"
_MODEL_VERSION = "1.0.0"
_PII = re.compile(
    r"(?:\b[\w.+-]+@[\w-]+\.[\w.-]+\b|\b(?:\+44|0)\s?7\d{3}\s?\d{3}\s?\d{3}\b)", re.I
)


class AttributionValidationError(ValueError):
    """Raised when a lead cannot safely yield an inert attribution record."""


class AttributionConflictError(AttributionValidationError):
    """Raised when a stable attribution identifier maps to different content."""


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AttributionValidationError(f"{name} must be an object")
    return deepcopy(dict(value))


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 160:
        raise AttributionValidationError(f"{name} must be a bounded non-empty string")
    result = value.strip()
    if _PII.search(result):
        raise AttributionValidationError(f"{name} must not contain PII")
    return result


def _contains_pii(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PII.search(value))
    if isinstance(value, Mapping):
        return any(_contains_pii(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_pii(item) for item in value)
    return False


def _test_url(value: Any, name: str) -> str:
    url = _text(value, name)
    parsed = urlparse(url)
    if (parsed.scheme != "https" or not parsed.hostname or
            not parsed.hostname.endswith(".test") or parsed.username or
            parsed.password or parsed.port):
        raise AttributionValidationError(f"{name} must be a credential-free HTTPS .test URL")
    return url


def _validate_model(model: Any) -> dict[str, Any]:
    candidate = _mapping(model, "attribution_model")
    if set(candidate) != {"name", "version", "confidence"}:
        raise AttributionValidationError("attribution_model has an unsafe or ambiguous schema")
    if candidate["name"] != _MODEL_NAME or candidate["version"] != _MODEL_VERSION:
        raise AttributionValidationError("attribution model or version is not allowlisted")
    confidence = candidate["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise AttributionValidationError("attribution confidence must be a number from zero through one")
    return {"name": _MODEL_NAME, "version": _MODEL_VERSION, "confidence": confidence}


def _validate_lead(lead: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _mapping(lead, "node_27_lead")
    if _contains_pii(candidate):
        raise AttributionValidationError("Node 27 lead must not contain PII")
    if candidate.get("schema_version") != "1.0.0" or candidate.get("capture_version") != "structured_lead_capture_v1.0.0":
        raise AttributionValidationError("a valid Node 27 structured lead is required")
    if candidate.get("external_action") is not False:
        raise AttributionValidationError("Node 27 lead must be non-executing")
    lead_id = _text(candidate.get("lead_id"), "lead_id")
    if not lead_id.startswith("slc_"):
        raise AttributionValidationError("lead_id must be a stable Node 27 identifier")
    session_id = _text(candidate.get("session_id"), "session_id")
    source = _text(candidate.get("source"), "source")
    consent = _mapping(candidate.get("consent"), "consent")
    if set(consent) != {"granted", "timestamp", "version", "basis"} or consent.get("granted") is not True:
        raise AttributionValidationError("explicit granted consent is required")
    for field in ("timestamp", "version", "basis"):
        _text(consent.get(field), f"consent.{field}")
    acquisition = _mapping(candidate.get("acquisition"), "acquisition")
    required = ("route_id", "destination_url", "cta_type", "cta_label", "channel", "publication_plan_id", "search_distribution_id", "asset_id", "target_id", "opportunity_id")
    if set(acquisition) != set(required):
        raise AttributionValidationError("lead acquisition lineage is missing or ambiguous")
    route_id = _text(acquisition["route_id"], "acquisition.route_id")
    if not route_id.startswith("sdr_"):
        raise AttributionValidationError("lead acquisition route_id is invalid")
    destination_url = _test_url(acquisition["destination_url"], "acquisition.destination_url")
    normalized = {name: _text(acquisition[name], f"acquisition.{name}") for name in required if name != "destination_url"}
    if source != normalized["channel"]:
        raise AttributionValidationError("source must match inherited channel lineage")
    return {"lead_id": lead_id, "session_id": session_id, "source": source, "consent": consent, "destination_url": destination_url, **normalized}


def build_attribution_record(node_27_lead: Mapping[str, Any], attribution_model: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic local attribution record; never track or execute."""
    lead = _validate_lead(node_27_lead)
    model = _validate_model(attribution_model)
    key = {"attribution_version": ATTRIBUTION_VERSION, "lead_id": lead["lead_id"], "model": model}
    attribution_id = "atr_" + hashlib.sha256(
        json.dumps(key, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    lineage_fields = ("target_id", "opportunity_id", "asset_id", "publication_plan_id", "search_distribution_id")
    return {
        "schema_version": "1.0.0",
        "attribution_id": attribution_id,
        "attribution_version": ATTRIBUTION_VERSION,
        "attribution_model": model,
        "lead_id": lead["lead_id"],
        "consent": lead["consent"],
        "session_id": lead["session_id"],
        "source": lead["source"],
        "route_context": {
            "route_id": lead["route_id"], "destination_url": lead["destination_url"],
            "cta_type": lead["cta_type"], "cta_label": lead["cta_label"], "channel": lead["channel"],
        },
        "lineage": {name: lead[name] for name in lineage_fields},
        "external_action": False,
    }


@dataclass
class LocalAttributionRepository:
    """Conflict-protected JSON persistence for inert offline attribution records."""
    root: Path
    _records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def store(self, record: Mapping[str, Any]) -> dict[str, Any]:
        candidate = deepcopy(_mapping(record, "record"))
        attribution_id = candidate.get("attribution_id")
        if (not isinstance(attribution_id, str) or not attribution_id.startswith("atr_") or
                candidate.get("external_action") is not False or _contains_pii(candidate)):
            raise AttributionValidationError("only PII-free non-executing attribution records may be stored")
        existing = self._records.get(attribution_id)
        if existing is not None:
            if existing != candidate:
                raise AttributionConflictError(f"conflicting record for {attribution_id}")
            return deepcopy(existing)
        path = self.root / f"{attribution_id}.json"
        if path.exists():
            stored = json.loads(path.read_text(encoding="utf-8"))
            if stored != candidate:
                raise AttributionConflictError(f"conflicting persisted record for {attribution_id}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(candidate, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        self._records[attribution_id] = deepcopy(candidate)
        return deepcopy(candidate)
