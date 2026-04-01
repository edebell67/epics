import os
import sys
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock

# Set DATABASE_URL to sqlite in memory for testing BEFORE importing src
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.database import Base
from src.models.ContentQueue import ContentQueue, QueueStatus
from src.models.ContentVariant import ContentVariant
from src.services.contentQueueService import ContentQueueService, get_now
from src.schemas.content_schema import PublishableContent, ContentType, CampaignAngle, Platform, VariantContent

@pytest.fixture
def db_session():
    # Use a fresh engine for each test to ensure a clean in-memory DB
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_add_to_queue(db_session):
    service = ContentQueueService(db_session)
    content = PublishableContent(
        content_type=ContentType.SIGNAL_ALERT,
        campaign_angle=CampaignAngle.MOMENTUM,
        pillar="daily_signal_edge",
        format_name="flash_signal_post",
        headline="Test Headline",
        body="Test Body",
        call_to_action="Join now",
        landing_page_url="https://example.com",
        platform_variants={
            Platform.TWITTER: VariantContent(
                platform=Platform.TWITTER,
                headline="Twitter Headline",
                body="Twitter Body",
                hashtags=["#test"],
                call_to_action="Join Twitter"
            )
        }
    )
    
    items = service.add_to_queue(content)
    assert len(items) == 1
    assert items[0].status == QueueStatus.PENDING
    variants = db_session.query(ContentVariant).all()
    assert len(variants) == 1
    assert variants[0].queue_item_id == items[0].id
    assert variants[0].platform == Platform.TWITTER.value

def test_get_next_to_publish_due_now(db_session):
    service = ContentQueueService(db_session)
    now = get_now()
    item = ContentQueue(
        platform=Platform.TWITTER.value,
        status=QueueStatus.PENDING,
        content_data={"test": "data"},
        scheduled_for=now - timedelta(minutes=10)
    )
    db_session.add(item)
    db_session.commit()
    
    next_item = service.get_next_to_publish(Platform.TWITTER.value)
    assert next_item is not None
    assert next_item.id == item.id

def test_get_next_to_publish_future(db_session):
    service = ContentQueueService(db_session)
    now = get_now()
    future = now + timedelta(minutes=10)
    item = ContentQueue(
        platform=Platform.TWITTER.value,
        status=QueueStatus.PENDING,
        content_data={"test": "data"},
        scheduled_for=future
    )
    db_session.add(item)
    db_session.commit()
    
    next_item = service.get_next_to_publish(Platform.TWITTER.value)
    assert next_item is None

def test_retry_logic(db_session):
    service = ContentQueueService(db_session)
    item = ContentQueue(
        platform=Platform.TWITTER.value,
        status=QueueStatus.IN_PROGRESS,
        content_data={"test": "data"},
        scheduled_for=get_now() - timedelta(minutes=10)
    )
    db_session.add(item)
    db_session.commit()
    
    service.mark_as_failed(item.id, "Rate limit exceeded")
    db_session.refresh(item)
    
    assert item.status == QueueStatus.FAILED
    assert item.retry_count == 1
    assert item.next_retry_at is not None
    assert item.next_retry_at > get_now() - timedelta(seconds=1)

def test_queue_priority(db_session):
    service = ContentQueueService(db_session)
    now = get_now()
    # Item 1: lower priority
    item1 = ContentQueue(
        platform=Platform.TWITTER.value,
        status=QueueStatus.PENDING,
        content_data={"id": 1},
        scheduled_for=now - timedelta(minutes=10),
        priority=1
    )
    # Item 2: higher priority
    item2 = ContentQueue(
        platform=Platform.TWITTER.value,
        status=QueueStatus.PENDING,
        content_data={"id": 2},
        scheduled_for=now - timedelta(minutes=5),
        priority=10
    )
    db_session.add_all([item1, item2])
    db_session.commit()
    
    next_item = service.get_next_to_publish(Platform.TWITTER.value)
    assert next_item.priority == 10
    assert next_item.content_data["id"] == 2

def test_rate_limiting_integration(db_session):
    mock_rules = MagicMock()
    # First call returns True, second returns False
    mock_rules.can_post.side_effect = [True, False]
    
    service = ContentQueueService(db_session, posting_rules=mock_rules)
    now = get_now()
    
    item1 = ContentQueue(
        platform=Platform.TWITTER.value,
        status=QueueStatus.PENDING,
        content_data={"content_type": "signal_alert"},
        scheduled_for=now - timedelta(minutes=10),
        priority=10
    )
    item2 = ContentQueue(
        platform=Platform.TWITTER.value,
        status=QueueStatus.PENDING,
        content_data={"content_type": "signal_alert"},
        scheduled_for=now - timedelta(minutes=5),
        priority=5
    )
    db_session.add_all([item1, item2])
    db_session.commit()
    
    # First call: item1 should be returned (mock returns True)
    next1 = service.get_next_to_publish(Platform.TWITTER.value)
    assert next1 is not None
    assert next1.id == item1.id
    
    # Second call: item2 should NOT be returned (mock returns False)
    next2 = service.get_next_to_publish(Platform.TWITTER.value)
    assert next2 is None
