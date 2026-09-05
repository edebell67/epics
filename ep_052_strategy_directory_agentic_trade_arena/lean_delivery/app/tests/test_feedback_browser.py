# VERSION HISTORY v1.0.0 · 2026-09-02 · Static transport/safety tests supplement, not replace, actual browser feedback acceptance.
from fastapi.testclient import TestClient
from lean_exchange.api import create_app


def test_owner_workspace_assets_and_security_headers():
    with TestClient(create_app()) as client:
        html = client.get('/owner')
        assert html.status_code == 200
        assert "frame-ancestors 'none'" in html.headers['content-security-policy']
        script = client.get('/assets/owner.js')
        assert script.status_code == 200
        assert 'localStorage' not in script.text and '.innerHTML' not in script.text
        assert '/v1/owner/feedback?latest=true' in script.text
        assert client.get('/assets/intelligence.key').status_code == 404
        assert 'feedback_view' in client.get('/v1/exchange').json()['capabilities']
