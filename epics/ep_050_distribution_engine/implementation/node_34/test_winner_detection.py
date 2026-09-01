# epics/ep_050_distribution_engine/implementation/node_34/test_winner_detection.py
# EP050 Node 34 — Winner Detection Test Suite.

from __future__ import annotations

import pytest
from winner_detection import (
    WinnerDetectionValidationError,
    detect_winning_strategy,
    derive_winner_id,
)

SAMPLE_PERFORMANCE = {
    "schema_version": "1.0.0",
    "performance_record_id": "pwr_38c92a1b4f5e",
    "opportunity_id": "opp_diagnostic_quote_001",
    "channel": "search_landing",
    "metrics": {
        "return_on_ad_spend": 12.5,
        "conversion_rate": 0.06,
        "leads_captured": 8,
    }
}


def test_detect_winning_strategy_gold_tier():
    res = detect_winning_strategy(SAMPLE_PERFORMANCE)
    assert res["schema_version"] == "1.0.0"
    assert res["is_winner"] is True
    assert res["winner_id"].startswith("wnr_")
    assert res["performance_assessment"]["winner_tier"] == "gold"
    assert res["recommendation"] == "amplify_and_scale"


def test_detect_underperforming_strategy():
    underperforming = {
        "schema_version": "1.0.0",
        "performance_record_id": "pwr_bad_perf_01",
        "opportunity_id": "opp_low_roi",
        "channel": "unoptimized_banner",
        "metrics": {"return_on_ad_spend": 1.2, "conversion_rate": 0.005, "leads_captured": 1}
    }
    res = detect_winning_strategy(underperforming)
    assert res["is_winner"] is False
    assert res["performance_assessment"]["winner_tier"] == "underperforming"
