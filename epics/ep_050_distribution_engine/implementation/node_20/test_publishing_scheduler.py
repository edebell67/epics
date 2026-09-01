# epics/ep_050_distribution_engine/implementation/node_20/test_publishing_scheduler.py — Consolidated offline Node 19-to-20 consumer regression suite.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds current-code negative and repository-conflict coverage for the required consolidation run.
# v1.0.0 · 2026-08-17 · Initial real Node 19-to-20 offline integration coverage.

"""Offline regression tests for canonical Node 19 -> Node 20 integration."""
from __future__ import annotations

import socket
import sys
import unittest
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve()
IMPL = HERE.parents[1]
sys.path.insert(0, str(IMPL / "node_19"))
from quality_compliance import evaluate_asset_compliance  # noqa: E402
from publishing_scheduler import (  # noqa: E402
    InMemoryMockPublicationRepository,
    PublicationPlanConflictError,
    PublicationPlanValidationError,
    build_mock_publication_plan,
    create_mock_publication_plan,
)


class Node19ToNode20IntegrationTest(unittest.TestCase):
    """Uses actual Node 19 output while blocking all socket construction."""

    def setUp(self) -> None:
        self._socket = socket.socket
        socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network prohibited"))
        source = {
            "asset_id": "asset_node19_live_001",
            "target_id": "target_boiler_repair_blackheath",
            "opportunity_id": "opp_node19_live_001",
            "title": "Safe Boiler Pressure Guide",
            "body_content": "Check the gauge safely.\nConsult a qualified engineer.",
            "safety_disclaimer": "SAFETY: Gas Safe guidance requires qualified inspection.",
            "call_to_action": "Request a diagnostic quote.",
            "fact_ids": ["fact_verified_001"],
            "metadata": {"channel": "search_landing", "external_action": False},
            "created_at": "2026-08-17T06:20:00+01:00",
        }
        result, package = evaluate_asset_compliance(source)
        self.assertTrue(result.approved)
        self.assertIsNotNone(package)
        self.package = package

    def tearDown(self) -> None:
        socket.socket = self._socket

    def test_real_node_19_output_creates_canonical_mock_plan(self) -> None:
        plan = create_mock_publication_plan(self.package)
        self.assertEqual("1.1.0", plan["schema_version"])
        self.assertEqual(self.package.asset_id, plan["asset_id"])
        self.assertEqual("approved", plan["approval_state"])
        self.assertIs(False, plan["external_action"])
        self.assertTrue(plan["publication_plan_id"].startswith("mpp_"))

    def test_real_node_19_output_is_idempotent(self) -> None:
        repository = InMemoryMockPublicationRepository()
        self.assertEqual(
            create_mock_publication_plan(self.package, repository),
            create_mock_publication_plan(self.package, repository),
        )

    def test_lineage_mismatch_fails_closed(self) -> None:
        unsafe = self.package.to_dict()
        unsafe["cta_definition"] = deepcopy(unsafe["cta_definition"])
        unsafe["cta_definition"]["tracking_params"]["asset_id"] = "different_asset"
        with self.assertRaisesRegex(PublicationPlanValidationError, "tracking asset_id"):
            create_mock_publication_plan(unsafe)

    def test_non_test_destination_fails_closed(self) -> None:
        unsafe = self.package.to_dict()
        unsafe["cta_definition"] = deepcopy(unsafe["cta_definition"])
        unsafe["cta_definition"]["destination_url"] = "https://example.com/real"
        with self.assertRaises(PublicationPlanValidationError):
            create_mock_publication_plan(unsafe)

    def test_unapproved_compliance_fails_closed(self) -> None:
        unsafe = self.package.to_dict()
        unsafe["compliance_stamp"] = deepcopy(unsafe["compliance_stamp"])
        unsafe["compliance_stamp"]["approved"] = False
        with self.assertRaises(PublicationPlanValidationError):
            create_mock_publication_plan(unsafe)

    def test_invalid_timestamp_fails_closed(self) -> None:
        unsafe = self.package.to_dict()
        unsafe["generated_at"] = "not-a-timestamp"
        with self.assertRaises(PublicationPlanValidationError):
            create_mock_publication_plan(unsafe)

    def test_undeclared_schedule_channel_fails_closed(self) -> None:
        unsafe = self.package.to_dict()
        unsafe["schedule_request"] = deepcopy(unsafe["schedule_request"])
        unsafe["schedule_request"]["channel"] = "social_post"
        with self.assertRaises(PublicationPlanValidationError):
            create_mock_publication_plan(unsafe)

    def test_unexpected_package_property_fails_closed(self) -> None:
        unsafe = self.package.to_dict()
        unsafe["adapter"] = "publish"
        with self.assertRaises(PublicationPlanValidationError):
            create_mock_publication_plan(unsafe)

    def test_repository_conflict_fails_closed(self) -> None:
        repository = InMemoryMockPublicationRepository()
        plan = build_mock_publication_plan(self.package)
        repository.store(plan)
        conflicting = deepcopy(plan)
        conflicting["audience"] = "changed synthetic audience"
        with self.assertRaisesRegex(PublicationPlanConflictError, "conflicting record"):
            repository.store(conflicting)

    def test_non_mapping_package_fails_closed(self) -> None:
        with self.assertRaisesRegex(PublicationPlanValidationError, "mapping"):
            create_mock_publication_plan(object())


if __name__ == "__main__":
    unittest.main(verbosity=2)
