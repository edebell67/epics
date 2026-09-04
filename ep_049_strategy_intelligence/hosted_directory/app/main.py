"""EP049 strategy-intelligence service - standalone FastAPI host for the
agent-queryable query/discovery API, the EP052 Arena intelligence provider,
and per-user intelligence objects (watchlists, saved searches, collections).

Extracted from epics/ep_051_strategy_directory/hosted_directory/app/main.py
(where these routes and their helper closures originally lived alongside
EP051's own directory-listing routes) into its own deployable service, per
Ed's explicit EP049 ownership decision. app.config/app.contracts/app.repository
are now vendored copies of EP051's (see their own version histories) living
directly under this service's own app/, not merged in via namespace package -
this service has its own Dockerfile/requirements.txt and deploys standalone
on its own Render rootDir, independent of EP051's filesystem path.

Postgres/memory backends only - unlike EP051, this service never runs
against local SQL Server, so none of the sqlserver-only fast-path branches
that existed in the original closures were carried over; only the
repository-backed implementations built during the EP051 Postgres port
(FS commit 9c74a022) needed moving.

Version history:
- 1.1.0 (2026-09-04): Vendors app.config/app.contracts/app.repository locally
  (previously reused via namespace-package merge with EP051's directory) and
  adds a module-level `app = create_app()` ASGI instance, so this service can
  deploy standalone with its own Dockerfile/requirements.txt, independent of
  EP051's filesystem/package path.
- 1.0.0 (2026-09-04): Initial standalone extraction from EP051's main.py.
"""
from __future__ import annotations
import hashlib, hmac, json, os, statistics, subprocess, time as clock
from threading import Lock
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, Path as ApiPath, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.contracts import Strategy
from app.repository import MemoryRepository, PostgresRepository, rebase_equity_rows
from app.intelligence.profile import UNITS, build_profile
from app.intelligence.metrics import calculate as calculate_metrics
from app.intelligence.comparative import cohort_percentiles, correlation, related_strategies, score_profile, similarity
from app.intelligence.discovery import NaturalLanguageRequest, StrategyQuery, chain, exclusion_trace, facet_counts, interpret_with_trace, retrieve
from app.intelligence.user import PostgresUserIntelligenceStore, UserIntelligenceStore, preference_trace
from app.intelligence.regime import classify, recommend, strategy_regime_profile
from app.intelligence.market import MarketFeatureStore, PostgresMarketFeatureStore, build_regime_label_index, freshness_limit, join_regimes_bisect, join_regimes_without_lookahead
from app.intelligence.contracts import (ChainRequest, CollectionRequest, ConsentRequest, PreferenceRequest,
    MarketFeatureIngestRequest, RecommendationRequest, RegimeFeaturesRequest, SavedSearchRequest, SearchRequest,
    SimilarDaysRequest, TimeTravelRequest, TimeTravelSeriesRequest, TimeWindowRequest, TopPerformersRequest)
from app.intelligence import regime_shape
from app import arena_provider


def _detect_build_sha() -> str | None:
    sha = os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("GIT_COMMIT_SHA")
    if sha:
        return sha
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
            stderr=subprocess.DEVNULL, timeout=2,
        ).decode().strip()
    except Exception:
        return None


BUILD_SHA = _detect_build_sha()


def create_app(repository=None, settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    repo = repository or (PostgresRepository(cfg.database_url) if cfg.data_backend == "postgres" and cfg.database_url else None)
    app = FastAPI(title="EP049 Strategy Intelligence API", version="1.0.0", docs_url=None, redoc_url=None)
    user_store = PostgresUserIntelligenceStore(cfg.database_url, maintenance_database_url=cfg.maintenance_database_url) if cfg.data_backend == "postgres" and cfg.database_url else UserIntelligenceStore()
    market_store = PostgresMarketFeatureStore(cfg.database_url) if cfg.data_backend == "postgres" and cfg.database_url else MarketFeatureStore()
    app.state.repository = repo; app.state.settings = cfg; app.state.user_intelligence = user_store; app.state.market_features = market_store
    app.state.profile_cache = {"at": 0.0, "profiles": None, "curves": None}; app.state.profile_cache_lock = Lock()
    app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-User-ID"])

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"; response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    def trusted_user(authorization: str | None = Header(None), x_user_id: str | None = Header(None, alias="X-User-ID")):
        """Trust user identity only behind the configured shared edge boundary."""
        expected = cfg.intelligence_user_token or ""; supplied = (authorization or "").removeprefix("Bearer ")
        if not expected: raise HTTPException(503, "Private intelligence identity is not configured")
        if not hmac.compare_digest(supplied, expected): raise HTTPException(401, "Unauthorized")
        if not x_user_id or len(x_user_id) > 128: raise HTTPException(401, "A trusted user identity is required")
        return x_user_id

    def trusted_publisher(authorization: str | None = Header(None)):
        expected = cfg.sync_token or ""; supplied = (authorization or "").removeprefix("Bearer ")
        if not expected or not hmac.compare_digest(supplied, expected): raise HTTPException(401, "Unauthorized")

    def cached_summary(profile, points=None):
        metrics = profile["metrics"]; evidence = profile["evidence"]; identity = profile["identity"]; classification = profile["classification"]
        if points is None:
            total = int(evidence["trade_count"]); net = metrics["total_return"]["value"] or 0; rate = metrics["win_rate"]["value"]
            wins = round(total * rate) if rate is not None else 0; losses = total - wins
        else:
            returns = [float(point["net_return"]) for point in points]; total = len(returns); net = sum(returns); wins = sum(value > 0 for value in returns); losses = sum(value < 0 for value in returns); rate = wins / total if total else 0.0
            gains = sum(value for value in returns if value > 0); loss_value = abs(sum(value for value in returns if value < 0)); profit_factor = gains / loss_value if loss_value else None
        instruments = classification.get("instruments") or []
        return Strategy(strategy_id=identity["strategy_id"], descriptive_name=identity.get("name"), market=classification.get("asset_class") or "FX", product_name=", ".join(instruments) or None, status="active", total_trades=total, wins=wins, losses=losses, breakevens=total - wins - losses, total_net_return=net, win_rate=rate, profit_factor=metrics["profit_factor"]["value"] if points is None else profit_factor, max_drawdown_money=metrics["max_drawdown"]["value"] if points is None else min((point["drawdown"] for point in points), default=None), quality_state="VALID" if total >= 30 else "COLLECTING", evidence_start=evidence.get("start") if points is None else (points[0]["closed_at"] if points else None), evidence_end=evidence.get("end") if points is None else (points[-1]["closed_at"] if points else None))

    def all_profiles():
        """Repository-backed profile pool, TTL-cached (intelligence_profile_cache_seconds,
        default 60s) rather than invalidated by an explicit signal - this
        service runs as its own process, separate from whichever service
        actually ingests/promotes a new snapshot, so it cannot be notified
        synchronously the way the original single-process closure was."""
        cached = app.state.profile_cache
        if cached["profiles"] is not None and clock.monotonic() - cached["at"] < cfg.intelligence_profile_cache_seconds:
            return cached["profiles"]
        with app.state.profile_cache_lock:
            cached = app.state.profile_cache
            if cached["profiles"] is not None and clock.monotonic() - cached["at"] < cfg.intelligence_profile_cache_seconds:
                return cached["profiles"]
            if app.state.repository is None: raise HTTPException(503, "Intelligence repository is not configured")
            profiles = app.state.repository.current_profiles(); curves = app.state.repository.current_equity_curves()
            for profile in profiles: profile.setdefault("score", score_profile(profile))
            app.state.profile_cache = {"at": clock.monotonic(), "profiles": profiles, "curves": curves}; return profiles

    def _parse_ts(value):
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00")); return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)

    def cached_points(strategy_id, start=None, end=None):
        if app.state.repository is None: return None
        points = app.state.repository.current_equity_curves().get(strategy_id, [])
        filtered = [p for p in points if (start is None or _parse_ts(p["closed_at"]) >= start) and (end is None or _parse_ts(p["closed_at"]) < end)]
        return rebase_equity_rows(filtered)

    def resolved_profile(strategy_id, start=None, end=None):
        return next((profile for profile in all_profiles() if profile["identity"]["strategy_id"] == strategy_id), None)

    def repository_points_today():
        """'Today' is the calendar date of the latest observed trade in the
        published data (already tz-aware real UTC), not the system clock's
        date - the hosted snapshot is published periodically, not truly live."""
        if app.state.repository is None: return {}
        curves = app.state.repository.current_equity_curves()
        latest = None
        for points in curves.values():
            for point in points:
                stamp = _parse_ts(point["closed_at"])
                if latest is None or stamp > latest: latest = stamp
        if latest is None: return {}
        day_start = datetime.combine(latest.date(), time.min, timezone.utc); day_end = day_start + timedelta(days=1)
        out = {}
        for strategy_id, points in curves.items():
            todays = [p for p in points if day_start <= _parse_ts(p["closed_at"]) < day_end]
            if todays: out[strategy_id] = todays
        return out

    def current_now(fresh=None):
        fresh = repository_points_today() if fresh is None else fresh
        latest = None
        for points in fresh.values():
            for point in points:
                stamp = _parse_ts(point["closed_at"])
                if latest is None or stamp > latest: latest = stamp
        return latest or datetime.now(timezone.utc)

    def strategy_names():
        return {p["identity"]["strategy_id"]: p["identity"].get("name") for p in all_profiles()}

    def basis_profiles(end, return_basis="net_return", start=None):
        """Bulk profiles built directly from repository trade data, under the
        requested return_basis and bounded to trades closed in [start, end)
        (start=None = since inception, end=None = through now). Strategies
        with zero eligible trades in that window/basis are excluded - they
        weren't evidenced under that basis, so a screen correctly cannot have
        selected them. alt_net_return reverses every trade, so this is also
        how a query answers 'would fading this have worked'."""
        if app.state.repository is None: return None
        out = []
        for source in all_profiles():
            strategy_id = source["identity"]["strategy_id"]
            points = cached_points(strategy_id, start, end) or []
            points = [p for p in points if p.get(return_basis) is not None]
            if not points: continue
            profile = build_profile(cached_summary(source, points).model_dump(mode="json"), points, return_basis).model_dump(mode="json")
            profile["score"] = score_profile(profile); out.append(profile)
        return out

    def forward_performance(strategy_ids, start, end, return_basis="net_return"):
        results = []
        for strategy_id in strategy_ids:
            points = cached_points(strategy_id, start, end)
            if points is None: continue
            points = [p for p in points if p.get(return_basis) is not None]
            computed = calculate_metrics([float(p[return_basis]) for p in points])
            results.append({"strategy_id": strategy_id, "forward_trade_count": len(points), "forward_net_return": computed["total_return"], "forward_win_rate": computed["win_rate"]})
        traded = [r for r in results if r["forward_trade_count"] > 0]
        positive_rate = round(sum(r["forward_net_return"] > 0 for r in traded) / len(traded), 4) if traded else None
        aggregate = {"strategy_count": len(results), "traded_count": len(traded),
                   "mean_forward_net_return": round(statistics.mean(r["forward_net_return"] for r in traded), 4) if traded else None,
                   "positive_rate": positive_rate, "effectiveness_pct": round(positive_rate * 100, 1) if positive_rate is not None else None}
        return results, aggregate

    def run_timetravel(plan, as_of, forward_to):
        """Evaluate `plan` using only evidence available on `as_of`, then measure
        how the matched strategies actually performed afterwards (as_of, forward_to],
        against a same-window baseline of the whole as-of-eligible universe."""
        as_of_end = datetime.combine(as_of + timedelta(days=1), time.min, timezone.utc)
        universe = basis_profiles(as_of_end, plan.return_basis)
        if universe is None: raise HTTPException(503, "Intelligence repository is not configured")
        matched = retrieve(universe, plan); matched = matched[:cfg.intelligence_max_query_results]
        matched_ids = [item["profile"]["identity"]["strategy_id"] for item in matched]
        names = {item["profile"]["identity"]["strategy_id"]: item["profile"]["identity"].get("name") for item in matched}
        as_of_metrics = {item["profile"]["identity"]["strategy_id"]: {key: item["profile"]["metrics"][key]["value"] for key in ("win_rate", "sharpe", "profit_factor", "max_drawdown")} for item in matched}
        forward_end = datetime.combine(forward_to + timedelta(days=1), time.min, timezone.utc)
        matched_forward, matched_aggregate = forward_performance(matched_ids, as_of_end, forward_end, plan.return_basis)
        for row in matched_forward: row["name"] = names.get(row["strategy_id"]); row["as_of_metrics"] = as_of_metrics.get(row["strategy_id"])
        universe_ids = [p["identity"]["strategy_id"] for p in universe]
        _, baseline_aggregate = forward_performance(universe_ids, as_of_end, forward_end, plan.return_basis)
        lift = (round(matched_aggregate["mean_forward_net_return"] - baseline_aggregate["mean_forward_net_return"], 4)
              if matched_aggregate["mean_forward_net_return"] is not None and baseline_aggregate["mean_forward_net_return"] is not None else None)
        return {"as_of": as_of, "query_universe_size": len(universe),
                "matched_at_as_of": {"count": len(matched_ids), "strategy_ids": matched_ids},
                "forward_window": {"from": as_of_end.date().isoformat(), "to": forward_to.isoformat()},
                "forward_performance": {"matched": matched_aggregate, "baseline_all_as_of_strategies": baseline_aggregate, "lift_vs_baseline": lift, "per_strategy": matched_forward}}

    CONSISTENCY_WEIGHTS = {"outperform_rate": 0.6, "stability": 0.4}
    CONSISTENCY_METHOD_VERSION = "1.0.0"

    def series_consistency(series):
        days = [d for d in series if d["effectiveness_pct"] is not None]
        if not days: return {"days_with_data": 0, "consistency_score": None, "confidence_band": "insufficient evidence", "methodology_version": CONSISTENCY_METHOD_VERSION}
        values = [d["effectiveness_pct"] for d in days]; lifts = [d["lift_vs_baseline"] for d in days if d["lift_vs_baseline"] is not None]
        stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
        stability = max(0.0, 1 - stdev / 100)
        outperform_rate = round(sum(value > 0 for value in lifts) / len(lifts), 4) if lifts else None
        score = CONSISTENCY_WEIGHTS["outperform_rate"] * (outperform_rate or 0) + CONSISTENCY_WEIGHTS["stability"] * stability
        band = "insufficient evidence" if len(days) < 3 else "high" if score >= 0.75 else "medium" if score >= 0.5 else "low"
        return {"days_with_data": len(days), "mean_effectiveness_pct": round(statistics.mean(values), 1), "stdev_effectiveness_pct": round(stdev, 1),
                "min_effectiveness_pct": min(values), "max_effectiveness_pct": max(values), "days_beating_baseline": sum(value > 0 for value in lifts) if lifts else None,
                "outperform_rate": outperform_rate, "consistency_score": round(score, 4), "confidence_band": band,
                "weights": CONSISTENCY_WEIGHTS, "methodology_version": CONSISTENCY_METHOD_VERSION}

    @app.post("/api/intelligence/query/timetravel")
    def timetravel_query(request: TimeTravelRequest):
        """Point-in-time query backtest for a single as-of date."""
        forward_to = request.forward_to or datetime.now(timezone.utc).date()
        result = run_timetravel(request.plan, request.as_of, forward_to)
        return {"plan": request.plan.model_dump(mode="json"), **result,
                "notice": "walk_forward and live_backtest_divergence are re-windowed to as_of; parameter_sensitivity still requires a separately tracked parameter-run table and stays COLLECTING.",
                "schema_version": "1.0.0"}

    @app.post("/api/intelligence/query/timetravel/series")
    def timetravel_series(request: TimeTravelSeriesRequest):
        """Day-by-day point-in-time backtest: for every as-of date in
        [as_of_from, as_of_to], evaluate `plan` as of that day and measure the
        matched strategies' effectiveness over the following `forward_days`."""
        series = []; cursor = request.as_of_from
        while cursor <= request.as_of_to:
            forward_to = cursor + timedelta(days=request.forward_days)
            if forward_to > date.today(): break
            result = run_timetravel(request.plan, cursor, forward_to)
            series.append({"as_of": cursor.isoformat(), "matched_count": result["matched_at_as_of"]["count"],
                           "effectiveness_pct": result["forward_performance"]["matched"]["effectiveness_pct"],
                           "mean_forward_net_return": result["forward_performance"]["matched"]["mean_forward_net_return"],
                           "baseline_effectiveness_pct": result["forward_performance"]["baseline_all_as_of_strategies"]["effectiveness_pct"],
                           "lift_vs_baseline": result["forward_performance"]["lift_vs_baseline"]})
            cursor += timedelta(days=1)
        consistency = series_consistency(series)
        return {"plan": request.plan.model_dump(mode="json"), "forward_days": request.forward_days, "days_evaluated": len(series), "series": series, "consistency": consistency,
                "notice": "A day is omitted when its forward window would extend past today. Robustness fields are all-time, not re-windowed per as_of.",
                "schema_version": "1.0.0"}

    def regime_index_path(instrument):
        index_dir = Path(cfg.regime_shape_index_dir); index_dir = index_dir if index_dir.is_absolute() else Path(__file__).resolve().parents[1] / index_dir
        return index_dir / f"{instrument.upper()}.json"

    @app.post("/api/intelligence/regime/similar-days")
    def regime_similar_days(request: SimilarDaysRequest):
        """Find historical days whose intraday price shape is closest to a
        target day, then reports how the strategy actually performed on
        each matched day. Reads only the pre-built index
        (sync/warm_regime_shape_index.py)."""
        profile = resolved_profile(request.strategy_id)
        if profile is None: raise HTTPException(404, "Strategy evidence was not found")
        instruments = profile["classification"].get("instruments") or []
        if not instruments: raise HTTPException(422, "Strategy has no traded instrument to build a regime shape from")
        instrument = instruments[0].upper()
        cache_path = regime_index_path(instrument)
        index = regime_shape.load_index(cache_path)
        if not index: raise HTTPException(503, f"No regime-shape index for {instrument} yet; run: python -m sync.warm_regime_shape_index --instrument {instrument}")
        as_of = request.as_of or date.today(); as_of_str = as_of.isoformat()
        if as_of_str in index and request.through_hour is None:
            target = index[as_of_str]
        elif as_of_str in index:
            target = index[as_of_str][:request.through_hour + 1]
        else:
            root = cfg.regime_price_capture_root
            if not root or not Path(root).exists(): raise HTTPException(503, f"{as_of_str} is not indexed and the price-capture source is not reachable")
            target = regime_shape.build_day_vector_for_date(Path(root), instrument, as_of, request.through_hour)
            if target is None: raise HTTPException(404, f"No price-capture data for {instrument} on {as_of_str}")
        candidates = {day: vector for day, vector in index.items() if day != as_of_str}
        ranked = regime_shape.find_similar_days(target, candidates, min_periods=cfg.regime_shape_min_periods)[:request.top_n]
        for row in ranked:
            day = date.fromisoformat(row["date"]); start = datetime.combine(day, time.min, timezone.utc); end = start + timedelta(days=1)
            points = cached_points(request.strategy_id, start, end) or []
            computed = calculate_metrics([float(p["net_return"]) for p in points]) if points else None
            row["strategy_performance"] = {"trade_count": len(points), "net_return": computed["total_return"] if computed else None, "win_rate": computed["win_rate"] if computed else None}
        return {"strategy_id": request.strategy_id, "instrument": instrument, "as_of": as_of_str, "through_hour": request.through_hour,
                "target_periods": sum(1 for p in target if p is not None), "index_size": len(index), "similar_days": ranked,
                "notice": "Distance is Euclidean over whichever hourly periods both days have (min " + str(cfg.regime_shape_min_periods) + " overlapping periods required). strategy_performance is that day's actual, real trades - not a prediction.",
                "schema_version": "1.0.0"}

    @app.get("/healthz")
    def health(): return {"status": "ok", "build_sha": BUILD_SHA[:12] if BUILD_SHA else None}

    @app.get("/readyz")
    def ready():
        try:
            if app.state.repository is None: raise HTTPException(503, "Intelligence repository is not configured")
        except HTTPException: raise
        except Exception: raise HTTPException(503, "Intelligence data is unavailable")
        return {"status": "ready"}

    @app.get("/api/intelligence/strategies/{strategy_id}")
    def intelligence_profile(strategy_id: str = ApiPath(pattern=r"^DNA_[A-Za-z0-9]+$"), date_from: date | None = Query(None), date_to: date | None = Query(None), fields: str | None = Query(None, max_length=120, pattern=r"^[a-z_,]*$")):
        if date_from and date_to and date_from > date_to: raise HTTPException(422, "date_from must be on or before date_to")
        start = datetime.combine(date_from, time.min, timezone.utc) if date_from else None
        end = datetime.combine(date_to + timedelta(days=1), time.min, timezone.utc) if date_to else None
        payload = resolved_profile(strategy_id, start, end)
        if payload is None: raise HTTPException(404, "Strategy evidence was not found")
        if fields:
            selected = [field for field in fields.split(",") if field]; allowed = {"schema_version", "generated_at", "identity", "classification", "metrics", "evidence", "robustness", "links", "methodology"}
            if any(field not in allowed for field in selected): raise HTTPException(422, "Unsupported profile field selection")
            payload = {field: payload[field] for field in selected}
        return payload

    @app.get("/api/intelligence/metric-registry")
    def metric_registry():
        return {"methodology_version": "1.0.0", "metrics": [{"name": name, "unit": unit, "computed_by": "intelligence-layer"} for name, unit in UNITS.items()]}

    @app.get("/api/intelligence/strategies/{strategy_id}/score")
    def intelligence_score(strategy_id: str = ApiPath(pattern=r"^DNA_[A-Za-z0-9]+$")):
        profile = resolved_profile(strategy_id)
        if profile is None: raise HTTPException(404, "Strategy evidence was not found")
        return {"strategy_id": strategy_id, "score": profile.get("score") or score_profile(profile)}

    def comparative_records():
        records = []
        for profile in all_profiles():
            classification = profile["classification"]; metrics = profile["metrics"]; records.append({"strategy_id": profile["identity"]["strategy_id"], "quality_score": profile["score"]["quality_score"], "win_rate": metrics["win_rate"]["value"], "profit_factor": metrics["profit_factor"]["value"], "max_drawdown": metrics["max_drawdown"]["value"], "asset_class": classification["asset_class"], "family": classification.get("strategy_family"), "instrument": (classification.get("instruments") or [None])[0], "track_record": int(profile["evidence"]["years"] or 0)})
        return records

    @app.get("/api/intelligence/cohorts")
    def intelligence_cohorts(metric: str = Query("quality_score", pattern=r"^(quality_score|win_rate|profit_factor|max_drawdown)$")):
        records = comparative_records(); return {"metric": metric, "minimum_cohort_size": 5, "items": cohort_percentiles(records, metric), "methodology_version": "1.1.0"}

    @app.get("/api/intelligence/strategies/{strategy_id}/related")
    def intelligence_related(strategy_id: str = ApiPath(pattern=r"^DNA_[A-Za-z0-9]+$"), limit: int = Query(5, ge=1, le=20)):
        records = comparative_records(); target = next((item for item in records if item["strategy_id"] == strategy_id), None)
        if target is None: raise HTTPException(404, "Strategy intelligence was not found")
        return {"strategy_id": strategy_id, "items": related_strategies(target, records, limit), "methodology_version": "1.1.0"}

    @app.get("/api/intelligence/compare")
    def intelligence_compare(strategy_ids: str = Query(min_length=1, max_length=160), format: str = Query("json", pattern=r"^(json|csv)$")):
        ids = [x.strip().upper() for x in strategy_ids.split(",") if x.strip()]
        if len(ids) < 2 or len(ids) > 5 or any(not x.startswith("DNA_") for x in ids): raise HTTPException(422, "Provide 2 to 5 canonical strategy IDs")
        profiles = {}
        for strategy_id in ids:
            profile = resolved_profile(strategy_id)
            if profile is None: raise HTTPException(404, f"{strategy_id} was not found")
            profile = dict(profile); profile.setdefault("score", score_profile(profile)); profiles[strategy_id] = profile
        if app.state.repository is None: raise HTTPException(503, "Intelligence repository is not configured")
        daily = app.state.repository.current_daily_returns(ids, 2000)
        relationships = []
        for index, left in enumerate(ids):
            for right in ids[index + 1:]:
                lreturns = daily[left]; rreturns = daily[right]
                lf = {"quality_score": profiles[left]["score"]["quality_score"], "win_rate": profiles[left]["metrics"]["win_rate"]["value"], "profit_factor": profiles[left]["metrics"]["profit_factor"]["value"], "max_drawdown": profiles[left]["metrics"]["max_drawdown"]["value"]}
                rf = {"quality_score": profiles[right]["score"]["quality_score"], "win_rate": profiles[right]["metrics"]["win_rate"]["value"], "profit_factor": profiles[right]["metrics"]["profit_factor"]["value"], "max_drawdown": profiles[right]["metrics"]["max_drawdown"]["value"]}
                relationships.append({"left": left, "right": right, "correlation": correlation(lreturns, rreturns), "similarity": similarity(lf, rf)})
        starts = [p["evidence"]["start"] for p in profiles.values() if p["evidence"]["start"]]
        ends = [p["evidence"]["end"] for p in profiles.values() if p["evidence"]["end"]]
        warnings = []
        if starts and ends and (min(starts) != max(starts) or min(ends) != max(ends)):
            warnings.append("Evidence windows differ; period-sensitive metrics are not directly comparable.")
        payload = {"profiles": profiles, "relationships": relationships, "warnings": warnings, "methodology_version": "1.0.0"}
        if format == "csv":
            columns = ("strategy_id", "quality_score", "annualized_return", "win_rate", "sharpe", "max_drawdown", "evidence_start", "evidence_end"); lines = [",".join(columns)]
            for strategy_id, profile in profiles.items():
                values = (strategy_id, profile["score"]["quality_score"], profile["metrics"]["annualized_return"]["value"], profile["metrics"]["win_rate"]["value"], profile["metrics"]["sharpe"]["value"], profile["metrics"]["max_drawdown"]["value"], profile["evidence"]["start"], profile["evidence"]["end"]); lines.append(",".join("" if value is None else str(value) for value in values))
            return Response("\n".join(lines), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=dna-strategy-comparison.csv"})
        return payload

    @app.post("/api/intelligence/query/interpret")
    def interpret_intelligence_query(request: NaturalLanguageRequest):
        result = interpret_with_trace(request.query); plan = result.pop("plan")
        return {"query": request.query, "plan": plan.model_dump(mode="json"), **result, "schema_version": "1.0.0",
                "notice": "The plan is validated and must be applied before ranking."}

    def attach_regimes(profiles, curves, return_basis="net_return"):
        """Populate profile["regimes"] the same way /recommendations already
        does per-strategy, but in bulk across a whole profile pool via a
        bisect join so StrategyQuery.regime works as a real filter/rank input."""
        if not profiles: return profiles
        now = datetime.now(timezone.utc); by_market = {}
        for profile in profiles:
            if profile.get("regimes"): continue
            by_market.setdefault(profile["classification"].get("asset_class") or "FX", []).append(profile)
        for market, group in by_market.items():
            history = app.state.market_features.history(market, through=now)
            if not history:
                for profile in group: profile["regimes"] = {}
                continue
            labels = [{"as_of": row["as_of"], "state": classify(row["features"])["state"]} for row in history]
            index = build_regime_label_index(labels)
            for profile in group:
                strategy_id = profile["identity"]["strategy_id"]
                points = [point for point in curves.get(strategy_id, []) if point.get(return_basis) is not None]
                returns = [{"timestamp": point["closed_at"], "return": float(point[return_basis])} for point in points]
                joined = join_regimes_bisect(returns, index)
                profile["regimes"] = strategy_regime_profile(joined, minimum=cfg.intelligence_min_regime_samples)
        return profiles

    def query_pool(return_basis="net_return", lookback_hours=None):
        """The candidate universe a query/chain runs against. lookback_hours
        (None = since inception) makes this a trailing-window pool - every
        metric/filter/rank recomputed from just the last N hours, via the
        same basis_profiles() used for alt_net_return."""
        if lookback_hours is None and return_basis == "net_return":
            profiles = all_profiles(); curves = app.state.profile_cache.get("curves") or {}
            return attach_regimes(profiles, curves, return_basis)
        start = datetime.now(timezone.utc) - timedelta(hours=lookback_hours) if lookback_hours is not None else None
        pool = basis_profiles(None, return_basis, start=start)
        if pool is None: raise HTTPException(503, "Intelligence repository is not configured")
        return attach_regimes(pool, {}, return_basis)

    @app.post("/api/intelligence/query/search")
    def search_intelligence(request: SearchRequest):
        profiles = query_pool(request.plan.return_basis, request.plan.lookback_hours); all_results = retrieve(profiles, request.plan); results = all_results[:cfg.intelligence_max_query_results]; all_exclusions = exclusion_trace(profiles, request.plan)
        return {"plan": request.plan.model_dump(mode="json"), "items": results, "total": len(all_results), "facets": facet_counts([item["profile"] for item in all_results]), "exclusions": all_exclusions[:cfg.intelligence_max_query_results], "excluded_total": len(all_exclusions),
                "constraint_order": "filter-before-rank", "schema_version": "1.0.0"}

    def _window_ts(value):
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00")); return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)

    @app.post("/api/intelligence/query/top-performers")
    def top_performers(request: TopPerformersRequest):
        """Canned answer to 'top N strategies in the last H hours, among
        strategies with at least M trades today' - two DIFFERENT windows,
        not one: min_trade_count is an activity/liquidity gate over the
        WHOLE day, while the ranked return is computed only from trades
        inside the last lookback_hours."""
        fresh = repository_points_today()
        now = current_now(fresh); window_start = now - timedelta(hours=request.lookback_hours)
        names = strategy_names()
        candidates = []
        for strategy_id, points in fresh.items():
            valid = [p for p in points if p.get(request.return_basis) is not None]
            if len(valid) < request.min_trade_count: continue
            window_points = [p for p in valid if window_start <= _window_ts(p["closed_at"]) < now]
            if not window_points: continue
            window_return = sum(float(p[request.return_basis]) for p in window_points)
            wins = sum(1 for p in window_points if float(p[request.return_basis]) > 0)
            candidates.append({"strategy_id": strategy_id, "name": names.get(strategy_id),
                "trades_today": len(valid), "trades_in_window": len(window_points),
                "window_return": round(window_return, 4), "window_win_rate": round(wins / len(window_points), 4)})
        sort_key = {"annualized_return": "window_return", "win_rate": "window_win_rate"}.get(request.sort, "window_return")
        candidates.sort(key=lambda row: row[sort_key], reverse=True)
        results = candidates[:request.top_n]
        return {"now": now.isoformat(), "window": {"from": window_start.isoformat(), "to": now.isoformat()}, "time_basis": "UTC, as published in directory_return_series",
                "lookback_hours": request.lookback_hours, "min_trade_count_today": request.min_trade_count,
                "candidates_meeting_trade_count": len(candidates), "items": results,
                "notice": "min_trade_count is evaluated against today's TOTAL trades, not just trades inside the lookback window; window_return/window_win_rate are computed only from trades inside the lookback window.",
                "schema_version": "1.0.0"}

    @app.post("/api/intelligence/query/time-window")
    def time_window_query(request: TimeWindowRequest):
        """Screen today's strategies by performance within a fixed clock-time
        window - distinct from /query/top-performers' trailing lookback_hours
        from now."""
        fresh = repository_points_today(); today = current_now(fresh).date()
        before_dt = datetime.combine(today, datetime.strptime(request.before, "%H:%M").time()).replace(tzinfo=timezone.utc) if request.before else None
        after_dt = datetime.combine(today, datetime.strptime(request.after, "%H:%M").time()).replace(tzinfo=timezone.utc) if request.after else None
        names = strategy_names()
        candidates = []
        for strategy_id, points in fresh.items():
            valid = [p for p in points if p.get(request.return_basis) is not None]
            windowed = [p for p in valid if (before_dt is None or _window_ts(p["closed_at"]) < before_dt) and (after_dt is None or _window_ts(p["closed_at"]) >= after_dt)]
            if len(windowed) < request.min_trade_count: continue
            wins = sum(1 for p in windowed if float(p[request.return_basis]) > 0)
            win_rate = wins / len(windowed) if windowed else None
            if request.min_win_rate is not None and (win_rate is None or win_rate < request.min_win_rate): continue
            net = sum(float(p[request.return_basis]) for p in windowed)
            candidates.append({"strategy_id": strategy_id, "name": names.get(strategy_id), "trade_count": len(windowed),
                                "win_rate": round(win_rate, 4) if win_rate is not None else None, "net_return": round(net, 4)})
        candidates.sort(key=lambda row: (row[request.sort] if row[request.sort] is not None else float("-inf")), reverse=True)
        results = candidates[:request.top_n]
        return {"date": today.isoformat(), "before": request.before, "after": request.after, "time_basis": "UTC, as published in directory_return_series",
                "min_trade_count": request.min_trade_count, "min_win_rate": request.min_win_rate, "sort": request.sort,
                "candidates_meeting_criteria": len(candidates), "items": results,
                "notice": "min_trade_count and min_win_rate are evaluated over trades strictly inside the [after, before) time-of-day window, not the whole day.",
                "schema_version": "1.0.0"}

    @app.post("/api/intelligence/query/chain")
    def chain_intelligence_query(request: ChainRequest):
        """Apply up to 10 StrategyQuery stages as a narrowing funnel: each
        stage's survivors feed the next."""
        profiles = query_pool(request.stages[0].return_basis, request.stages[0].lookback_hours); result = chain(profiles, request.stages); result_items = result["items"][:cfg.intelligence_max_query_results]
        return {"stages": result["stages"], "final_total": result["final_count"], "items": result_items,
                "strategy_ids": [item["profile"]["identity"]["strategy_id"] for item in result_items],
                "strategies": [{"strategy_id": item["profile"]["identity"]["strategy_id"], "name": item["profile"]["identity"].get("name")} for item in result_items],
                "constraint_order": "filter-before-rank, sequential per stage", "schema_version": "1.0.0"}

    @app.get("/api/intelligence/query/schema")
    def query_schema():
        """Machine-readable description of every queryable field, for an
        automated caller (agent) to introspect available screens without
        reading source."""
        return {"single_query_endpoint": "/api/intelligence/query/search", "chain_endpoint": "/api/intelligence/query/chain",
                "timetravel_endpoint": "/api/intelligence/query/timetravel", "timetravel_series_endpoint": "/api/intelligence/query/timetravel/series",
                "top_performers_endpoint": "/api/intelligence/query/top-performers", "time_window_endpoint": "/api/intelligence/query/time-window",
                "chain_max_stages": 10, "timetravel_series_max_range_days": 90, "strategy_query_schema": StrategyQuery.model_json_schema(),
                "top_performers_schema": TopPerformersRequest.model_json_schema(), "time_window_schema": TimeWindowRequest.model_json_schema(),
                "notes": ["Each field on StrategyQuery is an independent AND constraint; omit a field to leave it unconstrained.",
                         "For /query/chain, POST {\"stages\":[StrategyQuery, StrategyQuery, ...]}; the survivors of stage N become the candidate pool for stage N+1.",
                         "For /query/timetravel, POST {\"plan\":StrategyQuery,\"as_of\":date,\"forward_to\":date} to see how strategies matching the query as of a past date actually performed afterwards, vs a same-window baseline.",
                         "For /query/timetravel/series, POST {\"plan\":StrategyQuery,\"as_of_from\":date,\"as_of_to\":date,\"forward_days\":int} for a daily effectiveness_pct series (max 90-day range).",
                         "return_basis (default net_return) selects the outcome every metric/filter/rank/robustness check is computed from. alt_net_return reverses every trade in the ledger, so a query with return_basis=alt_net_return answers 'would fading this strategy have worked'.",
                         "Persist a result as a watchlist via POST /api/intelligence/user/collections with the returned strategy_ids."],
                "schema_version": "1.0.0"}

    @app.get("/api/intelligence/user")
    def user_export(user_id: str = Depends(trusted_user)):
        payload = app.state.user_intelligence.export(user_id)
        try: versions = {profile["identity"]["strategy_id"]: profile.get("generated_at") for profile in all_profiles()}
        except HTTPException: versions = {}
        payload["watchlist_details"] = [{"strategy_id": strategy_id, "saved_evidence_version": payload.get("watch_versions", {}).get(strategy_id), "current_evidence_version": versions.get(strategy_id), "stale": bool(payload.get("watch_versions", {}).get(strategy_id) and payload.get("watch_versions", {}).get(strategy_id) != versions.get(strategy_id))} for strategy_id in payload["watchlist"]]
        for collection in payload["collections"].values(): collection["stale_strategy_ids"] = [strategy_id for strategy_id, version in collection.get("evidence_versions", {}).items() if version and version != versions.get(strategy_id)]
        return payload

    @app.delete("/api/intelligence/user", status_code=204)
    def user_delete(user_id: str = Depends(trusted_user)):
        app.state.user_intelligence.delete(user_id)

    @app.put("/api/intelligence/user/consent")
    def user_consent(request: ConsentRequest, user_id: str = Depends(trusted_user)):
        app.state.user_intelligence.set_consent(user_id, request.history); return {"history": request.history}

    @app.put("/api/intelligence/user/watchlist/{strategy_id}")
    def watch_strategy(strategy_id: str = ApiPath(pattern=r"^DNA_[A-Za-z0-9]+$"), user_id: str = Depends(trusted_user)):
        profile = resolved_profile(strategy_id) if app.state.repository is not None else None
        if profile is None and cfg.data_backend != "memory": raise HTTPException(404, "Strategy evidence was not found")
        version = profile.get("generated_at") if profile else None; app.state.user_intelligence.watch(user_id, strategy_id, version); return {"strategy_id": strategy_id, "watched": True, "evidence_version": version}

    @app.delete("/api/intelligence/user/watchlist/{strategy_id}")
    def unwatch_strategy(strategy_id: str = ApiPath(pattern=r"^DNA_[A-Za-z0-9]+$"), user_id: str = Depends(trusted_user)):
        app.state.user_intelligence.unwatch(user_id, strategy_id); return {"strategy_id": strategy_id, "watched": False}

    @app.post("/api/intelligence/user/searches", status_code=201)
    def save_user_search(request: SavedSearchRequest, user_id: str = Depends(trusted_user)):
        item_id = app.state.user_intelligence.save_search(user_id, request.name, request.plan.model_dump(mode="json")); return {"id": item_id}

    @app.post("/api/intelligence/user/searches/{item_id}/replay")
    def replay_user_search(item_id: str = ApiPath(pattern=r"^[0-9a-fA-F-]{36}$"), user_id: str = Depends(trusted_user)):
        exported = app.state.user_intelligence.export(user_id); item = exported["searches"].get(item_id)
        if item is None: raise HTTPException(404, "Saved search was not found")
        plan = StrategyQuery.model_validate(item["plan"]); results = retrieve(all_profiles(), plan); ids = [result["profile"]["identity"]["strategy_id"] for result in results]
        replay = app.state.user_intelligence.replay_search(user_id, item_id, ids); previous = set(replay["previous_result_ids"])
        return {"id": item_id, "plan": plan.model_dump(mode="json"), "result_ids": ids, "added": sorted(set(ids) - previous), "removed": sorted(previous - set(ids)), "evidence_replayed_at": datetime.now(timezone.utc).isoformat()}

    @app.post("/api/intelligence/user/collections", status_code=201)
    def create_user_collection(request: CollectionRequest, user_id: str = Depends(trusted_user)):
        item_id = app.state.user_intelligence.create_collection(user_id, request.name, request.strategy_ids, request.notes, request.evidence_versions); return {"id": item_id}

    @app.put("/api/intelligence/user/preferences")
    def set_user_preferences(request: PreferenceRequest, user_id: str = Depends(trusted_user)):
        app.state.user_intelligence.set_preferences(user_id, request.preferences)
        return preference_trace(request.preferences, app.state.user_intelligence.export(user_id)["history"])

    @app.delete("/api/intelligence/user/preferences")
    def reset_user_preferences(user_id: str = Depends(trusted_user)):
        app.state.user_intelligence.reset_preferences(user_id); return {"reset": True}

    @app.post("/api/intelligence/regimes/classify")
    def classify_regime(request: RegimeFeaturesRequest):
        now = datetime.now(timezone.utc); at = request.as_of or now
        if at.tzinfo is None or at.utcoffset() is None: raise HTTPException(422, "as_of must include a timezone")
        at = at.astimezone(timezone.utc)
        if at > now + timedelta(minutes=5): raise HTTPException(422, "as_of cannot be in the future")
        row = app.state.market_features.as_of(request.market, at)
        if row is None: return {"market": request.market, "as_of": at, "state": "UNKNOWN", "confidence": 0, "reason": "NO_CANONICAL_FEATURES"}
        age = (at - row["as_of"]).total_seconds(); limit = freshness_limit(at, cfg.intelligence_market_feature_max_age_seconds, cfg.intelligence_market_feature_weekend_max_age_seconds); fresh = age <= limit
        if request.as_of is None and not fresh: return {"market": request.market, "as_of": at, "feature_as_of": row["as_of"], "state": "UNKNOWN", "confidence": 0, "reason": "STALE", "source_version": row["source_version"]}
        return {"market": request.market, "as_of": at, "feature_as_of": row["as_of"], "source_version": row["source_version"], "feature_sha256": row["sha256"], "fresh": fresh, **classify(row["features"])}

    @app.post("/api/intelligence/recommendations")
    def intelligence_recommendations(request: RecommendationRequest):
        now = datetime.now(timezone.utc); at = request.as_of or now
        if at.tzinfo is None or at.utcoffset() is None: raise HTTPException(422, "as_of must include a timezone")
        at = at.astimezone(timezone.utc)
        if at > now + timedelta(minutes=5): raise HTTPException(422, "as_of cannot be in the future")
        row = app.state.market_features.as_of(request.market, at)
        if row is None: return {"items": [], "total": 0, "state": "UNKNOWN", "reason": "NO_CANONICAL_FEATURES", "methodology_version": "1.0.0", "decision_support_only": True}
        age = (at - row["as_of"]).total_seconds()
        limit = freshness_limit(at, cfg.intelligence_market_feature_max_age_seconds, cfg.intelligence_market_feature_weekend_max_age_seconds)
        if age < 0 or age > limit: return {"items": [], "total": 0, "state": "UNKNOWN", "reason": "STALE", "feature_age_seconds": age, "feature_as_of": row["as_of"], "methodology_version": "1.0.0", "decision_support_only": True}
        current = classify(row["features"]); profiles = {item["identity"]["strategy_id"]: item for item in all_profiles()}
        curves = app.state.profile_cache.get("curves") or {}; labels = []
        for feature_row in app.state.market_features.history(request.market, through=at): labels.append({"as_of": feature_row["as_of"], "state": classify(feature_row["features"])["state"]})
        candidates = []
        for strategy_id in request.strategy_ids:
            profile = profiles.get(strategy_id)
            if profile is None: continue
            joined = join_regimes_without_lookahead([{"timestamp": point["closed_at"], "return": point["net_return"]} for point in curves.get(strategy_id, [])], labels)
            regimes = strategy_regime_profile(joined, minimum=cfg.intelligence_min_regime_samples)
            candidates.append({"strategy_id": strategy_id, "quality_score": profile["score"]["quality_score"], "max_drawdown": profile["metrics"]["max_drawdown"]["value"], "regimes": regimes})
        result = recommend(current, candidates, request.risk_limit)
        return {"items": result, "total": len(result), "market": request.market, "regime": current, "feature_as_of": row["as_of"], "feature_age_seconds": age, "mode": "historical" if request.as_of else "current", "source_version": row["source_version"], "feature_sha256": row["sha256"], "methodology_version": "1.0.0", "decision_support_only": True}

    @app.post("/internal/intelligence/market-features", status_code=202)
    def ingest_market_features(request: MarketFeatureIngestRequest, _: None = Depends(trusted_publisher)):
        try:
            digest = app.state.market_features.ingest(request.market, request.as_of, request.features, request.source_version); result = classify(request.features)
            app.state.market_features.record_label(request.market, request.as_of, result, request.as_of, result["version"])
        except ValueError as exc: raise HTTPException(422, str(exc))
        return {"accepted": True, "market": request.market, "as_of": request.as_of, "sha256": digest, "regime": result}

    @app.post("/internal/intelligence/refresh", status_code=202)
    def refresh_intelligence_profiles(_: None = Depends(trusted_publisher)):
        app.state.profile_cache = {"at": 0.0, "profiles": None, "curves": None}
        return {"accepted": True, "reason": "operator-authorized evidence refresh"}

    @app.post("/internal/intelligence/privacy/purge", status_code=202)
    def purge_private_history(_: None = Depends(trusted_publisher)):
        try: return {"state": "completed", "deleted": app.state.user_intelligence.purge_expired()}
        except RuntimeError as exc: raise HTTPException(503, str(exc))

    @app.get("/api/intelligence/warmup-status")
    def warmup_status():
        return {"ready": app.state.profile_cache.get("profiles") is not None, "mode": cfg.data_backend}

    def arena_universe(start, end):
        """Candidate pool for the EP052 Arena intelligence provider: the full
        since-inception pool when no window is given, or the windowed
        basis_profiles() rebuild when one is."""
        if start is None and end is None: return all_profiles()
        return basis_profiles(end, "net_return", start=start)

    arena_provider.install(app, cfg, arena_universe)
    return app


# Module-level ASGI instance for `uvicorn app.main:app` (Render's Dockerfile
# CMD, added 2026-09-04). Settings load from the environment at import time,
# same as create_app()'s own default when called with no arguments.
app = create_app()
