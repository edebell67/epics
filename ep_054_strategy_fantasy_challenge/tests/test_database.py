# tests/test_database.py — Static and configuration gates for EP054 PostgreSQL isolation.
#
# VERSION HISTORY
# v1.0.1 · 2026-09-01 · Checks forbidden shared-schema qualifiers rather than legitimate EP051 evidence-version text.
# v1.0.0 · 2026-09-01 · Proves DATABASE_URL fail-closed behavior and schema-qualified migration boundaries.
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class DatabaseBoundaryTests(unittest.TestCase):
    def test_database_url_rejects_missing_and_sqlite_values(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(database.DatabaseConfigurationError):
                database.database_url()
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///fantasy.db"}, clear=True):
            with self.assertRaises(database.DatabaseConfigurationError):
                database.database_url()

    def test_database_url_accepts_postgresql(self):
        value = "postgresql://ep054:test@database.example/epics"
        with patch.dict(os.environ, {"DATABASE_URL": value}, clear=True):
            self.assertEqual(database.database_url(), value)

    def test_migrations_are_isolated_and_reversible(self):
        root = Path(database.__file__).parent
        up = (root / "migrations" / "001_fantasy_schema.up.sql").read_text(encoding="utf-8")
        down = (root / "migrations" / "001_fantasy_schema.down.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE fantasy.portfolios", up)
        self.assertIn("CREATE TABLE fantasy.competition_entries", up)
        self.assertIn("CREATE TABLE fantasy.score_runs", up)
        self.assertIn("token_hash text UNIQUE NOT NULL", up)
        self.assertNotIn("CREATE TABLE public.", up)
        self.assertNotIn("ep047.", up.lower())
        self.assertNotIn("ep051.", up.lower())
        self.assertIn("DROP SCHEMA IF EXISTS fantasy CASCADE", down)


if __name__ == "__main__":
    unittest.main()
