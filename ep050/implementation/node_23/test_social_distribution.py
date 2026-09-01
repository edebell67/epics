# epics/ep_050_distribution_engine/implementation/node_23/test_social_distribution.py
# EP050 Node 23 — Social Distribution Test Suite.

from __future__ import annotations

import json
from pathlib import Path
import pytest

from social_distribution import (
    SocialDistributionValidationError,
    build_social_distribution_package,
    derive_social_package_id,
    SUPPORTED_NETWORKS,
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


def test_build_social_distribution_package_linkedin(valid_package):
    pkg = build_social_distribution_package(valid_package, network="linkedin")
    assert pkg["schema_version"] == "1.0.0"
    assert pkg["network"] == "linkedin"
    assert pkg["social_package_id"].startswith("sdp_")
    assert len(pkg["social_payload"]["posts"]) == 1
    assert "hashtags" in pkg["social_payload"]


def test_build_social_distribution_package_twitter_threading(valid_package):
    pkg = build_social_distribution_package(valid_package, network="x_twitter")
    assert pkg["network"] == "x_twitter"
    assert len(pkg["social_payload"]["posts"]) >= 1


def test_invalid_network_rejected(valid_package):
    with pytest.raises(SocialDistributionValidationError, match="network must be one of"):
        build_social_distribution_package(valid_package, network="unknown_space")
