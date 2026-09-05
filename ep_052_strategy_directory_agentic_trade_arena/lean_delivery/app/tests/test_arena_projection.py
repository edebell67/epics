# VERSION HISTORY v1.0.0 · 2026-09-02 · Verify shared projections, privacy, exact cursor continuation, atomic rollback and migration recovery.
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from lean_exchange.records import Store
from test_trade_recording import fixture_app, price, request, agent, headers
from test_query_fees import setup_app, register


def test_trade_effects_public_but_private_funding_and_owner_data_absent(tmp_path):
    app, cfg = fixture_app(tmp_path / 'arena.sqlite')
    quote = price(app, cfg)
    with TestClient(app) as client:
        a, other = agent(app, client), agent(app, client)
        body = request(quote, units=5)
        trade = client.post('/v1/trades', json=body, headers=headers(a)).json()
        client.post('/v1/trades', json=body, headers=headers(a))
        rejected = request(quote, side='SELL', units=6)
        assert client.post('/v1/trades', json=rejected, headers=headers(a)).status_code == 409
        client.post('/v1/trades', json=rejected, headers=headers(a))
        result = client.get('/v1/arena/activity', headers=headers(other)).json()
        assert [item['operation'] for item in result['items']] == ['BUY','REJECTED']
        public = result['items'][0]
        assert public['resource_id'] == trade['trade_id']
        assert public['details']['available_units_before'] == 1000 and public['details']['available_units_after'] == 995
        serialized = json.dumps(result)
        for secret in (a['token'], a['owner_id'], trade['funding_reference'], 'spendable_usd', 'owned_units_after'):
            assert secret not in serialized
        assert client.get('/v1/trades/' + trade['trade_id'], headers=headers(other)).status_code == 404
        assert client.get('/v1/arena/activity').status_code == 401
        effects = client.get('/v1/arena/inventory-effects', headers=headers(other)).json()
        assert len(effects['items']) == 1 and effects['items'][0]['event_id'] == public['event_id']
        logs = client.get('/v1/me/activity', headers=headers(a)).json()['items']
        assert any(row['operation'] == 'POST /v1/trades' and row['request_id'] == body['request_id'] for row in logs)


def test_filters_cursor_resume_and_same_timestamp_boundary(tmp_path):
    app, cfg = fixture_app(tmp_path / 'cursor.sqlite')
    quote = price(app, cfg)
    with TestClient(app) as client:
        a = agent(app, client)
        for _ in range(3):
            assert client.post('/v1/trades', json=request(quote), headers=headers(a)).status_code == 200
        first = client.get('/v1/arena/activity?limit=1', headers=headers(a)).json()
        second = client.get('/v1/arena/activity', params={'after': first['next_cursor'], 'limit': 1}, headers=headers(a)).json()
        last = client.get('/v1/arena/activity', params={'after': second['next_cursor'], 'limit': 1}, headers=headers(a)).json()
        assert first['has_more'] and second['has_more'] and not last['has_more']
        assert len({page['items'][0]['event_id'] for page in (first, second, last)}) == 3
        assert client.get('/v1/arena/activity', params={'after': last['next_cursor']}, headers=headers(a)).json()['items'] == []
        at = datetime.fromisoformat(second['items'][0]['occurred_at']).astimezone(timezone(timedelta(hours=1))).isoformat()
        filtered = client.get('/v1/arena/activity', params={'agent_id': a['agent_id'], 'strategy_id': 'DNA_1', 'operation': 'BUY', 'from': at, 'to': at}, headers=headers(a)).json()
        assert [row['event_id'] for row in filtered['items']] == [second['items'][0]['event_id']]
        empty = client.get('/v1/arena/activity?operation=SELL', headers=headers(a)).json()
        assert empty['items'] == [] and empty['next_cursor'] == last['high_water_cursor']
        assert client.get('/v1/arena/activity?from=2026-01-01T00:00:00', headers=headers(a)).status_code == 422
        assert client.get('/v1/arena/activity?limit=100000', headers=headers(a)).status_code == 422


def test_query_reports_privacy_and_success_only_projection(tmp_path):
    app = setup_app(tmp_path / 'queries.sqlite', [])
    with TestClient(app) as client:
        a = register(client, app)
        body = {'request_id': str(uuid4()), 'kind': 'PRIVATE research note', 'limit': 1}
        assert client.post('/participant/v1/me/queries', json=body, headers=headers(a)).status_code == 200
        client.post('/participant/v1/me/queries', json=body, headers=headers(a))
        hold = {'request_id': str(uuid4()), 'action': 'HOLD', 'explanation': 'PRIVATE explanation'}
        assert client.post('/v1/me/decisions', json=hold, headers=headers(a)).status_code == 200
        client.post('/v1/me/decisions', json=hold, headers=headers(a))
        events = client.get('/v1/arena/activity', headers=headers(a)).json()
        assert [item['operation'] for item in events['items']] == ['QUERY','REPORT']
        assert events['items'][0]['details']['kind'] == 'custom'
        assert 'PRIVATE' not in json.dumps(events)
        matches = client.get('/v1/arena/activity?strategy_id=DNA_100001', headers=headers(a)).json()
        assert len(matches['items']) == 1 and matches['items'][0]['operation'] == 'QUERY'
    failing = setup_app(tmp_path / 'failure.sqlite', [], failure='http')
    with TestClient(failing) as client:
        a = register(client, failing)
        assert client.post('/participant/v1/me/queries', json=body, headers=headers(a)).status_code == 503
        assert client.get('/v1/arena/activity?operation=QUERY', headers=headers(a)).json()['items'] == []
        assert any(row['status_code'] == 503 and row['request_id'] == body['request_id'] for row in client.get('/v1/me/activity', headers=headers(a)).json()['items'])


def test_event_failure_rolls_back_settlement(tmp_path, monkeypatch):
    from lean_exchange import trades
    app, cfg = fixture_app(tmp_path / 'rollback.sqlite')
    quote = price(app, cfg)
    with TestClient(app, raise_server_exceptions=False) as client:
        a = agent(app, client)
        def fail(*args):
            raise RuntimeError('Injected event failure')
        monkeypatch.setattr(trades, 'trade_event', fail)
        assert client.post('/v1/trades', json=request(quote), headers=headers(a)).status_code == 500
        with app.state.authority.store.transaction() as db:
            for table in ('trade_records','trade_requests','participant_movements','arena_events'):
                assert db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0


def test_restart_and_backfill_do_not_duplicate_receipts_or_fees(tmp_path):
    path = tmp_path / 'migration.sqlite'
    app, cfg = fixture_app(path)
    quote = price(app, cfg)
    with TestClient(app) as client:
        a = agent(app, client)
        assert client.post('/v1/trades', json=request(quote), headers=headers(a)).status_code == 200
    with app.state.authority.store.transaction(immediate=True) as db:
        db.execute('DELETE FROM arena_events')
        db.execute("DELETE FROM metadata WHERE key='arena_backfill_v1'")
    migrated = Store(path)
    with migrated.transaction() as db:
        initial = [dict(row) for row in db.execute('SELECT * FROM arena_events')]
        assert len(initial) == 1
    restarted = Store(path)
    with restarted.transaction() as db:
        assert [dict(row) for row in db.execute('SELECT * FROM arena_events')] == initial
        assert db.execute('SELECT count(*) FROM participant_movements').fetchone()[0] == 1


def test_connection_transitions_once_and_no_owner_association(tmp_path):
    app, _ = fixture_app(tmp_path / 'presence.sqlite')
    with TestClient(app) as client:
        a = agent(app, client)
        body = {'request_id': str(uuid4()), 'purpose': 'strategy_trading'}
        connected = client.post('/v1/connections', json=body, headers=headers(a)).json()
        client.post('/v1/connections', json=body, headers=headers(a))
        for _ in range(2):
            assert client.delete('/v1/connections/' + connected['id'], headers=headers(a)).status_code == 200
        page = client.get('/v1/arena/activity', headers=headers(a)).json()
        assert [row['operation'] for row in page['items']] == ['CONNECT','DISCONNECT']
        assert a['owner_id'] not in json.dumps(page)
