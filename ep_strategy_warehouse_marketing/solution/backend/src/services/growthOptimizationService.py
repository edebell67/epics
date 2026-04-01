from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml


class GrowthOptimizationService:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self.logger = logging.getLogger("GrowthOptimizationService")
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Growth optimization config not found: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
        self.logger.info("Loaded growth optimization rules from %s", self.config_path)
        return config

    def generate_recommendations(
        self,
        campaigns: list[dict[str, Any]],
        subscriber_funnel: dict[str, Any],
    ) -> list[dict[str, Any]]:
        thresholds = self.config.get("thresholds", {})
        minimums = self.config.get("global", {})
        actions = self.config.get("actions", {})
        preferences = self.config.get("channel_preferences", {})

        recommendations: list[dict[str, Any]] = []
        channel_scores: dict[str, list[float]] = {}

        for campaign in campaigns:
            impressions = float(campaign.get("impressions", 0))
            clicks = float(campaign.get("clicks", 0))
            engagements = float(campaign.get("engagements", 0))
            conversions = float(campaign.get("conversions", 0))
            unsubscribes = float(campaign.get("unsubscribes", 0))
            cadence = float(campaign.get("cadence_per_week", 0))
            fatigue_signals = float(campaign.get("fatigue_signals", 0))
            channel = str(campaign.get("channel", "unknown"))
            theme = str(campaign.get("content_theme", "general"))

            if impressions < float(minimums.get("min_impressions", 0)):
                continue

            engagement_rate = engagements / impressions if impressions else 0.0
            ctr = clicks / impressions if impressions else 0.0
            conversion_rate = conversions / clicks if clicks else 0.0
            unsubscribe_rate = unsubscribes / conversions if conversions else 0.0
            fatigue_rate = fatigue_signals / impressions if impressions else 0.0
            priority_weight = float(preferences.get(channel, {}).get("priority_weight", 1.0))

            channel_scores.setdefault(channel, []).append((engagement_rate + conversion_rate) * priority_weight)

            if engagement_rate < float(thresholds.get("engagement_rate_floor", 0.0)) and ctr < float(
                thresholds.get("click_through_rate_floor", 0.0)
            ):
                recommendations.append(
                    self._build_recommendation(
                        recommendation_type="content",
                        priority=94,
                        action_key="underperforming_content",
                        actions=actions,
                        target=theme,
                        metrics={
                            "channel": channel,
                            "engagement_rate": round(engagement_rate, 4),
                            "click_through_rate": round(ctr, 4),
                        },
                    )
                )

            if clicks >= float(minimums.get("min_clicks", 0)) and conversion_rate < float(
                thresholds.get("conversion_rate_floor", 0.0)
            ):
                recommendations.append(
                    self._build_recommendation(
                        recommendation_type="funnel",
                        priority=92,
                        action_key="weak_funnel",
                        actions=actions,
                        target=channel,
                        metrics={
                            "content_theme": theme,
                            "conversion_rate": round(conversion_rate, 4),
                            "clicks": int(clicks),
                        },
                    )
                )

            if unsubscribe_rate > float(thresholds.get("unsubscribe_rate_ceiling", 1.0)) or fatigue_rate > float(
                thresholds.get("cadence_fatigue_ceiling", 1.0)
            ):
                recommendations.append(
                    self._build_recommendation(
                        recommendation_type="cadence",
                        priority=96,
                        action_key="audience_fatigue",
                        actions=actions,
                        target=channel,
                        metrics={
                            "cadence_per_week": cadence,
                            "unsubscribe_rate": round(unsubscribe_rate, 4),
                            "fatigue_rate": round(fatigue_rate, 4),
                        },
                    )
                )

        for channel, scores in channel_scores.items():
            average_score = sum(scores) / len(scores)
            if average_score >= float(thresholds.get("engagement_rate_win", 0.0)) + float(
                thresholds.get("conversion_rate_floor", 0.0)
            ):
                recommendations.append(
                    self._build_recommendation(
                        recommendation_type="channel",
                        priority=90,
                        action_key="winning_channel",
                        actions=actions,
                        target=channel,
                        metrics={"channel_score": round(average_score, 4)},
                    )
                )
            elif average_score < float(thresholds.get("engagement_rate_floor", 0.0)) + float(
                thresholds.get("conversion_rate_floor", 0.0)
            ):
                recommendations.append(
                    self._build_recommendation(
                        recommendation_type="channel",
                        priority=88,
                        action_key="underperforming_channel",
                        actions=actions,
                        target=channel,
                        metrics={"channel_score": round(average_score, 4)},
                    )
                )

        visitors = float(subscriber_funnel.get("landing_page_visitors", 0))
        new_subscribers = float(subscriber_funnel.get("new_subscribers", 0))
        subscriber_conversion_rate = new_subscribers / visitors if visitors else 0.0
        if visitors >= float(minimums.get("min_visitors", 0)) and subscriber_conversion_rate < float(
            thresholds.get("conversion_rate_floor", 0.0)
        ):
            recommendations.append(
                self._build_recommendation(
                    recommendation_type="funnel",
                    priority=93,
                    action_key="weak_funnel",
                    actions=actions,
                    target="landing_page",
                    metrics={
                        "landing_page_visitors": int(visitors),
                        "subscriber_conversion_rate": round(subscriber_conversion_rate, 4),
                    },
                )
            )

        unique_recommendations = self._deduplicate(recommendations)
        return sorted(unique_recommendations, key=lambda item: item["priority"], reverse=True)

    def run_cycle(self, campaigns: list[dict[str, Any]], subscriber_funnel: dict[str, Any]) -> dict[str, Any]:
        recommendations = self.generate_recommendations(campaigns, subscriber_funnel)
        max_adjustments = int(self.config.get("global", {}).get("max_adjustments_per_cycle", len(recommendations)))
        applied_adjustments = recommendations[:max_adjustments]
        summary = {
            "recommendation_count": len(recommendations),
            "applied_adjustment_count": len(applied_adjustments),
            "applied_adjustments": applied_adjustments,
        }
        for adjustment in applied_adjustments:
            self.logger.info(
                "Optimization action=%s target=%s reason=%s",
                adjustment["action"],
                adjustment["target"],
                adjustment["reason"],
            )
        return summary

    def _build_recommendation(
        self,
        recommendation_type: str,
        priority: int,
        action_key: str,
        actions: dict[str, Any],
        target: str,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        action_config = actions.get(action_key, {})
        return {
            "type": recommendation_type,
            "priority": priority,
            "action": action_config.get("action", action_key),
            "target": target,
            "reason": action_config.get("reason", ""),
            "metrics": metrics,
        }

    def _deduplicate(self, recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduplicated: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for recommendation in recommendations:
            key = (
                recommendation["type"],
                recommendation["action"],
                recommendation["target"],
            )
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(recommendation)
        return deduplicated
