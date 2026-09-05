# VERSION HISTORY v1.1.0 · 2026-09-02 · Declare bearer security in OpenAPI so protected APIs can be tested interactively.
# v1.0.0 · 2026-09-02 · Opaque owner/agent credentials, durable expiry/revocation and role boundaries.
from hashlib import sha256
import secrets
import time
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings
from .records import Store

bearer = HTTPBearer(auto_error=False)


class Authority:
    def __init__(self, store: Store, settings: Settings, clock=time.time):
        self.store, self.settings, self.clock = store, settings, clock

    def issue(self, db, owner_id, agent_id, role):
        token = secrets.token_urlsafe(48)
        credential_id = str(uuid4())
        expires_at = self.clock() + self.settings.credential_ttl_seconds
        db.execute('INSERT INTO credentials(id,token_hash,owner_id,agent_id,role,expires_at) VALUES (?,?,?,?,?,?)',
                   (credential_id, sha256(token.encode()).hexdigest(), owner_id, agent_id, role, expires_at))
        return {'credential_id': credential_id, 'token': token, 'expires_at': expires_at,
                'owner_id': owner_id, 'agent_id': agent_id, 'role': role}

    def create_owner(self, name):
        with self.store.transaction() as db:
            owner_id = str(uuid4())
            db.execute('INSERT INTO owners VALUES (?,?)', (owner_id, name))
            return self.issue(db, owner_id, None, 'owner')

    def authenticate(self, request: Request, credential: HTTPAuthorizationCredentials | None = Depends(bearer)):
        header = request.headers.get('authorization', '')
        if not header.startswith('Bearer ') or len(header) > 256:
            raise HTTPException(401, 'Valid bearer credential required')
        digest = sha256(header[7:].encode()).hexdigest()
        with self.store.transaction() as db:
            row = db.execute('SELECT id,owner_id,agent_id,role,expires_at,revoked FROM credentials WHERE token_hash=?', (digest,)).fetchone()
        if not row or row['revoked'] or row['expires_at'] <= self.clock():
            raise HTTPException(401, 'Invalid, expired or revoked credential')
        actor = dict(row)
        request.state.actor = actor
        return actor

    def owner(self, request: Request, credential: HTTPAuthorizationCredentials | None = Depends(bearer)):
        actor = self.authenticate(request)
        if actor['role'] != 'owner':
            raise HTTPException(403, 'Owner scope required')
        return actor

    def agent(self, request: Request, credential: HTTPAuthorizationCredentials | None = Depends(bearer)):
        actor = self.authenticate(request)
        if actor['role'] != 'agent':
            raise HTTPException(403, 'Agent scope required')
        return actor
