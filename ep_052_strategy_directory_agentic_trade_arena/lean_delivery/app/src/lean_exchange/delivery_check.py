# VERSION HISTORY v1.0.1 · 2026-09-02 · Treat wrong JSON shapes as failed checks rather than aborting a delivery report.
# v1.0.0 · 2026-09-02 · Provide a non-trading HTTP delivery check with explicit separation from full MVP acceptance.
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx


PUBLIC_PATHS = ('/health', '/v1/exchange', '/openapi.json', '/v1/rules/exchange_rules',
                '/v1/rules/agent_rules', '/v1/rules/example_trading_skill', '/arena', '/owner')
PRIVATE_PATHS = ('/v1/me', '/v1/me/positions', '/participant/v1/me/funds', '/v1/owner/agents',
                 '/v1/me/activity', '/v1/arena/activity')


def check(base_url, transport=None):
    parsed = urlsplit(base_url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('Use a plain loopback HTTP base URL; hosted verification is a separate acceptance step.')
    checks, discovery = [], {}
    with httpx.Client(base_url=base_url, timeout=15, follow_redirects=False, transport=transport) as client:
        for path in PUBLIC_PATHS + PRIVATE_PATHS:
            expected = 401 if path in PRIVATE_PATHS else 200
            row = {'path': path, 'expected_status': expected}
            try:
                response = client.get(path)
                row.update(status=response.status_code, passed=response.status_code == expected)
                if path == '/v1/exchange' and row['passed']:
                    discovery = response.json()
                    count = discovery.get('published_strategy_count')
                    if type(count) is not int or count < 0 or not isinstance(discovery.get('instance_id'), str):
                        row.update(passed=False, error='INVALID_DISCOVERY')
                        discovery = {}
                if path == '/openapi.json' and row['passed']:
                    routes = response.json()['paths']
                    row['passed'] = 'post' in routes.get('/v1/trades', {}) and 'get' in routes.get('/v1/me/positions', {})
                if path == '/v1/rules/agent_rules' and row['passed']:
                    row['passed'] = 'Recorded trading is available' in response.text and 'Trading remains pending' not in response.text
            except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
                if path == '/v1/exchange':
                    discovery = {}
                row.update(passed=False, error='REQUEST_OR_CONTRACT_FAILED')
            checks.append(row)
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'base_url': base_url,
            'http_checks_passed': all(row['passed'] for row in checks),
            'instance_id': discovery.get('instance_id'),
            'published_strategy_count': discovery.get('published_strategy_count'),
            'quote_inputs_present': bool(discovery.get('published_strategy_count', 0)),
            'full_mvp_acceptance': 'NOT_ASSESSED', 'checks': checks,
            'limitations': ['No credentials used: successful authenticated use and owner isolation are not proved.',
                           'No trades or paid queries submitted; GET requests may create activity logs.',
                           'Quotes, if present, are not verified as authoritative by this check.',
                           'Hermes behaviour, ten-agent operation, browser layout and recovery require separate evidence.']}


def main():
    parser = argparse.ArgumentParser(description='Check local EP052 API access without credentials, trades or paid queries.')
    parser.add_argument('--base-url', default='http://127.0.0.1:8054')
    parser.add_argument('--output', type=Path, help='Optional new sanitized JSON report; never overwrites a file.')
    args = parser.parse_args()
    result = check(args.base_url)
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(payload + '\n')
    print(payload)
    return 0 if result['http_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
