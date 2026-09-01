# server.py — EP054 FastAPI application backed by isolated PostgreSQL repositories.
#
# VERSION HISTORY
# v4.0.0 · 2026-09-01 · Replaces SQLite with workflow-compliant PostgreSQL migrations, repositories and immutable score runs.
# v3.1.0 · 2026-08-31 · Limits new portfolio eligibility to strategies traded on the current UTC date.
# v3.0.0 · 2026-08-31 · Uses EP051 catalogue and costs-inclusive equity evidence for eligibility, baselines and scoring.
# v2.0.0 · 2026-08-31 · Adds persistent MVP entries, leaderboard and invitation APIs.
# v1.0.0 · 2026-08-31 · Version history added; file predates this convention.
from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import apply_migrations
from directory_client import DirectoryUnavailable, StrategyDirectoryClient
from repository import FantasyRepository

ROOT = Path(__file__).resolve().parent
CHALLENGE_ID = "GLOBAL_WEEKLY"
SCORING_VERSION = "ep051-equity-v1"
directory = StrategyDirectoryClient()
repository: FantasyRepository | None = None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_repository() -> FantasyRepository:
    global repository
    if repository is None:
        repository = FantasyRepository()
    return repository


def initialise() -> None:
    apply_migrations()
    get_repository().ping()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialise()
    yield


class EntryCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=2, max_length=40)
    portfolio_name: str = Field(min_length=2, max_length=44)
    strategy_ids: list[str]


class InvitationCreate(BaseModel):
    entry_id: str


class InvitationAccept(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=2, max_length=40)


app = FastAPI(title="Strategy Fantasy Challenge MVP", docs_url="/api/docs", redoc_url=None, lifespan=lifespan)


@app.get("/health", include_in_schema=False)
def health():
    try:
        get_repository().ping()
        database_status = {"status": "ok", "engine": "postgresql", "schema": "fantasy"}
    except Exception as exc:
        database_status = {"status": "unavailable", "engine": "postgresql", "schema": "fantasy", "detail": str(exc)}
    try:
        source = directory.catalogue(page_size=1)
        directory_status = {"status": "ok", "url": directory.base_url, "as_of": source["as_of"], "methodology_version": source["methodology_version"], "eligibility_date": source["activity_date"]}
    except DirectoryUnavailable as exc:
        directory_status = {"status": "unavailable", "url": directory.base_url, "detail": str(exc)}
    status = "ok" if database_status["status"] == directory_status["status"] == "ok" else "degraded"
    return {"status": status, "service": "strategy-fantasy-challenge-mvp", "database": database_status, "strategy_directory": directory_status}


@app.get("/api/strategies")
def strategies():
    try:
        source = directory.catalogue()
    except DirectoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    rows = [{"strategy_id": row["strategy_id"], "display_name": row.get("descriptive_name") or row["strategy_id"], "source": "EP051 Strategy Directory", "total_trades": row["total_trades"], "total_net_return": row["total_net_return"], "win_rate": row.get("win_rate"), "evidence_end": row.get("evidence_end"), "quality_state": row.get("quality_state")} for row in source["items"]]
    return {"challenge_id": CHALLENGE_ID, "min_strategies": 3, "max_strategies": 10, "strategies": rows, "source": {"url": directory.base_url, "as_of": source["as_of"], "methodology_version": source["methodology_version"], "basis": source["basis"], "total": source["total"], "eligibility_date": source["activity_date"], "eligibility_rule": "at least one EP051 closed trade on the current UTC date"}}


@app.post("/api/entries", status_code=201)
def create_entry(payload: EntryCreate):
    ids = list(dict.fromkeys(payload.strategy_ids))
    if len(ids) != len(payload.strategy_ids):
        raise HTTPException(422, "Strategies must be unique")
    if not 3 <= len(ids) <= 10:
        raise HTTPException(422, "Select between 3 and 10 strategies")
    try:
        source_rows = [directory.strategy(strategy_id) for strategy_id in ids]
        baseline_points = [directory.evidence(strategy_id) for strategy_id in ids]
    except DirectoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    timestamp = now_utc()
    fingerprint = hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest().upper()
    methodology = source_rows[0]["methodology_version"]
    directory_as_of = source_rows[0]["as_of"]
    if any(row["methodology_version"] != methodology or row["as_of"] != directory_as_of for row in source_rows):
        raise HTTPException(409, "Strategy Directory snapshot changed during entry creation; retry")
    baseline_version = f"EP051:{methodology}:{directory_as_of}"
    persisted = get_repository().create_entry(email=payload.email, display_name=payload.display_name, portfolio_name=payload.portfolio_name, strategy_ids=ids, fingerprint=fingerprint, timestamp=timestamp, baseline_version=baseline_version, directory_as_of=directory_as_of, methodology=methodology, baseline_points=baseline_points, challenge_id=CHALLENGE_ID)
    weight = 1.0 / len(ids)
    return {**persisted, "challenge_id": CHALLENGE_ID, "composition_hash": fingerprint, "baseline_version": baseline_version, "score": 0.0, "score_basis": "equal-weight change in EP051 cumulative net return after entry; costs and commission included", "evidence": [{"strategy_id": point.strategy_id, "evidence_ref": point.evidence_ref, "baseline_equity": point.equity, "observed_at": point.observed_at, "weight": weight} for point in baseline_points], "status": "ACTIVE"}


@app.get("/api/leaderboard")
def leaderboard(entry_id: str | None = None):
    repo = get_repository()
    active_entries = repo.active_entries(CHALLENGE_ID)
    latest_cache = {}
    rows = []
    source_refs: list[str] = []
    for entry in active_entries:
        contributions = []
        for baseline in repo.entry_strategies(entry["entry_id"]):
            strategy_id = baseline["strategy_id"]
            if strategy_id not in latest_cache:
                try:
                    latest_cache[strategy_id] = directory.evidence(strategy_id)
                except DirectoryUnavailable as exc:
                    raise HTTPException(503, str(exc)) from exc
            latest = latest_cache[strategy_id]
            source_refs.append(latest.evidence_ref)
            contribution = (latest.equity - baseline["baseline_equity"]) * baseline["weight"]
            contributions.append({"strategy_id": strategy_id, "baseline_equity": baseline["baseline_equity"], "latest_equity": latest.equity, "net_change": latest.equity - baseline["baseline_equity"], "weight": baseline["weight"], "weighted_contribution": contribution, "baseline_evidence_ref": baseline["evidence_ref"], "latest_evidence_ref": latest.evidence_ref})
        rows.append({**entry, "score": sum(item["weighted_contribution"] for item in contributions), "contributions": contributions})
    rows.sort(key=lambda row: (-row["score"], row["entry_id"]))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
        row["is_current"] = row["entry_id"] == entry_id
    calculated_at = now_utc()
    source_version = hashlib.sha256("|".join(sorted(source_refs)).encode()).hexdigest()
    score_run_id = repo.record_score_run(CHALLENGE_ID, SCORING_VERSION, source_version, calculated_at, rows)
    current = next((row for row in rows if row["is_current"]), None)
    return {"challenge_id": CHALLENGE_ID, "score_run_id": score_run_id, "scoring_version": SCORING_VERSION, "updated_at": calculated_at.isoformat(), "total_players": len(rows), "current": current, "rows": rows, "basis": "equal-weight change in EP051 cumulative net return after each entry baseline; costs and commission included", "source": {"strategy_directory_url": directory.base_url, "source_version": source_version}}


@app.post("/api/invitations", status_code=201)
def create_invitation(payload: InvitationCreate):
    invitation = get_repository().create_invitation(payload.entry_id, now_utc())
    if not invitation:
        raise HTTPException(404, "Entry not found")
    return {**invitation, "invite_url": f"/invite/{invitation['invite_token']}"}


@app.get("/api/invitations/{token}")
def open_invitation(token: str):
    invitation = get_repository().open_invitation(token, now_utc())
    if not invitation:
        raise HTTPException(404, "Invitation not found, expired, or revoked")
    return {"invite_token": token, "challenge_id": invitation["competition_id"], "status": invitation["status"], "inviter": {"portfolio_name": invitation["portfolio_name"], "score": invitation["score"], "display_name": invitation["display_name"]}}


@app.post("/api/invitations/{token}/accept")
def accept_invitation(token: str, payload: InvitationAccept):
    invitation = get_repository().accept_invitation(token, payload.email, payload.display_name, now_utc())
    if not invitation:
        raise HTTPException(409, "Invitation is invalid, expired, revoked, or already accepted")
    return {"invite_token": token, "challenge_id": invitation["competition_id"], "player_id": invitation["player_id"], "status": "ACCEPTED", "next": "/#build"}


@app.get("/invite/{token}", include_in_schema=False)
def invitation_landing(token: str):
    return FileResponse(ROOT / "index.html")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "index.html")


app.mount("/", StaticFiles(directory=ROOT, html=True), name="static")
