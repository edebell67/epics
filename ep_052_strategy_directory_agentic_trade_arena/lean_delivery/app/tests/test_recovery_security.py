# VERSION HISTORY v1.0.0 · 2026-09-02 · Verify WAL-safe backup, isolated restore, cursor/receipt retention and non-overwriting/future-schema safeguards.
from decimal import Decimal
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from lean_exchange.recovery import backup, restore, manifest
from lean_exchange.records import Store
from test_trade_recording import fixture_app, price, request, agent, headers


def test_backup_restore_preserves_receipts_fees_and_cursors(tmp_path):
    source = tmp_path / 'source.sqlite'
    app, cfg = fixture_app(source)
    quote = price(app, cfg)
    with TestClient(app) as client:
        actor = agent(app, client)
        body = request(quote, units=5)
        receipt = client.post('/v1/trades', json=body, headers=headers(actor)).json()
        page = client.get('/v1/arena/activity', headers=headers(actor)).json()
        checkpoint = backup(source, tmp_path / 'backup.sqlite')
    restored = tmp_path / 'restored.sqlite'
    assert restore(tmp_path / 'backup.sqlite', restored) == checkpoint == manifest(restored)
    recovered, _ = fixture_app(restored)
    with TestClient(recovered) as client:
        assert client.post('/v1/trades', json=body, headers=headers(actor)).json() == receipt
        assert client.get('/v1/arena/activity', headers=headers(actor)).json()['items'] == page['items']
        assert client.get('/v1/arena/activity', params={'after': page['next_cursor']}, headers=headers(actor)).json()['items'] == []
        funds = client.get('/participant/v1/me/funds', headers=headers(actor)).json()
        assert len(funds['movements']) == 1 and Decimal(funds['spendable_usd']) == Decimal('994.24')
        connection = client.post('/v1/connections', json={'request_id': str(uuid4()), 'purpose': 'strategy_trading'}, headers=headers(actor))
        assert connection.status_code == 200
        resumed = client.get('/v1/arena/activity', params={'after': page['next_cursor']}, headers=headers(actor)).json()
        assert len(resumed['items']) == 1 and resumed['items'][0]['operation'] == 'CONNECT'


def test_wal_commits_included_and_uncommitted_changes_excluded(tmp_path):
    source = tmp_path / 'wal.sqlite'
    store = Store(source)
    writer = sqlite3.connect(source)
    try:
        writer.execute("INSERT INTO metadata VALUES ('committed','yes')")
        writer.commit()
        writer.execute("INSERT INTO metadata VALUES ('uncommitted','no')")
        backup(source, tmp_path / 'backup.sqlite')
        with sqlite3.connect(tmp_path / 'backup.sqlite') as db:
            assert db.execute("SELECT value FROM metadata WHERE key='committed'").fetchone()[0] == 'yes'
            assert db.execute("SELECT value FROM metadata WHERE key='uncommitted'").fetchone() is None
    finally:
        writer.rollback(); writer.close()


def test_restore_refuses_existing_destination_and_preserves_it(tmp_path):
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    Store(source); Store(target)
    before = manifest(target)
    with pytest.raises(FileExistsError):
        restore(source, target)
    assert manifest(target) == before
    with pytest.raises(ValueError, match='DISTINCT'):
        backup(source, source)


def test_future_schema_is_never_downgraded(tmp_path):
    source = tmp_path / 'future.sqlite'
    Store(source)
    with sqlite3.connect(source) as db:
        db.execute('PRAGMA user_version=99')
    with pytest.raises(ValueError, match='NEWER'):
        Store(source)
    with sqlite3.connect(source) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 99
    with pytest.raises(ValueError, match='UNSUPPORTED'):
        restore(source, tmp_path / 'should-not-exist.sqlite')
    assert not (tmp_path / 'should-not-exist.sqlite').exists()
