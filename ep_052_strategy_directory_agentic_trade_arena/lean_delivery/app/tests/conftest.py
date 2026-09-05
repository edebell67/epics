# VERSION HISTORY v1.0.0 · 2026-09-02 · Isolate every API test from live local exchange records.
import pytest


@pytest.fixture(autouse=True)
def isolated_exchange_database(tmp_path, monkeypatch):
    monkeypatch.setenv('EP052_DATABASE', str(tmp_path / 'exchange.sqlite'))
