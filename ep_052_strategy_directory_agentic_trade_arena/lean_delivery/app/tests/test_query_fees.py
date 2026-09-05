# VERSION HISTORY v1.0.1 · 2026-09-02 · Exercise exact concurrent retries when only one fee remains available.
# v1.0.0 · 2026-09-02 · Participant gateway charges only durable delivered results; retries, race, failure and isolation coverage.
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient
import httpx
import pytest

from lean_exchange.api import create_app
from lean_exchange.config import Settings, load_settings
from lean_exchange.intelligence_client import IntelligenceClient


def headers(record):
    return {'Authorization': 'Bearer ' + record['token']}


def provider(cfg, calls, failure=None):
    def respond(request):
        import json
        body = json.loads(request.content)
        calls.append(body)
        if failure == 'http':
            return httpx.Response(503, text='PRIVATE upstream diagnostics')
        identity = request.headers['X-EP052-Agent-ID'] + body['request_id'] + str(body['revision'])
        payload = {'delivery_id': str(uuid5(NAMESPACE_URL, identity)), 'request_id': body['request_id'],
                   'revision': body['revision'], 'result_version': str(uuid5(NAMESPACE_URL, identity + 'result')),
                   'created_at': datetime.now(timezone.utc).isoformat(), 'source_version': 'source1',
                   'mode': 'simulated_random', 'strategy_ids': ['DNA_100001'], 'query': body, 'notice': 'Random list only'}
        if failure == 'mismatched':
            payload['request_id'] = str(uuid4())
        if failure == 'mode':
            payload['mode'] = 'external'
        if failure == 'duplicates':
            payload['strategy_ids'] *= 2
        return httpx.Response(200, json=payload)
    return IntelligenceClient(cfg, token='test-only', transport=httpx.MockTransport(respond))


def setup_app(path, calls, failure=None, **settings):
    cfg = Settings.model_validate(load_settings().model_dump() | settings)
    app = create_app(cfg, database=path, intelligence_provider=provider(cfg, calls, failure))
    return app


def register(client, app):
    owner = app.state.authority.create_owner('Test participant')
    return client.post('/v1/owner/agents', json={'name': 'Test client'}, headers=headers(owner)).json()


def test_success_exact_retry_refresh_receipt_and_restart(tmp_path):
    path, calls = tmp_path / 'query.sqlite', []
    app = setup_app(path, calls)
    query = {'request_id': str(uuid4()), 'kind': 'lowest_drawdown', 'limit': 2}
    with TestClient(app) as client:
        agent = register(client, app)
        auth = headers(agent)
        result = client.post('/participant/v1/me/queries', json=query, headers=auth)
        assert result.status_code == 200
        original = result.json()
        assert original['fee_usd'] == '0.01'
        assert client.get('/participant/v1/me/funds', headers=auth).json()['spendable_usd'] == '999.99'
        assert client.post('/participant/v1/me/queries', json=query, headers=auth).json() == original
        assert len(calls) == 1
        assert client.post('/participant/v1/me/queries', json=query | {'kind': 'changed'}, headers=auth).status_code == 409
        updated = client.post('/participant/v1/me/queries', json=query | {'revision': 1}, headers=auth).json()
        assert updated['delivery']['delivery_id'] != original['delivery']['delivery_id']
        assert client.get('/participant/v1/me/funds', headers=auth).json()['spendable_usd'] == '999.98'
        other = register(client, app)
        url = '/participant/v1/me/queries/' + original['delivery']['delivery_id']
        assert client.get(url, headers=headers(other)).status_code == 404
    app = setup_app(path, calls, failure='http', intelligence_fee='0.03')
    with TestClient(app) as client:
        assert client.post('/participant/v1/me/queries', json=query, headers=auth).json() == original
        assert client.get(url, headers=auth).json() == original
        assert client.get('/participant/v1/me/funds', headers=auth).json()['spendable_usd'] == '999.98'


@pytest.mark.parametrize('failure', ['http', 'mismatched', 'mode', 'duplicates'])
def test_provider_failure_never_charges_or_exposes_result(tmp_path, failure):
    app = setup_app(tmp_path / 'query.sqlite', [], failure=failure)
    with TestClient(app) as client:
        auth = headers(register(client, app))
        result = client.post('/participant/v1/me/queries', json={'request_id': str(uuid4()), 'kind': 'random'}, headers=auth)
        assert result.status_code == 503 and 'PRIVATE' not in result.text
        funds = client.get('/participant/v1/me/funds', headers=auth).json()
        assert Decimal(funds['spendable_usd']) == 1000 and funds['movements'] == []


def test_concurrent_final_cent_delivers_only_one_query(tmp_path):
    calls = []
    app = setup_app(tmp_path / 'query.sqlite', calls, seed_funds='0.01')
    with TestClient(app) as client:
        auth = headers(register(client, app))
        def submit(_):
            return client.post('/participant/v1/me/queries', json={'request_id': str(uuid4()), 'kind': 'random'}, headers=auth)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(submit, range(4)))
        assert sorted(r.status_code for r in results) == [200, 409, 409, 409]
        funds = client.get('/participant/v1/me/funds', headers=auth).json()
        assert Decimal(funds['spendable_usd']) == 0 and len(funds['movements']) == 1


def test_concurrent_exact_retry_one_fee(tmp_path):
    app = setup_app(tmp_path / 'query.sqlite', [], seed_funds='0.01')
    with TestClient(app) as client:
        auth = headers(register(client, app))
        body = {'request_id': str(uuid4()), 'kind': 'random'}
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: client.post('/participant/v1/me/queries', json=body, headers=auth), range(4)))
        assert all(r.status_code == 200 for r in results)
        assert len({r.json()['delivery']['delivery_id'] for r in results}) == 1
        assert Decimal(client.get('/participant/v1/me/funds', headers=auth).json()['spendable_usd']) == 0
