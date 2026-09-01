# repository.py — PostgreSQL repositories for EP054 portfolio, entry, scoring and invitation state.
#
# VERSION HISTORY
# v1.1.1 · 2026-09-01 · Makes competition-entry creation idempotent under concurrent duplicate submissions.
# v1.1.0 · 2026-09-01 · Makes owner and composition deduplication concurrency-safe and scopes score hashes to their competition.
# v1.0.0 · 2026-09-01 · Introduces schema-qualified repositories so EP054 no longer persists through SQLite.
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from database import connect


def _id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6).upper()}"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class FantasyRepository:
    """All durable EP054 access, explicitly confined to the fantasy schema."""

    def ping(self) -> None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM fantasy.schema_migrations LIMIT 1")
            cursor.fetchone()

    def create_entry(
        self,
        *,
        email: str,
        display_name: str,
        portfolio_name: str,
        strategy_ids: list[str],
        fingerprint: str,
        timestamp: datetime,
        baseline_version: str,
        directory_as_of: str,
        methodology: str,
        baseline_points: list[Any],
        challenge_id: str,
    ) -> dict[str, Any]:
        weight = 1.0 / len(strategy_ids)
        with connect() as connection, connection.cursor() as cursor:
            proposed_player_id = _id("PLY")
            cursor.execute(
                """
                INSERT INTO fantasy.players(player_id,email,display_name,created_at)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (lower(email)) DO UPDATE SET display_name = EXCLUDED.display_name
                RETURNING player_id
                """,
                (proposed_player_id, email, display_name, timestamp),
            )
            player_id = cursor.fetchone()["player_id"]

            proposed_portfolio_id = _id("PF")
            cursor.execute(
                """
                INSERT INTO fantasy.portfolios(
                    portfolio_id,owner_id,portfolio_name,composition_hash,created_at,updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (owner_id,composition_hash) WHERE lifecycle_state <> 'ARCHIVED'
                DO NOTHING
                RETURNING portfolio_id,current_revision
                """,
                (proposed_portfolio_id, player_id, portfolio_name, fingerprint, timestamp, timestamp),
            )
            portfolio = cursor.fetchone()
            created_portfolio = portfolio is not None
            if not portfolio:
                cursor.execute(
                    """
                    SELECT portfolio_id,current_revision FROM fantasy.portfolios
                    WHERE owner_id = %s AND composition_hash = %s AND lifecycle_state <> 'ARCHIVED'
                    FOR UPDATE
                    """,
                    (player_id, fingerprint),
                )
                portfolio = cursor.fetchone()
            portfolio_id = portfolio["portfolio_id"]
            revision = portfolio["current_revision"]
            if not created_portfolio:
                cursor.execute(
                    "UPDATE fantasy.portfolios SET portfolio_name = %s, updated_at = %s WHERE portfolio_id = %s",
                    (portfolio_name, timestamp, portfolio_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO fantasy.portfolio_revisions(portfolio_id,revision,evidence_version,created_at) VALUES (%s,%s,%s,%s)",
                    (portfolio_id, revision, baseline_version, timestamp),
                )
                for point in baseline_points:
                    cursor.execute(
                        """
                        INSERT INTO fantasy.portfolio_members(
                            portfolio_id,revision,strategy_id,weight,evidence_ref,evidence_basis,
                            directory_as_of,methodology_version
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            portfolio_id,
                            revision,
                            point.strategy_id,
                            weight,
                            point.evidence_ref,
                            point.basis,
                            directory_as_of,
                            methodology,
                        ),
                    )

            proposed_entry_id = _id("ENT")
            cursor.execute(
                """
                INSERT INTO fantasy.competition_entries(
                    entry_id,competition_id,portfolio_id,portfolio_revision,entry_timestamp,status
                ) VALUES (%s,%s,%s,%s,%s,'ACTIVE')
                ON CONFLICT (competition_id,portfolio_id,portfolio_revision) DO NOTHING
                RETURNING entry_id,entry_timestamp
                """,
                (proposed_entry_id, challenge_id, portfolio_id, revision, timestamp),
            )
            entry = cursor.fetchone()
            created_entry = entry is not None
            if not entry:
                cursor.execute(
                    """
                    SELECT entry_id,entry_timestamp FROM fantasy.competition_entries
                    WHERE competition_id = %s AND portfolio_id = %s AND portfolio_revision = %s
                    """,
                    (challenge_id, portfolio_id, revision),
                )
                entry = cursor.fetchone()
            entry_id = entry["entry_id"]
            if not created_entry:
                return {
                    "entry_id": entry_id,
                    "player_id": player_id,
                    "portfolio_id": portfolio_id,
                    "portfolio_revision": revision,
                    "entry_timestamp": entry["entry_timestamp"],
                    "reused": True,
                }
            for point in baseline_points:
                cursor.execute(
                    """
                    INSERT INTO fantasy.entry_strategies(
                        entry_id,strategy_id,weight,baseline_equity,baseline_net_return,
                        baseline_trade_number,baseline_observed_at,evidence_ref,evidence_basis,
                        directory_as_of,methodology_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        entry_id,
                        point.strategy_id,
                        weight,
                        point.equity,
                        point.net_return,
                        point.trade_number,
                        point.observed_at,
                        point.evidence_ref,
                        point.basis,
                        directory_as_of,
                        methodology,
                    ),
                )
            return {
                "entry_id": entry_id,
                "player_id": player_id,
                "portfolio_id": portfolio_id,
                "portfolio_revision": revision,
                "entry_timestamp": timestamp,
                "reused": False,
            }

    def active_entries(self, challenge_id: str) -> list[dict[str, Any]]:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ce.entry_id, p.portfolio_name, pl.display_name
                FROM fantasy.competition_entries ce
                JOIN fantasy.portfolios p ON p.portfolio_id = ce.portfolio_id
                JOIN fantasy.players pl ON pl.player_id = p.owner_id
                WHERE ce.competition_id = %s AND ce.status = 'ACTIVE'
                  AND EXISTS (
                    SELECT 1 FROM fantasy.entry_strategies es WHERE es.entry_id = ce.entry_id
                  )
                ORDER BY ce.entry_id
                """,
                (challenge_id,),
            )
            return list(cursor.fetchall())

    def entry_strategies(self, entry_id: str) -> list[dict[str, Any]]:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM fantasy.entry_strategies WHERE entry_id = %s ORDER BY strategy_id",
                (entry_id,),
            )
            return list(cursor.fetchall())

    def record_score_run(
        self,
        challenge_id: str,
        scoring_version: str,
        source_version: str,
        calculated_at: datetime,
        rows: list[dict[str, Any]],
    ) -> str:
        canonical = json.dumps(
            {"competition_id": challenge_id, "scoring_version": scoring_version, "source_version": source_version, "rows": [{"entry_id": row["entry_id"], "score": row["score"], "contributions": row["contributions"]} for row in rows]},
            sort_keys=True,
            separators=(",", ":"),
        )
        input_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        score_run_id = "SR_" + input_hash[:20].upper()
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO fantasy.score_runs(
                    score_run_id,competition_id,scoring_version,input_hash,source_version,calculated_at,promoted_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (competition_id,scoring_version,input_hash) DO NOTHING
                """,
                (score_run_id, challenge_id, scoring_version, input_hash, source_version, calculated_at, calculated_at),
            )
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO fantasy.entry_scores(score_run_id,entry_id,score,rank,breakdown)
                    VALUES (%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (score_run_id,entry_id) DO NOTHING
                    """,
                    (score_run_id, row["entry_id"], row["score"], row["rank"], json.dumps(row["contributions"])),
                )
        return score_run_id

    def create_invitation(self, entry_id: str, now: datetime) -> dict[str, Any] | None:
        token = secrets.token_urlsafe(24)
        invitation_id = _id("INV")
        expires_at = now + timedelta(days=7)
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT competition_id FROM fantasy.competition_entries WHERE entry_id = %s",
                (entry_id,),
            )
            entry = cursor.fetchone()
            if not entry:
                return None
            cursor.execute(
                """
                INSERT INTO fantasy.invitations(
                    invitation_id,token_hash,inviter_entry_id,competition_id,created_at,expires_at,status
                ) VALUES (%s,%s,%s,%s,%s,%s,'CREATED')
                """,
                (invitation_id, _token_hash(token), entry_id, entry["competition_id"], now, expires_at),
            )
            cursor.execute(
                "INSERT INTO fantasy.invitation_events(invitation_id,event_type,occurred_at) VALUES (%s,'CREATED',%s)",
                (invitation_id, now),
            )
        return {
            "invitation_id": invitation_id,
            "invite_token": token,
            "entry_id": entry_id,
            "challenge_id": entry["competition_id"],
            "created_at": now,
            "expires_at": expires_at,
            "status": "CREATED",
        }

    def open_invitation(self, token: str, now: datetime) -> dict[str, Any] | None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT i.*, p.portfolio_name, pl.display_name,
                       COALESCE(es.score, 0) AS score
                FROM fantasy.invitations i
                JOIN fantasy.competition_entries ce ON ce.entry_id = i.inviter_entry_id
                JOIN fantasy.portfolios p ON p.portfolio_id = ce.portfolio_id
                JOIN fantasy.players pl ON pl.player_id = p.owner_id
                LEFT JOIN LATERAL (
                    SELECT value.score
                    FROM fantasy.entry_scores value
                    JOIN fantasy.score_runs run ON run.score_run_id = value.score_run_id
                    WHERE value.entry_id = ce.entry_id
                    ORDER BY run.promoted_at DESC LIMIT 1
                ) es ON true
                WHERE i.token_hash = %s
                FOR UPDATE OF i
                """,
                (_token_hash(token),),
            )
            invitation = cursor.fetchone()
            if not invitation or invitation["status"] in {"REVOKED", "EXPIRED"}:
                return None
            if invitation["expires_at"] <= now:
                cursor.execute(
                    "UPDATE fantasy.invitations SET status = 'EXPIRED' WHERE invitation_id = %s",
                    (invitation["invitation_id"],),
                )
                return None
            opened_at = invitation["opened_at"] or now
            cursor.execute(
                """
                UPDATE fantasy.invitations
                SET opened_at = %s, status = CASE WHEN status = 'CREATED' THEN 'OPENED' ELSE status END
                WHERE invitation_id = %s
                """,
                (opened_at, invitation["invitation_id"]),
            )
            if invitation["opened_at"] is None:
                cursor.execute(
                    "INSERT INTO fantasy.invitation_events(invitation_id,event_type,occurred_at) VALUES (%s,'OPENED',%s)",
                    (invitation["invitation_id"], now),
                )
            visible_status = "OPENED" if invitation["status"] in {"CREATED", "OPENED"} else invitation["status"]
            return {**invitation, "opened_at": opened_at, "status": visible_status}

    def accept_invitation(
        self, token: str, email: str, display_name: str, now: datetime
    ) -> dict[str, Any] | None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM fantasy.invitations WHERE token_hash = %s FOR UPDATE",
                (_token_hash(token),),
            )
            invitation = cursor.fetchone()
            if not invitation or invitation["status"] in {"ACCEPTED", "REVOKED", "EXPIRED"}:
                return None
            if invitation["expires_at"] <= now:
                cursor.execute(
                    "UPDATE fantasy.invitations SET status = 'EXPIRED' WHERE invitation_id = %s",
                    (invitation["invitation_id"],),
                )
                return None
            cursor.execute(
                "SELECT player_id FROM fantasy.players WHERE lower(email) = lower(%s)",
                (email,),
            )
            player = cursor.fetchone()
            player_id = player["player_id"] if player else _id("PLY")
            if player:
                cursor.execute(
                    "UPDATE fantasy.players SET display_name = %s WHERE player_id = %s",
                    (display_name, player_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO fantasy.players(player_id,email,display_name,created_at) VALUES (%s,%s,%s,%s)",
                    (player_id, email, display_name, now),
                )
            cursor.execute(
                """
                UPDATE fantasy.invitations
                SET accepted_at = %s, accepted_player_id = %s, status = 'ACCEPTED'
                WHERE invitation_id = %s
                """,
                (now, player_id, invitation["invitation_id"]),
            )
            cursor.execute(
                """
                INSERT INTO fantasy.invitation_events(invitation_id,event_type,occurred_at,actor_player_id)
                VALUES (%s,'ACCEPTED',%s,%s)
                """,
                (invitation["invitation_id"], now, player_id),
            )
            return {**invitation, "player_id": player_id, "status": "ACCEPTED"}
