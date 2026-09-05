# VERSION HISTORY v1.2.0 · 2026-09-02 · Publish report existence without exposing private explanation text.
# v1.1.0 · 2026-09-02 · Accept only actor-owned matching settled trade links; reports never execute trades.
# v1.0.0 · 2026-09-02 · Durable external HOLD reports without fees; unverified trade claims cannot change positions.
from datetime import datetime, timezone
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from .contracts import DecisionReport, fingerprint
from .arena import report_event


def router(authority):
    routes, store = APIRouter(), authority.store

    def detail(row):
        return {'id': row['id'], 'cursor': row['cursor'], 'created_at': row['created_at'],
                'report': json.loads(row['payload']), 'fee_usd': '0', 'executed_trade': False}

    @routes.post('/v1/me/decisions')
    def report(request: DecisionReport, actor=Depends(authority.agent)):
        with store.transaction(immediate=True) as db:
            if request.action != 'HOLD':
                trade = db.execute('SELECT side FROM trade_records WHERE id=? AND agent_id=?',
                                   (str(request.trade_id), actor['agent_id'])).fetchone()
                if not trade or trade['side'] != request.action:
                    raise HTTPException(409, 'VERIFIED_TRADE_REQUIRED')
            row = db.execute('SELECT * FROM decision_reports WHERE agent_id=? AND request_id=?',
                             (actor['agent_id'], str(request.request_id))).fetchone()
            if row:
                if row['fingerprint'] != fingerprint(request):
                    raise HTTPException(409, 'REQUEST_ID_CONFLICT')
                return detail(row)
            report_id = str(uuid4())
            db.execute('INSERT INTO decision_reports(id,agent_id,request_id,fingerprint,payload,created_at) VALUES (?,?,?,?,?,?)',
                       (report_id, actor['agent_id'], str(request.request_id), fingerprint(request), request.model_dump_json(),
                        datetime.now(timezone.utc).isoformat()))
            saved = db.execute('SELECT * FROM decision_reports WHERE id=?', (report_id,)).fetchone()
            report_event(db, actor['agent_id'], report_id, str(request.request_id), request.action,
                         str(request.trade_id) if request.trade_id else None, saved['created_at'])
            return detail(saved)

    @routes.get('/v1/me/decisions')
    def reports(after: int = Query(default=0, ge=0), actor=Depends(authority.agent)):
        with store.transaction() as db:
            rows = db.execute('SELECT * FROM decision_reports WHERE agent_id=? AND cursor>? ORDER BY cursor LIMIT ?',
                              (actor['agent_id'], after, authority.settings.activity_page_size)).fetchall()
            return {'items': [detail(row) for row in rows], 'next_cursor': rows[-1]['cursor'] if rows else after}

    return routes
