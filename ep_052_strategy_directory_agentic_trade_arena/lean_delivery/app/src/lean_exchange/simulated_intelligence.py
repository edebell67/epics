# VERSION HISTORY v1.0.1 · 2026-09-02 · Compare header bytes safely for malformed non-ASCII credential input.
# v1.0.0 · 2026-09-02 · Separate replaceable random-selection API with durable, actor-scoped delivery receipts.
from contextlib import closing
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import APP_ROOT, Settings, load_settings
from .contracts import QueryDelivery, QueryRequest, fingerprint
from .providers import DirectoryProvider, ProviderError


def create_app(settings: Settings | None = None, database: Path | None = None,
               token: str | None = None, directory: DirectoryProvider | None = None) -> FastAPI:
    cfg = settings or load_settings()
    service_token = token or os.environ.get('EP052_INTELLIGENCE_TOKEN')
    if not service_token or len(service_token) < 32:
        raise ValueError('Configure a service token of at least 32 characters outside source and logs')
    database = database or APP_ROOT / 'runtime' / 'intelligence.sqlite'
    database.parent.mkdir(parents=True, exist_ok=True)
    provider = directory or DirectoryProvider(cfg)
    with closing(sqlite3.connect(database)) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('''CREATE TABLE IF NOT EXISTS deliveries (
            delivery_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, request_id TEXT NOT NULL,
            revision INTEGER NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
            UNIQUE(agent_id,request_id,revision))''')
        db.commit()
    app = FastAPI(title='EP052 Simulated Intelligence Provider', version='0.1.0',
                  description='Separate random-list provider; no rankings, agent execution or participant funds.')
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

    def actor(authorization: str = Header(default=''), x_ep052_agent_id: UUID | None = Header(default=None)) -> str:
        if not hmac.compare_digest(authorization.encode(), ('Bearer ' + service_token).encode()):
            raise HTTPException(401, 'Invalid service credential')
        if x_ep052_agent_id is None:
            raise HTTPException(422, 'Trusted caller must supply its authenticated agent identity')
        return str(x_ep052_agent_id)

    @app.get('/health')
    def health():
        return {'status': 'ok', 'mode': 'simulated_random', 'charging': 'participant_gateway_not_provider'}

    @app.post('/v1/queries', response_model=QueryDelivery)
    def query(request: QueryRequest, agent_id: str = Depends(actor)):
        if request.limit > cfg.max_query_results:
            raise HTTPException(422, 'Configured query result limit exceeded')
        identity = (agent_id, str(request.request_id), request.revision)
        request_hash = fingerprint(request)

        def existing(db):
            row = db.execute('SELECT fingerprint,payload FROM deliveries WHERE agent_id=? AND request_id=? AND revision=?', identity).fetchone()
            if row:
                if row[0] != request_hash:
                    raise HTTPException(409, 'REQUEST_ID_CONFLICT')
                return QueryDelivery.model_validate_json(row[1])
            return None

        with closing(sqlite3.connect(database)) as db:
            recovered = existing(db)
            if recovered:
                return recovered
        try:
            snapshot = provider.fetch()
        except ProviderError as exc:
            raise HTTPException(503, str(exc)) from exc
        choices = [x.strategy_id for x in snapshot.items if x.status == 'active']
        if request.strategy_ids:
            requested = set(request.strategy_ids)
            choices = [sid for sid in choices if sid in requested]
        selected = secrets.SystemRandom().sample(choices, min(len(choices), request.limit))
        result = QueryDelivery(delivery_id=uuid4(), request_id=request.request_id, revision=request.revision,
                               result_version=uuid4(), created_at=datetime.now(timezone.utc),
                               source_version=snapshot.source_version, mode='simulated_random',
                               strategy_ids=selected, query=request,
                               notice='Random list, not a ranking. Query kind/time window not evaluated. Confirm exchange availability before buying.')
        with closing(sqlite3.connect(database, timeout=cfg.provider_timeout_seconds)) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                recovered = existing(db)
                if recovered:
                    return recovered
                db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?,?)',
                           (str(result.delivery_id), *identity, request_hash, result.model_dump_json()))
                db.commit()
            finally:
                if db.in_transaction:
                    db.rollback()
        return result

    @app.get('/v1/deliveries/{delivery_id}', response_model=QueryDelivery)
    def recover(delivery_id: UUID, agent_id: str = Depends(actor)):
        with closing(sqlite3.connect(database)) as db:
            row = db.execute('SELECT payload FROM deliveries WHERE delivery_id=? AND agent_id=?',
                             (str(delivery_id), agent_id)).fetchone()
        if not row:
            raise HTTPException(404, 'Delivery not found')
        return QueryDelivery.model_validate_json(row[0])

    return app


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('lean_exchange.simulated_intelligence:create_app', factory=True,
                host='127.0.0.1', port=int(os.environ.get('EP052_INTELLIGENCE_PORT', '8055')))
