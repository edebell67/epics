# VERSION HISTORY v1.1.0 · 2026-09-02 · Publish connection/disconnection transitions without owner associations.
# v1.0.0 · 2026-09-02 · Independent visiting-agent connections with persisted heartbeat/disconnect state.
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from .auth import Authority
from .contracts import ConnectionRequest, fingerprint
from .arena import emit


def router(authority: Authority):
    routes = APIRouter()
    store, cfg, clock = authority.store, authority.settings, authority.clock

    def project(row):
        item = dict(row)
        item['purpose'] = 'strategy_trading'
        item['active'] = not item['disconnected'] and clock() - item['last_seen'] < cfg.connection_expiry_seconds
        item.pop('fingerprint', None)
        return item

    @routes.post('/v1/connections')
    def connect(request: ConnectionRequest, actor=Depends(authority.agent)):
        with store.transaction(immediate=True) as db:
            row = db.execute('SELECT * FROM connections WHERE agent_id=? AND request_id=?',
                             (actor['agent_id'], str(request.request_id))).fetchone()
            if row:
                if row['fingerprint'] != fingerprint(request):
                    raise HTTPException(409, 'REQUEST_ID_CONFLICT')
                return project(row)
            now = clock()
            connection_id = str(uuid4())
            # A fresh connect replaces this agent's earlier presence; never creates an agent worker.
            db.execute('UPDATE connections SET disconnected=1 WHERE agent_id=?', (actor['agent_id'],))
            db.execute('INSERT INTO connections VALUES (?,?,?,?,?,?,?,0)',
                       (connection_id, actor['owner_id'], actor['agent_id'], str(request.request_id), fingerprint(request), now, now))
            emit(db, source_key='connect:' + connection_id, agent_id=actor['agent_id'], operation='CONNECT',
                 resource_id=connection_id, request_id=str(request.request_id), payload={'purpose': 'strategy_trading'})
            return project(db.execute('SELECT * FROM connections WHERE id=?', (connection_id,)).fetchone())

    @routes.post('/v1/connections/{connection_id}/heartbeat')
    def heartbeat(connection_id: UUID, actor=Depends(authority.agent)):
        with store.transaction(immediate=True) as db:
            result = db.execute('UPDATE connections SET last_seen=? WHERE id=? AND agent_id=? AND disconnected=0',
                                (clock(), str(connection_id), actor['agent_id']))
            if not result.rowcount:
                raise HTTPException(404, 'Active connection not found')
            return project(db.execute('SELECT * FROM connections WHERE id=?', (str(connection_id),)).fetchone())

    @routes.delete('/v1/connections/{connection_id}')
    def disconnect(connection_id: UUID, actor=Depends(authority.agent)):
        with store.transaction(immediate=True) as db:
            prior = db.execute('SELECT disconnected FROM connections WHERE id=? AND agent_id=?',
                               (str(connection_id), actor['agent_id'])).fetchone()
            result = db.execute('UPDATE connections SET disconnected=1 WHERE id=? AND agent_id=?', (str(connection_id), actor['agent_id']))
            if not result.rowcount:
                raise HTTPException(404, 'Connection not found')
            if not prior['disconnected']:
                emit(db, source_key='disconnect:' + str(connection_id), agent_id=actor['agent_id'], operation='DISCONNECT',
                     resource_id=str(connection_id), payload={'purpose': 'strategy_trading'})
        return {'disconnected': True}

    @routes.get('/v1/arena/connections')
    def connected(actor=Depends(authority.authenticate)):
        with store.transaction() as db:
            # Arena only exposes public agent identity/presence, not owner association or credentials.
            rows = db.execute('SELECT id,agent_id,last_seen,disconnected FROM connections WHERE disconnected=0').fetchall()
            items = [project(row) for row in rows]
        return {'items': [item for item in items if item['active']]}

    return routes
