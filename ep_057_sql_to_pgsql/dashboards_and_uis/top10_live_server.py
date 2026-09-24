# epics/ep_057_sql_to_pgsql/dashboards_and_uis/top10_live_server.py — Live equity-curve API and static dashboard server.
#
# VERSION HISTORY
# v1.5.0 · 2026-09-23 · _connect() honours DATABASE_URL (Render); PG* variables remain the local default.
# v1.4.0 · 2026-09-22 · Adds configurable 10/20/30 scenario limits and explicit portfolio model snapshots (maximum ten models).
# v1.3.0 · 2026-09-22 · Adds canonical breakout strategy-family filtering before scenario ranking.
# v1.2.0 · 2026-09-22 · Adds validated dependent product filtering and product metadata so every dashboard result can share the selected type/product scope.
# v1.1.0 · 2026-09-21 · Adds validated product-type filtering so callers can isolate forex or crypto models without changing the default all-products view.
# v1.0.0 · 2026-09-21 · Version history added; file predates this convention.
"""
EP057 Top10 5min Equity Curves - static + live data server (port 8765).

Serves this folder (so top10_5min_equity_curves.html loads as before) and adds:
    GET /api/live_day?date=YYYY-MM-DD
returning {"date", "generated_at", "top_net": [...], "top_alt_net": [...]}
in the same model-list shape as ALL_CRITERIA_DATA[scenario][date], built
with the same queries as scratch_and_tools/append_today_data_to_html.py.

DB settings come from PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD (repo .env
is loaded if present), defaulting to the local tradedb used by the ep057 scripts.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import psycopg2

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("EP057_LIVE_PORT", "8765"))

try:
    from dotenv import load_dotenv

    load_dotenv(HERE.parents[2] / ".env")
except ImportError:
    pass

COLORS = [
    "#38bdf8", "#34d399", "#f472b6", "#fbbf24", "#a78bfa",
    "#fb923c", "#2dd4bf", "#4ade80", "#e879f9", "#f87171",
]

# Per-model stats for one trading date; strategy/tp from the canonical model definition
STATS_SQL = """
    WITH bounds AS (SELECT %s::date AS day)
    SELECT c.model,
           ROUND(SUM(c.net_return)::numeric, 2) AS total_net,
           ROUND(SUM(c.alt_net_return)::numeric, 2) AS total_alt_net,
           COUNT(*) AS total_trades,
           COUNT(*) FILTER (WHERE c.net_return > 0) AS wins,
           COUNT(*) FILTER (WHERE c.net_return <= 0) AS losses,
           ROUND((COUNT(*) FILTER (WHERE c.net_return > 0)::numeric / COUNT(*)::numeric * 100), 1) AS win_rate,
           COUNT(*) FILTER (WHERE c.alt_net_return > 0) AS alt_wins,
           ROUND((COUNT(*) FILTER (WHERE c.alt_net_return > 0)::numeric / COUNT(*)::numeric * 100), 1) AS alt_win_rate,
           MAX(TRIM(c.product)) AS product,
           COALESCE(MAX(TRIM(pf.strategy_name)), MAX(TRIM(c.strategy_name))) AS strategy,
           MAX(pf.target_profit) AS target_profit,
           MAX(LOWER(TRIM(c.product_type))) AS product_type
    FROM combined_trades_closed c
    CROSS JOIN bounds b
    LEFT JOIN product_forex pf ON TRIM(pf.model) = c.model
    WHERE c.created >= b.day
      AND c.created < b.day + INTERVAL '1 day'
      AND (%s = 'all' OR LOWER(TRIM(c.product_type)) = %s)
      AND (%s = 'all' OR LOWER(TRIM(c.product)) = %s)
    GROUP BY c.model;
"""

PRODUCTS_SQL = """
    SELECT DISTINCT LOWER(TRIM(product)) AS product
    FROM product_forex
    WHERE product IS NOT NULL
      AND (%s = 'all' OR LOWER(TRIM(product_type)) = %s)
    ORDER BY product;
"""

SNAP_SQL = """
    WITH bounds AS (SELECT %s::date AS day)
    SELECT model,
           to_char(snapshot_timestamp, 'HH24:MI') AS time_str,
           ROUND(cum_net::numeric, 1), ROUND(cum_buy_net::numeric, 1), ROUND(cum_sell_net::numeric, 1),
           ROUND(cum_alt_net::numeric, 1), ROUND(cum_buy_alt_net::numeric, 1), ROUND(cum_sell_alt_net::numeric, 1),
           open_trade_count, closed_trade_count
    FROM tbl_dna_model_summary_snapshots_5min s
    CROSS JOIN bounds b
    WHERE snapshot_timestamp >= b.day
      AND snapshot_timestamp < b.day + INTERVAL '1 day'
      AND model = ANY(%s)
    ORDER BY snapshot_timestamp;
"""

TOUCHED_RANK_ONE_SQL = """
    WITH bounds AS (SELECT %s::date AS day), ranked AS (
        SELECT model, snapshot_timestamp,
               DENSE_RANK() OVER (
                   PARTITION BY snapshot_timestamp
                   ORDER BY cum_net DESC
               ) AS position
        FROM tbl_dna_model_summary_snapshots_5min s
        CROSS JOIN bounds b
        WHERE snapshot_timestamp >= b.day
          AND snapshot_timestamp < b.day + INTERVAL '1 day'
          AND model = ANY(%s)
    )
    SELECT DISTINCT model
    FROM ranked
    WHERE position = 1;
"""


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def _connect():
    if os.environ.get("DATABASE_URL"):
        return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "tradedb"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD"),
        connect_timeout=5,
    )


STAT_COLS = ["model", "net", "alt", "trades", "wins", "losses", "win_rate",
             "alt_wins", "alt_win_rate", "product", "strategy", "target_profit", "product_type"]
MIN_SCENARIO_MODELS = 2  # fewer qualifying models -> scenario falls back to top_net


def _family_leaders(stats: list[dict], metric: str) -> list[dict]:
    """Return the best strategy in each canonical family for the chosen metric."""
    win_metric = "alt_win_rate" if metric == "alt" else "win_rate"
    winners: dict[str, dict] = {}
    for stat in stats:
        family = strategy_family(stat.get("strategy"))
        if family == "unknown":
            continue
        incumbent = winners.get(family)
        rank_key = (-stat[metric], -stat[win_metric], stat["model"])
        if incumbent is None or rank_key < (-incumbent[metric], -incumbent[win_metric], incumbent["model"]):
            winners[family] = stat
    family_order = ("breakout", "breakout_r", "breakout_rev", "breakout_r_rev")
    return [winners[family] for family in family_order if family in winners]


def _top_family(stats: list[dict], family: str, metric: str, limit: int = 5) -> list[dict]:
    """Return the strongest models in one family for the selected return metric."""
    win_metric = "alt_win_rate" if metric == "alt" else "win_rate"
    return sorted(
        (stat for stat in stats if strategy_family(stat.get("strategy")) == family),
        key=lambda stat: (-stat[metric], -stat[win_metric], stat["model"]),
    )[:limit]


def _scenario_ids(stats: list[dict], snaps: dict[str, list[dict]], limit: int = 10,
                  touched_rank_one_ids: set[str] | None = None,
                  family_stats: list[dict] | None = None) -> dict[str, list[str]]:
    """Scenario model lists for one trading date.

    Rules reproduce the stored 14-18 Sep lists: each scenario filters the day's pool
    (Top 10 Net Return + Top 10 Win Rate) and falls back to Top 10 Net Return when fewer
    than MIN_SCENARIO_MODELS qualify. weakening_selection follows its catalogue text
    (high-volume pool models below their intraday peak) - the original rule is unknown.
    """
    by_net = sorted(stats, key=lambda s: (-s["net"], -s["win_rate"], s["model"]))
    top_net = by_net[:limit]
    top_alt = sorted(stats, key=lambda s: (-s["alt"], s["model"]))[:limit]
    top_win = sorted((s for s in stats if s["win_rate"] >= 50),
                     key=lambda s: (-s["win_rate"], -s["net"], s["model"]))[:limit]
    pool, seen = [], set()
    for s in top_net + top_win:
        if s["model"] not in seen:
            seen.add(s["model"])
            pool.append(s)

    def tp_pips(s):
        return (s["target_profit"] or 0) / 10

    def drawdown(s):
        series = snaps.get(s["model"]) or []
        return (max(p["net"] for p in series) - series[-1]["net"]) if series else 0.0

    def pick(models, pick_limit=None):
        models = list(models)[:pick_limit or limit]
        return models if len(models) >= MIN_SCENARIO_MODELS else top_net

    family_stats = family_stats if family_stats is not None else stats
    lists = {
        "top_net": top_net,
        "top_alt_net": top_alt,
        "family_leaders_net": _family_leaders(stats, "net"),
        "family_leaders_alt": _family_leaders(stats, "alt"),
        "top_win": top_win or top_net,
        "strongest_three": sorted(pool, key=lambda s: -s["net"])[:3],
        "strengthening_cluster": pick(s for s in pool if (s["strategy"] or "").startswith("breakout_R_")),
        "relative_value": pick(sorted((s for s in pool if s["win_rate"] >= 85), key=lambda s: -s["win_rate"])),
        "market_move": pick(s for s in pool if tp_pips(s) >= 10),
        "opposite_cluster": pick(s for s in pool if 3 <= tp_pips(s) <= 5),
        "weakening_selection": pick(sorted((s for s in pool if drawdown(s) > 0),
                                           key=lambda s: (-s["trades"], -drawdown(s)))),
        "repair_negative": pick(s for s in pool if s["win_rate"] == 100 and s["net"] > 0),
        # Every strategy that held the highest cumulative net at one or more
        # five-minute snapshots. Ties at #1 are deliberately included.
        "touched_rank_one": sorted(
            (s for s in stats if s["model"] in (touched_rank_one_ids or set())),
            key=lambda s: (-s["net"], -s["win_rate"], s["model"]),
        )[:limit],
    }
    for family in ("breakout", "breakout_r", "breakout_rev", "breakout_r_rev"):
        lists[f"top5_{family}_net"] = _top_family(family_stats, family, "net")
        lists[f"top5_{family}_alt"] = _top_family(family_stats, family, "alt")
    lists["NET_RETURN"] = lists["top_net"]
    lists["WIN_RATE"] = lists["top_win"]
    return {k: [s["model"] for s in v] for k, v in lists.items()}


PRODUCT_TYPES = {"all", "forex", "crypto"}
STRATEGY_FAMILIES = {"all", "breakout", "breakout_r", "breakout_rev", "breakout_r_rev"}


def normalize_product_type(value: str | None) -> str:
    product_type = (value or "all").strip().lower()
    if product_type not in PRODUCT_TYPES:
        raise ValueError("product_type must be all, forex, or crypto")
    return product_type


def normalize_product(value: str | None) -> str:
    product = (value or "all").strip().lower()
    if product != "all" and not re.fullmatch(r"[a-z0-9._-]+", product):
        raise ValueError("product contains unsupported characters")
    return product


def strategy_family(value: str | None) -> str:
    name = (value or "").strip().lower()
    for family in ("breakout_r_rev", "breakout_rev", "breakout_r", "breakout"):
        if name == family or name.startswith(f"{family}_"):
            return family
    return "unknown"


def normalize_strategy_family(value: str | None) -> str:
    family = (value or "all").strip().lower()
    if family not in STRATEGY_FAMILIES:
        raise ValueError("strategy_family must be all, breakout, breakout_r, breakout_rev, or breakout_r_rev")
    return family


def normalize_model_limit(value: int | str | None) -> int:
    limit = int(value or 10)
    if limit not in (10, 20, 30):
        raise ValueError("limit must be 10, 20, or 30")
    return limit


_LIVE_DAY_CACHE: dict[tuple, tuple[float, dict]] = {}
LIVE_DAY_CACHE_SECONDS = 30


def build_live_day(date_str: str, product_type: str = "all", product: str = "all", strategy_family_filter: str = "all", limit: int = 10) -> dict:
    product_type = normalize_product_type(product_type)
    product = normalize_product(product)
    strategy_family_filter = normalize_strategy_family(strategy_family_filter)
    limit = normalize_model_limit(limit)
    cache_key = (date_str, product_type, product, strategy_family_filter, limit)
    cached = _LIVE_DAY_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[0] < LIVE_DAY_CACHE_SECONDS:
        return cached[1]
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(PRODUCTS_SQL, (product_type, product_type))
        products = [r[0] for r in cur.fetchall()]
        if product != "all" and product not in products:
            raise ValueError(f"product {product!r} is not available for type {product_type!r}")
        cur.execute(STATS_SQL, (date_str, product_type, product_type, product, product))
        stats = [dict(zip(STAT_COLS, r)) for r in cur.fetchall()]
        for s in stats:
            for k in ("net", "alt", "win_rate", "alt_win_rate", "target_profit"):
                s[k] = _f(s[k])
        product_stats = list(stats)
        if strategy_family_filter != "all":
            stats = [s for s in stats if strategy_family(s["strategy"]) == strategy_family_filter]

        # Snapshots for every model that can appear in a scenario (top net / alt / win-rate pools)
        candidates = {s["model"] for s in sorted(stats, key=lambda s: -s["net"])[:limit]}
        candidates |= {s["model"] for s in sorted(stats, key=lambda s: -s["alt"])[:limit]}
        candidates |= {s["model"] for s in sorted((s for s in stats if s["win_rate"] >= 50),
                                                  key=lambda s: (-s["win_rate"], -s["net"], s["model"]))[:limit]}
        candidates |= {s["model"] for s in _family_leaders(stats, "net")}
        candidates |= {s["model"] for s in _family_leaders(stats, "alt")}
        for family in ("breakout", "breakout_r", "breakout_rev", "breakout_r_rev"):
            candidates |= {s["model"] for s in _top_family(product_stats, family, "net")}
            candidates |= {s["model"] for s in _top_family(product_stats, family, "alt")}
        touched_rank_one_ids: set[str] = set()
        all_model_ids = [s["model"] for s in stats]
        if all_model_ids:
            cur.execute(TOUCHED_RANK_ONE_SQL, (date_str, all_model_ids))
            touched_rank_one_ids = {row[0] for row in cur.fetchall()}
            candidates |= touched_rank_one_ids
        snaps: dict[str, list[dict]] = {}
        if candidates:
            cur.execute(SNAP_SQL, (date_str, sorted(candidates)))
            for m, tm, net, buy, sell, a_net, a_buy, a_sell, op, tr in cur.fetchall():
                snaps.setdefault(m, []).append({
                    "time": tm, "net": _f(net), "buy": _f(buy), "sell": _f(sell),
                    "alt_net": _f(a_net), "alt_buy": _f(a_buy), "alt_sell": _f(a_sell),
                    "open": int(op or 0), "trades": int(tr or 0),
                })

    by_model = {s["model"]: s for s in product_stats}

    def model_list(ids: list[str]) -> list[dict]:
        out = []
        for rank, m in enumerate(ids, start=1):
            s = by_model[m]
            series = snaps.get(m) or [{
                "time": "02:00", "net": s["net"], "buy": 0.0, "sell": s["net"],
                "alt_net": s["alt"], "alt_buy": 0.0, "alt_sell": s["alt"],
                "open": 0, "trades": int(s["trades"]),
            }]
            last = series[-1]
            out.append({
                "rank": rank, "model": m, "product": s["product"] or "GBP",
                "product_type": s["product_type"] or "forex",
                "strategy": s["strategy"] or "breakout_strategy",
                "color": COLORS[(rank - 1) % len(COLORS)],
                "trades": int(s["trades"]), "wins": int(s["wins"]), "losses": int(s["losses"]),
                "win_rate": s["win_rate"], "alt_wins": int(s["alt_wins"]), "alt_win_rate": s["alt_win_rate"],
                "cum_net": last["net"], "buy_net": last["buy"], "sell_net": last["sell"],
                "cum_alt_net": last["alt_net"], "buy_alt_net": last["alt_buy"],
                "sell_alt_net": last["alt_sell"], "series": series,
            })
        return out

    payload = {"date": date_str, "product_type": product_type, "product": product,
               "strategy_family": strategy_family_filter, "limit": limit,
               "products": products,
               "generated_at": dt.datetime.now().isoformat(timespec="seconds")}
    for sc, ids in _scenario_ids(stats, snaps, limit, touched_rank_one_ids, product_stats).items():
        payload[sc] = model_list(ids)
    _LIVE_DAY_CACHE[cache_key] = (time.monotonic(), payload)
    if len(_LIVE_DAY_CACHE) > 64:
        cutoff = time.monotonic() - LIVE_DAY_CACHE_SECONDS
        for key, value in list(_LIVE_DAY_CACHE.items()):
            if value[0] < cutoff:
                _LIVE_DAY_CACHE.pop(key, None)
    return payload


def build_portfolio_day(date_str: str, model_ids: list[str]) -> dict:
    clean_ids = list(dict.fromkeys(str(m).strip() for m in model_ids if str(m).strip()))
    if not clean_ids or len(clean_ids) > 10:
        raise ValueError("portfolio requires between 1 and 10 unique models")
    if any(not re.fullmatch(r"[A-Za-z0-9._-]+", model) for model in clean_ids):
        raise ValueError("portfolio contains an invalid model id")

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(STATS_SQL, (date_str, "all", "all", "all", "all"))
        stats = [dict(zip(STAT_COLS, row)) for row in cur.fetchall()]
        stats = [s for s in stats if s["model"] in clean_ids]
        for stat in stats:
            for key in ("net", "alt", "win_rate", "alt_win_rate", "target_profit"):
                stat[key] = _f(stat[key])
        cur.execute(SNAP_SQL, (date_str, clean_ids))
        snaps: dict[str, list[dict]] = {}
        for model, tm, net, buy, sell, a_net, a_buy, a_sell, op, trades in cur.fetchall():
            snaps.setdefault(model, []).append({
                "time": tm, "net": _f(net), "buy": _f(buy), "sell": _f(sell),
                "alt_net": _f(a_net), "alt_buy": _f(a_buy), "alt_sell": _f(a_sell),
                "open": int(op or 0), "trades": int(trades or 0),
            })

    by_model = {s["model"]: s for s in stats}
    models = []
    for rank, model in enumerate(clean_ids, start=1):
        stat = by_model.get(model)
        if not stat:
            continue
        series = snaps.get(model) or [{
            "time": "02:00", "net": stat["net"], "buy": 0.0, "sell": stat["net"],
            "alt_net": stat["alt"], "alt_buy": 0.0, "alt_sell": stat["alt"],
            "open": 0, "trades": int(stat["trades"]),
        }]
        last = series[-1]
        models.append({
            "rank": rank, "model": model, "product": stat["product"] or "GBP",
            "product_type": stat["product_type"] or "forex",
            "strategy": stat["strategy"] or "breakout_strategy",
            "color": COLORS[(rank - 1) % len(COLORS)],
            "trades": int(stat["trades"]), "wins": int(stat["wins"]), "losses": int(stat["losses"]),
            "win_rate": stat["win_rate"], "alt_wins": int(stat["alt_wins"]), "alt_win_rate": stat["alt_win_rate"],
            "cum_net": last["net"], "buy_net": last["buy"], "sell_net": last["sell"],
            "cum_alt_net": last["alt_net"], "buy_alt_net": last["alt_buy"],
            "sell_alt_net": last["alt_sell"], "series": series,
        })
    return {"date": date_str, "requested_models": clean_ids, "models": models,
            "generated_at": dt.datetime.now().isoformat(timespec="seconds")}


TRADES_CLOSED_SQL = """
    SELECT 'closed', to_char(created, 'YYYY-MM-DD HH24:MI:SS'), to_char(last_update, 'YYYY-MM-DD HH24:MI:SS'),
           TRIM(signal), TRIM(product), entry_price, latest_price, trade_quantity,
           net_return, alt_net_return, min_net_return, max_net_return,
           TRIM(close_type), TRIM(trade_reason), TRIM(strategy_name), target_profit, target_loss
    FROM combined_trades_closed
    WHERE model = %s AND created::date BETWEEN %s AND %s
    ORDER BY created;
"""

TRADES_OPEN_SQL = """
    SELECT 'open', to_char(created, 'YYYY-MM-DD HH24:MI:SS'), to_char(last_update, 'YYYY-MM-DD HH24:MI:SS'),
           TRIM(signal), TRIM(product), entry_price, latest_price, trade_quantity,
           net_return, alt_net_return, min_net_return, max_net_return,
           NULL, TRIM(trade_reason), TRIM(strategy_name), target_profit, target_loss
    FROM combined_trades_open
    WHERE TRIM(model) = %s AND created::date BETWEEN %s AND %s
    ORDER BY created;
"""

TRADE_COLS = [
    "status", "opened", "last_update", "signal", "product", "entry_price", "latest_price",
    "quantity", "net_return", "alt_net_return", "min_net_return", "max_net_return",
    "close_type", "trade_reason", "strategy", "target_profit", "target_loss",
]


def build_model_trades(model: str, date_from: str, date_to: str, product_type: str = "all", product: str = "all") -> dict:
    product_type = normalize_product_type(product_type)
    product = normalize_product(product)
    with _connect() as conn, conn.cursor() as cur:
        rows = []
        for sql in (TRADES_OPEN_SQL, TRADES_CLOSED_SQL):
            cur.execute(sql.replace("ORDER BY created;", "AND (%s = 'all' OR LOWER(TRIM(product_type)) = %s) AND (%s = 'all' OR LOWER(TRIM(product)) = %s) ORDER BY created;"),
                        (model, date_from, date_to, product_type, product_type, product, product))
            rows += cur.fetchall()
        # Canonical model definition: {script}_{window}_tp{tp}_sl{sl} plus params, e.g. breakout_2_tp5_sl20
        cur.execute(
            "SELECT TRIM(strategy_name), TRIM(strategy_params) FROM product_forex WHERE TRIM(model) = %s AND (%s = 'all' OR LOWER(TRIM(product_type)) = %s) AND (%s = 'all' OR LOWER(TRIM(product)) = %s) LIMIT 1",
            (model, product_type, product_type, product, product),
        )
        pf = cur.fetchone() or (None, None)
    trades = []
    for r in rows:
        t = dict(zip(TRADE_COLS, r))
        for k in ("entry_price", "latest_price", "quantity", "net_return",
                  "alt_net_return", "min_net_return", "max_net_return",
                  "target_profit", "target_loss"):
            t[k] = float(t[k]) if t[k] is not None else None
        trades.append(t)
    return {
        "model": model, "from": date_from, "to": date_to, "product_type": product_type, "product": product,
        "strategy_name": pf[0], "strategy_params": pf[1], "trades": trades,
    }


DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/api/model_trades":
            q = parse_qs(url.query)
            model = q.get("model", [""])[0]
            d_from = q.get("from", [""])[0]
            d_to = q.get("to", [d_from])[0]
            product_type = q.get("product_type", ["all"])[0]
            product = q.get("product", ["all"])[0]
            if not model or not DATE_RE.fullmatch(d_from) or not DATE_RE.fullmatch(d_to):
                return self._json(400, {"error": "model, from=YYYY-MM-DD [, to=YYYY-MM-DD] required"})
            try:
                return self._json(200, build_model_trades(model, d_from, d_to, product_type, product))
            except Exception as exc:
                return self._json(500, {"error": str(exc)})
        if url.path != "/api/live_day":
            if url.path == "/api/portfolio_day":
                q = parse_qs(url.query)
                portfolio_date = q.get("date", [dt.date.today().isoformat()])[0]
                models = q.get("models", [""])[0].split(",")
                if not DATE_RE.fullmatch(portfolio_date):
                    return self._json(400, {"error": "date must be YYYY-MM-DD"})
                try:
                    return self._json(200, build_portfolio_day(portfolio_date, models))
                except Exception as exc:
                    return self._json(500, {"error": str(exc)})
            return super().do_GET()
        date_str = parse_qs(url.query).get("date", [dt.date.today().isoformat()])[0]
        product_type = parse_qs(url.query).get("product_type", ["all"])[0]
        product = parse_qs(url.query).get("product", ["all"])[0]
        strategy_family_filter = parse_qs(url.query).get("strategy_family", ["all"])[0]
        limit = parse_qs(url.query).get("limit", ["10"])[0]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            return self._json(400, {"error": "date must be YYYY-MM-DD"})
        try:
            self._json(200, build_live_day(date_str, product_type, product, strategy_family_filter, limit))
        except Exception as exc:  # surface DB errors to the page status badge
            self._json(500, {"error": str(exc)})

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(HERE)))
    print(f"EP057 top10 live server on http://localhost:{PORT}/top10_5min_equity_curves.html")
    server.serve_forever()
