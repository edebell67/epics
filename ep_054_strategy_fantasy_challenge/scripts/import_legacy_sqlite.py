# scripts/import_legacy_sqlite.py — One-time, idempotent transfer of legacy EP054 SQLite records into PostgreSQL.
#
# VERSION HISTORY
# v1.1.1 · 2026-09-01 · Removes a redundant legacy portfolio-ID assignment after the consolidation fix.
# v1.1.0 · 2026-09-01 · Consolidates legacy duplicate compositions into canonical portfolios and remaps dependent invitations.
# v1.0.0 · 2026-09-01 · Preserves existing MVP records while retiring SQLite from the application runtime.
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from database import apply_migrations, connect  # noqa: E402


def rows(connection: sqlite3.Connection, table: str) -> list[dict]:
    try:
        return [dict(row) for row in connection.execute(f"SELECT * FROM {table}")]
    except sqlite3.OperationalError as exc:
        raise RuntimeError(f"Legacy database is missing required table {table!r}") from exc


def import_database(source: Path) -> dict[str, int]:
    if not source.is_file():
        raise FileNotFoundError(source)
    apply_migrations()
    legacy = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    legacy.row_factory = sqlite3.Row
    try:
        players = rows(legacy, "players")
        entries = rows(legacy, "entries")
        baselines = rows(legacy, "entry_strategy_baselines")
        invitations = rows(legacy, "invitations")
    finally:
        legacy.close()

    baselines_by_entry: dict[str, list[dict]] = {}
    for item in baselines:
        baselines_by_entry.setdefault(item["entry_id"], []).append(item)

    portfolio_ids: set[str] = set()
    entry_ids: set[str] = set()
    legacy_entry_map: dict[str, str] = {}
    with connect() as target, target.cursor() as cursor:
        for player in players:
            cursor.execute(
                """
                INSERT INTO fantasy.players(player_id,email,display_name,created_at)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (player_id) DO UPDATE
                SET email = EXCLUDED.email, display_name = EXCLUDED.display_name
                """,
                (player["player_id"], player["email"], player["display_name"], player["created_at"]),
            )
        for entry in entries:
            proposed_portfolio_id = "PF_LEGACY_" + entry["entry_id"].removeprefix("ENT_")
            cursor.execute(
                """
                INSERT INTO fantasy.portfolios(
                    portfolio_id,owner_id,portfolio_name,composition_hash,provenance,
                    lifecycle_state,current_revision,created_at,updated_at
                ) VALUES (%s,%s,%s,%s,'LEGACY_SQLITE_IMPORT','ACTIVE',1,%s,%s)
                ON CONFLICT (owner_id,composition_hash) WHERE lifecycle_state <> 'ARCHIVED'
                DO NOTHING RETURNING portfolio_id
                """,
                (proposed_portfolio_id, entry["player_id"], entry["portfolio_name"], entry["composition_hash"], entry["entry_timestamp"], entry["entry_timestamp"]),
            )
            created = cursor.fetchone()
            if created:
                portfolio_id = created["portfolio_id"]
            else:
                cursor.execute(
                    """
                    SELECT portfolio_id FROM fantasy.portfolios
                    WHERE owner_id = %s AND composition_hash = %s AND lifecycle_state <> 'ARCHIVED'
                    """,
                    (entry["player_id"], entry["composition_hash"]),
                )
                portfolio_id = cursor.fetchone()["portfolio_id"]
            portfolio_ids.add(portfolio_id)
            cursor.execute(
                """
                INSERT INTO fantasy.portfolio_revisions(portfolio_id,revision,evidence_version,created_at)
                VALUES (%s,1,%s,%s) ON CONFLICT DO NOTHING
                """,
                (portfolio_id, entry["baseline_version"], entry["entry_timestamp"]),
            )
            for baseline in baselines_by_entry.get(entry["entry_id"], []):
                member_values = (portfolio_id, baseline["strategy_id"], baseline["weight"], baseline["evidence_ref"], baseline["evidence_basis"], baseline["directory_as_of"], baseline["methodology_version"])
                cursor.execute(
                    """
                    INSERT INTO fantasy.portfolio_members(
                        portfolio_id,revision,strategy_id,weight,evidence_ref,evidence_basis,directory_as_of,methodology_version
                    ) VALUES (%s,1,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
                    """,
                    member_values,
                )
            cursor.execute(
                """
                INSERT INTO fantasy.competition_entries(
                    entry_id,competition_id,portfolio_id,portfolio_revision,entry_timestamp,status
                ) VALUES (%s,%s,%s,1,%s,%s)
                ON CONFLICT (competition_id,portfolio_id,portfolio_revision) DO NOTHING
                RETURNING entry_id
                """,
                (entry["entry_id"], entry["challenge_id"], portfolio_id, entry["entry_timestamp"], entry["status"]),
            )
            inserted_entry = cursor.fetchone()
            if inserted_entry:
                canonical_entry_id = inserted_entry["entry_id"]
            else:
                cursor.execute(
                    """
                    SELECT entry_id FROM fantasy.competition_entries
                    WHERE competition_id = %s AND portfolio_id = %s AND portfolio_revision = 1
                    """,
                    (entry["challenge_id"], portfolio_id),
                )
                canonical_entry_id = cursor.fetchone()["entry_id"]
            legacy_entry_map[entry["entry_id"]] = canonical_entry_id
            entry_ids.add(canonical_entry_id)
            for baseline in baselines_by_entry.get(entry["entry_id"], []):
                cursor.execute(
                    """
                    INSERT INTO fantasy.entry_strategies(
                        entry_id,strategy_id,weight,baseline_equity,baseline_net_return,
                        baseline_trade_number,baseline_observed_at,evidence_ref,evidence_basis,
                        directory_as_of,methodology_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
                    """,
                    (canonical_entry_id, baseline["strategy_id"], baseline["weight"], baseline["baseline_equity"], baseline["baseline_net_return"], baseline["baseline_trade_number"], baseline["baseline_observed_at"], baseline["evidence_ref"], baseline["evidence_basis"], baseline["directory_as_of"], baseline["methodology_version"]),
                )
        for invite in invitations:
            invitation_id = "INV_LEGACY_" + hashlib.sha256(invite["invite_token"].encode()).hexdigest()[:16].upper()
            expires_expression = "(%s::timestamptz + interval '7 days')"
            cursor.execute(
                f"""
                INSERT INTO fantasy.invitations(
                    invitation_id,token_hash,inviter_entry_id,competition_id,created_at,expires_at,
                    opened_at,accepted_at,accepted_player_id,status
                ) VALUES (%s,%s,%s,%s,%s,{expires_expression},%s,%s,%s,%s)
                ON CONFLICT (token_hash) DO NOTHING
                """,
                (invitation_id, hashlib.sha256(invite["invite_token"].encode()).hexdigest(), legacy_entry_map[invite["inviter_entry_id"]], invite["challenge_id"], invite["created_at"], invite["created_at"], invite["opened_at"], invite["accepted_at"], invite["accepted_player_id"], invite["status"]),
            )
    return {"source_players": len(players), "source_entries": len(entries), "canonical_portfolios": len(portfolio_ids), "canonical_entries": len(entry_ids), "source_entry_strategies": len(baselines), "source_invitations": len(invitations)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Import the retired EP054 SQLite database into the isolated PostgreSQL fantasy schema.")
    parser.add_argument("source", type=Path, help="Path to the legacy fantasy_mvp.sqlite3 file")
    parser.add_argument("--confirm", action="store_true", help="Required acknowledgement that DATABASE_URL targets the approved PostgreSQL service")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("--confirm is required")
    counts = import_database(args.source.resolve())
    print("Legacy import committed:", ", ".join(f"{key}={value}" for key, value in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
