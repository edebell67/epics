"""Container-ready directory API and screen host.

Version history:
- 3.0.0 (2026-09-04): Removes the agent-queryable intelligence query API, per-user
  intelligence objects, market-feature/regime endpoints, and the EP052 Arena
  provider mount - these now live as their own standalone service in
  epics/ep_049_strategy_intelligence/hosted_directory/app/main.py, per Ed's
  explicit EP049 ownership decision. This app keeps only its own directory-
  listing responsibility (strategy list/detail/equity-curve/trades/rank-journey)
  and snapshot ingestion. See that file's own version history for what moved.
- 2.2.0 (2026-09-04): Ports timetravel/timetravel-series/top-performers/time-window off the SQL-Server-only 501 gate onto a repository-backed (Postgres/memory) path, so they work on the hosted deployment.
- 2.1.2 (2026-08-28): Allows caller-selected evidence trade-count threshold, default 5, independently of result filtering.
- 2.1.1 (2026-08-27): Serves the shared Tech Principle screen-theme stylesheet.
- 2.1.0 (2026-08-27): Adds profitable-strategy count and percentage to the selected-period directory summary.
- 2.0.0 (2026-08-25): Defines headline strategies as models executed within the selected period.
- 1.9.0 (2026-08-25): Reports exact constructed product_forex models as a reference total.
- 1.8.0 (2026-08-25): Keeps the full product_forex strategy population in directory summaries.
- 1.8.2 (2026-08-25): Falls back to fresh grant-free period evidence when the local snapshot has no matching day.
- 1.8.1 (2026-08-25): Adds full-filter directory summary totals so the listing can show persistent evidence coverage independently of pagination.
- 1.8.0 (2026-08-24): Caches period directory aggregates and avoids repeated snapshot validation.
- 1.7.0 (2026-08-24): Integrates discovery retrieval, private user objects and fail-closed regime APIs.
- 1.6.0 (2026-08-24): Adds validated natural-language-to-query-plan interpretation endpoint.
- 1.5.0 (2026-08-24): Adds explainable scoring and multi-strategy comparative intelligence APIs.
- 1.4.0 (2026-08-24): Adds the versioned server-side Strategy Intelligence Profile API.
- 1.2.0 (2026-08-24): Adds period-aware strategy equity-curve endpoint.
- 1.1.0 (2026-08-24): Adds inclusive date-range filtering and period metadata to directory responses.
- 1.0.0 (2026-08-23): Local SQL and hosted snapshot modes, ingestion and screens.
"""
from __future__ import annotations
import base64,hashlib,hmac, json,os,re,secrets,subprocess, time as clock
from threading import Lock,Thread
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, Path as ApiPath, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,Response

from .config import Settings, get_settings
from .contracts import Snapshot, SnapshotBatch, SnapshotEnvelope, Strategy
from .repository import MemoryRepository, PostgresRepository, local_closed_trades, local_equity_curve, local_equity_curves, local_period_strategies, local_products, local_rank_journey, local_strategies, rebase_equity_rows
from .intelligence.assurance import OperationsMonitor
from .intelligence.cache import validate_local_cache,validate_local_cache_freshness

WEB = Path(__file__).resolve().parents[1] / "web"


def _detect_build_sha() -> str | None:
    """Identifies exactly which commit this running process was built from,
    so a local checkout and a live deploy can be compared directly instead of
    guessed at - the source-boundary confusion around PUB-04's rollout (two
    different GitHub repos, stale branches) made this worth having. Render
    auto-injects RENDER_GIT_COMMIT for git-backed deploys; falls back to
    asking git directly for a local dev run."""
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


def html_signature():
    # Cheap staleness check (name+mtime+size only, no file reads) so the CSP
    # cache below can detect an edited web/*.html without hashing on every request.
    return tuple(sorted((p.name,p.stat().st_mtime_ns,p.stat().st_size) for p in WEB.glob("*.html")))


def content_security_policy():
    hashes=[]
    for path in WEB.glob("*.html"):
        for script in re.findall(r"<script>(.*?)</script>",path.read_text(encoding="utf-8"),re.DOTALL):
            digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode();hashes.append(f"'sha256-{digest}'")
    return "default-src 'self'; script-src 'self' "+" ".join(sorted(set(hashes)))+"; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"


def create_app(repository=None, settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    repo = repository or (PostgresRepository(cfg.database_url) if cfg.data_backend == "postgres" and cfg.database_url else None)
    app = FastAPI(title="DNA Strategy Directory API", version="1.0.0", docs_url=None, redoc_url=None)
    app.state.repository = repo; app.state.settings = cfg
    app.state.operations=OperationsMonitor()
    app.state.csp_cache={"signature":None,"value":None};app.state.csp_cache_lock=Lock()
    app.state.snapshot_cache={"snapshot":None};app.state.snapshot_cache_lock=Lock()
    app.state.strategy_cache=None;app.state.strategy_cache_lock=Lock()
    app.state.local_snapshot_cache=None
    app.state.local_snapshot_cache_mtime=None
    app.state.period_strategy_cache={}
    app.state.period_strategy_cache_lock=Lock()
    app.state.period_refreshing=set()
    app.state.directory_summary_cache={"mtime":None,"payload":None}
    app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins, allow_credentials=False,
                       allow_methods=["GET","POST","PUT","DELETE"], allow_headers=["Authorization","Content-Type","Idempotency-Key","X-User-ID"])

    def current_csp():
        # Recomputed whenever any web/*.html file's name/mtime/size changes, so an
        # edited inline <script> gets its new hash on the very next request instead
        # of requiring a process restart. The signature check is stat()-only and
        # cheap; the sha256 rehash only runs when it actually changed.
        signature=html_signature();cache=app.state.csp_cache
        if cache["signature"]!=signature:
            with app.state.csp_cache_lock:
                if cache["signature"]!=signature:
                    cache["value"]=content_security_policy();cache["signature"]=signature
        return cache["value"]

    @app.middleware("http")
    async def headers(request: Request, call_next):
        if request.url.path=="/internal/snapshots" or request.url.path.startswith("/internal/snapshots/"):
            raw=request.headers.get("content-length")
            if raw is None:raise HTTPException(411,"Content-Length is required")
            try:size=int(raw)
            except ValueError:raise HTTPException(400,"Invalid Content-Length")
            if size<0 or size>cfg.max_snapshot_bytes:raise HTTPException(413,"Snapshot body limit exceeded")
        request.state.request_id = request.headers.get("X-Request-ID", secrets.token_hex(8))[:64];started=clock.perf_counter()
        try:response = await call_next(request)
        except Exception:
            app.state.operations.observe((clock.perf_counter()-started)*1000,False);raise
        app.state.operations.observe((clock.perf_counter()-started)*1000,response.status_code<500);response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"; response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"]=current_csp();response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
        return response

    def hosted_snapshot():
        # current_snapshot() re-runs a full jsonb_agg reconstruction of every
        # item on each call - expensive with 2000 strategies and was being
        # invoked twice per /api/dna/strategies request with zero caching.
        # Cached here and invalidated on every successful promote/finalize,
        # matching the pattern local_snapshot() already uses for the SQL
        # Server backend.
        if app.state.repository is None:return None
        cached=app.state.snapshot_cache["snapshot"]
        if cached is not None:return cached
        with app.state.snapshot_cache_lock:
            cached=app.state.snapshot_cache["snapshot"]
            if cached is not None:return cached
            snapshot=app.state.repository.current_snapshot()
            app.state.snapshot_cache["snapshot"]=snapshot
            return snapshot

    def invalidate_snapshot_cache():
        with app.state.snapshot_cache_lock:app.state.snapshot_cache["snapshot"]=None

    def local_snapshot():
        if cfg.data_backend!="sqlserver":return None
        cache_path=Path(cfg.local_intelligence_cache_path);cache_path=cache_path if cache_path.is_absolute() else Path(__file__).resolve().parents[1]/cache_path
        try:
            mtime=cache_path.stat().st_mtime_ns
            if app.state.local_snapshot_cache is not None and app.state.local_snapshot_cache_mtime==mtime:
                return validate_local_cache_freshness(app.state.local_snapshot_cache,cfg.local_intelligence_cache_max_age_seconds)
            payload=json.loads(cache_path.read_text(encoding="utf-8"));validate_local_cache(payload,cfg.local_intelligence_cache_max_age_seconds);app.state.local_snapshot_cache=payload;app.state.local_snapshot_cache_mtime=mtime;return payload
        except (OSError,ValueError,KeyError,TypeError):return None

    def cached_summary(profile,points=None):
        metrics=profile["metrics"];evidence=profile["evidence"];identity=profile["identity"];classification=profile["classification"]
        if points is None:
            total=int(evidence["trade_count"]);net=metrics["total_return"]["value"] or 0;rate=metrics["win_rate"]["value"]
            wins=round(total*rate) if rate is not None else 0;losses=total-wins
        else:
            returns=[float(point["net_return"]) for point in points];total=len(returns);net=sum(returns);wins=sum(value>0 for value in returns);losses=sum(value<0 for value in returns);rate=wins/total if total else 0.0
            gains=sum(value for value in returns if value>0);loss_value=abs(sum(value for value in returns if value<0));profit_factor=gains/loss_value if loss_value else None
        instruments=classification.get("instruments") or []
        return Strategy(strategy_id=identity["strategy_id"],descriptive_name=identity.get("name"),market=classification.get("asset_class") or "FX",product_name=", ".join(instruments) or None,status="active",total_trades=total,wins=wins,losses=losses,breakevens=total-wins-losses,total_net_return=net,win_rate=rate,profit_factor=metrics["profit_factor"]["value"] if points is None else profit_factor,max_drawdown_money=metrics["max_drawdown"]["value"] if points is None else min((point["drawdown"] for point in points),default=None),quality_state="VALID" if total>=30 else "COLLECTING",evidence_start=evidence.get("start") if points is None else (points[0]["closed_at"] if points else None),evidence_end=evidence.get("end") if points is None else (points[-1]["closed_at"] if points else None))

    def refresh_period_in_background(cache_key,start,end,canonical_strategy):
        try:
            refreshed=[Strategy.model_validate(x) for x in local_period_strategies(
                cfg,start.replace(tzinfo=None),end.replace(tzinfo=None),canonical_strategy
            )]
            with app.state.period_strategy_cache_lock:
                app.state.period_strategy_cache[cache_key]=refreshed
        finally:
            with app.state.period_strategy_cache_lock:
                app.state.period_refreshing.discard(cache_key)

    def period_cache_key(date_from, date_to, canonical_strategy):
        """Refresh a live/current period at least once per minute."""
        today = datetime.now(timezone.utc).date()
        live_bucket = (
            datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
            if date_to is not None and date_to >= today else None
        )
        return (app.state.local_snapshot_cache_mtime,date_from,date_to,canonical_strategy,live_bucket)

    def current_directory_cache(request_date: date):
        cache_path=Path(__file__).resolve().parents[1]/"runtime"/"directory_summary_cache.json"
        try:
            mtime=cache_path.stat().st_mtime_ns
            if app.state.directory_summary_cache["mtime"] != mtime:
                payload=json.loads(cache_path.read_text(encoding="utf-8"))
                if payload.get("date_from") != request_date.isoformat():
                    raise ValueError("current-day directory cache is stale")
                app.state.directory_summary_cache={"mtime":mtime,"payload":payload}
            return app.state.directory_summary_cache["payload"]
        except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError):
            raise HTTPException(503,"Current-day directory cache is warming; retry shortly")

    def points_from_snapshot(snapshot,strategy_id,start=None,end=None):
        if snapshot is None:return None
        points=[]
        for point in snapshot["curves"].get(strategy_id,[]):
            observed=datetime.fromisoformat(str(point["closed_at"]).replace("Z","+00:00"));observed=observed if observed.tzinfo else observed.replace(tzinfo=timezone.utc)
            if (start is None or observed>=start) and (end is None or observed<end):points.append(point)
        equity=peak=0.0;rebased=[]
        for index,point in enumerate(points,1):
            equity+=float(point["net_return"]);peak=max(peak,equity);rebased.append({**point,"trade_number":index,"equity":equity,"drawdown":equity-peak})
        return rebased

    def items(date_from: date | None = None, date_to: date | None = None, canonical_strategy: str | None = None, signal: str | None = None):
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "date_from must be on or before date_to")
        start = datetime.combine(date_from, time.min,timezone.utc) if date_from else None
        end = datetime.combine(date_to + timedelta(days=1), time.min,timezone.utc) if date_to else None
        if cfg.data_backend == "sqlserver":
            # Current-day list and detail summaries share the same atomic cache
            # as the ledger and curve. This check must precede the exact-ID
            # fallback or strategy pages still issue a slow raw-table query.
            if date_from == datetime.now(timezone.utc).date() and date_to == date_from:
                payload=current_directory_cache(date_from)
                rows=payload["datasets"][signal or "BOTH"]
                if canonical_strategy:
                    rows=[row for row in rows if row["strategy_id"] == canonical_strategy]
                return [Strategy.model_validate(row) for row in rows]
            # Historical detail periods retain the bounded SQL fallback until
            # historical cache partitions are published.
            if canonical_strategy and start is not None and end is not None:
                return [Strategy.model_validate(x) for x in local_strategies(
                    cfg,start.replace(tzinfo=None),end.replace(tzinfo=None),canonical_strategy,signal
                )]
            # The grant-free entry-date cohort query completes within the UI
            # latency target and must be authoritative. Returning it directly
            # prevents a completed current-day result from being replaced by a
            # stale snapshot/cache entry while trading continues.
            if start is not None and end is not None:
                return [Strategy.model_validate(x) for x in local_period_strategies(
                    cfg,start.replace(tzinfo=None),end.replace(tzinfo=None),canonical_strategy,signal
                )]
            if signal is not None:
                return [Strategy.model_validate(x) for x in local_strategies(
                    cfg,canonical_strategy=canonical_strategy,signal=signal
                )]
            cached=local_snapshot()
            if cached is not None:
                profiles=cached["profiles"]
                if canonical_strategy:profiles=[profile for profile in profiles if profile["identity"]["strategy_id"]==canonical_strategy]
                if start is None and end is None:return [cached_summary(profile) for profile in profiles]
                cache_key=period_cache_key(date_from,date_to,canonical_strategy)
                period_cached=app.state.period_strategy_cache.get(cache_key)
                if period_cached is not None:return period_cached
                with app.state.period_strategy_cache_lock:
                    period_cached=app.state.period_strategy_cache.get(cache_key)
                    if period_cached is not None:return period_cached
                    output=[]
                    for profile in profiles:
                        strategy_id=profile["identity"]["strategy_id"];points=points_from_snapshot(cached,strategy_id,start,end)
                        if points:output.append(cached_summary(profile,points))
                    if not output and start is not None and end is not None:
                        # Display the complete strategy population immediately;
                        # live period evidence is refreshed outside the request.
                        output=[cached_summary(profile,[]) for profile in profiles]
                    if start is not None and end is not None:
                        # Snapshot evidence may contain only a partial current period.
                        # Always reconcile a requested period with the live source once,
                        # then atomically replace the provisional cached result.
                        app.state.period_refreshing.add(cache_key)
                        Thread(target=refresh_period_in_background,args=(cache_key,start,end,canonical_strategy),daemon=True).start()
                    app.state.period_strategy_cache[cache_key]=output
                    return output
            if not cfg.allow_synchronous_local_fallback:raise HTTPException(503,"Local intelligence snapshot is missing or stale; run the operator warm-up")
            if start is None and end is None:
                if app.state.strategy_cache is None:
                    with app.state.strategy_cache_lock:
                        if app.state.strategy_cache is None:
                            candidates=[Strategy.model_validate(x) for x in local_strategies(cfg)];candidates.sort(key=lambda item:(-item.total_trades,item.strategy_id));app.state.strategy_cache=candidates
                return [item for item in app.state.strategy_cache if canonical_strategy is None or item.strategy_id==canonical_strategy]
            return [Strategy.model_validate(x) for x in local_strategies(cfg,start.replace(tzinfo=None) if start else None,end.replace(tzinfo=None) if end else None,canonical_strategy)]
        if app.state.repository is None: raise HTTPException(503, "Directory repository is not configured")
        if date_from or date_to:
            # Published trade-level return_series carries no per-trade BUY/SELL
            # signal, unlike the local SQL Server source - a signal-filtered
            # period query cannot be answered hosted yet.
            if signal is not None: raise HTTPException(501, "Signal-filtered period evidence has not been published yet")
            rows=app.state.repository.period_items(start,end,canonical_strategy)
            return [Strategy.model_validate(x) for x in rows]
        snap=hosted_snapshot();return [] if snap is None else snap.items

    def trusted_publisher(authorization:str|None=Header(None)):
        expected=cfg.sync_token or "";supplied=(authorization or "").removeprefix("Bearer ")
        if not expected or not hmac.compare_digest(supplied,expected):raise HTTPException(401,"Unauthorized")

    @app.get("/healthz")
    def health(): return {"status":"ok","build_sha":BUILD_SHA[:12] if BUILD_SHA else None}

    @app.get("/favicon.ico",include_in_schema=False)
    def favicon():return Response(status_code=204)

    @app.get("/readyz")
    def ready():
        try: items()
        except Exception: raise HTTPException(503,"Directory data is unavailable")
        return {"status":"ready"}

    @app.get("/api/dna/strategies")
    def strategies(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100),search:str|None=Query(None,max_length=32,pattern=r"^[A-Za-z0-9_]*$"),
                   product:str|None=Query(None,max_length=32,pattern=r"^[A-Za-z0-9_]*$"),
                   evidence_min_trades:int=Query(5,ge=1,le=1000000),
                   minimum_trades:int=Query(0,ge=0),sort:str=Query("strategy_id",pattern=r"^(strategy_id|total_trades|total_net_return|win_rate|profit_factor|max_drawdown_money)$"),
                   direction:str=Query("asc",pattern=r"^(asc|desc)$"),
                   signal:str|None=Query(None,pattern=r"^(BUY|SELL)$"),
                   date_from:date|None=Query(None),date_to:date|None=Query(None)):
        exact_strategy = search.upper() if search and search.upper().startswith("DNA_") else None
        requested_product=product.upper() if product else None
        rows=[x for x in items(date_from,date_to,exact_strategy,signal)
              if x.total_trades>=minimum_trades
              and (not search or search.upper() in x.strategy_id.upper() or search.upper() in (x.descriptive_name or "").upper())
              and (not requested_product or requested_product in {part.strip().upper() for part in (x.product_name or "").split(",")})]
        rows.sort(key=lambda x:(getattr(x,sort) is None,getattr(x,sort)),reverse=direction=="desc")
        total=len(rows)
        # These headline values describe the exact evidence rows already loaded
        # for this request. Deriving them here keeps the public list independent
        # of SQL Server latency and guarantees a cache-only display path.
        headline_total=sum(row.total_trades>0 for row in rows)
        profitable_strategies=sum(
            row.total_trades>0 and float(row.total_net_return or 0)>0
            for row in rows
        )
        summary={
            "strategies":headline_total,
            "closed_trades":sum(row.total_trades for row in rows),
            "total_net_return":sum(float(row.total_net_return or 0) for row in rows),
            "profitable_strategies":profitable_strategies,
            "profitable_percentage":round(profitable_strategies/headline_total*100,2) if headline_total else 0.0,
            "evidence_ready":sum(row.total_trades>=evidence_min_trades for row in rows),
            "evidence_min_trades":evidence_min_trades,
            "collecting":sum(row.quality_state=="COLLECTING" for row in rows),
        }
        if cfg.data_backend=="sqlserver" and not search and minimum_trades==0:
            summary.update(executed_trades=summary["closed_trades"],constructed_strategies=total)
        refresh_pending=False
        if cfg.data_backend=="sqlserver" and (date_from or date_to):
            refresh_key=period_cache_key(date_from,date_to,exact_strategy)
            with app.state.period_strategy_cache_lock:refresh_pending=refresh_key in app.state.period_refreshing
        rows=rows[(page-1)*page_size:page*page_size]
        snap=hosted_snapshot() if cfg.data_backend=="postgres" else None
        return {"data":{"items":[x.model_dump(mode="json") for x in rows],"page":page,"page_size":page_size,"total":total,"summary":summary,"refresh_pending":refresh_pending},
                "as_of":(snap.generated_at if snap else datetime.now(timezone.utc)).isoformat(),
                "basis":"net return; costs and commission already included","methodology_version":snap.methodology_version if snap else "1.0.0",
                "quality_state":"VALID","period":{"date_from":date_from.isoformat() if date_from else None,
                "date_to":date_to.isoformat() if date_to else None}}

    @app.get("/api/dna/products")
    def products():
        if cfg.data_backend == "sqlserver":
            values=local_products(cfg)
        else:
            snap=hosted_snapshot();values=sorted({part.strip().upper() for item in ([] if snap is None else snap.items)
                           for part in (item.product_name or "").split(",") if part.strip()})
        return {"items":values,"total":len(values)}

    @app.get("/api/dna/strategies/{strategy_id}/equity-curve")
    def equity_curve(strategy_id:str=ApiPath(pattern=r"^DNA_[A-Za-z0-9]+$"),
                     date_from:date|None=Query(None),date_to:date|None=Query(None)):
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "date_from must be on or before date_to")
        start = datetime.combine(date_from, time.min,timezone.utc) if date_from else None
        end = datetime.combine(date_to + timedelta(days=1), time.min,timezone.utc) if date_to else None
        if cfg.data_backend=="sqlserver" and date_from==datetime.now(timezone.utc).date() and date_to==date_from:
            trades=current_directory_cache(date_from).get("trades_by_strategy",{}).get(strategy_id,[])
            ordered=sorted(trades,key=lambda row:(row.get("exit_time") or "",row.get("entry_time") or "",row.get("guid") or ""))
            equity=peak=0.0;points=[]
            for number,row in enumerate(ordered,1):
                equity+=float(row["net_return"]);peak=max(peak,equity)
                points.append({"trade_number":number,"opened_at":row["entry_time"],"closed_at":row["exit_time"],
                               "net_return":row["net_return"],"signal":row.get("signal"),"equity":equity,"drawdown":equity-peak})
            return {"strategy_id":strategy_id,"points":points,"total_points":len(points),
                    "period":{"date_from":date_from.isoformat(),"date_to":date_to.isoformat()},
                    "basis":"cached cumulative net return; costs and commission already included"}
        # Individual SQL Server evidence must be internally consistent with the
        # live trade ledger. Snapshot curves can be non-empty but incomplete
        # when additional trades close, so never use them on this detail route.
        points = local_equity_curve(cfg,strategy_id,start,end) if cfg.data_backend=="sqlserver" else app.state.repository.current_equity_curve(strategy_id,start,end)
        if points is None:
            if not cfg.allow_synchronous_local_fallback:raise HTTPException(503,"Local intelligence snapshot is missing or stale; run the operator warm-up")
            points=local_equity_curve(cfg,strategy_id,start,end)
        return {"strategy_id":strategy_id,"points":points,"total_points":len(points),
                "period":{"date_from":date_from.isoformat() if date_from else None,
                          "date_to":date_to.isoformat() if date_to else None},
                "basis":"cumulative net return; costs and commission already included"}

    @app.get("/api/dna/strategies/{strategy_id}/trades")
    def closed_trades(strategy_id:str=ApiPath(pattern=r"^DNA_[A-Za-z0-9]+$"),
                      date_from:date|None=Query(None),date_to:date|None=Query(None),
                      limit:int=Query(1000,ge=1,le=5000)):
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "date_from must be on or before date_to")
        start = datetime.combine(date_from, time.min,timezone.utc) if date_from else None
        end = datetime.combine(date_to + timedelta(days=1), time.min,timezone.utc) if date_to else None
        if cfg.data_backend == "sqlserver":
            if date_from==datetime.now(timezone.utc).date() and date_to==date_from:
                trades=current_directory_cache(date_from).get("trades_by_strategy",{}).get(strategy_id,[])[:limit]
            else:
                trades=local_closed_trades(cfg,strategy_id,start,end,limit)
        else:
            if app.state.repository is None: raise HTTPException(503,"Directory repository is not configured")
            trades=app.state.repository.current_closed_trades(strategy_id,start,end,limit)
        return {"strategy_id":strategy_id,"items":trades,"total":len(trades),"limit":limit,
                "period":{"date_from":date_from.isoformat() if date_from else None,
                          "date_to":date_to.isoformat() if date_to else None},
                "basis":"closed trades; net return includes costs and commission"}

    @app.get("/api/dna/strategies/{strategy_id}/rank-journey")
    def rank_journey(strategy_id:str=ApiPath(pattern=r"^DNA_[A-Za-z0-9]+$"),
                     date_from:date|None=Query(None),date_to:date|None=Query(None)):
        """This strategy's rank among every strategy active in the window,
        at the instant right after each of its own trades closed.

        Local (SQL Server): computed live from a single plain scan of the
        day's closed trades (see local_rank_journey()'s docstring for why
        a snapshot-table read and several SQL-side rewrites were tried and
        dropped in favor of this) - current-day-scoped by the date_from/
        date_to window, exact.

        Hosted: read from rank_position/total_strategies stamped on each
        return-series point at export time (sync/export_snapshot.py,
        current_rank_journey()) - hosted has no SQL Server connection to
        compute this per-request. Necessarily an all-time ranking over
        whatever population the last export selected, not scoped to
        date_from/date_to the way local's is - those params still filter
        which of the target's OWN trades are returned, just not the
        ranking population itself."""
        if date_from and date_to and date_from > date_to:
            raise HTTPException(422, "date_from must be on or before date_to")
        today=datetime.now(timezone.utc).date()
        start=datetime.combine(date_from or today, time.min,timezone.utc)
        end=datetime.combine((date_to or today) + timedelta(days=1), time.min,timezone.utc)
        if cfg.data_backend=="sqlserver":
            journey=local_rank_journey(cfg,strategy_id,start,end)
            basis="rank among strategies active in the selected period, by cumulative net return at each close"
        else:
            if app.state.repository is None: raise HTTPException(503,"Directory repository is not configured")
            journey=app.state.repository.current_rank_journey(strategy_id,start,end)
            basis="rank among strategies in the last published snapshot, by all-time cumulative net return at each close - not scoped to the selected period"
        return {"strategy_id":strategy_id,"items":journey,"total":len(journey),
                "period":{"date_from":(date_from or today).isoformat(),"date_to":(date_to or today).isoformat()},
                "basis":basis}

    @app.post("/internal/snapshots",status_code=202)
    async def ingest(snapshot:Snapshot, _:None=Depends(trusted_publisher), idempotency_key:str|None=Header(None)):
        if idempotency_key != snapshot.snapshot_id: raise HTTPException(400,"Idempotency key mismatch")
        if snapshot.item_count > cfg.max_snapshot_items: raise HTTPException(413,"Snapshot item limit exceeded")
        now=datetime.now(timezone.utc)
        if snapshot.generated_at>now+timedelta(minutes=5) or snapshot.source_watermark>now+timedelta(minutes=5):raise HTTPException(422,"Snapshot timestamp is in the future")
        if now-snapshot.source_watermark>timedelta(hours=cfg.snapshot_max_age_hours):raise HTTPException(422,"Snapshot source watermark is stale")
        try: snapshot.verified(); app.state.repository.promote(snapshot);invalidate_snapshot_cache()
        except ValueError as exc: raise HTTPException(422,str(exc))
        return {"accepted":True,"snapshot_id":snapshot.snapshot_id,"items":snapshot.item_count}

    # Staged, batched ingestion (PUB-04) - builds one snapshot across several
    # small requests instead of one large POST /internal/snapshots body.
    # begin declares the envelope; batch inserts a chunk of rows (repeatable,
    # idempotent per batch_index); finalize reassembles the full snapshot from
    # staged rows, runs the same verified() reconciliation, and does the same
    # staged->current/retained flip promote() always did.
    @app.post("/internal/snapshots/{snapshot_id}/begin",status_code=202)
    def begin_snapshot(envelope:SnapshotEnvelope, snapshot_id:str=ApiPath(pattern=r"^[A-Za-z0-9._:-]+$"), _:None=Depends(trusted_publisher)):
        if envelope.snapshot_id != snapshot_id: raise HTTPException(400,"snapshot_id path/body mismatch")
        if envelope.item_count > cfg.max_snapshot_items: raise HTTPException(413,"Snapshot item limit exceeded")
        now=datetime.now(timezone.utc)
        if envelope.generated_at>now+timedelta(minutes=5) or envelope.source_watermark>now+timedelta(minutes=5):raise HTTPException(422,"Snapshot timestamp is in the future")
        if now-envelope.source_watermark>timedelta(hours=cfg.snapshot_max_age_hours):raise HTTPException(422,"Snapshot source watermark is stale")
        try: app.state.repository.begin_snapshot(envelope)
        except ValueError as exc: raise HTTPException(422,str(exc))
        return {"accepted":True,"snapshot_id":snapshot_id,"status":"staged"}

    @app.post("/internal/snapshots/{snapshot_id}/batch",status_code=202)
    def add_snapshot_batch(batch:SnapshotBatch, snapshot_id:str=ApiPath(pattern=r"^[A-Za-z0-9._:-]+$"), _:None=Depends(trusted_publisher), idempotency_key:str|None=Header(None)):
        if idempotency_key != f"{snapshot_id}:{batch.batch_index}": raise HTTPException(400,"Idempotency key mismatch")
        try: app.state.repository.add_snapshot_batch(snapshot_id,batch.items,batch.intelligence_profiles,batch.return_series)
        except KeyError: raise HTTPException(404,"Snapshot has not been started - call begin first")
        except ValueError as exc: raise HTTPException(422,str(exc))
        return {"accepted":True,"snapshot_id":snapshot_id,"batch_index":batch.batch_index}

    @app.post("/internal/snapshots/{snapshot_id}/finalize",status_code=202)
    def finalize_snapshot(snapshot_id:str=ApiPath(pattern=r"^[A-Za-z0-9._:-]+$"), _:None=Depends(trusted_publisher), idempotency_key:str|None=Header(None)):
        if idempotency_key != snapshot_id: raise HTTPException(400,"Idempotency key mismatch")
        try: app.state.repository.finalize_snapshot(snapshot_id)
        except KeyError: raise HTTPException(404,"Snapshot has not been started - call begin first")
        except ValueError as exc: raise HTTPException(422,str(exc))
        invalidate_snapshot_cache()
        return {"accepted":True,"snapshot_id":snapshot_id,"status":"current"}

    no_store={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0"}

    @app.get("/")
    def directory(): return FileResponse(WEB/"index.html",headers=no_store)
    @app.get("/{screen}.html")
    def screen(screen:str):
        if screen not in {"strategy","compare","builder","intelligence","account","regimes","search"}: raise HTTPException(404)
        return FileResponse(WEB/f"{screen}.html",headers=no_store)
    @app.get("/assets/{name}")
    def asset(name:str):
        if name not in {"styles.css","tech-principle-theme.css","thetechprinciple-icon-180.png","api-client.js","period-filter.js","equity-chart.js","button-feedback.js","theme-toggle.js"}: raise HTTPException(404)
        return FileResponse(WEB/name,headers=no_store)

    return app
