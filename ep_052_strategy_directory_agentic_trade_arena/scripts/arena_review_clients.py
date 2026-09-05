# VERSION HISTORY v1.0.0 · 2026-09-02 · Bounded external HTTP presence clients for one/ten-agent UI tests, not autonomous agents or product execution.
import argparse
import json
from pathlib import Path
from uuid import uuid4

import httpx

from lean_exchange.auth import Authority
from lean_exchange.config import APP_ROOT, load_settings
from lean_exchange.records import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review-dir', type=Path, required=True)
    parser.add_argument('--count', type=int, choices=(0, 1, 10), required=True)
    args = parser.parse_args()
    root = args.review_dir.resolve()
    if not root.is_relative_to((APP_ROOT.parents[1] / 'evidence' / 'trading').resolve()):
        parser.error('Use the isolated trade review directory')
    info = json.loads((root / 'review.json').read_text(encoding='utf-8'))
    secret = root / 'arena-ui-clients.secret.json'
    with httpx.Client(base_url=info['base_url'], timeout=30) as client:
        assert client.get('/v1/exchange').json()['instance_id'] == info['instance_id']
        if secret.exists():
            state = json.loads(secret.read_text(encoding='utf-8'))
        else:
            if args.count == 0:
                print('No review clients to disconnect'); return
            owner = Authority(Store(root / 'exchange.sqlite'), load_settings()).create_owner('Arena presence test owner')
            state = {'owner': owner, 'clients': []}
            secret.write_text(json.dumps(state), encoding='utf-8')
        # Save after each mutation so interrupted acceptance work remains recoverable.
        while len(state['clients']) < 10 and args.count:
            response = client.post('/v1/owner/agents', headers={'Authorization': 'Bearer ' + state['owner']['token']},
                                   json={'name': 'External HTTP presence client ' + str(len(state['clients']) + 1)})
            response.raise_for_status()
            state['clients'].append(response.json())
            secret.write_text(json.dumps(state), encoding='utf-8')
        for index, actor in enumerate(state['clients']):
            client.headers['Authorization'] = 'Bearer ' + actor['token']
            if index < args.count:
                if actor.get('connection_id'):
                    response = client.post('/v1/connections/' + actor['connection_id'] + '/heartbeat')
                else:
                    response = client.post('/v1/connections', json={'request_id': str(uuid4()), 'purpose': 'strategy_trading'})
                response.raise_for_status()
                actor['connection_id'] = response.json()['id']
            elif actor.get('connection_id'):
                client.delete('/v1/connections/' + actor['connection_id']).raise_for_status()
                actor.pop('connection_id')
            secret.write_text(json.dumps(state), encoding='utf-8')
        print(json.dumps({'status': 'PASS', 'connected_review_clients': args.count, 'autonomous_agents': False, 'trades_created': 0}))


if __name__ == '__main__':
    main()
