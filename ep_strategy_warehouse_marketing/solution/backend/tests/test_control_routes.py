import os
from datetime import datetime

os.environ["DATABASE_URL"] = "sqlite:///./test_controls.db"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.ContentQueue import ContentQueue, QueueStatus
from src.models.database import Base, get_db
from src.routes import controlRoutes


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_controls.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(controlRoutes.router)
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_control_routes_expose_status_and_logs():
    with TestingSessionLocal() as db:
        queue_item = ContentQueue(
            platform="twitter",
            status=QueueStatus.APPROVAL_PENDING,
            content_data={"content_type": "signal_alert"},
            scheduled_for=datetime(2026, 3, 21, 10, 0, 0),
        )
        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)
        queue_id = queue_item.id

    pause_response = client.post(
        "/controls/pause/global",
        json={"actor": "ops@example.com", "paused": True, "reason": "maintenance"},
    )
    assert pause_response.status_code == 200
    assert pause_response.json()["is_paused"] is True

    approve_response = client.post(
        f"/controls/queue/{queue_id}/approve",
        json={"actor": "reviewer@example.com", "reason": "ship it"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "paused"

    status_response = client.get("/controls/status")
    assert status_response.status_code == 200
    assert status_response.json()["pending_approvals"] == []
    assert status_response.json()["global_control"]["is_paused"] is True

    log_response = client.get("/controls/interventions")
    assert log_response.status_code == 200
    actions = [entry["action"] for entry in log_response.json()]
    assert "global_pause_set" in actions
    assert "queue_item_approved" in actions
