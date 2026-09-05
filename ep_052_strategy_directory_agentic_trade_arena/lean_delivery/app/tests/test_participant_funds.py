# VERSION HISTORY v1.0.0 · 2026-09-02 · Seed-once, scoped funding, atomic Decimal debits/credits and no public top-up.
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from lean_exchange.api import create_app
from lean_exchange.config import Settings, load_settings
from lean_exchange.participant_funds import FundingError, balance, move


def headers(record):
    return {'Authorization': 'Bearer ' + record['token']}


def test_seed_configurable_persistent_and_owner_scoped(tmp_path):
    path = tmp_path / 'funds.sqlite'
    cfg = Settings.model_validate(load_settings().model_dump() | {'seed_funds': '1250.50'})
    app = create_app(cfg, database=path)
    owner = app.state.authority.create_owner('A')
    other = app.state.authority.create_owner('B')
    with TestClient(app) as client:
        agent = client.post('/v1/owner/agents', json={'name': 'A1'}, headers=headers(owner)).json()
        value = client.get('/participant/v1/me/funds', headers=headers(agent)).json()
        assert value['seed_usd'] == value['spendable_usd'] == '1250.50'
        assert value['boundary'] == 'participant' and not value['unrealised_gains_spendable']
        url = '/participant/v1/owner/agents/' + agent['agent_id'] + '/funds'
        assert client.get(url, headers=headers(other)).status_code == 404
        assert client.get(url, headers=headers(owner)).status_code == 200
        assert client.get('/participant/v1/me/funds', headers=headers(owner)).status_code == 403
        assert client.post('/participant/v1/me/funds', json={'amount': 100000}, headers=headers(agent)).status_code == 405
    with TestClient(create_app(database=path)) as client:
        assert client.get('/participant/v1/me/funds', headers=headers(agent)).json()['seed_usd'] == '1250.50'


def test_internal_funding_references_no_overspend_or_duplicate_effect(tmp_path):
    app = create_app(database=tmp_path / 'funds.sqlite')
    owner = app.state.authority.create_owner('A')
    with TestClient(app) as client:
        agent = client.post('/v1/owner/agents', json={'name': 'A1'}, headers=headers(owner)).json()['agent_id']
    store = app.state.authority.store
    with store.transaction(immediate=True) as db:
        receipt = move(db, agent, 'trade:buy-1', 'BUY', Decimal('-575.01'))
        assert move(db, agent, 'trade:buy-1', 'BUY', Decimal('-575.01')) == receipt
        assert balance(db, agent) == Decimal('424.99')
        with pytest.raises(FundingError, match='CONFLICT'):
            move(db, agent, 'trade:buy-1', 'BUY', Decimal('-1'))
        with pytest.raises(FundingError, match='INSUFFICIENT'):
            move(db, agent, 'trade:excess', 'BUY', Decimal('-500'))
        move(db, agent, 'trade:sell-1', 'SELL', Decimal('74.99'))
        assert balance(db, agent) == Decimal('499.98')
    with pytest.raises(RuntimeError):
        with store.transaction(immediate=True) as db:
            move(db, agent, 'trade:rolled-back', 'BUY', Decimal('-1'))
            raise RuntimeError('Injected failure before operation commit')
    with store.transaction() as db:
        assert balance(db, agent) == Decimal('499.98')
        assert db.execute('SELECT count(*) FROM participant_movements WHERE agent_id=?', (agent,)).fetchone()[0] == 2
