# VERSION HISTORY v1.1.0 · 2026-09-02 · Contract now advertises the implemented charging gateway, separately tested.
# v1.0.0 · 2026-09-02 · Verify public query/delivery schemas and explicit retry/fee semantics.
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from lean_exchange.api import create_app
from lean_exchange.contracts import QueryRequest, assert_same_request


def test_intelligence_contract_is_inspectable_and_explicitly_simulated():
    with TestClient(create_app()) as client:
        response = client.get('/v1/contracts/intelligence')
        assert response.status_code == 200
        data = response.json()
        assert data['mode'] == 'simulated_random'
        assert data['fee_usd'] == '0.01'
        assert data['charging_implemented']
        assert data['visitor_query_url'] == '/participant/v1/me/queries'
        assert 'without another fee' in data['exact_retry']
        assert 'new fee' in data['refresh']
        assert 'no intelligence fee' in data['provider_failure']


def test_query_validation_does_not_deliver_or_charge():
    with TestClient(create_app()) as client:
        request = {'request_id': str(uuid4()), 'kind': 'lowest_drawdown', 'limit': 3}
        result = client.post('/v1/contracts/validate/query', json=request)
        assert result.status_code == 200
        assert result.json()['charged'] is False and result.json()['delivered'] is False
        assert client.post('/v1/contracts/validate/query', json=request | {'limit': 21}).status_code == 422


def test_receipt_identity_has_explicit_refresh_revision():
    request = QueryRequest(request_id=uuid4(), kind='recent_winners')
    assert_same_request(request, request.model_copy())
    with pytest.raises(ValueError, match='REQUEST_ID_CONFLICT'):
        assert_same_request(request, request.model_copy(update={'revision': 1}))


@pytest.mark.parametrize('changes', [{'limit': 0}, {'limit': 1.5}, {'revision': True}, {'revision': -1},
                                   {'window_start': '2026-09-02T13:00:00'},
                                   {'window_start': '2026-09-02T14:00:00Z', 'window_end': '2026-09-02T13:00:00Z'}])
def test_invalid_queries_rejected(changes):
    with pytest.raises(ValidationError):
        QueryRequest.model_validate({'request_id': str(uuid4()), 'kind': 'random'} | changes)
