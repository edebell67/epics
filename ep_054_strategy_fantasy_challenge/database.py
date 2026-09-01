# database.py — PostgreSQL connection and transactional migration gate for EP054.
#
# VERSION HISTORY
# v1.0.0 · 2026-09-01 · Replaces the SQLite bootstrap with DATABASE_URL-backed, isolated-schema PostgreSQL migrations.
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

MIGRATIONS = Path(__file__).resolve().parent / "migrations"
SCHEMA = "fantasy"


class DatabaseConfigurationError(RuntimeError):
    """Raised when EP054 cannot establish its approved PostgreSQL boundary."""


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    scheme = urlparse(value).scheme.lower()
    if scheme not in {"postgres", "postgresql"}:
        raise DatabaseConfigurationError(
            "DATABASE_URL must reference the approved PostgreSQL service; SQLite and local file databases are not supported"
        )
    return value


@contextmanager
def connect() -> Iterator[Connection]:
    with psycopg.connect(database_url(), row_factory=dict_row) as connection:
        with connection.transaction():
            yield connection


def apply_migrations() -> list[str]:
    """Apply unapplied forward migrations atomically under an advisory lock."""
    applied: list[str] = []
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("ep054:fantasy:migrations",))
            cursor.execute("CREATE SCHEMA IF NOT EXISTS fantasy AUTHORIZATION CURRENT_USER")
            cursor.execute("REVOKE ALL ON SCHEMA fantasy FROM PUBLIC")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fantasy.schema_migrations (
                    version text PRIMARY KEY,
                    applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
                )
                """
            )
            for path in sorted(MIGRATIONS.glob("*.up.sql")):
                version = path.name.removesuffix(".up.sql")
                cursor.execute(
                    "SELECT 1 FROM fantasy.schema_migrations WHERE version = %s",
                    (version,),
                )
                if cursor.fetchone():
                    continue
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute(
                    "INSERT INTO fantasy.schema_migrations(version) VALUES (%s)",
                    (version,),
                )
                applied.append(version)
    return applied


def rollback_migration(version: str) -> None:
    """Rollback one migration for rehearsals; callers must target an isolated database."""
    path = MIGRATIONS / f"{version}.down.sql"
    if not path.is_file():
        raise ValueError(f"No rollback migration exists for {version}")
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("ep054:fantasy:migrations",))
            cursor.execute(path.read_text(encoding="utf-8"))
