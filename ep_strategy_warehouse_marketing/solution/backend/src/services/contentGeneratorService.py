from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.schemas.content_schema import (
    PLATFORM_LIMITS,
    CampaignAngle,
    CampaignAsset,
    ContentMatrixEntry,
    ContentType,
    Platform,
    PublishableContent,
    VariantContent,
)


DEFAULT_LANDING_PAGE_URL = "https://strategywarehouse.example.com/subscribe"
DEFAULT_HASHTAGS = ["#StrategyWarehouse", "#TradingSignals", "#AlgoTrading"]


@dataclass(frozen=True)
class PillarDefinition:
    pillar: str
    campaign_angle: CampaignAngle
    content_type: ContentType
    theme: str
    format_name: str
    target_platforms: tuple[Platform, ...]
    hook_style: str
    call_to_action: str


CONTENT_MATRIX: tuple[PillarDefinition, ...] = (
    PillarDefinition(
        pillar="daily_signal_edge",
        campaign_angle=CampaignAngle.MOMENTUM,
        content_type=ContentType.SIGNAL_ALERT,
        theme="Surface the strongest live mover with fast proof and a clear invite.",
        format_name="flash_signal_post",
        target_platforms=(Platform.TWITTER, Platform.DISCORD, Platform.TELEGRAM, Platform.TIKTOK),
        hook_style="Urgent momentum hook",
        call_to_action="Join the Strategy Warehouse list for the next live signal batch.",
    ),
    PillarDefinition(
        pillar="performance_recap",
        campaign_angle=CampaignAngle.RISK_DISCIPLINE,
        content_type=ContentType.PERFORMANCE_SUMMARY,
        theme="Translate snapshot data into disciplined weekly-style proof.",
        format_name="proof_of_process_post",
        target_platforms=(Platform.LINKEDIN, Platform.REDDIT, Platform.TWITTER, Platform.TIKTOK),
        hook_style="Measured proof hook",
        call_to_action="Get the operating notes and performance recap in the subscriber digest.",
    ),
    PillarDefinition(
        pillar="leaderboard_watch",
        campaign_angle=CampaignAngle.LEADERBOARD,
        content_type=ContentType.STRATEGY_RANKING,
        theme="Show ranked leaders and why the board is rotating.",
        format_name="leaderboard_carousel",
        target_platforms=(Platform.TWITTER, Platform.LINKEDIN, Platform.TIKTOK),
        hook_style="Competitive leaderboard hook",
        call_to_action="Subscribe to track when the leaderboard flips.",
    ),
    PillarDefinition(
        pillar="trader_education",
        campaign_angle=CampaignAngle.EDUCATION,
        content_type=ContentType.EDUCATIONAL,
        theme="Turn warehouse output into reusable explanations about risk and selection.",
        format_name="educational_breakdown",
        target_platforms=(Platform.LINKEDIN, Platform.REDDIT, Platform.DISCORD, Platform.TIKTOK),
        hook_style="Teach with one sharp lesson",
        call_to_action="Join for deeper breakdowns behind each strategy setup.",
    ),
)


class StrategyWarehouseDataLoader:
    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)

    def latest_snapshot_dir(self) -> Path:
        date_dirs = sorted(
            [path for path in self.base_path.iterdir() if path.is_dir()],
            reverse=True,
        )
        if not date_dirs:
            raise FileNotFoundError(f"No dated snapshot directories found in {self.base_path}")
        return date_dirs[0]

    def load_snapshot_bundle(self, snapshot_dir: str | Path | None = None) -> dict[str, Any]:
        target_dir = Path(snapshot_dir) if snapshot_dir else self.latest_snapshot_dir()
        bundle: dict[str, Any] = {}
        for file_name in ("_summary_net.json", "_frequency.json", "_dna_frequency.json"):
            file_path = target_dir / file_name
            with file_path.open("r", encoding="utf-8") as handle:
                bundle[file_name] = json.load(handle)
        bundle["snapshot_dir"] = str(target_dir)
        return bundle


class ContentGeneratorService:
    def __init__(
        self,
        template_dir: str | Path | None = None,
        landing_page_url: str = DEFAULT_LANDING_PAGE_URL,
    ) -> None:
        resolved_template_dir = (
            Path(template_dir)
            if template_dir
            else Path(__file__).resolve().parent.parent / "templates"
        )
        self.environment = Environment(
            loader=FileSystemLoader(str(resolved_template_dir)),
            autoescape=select_autoescape(enabled_extensions=("j2", "jinja2")),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.landing_page_url = landing_page_url

    def build_content_matrix(self) -> list[ContentMatrixEntry]:
        return [
            ContentMatrixEntry(
                pillar=definition.pillar,
                campaign_angle=definition.campaign_angle,
                content_type=definition.content_type,
                theme=definition.theme,
                format_name=definition.format_name,
                target_platforms=list(definition.target_platforms),
                hook_style=definition.hook_style,
                call_to_action=definition.call_to_action,
            )
            for definition in CONTENT_MATRIX
        ]

    def generate_campaign_bundle(self, warehouse_data: dict[str, Any]) -> dict[str, Any]:
        matrix = self.build_content_matrix()
        posts = [
            self._build_signal_alert(warehouse_data),
            self._build_performance_summary(warehouse_data),
            self._build_strategy_ranking(warehouse_data),
            self._build_educational_post(warehouse_data),
        ]
        return {
            "content_matrix": [entry.model_dump(mode="json") for entry in matrix],
            "generated_at": warehouse_data["_summary_net.json"]["last_update"],
            "source_snapshot_dir": warehouse_data["snapshot_dir"],
            "posts": [post.model_dump(mode="json") for post in posts],
        }

    def _build_signal_alert(self, warehouse_data: dict[str, Any]) -> PublishableContent:
        summary = warehouse_data["_summary_net.json"]
        strategy, product, point = self._best_signal(summary)
        body = self.environment.get_template("signal_alert.jinja2").render(
            hook="Momentum check:",
            strategy=self._shorten_strategy(strategy),
            product=product,
            net_points=self._format_points(point["net"]),
            directional_bias=self._directional_bias(point),
            proof_point=f"{point['b_c']} buys vs {point['s_c']} sells on the latest pass.",
        )
        headline = f"{product} setup presses {self._format_points(point['net'])} pts"
        return self._build_content_item(
            definition=CONTENT_MATRIX[0],
            headline=headline,
            body=body,
            hashtags=DEFAULT_HASHTAGS + [f"#{product}"],
            source_data={
                "strategy": strategy,
                "product": product,
                "latest_point": point,
            },
            campaign_assets=[
                CampaignAsset(
                    asset_type="quote_card",
                    title=f"{product} momentum card",
                    visual_brief=f"Highlight {product} net curve and current strategy label.",
                    callout="Fast signal, clear edge, direct CTA.",
                )
            ],
        )

    def _build_performance_summary(self, warehouse_data: dict[str, Any]) -> PublishableContent:
        frequency = warehouse_data["_frequency.json"]
        latest_snapshot = frequency["snapshots"][-1]
        top_leader = latest_snapshot["leaders"][0]
        body = self.environment.get_template("performance_summary.jinja2").render(
            lead_in="Discipline over noise:",
            winning_product=top_leader["product"],
            winning_net=self._format_points(top_leader["net"]),
            snapshot_count=frequency["snapshot_count"],
            risk_frame="The engine keeps publishing only when the board shows repeatable strength.",
        )
        headline = f"{top_leader['product']} leads {frequency['snapshot_count']} live checks"
        return self._build_content_item(
            definition=CONTENT_MATRIX[1],
            headline=headline,
            body=body,
            hashtags=DEFAULT_HASHTAGS + ["#RiskManagement"],
            source_data={
                "latest_snapshot_time": latest_snapshot["time"],
                "leader": top_leader,
                "snapshot_count": frequency["snapshot_count"],
            },
            campaign_assets=[
                CampaignAsset(
                    asset_type="carousel",
                    title="Performance recap carousel",
                    visual_brief="Slide 1 headline, slide 2 snapshot count, slide 3 why discipline matters.",
                    callout="Proof without overclaiming.",
                )
            ],
        )

    def _build_strategy_ranking(self, warehouse_data: dict[str, Any]) -> PublishableContent:
        dna_frequency = warehouse_data["_dna_frequency.json"]
        latest_snapshot = dna_frequency["snapshots"][-1]
        leaders = [
            f"{leader['rank']}. {leader['product']} ({self._format_points(leader['net'])})"
            for leader in latest_snapshot["leaders"][:3]
        ]
        body = self.environment.get_template("strategy_ranking.jinja2").render(
            lead_in="Leaderboard watch:",
            leaders=leaders,
            takeaway="Rotation matters more than hype. Watch which names stay on the board.",
        )
        headline = "DNA leaderboard rotation is tightening"
        return self._build_content_item(
            definition=CONTENT_MATRIX[2],
            headline=headline,
            body=body,
            hashtags=DEFAULT_HASHTAGS + ["#Leaderboard"],
            source_data={
                "latest_snapshot_time": latest_snapshot["time"],
                "leaders": latest_snapshot["leaders"][:5],
            },
            campaign_assets=[
                CampaignAsset(
                    asset_type="leaderboard_card",
                    title="Top 3 DNA strategies",
                    visual_brief="Three-column leaderboard with rank badges and point totals.",
                    callout="Show movement between yesterday and today.",
                )
            ],
        )

    def _build_educational_post(self, warehouse_data: dict[str, Any]) -> PublishableContent:
        frequency = warehouse_data["_frequency.json"]
        latest_snapshot = frequency["snapshots"][-1]
        leaders = latest_snapshot["leaders"][:2]
        leader_names = ", ".join(self._shorten_strategy(item["strategy"]) for item in leaders)
        body = (
            "What makes a strategy feed usable? "
            "Repeated snapshots, ranked leaders, and a clear filter for noise. "
            f"Today that means tracking {leader_names} and ignoring one-off spikes."
        )
        headline = "How to read a strategy board without chasing noise"
        return self._build_content_item(
            definition=CONTENT_MATRIX[3],
            headline=headline,
            body=body,
            hashtags=["#TradingEducation", "#StrategyWarehouse", "#ProcessOverPrediction"],
            source_data={
                "leaders": leaders,
                "lesson": "Use repeat snapshots to separate consistency from noise.",
            },
            campaign_assets=[
                CampaignAsset(
                    asset_type="script_outline",
                    title="Educational explainer",
                    visual_brief="30-second talking-head outline with one chart overlay.",
                    callout="Teach the filter, not the prediction.",
                )
            ],
        )

    def _build_content_item(
        self,
        definition: PillarDefinition,
        headline: str,
        body: str,
        hashtags: list[str],
        source_data: dict[str, Any],
        campaign_assets: list[CampaignAsset],
    ) -> PublishableContent:
        base_cta = definition.call_to_action
        platform_variants = self._build_platform_variants(
            headline=headline,
            body=body,
            hashtags=hashtags,
            call_to_action=base_cta,
            target_platforms=definition.target_platforms,
        )
        return PublishableContent(
            content_type=definition.content_type,
            campaign_angle=definition.campaign_angle,
            pillar=definition.pillar,
            format_name=definition.format_name,
            headline=self._trim(headline, PLATFORM_LIMITS[Platform.TWITTER]["headline"]),
            body=self._trim(body, PLATFORM_LIMITS[Platform.TWITTER]["body"]),
            hashtags=hashtags[: PLATFORM_LIMITS[Platform.TWITTER]["hashtags"]],
            call_to_action=base_cta,
            landing_page_url=self.landing_page_url,
            platform_variants=platform_variants,
            source_data=source_data,
            campaign_assets=campaign_assets,
        )

    def _build_platform_variants(
        self,
        headline: str,
        body: str,
        hashtags: list[str],
        call_to_action: str,
        target_platforms: tuple[Platform, ...],
    ) -> dict[Platform, VariantContent]:
        variants: dict[Platform, VariantContent] = {}
        for platform in target_platforms:
            limits = PLATFORM_LIMITS[platform]
            platform_tags = hashtags[: limits["hashtags"]]
            cta = self._trim(call_to_action, 160)
            if platform == Platform.REDDIT:
                variant_body = f"{body}\n\nCTA: {cta}"
            elif platform == Platform.DISCORD:
                variant_body = f"{body} {cta}"
            else:
                variant_body = f"{body} {' '.join(platform_tags)} {cta}".strip()
            variants[platform] = VariantContent(
                platform=platform,
                headline=self._trim(headline, limits["headline"]),
                body=self._trim(variant_body, limits["body"]),
                hashtags=platform_tags,
                call_to_action=cta,
            )
        return variants

    @staticmethod
    def _best_signal(summary: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        best_item: tuple[str, str, dict[str, Any]] | None = None
        for strategy, products in summary["strategies"].items():
            for product, points in products.items():
                if not points:
                    continue
                latest = points[-1]
                if best_item is None or latest["net"] > best_item[2]["net"]:
                    best_item = (strategy, product, latest)
        if best_item is None:
            raise ValueError("No strategy points available in summary feed")
        return best_item

    @staticmethod
    def _directional_bias(point: dict[str, Any]) -> str:
        if point["buy_net"] > point["sell_net"]:
            return "buy-led"
        if point["sell_net"] > point["buy_net"]:
            return "sell-led"
        return "balanced"

    @staticmethod
    def _trim(text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."

    @staticmethod
    def _shorten_strategy(strategy: str) -> str:
        return strategy.replace("breakout_", "brk_").replace("_", " ")

    @staticmethod
    def _format_points(value: float) -> str:
        rounded = round(value, 1)
        return f"{rounded:+g}"
