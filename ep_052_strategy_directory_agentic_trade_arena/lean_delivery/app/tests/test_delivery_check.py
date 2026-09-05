# VERSION HISTORY v1.0.1 · 2026-09-02 · Cover malformed discovery shape so broken services still produce explicit failed reports.
# v1.0.0 · 2026-09-02 · Test that public access checks never claim complete delivery or hide missing quotes/auth failures.
import httpx
import pytest

from lean_exchange.delivery_check import check, PRIVATE_PATHS


def transport(count=0, private_status=401, stale_rules=False):
    def handle(request):
        assert request.method == 'GET' and 'authorization' not in request.headers
        path = request.url.path
        if path in PRIVATE_PATHS:
            return httpx.Response(private_status)
        if path == '/v1/exchange':
            return httpx.Response(200, json={'instance_id': 'test-instance', 'published_strategy_count': count})
        if path == '/openapi.json':
            return httpx.Response(200, json={'paths': {'/v1/trades': {'post': {}}, '/v1/me/positions': {'get': {}}}})
        if path == '/v1/rules/agent_rules':
            return httpx.Response(200, text='Trading remains pending' if stale_rules else 'Recorded trading is available')
        return httpx.Response(200, text='OK')
    return httpx.MockTransport(handle)


def test_available_http_is_not_trading_readiness_or_mvp_acceptance():
    result = check('http://127.0.0.1:8054', transport())
    assert result['http_checks_passed'] and not result['quote_inputs_present']
    assert result['full_mvp_acceptance'] == 'NOT_ASSESSED'
    quoted = check('http://localhost:8056', transport(count=1))
    assert quoted['quote_inputs_present'] and quoted['full_mvp_acceptance'] == 'NOT_ASSESSED'


@pytest.mark.parametrize('provider', [transport(private_status=200), transport(stale_rules=True), transport(count=True)])
def test_unsafe_or_invalid_responses_fail(provider):
    assert not check('http://127.0.0.1:8054', provider)['http_checks_passed']


def test_connection_failure_returns_failed_observations():
    def unavailable(request):
        raise httpx.ConnectError('Unavailable')
    result = check('http://127.0.0.1:8054', httpx.MockTransport(unavailable))
    assert not result['http_checks_passed']
    assert all(row['error'] == 'REQUEST_OR_CONTRACT_FAILED' for row in result['checks'])


def test_wrong_json_shape_is_reported_as_failure():
    result = check('http://127.0.0.1:8054', httpx.MockTransport(lambda request: httpx.Response(200, json=[])))
    assert not result['http_checks_passed'] and result['instance_id'] is None


@pytest.mark.parametrize('url', ['https://example.com', 'http://user:secret@localhost:8054', 'http://localhost/private'])
def test_nonlocal_or_credential_urls_rejected(url):
    with pytest.raises(ValueError):
        check(url)
