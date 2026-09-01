# epics/ep_050_distribution_engine/implementation/node_22/test_video_distribution.py
# EP050 Node 22 — Video Distribution Test Suite.

from __future__ import annotations

import json
from pathlib import Path
import pytest

from video_distribution import (
    VideoDistributionValidationError,
    build_video_distribution_package,
    derive_video_package_id,
    SUPPORTED_PLATFORMS,
)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_19"))
from quality_compliance import evaluate_asset_compliance

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "node_21"
    / "fixtures"
    / "approved_search_asset_fixture.json"
)


@pytest.fixture
def valid_package() -> dict:
    source = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    _, package = evaluate_asset_compliance(source)
    return package.to_dict()


def test_build_video_distribution_package_success(valid_package):
    pkg = build_video_distribution_package(valid_package, platform="youtube")
    assert pkg["schema_version"] == "1.0.0"
    assert pkg["platform"] == "youtube"
    assert pkg["video_package_id"].startswith("vdp_")
    assert "chapters" in pkg["video_payload"]
    assert "cta_overlay" in pkg["video_payload"]
    assert pkg["video_payload"]["cta_overlay"]["destination_url"] == valid_package["cta_definition"]["destination_url"]


def test_unsupported_platform_rejected(valid_package):
    with pytest.raises(VideoDistributionValidationError, match="platform must be one of"):
        build_video_distribution_package(valid_package, platform="unknown_tv")


def test_custom_chapters_and_tags(valid_package):
    custom_meta = {
        "tags": ["boiler", "london"],
        "chapters": [{"timestamp": "00:00", "title": "Start"}]
    }
    pkg = build_video_distribution_package(valid_package, platform="youtube_shorts", video_metadata=custom_meta)
    assert pkg["platform"] == "youtube_shorts"
    assert pkg["video_payload"]["tags"] == ["boiler", "london"]
    assert len(pkg["video_payload"]["chapters"]) == 1
