# epics/ep_050_distribution_engine/implementation/node_24/test_community_participation.py
# EP050 Node 24 — Community Participation Test Suite.

from __future__ import annotations

import json
from pathlib import Path
import pytest

from community_participation import (
    CommunityParticipationValidationError,
    build_community_participation_plan,
    derive_community_plan_id,
    SUPPORTED_COMMUNITIES,
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


def test_build_community_participation_plan_reddit(valid_package):
    plan = build_community_participation_plan(valid_package, community="reddit", target_thread_url="https://reddit.test/r/test_community/comments/test_thread")
    assert plan["schema_version"] == "1.0.0"
    assert plan["community"] == "reddit"
    assert plan["community_plan_id"].startswith("cpp_")
    assert plan["response_payload"]["requires_human_approval"] is True
    assert plan["response_payload"]["non_promotional_compliance_score"] >= 0.90


def test_invalid_community_rejected(valid_package):
    with pytest.raises(CommunityParticipationValidationError, match="community must be one of"):
        build_community_participation_plan(valid_package, community="unmoderated_chat", target_thread_url="https://reddit.test/r/test_community/comments/test_thread")
