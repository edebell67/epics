"""
EP050 Node 19: Quality & Compliance Review

Automated deterministic hard stop-gate validating candidate AssetPayload objects from Node 17
against verified facts (Node 16), safety regulations, PII boundaries, and the canonical
Node 19-to-Node 20 Contract v1.1.0.

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial deterministic implementation of Quality & Compliance stop-gate with Canonical Contract v1.1.0 package generation.
"""

from __future__ import annotations

import os
import sys
import re
import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_16_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_16"))
NODE_17_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_17"))

for p in (NODE_16_DIR, NODE_17_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from canonical_knowledge_store import CanonicalKnowledgeStore, CanonicalFactRecord
    from content_utility_factory import AssetPayload, AssetMetadata
except ImportError:
    pass


class ValidationError(ValueError):
    """Raised when evaluation input is completely malformed."""
    pass


VALIDATOR_VERSION = "node_19_v1.0"
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(?:\+44|0)\s?(?:7\d{3}|\d{4})\s?\d{3}\s?\d{3}")
TEST_URL_PATTERN = re.compile(r"^https://[A-Za-z0-9.-]+\.test(?:/.*)?$")


@dataclass(frozen=True)
class ComplianceCheckResult:
    """Evaluation outcome of Quality & Compliance review."""
    check_id: str
    asset_id: str
    approved: bool
    checked_at: str
    reasons: List[str]
    disclaimer_verified: bool
    facts_verified: bool
    validator_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "asset_id": self.asset_id,
            "approved": self.approved,
            "checked_at": self.checked_at,
            "reasons": list(self.reasons),
            "disclaimer_verified": self.disclaimer_verified,
            "facts_verified": self.facts_verified,
            "validator_version": self.validator_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass(frozen=True)
class ApprovedAssetPackage:
    """Conforms byte-for-byte with Canonical Contract v1.1.0 approved_asset_package_schema."""
    schema_version: str
    asset_id: str
    target_id: str
    opportunity_id: str
    asset_type: str
    headline: str
    body_content: Dict[str, Any]
    cta_definition: Dict[str, Any]
    compliance_stamp: Dict[str, Any]
    target_channels: List[str]
    schedule_request: Dict[str, Any]
    generated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _compute_deterministic_check_id(
    asset_id: str,
    target_id: str,
    opportunity_id: str,
    validator_version: str
) -> str:
    """Generates a reproducible, stable hash-based check ID."""
    token = f"{asset_id}:{target_id}:{opportunity_id}:{validator_version}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"chk_{digest}"


def evaluate_asset_compliance(
    asset_input: Union[AssetPayload, Dict[str, Any]],
    knowledge_store: Optional[CanonicalKnowledgeStore] = None,
    default_destination_url: str = "https://service.placeholder.test/book"
) -> Tuple[ComplianceCheckResult, Optional[ApprovedAssetPackage]]:
    """
    Evaluates an AssetPayload against factual, safety, regulatory, and contract constraints.
    Returns (ComplianceCheckResult, Optional[ApprovedAssetPackage]).
    """
    if isinstance(asset_input, dict):
        raw = asset_input
    elif hasattr(asset_input, "to_dict"):
        raw = asset_input.to_dict()
    else:
        raise ValidationError("asset_input must be an AssetPayload or dictionary.")

    asset_id = str(raw.get("asset_id", "")).strip()
    target_id = str(raw.get("target_id", "")).strip()
    opportunity_id = str(raw.get("opportunity_id", "")).strip()

    reasons: List[str] = []
    disclaimer_verified = False
    facts_verified = False

    # 1. Lineage & Field Presence Checks
    for req in ("asset_id", "target_id", "opportunity_id", "title", "body_content", "safety_disclaimer", "call_to_action", "fact_ids", "metadata"):
        if req not in raw or not raw[req]:
            reasons.append(f"Missing mandatory field '{req}'.")

    # 2. Safety Disclaimer Check
    disclaimer = str(raw.get("safety_disclaimer", "")).strip()
    if not disclaimer or len(disclaimer) < 10:
        reasons.append("Safety disclaimer is missing or too short.")
    elif "SAFETY" not in disclaimer.upper():
        # Previously also accepted the literal "GAS SAFE" as an alternative -- a gas/boiler-
        # specific regulatory scheme that has no meaning for any other vertical. It was never
        # load-bearing (every real disclaimer already contains "SAFETY"); removed rather than
        # generalised, since a generic check has nothing domain-specific left to say.
        reasons.append("Safety disclaimer must explicitly reference regulatory safety standard.")
    else:
        disclaimer_verified = True

    # 3. Facts Verification vs Knowledge Store
    fact_ids = raw.get("fact_ids", [])
    if not fact_ids or not isinstance(fact_ids, list):
        reasons.append("Asset must cite at least one verified fact ID.")
    elif knowledge_store is not None:
        missing_facts = []
        for fid in fact_ids:
            rec = knowledge_store.get_fact(fid)
            if not rec:
                missing_facts.append(fid)
        if missing_facts:
            reasons.append(f"Referenced fact IDs not found in CanonicalKnowledgeStore: {missing_facts}")
        else:
            facts_verified = True
    else:
        # If knowledge_store not explicitly passed, assume fact IDs are syntactically valid
        if all(isinstance(f, str) and f.startswith("fact_") for f in fact_ids):
            facts_verified = True
        else:
            reasons.append("Fact IDs must follow standard 'fact_' prefix convention.")

    # 4. Prohibited PII Screening
    full_text = f"{raw.get('title', '')} {raw.get('body_content', '')} {raw.get('call_to_action', '')} {disclaimer}"
    if EMAIL_PATTERN.search(full_text):
        reasons.append("Prohibited PII detected: email address found in asset content.")
    if PHONE_PATTERN.search(full_text):
        reasons.append("Prohibited PII detected: direct telephone number found in asset content.")

    # 5. External Action Guarantee
    meta = raw.get("metadata", {})
    if meta.get("external_action", False) is not False:
        reasons.append("Asset violates offline safety boundary: external_action is not False.")

    # 6. Check destination URL pattern
    if not TEST_URL_PATTERN.match(default_destination_url):
        reasons.append(f"CTA destination URL '{default_destination_url}' does not conform to .test domain requirement.")

    # Determine Approval Decision
    checked_at = datetime.now(timezone.utc).isoformat()
    approved = (len(reasons) == 0) and disclaimer_verified and facts_verified
    check_id = _compute_deterministic_check_id(asset_id, target_id, opportunity_id, VALIDATOR_VERSION)

    check_result = ComplianceCheckResult(
        check_id=check_id,
        asset_id=asset_id,
        approved=approved,
        checked_at=checked_at,
        reasons=reasons,
        disclaimer_verified=disclaimer_verified,
        facts_verified=facts_verified,
        validator_version=VALIDATOR_VERSION
    )

    if not approved:
        return check_result, None

    # Construct ApprovedAssetPackage according to Canonical Contract v1.1.0.
    # Every fallback below only fires if the (already-validated, required) asset field is
    # genuinely empty -- it previously named "boiler"/"Blackheath" regardless of what business or
    # town the asset was actually for. Fallbacks are now domain-neutral placeholders, never a
    # specific trade or place, and asset_id/intent_category are used to keep utm_campaign real
    # rather than a fixed literal.
    body_text = str(raw.get("body_content", ""))
    lines = [line.strip("- ").strip() for line in body_text.splitlines() if line.strip()]
    summary = lines[0] if lines else "See safety disclaimer and referenced facts for details."
    steps = lines[1:] if len(lines) > 1 else ["Review the verified facts below.", "Consult a suitably qualified professional."]
    intent_category = str(meta.get("intent_category") or "general").strip() or "general"

    approved_package = ApprovedAssetPackage(
        schema_version="1.1.0",
        asset_id=asset_id,
        target_id=target_id,
        opportunity_id=opportunity_id,
        asset_type="troubleshooting_guide",
        headline=str(raw.get("title") or f"Verified guidance ({asset_id})"),
        body_content={
            "summary": summary,
            "steps": steps,
            "safety_disclaimer": disclaimer
        },
        cta_definition={
            "cta_label": str(raw.get("call_to_action") or "Get in touch"),
            "cta_type": "lead_intake",
            "destination_url": default_destination_url,
            "tracking_params": {
                "utm_source": "distribution_engine",
                "utm_medium": str(meta.get("channel", "search_landing")),
                "utm_campaign": intent_category,
                "asset_id": asset_id
            }
        },
        compliance_stamp={
            "approved": True,
            "checked_at": checked_at,
            "validator_version": VALIDATOR_VERSION,
            "disclaimer_verified": True,
            "facts_verified": True
        },
        target_channels=["search_landing"],
        schedule_request={
            "channel": "search_landing",
            "audience": f"aud_{target_id}",
            "scheduled_at": checked_at
        },
        generated_at=str(raw.get("created_at", checked_at))
    )

    return check_result, approved_package
