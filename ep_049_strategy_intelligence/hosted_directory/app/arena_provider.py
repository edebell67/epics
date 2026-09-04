"""EP052 Lean Exchange intelligence provider - the real implementation of the
contract ep_052's IntelligenceClient/simulated_intelligence.py already define
and validate against (GET /v1/contracts/intelligence on the arena). Replaces
simulated_intelligence.py's random selection with actual ranked queries
against this directory's own StrategyQuery/basis_profiles engine, gated by
the same Authorization: Bearer <service token> + X-EP052-Agent-ID header
pair the arena's client already sends - the arena's own owner/agent/
connection model is the identity system; this only verifies the arena
itself is a trusted caller and logs which of its agents triggered each query.

VERSION HISTORY
v1.2.0 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/app/
to epics/ep_049_strategy_intelligence/hosted_directory/app/ per Ed's EP049 ownership decision
(this is intelligence infrastructure, not EP051's own directory-listing responsibility). No
code changes - imported by EP051's app/main.py (the shared FastAPI host) via a namespace-package
merge across both hosted_directory/ trees (see both directories' conftest.py).
v1.1.0 - RIP-100/RIP-110: durable per-query observability log (agent_id,
kind, fallback, window, requested/returned/universe counts, latency, cache
hit), a rolling per-agent volume check that logs a warning on anomalous
bursts, GET /v1/observability/agents for audit, and GET /v1/kinds
publishing the recognized kind vocabulary plus its live fallback rate so
agent authors can discover kinds without reading source.
v1.0.0 - Initial real provider: kind-dispatched ranking, durable idempotent
deliveries (mirrors simulated_intelligence.py's SQLite receipt table so a
retried request_id/revision replays the same result instead of re-billing).
"""
from __future__ import annotations
from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4
import hmac, json, logging, sqlite3, time

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

log = logging.getLogger("arena_provider")

StrategyId = Field(pattern=r"^DNA_[0-9]+$")

# Recognized `kind` values and which profile metric they rank by. `kind` is
# free text in the contract (no enum enforced) - an unrecognized value falls
# back to quality_score rather than erroring, same tolerant spirit as the
# simulated provider ignoring kind entirely, but ours actually uses it when
# it understands it and says so either way in `notice`.
KIND_METRICS = {
    "top_performers": ("metrics", "total_return"),
    "best_return": ("metrics", "total_return"),
    "net_return": ("metrics", "total_return"),
    "high_win_rate": ("metrics", "win_rate"),
    "win_rate": ("metrics", "win_rate"),
    "low_drawdown": ("metrics", "max_drawdown"),
    "safe": ("metrics", "max_drawdown"),
    "quality": ("score", "quality_score"),
    "quality_score": ("score", "quality_score"),
}
DEFAULT_KIND = "quality"
KIND_DESCRIPTIONS = {
    "top_performers": "Rank by all-time total net return, highest first.",
    "best_return": "Alias of top_performers.",
    "net_return": "Alias of top_performers.",
    "high_win_rate": "Rank by win rate, highest first.",
    "win_rate": "Alias of high_win_rate.",
    "low_drawdown": "Rank by maximum drawdown, safest (closest to zero) first.",
    "safe": "Alias of low_drawdown.",
    "quality": f"Rank by composite quality_score, highest first. Also the fallback for any unrecognized kind.",
    "quality_score": "Alias of quality.",
}


class ArenaQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    revision: int = Field(default=0, ge=0)
    kind: str = Field(min_length=1, max_length=128)
    strategy_ids: list[str] = Field(default_factory=list, max_length=1000)
    window_start: datetime | None = None
    window_end: datetime | None = None
    limit: int = Field(default=5, gt=0)

    @model_validator(mode="after")
    def valid_window(self):
        for value in (self.window_start, self.window_end):
            if value is not None and value.tzinfo is None:
                raise ValueError("Query timestamps require timezone")
        if self.window_start and self.window_end and self.window_start > self.window_end:
            raise ValueError("Query start must not follow end")
        return self


class ArenaQueryDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delivery_id: UUID
    request_id: UUID
    revision: int = Field(ge=0)
    result_version: UUID
    created_at: datetime
    source_version: str
    mode: Literal["simulated_random", "external"]
    strategy_ids: list[str]
    query: ArenaQueryRequest
    notice: str


def _fingerprint(request: ArenaQueryRequest) -> str:
    return sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _metric_value(profile: dict, path: tuple[str, str]) -> float | None:
    section, key = path
    if section == "score":
        return profile.get("score", {}).get(key)
    return profile.get("metrics", {}).get(key, {}).get("value")


def select_strategies(request: ArenaQueryRequest, universe_fn, cfg) -> tuple[list[str], str, bool, int]:
    """Resolve one ArenaQueryRequest against the real directory: builds the
    candidate pool for [window_start, window_end) via basis_profiles (or the
    full since-inception pool when no window is given), ranks by whatever
    `kind` maps to, restricts to request.strategy_ids when given, and caps
    at request.limit. Returns (strategy_ids, notice, fallback, universe_size)."""
    metric_path = KIND_METRICS.get(request.kind.lower())
    fallback = metric_path is None
    if fallback:
        metric_path = KIND_METRICS[DEFAULT_KIND]
    profiles = universe_fn(request.window_start, request.window_end)
    if profiles is None:
        raise HTTPException(503, "EXTERNAL_PROVIDER_UNAVAILABLE")
    if request.strategy_ids:
        requested = set(request.strategy_ids)
        profiles = [p for p in profiles if p["identity"]["strategy_id"] in requested]
    reverse = metric_path[1] != "max_drawdown"  # drawdown: closer to zero (less negative) is better -> descending still correct since values are <=0
    ranked = sorted(profiles, key=lambda p: (_metric_value(p, metric_path) if _metric_value(p, metric_path) is not None else float("-inf")), reverse=reverse)
    selected = [p["identity"]["strategy_id"] for p in ranked[:request.limit]]
    window_note = f" within [{request.window_start.isoformat() if request.window_start else 'inception'}, {request.window_end.isoformat() if request.window_end else 'now'})"
    if fallback:
        notice = f"kind '{request.kind}' is not a recognized ranking; ranked by quality_score{window_note} instead. Recognized kinds: {sorted(KIND_METRICS)}."
    else:
        notice = f"Ranked by {'/'.join(metric_path)}{window_note}, {len(profiles)} strategies eligible, {len(selected)} returned."
    return selected, notice, fallback, len(profiles)


def install(app: FastAPI, cfg, universe_fn):
    """Mount POST /v1/queries and GET /v1/deliveries/{id} on `app`, matching
    ep_052's IntelligenceClient contract exactly. `universe_fn(start,end)`
    must return a list of profile dicts (or None if unavailable) bounded to
    that window - the caller supplies this so this module stays independent
    of main.py's specific profile-cache plumbing."""
    db_path = Path(cfg.arena_deliveries_path)
    db_path = db_path if db_path.is_absolute() else Path(__file__).resolve().parents[1] / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS deliveries (
            delivery_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, request_id TEXT NOT NULL,
            revision INTEGER NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
            UNIQUE(agent_id,request_id,revision))""")
        db.execute("""CREATE TABLE IF NOT EXISTS query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL, kind TEXT NOT NULL,
            fallback INTEGER NOT NULL, window_start TEXT, window_end TEXT,
            requested_count INTEGER NOT NULL, returned_count INTEGER NOT NULL, universe_size INTEGER,
            latency_ms REAL NOT NULL, cache_hit INTEGER NOT NULL, created_at TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS query_log_agent_time ON query_log(agent_id, created_at)")
        db.commit()

    def service_actor(authorization: str = Header(default="")) -> None:
        """Verifies the caller is the Arena itself (the one shared service
        token), without requiring a specific agent identity - for operator/
        audit surfaces (RIP-100's observability endpoint), not per-agent
        query endpoints."""
        token = cfg.ep052_intelligence_token
        if not token:
            raise HTTPException(503, "EP052 intelligence provider is not configured")
        if not hmac.compare_digest(authorization.encode(), ("Bearer " + token).encode()):
            raise HTTPException(401, "Invalid service credential")

    def arena_actor(authorization: str = Header(default=""), x_ep052_agent_id: UUID | None = Header(default=None)) -> str:
        service_actor(authorization)
        if x_ep052_agent_id is None:
            raise HTTPException(422, "Trusted caller must supply its authenticated agent identity")
        return str(x_ep052_agent_id)

    def log_query(agent_id, kind, fallback, request, returned_count, universe_size, latency_ms, cache_hit):
        """RIP-100: durable per-query observability, plus a rolling-window
        volume check per agent that logs a warning on an anomalous burst -
        the concrete, real-identity anchor for the rate-limit/concurrency
        design discussed earlier, now that agent_id is a real Arena agent
        rather than a hypothetical registry entry."""
        now = datetime.now(timezone.utc)
        with closing(sqlite3.connect(db_path, timeout=15)) as db:
            db.execute("""INSERT INTO query_log
                (agent_id,kind,fallback,window_start,window_end,requested_count,returned_count,universe_size,latency_ms,cache_hit,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (agent_id, kind, int(fallback), request.window_start.isoformat() if request.window_start else None,
                 request.window_end.isoformat() if request.window_end else None, len(request.strategy_ids),
                 returned_count, universe_size, latency_ms, int(cache_hit), now.isoformat()))
            db.commit()
            cutoff = (now - timedelta(seconds=cfg.arena_anomaly_window_seconds)).isoformat()
            recent = db.execute("SELECT COUNT(*) FROM query_log WHERE agent_id=? AND created_at>=?", (agent_id, cutoff)).fetchone()[0]
        if recent > cfg.arena_anomaly_threshold:
            log.warning("EP052 agent %s made %d intelligence queries in the last %ds (threshold %d)",
                        agent_id, recent, cfg.arena_anomaly_window_seconds, cfg.arena_anomaly_threshold)

    @app.post("/v1/queries", response_model=ArenaQueryDelivery)
    def arena_query(request: ArenaQueryRequest, agent_id: str = Depends(arena_actor)):
        started = time.perf_counter()
        if request.limit > cfg.intelligence_max_query_results:
            raise HTTPException(422, "Configured query result limit exceeded")
        identity = (agent_id, str(request.request_id), request.revision)
        request_hash = _fingerprint(request)

        def existing(db):
            row = db.execute("SELECT fingerprint,payload FROM deliveries WHERE agent_id=? AND request_id=? AND revision=?", identity).fetchone()
            if row:
                if row[0] != request_hash:
                    raise HTTPException(409, "REQUEST_ID_CONFLICT")
                return ArenaQueryDelivery.model_validate_json(row[1])
            return None

        with closing(sqlite3.connect(db_path)) as db:
            recovered = existing(db)
            if recovered:
                log_query(agent_id, request.kind, request.kind.lower() not in KIND_METRICS, request,
                          len(recovered.strategy_ids), None, (time.perf_counter() - started) * 1000, cache_hit=True)
                return recovered

        selected, notice, fallback, universe_size = select_strategies(request, universe_fn, cfg)
        result = ArenaQueryDelivery(delivery_id=uuid4(), request_id=request.request_id, revision=request.revision,
                                     result_version=uuid4(), created_at=datetime.now(timezone.utc),
                                     source_version="dna-strategy-directory-1.0.0", mode="external",
                                     strategy_ids=selected, query=request, notice=notice)
        with closing(sqlite3.connect(db_path, timeout=15)) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                recovered = existing(db)
                if recovered:
                    log_query(agent_id, request.kind, fallback, request, len(recovered.strategy_ids), universe_size,
                              (time.perf_counter() - started) * 1000, cache_hit=True)
                    return recovered
                db.execute("INSERT INTO deliveries VALUES (?,?,?,?,?,?)",
                           (str(result.delivery_id), *identity, request_hash, result.model_dump_json()))
                db.commit()
            finally:
                if db.in_transaction:
                    db.rollback()
        log_query(agent_id, request.kind, fallback, request, len(selected), universe_size,
                  (time.perf_counter() - started) * 1000, cache_hit=False)
        return result

    @app.get("/v1/deliveries/{delivery_id}", response_model=ArenaQueryDelivery)
    def arena_recover(delivery_id: UUID, agent_id: str = Depends(arena_actor)):
        with closing(sqlite3.connect(db_path)) as db:
            row = db.execute("SELECT payload FROM deliveries WHERE delivery_id=? AND agent_id=?",
                              (str(delivery_id), agent_id)).fetchone()
        if not row:
            raise HTTPException(404, "Delivery not found")
        return ArenaQueryDelivery.model_validate_json(row[0])

    @app.get("/v1/observability/agents")
    def arena_observability(agent_id: str | None = None, _: None = Depends(service_actor)):
        """RIP-100: per-agent query activity for audit and the rate-limit
        design's real anchor - service-token-authenticated (the Arena or an
        operator), not per-agent, since this spans every agent. Optional
        ?agent_id= narrows to one agent's own recent history."""
        clause = "WHERE agent_id=?" if agent_id else ""
        params = (agent_id,) if agent_id else ()
        with closing(sqlite3.connect(db_path)) as db:
            rows = db.execute(f"""SELECT agent_id, COUNT(*), SUM(fallback), AVG(latency_ms), SUM(cache_hit), MAX(created_at), MIN(created_at)
                FROM query_log {clause} GROUP BY agent_id ORDER BY COUNT(*) DESC""", params).fetchall()
        agents = [{"agent_id": row[0], "query_count": row[1], "fallback_count": row[2],
                   "fallback_rate": round(row[2] / row[1], 4) if row[1] else None,
                   "avg_latency_ms": round(row[3], 2) if row[3] is not None else None,
                   "cache_hit_count": row[4], "last_seen": row[5], "first_seen": row[6]} for row in rows]
        return {"anomaly_threshold": cfg.arena_anomaly_threshold, "anomaly_window_seconds": cfg.arena_anomaly_window_seconds,
                "agents": agents, "schema_version": "1.0.0"}

    @app.get("/v1/kinds")
    def arena_kinds():
        """RIP-110: the recognized `kind` vocabulary as a discoverable, live
        contract - no auth required, same public spirit as the Arena's own
        GET /v1/contracts/intelligence. fallback_rate_all_time is the
        concrete signal that agents want a kind that doesn't exist yet."""
        with closing(sqlite3.connect(db_path)) as db:
            row = db.execute("SELECT COUNT(*), SUM(fallback) FROM query_log").fetchone()
        total, fallback_total = (row[0] or 0), (row[1] or 0)
        kinds = [{"kind": name, "metric": "/".join(KIND_METRICS[name]), "description": KIND_DESCRIPTIONS[name],
                  "is_default_fallback": name == DEFAULT_KIND} for name in sorted(KIND_METRICS)]
        return {"kinds": kinds, "default_fallback_kind": DEFAULT_KIND,
                "fallback_rate_all_time": round(fallback_total / total, 4) if total else None,
                "total_queries_observed": total, "schema_version": "1.0.0"}
