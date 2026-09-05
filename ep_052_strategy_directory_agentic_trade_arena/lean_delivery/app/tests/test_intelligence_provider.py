# VERSION HISTORY v1.0.0 · 2026-09-02 · Durable separate-provider retries, random list provenance, isolation and failure tests.
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx

from lean_exchange.config import load_settings
from lean_exchange.providers import DirectoryProvider
from lean_exchange.simulated_intelligence import create_app

TOKEN = 'test-only-provider-token-not-a-production-secret'


def headers(actor=None):
    return {'Authorization': 'Bearer ' + TOKEN, 'X-EP052-Agent-ID': str(actor or uuid4())}


def source(status=200):
    return DirectoryProvider(load_settings(), httpx.MockTransport(lambda _: httpx.Response(status, json={
        'data': {'page': 1, 'total': 4, 'items': [
            {'strategy_id': f'DNA_{i}', 'status': 'active', 'total_trades': 1, 'total_net_return': 0} for i in range(4)]},
        'as_of': '2026-09-02T14:00:00Z'})))


def test_random_list_receipt_recovery_refresh_and_restart(tmp_path):
    database = tmp_path / 'receipts.sqlite'
    auth = headers()
    request = {'request_id': str(uuid4()), 'kind': 'lowest_drawdown', 'limit': 2}
    with TestClient(create_app(database=database, token=TOKEN, directory=source())) as client:
        first = client.post('/v1/queries', json=request, headers=auth)
        assert first.status_code == 200
        result = first.json()
        assert result['mode'] == 'simulated_random' and len(set(result['strategy_ids'])) == 2
        assert set(result['strategy_ids']) <= {'DNA_0', 'DNA_1', 'DNA_2', 'DNA_3'}
        assert client.post('/v1/queries', json=request, headers=auth).json() == result
        assert client.post('/v1/queries', json=request | {'limit': 1}, headers=auth).status_code == 409
        refreshed = client.post('/v1/queries', json=request | {'revision': 1}, headers=auth).json()
        assert refreshed['delivery_id'] != result['delivery_id'] and refreshed['result_version'] != result['result_version']
        assert client.get('/v1/deliveries/' + result['delivery_id'], headers=headers()).status_code == 404
    # Restart and unavailable directory must not prevent recovery of an already-issued receipt.
    with TestClient(create_app(database=database, token=TOKEN, directory=source(503))) as client:
        assert client.post('/v1/queries', json=request, headers=auth).json() == result
        assert client.get('/v1/deliveries/' + result['delivery_id'], headers=auth).json() == result


def test_no_identity_no_access_and_provider_failure_has_no_receipt(tmp_path):
    database = tmp_path / 'receipts.sqlite'
    with TestClient(create_app(database=database, token=TOKEN, directory=source(503))) as client:
        request = {'request_id': str(uuid4()), 'kind': 'recent_winners'}
        assert client.post('/v1/queries', json=request).status_code == 401
        assert client.post('/v1/queries', json=request, headers={'Authorization': 'Bearer ' + TOKEN}).status_code == 422
        response = client.post('/v1/queries', json=request, headers=headers())
        assert response.status_code == 503 and 'delivery_id' not in response.json()
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(database)) as db:
        assert db.execute('SELECT count(*) FROM deliveries').fetchone()[0] == 0


def test_concurrent_exact_retry_has_one_delivery(tmp_path):
    with TestClient(create_app(database=tmp_path / 'receipts.sqlite', token=TOKEN, directory=source())) as client:
        request = {'request_id': str(uuid4()), 'kind': 'random', 'limit': 2}
        auth = headers()
        with ThreadPoolExecutor(max_workers=4) as executor:
            responses = list(executor.map(lambda _: client.post('/v1/queries', json=request, headers=auth), range(8)))
        assert all(r.status_code == 200 for r in responses)
        assert len({r.json()['delivery_id'] for r in responses}) == 1
