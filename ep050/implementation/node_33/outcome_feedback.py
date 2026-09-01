# epics/ep_050_distribution_engine/implementation/node_33/outcome_feedback.py
# EP050 Node 33 — Outcome Feedback Ingestion & Normalizer.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial normalized outcome feedback ingestion from CRM, booking, invoicing, and client satisfaction signals.

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

FEEDBACK_VERSION = "outcome_feedback_v1.0.0"
SUPPORTED_FEEDBACK_SOURCES = frozenset({"crm_sync", "client_portal", "technician_app", "accounting_webhook"})


class OutcomeFeedbackValidationError(ValueError):
    """Raised when feedback input cannot be safely normalized."""


def derive_feedback_id(lead_id: str, source: str) -> str:
    key = f"{lead_id}:{source}"
    return "ofb_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def ingest_outcome_feedback(
    *,
    lead_id: str,
    target_id: str,
    feedback_source: str,
    job_status: str = "completed_satisfied",
    customer_rating: int = 5,
    actual_invoice_gbp: float = 240.0,
    technician_notes: str = "Standard repressurization and pressure relief valve replacement.",
) -> dict[str, Any]:
    """Ingest and validate real-world outcome feedback."""
    if not lead_id or not target_id:
        raise OutcomeFeedbackValidationError("lead_id and target_id are required")

    source = feedback_source.lower().strip()
    if source not in SUPPORTED_FEEDBACK_SOURCES:
        raise OutcomeFeedbackValidationError(
            f"feedback_source must be one of {sorted(SUPPORTED_FEEDBACK_SOURCES)}, got {source!r}"
        )

    return {
        "schema_version": "1.0.0",
        "feedback_id": derive_feedback_id(lead_id, source),
        "lead_id": lead_id,
        "target_id": target_id,
        "feedback_source": source,
        "outcome": {
            "job_status": job_status,
            "customer_rating": max(1, min(5, customer_rating)),
            "actual_invoice_gbp": round(float(actual_invoice_gbp), 2),
            "summary_notes": technician_notes.strip(),
        },
        "ingested_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
