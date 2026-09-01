# epics/ep_050_distribution_engine/implementation/node_21/test_search_distribution.py — Offline regression coverage for Node 19→20→21 search packages.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Uses the versioned synthetic asset fixture so real Node 19→20→21 coverage is reproducible.
# v1.0.0 · 2026-08-17 · Initial real-lineage, fail-closed, persistence, determinism, and no-network regression coverage.

"""Offline tests for Search Distribution; socket construction is prohibited."""
from __future__ import annotations

import json
import socket
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve()
IMPL = HERE.parents[1]
sys.path.insert(0, str(IMPL / "node_19"))
sys.path.insert(0, str(IMPL / "node_20"))
sys.path.insert(0, str(IMPL / "node_21"))
from publishing_scheduler import build_mock_publication_plan  # noqa: E402
from quality_compliance import evaluate_asset_compliance  # noqa: E402
from search_distribution import (  # noqa: E402
    LocalSearchDistributionRepository,
    SearchDistributionConflictError,
    SearchDistributionValidationError,
    build_search_distribution_package,
    validate_search_distribution_inputs,
)


class Node19ToNode21SearchDistributionTest(unittest.TestCase):
    """Exercise actual local Node 19 and Node 20 producer outputs."""

    def setUp(self) -> None:
        self._socket = socket.socket
        socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network prohibited"))
        fixture = HERE.parent / "fixtures" / "approved_search_asset_fixture.json"
        source = json.loads(fixture.read_text(encoding="utf-8"))
        result, package = evaluate_asset_compliance(source)
        self.assertTrue(result.approved)
        self.approved = package.to_dict()
        self.plan = build_mock_publication_plan(self.approved)

    def tearDown(self) -> None:
        socket.socket = self._socket

    def test_real_node19_to_node20_to_node21_generation(self) -> None:
        package = build_search_distribution_package(self.plan, self.approved)
        manifest = package["manifest"]
        self.assertTrue(manifest["search_distribution_id"].startswith("sdp_"))
        self.assertIs(False, manifest["external_action"])
        self.assertEqual(8, len(package["artifacts"]))
        self.assertIn("SAFETY", package["artifacts"]["landing-page.md"])
        self.assertFalse(package["artifacts"]["sitemap-indexing-support.json"]["indexing_request"])

    def test_is_deterministic(self) -> None:
        self.assertEqual(
            build_search_distribution_package(self.plan, self.approved),
            build_search_distribution_package(self.plan, self.approved),
        )

    def test_local_persistence_and_idempotency(self) -> None:
        package = build_search_distribution_package(self.plan, self.approved)
        with tempfile.TemporaryDirectory() as temp:
            repo = LocalSearchDistributionRepository(Path(temp))
            first = repo.store(package)
            second = repo.store(package)
            self.assertEqual(first, second)
            folder = Path(temp) / package["manifest"]["search_distribution_id"]
            self.assertEqual(set(package["artifacts"]), {p.name for p in folder.iterdir()})
            persisted = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(package["manifest"], persisted)

    def test_repository_conflict_fails_closed(self) -> None:
        package = build_search_distribution_package(self.plan, self.approved)
        altered = deepcopy(package)
        altered["artifacts"]["article.md"] += "changed"
        with tempfile.TemporaryDirectory() as temp:
            repo = LocalSearchDistributionRepository(Path(temp))
            repo.store(package)
            with self.assertRaisesRegex(SearchDistributionConflictError, "conflicting record"):
                repo.store(altered)

    def test_non_test_destination_fails_closed(self) -> None:
        unsafe = deepcopy(self.approved)
        unsafe["cta_definition"]["destination_url"] = "https://example.com/real"
        with self.assertRaises(SearchDistributionValidationError):
            build_search_distribution_package(self.plan, unsafe)

    def test_external_action_request_fails_closed(self) -> None:
        unsafe = deepcopy(self.plan)
        unsafe["external_action"] = True
        with self.assertRaisesRegex(SearchDistributionValidationError, "exactly match"):
            validate_search_distribution_inputs(unsafe, self.approved)

    def test_broken_lineage_fails_closed(self) -> None:
        unsafe = deepcopy(self.plan)
        unsafe["cta"]["tracking_params"]["asset_id"] = "wrong"
        with self.assertRaises(SearchDistributionValidationError):
            build_search_distribution_package(unsafe, self.approved)

    def test_incomplete_compliance_fails_closed(self) -> None:
        unsafe = deepcopy(self.approved)
        unsafe["compliance_stamp"]["disclaimer_verified"] = False
        with self.assertRaises(SearchDistributionValidationError):
            build_search_distribution_package(self.plan, unsafe)

    def test_missing_disclaimer_fails_closed(self) -> None:
        unsafe = deepcopy(self.approved)
        unsafe["body_content"]["safety_disclaimer"] = ""
        with self.assertRaises(SearchDistributionValidationError):
            build_search_distribution_package(self.plan, unsafe)

    def test_missing_cta_fails_closed(self) -> None:
        unsafe = deepcopy(self.approved)
        unsafe["cta_definition"]["cta_label"] = ""
        with self.assertRaises(SearchDistributionValidationError):
            build_search_distribution_package(self.plan, unsafe)

    def test_malformed_schema_fails_closed(self) -> None:
        with self.assertRaisesRegex(SearchDistributionValidationError, "mapping"):
            build_search_distribution_package([], self.approved)

    def test_persisted_conflict_fails_closed(self) -> None:
        package = build_search_distribution_package(self.plan, self.approved)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / package["manifest"]["search_distribution_id"]
            folder.mkdir()
            (folder / "manifest.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(SearchDistributionConflictError):
                LocalSearchDistributionRepository(Path(temp)).store(package)


if __name__ == "__main__":
    unittest.main(verbosity=2)
