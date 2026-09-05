# VERSION HISTORY v1.1.0 · 2026-09-02 · Attribute valid visitors on public routes and align scoped outcomes with the published contract.
# v1.0.1 · 2026-09-02 · Retain validated request identity from bounded JSON bodies without persisting their private contents.
# v1.0.0 · 2026-09-02 · Bounded HTTP input and safe durable action outcomes; owner/agent-scoped cursor reads.
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.responses import JSONResponse


class BodyLimitExceeded(Exception):
    pass


class ActionMiddleware:
    def __init__(self, app, authority):
        self.app, self.authority = app, authority

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        store, cfg, clock = self.authority.store, self.authority.settings, self.authority.clock
        status = 500
        response_started = False
        total = 0
        body_parts = []

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get('body', b''))
            if total > cfg.max_body_bytes:
                raise BodyLimitExceeded()
            body_parts.append(message.get('body', b''))
            return message

        async def capture(message):
            nonlocal status, response_started
            if message['type'] == 'http.response.start':
                status, response_started = message['status'], True
            await send(message)

        try:
            headers = dict(scope.get('headers', []))
            raw_length = headers.get(b'content-length')
            if raw_length and (not raw_length.isdigit() or int(raw_length) > cfg.max_body_bytes):
                await JSONResponse({'code': 'BODY_LIMIT'}, status_code=413)(scope, receive, capture)
            elif not store.rate_allowed('ip:' + str(scope.get('client', ('unknown',))[0]),
                                        clock(), cfg.rate_window_seconds, cfg.requests_per_window):
                await JSONResponse({'code': 'RATE_LIMIT'}, status_code=429)(scope, receive, capture)
            else:
                await self.app(scope, bounded_receive, capture)
        except BodyLimitExceeded:
            if not response_started:
                await JSONResponse({'code': 'BODY_LIMIT'}, status_code=413)(scope, receive, capture)
        finally:
            route = scope.get('route')
            operation = scope['method'] + ' ' + getattr(route, 'path', '[unmatched]')
            request_id = None
            try:
                request_id = str(UUID(headers.get(b'x-request-id', b'').decode()))
            except (ValueError, UnicodeError):
                pass
            try:
                payload = json.loads(b''.join(body_parts))
                if isinstance(payload, dict) and 'request_id' in payload:
                    request_id = str(UUID(str(payload['request_id'])))
            except (ValueError, UnicodeError, TypeError, RecursionError):
                pass
            # Never record URL query strings, Authorization, bodies, tokens or private reasoning.
            actor = scope.get('state', {}).get('actor')
            if actor is None:
                try:
                    actor = self.authority.authenticate(Request(scope))
                except HTTPException:
                    pass
            store.record(operation, status, actor, request_id)


def router(authority):
    routes = APIRouter()

    @routes.get('/v1/me/activity')
    def read(after: int = Query(default=0, ge=0), limit: int | None = Query(default=None, gt=0),
             actor=Depends(authority.authenticate)):
        limit = limit or authority.settings.activity_page_size
        if limit > authority.settings.activity_page_size:
            raise HTTPException(422, 'Configured activity page limit exceeded')
        where = 'owner_id=?' if actor['role'] == 'owner' else 'owner_id=? AND agent_id=?'
        parameters = [actor['owner_id']]
        if actor['role'] == 'agent':
            parameters.append(actor['agent_id'])
        with authority.store.transaction() as db:
            rows = db.execute(f'SELECT * FROM activity WHERE {where} AND cursor>? ORDER BY cursor LIMIT ?',
                              (*parameters, after, limit)).fetchall()
        items = [dict(row) | {'outcome': 'error' if row['status_code'] >= 500 else 'rejected' if row['status_code'] >= 400 else 'success'} for row in rows]
        return {'items': items, 'next_cursor': items[-1]['cursor'] if items else after}

    return routes
