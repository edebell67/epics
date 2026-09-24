# epics/ep_057_sql_to_pgsql/dashboards_and_uis/top10_live_app.py — ASGI entry point for the live equity-curves dashboard.
#
# VERSION HISTORY
# v1.5.0 · 2026-09-22 · Uses orjson plus gzip for substantially faster large live-day responses.
# v1.4.0 · 2026-09-22 · Adds 10/20/30 scenario limits and the named-portfolio data endpoint.
# v1.3.0 · 2026-09-22 · Exposes canonical strategy_family filtering on the live-day endpoint.
# v1.2.0 · 2026-09-22 · Adds the dependent product parameter to live-day and model-trades endpoints.
# v1.1.0 · 2026-09-21 · Adds validated product_type parameters to live-day and model-trades endpoints.
# v1.0.0 · 2026-09-21 · Version history added; file predates this convention.
"""
EP057 Top10 5min Equity Curves - ASGI app for uvicorn (port 8765).

Same endpoints as top10_live_server.py, reusing its query builders:
    GET /api/live_day?date=YYYY-MM-DD
    GET /api/model_trades?model=...&from=YYYY-MM-DD[&to=YYYY-MM-DD]
and serves this folder statically (top10_5min_equity_curves.html etc.).

Run:  uvicorn top10_live_app:app --host 127.0.0.1 --port 8765
"""
from __future__ import annotations

import datetime as dt

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles

from top10_live_server import DATE_RE, HERE, build_live_day, build_model_trades, build_portfolio_day, normalize_model_limit, normalize_product, normalize_product_type, normalize_strategy_family

app = FastAPI(title="EP057 Top10 Live", docs_url=None, redoc_url=None, default_response_class=ORJSONResponse)
app.add_middleware(GZipMiddleware, minimum_size=1_000, compresslevel=5)

NO_STORE = {"Cache-Control": "no-store"}


def _check_date(value: str) -> str:
    if not DATE_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    return value


@app.get("/api/live_day")
async def live_day(date: str | None = None, product_type: str = "all", product: str = "all", strategy_family: str = "all", limit: int = 10) -> JSONResponse:
    date_str = _check_date(date or dt.date.today().isoformat())
    try:
        product_type = normalize_product_type(product_type)
        product = normalize_product(product)
        strategy_family = normalize_strategy_family(strategy_family)
        limit = normalize_model_limit(limit)
        payload = await run_in_threadpool(build_live_day, date_str, product_type, product, strategy_family, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # surfaced on the page's live badge
        return JSONResponse({"error": str(exc)}, status_code=500, headers=NO_STORE)
    return ORJSONResponse(payload, headers=NO_STORE)


@app.get("/api/portfolio_day")
async def portfolio_day(models: str = Query(..., min_length=1), date: str | None = None) -> JSONResponse:
    date_str = _check_date(date or dt.date.today().isoformat())
    try:
        payload = await run_in_threadpool(build_portfolio_day, date_str, models.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500, headers=NO_STORE)
    return ORJSONResponse(payload, headers=NO_STORE)


@app.get("/api/model_trades")
async def model_trades(
    model: str = Query(..., min_length=1),
    date_from: str = Query(..., alias="from"),
    date_to: str | None = Query(None, alias="to"),
    product_type: str = "all",
    product: str = "all",
) -> JSONResponse:
    d_from = _check_date(date_from)
    d_to = _check_date(date_to or date_from)
    try:
        product_type = normalize_product_type(product_type)
        product = normalize_product(product)
        payload = await run_in_threadpool(build_model_trades, model, d_from, d_to, product_type, product)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500, headers=NO_STORE)
    return ORJSONResponse(payload, headers=NO_STORE)


# Static last so the /api routes take precedence
app.mount("/", StaticFiles(directory=str(HERE), html=True), name="static")
