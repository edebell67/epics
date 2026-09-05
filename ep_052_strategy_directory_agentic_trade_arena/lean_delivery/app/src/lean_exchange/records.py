# VERSION HISTORY v1.4.1 · 2026-09-02 · Refuse future database schemas instead of silently downgrading their version on startup.
# v1.4.0 · 2026-09-02 · Persist public Arena projections atomically and backfill earlier committed records once.
# v1.3.0 · 2026-09-02 · Add immutable issued-unit baselines, published quotes and atomic trade/request records.
# v1.2.0 · 2026-09-02 · Persist owner feedback, per-agent acknowledgements/replies and reported decisions.
# v1.1.0 · 2026-09-02 · Add participant funding movements and actor-scoped delivered-query records.
# v1.0.0 · 2026-09-02 · Durable identities, scoped credentials, connections and API activity with sync-stable IDs.
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from .config import APP_ROOT

SCHEMA = '''
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS owners (id TEXT PRIMARY KEY,name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agents (
 id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES owners(id),name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS credentials (
 id TEXT PRIMARY KEY,token_hash TEXT UNIQUE NOT NULL,owner_id TEXT NOT NULL REFERENCES owners(id),
 agent_id TEXT REFERENCES agents(id),role TEXT NOT NULL CHECK(role IN ('owner','agent')),
 expires_at REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS connections (
 id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES owners(id),agent_id TEXT NOT NULL REFERENCES agents(id),
 request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,connected_at REAL NOT NULL,last_seen REAL NOT NULL,
 disconnected INTEGER NOT NULL DEFAULT 0,UNIQUE(agent_id,request_id));
CREATE TABLE IF NOT EXISTS activity (
 cursor INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,occurred_at TEXT NOT NULL,
 owner_id TEXT,agent_id TEXT,operation TEXT NOT NULL,status_code INTEGER NOT NULL,request_id TEXT);
CREATE TABLE IF NOT EXISTS rate_windows (
 subject TEXT PRIMARY KEY,window INTEGER NOT NULL,count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS participant_allocations (
 agent_id TEXT PRIMARY KEY REFERENCES agents(id),seed_usd TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS participant_movements (
 id TEXT PRIMARY KEY,agent_id TEXT NOT NULL REFERENCES agents(id),operation_id TEXT NOT NULL,
 kind TEXT NOT NULL,amount_usd TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(agent_id,operation_id));
CREATE TABLE IF NOT EXISTS query_deliveries (
 id TEXT PRIMARY KEY,agent_id TEXT NOT NULL REFERENCES agents(id),request_id TEXT NOT NULL,
 revision INTEGER NOT NULL,fingerprint TEXT NOT NULL,payload TEXT NOT NULL,fee_usd TEXT NOT NULL,
 UNIQUE(agent_id,request_id,revision));
CREATE TABLE IF NOT EXISTS feedback (
 cursor INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,owner_id TEXT NOT NULL REFERENCES owners(id),
 request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,message TEXT NOT NULL,created_at TEXT NOT NULL,
 UNIQUE(owner_id,request_id));
CREATE TABLE IF NOT EXISTS feedback_targets (
 feedback_id TEXT NOT NULL REFERENCES feedback(id),agent_id TEXT NOT NULL REFERENCES agents(id),
 acknowledged_at TEXT,PRIMARY KEY(feedback_id,agent_id));
CREATE TABLE IF NOT EXISTS feedback_replies (
 id TEXT PRIMARY KEY,feedback_id TEXT NOT NULL REFERENCES feedback(id),agent_id TEXT NOT NULL REFERENCES agents(id),
 request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,message TEXT NOT NULL,created_at TEXT NOT NULL,
 UNIQUE(agent_id,request_id));
CREATE TABLE IF NOT EXISTS decision_reports (
 cursor INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,agent_id TEXT NOT NULL REFERENCES agents(id),
 request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL,
 UNIQUE(agent_id,request_id));
CREATE TABLE IF NOT EXISTS strategy_units (
 strategy_id TEXT PRIMARY KEY,issued_units INTEGER NOT NULL CHECK(issued_units>0));
CREATE TABLE IF NOT EXISTS price_quotes (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,strategy_id TEXT NOT NULL REFERENCES strategy_units(strategy_id),
 source_version TEXT NOT NULL,payload TEXT NOT NULL,published_at TEXT NOT NULL,
 UNIQUE(strategy_id,source_version));
CREATE TABLE IF NOT EXISTS trade_records (
 cursor INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,agent_id TEXT NOT NULL REFERENCES agents(id),
 request_id TEXT NOT NULL,strategy_id TEXT NOT NULL REFERENCES strategy_units(strategy_id),side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
 units INTEGER NOT NULL CHECK(units>0),price_id TEXT NOT NULL REFERENCES price_quotes(id),payload TEXT NOT NULL,
 UNIQUE(agent_id,request_id));
CREATE TABLE IF NOT EXISTS trade_requests (
 agent_id TEXT NOT NULL REFERENCES agents(id),request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,
 status_code INTEGER NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(agent_id,request_id));
CREATE TABLE IF NOT EXISTS arena_events (
 cursor INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,source_key TEXT UNIQUE NOT NULL,
 occurred_at TEXT NOT NULL,agent_id TEXT NOT NULL,operation TEXT NOT NULL,strategy_id TEXT,
 resource_id TEXT NOT NULL,request_id TEXT,payload TEXT NOT NULL);
'''


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(os.environ.get('EP052_DATABASE', APP_ROOT / 'runtime' / 'exchange.sqlite'))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] > 5:
                raise ValueError('DATABASE_SCHEMA_NEWER_THAN_APPLICATION')
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript(SCHEMA)
            db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)', ('instance_id', str(uuid4())))
            from .arena import backfill
            backfill(db)
            db.execute('PRAGMA user_version=5')

    @contextmanager
    def transaction(self, immediate=False):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            if immediate:
                db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def record(self, operation, status_code, actor=None, request_id=None):
        actor = actor or {}
        with self.transaction() as db:
            db.execute('INSERT INTO activity(event_id,occurred_at,owner_id,agent_id,operation,status_code,request_id) VALUES (?,?,?,?,?,?,?)',
                       (str(uuid4()), datetime.now(timezone.utc).isoformat(), actor.get('owner_id'),
                        actor.get('agent_id'), operation, status_code, request_id))

    def rate_allowed(self, subject, now, window_seconds, limit):
        window = int(now // window_seconds)
        with self.transaction(immediate=True) as db:
            row = db.execute('SELECT window,count FROM rate_windows WHERE subject=?', (subject,)).fetchone()
            count = row['count'] + 1 if row and row['window'] == window else 1
            db.execute('INSERT INTO rate_windows VALUES (?,?,?) ON CONFLICT(subject) DO UPDATE SET window=excluded.window,count=excluded.count',
                       (subject, window, count))
            return count <= limit
