# VERSION HISTORY v1.1.0 · 2026-09-02 · Assert restored3D canvas and audit switch use only existing allowlisted assets.
# v1.0.0 · 2026-09-02 · Validate Arena transport/read-only assets; actual browser behavior remains a separate evidence gate.
from fastapi.testclient import TestClient
from lean_exchange.api import create_app


def test_arena_assets_are_allowlisted_and_observer_is_read_only():
    with TestClient(create_app()) as client:
        response = client.get('/arena')
        assert response.status_code == 200
        assert "frame-ancestors 'none'" in response.headers['content-security-policy']
        assert 'Arena activity' in response.text
        assert 'arena-canvas' in response.text and 'Activity audit' in response.text
        assert 'engine.js' not in response.text and 'Deploy a demo' not in response.text
        script = client.get('/assets/arena.js')
        assert script.status_code == 200
        for forbidden in ('localStorage', 'sessionStorage', '.innerHTML', "method:'POST'", "method:'DELETE'"):
            assert forbidden not in script.text
        assert 'page.next_cursor' in script.text and 'config.instance_id' in script.text
        assert '/v1/arena/activity?' in script.text and '/v1/strategies' in script.text
        assert client.get('/assets/arena.css').status_code == 200
        assert client.get('/assets/owner.secret.json').status_code == 404
        assert client.get('/v1/exchange').json()['configuration']['view_poll_seconds'] == 5
