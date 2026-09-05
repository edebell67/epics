# VERSION HISTORY v1.1.0 · 2026-09-02 · Latest-first owner history with an explicit older-message cursor for the workspace.
# v1.0.0 · 2026-09-02 · Owner-scoped feedback, target-only acknowledgement and independently posted agent replies.
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from .contracts import Contract, FeedbackRequest, SafeText, fingerprint


class FeedbackReply(Contract):
    request_id: UUID
    message: SafeText


def router(authority):
    routes, store = APIRouter(), authority.store

    def detail(db, row, agent_id=None):
        item = dict(row)
        item.pop('fingerprint', None)
        target_filter, params = (' AND agent_id=?', (row['id'], agent_id)) if agent_id else ('', (row['id'],))
        item['recipients'] = [dict(target) for target in db.execute(
            'SELECT agent_id,acknowledged_at FROM feedback_targets WHERE feedback_id=?' + target_filter + ' ORDER BY agent_id', params)]
        item['replies'] = [dict(reply) for reply in db.execute(
            'SELECT id,agent_id,message,created_at FROM feedback_replies WHERE feedback_id=?' + target_filter + ' ORDER BY created_at,id', params)]
        if agent_id:
            item.pop('owner_id', None)
        return item

    def target(db, feedback_id, agent_id):
        if not db.execute('SELECT 1 FROM feedback_targets WHERE feedback_id=? AND agent_id=?', (feedback_id, agent_id)).fetchone():
            raise HTTPException(404, 'Feedback not found')

    @routes.post('/v1/owner/feedback')
    def send(request: FeedbackRequest, actor=Depends(authority.owner)):
        if len(set(request.agent_ids)) != len(request.agent_ids):
            raise HTTPException(422, 'Duplicate recipients')
        with store.transaction(immediate=True) as db:
            existing = db.execute('SELECT * FROM feedback WHERE owner_id=? AND request_id=?',
                                  (actor['owner_id'], str(request.request_id))).fetchone()
            if existing:
                if existing['fingerprint'] != fingerprint(request):
                    raise HTTPException(409, 'REQUEST_ID_CONFLICT')
                return detail(db, existing)
            for agent_id in request.agent_ids:
                if not db.execute('SELECT 1 FROM agents WHERE id=? AND owner_id=?', (str(agent_id), actor['owner_id'])).fetchone():
                    raise HTTPException(404, 'Recipient not found')
            feedback_id = str(uuid4())
            db.execute('INSERT INTO feedback(id,owner_id,request_id,fingerprint,message,created_at) VALUES (?,?,?,?,?,?)',
                       (feedback_id, actor['owner_id'], str(request.request_id), fingerprint(request), request.message,
                        datetime.now(timezone.utc).isoformat()))
            db.executemany('INSERT INTO feedback_targets VALUES (?,?,NULL)',
                           [(feedback_id, str(agent_id)) for agent_id in request.agent_ids])
            return detail(db, db.execute('SELECT * FROM feedback WHERE id=?', (feedback_id,)).fetchone())

    @routes.get('/v1/owner/feedback')
    def owner_read(after: int = Query(default=0, ge=0), before: int | None = Query(default=None, gt=0),
                   latest: bool = False, actor=Depends(authority.owner)):
        if after and before:
            raise HTTPException(422, 'Use either after or before, not both')
        with store.transaction() as db:
            direction = 'DESC' if latest or before else 'ASC'
            comparison = 'cursor<?' if before else 'cursor>?'
            rows = db.execute(f'SELECT * FROM feedback WHERE owner_id=? AND {comparison} ORDER BY cursor {direction} LIMIT ?',
                              (actor['owner_id'], before if before else after, authority.settings.activity_page_size)).fetchall()
            return {'items': [detail(db, row) for row in rows], 'next_cursor': rows[-1]['cursor'] if rows else after}

    @routes.get('/v1/owner/feedback/{feedback_id}')
    def owner_detail(feedback_id: UUID, actor=Depends(authority.owner)):
        with store.transaction() as db:
            row = db.execute('SELECT * FROM feedback WHERE id=? AND owner_id=?', (str(feedback_id), actor['owner_id'])).fetchone()
            if not row:
                raise HTTPException(404, 'Feedback not found')
            return detail(db, row)

    @routes.get('/v1/me/feedback')
    def agent_read(after: int = Query(default=0, ge=0), actor=Depends(authority.agent)):
        with store.transaction() as db:
            rows = db.execute('''SELECT f.* FROM feedback f JOIN feedback_targets t ON f.id=t.feedback_id
                                 WHERE t.agent_id=? AND f.cursor>? ORDER BY f.cursor LIMIT ?''',
                              (actor['agent_id'], after, authority.settings.activity_page_size)).fetchall()
            return {'items': [detail(db, row, actor['agent_id']) for row in rows], 'next_cursor': rows[-1]['cursor'] if rows else after}

    @routes.post('/v1/me/feedback/{feedback_id}/ack')
    def acknowledge(feedback_id: UUID, actor=Depends(authority.agent)):
        with store.transaction(immediate=True) as db:
            target(db, str(feedback_id), actor['agent_id'])
            db.execute('UPDATE feedback_targets SET acknowledged_at=COALESCE(acknowledged_at,?) WHERE feedback_id=? AND agent_id=?',
                       (datetime.now(timezone.utc).isoformat(), str(feedback_id), actor['agent_id']))
            row = db.execute('SELECT acknowledged_at FROM feedback_targets WHERE feedback_id=? AND agent_id=?',
                             (str(feedback_id), actor['agent_id'])).fetchone()
        return {'feedback_id': str(feedback_id), 'acknowledged_at': row['acknowledged_at'], 'meaning': 'receipt acknowledged, not proof of compliance'}

    @routes.post('/v1/me/feedback/{feedback_id}/responses')
    def reply(feedback_id: UUID, request: FeedbackReply, actor=Depends(authority.agent)):
        with store.transaction(immediate=True) as db:
            target(db, str(feedback_id), actor['agent_id'])
            row = db.execute('SELECT * FROM feedback_replies WHERE agent_id=? AND request_id=?',
                             (actor['agent_id'], str(request.request_id))).fetchone()
            if row:
                if row['feedback_id'] != str(feedback_id) or row['fingerprint'] != fingerprint(request):
                    raise HTTPException(409, 'REQUEST_ID_CONFLICT')
                return {key: row[key] for key in ('id', 'feedback_id', 'message', 'created_at')}
            reply_id, now = str(uuid4()), datetime.now(timezone.utc).isoformat()
            db.execute('INSERT INTO feedback_replies VALUES (?,?,?,?,?,?,?)',
                       (reply_id, str(feedback_id), actor['agent_id'], str(request.request_id), fingerprint(request), request.message, now))
            return {'id': reply_id, 'feedback_id': str(feedback_id), 'message': request.message, 'created_at': now}

    return routes
