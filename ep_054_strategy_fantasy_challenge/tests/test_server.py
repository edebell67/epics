# tests/test_server.py — EP054 API contract tests with an infrastructure-free repository double.
#
# VERSION HISTORY
# v2.0.0 · 2026-09-01 · Removes SQLite tests and verifies repository-backed portfolio, scoring and hashed-invitation flows.
# v1.0.0 · 2026-08-31 · Verifies persistent MVP entry, ranking and invitation contracts.
from __future__ import annotations

import hashlib
import secrets
import unittest
from datetime import timedelta

import server
from directory_client import EvidencePoint, StrategyDirectoryClient


class DirectoryCurrentDateTests(unittest.TestCase):
    def test_catalogue_queries_only_the_current_utc_date(self):
        client = StrategyDirectoryClient("https://example.test")
        captured = {}

        def fake_get(path, query):
            captured.update(query)
            return {"data": {"items": [{"strategy_id": "DNA_NOW"}], "total": 1}, "as_of": "now", "methodology_version": "1", "basis": "net"}

        client._get = fake_get
        result = client.catalogue()
        self.assertEqual(captured["date_from"], client.current_trading_date())
        self.assertEqual(captured["date_to"], client.current_trading_date())
        self.assertEqual(result["activity_date"], client.current_trading_date())


class FakeDirectory:
    base_url = "https://ep051.example.test"
    ids = {"DNA_100001", "DNA_100002", "DNA_100003"}
    latest_equity = 10.0

    def catalogue(self, page_size=100):
        return {"items": [{"strategy_id": value, "descriptive_name": value, "total_trades": 2, "total_net_return": 10.0, "evidence_end": "2026-08-31T12:00:00Z", "quality_state": "VALID"} for value in sorted(self.ids)], "as_of": "2026-08-31T12:00:00Z", "methodology_version": "1.0.0", "basis": "costs included", "total": 3, "activity_date": "2026-08-31"}

    def strategy(self, strategy_id):
        if strategy_id not in self.ids:
            raise RuntimeError("ineligible")
        return {"item": {"strategy_id": strategy_id}, "as_of": "2026-08-31T12:00:00Z", "methodology_version": "1.0.0", "basis": "costs included"}

    def evidence(self, strategy_id):
        return EvidencePoint(strategy_id, self.latest_equity, 4.0, 2, "2026-08-31T12:00:00Z", "2026-08-31T11:00:00Z", "costs included")


class MemoryRepository:
    def __init__(self):
        self.entries = {}
        self.invitations = {}
        self.score_runs = []

    def ping(self):
        return None

    def create_entry(self, **values):
        entry_id = "ENT_TEST"
        self.entries[entry_id] = {
            "entry_id": entry_id,
            "portfolio_name": values["portfolio_name"],
            "display_name": values["display_name"],
            "baselines": [{"entry_id": entry_id, "strategy_id": point.strategy_id, "weight": 1 / len(values["baseline_points"]), "baseline_equity": point.equity, "evidence_ref": point.evidence_ref} for point in values["baseline_points"]],
        }
        return {"entry_id": entry_id, "player_id": "PLY_TEST", "portfolio_id": "PF_TEST", "portfolio_revision": 1, "entry_timestamp": values["timestamp"], "reused": False}

    def active_entries(self, challenge_id):
        return [{key: value[key] for key in ("entry_id", "portfolio_name", "display_name")} for value in self.entries.values()]

    def entry_strategies(self, entry_id):
        return self.entries[entry_id]["baselines"]

    def record_score_run(self, challenge_id, scoring_version, source_version, calculated_at, rows):
        self.score_runs.append(rows)
        return "SR_TEST"

    def create_invitation(self, entry_id, now):
        if entry_id not in self.entries:
            return None
        token = secrets.token_urlsafe(24)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.invitations[token_hash] = {"competition_id": server.CHALLENGE_ID, "inviter_entry_id": entry_id, "expires_at": now + timedelta(days=7), "status": "CREATED"}
        return {"invitation_id": "INV_TEST", "invite_token": token, "entry_id": entry_id, "challenge_id": server.CHALLENGE_ID, "created_at": now, "expires_at": now + timedelta(days=7), "status": "CREATED"}

    def open_invitation(self, token, now):
        invite = self.invitations.get(hashlib.sha256(token.encode()).hexdigest())
        if not invite:
            return None
        invite["status"] = "OPENED"
        entry = self.entries[invite["inviter_entry_id"]]
        return {**invite, "portfolio_name": entry["portfolio_name"], "display_name": entry["display_name"], "score": 0.0}

    def accept_invitation(self, token, email, display_name, now):
        invite = self.invitations.get(hashlib.sha256(token.encode()).hexdigest())
        if not invite or invite["status"] == "ACCEPTED":
            return None
        invite["status"] = "ACCEPTED"
        return {**invite, "player_id": "PLY_FRIEND"}


class MvpApiContractTests(unittest.TestCase):
    def setUp(self):
        self.original_directory = server.directory
        self.original_repository = server.repository
        server.directory = FakeDirectory()
        server.repository = MemoryRepository()

    def tearDown(self):
        server.directory = self.original_directory
        server.repository = self.original_repository

    def test_entry_leaderboard_and_invitation_lifecycle(self):
        entry = server.create_entry(server.EntryCreate(email="player@example.test", display_name="Player One", portfolio_name="Three Signals", strategy_ids=["DNA_100001", "DNA_100002", "DNA_100003"]))
        self.assertEqual(entry["challenge_id"], server.CHALLENGE_ID)
        self.assertEqual(entry["portfolio_id"], "PF_TEST")
        self.assertTrue(entry["baseline_version"].startswith("EP051:1.0.0:"))
        board = server.leaderboard(entry["entry_id"])
        self.assertEqual(board["score_run_id"], "SR_TEST")
        self.assertEqual(board["current"]["score"], 0.0)
        server.directory.latest_equity = 13.0
        advanced = server.leaderboard(entry["entry_id"])
        self.assertAlmostEqual(advanced["current"]["score"], 3.0)

        invite = server.create_invitation(server.InvitationCreate(entry_id=entry["entry_id"]))
        token_hash = hashlib.sha256(invite["invite_token"].encode()).hexdigest()
        self.assertIn(token_hash, server.repository.invitations)
        self.assertNotIn(invite["invite_token"], server.repository.invitations)
        opened = server.open_invitation(invite["invite_token"])
        self.assertEqual(opened["status"], "OPENED")
        accepted = server.accept_invitation(invite["invite_token"], server.InvitationAccept(email="friend@example.test", display_name="Friend"))
        self.assertEqual(accepted["status"], "ACCEPTED")

    def test_entry_requires_three_unique_eligible_strategies(self):
        with self.assertRaises(Exception):
            server.create_entry(server.EntryCreate(email="small@example.test", display_name="Small", portfolio_name="Too Small", strategy_ids=["DNA_100001"]))


if __name__ == "__main__":
    unittest.main()
