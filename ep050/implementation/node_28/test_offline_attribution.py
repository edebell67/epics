"""Offline Node 19→20→21→26→27→28 regression; socket construction is prohibited."""
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
for node in ("node_19", "node_20", "node_21", "node_26", "node_27", "node_28"):
    sys.path.insert(0, str(IMPL / node))

from quality_compliance import evaluate_asset_compliance
from publishing_scheduler import build_mock_publication_plan
from search_distribution import build_search_distribution_package
from smart_destination_router import build_route_recommendation
from structured_lead_capture import build_structured_lead_record
from offline_attribution import (
    AttributionConflictError,
    AttributionValidationError,
    LocalAttributionRepository,
    build_attribution_record,
)


class OfflineAttributionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.socket = socket.socket
        socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("network prohibited")
        )
        source = json.loads((IMPL / "node_21" / "fixtures" / "approved_search_asset_fixture.json").read_text())
        result, package = evaluate_asset_compliance(source)
        self.assertTrue(result.approved)
        plan = build_mock_publication_plan(package.to_dict())
        search = build_search_distribution_package(plan, package.to_dict())
        context = {
            "topic": "Safe Boiler Pressure Guide", "intent": "diagnostic_quote",
            "geography": "Blackheath", "service": "boiler_repair", "channel": "search_landing",
            "asset_id": plan["asset_id"], "target_id": plan["target_id"],
            "opportunity_id": plan["opportunity_id"], "external_action": False,
            "deferred_channel_context": {"22": "deferred", "23": "deferred", "24": "deferred", "25": "deferred"},
        }
        route = build_route_recommendation(plan, package.to_dict(), search, context)
        intake = json.loads((IMPL / "node_27" / "fixtures" / "approved_structured_lead_capture_fixture.json").read_text())
        self.lead = build_structured_lead_record(route, {name: intake[name] for name in ("session_id", "source", "consent")})
        fixture = json.loads((HERE.parent / "fixtures" / "approved_offline_attribution_fixture.json").read_text())
        self.model = fixture["attribution_model"]

    def tearDown(self) -> None:
        socket.socket = self.socket

    def record(self) -> dict:
        return build_attribution_record(self.lead, self.model)

    def test_real_node19_to_28_integration_and_lineage(self) -> None:
        record = self.record()
        self.assertTrue(record["attribution_id"].startswith("atr_"))
        self.assertIs(record["external_action"], False)
        self.assertEqual(record["lead_id"], self.lead["lead_id"])
        self.assertEqual(record["consent"], self.lead["consent"])
        self.assertEqual(record["route_context"]["route_id"], self.lead["acquisition"]["route_id"])
        self.assertEqual(record["lineage"]["asset_id"], self.lead["acquisition"]["asset_id"])

    def test_deterministic(self) -> None:
        self.assertEqual(self.record(), self.record())

    def test_persistence_and_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalAttributionRepository(Path(directory))
            self.assertEqual(repository.store(self.record()), repository.store(self.record()))
            persisted = list(Path(directory).glob("atr_*.json"))
            self.assertEqual(len(persisted), 1)
            self.assertEqual(json.loads(persisted[0].read_text()), self.record())

    def test_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = LocalAttributionRepository(Path(directory))
            repository.store(self.record())
            changed = deepcopy(self.record())
            changed["source"] = "other"
            with self.assertRaises(AttributionConflictError):
                repository.store(changed)

    def test_rejects_missing_consent_and_broken_lineage(self) -> None:
        missing_consent = deepcopy(self.lead)
        missing_consent["consent"]["granted"] = False
        broken_lineage = deepcopy(self.lead)
        del broken_lineage["acquisition"]["asset_id"]
        for lead in (missing_consent, broken_lineage):
            with self.assertRaises(AttributionValidationError):
                build_attribution_record(lead, self.model)

    def test_rejects_pii_non_test_ambiguous_model_and_execution(self) -> None:
        pii = deepcopy(self.lead)
        pii["session_id"] = "person@example.test"
        non_test = deepcopy(self.lead)
        non_test["acquisition"]["destination_url"] = "https://example.com/book"
        executing = deepcopy(self.lead)
        executing["external_action"] = True
        for lead, model in ((pii, self.model), (non_test, self.model), (executing, self.model), (self.lead, {"name": "unknown", "version": "1.0.0", "confidence": 1.0}), (self.lead, {"name": "deterministic_last_verified_touch", "version": "1.0.0", "confidence": 1.0, "extra": "ambiguity"})):
            with self.assertRaises(AttributionValidationError):
                build_attribution_record(lead, model)


if __name__ == "__main__":
    unittest.main()
