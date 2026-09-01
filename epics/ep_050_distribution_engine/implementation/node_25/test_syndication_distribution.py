# epics/ep_050_distribution_engine/implementation/node_25/test_syndication_distribution.py
# EP050 Node 25 — Syndication & Partner Placement Test Suite.

from __future__ import annotations

import json
from pathlib import Path
import pytest

from syndication_distribution import (
    SyndicationDistributionValidationError,
    build_syndication_distribution_package,
    derive_syndication_package_id,
    SUPPORTED_SYNDICATION_TYPES,
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


def test_build_syndication_distribution_package_directory(valid_package):
    pkg = build_syndication_distribution_package(valid_package, syndication_type="directory_listing")
    assert pkg["schema_version"] == "1.0.0"
    assert pkg["syndication_type"] == "directory_listing"
    assert pkg["syndication_package_id"].startswith("sdp_")
    assert pkg["syndication_payload"]["feed_ready"] is True
    assert "embed_code" in pkg["syndication_payload"]


def test_invalid_syndication_type_rejected(valid_package):
    with pytest.raises(SyndicationDistributionValidationError, match="syndication_type must be one of"):
        build_syndication_distribution_package(valid_package, syndication_type="unverified_ad_network")
