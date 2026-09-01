# epics/ep_050_distribution_engine/implementation/node_32/test_performance_warehouse.py
# EP050 Node 32 — Performance Warehouse Test Suite.

from __future__ import annotations

import pytest
from performance_warehouse import (
    PerformanceWarehouseValidationError,
    build_performance_record,
    derive_performance_record_id,
)


def test_build_performance_record_success():
    res = build_performance_record(
        target_id="tgt_boiler_repair_blackheath",
        opportunity_id="opp_diagnostic_quote_001",
        channel="search_landing",
        impressions=1000,
        clicks=50,
        leads_captured=5,
        jobs_won=3,
        revenue_realized_gbp=750.0,
        cost_gbp=50.0,
    )
    assert res["schema_version"] == "1.0.0"
    assert res["performance_record_id"].startswith("pwr_")
    assert res["metrics"]["click_through_rate"] == 0.05
    assert res["metrics"]["return_on_ad_spend"] == 15.0


def test_missing_required_ids_rejected():
    with pytest.raises(PerformanceWarehouseValidationError):
        build_performance_record(target_id="", opportunity_id="opp_1", channel="search")
