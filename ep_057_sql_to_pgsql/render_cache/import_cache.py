# epics/ep_057_sql_to_pgsql/render_cache/import_cache.py — Render cron: import new cache batches into Render Postgres.
#
# VERSION HISTORY
# v1.0.0 · 2026-09-23 · Initial version: ledgered idempotent import, latest-file full replace, retention prune.
"""Render cron entry point (every 5 minutes).

Reads manifest.json + batch files from CACHE_SOURCE (default: raw.githubusercontent.com data branch of edebell67/epics,
or a local directory for testing), imports anything not already in cache_import_ledger, then prunes rows outside the
manifest's retention window. Re-running is always safe: snapshots are ON CONFLICT DO NOTHING, closed trades upsert by
guid, open/product_forex files are full-replace transactions keyed on their sha256.

    python import_cache.py [--source URL_OR_DIR]     (target DB: DATABASE_URL, or PGHOST/PGPORT/...)
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from psycopg2.extras import execute_values

from cache_common import KINDS, RAW_BASE, connect, sha256_bytes

HERE = Path(__file__).resolve().parent
PAGE_ROWS = 20_000


def fetch(source: str, name: str) -> bytes:
    if not source.startswith("http"):
        return (Path(source) / name).read_bytes()
    url = f"{source.rstrip('/')}/{name}?t={int(time.time())}"  # cache-buster: raw.githubusercontent caches ~5 min
    req = urllib.request.Request(url, headers={"User-Agent": "top10-cache-importer", "Cache-Control": "no-cache"})
    last: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - retry any transport error
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"could not fetch {name}: {last}")


def parse(data: bytes) -> tuple[list[str], list[list]]:
    lines = gzip.decompress(data).decode().split("\n")
    cols = json.loads(lines[0])
    return cols, [json.loads(line) for line in lines[1:] if line]


def load_rows(cur, kind: str, cols: list[str], rows: list[list]) -> None:
    table, expected = KINDS[kind]
    if cols != expected:
        raise ValueError(f"{kind}: unexpected columns {cols}")
    col_sql = ", ".join(cols)
    if kind == "snap":
        tail = "ON CONFLICT (snapshot_id) DO NOTHING"
    elif kind in ("closed", "open"):
        updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != "guid")
        tail = f"ON CONFLICT (guid) DO UPDATE SET {updates}"
    else:
        tail = ""
    for i in range(0, len(rows), PAGE_ROWS):
        execute_values(cur, f"INSERT INTO {table} ({col_sql}) VALUES %s {tail}", rows[i:i + PAGE_ROWS])


def run(source: str) -> dict:
    manifest = json.loads(fetch(source, "manifest.json"))
    stats = {"imported": 0, "skipped": 0, "rows": 0, "pruned": 0}
    conn = connect("PG")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, sha256 FROM cache_import_ledger")
            ledger = dict(cur.fetchall())
        conn.commit()
        # Full-replace files (open, product_forex) first only when changed; delta batches in manifest order.
        work = [(b, False) for b in manifest["batches"]] + [(b, True) for b in manifest["latest"]]
        for item, replace in work:
            if ledger.get(item["name"]) == item["sha256"]:
                stats["skipped"] += 1
                continue
            data = fetch(source, item["name"])
            if sha256_bytes(data) != item["sha256"]:
                raise ValueError(f"{item['name']}: sha256 mismatch (partial push?) - will retry next run")
            cols, rows = parse(data)
            with conn.cursor() as cur:
                if replace:
                    cur.execute(f"DELETE FROM {KINDS[item['kind']][0]}")
                load_rows(cur, item["kind"], cols, rows)
                cur.execute("INSERT INTO cache_import_ledger (name, sha256, rows) VALUES (%s, %s, %s) "
                            "ON CONFLICT (name) DO UPDATE SET sha256=EXCLUDED.sha256, rows=EXCLUDED.rows, imported_at=now()",
                            (item["name"], item["sha256"], len(rows)))
            conn.commit()
            stats["imported"] += 1
            stats["rows"] += len(rows)
        # Retention: everything before the exporter's window_start goes, plus ledger rows for pruned batches.
        with conn.cursor() as cur:
            ws = manifest["window_start"]
            cur.execute("DELETE FROM tbl_dna_model_summary_snapshots_5min WHERE snapshot_timestamp < %s", (ws,))
            stats["pruned"] += cur.rowcount
            cur.execute("DELETE FROM combined_trades_closed WHERE created < %s", (ws,))
            stats["pruned"] += cur.rowcount
            keep = [b["name"] for b in manifest["batches"] + manifest["latest"]]
            cur.execute("DELETE FROM cache_import_ledger WHERE NOT (name = ANY(%s))", (keep,))
        conn.commit()
    finally:
        conn.close()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.environ.get("CACHE_SOURCE", RAW_BASE))
    ap.add_argument("--init-schema", action="store_true", help="apply schema_render.sql first (idempotent)")
    args = ap.parse_args()
    if args.init_schema or os.environ.get("CACHE_INIT_SCHEMA") == "1":
        conn = connect("PG")
        with conn, conn.cursor() as cur:
            cur.execute((HERE / "schema_render.sql").read_text())
        conn.close()
    stats = run(args.source)
    print(f"import ok: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
