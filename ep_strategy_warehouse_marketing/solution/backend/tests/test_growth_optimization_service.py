import logging
import os
# Use proper src package imports
from src.services.growthOptimizationService import GrowthOptimizationService


def _service() -> GrowthOptimizationService:
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "config",
        "growth_optimization_rules.yaml",
    )
    return GrowthOptimizationService(config_path)


def test_generate_recommendations_covers_content_channel_and_funnel_rules():
    service = _service()

    campaigns = [
        {
            "channel": "twitter",
            "content_theme": "trend_reversal",
            "impressions": 1200,
            "engagements": 12,
            "clicks": 10,
            "conversions": 1,
            "unsubscribes": 0,
            "cadence_per_week": 7,
            "fatigue_signals": 30,
        },
        {
            "channel": "linkedin",
            "content_theme": "case_study",
            "impressions": 1800,
            "engagements": 120,
            "clicks": 80,
            "conversions": 24,
            "unsubscribes": 0,
            "cadence_per_week": 3,
            "fatigue_signals": 12,
        },
    ]
    subscriber_funnel = {
        "landing_page_visitors": 240,
        "new_subscribers": 12,
    }

    recommendations = service.generate_recommendations(campaigns, subscriber_funnel)

    actions = {item["action"] for item in recommendations}
    assert "rotate_content_theme" in actions
    assert "reduce_channel_allocation" in actions
    assert "increase_channel_allocation" in actions
    assert "refresh_conversion_path" in actions


def test_run_cycle_limits_adjustments_and_logs_actions(caplog):
    service = _service()
    caplog.set_level(logging.INFO, logger="GrowthOptimizationService")

    campaigns = [
        {
            "channel": "twitter",
            "content_theme": "trend_reversal",
            "impressions": 1200,
            "engagements": 8,
            "clicks": 40,
            "conversions": 2,
            "unsubscribes": 1,
            "cadence_per_week": 7,
            "fatigue_signals": 200,
        },
        {
            "channel": "reddit",
            "content_theme": "weekly_breakdown",
            "impressions": 1100,
            "engagements": 18,
            "clicks": 20,
            "conversions": 1,
            "unsubscribes": 0,
            "cadence_per_week": 5,
            "fatigue_signals": 20,
        },
        {
            "channel": "linkedin",
            "content_theme": "case_study",
            "impressions": 2200,
            "engagements": 140,
            "clicks": 96,
            "conversions": 30,
            "unsubscribes": 0,
            "cadence_per_week": 3,
            "fatigue_signals": 8,
        },
    ]
    subscriber_funnel = {
        "landing_page_visitors": 310,
        "new_subscribers": 25,
    }

    summary = service.run_cycle(campaigns, subscriber_funnel)

    assert summary["recommendation_count"] >= summary["applied_adjustment_count"] >= 1
    assert summary["applied_adjustment_count"] == 3
    assert len(summary["applied_adjustments"]) == 3
    assert "Optimization action=" in caplog.text
