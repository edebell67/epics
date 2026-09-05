# VERSION HISTORY v1.0.0 · 2026-09-02 · Verify real HTTP owner/agent positions and historical attribution without creating trades.
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import httpx

from lean_exchange.config import APP_ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review-dir', required=True, type=Path)
    args = parser.parse_args()
    root = args.review_dir.resolve()
    epic = APP_ROOT.parents[1]
    if not root.is_relative_to((epic / 'evidence' / 'trading').resolve()):
        parser.error('Use an isolated trade-review directory')
    info = json.loads((root / 'review.json').read_text(encoding='utf-8'))
    original = json.loads((root / 'http-evidence.json').read_text(encoding='utf-8'))
    owner = json.loads((root / 'owner.secret.json').read_text(encoding='utf-8'))
    agent = json.loads((root / 'agent.secret.json').read_text(encoding='utf-8'))
    with httpx.Client(base_url=info['base_url'], timeout=30) as client:
        assert client.get('/v1/exchange').json()['instance_id'] == info['instance_id']
        client.headers['Authorization'] = 'Bearer ' + agent['token']
        current = client.get('/v1/me/positions')
        current.raise_for_status()
        current = current.json()
        assert Decimal(current['spendable_usd']) == Decimal('499.97')
        assert Decimal(current['holdings_value_usd']) == 675
        assert Decimal(current['total_value_usd']) == Decimal('1174.97')
        client.headers['Authorization'] = 'Bearer ' + owner['token']
        group = client.get('/v1/owner/positions', params={'agent_id': agent['agent_id']})
        group.raise_for_status()
        assert Decimal(group.json()['totals']['total_value_usd']) == Decimal('1174.97')
        path = '/v1/owner/agents/' + agent['agent_id'] + '/value-change'
        result = client.get(path, params={'from': current['allocation_created_at'], 'to': datetime.now(timezone.utc).isoformat()})
        result.raise_for_status()
        result = result.json()
        assert result['reconciled'] and Decimal(result['value_change_usd']) == Decimal('174.97')
        quote = current['positions'][0]['price']
        price_only = client.get(path, params={'from': original['buy']['executed_at'], 'to': quote['published_at']})
        price_only.raise_for_status()
        price_only = price_only.json()
        assert price_only['reconciled'] and Decimal(price_only['value_change_usd']) == 175
        assert Decimal(price_only['cash_change_usd']) == 0
        evidence = {'status': 'PASS', 'instance_id': info['instance_id'], 'valuation_kind': info['valuation_kind'],
                    'current': current, 'attribution': result, 'price_only': price_only, 'autonomous_agent': False}
        (epic / 'evidence' / 'positions' / 'live-output.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        print(json.dumps({'status': 'PASS', 'spendable_usd': current['spendable_usd'], 'holdings_value_usd': current['holdings_value_usd'],
                          'total_value_usd': current['total_value_usd'], 'value_change_usd': result['value_change_usd'],
                          'price_only_gain_usd': price_only['value_change_usd'], 'price_only_cash_change_usd': price_only['cash_change_usd']}))


if __name__ == '__main__':
    main()
