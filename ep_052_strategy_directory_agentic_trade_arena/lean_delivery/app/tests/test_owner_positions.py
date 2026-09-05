# VERSION HISTORY v1.0.1 · 2026-09-02 · Verify repeated entries preserve distinct prices without inventing a sold-lot policy.
# v1.0.0 · 2026-09-02 · Reconcile owner/agent positions and historical value changes with receipts, fees and published-time provenance.
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from lean_exchange.participant_funds import move
from lean_exchange.pricing import publish
from lean_exchange.providers import ValuationInput
from test_trade_recording import fixture_app, price, request, headers, IDS


def register(app, client, owner=None):
    owner = owner or app.state.authority.create_owner('Position test participant')
    response = client.post('/v1/owner/agents', headers=headers(owner), json={'name': 'Position test client'})
    assert response.status_code == 201
    return owner, response.json()


def test_worked_case_and_price_only_change_reconcile(tmp_path):
    app, cfg = fixture_app(tmp_path / 'positions.sqlite')
    first = price(app, cfg)
    with TestClient(app) as client:
        owner, actor = register(app, client)
        start = datetime.now(timezone.utc)
        with app.state.authority.store.transaction(immediate=True) as db:
            move(db, actor['agent_id'], 'fixture-delivery', 'INTELLIGENCE', Decimal('-.01'))
        bought = client.post('/v1/trades', json=request(first, units=500), headers=headers(actor)).json()
        before_price = datetime.now(timezone.utc)
        updated = price(app, cfg, nav='1500')
        after_price = datetime.now(timezone.utc)
        only_price = client.get('/v1/owner/agents/' + actor['agent_id'] + '/value-change',
                               params={'from': before_price.isoformat(), 'to': after_price.isoformat()}, headers=headers(owner)).json()
        assert only_price['reconciled'] is True
        assert Decimal(only_price['value_change_usd']) == 175
        assert Decimal(only_price['cash_change_usd']) == 0
        assert only_price['strategies'][0]['trade_effects'] == []
        sold = client.post('/v1/trades', json=request(updated, side='SELL', units=50), headers=headers(actor)).json()
        end = datetime.now(timezone.utc)
        view = client.get('/v1/me/positions', headers=headers(actor)).json()
        assert Decimal(view['spendable_usd']) == Decimal('499.97')
        assert Decimal(view['holdings_value_usd']) == 675
        assert Decimal(view['total_value_usd']) == Decimal('1174.97')
        assert Decimal(view['gain_since_seed_usd']) == Decimal('174.97')
        assert view['positions'][0]['units'] == 450
        assert view['positions'][0]['entry_trades'][0]['trade_id'] == bought['trade_id']
        assert view['positions'][0]['price']['price_version'] == updated['price_version']
        change = client.get('/v1/owner/agents/' + actor['agent_id'] + '/value-change',
                            params={'from': start.isoformat(), 'to': end.isoformat()}, headers=headers(owner))
        assert change.status_code == 200
        result = change.json()
        assert result['reconciled'] is True and Decimal(result['reconciliation_difference_usd']) == 0
        assert Decimal(result['price_and_trade_gain_usd']) == 175
        assert Decimal(result['trade_fees_usd']) == Decimal('.02')
        assert Decimal(result['intelligence_fees_usd']) == Decimal('.01')
        assert result['query_charges'][0]['operation_id'] == 'fixture-delivery'
        assert [row['trade_id'] for row in result['strategies'][0]['trade_effects']] == [bought['trade_id'], sold['trade_id']]


def test_group_selection_dynamic_and_owner_isolation(tmp_path):
    app, _ = fixture_app(tmp_path / 'groups.sqlite')
    with TestClient(app) as client:
        owner, a = register(app, client)
        _, b = register(app, client, owner)
        other_owner, other = register(app, client)
        group = client.get('/v1/owner/positions', headers=headers(owner)).json()
        assert group['agent_count'] == 2 and Decimal(group['totals']['total_value_usd']) == 2000
        selected = client.get('/v1/owner/positions', params={'agent_id': [a['agent_id'], a['agent_id']]}, headers=headers(owner)).json()
        assert selected['agent_count'] == 1 and Decimal(selected['totals']['seed_usd']) == 1000
        assert client.get('/v1/owner/positions', params={'agent_id': [a['agent_id'], other['agent_id']]}, headers=headers(owner)).status_code == 404
        assert client.get('/v1/owner/positions', headers=headers(a)).status_code == 403
        assert client.get('/v1/me/positions', headers=headers(owner)).status_code == 403
        assert client.get('/v1/me/positions').status_code == 401
        at = datetime.now(timezone.utc).isoformat()
        assert client.get('/v1/owner/agents/' + a['agent_id'] + '/value-change', params={'from': at, 'to': at}, headers=headers(other_owner)).status_code == 404
        assert {item['agent_id'] for item in group['agents']} == {a['agent_id'], b['agent_id']}


def test_sold_out_positions_remain_visible_and_full_exit_has_only_cash(tmp_path):
    app, cfg = fixture_app(tmp_path / 'soldout.sqlite')
    first = price(app, cfg, nav='100', units=10)
    with TestClient(app) as client:
        owner, actor = register(app, client)
        body = request(first, units=10)
        assert client.post('/v1/trades', json=body, headers=headers(actor)).status_code == 200
        assert client.get('/v1/strategies', headers=headers(actor)).json()['items'] == []
        assert client.get('/v1/me/positions', headers=headers(actor)).json()['positions'][0]['units'] == 10
        assert client.post('/v1/trades', json=request(first, side='SELL', units=10), headers=headers(actor)).status_code == 200
        view = client.get('/v1/me/positions', headers=headers(actor)).json()
        assert view['positions'] == [] and Decimal(view['total_value_usd']) == Decimal('999.98')


def test_backdated_source_time_cannot_leak_future_publication(tmp_path):
    app, cfg = fixture_app(tmp_path / 'asof.sqlite')
    first = price(app, cfg)
    with TestClient(app) as client:
        owner, actor = register(app, client)
        assert client.post('/v1/trades', json=request(first, units=1), headers=headers(actor)).status_code == 200
        boundary = datetime.now(timezone.utc)
        updated = publish(app.state.authority.store, cfg, ValuationInput(strategy_id='DNA_1', nav='2000', units_outstanding=1000,
                          currency='USD', source_version='backdated-source', valued_at=datetime.fromisoformat(first['valued_at'])),
                          known_strategy_ids=IDS, provenance='TEST_FIXTURE_NOT_LIVE_VALUATION')
        result = client.get('/v1/owner/agents/' + actor['agent_id'] + '/value-change',
                            params={'from': boundary.isoformat(), 'to': datetime.now(timezone.utc).isoformat()}, headers=headers(owner)).json()
        line = result['strategies'][0]
        assert line['opening_price']['price_version'] == first['price_version']
        assert line['closing_price']['price_version'] == updated['price_version']
        assert result['reconciled'] is True


def test_missing_quote_is_unknown_not_zero_or_reconciled(tmp_path, monkeypatch):
    from lean_exchange import positions
    app, cfg = fixture_app(tmp_path / 'unknown.sqlite')
    first = price(app, cfg)
    with TestClient(app) as client:
        owner, actor = register(app, client)
        assert client.post('/v1/trades', json=request(first), headers=headers(actor)).status_code == 200
        monkeypatch.setattr(positions, 'quote_at', lambda *args: None)
        view = client.get('/v1/me/positions', headers=headers(actor)).json()
        assert view['valuation_complete'] is False and view['total_value_usd'] is None
        assert view['positions'][0]['marked_value_usd'] is None
        group = client.get('/v1/owner/positions', headers=headers(owner)).json()
        assert group['totals']['total_value_usd'] is None
        at = datetime.now(timezone.utc).isoformat()
        result = client.get('/v1/owner/agents/' + actor['agent_id'] + '/value-change',
                            params={'from': at, 'to': at}, headers=headers(owner)).json()
        assert result['reconciled'] is False and result['value_change_usd'] is None


def test_invalid_time_windows_rejected(tmp_path):
    app, _ = fixture_app(tmp_path / 'windows.sqlite')
    with TestClient(app) as client:
        owner, actor = register(app, client)
        now = datetime.now(timezone.utc)
        for start, end in [(now.replace(tzinfo=None), now), (now, now - timedelta(seconds=1)),
                           (now, now + timedelta(days=1)), (now - timedelta(days=1), now)]:
            assert client.get('/v1/owner/agents/' + actor['agent_id'] + '/value-change',
                              params={'from': start.isoformat(), 'to': end.isoformat()}, headers=headers(owner)).status_code == 422


def test_multiple_entry_prices_retain_both_receipts_without_lot_allocation(tmp_path):
    app, cfg = fixture_app(tmp_path / 'entries.sqlite')
    first = price(app, cfg)
    with TestClient(app) as client:
        owner, actor = register(app, client)
        start = datetime.now(timezone.utc)
        assert client.post('/v1/trades', json=request(first, units=10), headers=headers(actor)).status_code == 200
        second = price(app, cfg, nav='2000')
        assert client.post('/v1/trades', json=request(second, units=5), headers=headers(actor)).status_code == 200
        assert client.post('/v1/trades', json=request(second, side='SELL', units=8), headers=headers(actor)).status_code == 200
        view = client.get('/v1/me/positions', headers=headers(actor)).json()
        holding = view['positions'][0]
        assert holding['units'] == 7
        assert [Decimal(item['unit_price']) for item in holding['entry_trades']] == [Decimal('1.15'), Decimal('2')]
        assert Decimal(view['total_value_usd']) == Decimal('1008.47')
        result = client.get('/v1/owner/agents/' + actor['agent_id'] + '/value-change',
                            params={'from': start.isoformat(), 'to': datetime.now(timezone.utc).isoformat()}, headers=headers(owner)).json()
        assert result['reconciled'] and Decimal(result['value_change_usd']) == Decimal('8.47')
