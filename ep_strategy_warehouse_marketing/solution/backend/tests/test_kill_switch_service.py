import os
import sys
from datetime import timedelta
from unittest.mock import MagicMock

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.ContentQueue import ContentQueue, QueueStatus
from src.models.database import Base
from src.services.autonomousSchedulerService import AutonomousSchedulerService
from src.services.contentQueueService import get_now
from src.services.killSwitchService import KillSwitchService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_queue_item(db_session, platform: str, status: QueueStatus = QueueStatus.PENDING) -> ContentQueue:
    item = ContentQueue(
        platform=platform,
        status=status,
        content_data={"content_type": "signal_alert", "body": "Test"},
        scheduled_for=get_now() - timedelta(minutes=5),
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_global_pause_stops_new_dispatches_immediately():
    scheduler = AutonomousSchedulerService.__new__(AutonomousSchedulerService)
    scheduler.config = {"jobs": {"queue_processing": {"enabled": True, "interval_seconds": 60}}}
    scheduler.last_run = {"queue_processing": get_now() - timedelta(minutes=5)}
    scheduler.logger = MagicMock()
    scheduler.posting_rules = MagicMock()
    scheduler.posting_rules.config = {"platforms": {"twitter": {}, "linkedin": {}}}
    scheduler.queue_service = MagicMock()
    scheduler.kill_switch_service = MagicMock()
    scheduler.kill_switch_service.is_dispatch_allowed.return_value = (False, "global_pause")
    scheduler._publish_item = MagicMock()

    scheduler._check_queue_processing(get_now())

    scheduler.queue_service.get_next_to_publish.assert_not_called()
    scheduler._publish_item.assert_not_called()


def test_platform_pause_leaves_other_platforms_operational():
    scheduler = AutonomousSchedulerService.__new__(AutonomousSchedulerService)
    scheduler.config = {"jobs": {"queue_processing": {"enabled": True, "interval_seconds": 60}}}
    scheduler.last_run = {"queue_processing": get_now() - timedelta(minutes=5)}
    scheduler.logger = MagicMock()
    scheduler.posting_rules = MagicMock()
    scheduler.posting_rules.config = {"platforms": {"twitter": {}, "linkedin": {}}}
    scheduler.queue_service = MagicMock()
    scheduler.kill_switch_service = MagicMock()
    scheduler.kill_switch_service.is_dispatch_allowed.side_effect = [
        (False, "platform_pause:twitter"),
        (True, None),
    ]

    linkedin_item = MagicMock()
    linkedin_item.id = 42
    scheduler.queue_service.get_next_to_publish.side_effect = [linkedin_item]
    scheduler._publish_item = MagicMock()

    scheduler._check_queue_processing(get_now())

    scheduler.queue_service.get_next_to_publish.assert_called_once_with("linkedin")
    scheduler._publish_item.assert_called_once_with(linkedin_item)


def test_emergency_stop_can_freeze_or_clear_pending_items(db_session):
    service = KillSwitchService(db_session)
    pending_item = _create_queue_item(db_session, "twitter", QueueStatus.PENDING)
    approval_item = _create_queue_item(db_session, "linkedin", QueueStatus.APPROVAL_PENDING)

    freeze_result = service.trigger_emergency_stop(actor="ops@example.com", mode="freeze", reason="incident")
    db_session.refresh(pending_item)
    db_session.refresh(approval_item)

    assert freeze_result["mode"] == "freeze"
    assert freeze_result["affected_items"] == 2
    assert pending_item.status == QueueStatus.PENDING
    assert approval_item.status == QueueStatus.APPROVAL_PENDING

    service.set_global_pause(False, actor="ops@example.com", reason="resume")
    clear_result = service.trigger_emergency_stop(actor="ops@example.com", mode="clear", reason="incident")
    db_session.refresh(pending_item)
    db_session.refresh(approval_item)

    assert clear_result["mode"] == "clear"
    assert clear_result["affected_items"] == 2
    assert pending_item.status == QueueStatus.CANCELED
    assert approval_item.status == QueueStatus.CANCELED


def test_all_control_actions_are_written_to_intervention_log(db_session):
    service = KillSwitchService(db_session)
    queue_item = _create_queue_item(db_session, "twitter", QueueStatus.APPROVAL_PENDING)

    service.set_global_pause(True, actor="ops@example.com", reason="maintenance")
    service.set_platform_pause("twitter", True, actor="ops@example.com", reason="twitter issue")
    service.approve_queue_item(queue_item.id, actor="reviewer@example.com", reason="approved")
    service.reject_queue_item(queue_item.id, actor="reviewer@example.com", reason="rejected after review")

    actions = [entry.action for entry in service.get_intervention_logs()]
    assert "global_pause_set" in actions
    assert "platform_pause_set" in actions
    assert "queue_item_approved" in actions
    assert "queue_item_rejected" in actions
