# epics/ep_050_distribution_engine/implementation/node_32/performance_warehouse.py
# EP050 Node 32 — Unified Performance Data Warehouse.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial unified multidimensional performance dataset model combining acquisition, distribution cost, response rate, conversion, and revenue metrics.

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

WAREHOUSE_VERSION = "performance_warehouse_v1.0.0"


class PerformanceWarehouseValidationError(ValueError):
    """Raised when records cannot safely join into the unified performance warehouse."""


def derive_performance_record_id(opportunity_id: str, channel: str) -> str:
    key = f"{opportunity_id}:{channel}"
    return "pwr_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def build_performance_record(
    *,
    target_id: str,
    opportunity_id: str,
    channel: str,
    impressions: int = 1200,
    clicks: int = 84,
    leads_captured: int = 6,
    leads_qualified: int = 5,
    jobs_won: int = 4,
    revenue_realized_gbp: float = 960.0,
    cost_gbp: float = 42.0,
) -> dict[str, Any]:
    """Compile an integrated multidimensional performance metric row."""
    if not target_id or not opportunity_id or not channel:
        raise PerformanceWarehouseValidationError("target_id, opportunity_id, and channel are required")

    ctr = round(clicks / max(1, impressions), 4)
    conv_rate = round(jobs_won / max(1, clicks), 4)
    cpa = round(cost_gbp / max(1, leads_captured), 2)
    roas = round(revenue_realized_gbp / max(0.01, cost_gbp), 2)

    return {
        "schema_version": "1.0.0",
        "performance_record_id": derive_performance_record_id(opportunity_id, channel),
        "target_id": target_id,
        "opportunity_id": opportunity_id,
        "channel": channel,
        "metrics": {
            "impressions": impressions,
            "clicks": clicks,
            "leads_captured": leads_captured,
            "leads_qualified": leads_qualified,
            "jobs_won": jobs_won,
            "revenue_realized_gbp": round(float(revenue_realized_gbp), 2),
            "cost_gbp": round(float(cost_gbp), 2),
            "click_through_rate": ctr,
            "conversion_rate": conv_rate,
            "cost_per_acquisition_gbp": cpa,
            "return_on_ad_spend": roas,
        },
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
