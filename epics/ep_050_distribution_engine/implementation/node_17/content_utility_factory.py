"""
EP050 Node 17: Content & Utility Factory

Synthesizes verified canonical domain knowledge facts (Node 16), classified customer intent (Node 11),
selected channel placements (Node 14), and conversion definitions (Node 04) into deterministic,
template-driven asset payloads with mandatory safety disclaimers, permitted CTAs, and external_action=False.

VERSION HISTORY
- v1.1.0 · 2026-08-19 · DE-HARDCODED the rendered copy. Every asset title, body and call-to-action
  previously contained the literal strings "Blackheath" and "SE3", plus boiler/gas-specific wording
  ("Gas Safe", "combi boilers", "repressurise"). That was correct only for the single original
  campaign. Because the engine's whole scaling model is geographic replication -- one winner spawns
  campaigns in neighbouring towns -- every replicated candidate rendered adverts naming the WRONG
  TOWN. Confirmed live: a real Greenwich candidate produced "Emergency Boiler Repair Blackheath ...
  rapid arrival across SE3" while its target, audience, cluster theme and shared_traits all
  correctly carried Greenwich. It went undetected because nothing had ever reached this node via a
  replicated candidate before, only via the original campaign where the literal happened to match.
  New resolve_campaign_context() derives locality/region/country/service_label/market_segment from
  Node 11's classification, which already carried geography and service_context (threaded down from
  the Node 05 demand signal) -- the data was always available, it simply was not used.
  generate_asset_payload() also accepts explicit geography/service_context overrides. Fails closed
  when no service is resolvable (refusing to invent a subject for an advert); when locality is
  genuinely unknown the copy OMITS any geographic claim rather than substituting a default.
  Additionally removed business claims that no node evidences -- "vetted", "fixed-fee", "same-day",
  "24/7", "Fixed diagnostic pricing" -- and replaced the gas-specific safety-disclaimer fallback
  with a domain-neutral one, since asserting Gas Safe regulation is both a hardcoded domain
  assumption and false for any non-gas vertical this engine is meant to serve. template_version
  1.0.0 -> 1.1.0 because rendered output changes for every asset.
- v1.0.0 · 2026-08-17 · Initial deterministic implementation of Content & Utility Factory with factual lineage preservation, safety disclaimers, and offline enclosure.
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
from typing import Any, Dict, List, Optional, Union

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_04_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_04"))
NODE_11_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_11"))
NODE_14_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_14"))
NODE_16_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_16"))

for p in (NODE_04_DIR, NODE_11_DIR, NODE_14_DIR, NODE_16_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from canonical_knowledge_store import CanonicalFactRecord, CanonicalKnowledgeStore
    from channel_placement_selection import ChannelSelectionRecord, RankedPlacementOption
    from intent_classification import IntentClassificationResult
except ImportError:
    pass


class ValidationError(ValueError):
    """Raised when asset generation payload fails schema, template, or safety validation."""
    pass


class LineageError(ValueError):
    """Raised when upstream factual or targeting lineage is missing or corrupt."""
    pass


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(?:\+44|0)\s?(?:7\d{3}|\d{4})\s?\d{3}\s?\d{3}")


@dataclass(frozen=True)
class AssetMetadata:
    """Metadata describing the rendered asset container."""
    channel: str
    placement_type: str
    format: str
    intent_category: str
    template_id: str
    template_version: str
    external_action: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AssetPayload:
    """Immutable output container for a rendered marketing and utility asset."""
    asset_id: str
    title: str
    body_content: str
    safety_disclaimer: str
    call_to_action: str
    fact_ids: List[str]
    target_id: str
    signal_id: str
    classification_id: str
    opportunity_id: str
    path_id: str
    selection_id: str
    metadata: AssetMetadata
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "title": self.title,
            "body_content": self.body_content,
            "safety_disclaimer": self.safety_disclaimer,
            "call_to_action": self.call_to_action,
            "fact_ids": list(self.fact_ids),
            "target_id": self.target_id,
            "signal_id": self.signal_id,
            "classification_id": self.classification_id,
            "opportunity_id": self.opportunity_id,
            "path_id": self.path_id,
            "selection_id": self.selection_id,
            "metadata": self.metadata.to_dict(),
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _compute_deterministic_asset_id(
    target_id: str,
    channel: str,
    placement_format: str,
    template_version: str,
    fact_checksum: str
) -> str:
    """Generates a reproducible, stable hash-based asset ID."""
    token = f"{target_id}:{channel}:{placement_format}:{template_version}:{fact_checksum}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"asset_{digest}"


def _humanise_token(value: str) -> str:
    """'boiler_repair' -> 'Boiler Repair'. Presentation only; invents no words of its own."""
    return " ".join(part for part in str(value).replace("_", " ").split() if part).title()


def _as_mapping(value: Any) -> Dict[str, Any]:
    """Normalise a record that may arrive as a dict, a dataclass-like object, or None."""
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        try:
            result = value.to_dict()
            return result if isinstance(result, dict) else {}
        except Exception:  # noqa: BLE001 - a non-conforming record simply yields no context
            return {}
    return {}


def resolve_campaign_context(
    intent_input: Any = None,
    geography: Optional[Dict[str, Any]] = None,
    service_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve the REAL locality/region/service this asset is for -- never a hardcoded default.

    Every value is read from upstream records that already carry it: Node 11's classification
    holds both `geography` and `service_context`, threaded down from the Node 05 demand signal.
    Explicit arguments win over the classification so a caller can be specific.

    Why this exists: until 2026-08-19 this module wrote the literal strings "Blackheath" and "SE3"
    into every asset's title, body and call-to-action. That was correct only for the single
    original campaign. The moment a replicated candidate reached Node 17 -- which is the entire
    scaling model, one winner spawning neighbouring towns -- it produced ad copy advertising the
    wrong town: a real Greenwich campaign rendered "Emergency Boiler Repair Blackheath ... rapid
    arrival across SE3", while every upstream node correctly carried Greenwich. Spend aimed at a
    place you are not targeting is worse than no campaign at all.

    Returns a dict with `locality`, `region`, `country`, `service_label`, `market_segment`. Any
    value that cannot be resolved from real data is returned empty, and the renderers below then
    OMIT that element rather than substituting a placeholder. Omission is honest; a default is not.
    """
    classification = _as_mapping(intent_input)
    resolved_geo = dict(geography or {}) or dict(_as_mapping(classification.get("geography")))
    resolved_service = dict(service_context or {}) or dict(_as_mapping(classification.get("service_context")))

    service_name = str(resolved_service.get("service_name") or "").strip()
    return {
        "locality": str(resolved_geo.get("locality") or "").strip(),
        "region": str(resolved_geo.get("region") or "").strip(),
        "country": str(resolved_geo.get("country") or "").strip(),
        "service_label": _humanise_token(service_name) if service_name else "",
        "market_segment": str(resolved_service.get("market_segment") or "").strip(),
    }


def generate_asset_payload(
    selection_input: Union[ChannelSelectionRecord, Dict[str, Any]],
    facts: List[Union[CanonicalFactRecord, Dict[str, Any]]],
    intent_input: Optional[Union[IntentClassificationResult, Dict[str, Any]]] = None,
    custom_cta: Optional[str] = None,
    template_override: Optional[str] = None,
    geography: Optional[Dict[str, Any]] = None,
    service_context: Optional[Dict[str, Any]] = None,
) -> AssetPayload:
    """
    Synthesizes upstream distribution selections and canonical facts into a validated AssetPayload.

    Locality and service are DERIVED from real upstream records (see resolve_campaign_context) --
    this module contains no hardcoded place name or service name. `geography`/`service_context` may
    be supplied explicitly to override what the classification carries.
    """
    # 1. Normalize selection input
    if isinstance(selection_input, dict):
        sel = selection_input
    elif hasattr(selection_input, "to_dict"):
        sel = selection_input.to_dict()
    else:
        raise ValidationError("selection_input must be a ChannelSelectionRecord or dictionary.")

    # 2. Lineage enforcement (Fail-Closed)
    for req_field in ("target_id", "signal_id", "classification_id", "opportunity_id", "path_id", "selection_id"):
        if not sel.get(req_field) or not str(sel[req_field]).strip():
            raise LineageError(f"Missing mandatory upstream lineage field '{req_field}'.")

    target_id = str(sel["target_id"]).strip()
    signal_id = str(sel["signal_id"]).strip()
    classification_id = str(sel["classification_id"]).strip()
    opportunity_id = str(sel["opportunity_id"]).strip()
    path_id = str(sel["path_id"]).strip()
    selection_id = str(sel["selection_id"]).strip()

    # 3. Facts validation (must have at least 1 verified fact)
    if not facts or not isinstance(facts, list) or len(facts) == 0:
        raise LineageError("Asset generation requires at least one verified CanonicalFactRecord from Node 16.")

    fact_records = []
    fact_ids = []
    has_safety_critical = False
    safety_guidances = []

    for f in facts:
        if isinstance(f, dict):
            fid = str(f.get("fact_id", "")).strip()
            claim = str(f.get("claim", "")).strip()
            is_sc = bool(f.get("is_safety_critical", False))
            sg = f.get("safety_guidance")
        elif hasattr(f, "fact_id"):
            fid = str(f.fact_id).strip()
            claim = str(f.claim).strip()
            is_sc = bool(f.is_safety_critical)
            sg = f.safety_guidance
        else:
            raise ValidationError("Facts list contains invalid element type.")

        if not fid or not claim:
            raise ValidationError("Fact record missing fact_id or claim.")

        fact_records.append({"fact_id": fid, "claim": claim, "is_safety_critical": is_sc, "safety_guidance": sg})
        fact_ids.append(fid)
        if is_sc:
            has_safety_critical = True
            if sg:
                safety_guidances.append(str(sg).strip())

    fact_checksum = hashlib.sha256(":".join(sorted(fact_ids)).encode("utf-8")).hexdigest()[:8]

    # 4. Resolve Channel & Format
    ranked = sel.get("ranked_placements", [])
    top_placement = ranked[0] if (ranked and isinstance(ranked, list)) else {}
    channel = top_placement.get("channel_name", sel.get("primary_channel", "organic_search"))
    placement_type = top_placement.get("placement_type", "diagnostic_landing_page")
    recommended_format = top_placement.get("recommended_format", "troubleshooting_guide")

    # 5. Resolve Intent
    intent_category = "troubleshooting"
    if intent_input is not None:
        if isinstance(intent_input, dict):
            intent_category = str(intent_input.get("primary_intent", "troubleshooting"))
        elif hasattr(intent_input, "primary_intent"):
            intent_category = str(intent_input.primary_intent)

    # 5b. Resolve the REAL campaign context. No literal locality or service appears below this
    # line -- every geographic and service reference is derived from upstream records.
    context = resolve_campaign_context(intent_input, geography=geography, service_context=service_context)
    service_label = context["service_label"]
    locality = context["locality"]
    region = context["region"]
    if not service_label:
        raise ValidationError(
            "Cannot render an asset without a real service to advertise. service_context.service_name "
            "was not resolvable from the classification or the explicit service_context argument; "
            "refusing to substitute a default (fail-closed)."
        )
    # "Greenwich, London" when both are known and distinct; just the one that is known otherwise;
    # empty when neither is -- in which case the copy simply carries no geographic claim.
    place = ", ".join(dict.fromkeys(part for part in (locality, region) if part))

    # 6. Safety Disclaimer Construction
    if safety_guidances:
        # Real, fact-attached guidance registered by Node 16.
        safety_disclaimer = "SAFETY MANDATE: " + " ".join(safety_guidances)
    else:
        # Domain-neutral fallback. This previously asserted Gas Safe / gas-appliance regulation
        # unconditionally, which is both a hardcoded domain assumption and a false statement for
        # any non-gas vertical this engine is meant to serve.
        safety_disclaimer = (
            "SAFETY NOTICE: Follow all applicable local regulations and use suitably qualified, "
            "registered professionals for this work."
        )

    # 7. Call To Action Resolution (Aligned with Node 04)
    if custom_cta:
        call_to_action = str(custom_cta).strip()
    else:
        # Deliberately claims nothing the pipeline cannot evidence. The previous default asserted
        # "vetted", "fixed-fee" and "same-day" -- none of which any node registers as a real fact.
        call_to_action = (
            f"Enquire about {service_label} in {place}." if place else f"Enquire about {service_label}."
        )

    # 8. Template Selection & Rendering
    template_version = "1.1.0"
    template_id = template_override or f"tpl_{channel}_{recommended_format}"

    primary_claims_text = "\n".join([f"- {fr['claim']}" for fr in fact_records])
    place_suffix = f" | {place}" if place else ""
    place_phrase = f" in {place}" if place else ""

    if "local_search" in channel or "maps" in placement_type:
        title = f"{service_label}{place_suffix}"
        body_content = (
            f"Local {service_label.lower()} support{place_phrase}.\n\n"
            f"Verified Technical Information:\n{primary_claims_text}"
        )
    elif "paid_search" in channel:
        title = f"{service_label}{place_suffix}"
        body_content = (
            f"{service_label}{place_phrase}.\n"
            f"Key Verified Facts:\n{primary_claims_text}"
        )
    else:
        title = f"{service_label}: Diagnosis and Repair Guide{place_suffix}"
        body_content = (
            f"Guide to {service_label.lower()}{place_phrase}.\n\n"
            f"Verified Technical Information:\n{primary_claims_text}"
        )

    # 9. PII Screening
    for text_block in (title, body_content, safety_disclaimer, call_to_action):
        if EMAIL_PATTERN.search(text_block) or PHONE_PATTERN.search(text_block):
            raise ValidationError("Prohibited PII detected in rendered asset content.")

    # 10. Deterministic Asset ID Calculation
    asset_id = _compute_deterministic_asset_id(target_id, channel, recommended_format, template_version, fact_checksum)
    created_at = datetime.now(timezone.utc).isoformat()

    metadata = AssetMetadata(
        channel=channel,
        placement_type=placement_type,
        format=recommended_format,
        intent_category=intent_category,
        template_id=template_id,
        template_version=template_version,
        external_action=False  # Literal False guarantee
    )

    return AssetPayload(
        asset_id=asset_id,
        title=title,
        body_content=body_content,
        safety_disclaimer=safety_disclaimer,
        call_to_action=call_to_action,
        fact_ids=fact_ids,
        target_id=target_id,
        signal_id=signal_id,
        classification_id=classification_id,
        opportunity_id=opportunity_id,
        path_id=path_id,
        selection_id=selection_id,
        metadata=metadata,
        created_at=created_at
    )
