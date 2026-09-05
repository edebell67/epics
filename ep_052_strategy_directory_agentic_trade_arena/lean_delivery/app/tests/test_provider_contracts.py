# VERSION HISTORY v1.0.0 · 2026-09-02 · Verify read-only pagination, source failures and reused Decimal valuation invariant.
from copy import deepcopy
from decimal import Decimal

from fastapi.testclient import TestClient
import httpx
from pydantic import ValidationError
import pytest

from lean_exchange.api import create_app
from lean_exchange.config import Settings, load_settings
from lean_exchange.providers import DirectoryProvider, ProviderError, ValuationInput, published_price


def cfg(**overrides):
    return Settings.model_validate(load_settings().model_dump() | overrides)


def page(number=1, total=2, sid=None):
    return {'data': {'page': number, 'total': total, 'items': [{
        'strategy_id': sid or f'DNA_{number}', 'status': 'active',
        'total_trades': 3, 'total_net_return': -2.5, 'product_name': 'gbp'}]},
        'as_of': '2026-09-02T14:00:00+00:00'}


def test_all_pages_preserve_source_and_missing_open_evidence():
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=page(int(request.url.params['page'])))
    provider = DirectoryProvider(cfg(directory_page_size=1), httpx.MockTransport(handle))
    first = provider.fetch()
    assert first.total == 2 and len(requests) == 2
    assert all(r.method == 'GET' for r in requests)
    assert [x.strategy_id for x in first.items] == ['DNA_1', 'DNA_2']
    assert first.items[0].open_trades is None
    assert first.items[0].total_net_return == Decimal('-2.5')
    assert first.items[0].model_extra['product_name'] == 'gbp'
    assert not first.open_evidence_available and not first.exchange_prices_available
    assert first.source_version == provider.fetch().source_version


@pytest.mark.parametrize('failure', ['duplicate', 'changed', 'empty', 'page_limit', 'malformed', 'unavailable', 'time'])
def test_provider_failures_do_not_return_partial_catalogue(failure):
    def handle(request):
        n = int(request.url.params['page'])
        data = page(n)
        if failure == 'unavailable':
            return httpx.Response(503, text='private upstream diagnostic')
        if failure == 'malformed':
            return httpx.Response(200, json={'private': 'not a directory'})
        if failure == 'duplicate':
            data['data']['items'][0]['strategy_id'] = 'DNA_1'
        if failure == 'changed' and n == 2:
            data['data']['total'] = 3
        if failure == 'empty':
            data['data']['items'] = []
        if failure == 'time':
            data['as_of'] = '2026-09-02T14:00:00'
        return httpx.Response(200, json=data)
    provider = DirectoryProvider(cfg(directory_page_size=1, directory_max_pages=1 if failure == 'page_limit' else 10),
                                 httpx.MockTransport(handle))
    with pytest.raises(ProviderError) as caught:
        provider.fetch()
    assert 'private' not in str(caught.value)


def test_http_source_inspection_and_safe_failure():
    provider = DirectoryProvider(cfg(), httpx.MockTransport(lambda _: httpx.Response(200, json=page(total=1))))
    with TestClient(create_app(directory=provider)) as client:
        response = client.get('/v1/providers/directory')
        assert response.status_code == 200
        assert response.json()['total'] == 1
        assert response.json()['exchange_prices_available'] is False
    failed = DirectoryProvider(cfg(), httpx.MockTransport(lambda _: httpx.Response(500, text='secret')))
    with TestClient(create_app(directory=failed)) as client:
        response = client.get('/v1/providers/directory')
        assert response.status_code == 503 and 'secret' not in response.text


VALUATION = {'strategy_id': 'DNA_100001', 'nav': '1150.00', 'units_outstanding': 1000,
             'currency': 'USD', 'source_version': 'valuation-1', 'valued_at': '2026-09-02T14:00:00Z'}


def test_reused_nav_division_is_decimal_and_preserves_provenance():
    value = ValuationInput.model_validate(VALUATION)
    quote = published_price(value, 10)
    assert quote['unit_price'] == '1.1500000000'
    assert quote['source_version'] == 'valuation-1' and quote['currency'] == 'USD'
    assert published_price(value, 2)['unit_price'] == '1.15'
    third = ValuationInput.model_validate(VALUATION | {'nav': '1', 'units_outstanding': 3})
    assert published_price(third, 10)['unit_price'] == '0.3333333333'


@pytest.mark.parametrize('changes', [{'currency': 'GBP'}, {'units_outstanding': 0}, {'units_outstanding': 1.5},
                                   {'units_outstanding': True}, {'nav': 'NaN'}, {'nav': '-1'},
                                   {'valued_at': '2026-09-02T14:00:00'}, {'strategy_id': 'not-dna'}])
def test_invalid_valuation_rejected(changes):
    with pytest.raises(ValidationError):
        ValuationInput.model_validate(VALUATION | changes)


@pytest.mark.parametrize('url', ['file:///private', 'http://user:secret@host/api', 'https://host/api?token=secret', 'missing'])
def test_bad_provider_configuration_rejected(url):
    with pytest.raises(ValidationError):
        cfg(directory_url=url)
