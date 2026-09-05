# VERSION HISTORY v1.1.0 · 2026-09-02 · Cover concurrent identical retries, complete exits and released position capacity.
# v1.0.0 · 2026-09-02 · Whole-unit trade acceptance with explicit fixture quotes; does not certify live valuation binding.
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx
import pytest

from lean_exchange.api import create_app
from lean_exchange.config import Settings, load_settings
from lean_exchange.contracts import TradeReceipt
from lean_exchange.participant_funds import move, balance
from lean_exchange.pricing import publish, PriceError, owned_units, available_units
from lean_exchange.providers import DirectoryProvider, ValuationInput

IDS = {f'DNA_{i}' for i in range(1, 13)}


def fixture_app(path, **overrides):
    cfg = Settings.model_validate(load_settings().model_dump() | overrides)
    provider = DirectoryProvider(cfg, httpx.MockTransport(lambda _: httpx.Response(200, json={
        'data': {'page': 1, 'total': len(IDS), 'items': [
            {'strategy_id': sid, 'status': 'active', 'total_trades': 1, 'total_net_return': 0} for sid in sorted(IDS)]},
        'as_of': datetime.now(timezone.utc).isoformat()})))
    app = create_app(cfg, database=path, directory=provider)
    return app, cfg


def price(app, cfg, sid='DNA_1', nav='1150', units=1000, version=None):
    value = ValuationInput(strategy_id=sid, nav=nav, units_outstanding=units, currency='USD',
                           source_version=version or str(uuid4()), valued_at=datetime.now(timezone.utc))
    return publish(app.state.authority.store, cfg, value, known_strategy_ids=IDS, provenance='TEST_FIXTURE_NOT_LIVE_VALUATION')


def agent(app, client):
    owner = app.state.authority.create_owner('Test participant')
    result = client.post('/v1/owner/agents', headers={'Authorization': 'Bearer ' + owner['token']}, json={'name': 'Trade test client'})
    assert result.status_code == 201
    return result.json()


def headers(actor):
    return {'Authorization': 'Bearer ' + actor['token']}


def request(quote, side='BUY', units=1, **changes):
    return {'request_id': str(uuid4()), 'strategy_id': quote['strategy_id'], 'side': side,
            'units': units, 'expected_price_version': quote['price_version']} | changes


def test_worked_buy_price_change_sell_and_exact_retry(tmp_path):
    path = tmp_path / 'trades.sqlite'
    app, cfg = fixture_app(path)
    first = price(app, cfg)
    with TestClient(app) as client:
        actor = agent(app, client)
        with app.state.authority.store.transaction(immediate=True) as db:
            move(db, actor['agent_id'], 'fixture-query', 'INTELLIGENCE', Decimal('-.01'))
        buy_request = request(first, units=500)
        bought = client.post('/v1/trades', json=buy_request, headers=headers(actor))
        assert bought.status_code == 200
        receipt = bought.json()
        TradeReceipt.model_validate(receipt)
        assert receipt['available_units_after'] == receipt['owned_units_after'] == 500
        assert client.get('/participant/v1/me/funds', headers=headers(actor)).json()['spendable_usd'] == '424.9800000000'
        updated = price(app, cfg, nav='1500')
        stale = client.post('/v1/trades', json=request(first), headers=headers(actor))
        assert stale.status_code == 409 and stale.json()['code'] == 'PRICE_CHANGED'
        sold = client.post('/v1/trades', json=request(updated, side='SELL', units=50), headers=headers(actor))
        assert sold.status_code == 200
        assert sold.json()['available_units_after'] == 550 and sold.json()['owned_units_after'] == 450
        assert Decimal(client.get('/participant/v1/me/funds', headers=headers(actor)).json()['spendable_usd']) == Decimal('499.97')
        assert client.post('/v1/trades', json=buy_request, headers=headers(actor)).json() == receipt
        assert client.post('/v1/trades', json=buy_request | {'units': 2}, headers=headers(actor)).status_code == 409
        assert client.get('/v1/trades/' + receipt['trade_id'], headers=headers(actor)).json() == receipt
        other = agent(app, client)
        assert client.get('/v1/trades/' + receipt['trade_id'], headers=headers(other)).status_code == 404
        reported = {'request_id': str(uuid4()), 'action': 'BUY', 'trade_id': receipt['trade_id'], 'explanation': 'Reported after receipt.'}
        assert client.post('/v1/me/decisions', json=reported, headers=headers(actor)).status_code == 200
        assert client.post('/v1/me/decisions', json=reported, headers=headers(other)).status_code == 409
        assert client.post('/v1/me/decisions', json=reported | {'action': 'SELL'}, headers=headers(actor)).status_code == 409
    restarted, _ = fixture_app(path)
    with TestClient(restarted) as client:
        assert client.post('/v1/trades', json=buy_request, headers=headers(actor)).json() == receipt
        assert len(client.get('/v1/me/trades', headers=headers(actor)).json()['items']) == 2


def test_final_unit_race_sold_out_discovery_and_no_duplicate_fee(tmp_path):
    app, cfg = fixture_app(tmp_path / 'race.sqlite')
    quote = price(app, cfg, nav='1.15', units=1)
    with TestClient(app) as client:
        actors = [agent(app, client) for _ in range(4)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda a: client.post('/v1/trades', json=request(quote), headers=headers(a)), actors))
        assert sorted(r.status_code for r in results) == [200, 409, 409, 409]
        available = client.get('/v1/strategies', headers=headers(actors[0])).json()['items']
        assert all(x['strategy_id'] != 'DNA_1' for x in available)
        detail = client.get('/v1/strategies/DNA_1', headers=headers(actors[0])).json()
        assert detail['available_units'] == 0 and detail['price']['unit_price'] == '1.1500000000'
    with app.state.authority.store.transaction() as db:
        assert available_units(db, 'DNA_1') + sum(owned_units(db, a['agent_id'], 'DNA_1') for a in actors) == 1
        assert db.execute('SELECT count(*) FROM participant_movements').fetchone()[0] == 1


def test_position_limit_and_adding_to_existing_position(tmp_path):
    app, cfg = fixture_app(tmp_path / 'positions.sqlite')
    quotes = [price(app, cfg, sid=sid, nav='100') for sid in sorted(IDS)]
    with TestClient(app) as client:
        actor = agent(app, client)
        for quote in quotes[:10]:
            assert client.post('/v1/trades', json=request(quote), headers=headers(actor)).status_code == 200
        blocked = client.post('/v1/trades', json=request(quotes[10]), headers=headers(actor))
        assert blocked.status_code == 409 and blocked.json()['code'] == 'PARTICIPANT_POSITION_LIMIT'
        assert client.post('/v1/trades', json=request(quotes[0]), headers=headers(actor)).status_code == 200


def test_rejections_durable_no_fees_and_no_overselling(tmp_path):
    app, cfg = fixture_app(tmp_path / 'rejections.sqlite', seed_funds='1')
    quote = price(app, cfg)
    with TestClient(app) as client:
        actor = agent(app, client)
        denied = request(quote)
        result = client.post('/v1/trades', json=denied, headers=headers(actor))
        assert result.status_code == 409 and result.json()['code'] == 'PARTICIPANT_FUNDS_INSUFFICIENT'
        assert client.post('/v1/trades', json=denied, headers=headers(actor)).json() == result.json()
        sell = client.post('/v1/trades', json=request(quote, side='SELL'), headers=headers(actor))
        assert sell.status_code == 409 and sell.json()['code'] == 'INSUFFICIENT_OWNED_UNITS'
        for units in (0, -1, 1.5, True, 2**63):
            assert client.post('/v1/trades', json=request(quote, units=units), headers=headers(actor)).status_code == 422
        assert client.get('/participant/v1/me/funds', headers=headers(actor)).json()['movements'] == []


def test_injected_failure_rolls_back_funds_trade_receipt_and_activity(tmp_path, monkeypatch):
    from lean_exchange import trades
    app, cfg = fixture_app(tmp_path / 'rollback.sqlite')
    quote = price(app, cfg)
    with TestClient(app, raise_server_exceptions=False) as client:
        actor = agent(app, client)
        body = request(quote)
        original = trades.record_trade
        def fail(*args):
            raise RuntimeError('Injected failure after funding movement')
        monkeypatch.setattr(trades, 'record_trade', fail)
        assert client.post('/v1/trades', json=body, headers=headers(actor)).status_code == 500
        with app.state.authority.store.transaction() as db:
            assert balance(db, actor['agent_id']) == 1000
            assert db.execute('SELECT count(*) FROM trade_records').fetchone()[0] == 0
            assert db.execute('SELECT count(*) FROM trade_requests').fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM activity WHERE operation LIKE 'TRADE %'").fetchone()[0] == 0
        monkeypatch.setattr(trades, 'record_trade', original)
        assert client.post('/v1/trades', json=body, headers=headers(actor)).status_code == 200


def test_unbound_inventory_never_invents_prices(tmp_path):
    app, _ = fixture_app(tmp_path / 'unbound.sqlite')
    with TestClient(app) as client:
        actor = agent(app, client)
        assert client.get('/v1/strategies', headers=headers(actor)).json()['items'] == []
        all_items = client.get('/v1/strategies?availability=all', headers=headers(actor)).json()['items']
        assert len(all_items) == len(IDS) and all(x['available_units'] is None and x['price'] is None for x in all_items)
        assert client.get('/v1/strategies/DNA_1/price', headers=headers(actor)).status_code == 404


def test_publisher_preserves_issued_units_and_refuses_unknown_ids(tmp_path):
    app, cfg = fixture_app(tmp_path / 'publication.sqlite')
    price(app, cfg)
    with pytest.raises(PriceError, match='BASELINE_CHANGED'):
        price(app, cfg, units=999)
    with pytest.raises(PriceError, match='NOT_IN_DIRECTORY'):
        price(app, cfg, sid='DNA_9999999')


def test_concurrent_exact_retry_settles_once(tmp_path):
    app, cfg = fixture_app(tmp_path / 'exact-retry.sqlite')
    quote = price(app, cfg)
    with TestClient(app) as client:
        actor = agent(app, client)
        body = request(quote, units=100)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: client.post('/v1/trades', json=body, headers=headers(actor)), range(4)))
        assert all(r.status_code == 200 for r in results)
        assert all(r.json() == results[0].json() for r in results)
        TradeReceipt.model_validate(results[0].json())
        with app.state.authority.store.transaction() as db:
            assert db.execute('SELECT count(*) FROM trade_records').fetchone()[0] == 1
            assert db.execute('SELECT count(*) FROM participant_movements').fetchone()[0] == 1
            assert db.execute("SELECT count(*) FROM activity WHERE operation='TRADE BUY'").fetchone()[0] == 1
            assert balance(db, actor['agent_id']) == Decimal('884.99')
            assert available_units(db, 'DNA_1') == 900


def test_full_exit_releases_position_slot_and_keeps_entry_receipt(tmp_path):
    app, cfg = fixture_app(tmp_path / 'exit.sqlite', maximum_positions=1)
    first, second = price(app, cfg), price(app, cfg, sid='DNA_2')
    with TestClient(app) as client:
        actor = agent(app, client)
        bought = client.post('/v1/trades', json=request(first, units=5), headers=headers(actor)).json()
        assert client.post('/v1/trades', json=request(second), headers=headers(actor)).status_code == 409
        sold = client.post('/v1/trades', json=request(first, side='SELL', units=5), headers=headers(actor))
        assert sold.status_code == 200
        assert sold.json()['owned_units_after'] == 0 and sold.json()['available_units_after'] == 1000
        assert client.post('/v1/trades', json=request(second), headers=headers(actor)).status_code == 200
        assert client.get('/v1/trades/' + bought['trade_id'], headers=headers(actor)).json() == bought
