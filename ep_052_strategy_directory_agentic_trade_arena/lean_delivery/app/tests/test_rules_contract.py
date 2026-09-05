# VERSION HISTORY v1.1.0 · 2026-09-02 · Verify visiting-agent instructions acknowledge delivered APIs and keep missing-price prerequisites explicit.
# v1.0.2 · 2026-09-02 · Trading route now exists but requires agent authentication.
# v1.0.1 · 2026-09-02 · Preserve rules checks while allowing the implemented source-inspection capability.
# v1.0.0 · 2026-09-02 · Real HTTP rule delivery and configurable economics acceptance.
from decimal import Decimal
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from lean_exchange.api import create_app
from lean_exchange.config import load_settings, Settings


def test_rule_delivery_and_discovery():
    with TestClient(create_app()) as client:
        discovery = client.get('/v1/exchange').json()
        assert discovery['configuration']['minimum_units'] == 1
        assert discovery['configuration']['seed_funds'] == '1000.00'
        assert {'discovery', 'rules'} <= set(discovery['capabilities'])
        assert {'trade_recording', 'priced_inventory', 'positions', 'feedback_api'} <= set(discovery['capabilities'])
        for url in discovery['rules']:
            response = client.get(url)
            assert response.status_code == 200 and len(response.text) > 300
        assert client.get('/v1/rules/not_allowed').status_code == 404
        assert client.post('/v1/trades', json={}).status_code == 401
        assert '/v1/rules/{name}' in client.get('/openapi.json').json()['paths']


def test_agent_instructions_match_delivered_routes_and_readiness():
    with TestClient(create_app()) as client:
        text = client.get('/v1/rules/agent_rules').text
        assert 'Trading remains pending' not in text
        assert 'Recorded trading is available' in text
        assert 'requires an existing published quote' in text
        assert 'no bound valuation feed' in text
        assert 'a report does not execute a trade' in text
        assert 'never creates another fee' in text
        paths = client.get('/openapi.json').json()['paths']
        operations = [('post', '/v1/trades'), ('get', '/v1/trades/{trade_id}'),
                      ('get', '/v1/strategies'), ('get', '/v1/strategies/{strategy_id}/price'),
                      ('get', '/v1/me/positions'), ('post', '/v1/me/decisions'),
                      ('get', '/v1/me/feedback'), ('post', '/v1/me/feedback/{feedback_id}/ack'),
                      ('post', '/v1/me/feedback/{feedback_id}/responses')]
        for method, path in operations:
            assert f'{method.upper()} {path}' in text
            assert method in paths[path]


def test_numeric_configuration_changes_are_published():
    raw = load_settings().model_dump()
    raw.update(seed_funds=Decimal('2500'), trade_fee=Decimal('.03'),
               intelligence_fee=Decimal('.02'), maximum_positions=7, minimum_units=2)
    cfg = Settings.model_validate(raw)
    with TestClient(create_app(cfg)) as client:
        data = client.get('/v1/exchange').json()['configuration']
        assert data['seed_funds'] == '2500' and data['trade_fee'] == '0.03'
        assert data['intelligence_fee'] == '0.02' and data['maximum_positions'] == 7
        assert data['minimum_units'] == 2


@pytest.mark.parametrize('key,value', [('minimum_units', 1.5), ('minimum_units', True),
                                      ('trade_fee', '-1'), ('seed_funds', 'NaN'),
                                      ('maximum_positions', 0)])
def test_invalid_settings_rejected(key, value):
    with pytest.raises(ValidationError):
        Settings.model_validate(load_settings().model_dump() | {key: value})
