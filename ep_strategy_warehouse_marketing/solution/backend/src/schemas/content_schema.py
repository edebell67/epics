from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContentType(str, Enum):
    SIGNAL_ALERT = "signal_alert"
    PERFORMANCE_SUMMARY = "performance_summary"
    STRATEGY_RANKING = "strategy_ranking"
    EDUCATIONAL = "educational"


class CampaignAngle(str, Enum):
    MOMENTUM = "momentum"
    RISK_DISCIPLINE = "risk_discipline"
    LEADERBOARD = "leaderboard"
    EDUCATION = "education"


class Platform(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    REDDIT = "reddit"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    TIKTOK = "tiktok"


PLATFORM_LIMITS: dict[Platform, dict[str, int]] = {
    Platform.TWITTER: {"headline": 100, "body": 280, "hashtags": 4},
    Platform.LINKEDIN: {"headline": 150, "body": 3000, "hashtags": 6},
    Platform.REDDIT: {"headline": 300, "body": 40000, "hashtags": 0},
    Platform.DISCORD: {"headline": 120, "body": 2000, "hashtags": 4},
    Platform.TELEGRAM: {"headline": 120, "body": 1024, "hashtags": 5},
    Platform.TIKTOK: {"headline": 120, "body": 2200, "hashtags": 6},
}


class VariantContent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    platform: Platform
    headline: str = Field(min_length=1)
    body: str = Field(min_length=1)
    hashtags: list[str] = Field(default_factory=list)
    call_to_action: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def validate_platform_limits(self) -> "VariantContent":
        limits = PLATFORM_LIMITS[self.platform]
        if len(self.headline) > limits["headline"]:
            raise ValueError(
                f"{self.platform} headline exceeds {limits['headline']} characters"
            )
        if len(self.body) > limits["body"]:
            raise ValueError(
                f"{self.platform} body exceeds {limits['body']} characters"
            )
        if len(self.hashtags) > limits["hashtags"]:
            raise ValueError(
                f"{self.platform} hashtag count exceeds {limits['hashtags']}"
            )
        return self


class CampaignAsset(BaseModel):
    asset_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=140)
    visual_brief: str = Field(min_length=1, max_length=280)
    callout: str = Field(min_length=1, max_length=180)


class PublishableContent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    content_id: UUID = Field(default_factory=uuid4)
    content_type: ContentType
    campaign_angle: CampaignAngle
    pillar: str = Field(min_length=1, max_length=80)
    format_name: str = Field(min_length=1, max_length=80)
    headline: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=280)
    media_urls: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    call_to_action: str = Field(min_length=1, max_length=160)
    landing_page_url: str = Field(min_length=1, max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scheduled_for: datetime | None = None
    platform_variants: dict[Platform, VariantContent] = Field(default_factory=dict)
    source_data: dict[str, Any] = Field(default_factory=dict)
    campaign_assets: list[CampaignAsset] = Field(default_factory=list)

    @field_validator("hashtags")
    @classmethod
    def validate_hashtags(cls, hashtags: list[str]) -> list[str]:
        for tag in hashtags:
            if not tag.startswith("#"):
                raise ValueError("hashtags must start with #")
        return hashtags

    @model_validator(mode="after")
    def validate_variant_platforms(self) -> "PublishableContent":
        for platform, variant in self.platform_variants.items():
            if variant.platform != platform:
                raise ValueError("platform_variants keys must match variant platform")
        return self


class ContentMatrixEntry(BaseModel):
    pillar: str = Field(min_length=1, max_length=80)
    campaign_angle: CampaignAngle
    content_type: ContentType
    theme: str = Field(min_length=1, max_length=140)
    format_name: str = Field(min_length=1, max_length=80)
    target_platforms: list[Platform] = Field(min_length=1)
    hook_style: str = Field(min_length=1, max_length=120)
    call_to_action: str = Field(min_length=1, max_length=160)
