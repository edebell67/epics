# tests/test_postgres_integration.py — Real PostgreSQL repository integration test for EP054.
#
# VERSION HISTORY
# v1.0.0 · 2026-09-01 · Exercises portfolio, entry, score-run and hashed-invitation persistence on a disposable database.
from __future__ import annotations

import os
import unittest

import database
import server
from directory_client import EvidencePoint
from repository import FantasyRepository


class FakeDirectory:
    base_url = "https://ep051.example.test"
    latest_equity = 10.0

    def strategy(self, strategy_id):
        return {"as_of": "2026-09-01T10:00:00Z", "methodology_version": "1.0.0"}

    def evidence(self, strategy_id):
        return EvidencePoint(strategy_id, self.latest_equity, 4.0, 2, "2026-09-01T10:00:00Z", "2026-09-01T09:00:00Z", "costs included")


@unittest.skipUnless(os.environ.get("EP054_TEST_DATABASE_URL"), "disposable PostgreSQL URL not supplied")
class PostgreSQLRepositoryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = os.environ["EP054_TEST_DATABASE_URL"]
        database.apply_migrations()
        cls.previous_directory = server.directory
        cls.previous_repository = server.repository
        server.directory = FakeDirectory()
        server.repository = FantasyRepository()

    @classmethod
    def tearDownClass(cls):
        server.directory = cls.previous_directory
        server.repository = cls.previous_repository
        database.rollback_migration("001_fantasy_schema")
        if cls.previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = cls.previous_url

    def test_full_repository_flow_and_duplicate_reuse(self):
        payload = server.EntryCreate(email="integration@example.test", display_name="Integration", portfolio_name="Postgres Three", strategy_ids=["DNA_100001", "DNA_100002", "DNA_100003"])
        first = server.create_entry(payload)
        duplicate = server.create_entry(payload)
        self.assertEqual(first["portfolio_id"], duplicate["portfolio_id"])
        self.assertEqual(first["entry_id"], duplicate["entry_id"])
        self.assertTrue(duplicate["reused"])

        board = server.leaderboard(first["entry_id"])
        self.assertEqual(board["current"]["score"], 0.0)
        self.assertTrue(board["score_run_id"].startswith("SR_"))
        server.directory.latest_equity = 13.0
        advanced = server.leaderboard(first["entry_id"])
        self.assertAlmostEqual(advanced["current"]["score"], 3.0)

        invite = server.create_invitation(server.InvitationCreate(entry_id=first["entry_id"]))
        opened = server.open_invitation(invite["invite_token"])
        self.assertEqual(opened["status"], "OPENED")
        accepted = server.accept_invitation(invite["invite_token"], server.InvitationAccept(email="friend@example.test", display_name="Friend"))
        self.assertEqual(accepted["status"], "ACCEPTED")
        with database.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT token_hash FROM fantasy.invitations")
            stored = cursor.fetchone()["token_hash"]
        self.assertNotEqual(stored, invite["invite_token"])
        self.assertEqual(len(stored), 64)
