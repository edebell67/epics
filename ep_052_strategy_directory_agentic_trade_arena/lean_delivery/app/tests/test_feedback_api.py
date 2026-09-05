# VERSION HISTORY v1.0.1 · 2026-09-02 · Verify latest-first and older-page cursor semantics used by the actual workspace.
# v1.0.0 · 2026-09-02 · Private owner/group feedback and agent acknowledgements/replies with durable retries.
from uuid import uuid4

from fastapi.testclient import TestClient

from lean_exchange.api import create_app
from lean_exchange.config import Settings, load_settings


def headers(record):
    return {'Authorization': 'Bearer ' + record['token']}


def agent(client, owner, name):
    response = client.post('/v1/owner/agents', json={'name': name}, headers=headers(owner))
    assert response.status_code == 201
    return response.json()


def test_owner_feedback_group_ack_reply_and_restart(tmp_path):
    path = tmp_path / 'feedback.sqlite'
    app = create_app(database=path)
    owner = app.state.authority.create_owner('Owner')
    outsider = app.state.authority.create_owner('Other owner')
    with TestClient(app) as client:
        first, second = agent(client, owner, 'A1'), agent(client, owner, 'A2')
        foreign = agent(client, outsider, 'B1')
        body = {'request_id': str(uuid4()), 'agent_ids': [first['agent_id'], second['agent_id']], 'message': 'Consider waiting for an updated quote.'}
        sent = client.post('/v1/owner/feedback', json=body, headers=headers(owner))
        assert sent.status_code == 200
        feedback_id = sent.json()['id']
        assert client.post('/v1/owner/feedback', json=body, headers=headers(owner)).json()['id'] == feedback_id
        assert client.post('/v1/owner/feedback', json=body | {'message': 'Changed'}, headers=headers(owner)).status_code == 409
        assert client.get('/v1/owner/feedback', headers=headers(outsider)).json()['items'] == []
        assert client.get('/v1/owner/feedback/' + feedback_id, headers=headers(outsider)).status_code == 404
        assert client.get('/v1/me/feedback', headers=headers(foreign)).json()['items'] == []
        assert client.post('/v1/me/feedback/' + feedback_id + '/ack', headers=headers(foreign)).status_code == 404
        inbox = client.get('/v1/me/feedback', headers=headers(first)).json()['items'][0]
        assert len(inbox['recipients']) == 1 and inbox['recipients'][0]['agent_id'] == first['agent_id']
        acknowledgement = client.post('/v1/me/feedback/' + feedback_id + '/ack', headers=headers(first)).json()
        assert client.post('/v1/me/feedback/' + feedback_id + '/ack', headers=headers(first)).json() == acknowledgement
        reply = {'request_id': str(uuid4()), 'message': 'Received. I am choosing HOLD for now.'}
        response = client.post('/v1/me/feedback/' + feedback_id + '/responses', json=reply, headers=headers(first))
        assert response.status_code == 200
        assert client.post('/v1/me/feedback/' + feedback_id + '/responses', json=reply, headers=headers(first)).json() == response.json()
        assert client.post('/v1/me/feedback/' + feedback_id + '/responses', json=reply | {'message': 'Changed'}, headers=headers(first)).status_code == 409
        sibling_view = client.get('/v1/me/feedback', headers=headers(second)).json()['items'][0]
        assert sibling_view['replies'] == []
        detail = client.get('/v1/owner/feedback/' + feedback_id, headers=headers(owner)).json()
        assert len(detail['replies']) == 1
        assert sum(x['acknowledged_at'] is not None for x in detail['recipients']) == 1
        assert client.get('/v1/owner/feedback', headers=headers(first)).status_code == 403
    with TestClient(create_app(database=path)) as restarted:
        assert restarted.get('/v1/owner/feedback/' + feedback_id, headers=headers(owner)).json() == detail


def test_invalid_group_is_atomic_and_pagination_is_scoped():
    app = create_app()
    owner, outsider = app.state.authority.create_owner('A'), app.state.authority.create_owner('B')
    with TestClient(app) as client:
        own, foreign = agent(client, owner, 'A1'), agent(client, outsider, 'B1')
        body = {'request_id': str(uuid4()), 'agent_ids': [own['agent_id'], foreign['agent_id']], 'message': 'Private'}
        assert client.post('/v1/owner/feedback', json=body, headers=headers(owner)).status_code == 404
        assert client.get('/v1/me/feedback', headers=headers(own)).json()['items'] == []
        assert client.post('/v1/owner/feedback', json=body | {'agent_ids': [own['agent_id']] * 2}, headers=headers(owner)).status_code == 422
        result = client.post('/v1/owner/feedback', json=body | {'agent_ids': [own['agent_id']]}, headers=headers(owner)).json()
        assert client.get('/v1/me/feedback?after=' + str(result['cursor']), headers=headers(own)).json()['items'] == []


def test_owner_latest_and_older_pagination():
    app = create_app(Settings.model_validate(load_settings().model_dump() | {'activity_page_size': 2}))
    owner = app.state.authority.create_owner('Owner')
    with TestClient(app) as client:
        own = agent(client, owner, 'A')
        for number in range(3):
            client.post('/v1/owner/feedback', headers=headers(owner), json={
                'request_id': str(uuid4()), 'agent_ids': [own['agent_id']], 'message': str(number)})
        latest = client.get('/v1/owner/feedback?latest=true', headers=headers(owner)).json()
        assert [x['message'] for x in latest['items']] == ['2', '1']
        older = client.get('/v1/owner/feedback?before=' + str(latest['next_cursor']), headers=headers(owner)).json()
        assert [x['message'] for x in older['items']] == ['0']
