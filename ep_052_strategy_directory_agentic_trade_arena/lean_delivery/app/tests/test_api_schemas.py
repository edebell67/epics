# VERSION HISTORY v1.0.1 · 2026-09-02 · Contract validator remains non-executing beside the newly implemented settlement route.
# v1.0.0 · 2026-09-02 · Validate strict visitor contracts without pretending to execute trades.
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from lean_exchange.api import create_app
from lean_exchange.contracts import TradeRequest, ConnectionRequest, DecisionReport, assert_same_request


def trade(**changes):
    return {'request_id': str(uuid4()), 'strategy_id': 'DNA_100001', 'side': 'BUY',
            'units': 1, 'expected_price_version': 'price-1'} | changes


@pytest.mark.parametrize('units', [0, -1, 1.5, True, '1'])
def test_invalid_units_cannot_validate(units):
    with TestClient(create_app()) as client:
        response = client.post('/v1/contracts/validate/trade', json=trade(units=units))
        assert response.status_code == 422


def test_trade_validation_is_accessible_and_never_executes():
    with TestClient(create_app()) as client:
        for side in ('BUY', 'SELL'):
            response = client.post('/v1/contracts/validate/trade', json=trade(side=side))
            assert response.status_code == 200
            assert response.json()['executed'] is False
        spec = client.get('/openapi.json').json()
        assert '/v1/contracts/validate/trade' in spec['paths']
        assert '/v1/trades' in spec['paths']
        assert spec['paths']['/v1/trades']['post']['security']
        models = client.get('/v1/contracts').json()['schemas']
        assert {'TradeRequest', 'ConnectionRequest', 'DecisionReport', 'TradeReceipt', 'ActivityRecord', 'FeedbackRequest'} <= models.keys()


def test_missing_identity_version_and_forged_owner_rejected():
    for key in ('request_id', 'expected_price_version'):
        payload = trade()
        del payload[key]
        with pytest.raises(ValidationError):
            TradeRequest.model_validate(payload)
    with pytest.raises(ValidationError):
        TradeRequest.model_validate(trade(owner_id=str(uuid4())))


def test_changed_retry_payload_conflicts():
    payload = trade()
    original = TradeRequest.model_validate(payload)
    assert_same_request(original, TradeRequest.model_validate(dict(reversed(list(payload.items())))))
    with pytest.raises(ValueError, match='REQUEST_ID_CONFLICT'):
        assert_same_request(original, TradeRequest.model_validate(payload | {'units': 2}))


def test_connections_and_reports_do_not_encode_agent_policy():
    connected = ConnectionRequest(request_id=uuid4(), purpose='strategy_trading')
    assert 'poll' not in str(connected.model_dump())
    DecisionReport(request_id=uuid4(), action='HOLD')
    with pytest.raises(ValidationError):
        DecisionReport(request_id=uuid4(), action='BUY')
    DecisionReport(request_id=uuid4(), action='SELL', trade_id=uuid4())
