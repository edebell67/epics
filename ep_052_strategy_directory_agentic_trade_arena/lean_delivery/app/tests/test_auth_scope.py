# VERSION HISTORY v1.0.0 · 2026-09-02 · Exercise actual owner/agent access, durable revoke/expiry, input/rate limits and secret redaction.
import json

from fastapi.testclient import TestClient

from lean_exchange.api import create_app
from lean_exchange.config import Settings, load_settings


def auth(credential):
    return {'Authorization': 'Bearer ' + credential['token']}


def test_owner_scoped_registration_and_durable_revocation(tmp_path):
    path = tmp_path / 'auth.sqlite'
    app = create_app(database=path)
    first = app.state.authority.create_owner('Owner A')
    second = app.state.authority.create_owner('Owner B')
    with TestClient(app) as client:
        assert client.get('/v1/me').status_code == 401
        agent = client.post('/v1/owner/agents', json={'name': 'Visiting Hermes'}, headers=auth(first)).json()
        assert client.get('/v1/me', headers=auth(agent)).json()['role'] == 'agent'
        assert client.get('/v1/owner/agents', headers=auth(agent)).status_code == 403
        assert client.get('/v1/owner/agents', headers=auth(second)).json()['items'] == []
        assert client.delete('/v1/owner/credentials/' + agent['credential_id'], headers=auth(second)).status_code == 404
        assert client.get('/v1/me', headers=auth(agent)).status_code == 200
        assert client.delete('/v1/owner/credentials/' + agent['credential_id'], headers=auth(first)).status_code == 200
        assert client.get('/v1/me', headers=auth(agent)).status_code == 401
    with TestClient(create_app(database=path)) as restarted:
        assert restarted.get('/v1/me', headers=auth(agent)).status_code == 401
        assert restarted.get('/v1/me', headers=auth(first)).status_code == 200
    with app.state.authority.store.transaction() as db:
        text = json.dumps([dict(row) for row in db.execute('SELECT * FROM activity')])
        stored = json.dumps([dict(row) for row in db.execute('SELECT * FROM credentials')])
        assert all(credential['token'] not in text + stored for credential in (first, second, agent))
        failed = db.execute('SELECT * FROM activity WHERE status_code=401').fetchall()
        assert failed and all(row['agent_id'] is None for row in failed)


def test_credential_expiry_and_rate_limits_configurable():
    now = [100.0]
    cfg = Settings.model_validate(load_settings().model_dump() | {'credential_ttl_seconds': 10, 'requests_per_window': 3})
    app = create_app(cfg, clock=lambda: now[0])
    owner = app.state.authority.create_owner('Owner')
    with TestClient(app) as client:
        assert client.get('/v1/me', headers=auth(owner)).status_code == 200
        now[0] = 111.0
        assert client.get('/v1/me', headers=auth(owner)).status_code == 401
        assert client.get('/health').status_code == 200
        assert client.get('/health').status_code == 429
        now[0] = 180.0
        assert client.get('/health').status_code == 200


def test_oversized_input_rejected_without_recording_body():
    cfg = Settings.model_validate(load_settings().model_dump() | {'max_body_bytes': 128})
    app = create_app(cfg)
    with TestClient(app) as client:
        response = client.post('/v1/owner/agents', content='PRIVATE-BODY' * 100)
        assert response.status_code == 413
        assert client.get('/v1/me?token=PRIVATE-QUERY').status_code == 401
    with app.state.authority.store.transaction() as db:
        events = json.dumps([dict(row) for row in db.execute('SELECT * FROM activity')])
        assert 'PRIVATE' not in events
