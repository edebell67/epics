# epics/ep_057_sql_to_pgsql/render_cache/export_cache.py — Local Postgres -> JSONL.gz batches -> data branch of edebell67/epics.
#
# VERSION HISTORY
# v1.0.0 · 2026-09-23 · Initial version: append-only snapshot deltas, GUID-diff closed-trade deltas, full open/product_forex files, manifest, orphan force-push.
"""Run every 5 minutes (see run_export.ps1).

Each run writes only NEW rows since the last run into outbox/ as gzip JSON-lines batches, prunes batches outside the
retention window, rewrites manifest.json, and (unless --no-push) publishes outbox/ as a single orphan commit force-pushed
to the data branch. Master is never touched, and the branch never accumulates history.

    python export_cache.py [--outbox DIR] [--no-push] [--reset]
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import subprocess
import sys
from pathlib import Path

from cache_common import (CLOSED_TABLE, DATA_BRANCH, OPEN_TABLE, PF_COLS, PF_TABLE, REPO_URL, RETENTION_DAYS, SNAP_COLS,
                          SNAP_TABLE, TRADE_COLS, connect, sha256_bytes)

HERE = Path(__file__).resolve().parent
CHUNK_ROWS = 100_000


def _enc(v):
    if isinstance(v, (dt.datetime, dt.date)):
        return v.isoformat(sep=" ")
    return float(v) if hasattr(v, "as_tuple") else v  # Decimal -> float


def _write_batch(outbox: Path, name: str, cols: list[str], rows) -> dict:
    body = "\n".join(json.dumps([_enc(v) for v in r], separators=(",", ":")) for r in rows).encode()
    data = gzip.compress(json.dumps(cols).encode() + b"\n" + body, compresslevel=6, mtime=0)
    (outbox / name).write_bytes(data)
    return {"name": name, "sha256": sha256_bytes(data), "rows": len(rows)}


def _trade_select(table: str, is_open: bool) -> str:
    close_type = "NULL::varchar" if is_open else "TRIM(close_type)"
    return (f"SELECT guid, TRIM(model), TRIM(product), TRIM(product_type), created, last_update, TRIM(signal), entry_price, "
            f"latest_price, trade_quantity::float8, net_return, alt_net_return, min_net_return, max_net_return, {close_type}, "
            f"TRIM(trade_reason), TRIM(strategy_name), target_profit::float8, target_loss::float8 FROM {table}")


def export(outbox: Path, now: dt.datetime, reset: bool) -> dict:
    outbox.mkdir(parents=True, exist_ok=True)
    state_path = outbox.parent / (outbox.name + "_state.json")
    state = {} if reset or not state_path.exists() else json.loads(state_path.read_text())
    window_start = (now - dt.timedelta(days=RETENTION_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
    old_batches = state.get("batches", [])
    batches = [b for b in old_batches if dt.datetime.fromisoformat(b["max_ts"]) >= window_start]
    for old in old_batches:
        if old not in batches:
            (outbox / old["name"]).unlink(missing_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%S")

    conn = connect("PG")
    try:
        cur = conn.cursor()
        # --- snapshots: append by snapshot_id -------------------------------------------------------------------
        last_id = state.get("last_snapshot_id", 0)
        cur.execute(f"SELECT {', '.join(SNAP_COLS)} FROM {SNAP_TABLE} WHERE snapshot_id > %s AND snapshot_timestamp >= %s "
                    f"ORDER BY snapshot_id", (last_id, window_start))
        while True:
            rows = cur.fetchmany(CHUNK_ROWS)
            if not rows:
                break
            info = _write_batch(outbox, f"snap_{rows[0][0]}_{rows[-1][0]}.jsonl.gz", SNAP_COLS, rows)
            info.update(kind="snap", max_ts=max(r[1] for r in rows).isoformat())
            batches.append(info)
            last_id = rows[-1][0]
        # --- closed trades: GUID diff. Rows enter the closed table late with their OLD last_update/created, so no
        # timestamp watermark can see them; instead export every window GUID not yet exported (immutable once closed).
        guid_path = outbox.parent / (outbox.name + "_guids.txt")
        exported = set() if reset or not guid_path.exists() else set(guid_path.read_text().split())
        cur.execute(f"SELECT guid FROM {CLOSED_TABLE} WHERE created >= %s", (window_start,))
        window_guids = {r[0] for r in cur.fetchall()}
        missing = sorted(window_guids - exported)
        for i in range(0, len(missing), CHUNK_ROWS):
            cur.execute(_trade_select(CLOSED_TABLE, False) + " WHERE guid = ANY(%s) ORDER BY created, guid", (missing[i:i + CHUNK_ROWS],))
            rows = cur.fetchall()
            info = _write_batch(outbox, f"closed_{stamp}_{len(batches)}.jsonl.gz", TRADE_COLS, rows)
            info.update(kind="closed", max_ts=max(r[4] for r in rows).isoformat())
            batches.append(info)
        guid_path.write_text("\n".join(sorted(window_guids)))
        # --- full-replace tables --------------------------------------------------------------------------------
        latest: dict[str, dict] = {}
        cur.execute(_trade_select(OPEN_TABLE, True))
        latest["open"] = _write_batch(outbox, "open_latest.jsonl.gz", TRADE_COLS, cur.fetchall())
        cur.execute(f"SELECT TRIM(model), TRIM(product), TRIM(product_type), TRIM(strategy_name), TRIM(strategy_params), target_profit::int "
                    f"FROM {PF_TABLE} WHERE model IS NOT NULL")
        latest["pf"] = _write_batch(outbox, "product_forex_latest.jsonl.gz", PF_COLS, cur.fetchall())
    finally:
        conn.close()

    manifest = {"version": 1, "generated_at": now.isoformat(timespec="seconds"), "window_start": window_start.isoformat(sep=" "),
                "retention_days": RETENTION_DAYS,
                "batches": [{k: b[k] for k in ("name", "kind", "sha256", "rows")} for b in batches],
                "latest": [{"name": v["name"], "kind": k, "sha256": v["sha256"], "rows": v["rows"]} for k, v in latest.items()]}
    (outbox / "manifest.json").write_text(json.dumps(manifest, indent=1))
    state.update(last_snapshot_id=last_id, batches=batches)
    state_path.write_text(json.dumps(state))
    return manifest


def _git(outbox: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(outbox), *args], check=True, capture_output=True, text=True)


def publish(outbox: Path, now: dt.datetime) -> None:
    """One orphan commit per run, force-pushed. The persistent local repo lets git send only blobs the remote lacks."""
    if not (outbox / ".git").exists():
        _git(outbox, "init", "-q")
        _git(outbox, "config", "user.name", "top10-cache-bot")
        _git(outbox, "config", "user.email", "top10-cache-bot@users.noreply.github.com")
    _git(outbox, "checkout", "-q", "--orphan", "tmp_publish")
    _git(outbox, "add", "-A")
    _git(outbox, "commit", "-q", "-m", f"top10 cache {now.isoformat(timespec='seconds')}")
    _git(outbox, "branch", "-M", DATA_BRANCH)
    _git(outbox, "push", "-q", "--force", REPO_URL, f"{DATA_BRANCH}:{DATA_BRANCH}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outbox", type=Path, default=HERE / "outbox")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--reset", action="store_true", help="ignore saved state and re-export the whole retention window")
    args = ap.parse_args()
    now = dt.datetime.now()
    manifest = export(args.outbox, now, args.reset)
    n = sum(b["rows"] for b in manifest["batches"])
    print(f"exported: {len(manifest['batches'])} batches / {n} rows in window, window_start={manifest['window_start']}")
    if not args.no_push:
        publish(args.outbox, now)
        print(f"published to {DATA_BRANCH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
