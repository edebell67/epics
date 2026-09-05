# VERSION HISTORY v1.1.0 · 2026-09-02 · Commit public delivered-research event with the charged receipt.
# v1.0.1 · 2026-09-02 · Make receipt/balance preflight a consistent short transaction for final-cent retries.
# v1.0.0 · 2026-09-02 · Participant-funded delivery, exact retry and refresh charging in one local commit.
import json
import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from .contracts import QueryRequest, fingerprint
from .arena import query_event
from .participant_funds import FundingError, balance, move
from .providers import ProviderError


def router(authority, provider):
    routes = APIRouter()
    store, cfg = authority.store, authority.settings

    def response(row):
        return {'delivery': json.loads(row['payload']), 'fee_usd': row['fee_usd'], 'currency': 'USD'}

    def existing(db, actor, request):
        row = db.execute('SELECT * FROM query_deliveries WHERE agent_id=? AND request_id=? AND revision=?',
                         (actor['agent_id'], str(request.request_id), request.revision)).fetchone()
        if row and row['fingerprint'] != fingerprint(request):
            raise HTTPException(409, 'REQUEST_ID_CONFLICT')
        return row

    @routes.post('/participant/v1/me/queries')
    def query(request: QueryRequest, actor=Depends(authority.agent)):
        if request.limit > cfg.max_query_results:
            raise HTTPException(422, 'Configured result limit exceeded')
        try:
            with store.transaction(immediate=True) as db:
                row = existing(db, actor, request)
                if row:
                    return response(row)
                if balance(db, actor['agent_id']) < cfg.intelligence_fee:
                    raise FundingError('PARTICIPANT_FUNDS_INSUFFICIENT')
            # No SQLite lock held across network I/O. Result remains internal until the fee/receipt commit.
            result = provider.query(actor['agent_id'], request)
            with store.transaction(immediate=True) as db:
                row = existing(db, actor, request)
                if row:
                    return response(row)
                move(db, actor['agent_id'], 'query:' + str(result.delivery_id), 'INTELLIGENCE', -cfg.intelligence_fee)
                db.execute('INSERT INTO query_deliveries VALUES (?,?,?,?,?,?,?)',
                           (str(result.delivery_id), actor['agent_id'], str(request.request_id), request.revision,
                            fingerprint(request), result.model_dump_json(), str(cfg.intelligence_fee)))
                row = existing(db, actor, request)
                receipt = response(row)
                query_event(db, actor['agent_id'], result.model_dump(mode='json'), cfg.intelligence_fee)
            return receipt
        except FundingError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ProviderError as exc:
            raise HTTPException(503, str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(502, 'INTELLIGENCE_RECEIPT_CONFLICT') from exc

    @routes.get('/participant/v1/me/queries/{delivery_id}')
    def recover(delivery_id: UUID, actor=Depends(authority.agent)):
        with store.transaction() as db:
            row = db.execute('SELECT * FROM query_deliveries WHERE id=? AND agent_id=?',
                             (str(delivery_id), actor['agent_id'])).fetchone()
            if not row:
                raise HTTPException(404, 'Delivery not found')
            return response(row)

    return routes
