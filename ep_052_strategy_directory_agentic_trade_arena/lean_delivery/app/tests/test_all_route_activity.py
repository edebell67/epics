# VERSION HISTORY v1.0.1 · 2026-09-02 · Include nested FastAPI routers in the authoritative route inventory.
# v1.0.0 · 2026-09-02 · Exercise every registered application route and require attributable durable HTTP outcomes.
from datetime import datetime, timezone
import json
from uuid import uuid4

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from lean_exchange.contracts import ActivityRecord
from lean_exchange.providers import DirectoryProvider, DirectorySnapshot, StrategyRecord
from test_query_fees import setup_app
from test_trade_recording import price, request, headers


def test_every_application_route_records_authenticated_outcome(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc)
    source = DirectorySnapshot(items=[StrategyRecord(strategy_id='DNA_1',status='active',total_trades=1,total_net_return=0)],
                               source_version='test-only', retrieved_at=now, page_as_of=[now], total=1,
                               open_evidence_available=False, warnings=['TEST_FIXTURE'])
    monkeypatch.setattr(DirectoryProvider, 'fetch', lambda self: source)
    app = setup_app(tmp_path / 'routes.sqlite', [])
    owner = app.state.authority.create_owner('Route coverage owner')
    actor = None
    observed = set()
    with TestClient(app, follow_redirects=False) as client:
        def call(method, path, template=None, credential=None, expected=200, **kwargs):
            credential = credential or actor or owner
            template = template or path
            with app.state.authority.store.transaction() as db:
                before = db.execute('SELECT coalesce(max(cursor),0) FROM activity').fetchone()[0]
            response = client.request(method, path, headers=headers(credential), **kwargs)
            assert response.status_code == expected, (method, path, response.text)
            with app.state.authority.store.transaction() as db:
                rows = db.execute('SELECT * FROM activity WHERE cursor>? AND operation=?', (before, method+' '+template)).fetchall()
            assert len(rows) == 1, (method, template, len(rows))
            assert rows[0]['status_code'] == response.status_code
            assert rows[0]['owner_id'] == credential['owner_id']
            assert rows[0]['agent_id'] == credential['agent_id']
            if isinstance(kwargs.get('json'), dict) and 'request_id' in kwargs['json']:
                assert rows[0]['request_id'] == kwargs['json']['request_id']
            observed.add((method, template))
            return response.json() if 'application/json' in response.headers.get('content-type','') else None

        actor = call('POST','/v1/owner/agents',credential=owner,expected=201,json={'name':'Route audit client'})
        quote = price(app, app.state.authority.settings)
        for path in ('/v1/me','/health','/v1/exchange','/v1/providers/directory','/v1/contracts','/v1/contracts/intelligence',
                     '/owner','/arena','/v1/strategies','/v1/me/positions','/v1/me/trades','/v1/me/decisions','/v1/me/feedback',
                     '/participant/v1/me/funds','/v1/arena/activity','/v1/arena/inventory-effects','/v1/arena/connections'):
            call('GET',path)
        call('GET','/',expected=307)
        call('GET','/assets/arena.js','/assets/{name}')
        call('GET','/v1/rules/exchange_rules','/v1/rules/{name}')
        call('GET','/v1/strategies/DNA_1','/v1/strategies/{strategy_id}')
        call('GET','/v1/strategies/DNA_1/price','/v1/strategies/{strategy_id}/price')
        call('GET','/v1/owner/agents',credential=owner)
        call('GET','/v1/owner/positions',credential=owner)
        call('GET','/participant/v1/owner/agents/'+actor['agent_id']+'/funds','/participant/v1/owner/agents/{agent_id}/funds',credential=owner)
        at = datetime.now(timezone.utc).isoformat()
        call('GET','/v1/owner/agents/'+actor['agent_id']+'/value-change','/v1/owner/agents/{agent_id}/value-change',credential=owner,params={'from':at,'to':at})
        connection = call('POST','/v1/connections',json={'request_id':str(uuid4()),'purpose':'strategy_trading'})
        call('POST','/v1/connections/'+connection['id']+'/heartbeat','/v1/connections/{connection_id}/heartbeat')
        call('DELETE','/v1/connections/'+connection['id'],'/v1/connections/{connection_id}')
        trade_body = request(quote)
        call('POST','/v1/contracts/validate/trade',json=trade_body)
        trade = call('POST','/v1/trades',json=trade_body)
        call('GET','/v1/trades/'+trade['trade_id'],'/v1/trades/{trade_id}')
        query = {'request_id':str(uuid4()),'kind':'random','limit':1}
        call('POST','/v1/contracts/validate/query',json=query)
        receipt = call('POST','/participant/v1/me/queries',json=query)
        call('GET','/participant/v1/me/queries/'+receipt['delivery']['delivery_id'],'/participant/v1/me/queries/{delivery_id}')
        message = call('POST','/v1/owner/feedback',credential=owner,json={'request_id':str(uuid4()),'agent_ids':[actor['agent_id']],'message':'PRIVATE audit feedback'})
        call('GET','/v1/owner/feedback',credential=owner)
        call('GET','/v1/owner/feedback/'+message['id'],'/v1/owner/feedback/{feedback_id}',credential=owner)
        call('POST','/v1/me/feedback/'+message['id']+'/ack','/v1/me/feedback/{feedback_id}/ack')
        call('POST','/v1/me/feedback/'+message['id']+'/responses','/v1/me/feedback/{feedback_id}/responses',json={'request_id':str(uuid4()),'message':'PRIVATE audit reply'})
        call('POST','/v1/me/decisions',json={'request_id':str(uuid4()),'action':'HOLD','explanation':'PRIVATE audit explanation'})
        call('POST','/v1/trades',expected=422,content='invalid JSON PRIVATE audit body')
        records = call('GET','/v1/me/activity',credential=owner)
        for row in records['items']:
            ActivityRecord.model_validate(row)
        assert 'PRIVATE' not in json.dumps(records)
        call('DELETE','/v1/owner/credentials/'+actor['credential_id'],'/v1/owner/credentials/{credential_id}',credential=owner)
        assert client.get('/v1/me',headers=headers(actor)).status_code == 401
    def application_routes(routes):
        for route in routes:
            if isinstance(route, APIRoute):
                yield from ((method, route.path) for method in route.methods)
            elif hasattr(route, 'original_router'):
                yield from application_routes(route.original_router.routes)
    expected_routes = set(application_routes(app.routes))
    assert observed == expected_routes, {'missing': expected_routes-observed, 'unexpected': observed-expected_routes}
    with app.state.authority.store.transaction() as db:
        failed = db.execute('SELECT agent_id FROM activity WHERE status_code=401').fetchall()
        assert failed and all(row['agent_id'] is None for row in failed)
