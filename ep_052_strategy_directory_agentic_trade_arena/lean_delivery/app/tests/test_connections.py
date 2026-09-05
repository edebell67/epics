# VERSION HISTORY v1.0.0 · 2026-09-02 · Ten API clients, scoped heartbeat/disconnect, expiry and restart without an agent runner.
from uuid import uuid4

from fastapi.testclient import TestClient

from lean_exchange.api import create_app
from lean_exchange.config import Settings, load_settings


def headers(credential):
    return {'Authorization': 'Bearer ' + credential['token']}


def test_ten_connections_expire_reconnect_and_preserve_on_restart(tmp_path):
    now = [1000.0]
    cfg = Settings.model_validate(load_settings().model_dump() | {'connection_expiry_seconds': 30})
    path = tmp_path / 'connections.sqlite'
    app = create_app(cfg, database=path, clock=lambda: now[0])
    owner = app.state.authority.create_owner('Test owner')
    agents, connections = [], []
    with TestClient(app) as client:
        for index in range(10):
            agent = client.post('/v1/owner/agents', headers=headers(owner), json={'name': f'External client {index}'}).json()
            agents.append(agent)
            request = {'request_id': str(uuid4()), 'purpose': 'strategy_trading'}
            response = client.post('/v1/connections', headers=headers(agent), json=request)
            assert response.status_code == 200
            connection = response.json()
            connections.append(connection)
            assert client.post('/v1/connections', headers=headers(agent), json=request).json()['id'] == connection['id']
        visible = client.get('/v1/arena/connections', headers=headers(owner)).json()['items']
        assert len(visible) == 10
        assert all('owner_id' not in item for item in visible)
        wrong = client.post('/v1/connections/' + connections[0]['id'] + '/heartbeat', headers=headers(agents[1]))
        assert wrong.status_code == 404
        now[0] += 31
        assert client.get('/v1/arena/connections', headers=headers(owner)).json()['items'] == []
        assert client.post('/v1/connections/' + connections[0]['id'] + '/heartbeat', headers=headers(agents[0])).status_code == 200
    with TestClient(create_app(cfg, database=path, clock=lambda: now[0])) as client:
        assert len(client.get('/v1/arena/connections', headers=headers(owner)).json()['items']) == 1
        assert client.delete('/v1/connections/' + connections[0]['id'], headers=headers(agents[0])).status_code == 200
        assert client.post('/v1/connections/' + connections[0]['id'] + '/heartbeat', headers=headers(agents[0])).status_code == 404
        request = {'request_id': str(uuid4()), 'purpose': 'strategy_trading'}
        assert client.post('/v1/connections', headers=headers(agents[0]), json=request).status_code == 200
        assert len(client.get('/v1/arena/connections', headers=headers(owner)).json()['items']) == 1
