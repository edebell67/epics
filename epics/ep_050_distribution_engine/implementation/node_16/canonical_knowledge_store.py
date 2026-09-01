"""
EP050 Node 16: Canonical Knowledge Store

Manages verified, offline canonical domain knowledge facts, technical claims,
and safety-critical guidelines for downstream narrative and packaging engines.

VERSION HISTORY
- v1.0.0 · 2026-08-17 · Initial deterministic implementation of Canonical Knowledge Store with safety screening, PII protection, and full lineage preservation.
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
NODE_01_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_01"))
NODE_02_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "node_02"))

if NODE_01_DIR not in sys.path:
    sys.path.insert(0, NODE_01_DIR)
if NODE_02_DIR not in sys.path:
    sys.path.insert(0, NODE_02_DIR)

try:
    from registration import TargetRegistry
    from product_intelligence import ProductIntelligenceRegistry
except ImportError:
    TargetRegistry = None  # type: ignore
    ProductIntelligenceRegistry = None  # type: ignore


class ValidationError(ValueError):
    """Raised when fact payload fails schema or safety validation."""
    pass


class LineageError(ValueError):
    """Raised when target or product lineage is invalid or missing."""
    pass


class ConflictError(ValueError):
    """Raised when duplicate or contradictory facts are registered."""
    pass


EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(?:\+44|0)\s?(?:7\d{3}|\d{4})\s?\d{3}\s?\d{3}")


@dataclass(frozen=True)
class CanonicalFactRecord:
    """Immutable record representing a verified canonical fact or claim."""
    fact_id: str
    target_id: str
    product_id: Optional[str]
    topic: str
    claim: str
    verification_source: str
    is_safety_critical: bool
    safety_guidance: Optional[str]
    validity_status: str
    version: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _compute_deterministic_fact_id(
    target_id: str,
    topic: str,
    claim: str,
    verification_source: str
) -> str:
    """Generates a reproducible, stable hash-based fact ID."""
    token = f"{target_id}:{topic}:{claim}:{verification_source}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"fact_{digest}"


class CanonicalKnowledgeStore:
    """Registry and storage engine for canonical domain knowledge facts."""

    def __init__(
        self,
        storage_path: Optional[Union[str, Path]] = None,
        target_registry: Optional[Any] = None,
        product_registry: Optional[Any] = None
    ) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self.target_registry = target_registry
        self.product_registry = product_registry
        self._facts: Dict[str, CanonicalFactRecord] = {}

        if self.storage_path and self.storage_path.exists():
            self._load()

    def register_fact(
        self,
        target_id: str,
        topic: str,
        claim: str,
        verification_source: str,
        is_safety_critical: bool = False,
        safety_guidance: Optional[str] = None,
        product_id: Optional[str] = None,
        validity_status: str = "verified",
        version: str = "1.0.0"
    ) -> CanonicalFactRecord:
        """Validates and registers a new canonical fact."""
        # 1. Lineage check (Fail-Closed)
        if not target_id or not str(target_id).strip():
            raise LineageError("target_id is required.")
        target_id = str(target_id).strip()

        if self.target_registry is not None:
            if hasattr(self.target_registry, "get"):
                if not self.target_registry.get(target_id):
                    raise LineageError(f"Target '{target_id}' not found in TargetRegistry.")
            elif hasattr(self.target_registry, "exists"):
                if not self.target_registry.exists(target_id):
                    raise LineageError(f"Target '{target_id}' not found in TargetRegistry.")

        if product_id:
            product_id = str(product_id).strip()
            if self.product_registry is not None:
                if hasattr(self.product_registry, "get"):
                    if not self.product_registry.get(product_id):
                        raise LineageError(f"Product '{product_id}' not found in ProductIntelligenceRegistry.")

        # 2. Text validation
        if not topic or not str(topic).strip():
            raise ValidationError("topic is required.")
        if not claim or not str(claim).strip():
            raise ValidationError("claim is required.")
        if not verification_source or not str(verification_source).strip():
            raise ValidationError("verification_source is required.")

        topic = str(topic).strip()
        claim = str(claim).strip()
        verification_source = str(verification_source).strip()

        # 3. PII screening
        for text in (topic, claim, verification_source, safety_guidance or ""):
            if EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text):
                raise ValidationError("Prohibited PII (email or phone number) detected in fact payload.")

        # 4. Safety-critical guidance enforcement
        if is_safety_critical:
            if not safety_guidance or not str(safety_guidance).strip():
                raise ValidationError("safety_guidance is mandatory when is_safety_critical is True.")
            safety_guidance = str(safety_guidance).strip()
        else:
            safety_guidance = str(safety_guidance).strip() if safety_guidance else None

        # 5. Deterministic ID calculation
        fact_id = _compute_deterministic_fact_id(target_id, topic, claim, verification_source)

        # 6. Idempotency & Conflict Check
        if fact_id in self._facts:
            existing = self._facts[fact_id]
            if (existing.is_safety_critical != is_safety_critical or
                existing.safety_guidance != safety_guidance or
                existing.validity_status != validity_status):
                raise ConflictError(f"Conflicting fact with ID '{fact_id}' already exists.")
            return existing

        created_at = datetime.now(timezone.utc).isoformat()

        record = CanonicalFactRecord(
            fact_id=fact_id,
            target_id=target_id,
            product_id=product_id,
            topic=topic,
            claim=claim,
            verification_source=verification_source,
            is_safety_critical=bool(is_safety_critical),
            safety_guidance=safety_guidance,
            validity_status=validity_status,
            version=version,
            created_at=created_at
        )

        self._facts[fact_id] = record
        if self.storage_path:
            self._save()

        return record

    def get_fact(self, fact_id: str) -> Optional[CanonicalFactRecord]:
        return self._facts.get(fact_id)

    def list_facts(
        self,
        target_id: Optional[str] = None,
        topic: Optional[str] = None,
        product_id: Optional[str] = None
    ) -> List[CanonicalFactRecord]:
        """Queries facts with optional filtering."""
        results = list(self._facts.values())
        if target_id:
            results = [f for f in results if f.target_id == target_id]
        if topic:
            results = [f for f in results if f.topic == topic]
        if product_id:
            results = [f for f in results if f.product_id == product_id]
        return results

    def get_safety_critical_facts(self, target_id: Optional[str] = None) -> List[CanonicalFactRecord]:
        """Returns all safety-critical facts."""
        facts = self.list_facts(target_id=target_id)
        return [f for f in facts if f.is_safety_critical]

    def _save(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._facts.items()}
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            self._facts[k] = CanonicalFactRecord(**v)
