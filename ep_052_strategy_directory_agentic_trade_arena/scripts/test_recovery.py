# VERSION HISTORY v1.0.0 · 2026-09-02 · Back up the live review, restore privately and verify receipts/cursors/revocation without changing live trading state.
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx

from lean_exchange.api import create_app
from lean_exchange.config import APP_ROOT
from lean_exchange.recovery import backup, restore, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review-dir', required=True, type=Path)
    args = parser.parse_args()
    root = args.review_dir.resolve()
    epic = APP_ROOT.parents[1]
    if not root.is_relative_to((epic / 'evidence' / 'trading').resolve()):
        parser.error('Use an isolated trade review')
    info = json.loads((root / 'review.json').read_text(encoding='utf-8'))
    actor = json.loads((root / 'agent.secret.json').read_text(encoding='utf-8'))
    owner = json.loads((root / 'owner.secret.json').read_text(encoding='utf-8'))
    receipts = json.loads((root / 'http-evidence.json').read_text(encoding='utf-8'))
    auth = {'Authorization': 'Bearer ' + actor['token']}
    with httpx.Client(base_url=info['base_url'], headers=auth, timeout=30) as live:
        assert live.get('/v1/exchange').json()['instance_id'] == info['instance_id']
        before = live.get('/v1/arena/activity').json()
        run = epic / 'evidence' / 'recovery' / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '_' + uuid4().hex[:8])
        run.mkdir(parents=True)
        saved, recovered = run / 'backup.private.sqlite', run / 'restored.private.sqlite'
        checkpoint = backup(root / 'exchange.sqlite', saved)
        assert restore(saved, recovered) == checkpoint == manifest(recovered)
        with TestClient(create_app(database=recovered)) as client:
            for side in ('buy','sell'):
                original = receipts[side]
                assert client.get('/v1/trades/' + original['trade_id'], headers=auth).json() == original
                body = {key: original[key] for key in ('request_id','strategy_id','side','units')}
                body['expected_price_version'] = original['price_version']
                response = client.post('/v1/trades', json=body, headers=auth)
                assert response.status_code == 200 and response.json() == original
            page = client.get('/v1/arena/activity', headers=auth).json()
            assert page['items'] == before['items'] and page['next_cursor'] == before['next_cursor']
            assert client.get('/v1/arena/activity', params={'after': page['next_cursor']}, headers=auth).json()['items'] == []
            funds = client.get('/participant/v1/me/funds', headers=auth).json()
            assert funds['spendable_usd'] == receipts['spendable_usd'] and len(funds['movements']) == receipts['movement_count']
            assert client.delete('/v1/owner/credentials/' + actor['credential_id'], headers={'Authorization': 'Bearer ' + owner['token']}).status_code == 200
        with TestClient(create_app(database=recovered)) as restarted:
            assert restarted.get('/v1/me', headers=auth).status_code == 401
        assert live.get('/v1/me').status_code == 200, 'Isolated revocation must not affect live review'
        report = {'status': 'PASS', 'instance_id': info['instance_id'], 'backup_integrity': checkpoint['integrity'],
                  'exact_restore': True, 'tables_verified': len(checkpoint['tables']),
                  'receipts_and_cursor_preserved': True, 'duplicate_fees': False,
                  'restored_revocation_survived_restart': True, 'live_credential_unchanged': True,
                  'autonomous_agent': False, 'privacy': 'Do not publish the private SQLite files in this run directory.'}
        (run / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2)); print('Report:', run / 'report.json')


if __name__ == '__main__':
    main()
