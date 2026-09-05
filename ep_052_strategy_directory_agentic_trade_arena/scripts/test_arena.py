# VERSION HISTORY v1.0.0 · 2026-09-02 · Real HTTP Arena cursor/presence verification against retained review receipts without new trading.
import argparse
import json
from pathlib import Path
from uuid import uuid4

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
    receipts = json.loads((root / 'http-evidence.json').read_text(encoding='utf-8'))
    actor = json.loads((root / 'agent.secret.json').read_text(encoding='utf-8'))
    with httpx.Client(base_url=info['base_url'], timeout=30, headers={'Authorization': 'Bearer ' + actor['token']}) as client:
        assert client.get('/v1/exchange').json()['instance_id'] == info['instance_id']
        connected = client.post('/v1/connections', json={'request_id': str(uuid4()), 'purpose': 'strategy_trading'})
        connected.raise_for_status()
        connection_id = connected.json()['id']
        try:
            presence = client.get('/v1/arena/connections')
            presence.raise_for_status()
            assert any(item['id'] == connection_id for item in presence.json()['items'])
        finally:
            client.delete('/v1/connections/' + connection_id).raise_for_status()
        cursor, pages, items = 0, 0, []
        while True:
            response = client.get('/v1/arena/activity', params={'after': cursor, 'limit': 2})
            response.raise_for_status()
            page = response.json()
            items.extend(page['items']); pages += 1; cursor = page['next_cursor']
            if not page['has_more']:
                break
        assert len({item['event_id'] for item in items}) == len(items)
        for side in ('buy', 'sell'):
            matches = [item for item in items if item['resource_id'] == receipts[side]['trade_id'] and item['operation'] == side.upper()]
            assert len(matches) == 1
            assert matches[0]['details']['available_units_after'] == receipts[side]['available_units_after']
        assert any(item['operation'] == 'QUERY' for item in items)
        assert any(item['operation'] == 'REPORT' for item in items)
        assert any(item['operation'] == 'REJECTED' for item in items)
        assert client.get('/v1/arena/activity', params={'after': cursor}).json()['items'] == []
        serialized = json.dumps(items)
        for secret in (actor['token'], actor['owner_id'], 'spendable_usd', 'funding_reference', 'Position-view acceptance'):
            assert secret not in serialized
        result = {'status': 'PASS', 'instance_id': info['instance_id'], 'valuation_kind': info['valuation_kind'],
                  'pages': pages, 'next_cursor': cursor, 'events': items, 'presence_checked': True, 'autonomous_agent': False}
        (epic / 'evidence' / 'arena' / 'live-output.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'status': 'PASS', 'pages': pages, 'events': len(items), 'presence_checked': True,
                          'duplicate_events': False, 'private_data_exposed': False, 'new_trades': 0}))


if __name__ == '__main__':
    main()
