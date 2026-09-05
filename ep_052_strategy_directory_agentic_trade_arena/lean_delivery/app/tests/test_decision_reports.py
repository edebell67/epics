# VERSION HISTORY v1.0.0 · 2026-09-02 · External HOLD is durable, fee-free and scoped; fabricated executions remain rejected.
from uuid import uuid4

from fastapi.testclient import TestClient

from lean_exchange.api import create_app


def test_hold_retries_are_durable_and_do_not_charge(tmp_path):
    path = tmp_path / 'decisions.sqlite'
    app = create_app(database=path)
    owner = app.state.authority.create_owner('Owner')
    owner_auth = {'Authorization': 'Bearer ' + owner['token']}
    with TestClient(app) as client:
        agent = client.post('/v1/owner/agents', json={'name': 'A1'}, headers=owner_auth).json()
        auth = {'Authorization': 'Bearer ' + agent['token']}
        body = {'request_id': str(uuid4()), 'action': 'HOLD', 'explanation': 'No suitable entry at the current quote.'}
        first = client.post('/v1/me/decisions', json=body, headers=auth)
        assert first.status_code == 200
        assert first.json()['fee_usd'] == '0' and not first.json()['executed_trade']
        assert client.post('/v1/me/decisions', json=body, headers=auth).json() == first.json()
        assert client.post('/v1/me/decisions', json=body | {'explanation': 'Changed'}, headers=auth).status_code == 409
        funds = client.get('/participant/v1/me/funds', headers=auth).json()
        assert funds['movements'] == []
        for action in ('BUY', 'SELL'):
            forged = {'request_id': str(uuid4()), 'action': action, 'trade_id': str(uuid4())}
            assert client.post('/v1/me/decisions', json=forged, headers=auth).status_code == 409
        assert len(client.get('/v1/me/decisions', headers=auth).json()['items']) == 1
        assert client.get('/v1/me/decisions', headers=owner_auth).status_code == 403
    with TestClient(create_app(database=path)) as restarted:
        assert restarted.get('/v1/me/decisions', headers=auth).json()['items'][0] == first.json()
