# VERSION HISTORY v1.1.0 · 2026-09-02 · Provide repeatable non-trading receipt/funds inspection after restart for user review.
# v1.0.1 · 2026-09-02 · Refuse reused acceptance state before mutations so repeat reviews cannot corrupt evidence.
# v1.0.0 · 2026-09-02 · Isolated real-HTTP trade acceptance using explicitly labelled fixture valuations and actual directory IDs.
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx

from lean_exchange.api import create_app
from lean_exchange.auth import Authority
from lean_exchange.config import APP_ROOT, load_settings
from lean_exchange.contracts import TradeReceipt
from lean_exchange.pricing import publish
from lean_exchange.providers import DirectoryProvider, ValuationInput
from lean_exchange.records import Store


def quote(store, cfg, strategy_id, nav, version):
    return publish(store, cfg, ValuationInput(strategy_id=strategy_id, nav=nav, units_outstanding=1000,
                    currency='USD', source_version=version, valued_at=datetime.now(timezone.utc)),
                   known_strategy_ids={strategy_id}, provenance='ISOLATED_ACCEPTANCE_FIXTURE_NOT_LIVE_VALUATION')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'run', 'test', 'inspect'])
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8056)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    allowed = APP_ROOT.parents[1] / 'evidence' / 'trading'
    if not root.is_relative_to(allowed.resolve()) or root == allowed.resolve():
        parser.error('Review directory must be a dedicated child of epic/evidence/trading')
    if not 1024 <= args.port <= 65535 or args.port in (8053, 8054, 8055):
        parser.error('Choose a distinct local review port')
    cfg = load_settings()
    database = root / 'exchange.sqlite'
    os.environ['EP052_DATABASE'] = str(database)
    if args.mode == 'prepare':
        if root.exists():
            parser.error('Use a new isolated review directory; existing state is never overwritten')
        source = DirectoryProvider(cfg).fetch()
        active = [item.strategy_id for item in source.items if item.status == 'active']
        if not active:
            raise RuntimeError('No actual directory strategies available for isolated review')
        root.mkdir(parents=True)
        store = Store(database)
        primary = quote(store, cfg, active[0], '1150', 'acceptance-entry')
        owner = Authority(store, cfg).create_owner('Isolated trade acceptance owner')
        with (root / 'owner.secret.json').open('x', encoding='utf-8') as output:
            json.dump(owner, output)
        with store.transaction() as db:
            instance_id = db.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()['value']
        info = {'instance_id': instance_id, 'strategy_id': active[0], 'source_version': source.source_version,
                'price': primary, 'base_url': f'http://127.0.0.1:{args.port}', 'valuation_kind': 'isolated_acceptance_fixture'}
        (root / 'review.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
        print('Prepared isolated trade review:', root)
    elif args.mode == 'run':
        if not (root / 'review.json').exists():
            raise RuntimeError('Prepare the isolated directory first')
        token_path = APP_ROOT / 'runtime' / 'intelligence.key'
        os.environ['EP052_INTELLIGENCE_TOKEN'] = token_path.read_text(encoding='utf-8').strip()
        import uvicorn
        uvicorn.run(create_app(cfg, database=database), host='127.0.0.1', port=args.port)
    elif args.mode == 'inspect':
        evidence = json.loads((root / 'http-evidence.json').read_text(encoding='utf-8'))
        actor = json.loads((root / 'agent.secret.json').read_text(encoding='utf-8'))
        with httpx.Client(base_url=f'http://127.0.0.1:{args.port}', timeout=30,
                          headers={'Authorization': 'Bearer ' + actor['token']}) as client:
            discovery = client.get('/v1/exchange')
            discovery.raise_for_status()
            assert discovery.json()['instance_id'] == evidence['instance_id'], 'Wrong server instance'
            for side in ('buy', 'sell'):
                response = client.get('/v1/trades/' + evidence[side]['trade_id'])
                response.raise_for_status()
                assert response.json() == evidence[side], 'Persisted receipt differs from captured settlement'
                TradeReceipt.model_validate(response.json())
            funds = client.get('/participant/v1/me/funds')
            funds.raise_for_status()
            assert funds.json()['spendable_usd'] == evidence['spendable_usd'], 'Funds changed after acceptance'
            assert len(funds.json()['movements']) == evidence['movement_count']
            spec = client.get('/openapi.json').json()
            assert spec['paths']['/v1/trades']['post']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/TradeReceipt')
        result = {'status': 'PASS', 'inspection': 'persisted receipts, published schema and unchanged funds',
                  'instance_id': evidence['instance_id'], 'valuation_kind': evidence['valuation_kind'],
                  'spendable_usd': evidence['spendable_usd'], 'movement_count': evidence['movement_count'],
                  'inspected_at': datetime.now(timezone.utc).isoformat(), 'autonomous_agent': False}
        (root / 'inspect-evidence.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))
    else:
        if (root / 'agent.secret.json').exists() or (root / 'http-evidence.json').exists():
            parser.error('This acceptance run has already started. Inspect its evidence; use a fresh review directory/port for another run.')
        info = json.loads((root / 'review.json').read_text(encoding='utf-8'))
        owner = json.loads((root / 'owner.secret.json').read_text(encoding='utf-8'))
        base = f'http://127.0.0.1:{args.port}'
        with httpx.Client(base_url=base, timeout=30) as client:
            assert client.get('/v1/exchange').json()['instance_id'] == info['instance_id'], 'Wrong server instance'
            client.headers['Authorization'] = 'Bearer ' + owner['token']
            registration = client.post('/v1/owner/agents', json={'name': 'Isolated HTTP trade-review client'})
            registration.raise_for_status()
            actor = registration.json()
            (root / 'agent.secret.json').write_text(json.dumps(actor), encoding='utf-8')
            client.headers['Authorization'] = 'Bearer ' + actor['token']
            connection = client.post('/v1/connections', json={'request_id': str(uuid4()), 'purpose': 'strategy_trading'})
            connection.raise_for_status()
            query = client.post('/participant/v1/me/queries', json={'request_id': str(uuid4()), 'kind': 'random', 'limit': 1})
            query.raise_for_status()
            entry = client.get('/v1/strategies/' + info['strategy_id'] + '/price').json()
            buy_body = {'request_id': str(uuid4()), 'strategy_id': info['strategy_id'], 'side': 'BUY', 'units': 500,
                        'expected_price_version': entry['price_version']}
            bought = client.post('/v1/trades', json=buy_body)
            bought.raise_for_status()
            updated = quote(Store(database), cfg, info['strategy_id'], '1500', 'acceptance-exit-' + str(uuid4()))
            sold = client.post('/v1/trades', json={'request_id': str(uuid4()), 'strategy_id': info['strategy_id'],
                                'side': 'SELL', 'units': 50, 'expected_price_version': updated['price_version']})
            sold.raise_for_status()
            assert client.post('/v1/trades', json=buy_body).json() == bought.json(), 'Retry changed original receipt'
            invalid = client.post('/v1/trades', json={'request_id': str(uuid4()), 'strategy_id': info['strategy_id'],
                                   'side': 'SELL', 'units': 451, 'expected_price_version': updated['price_version']})
            assert invalid.status_code == 409 and invalid.json()['code'] == 'INSUFFICIENT_OWNED_UNITS'
            funds = client.get('/participant/v1/me/funds').json()
            expected = cfg.seed_funds - cfg.intelligence_fee - 500 * Decimal(entry['unit_price']) - 2 * cfg.trade_fee + 50 * Decimal(updated['unit_price'])
            assert Decimal(funds['spendable_usd']) == expected
            assert sold.json()['owned_units_after'] == 450 and sold.json()['available_units_after'] == 550
            report = client.post('/v1/me/decisions', json={'request_id': str(uuid4()), 'action': 'SELL', 'trade_id': sold.json()['trade_id']})
            report.raise_for_status()
            client.delete('/v1/connections/' + connection.json()['id']).raise_for_status()
            evidence = {'status': 'PASS', 'base_url': base, 'instance_id': info['instance_id'],
                        'valuation_kind': info['valuation_kind'], 'strategy_id': info['strategy_id'],
                        'buy': bought.json(), 'sell': sold.json(), 'spendable_usd': funds['spendable_usd'],
                        'movement_count': len(funds['movements']), 'oversell': invalid.json(), 'autonomous_agent': False}
            (root / 'http-evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
            print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
