# VERSION HISTORY v1.1.0 · 2026-09-02 · Seed new participant allocations once when an owner registers an agent.
# v1.0.0 · 2026-09-02 · Owner-scoped provision/revoke/read APIs; no public self-registration.
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field

from .auth import Authority
from .contracts import Contract
from .participant_funds import initialise


class AgentRegistration(Contract):
    name: str = Field(min_length=1, max_length=128)


def router(authority: Authority):
    routes = APIRouter()
    store = authority.store

    @routes.get('/v1/me')
    def identity(actor=Depends(authority.authenticate)):
        return {key: actor[key] for key in ('owner_id', 'agent_id', 'role', 'expires_at')}

    @routes.post('/v1/owner/agents', status_code=201)
    def register(request: AgentRegistration, actor=Depends(authority.owner)):
        with store.transaction() as db:
            agent_id = str(uuid4())
            db.execute('INSERT INTO agents VALUES (?,?,?)', (agent_id, actor['owner_id'], request.name))
            initialise(db, agent_id, authority.settings.seed_funds)
            return authority.issue(db, actor['owner_id'], agent_id, 'agent')

    @routes.get('/v1/owner/agents')
    def agents(actor=Depends(authority.owner)):
        with store.transaction() as db:
            return {'items': [dict(row) for row in db.execute('SELECT id,name FROM agents WHERE owner_id=? ORDER BY id', (actor['owner_id'],))]}

    @routes.delete('/v1/owner/credentials/{credential_id}')
    def revoke(credential_id: UUID, actor=Depends(authority.owner)):
        with store.transaction() as db:
            result = db.execute('UPDATE credentials SET revoked=1 WHERE id=? AND owner_id=?',
                                (str(credential_id), actor['owner_id']))
            if result.rowcount == 0:
                raise HTTPException(404, 'Credential not found')
        return {'revoked': True, 'credential_id': credential_id}

    return routes
