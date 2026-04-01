import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ['DATABASE_URL'] = 'sqlite:///./test.db'

from src.main import app
from src.models.database import Base, get_db

# Mock database setup for tests
SQLALCHEMY_DATABASE_URL = 'sqlite:///./test.db'
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_create_subscription():
    response = client.post(
        '/subscriptions/',
        json={'email': 'test@example.com', 'preferences': {'news': True}, 'source_tag': 'landing_page'}
    )
    assert response.status_code == 201
    data = response.json()
    assert data['email'] == 'test@example.com'
    assert data['status'] == 'pending'
    assert data['confirmed_at'] is None


def test_create_duplicate_subscription():
    client.post('/subscriptions/', json={'email': 'test@example.com'})
    response = client.post('/subscriptions/', json={'email': 'test@example.com'})
    assert response.status_code == 201
    data = response.json()
    assert data['email'] == 'test@example.com'
    assert data['status'] == 'pending'


def test_get_subscription_status():
    client.post('/subscriptions/', json={'email': 'test@example.com'})
    response = client.get('/subscriptions/test@example.com')
    assert response.status_code == 200
    assert response.json()['email'] == 'test@example.com'


def test_invalid_email():
    response = client.post('/subscriptions/', json={'email': 'not-an-email'})
    assert response.status_code == 422


def test_confirm_subscription():
    create_response = client.post(
        '/subscriptions/',
        json={'email': 'confirm@example.com', 'preferences': {'digest': 'weekly'}}
    )
    assert create_response.status_code == 201

    token = create_response.json()['confirmation_token']
    confirm_response = client.post('/subscriptions/confirm', json={'token': token})

    assert confirm_response.status_code == 200
    assert confirm_response.json()['email'] == 'confirm@example.com'

    status_response = client.get('/subscriptions/confirm@example.com')
    assert status_response.status_code == 200
    assert status_response.json()['status'] == 'confirmed'
    assert status_response.json()['confirmed_at'] is not None
