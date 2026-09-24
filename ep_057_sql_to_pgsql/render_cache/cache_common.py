# epics/ep_057_sql_to_pgsql/render_cache/cache_common.py — Shared table/column definitions for the Top10 Render cache.
#
# VERSION HISTORY
# v1.0.1 · 2026-09-23 · Loads the repo .env when present (local exporter needs PGPASSWORD).
# v1.0.0 · 2026-09-23 · Initial version: trimmed same-name cache tables, batch file naming, sha256 helper.
"""Shared definitions for the local->Render Top10 cache pipeline.

The Render Postgres holds *trimmed copies* of four tables under the SAME names
as local tradedb, so top10_live_app.py runs on Render with only PG* env changes.
"""
from __future__ import annotations

import hashlib
import os
import psycopg2
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except ImportError:
    pass

RETENTION_DAYS = int(os.environ.get("CACHE_RETENTION_DAYS", "3"))
DATA_BRANCH = os.environ.get("CACHE_DATA_BRANCH", "top10-cache-data")
REPO_URL = os.environ.get("CACHE_REPO_URL", "https://github.com/edebell67/epics.git")
RAW_BASE = os.environ.get("CACHE_RAW_BASE", f"https://raw.githubusercontent.com/edebell67/epics/{DATA_BRANCH}")

SNAP_TABLE = "tbl_dna_model_summary_snapshots_5min"
SNAP_COLS = ["snapshot_id", "snapshot_timestamp", "model", "product", "strategy_name", "strategy_family",
             "cum_net", "cum_alt_net", "cum_buy_net", "cum_buy_alt_net", "cum_sell_net", "cum_sell_alt_net",
             "open_trade_count", "closed_trade_count", "buy_closed_count", "sell_closed_count"]

TRADE_COLS = ["guid", "model", "product", "product_type", "created", "last_update", "signal", "entry_price",
              "latest_price", "trade_quantity", "net_return", "alt_net_return", "min_net_return", "max_net_return",
              "close_type", "trade_reason", "strategy_name", "target_profit", "target_loss"]
CLOSED_TABLE = "combined_trades_closed"
OPEN_TABLE = "combined_trades_open"

PF_TABLE = "product_forex"
PF_COLS = ["model", "product", "product_type", "strategy_name", "strategy_params", "target_profit"]

# batch kind -> (table, columns, conflict handling)
KINDS = {
    "snap": (SNAP_TABLE, SNAP_COLS),
    "closed": (CLOSED_TABLE, TRADE_COLS),
    "open": (OPEN_TABLE, TRADE_COLS),
    "pf": (PF_TABLE, PF_COLS),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def connect(prefix: str = "PG"):
    """Connect using <prefix>HOST/PORT/DATABASE/USER/PASSWORD, or <prefix>_URL / DATABASE_URL if set."""
    url = os.environ.get(f"{prefix}_URL") or (os.environ.get("DATABASE_URL") if prefix == "PG" else None)
    if url:
        return psycopg2.connect(url, connect_timeout=10)
    return psycopg2.connect(
        host=os.environ.get(f"{prefix}HOST", "localhost"), port=int(os.environ.get(f"{prefix}PORT", "5432")),
        dbname=os.environ.get(f"{prefix}DATABASE", "tradedb"), user=os.environ.get(f"{prefix}USER", "postgres"),
        password=os.environ.get(f"{prefix}PASSWORD"), connect_timeout=10)
