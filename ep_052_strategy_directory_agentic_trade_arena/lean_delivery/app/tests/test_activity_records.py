# VERSION HISTORY v1.0.0 · 2026-09-02 · Verify scoped safe activity, stable event IDs and monotonic cursor continuation.
from fastapi.testclient import TestClient
from lean_exchange.api import create_app


def test_activity_is_scoped_and_paginates_without_duplicates():
    app = create_app()
    a = app.state.authority.create_owner('A')
    b = app.state.authority.create_owner('B')
    ha, hb = {'Authorization': 'Bearer ' + a['token']}, {'Authorization': 'Bearer ' + b['token']}
    with TestClient(app) as client:
        for _ in range(3):
            client.get('/v1/me', headers=ha)
            client.get('/v1/me', headers=hb)
        first = client.get('/v1/me/activity?limit=2', headers=ha).json()
        second = client.get('/v1/me/activity?limit=2&after=' + str(first['next_cursor']), headers=ha).json()
        ids = [row['event_id'] for page in (first, second) for row in page['items']]
        assert len(ids) == len(set(ids)) == 4
        assert all(row['owner_id'] == a['owner_id'] for page in (first, second) for row in page['items'])
        assert second['next_cursor'] > first['next_cursor']
