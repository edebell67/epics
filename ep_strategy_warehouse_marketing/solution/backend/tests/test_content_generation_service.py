from __future__ import annotations

from pathlib import Path

from src.schemas.content_schema import CampaignAngle, ContentType, Platform
from src.services.contentGeneratorService import ContentGeneratorService


def sample_warehouse_bundle() -> dict:
    return {
        "snapshot_dir": "synthetic/2026-03-18",
        "_summary_net.json": {
            "last_update": "2026-03-18T18:27:26.421368",
            "strategies": {
                "breakout_R_Rev_4_tp10.0_sl5.0": {
                    "EUR": [
                        {
                            "t": "2026-03-18T13:37:32.591957",
                            "net": 245.0,
                            "buy_net": 180.0,
                            "sell_net": 65.0,
                            "b_c": 3,
                            "s_c": 1,
                        }
                    ]
                }
            },
        },
        "_frequency.json": {
            "date": "2026-03-18",
            "snapshot_count": 206,
            "snapshots": [
                {
                    "time": "2026-03-18T17:20:00",
                    "leaders": [
                        {
                            "rank": 1,
                            "score_rank": 1,
                            "score": 11.0,
                            "product": "SOL",
                            "strategy": "breakout_2_tp20.0_sl20.0",
                            "net": 195.0,
                        }
                    ],
                }
            ],
        },
        "_dna_frequency.json": {
            "date": "2026-03-18",
            "snapshot_count": 215,
            "snapshots": [
                {
                    "time": "2026-03-18T17:55:00",
                    "leaders": [
                        {
                            "rank": 1,
                            "product": "DNA_105009_CAD",
                            "strategy": "EVENT-S-FLIP-T_tp348.00_sl53.00",
                            "net": 90.0,
                        },
                        {
                            "rank": 2,
                            "product": "DNA_105026_CAD",
                            "strategy": "BUCKET-S-TGT-P_tp437.00_sl54.00",
                            "net": 85.0,
                        },
                        {
                            "rank": 3,
                            "product": "DNA_105119_CAD",
                            "strategy": "BRK-S-DUR-TS_tp418.00_sl52.00",
                            "net": 80.0,
                        },
                    ],
                }
            ],
        },
    }


def test_build_content_matrix_covers_multiple_campaign_angles() -> None:
    service = ContentGeneratorService()

    matrix = service.build_content_matrix()

    assert len(matrix) == 4
    assert {entry.campaign_angle for entry in matrix} == {
        CampaignAngle.MOMENTUM,
        CampaignAngle.RISK_DISCIPLINE,
        CampaignAngle.LEADERBOARD,
        CampaignAngle.EDUCATION,
    }
    assert {entry.content_type for entry in matrix} == {
        ContentType.SIGNAL_ALERT,
        ContentType.PERFORMANCE_SUMMARY,
        ContentType.STRATEGY_RANKING,
        ContentType.EDUCATIONAL,
    }
    assert all(Platform.TIKTOK in entry.target_platforms for entry in matrix)


def test_generate_campaign_bundle_returns_repeatable_valid_posts() -> None:
    service = ContentGeneratorService(
        template_dir=Path(__file__).resolve().parents[1] / "src" / "templates"
    )

    bundle = service.generate_campaign_bundle(sample_warehouse_bundle())

    assert bundle["generated_at"] == "2026-03-18T18:27:26.421368"
    assert bundle["source_snapshot_dir"] == "synthetic/2026-03-18"
    assert len(bundle["content_matrix"]) == 4
    assert len(bundle["posts"]) == 4

    first_post = bundle["posts"][0]
    assert first_post["content_type"] == ContentType.SIGNAL_ALERT.value
    assert Platform.TWITTER.value in first_post["platform_variants"]
    assert Platform.TIKTOK.value in first_post["platform_variants"]
    assert len(first_post["campaign_assets"]) == 1
    assert first_post["headline"]
