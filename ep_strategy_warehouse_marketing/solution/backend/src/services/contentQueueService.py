import logging
from datetime import datetime, UTC, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ..models.ContentQueue import ContentQueue, QueueStatus
from ..models.ContentVariant import ContentVariant
from ..schemas.content_schema import PublishableContent
from .postingRulesService import PostingRulesService


def get_now():
    return datetime.now(UTC).replace(tzinfo=None)

class ContentQueueService:
    def __init__(self, db: Session, posting_rules: Optional[PostingRulesService] = None):
        self.db = db
        self.posting_rules = posting_rules
        self.logger = logging.getLogger("ContentQueueService")
        self.base_backoff_minutes = 5

    def add_to_queue(self, content: PublishableContent) -> List[ContentQueue]:
        queue_items = []
        scheduled_for = content.scheduled_for
        if scheduled_for and scheduled_for.tzinfo:
            scheduled_for = scheduled_for.replace(tzinfo=None)
        if not scheduled_for:
            scheduled_for = get_now()
        
        if not content.platform_variants:
            return []

        for platform, variant in content.platform_variants.items():
            platform_name = platform if isinstance(platform, str) else platform.value
            content_dict = {
                "content_id": str(content.content_id),
                "content_type": content.content_type,
                "campaign_angle": content.campaign_angle,
                "pillar": content.pillar,
                "format_name": content.format_name,
                "headline": variant.headline,
                "body": variant.body,
                "hashtags": variant.hashtags,
                "call_to_action": variant.call_to_action,
                "media_urls": content.media_urls,
                "landing_page_url": content.landing_page_url
            }
            requires_approval = False
            if self.posting_rules:
                requires_approval = self.posting_rules.requires_manual_approval(platform_name, str(content.content_type))
            queue_item = ContentQueue(
                content_id=content.content_id,
                platform=platform_name,
                status=QueueStatus.APPROVAL_PENDING if requires_approval else QueueStatus.PENDING,
                content_data=content_dict,
                scheduled_for=scheduled_for,
                priority=0
            )
            self.db.add(queue_item)
            self.db.flush()
            self.db.add(
                ContentVariant(
                    queue_item_id=queue_item.id,
                    platform=platform_name,
                    headline=variant.headline,
                    body=variant.body,
                    hashtags=variant.hashtags,
                    call_to_action=variant.call_to_action,
                    variant_metadata={
                        "content_type": str(content.content_type),
                        "campaign_angle": str(content.campaign_angle),
                        "pillar": content.pillar,
                        "format_name": content.format_name,
                    },
                )
            )
            queue_items.append(queue_item)
        self.db.commit()
        return queue_items

    def get_next_to_publish(self, platform: Optional[str] = None) -> Optional[ContentQueue]:
        now = get_now()
        
        # 1. Fetch candidates (Pending and due, or Failed and retry due)
        # We fetch all due items and check them against posting rules one by one
        
        query = self.db.query(ContentQueue).filter(
            or_(
                ContentQueue.status == QueueStatus.PENDING,
                and_(
                    ContentQueue.status == QueueStatus.FAILED,
                    ContentQueue.next_retry_at <= now,
                    ContentQueue.retry_count < ContentQueue.max_retries
                )
            )
        ).filter(
            ContentQueue.scheduled_for <= now
        ).order_by(desc(ContentQueue.priority), ContentQueue.scheduled_for.asc())
        
        if platform:
            query = query.filter(ContentQueue.platform == platform)
            
        candidates = query.all()
        
        for item in candidates:
            # Check rate limits if posting_rules service is available
            if self.posting_rules:
                content_type = item.content_data.get("content_type", "general")
                if not self.posting_rules.can_post(item.platform, content_type, now):
                    continue # Skip this item for now, check next
            
            # Found an item that can be published
            item.status = QueueStatus.IN_PROGRESS
            self.db.commit()
            self.db.refresh(item)
            return item
            
        return None

    def mark_as_published(self, queue_id: int):
        item = self.db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()
        if item:
            item.status = QueueStatus.PUBLISHED
            item.published_at = get_now()
            
            # Record the post in posting rules to update counters/timers
            if self.posting_rules:
                self.posting_rules.record_post(item.platform, item.published_at)
                
            self.db.commit()

    def mark_as_failed(self, queue_id: int, error_msg: str):
        item = self.db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()
        if item:
            item.status = QueueStatus.FAILED
            item.last_error = error_msg[:500]
            item.retry_count += 1
            if item.retry_count < item.max_retries:
                backoff = self.base_backoff_minutes * (2 ** (item.retry_count - 1))
                item.next_retry_at = get_now() + timedelta(minutes=backoff)
            self.db.commit()

    def get_queue_state(self, status: Optional[str] = None, platform: Optional[str] = None) -> List[ContentQueue]:
        query = self.db.query(ContentQueue)
        if status:
            query = query.filter(ContentQueue.status == status)
        if platform:
            query = query.filter(ContentQueue.platform == platform)
        return query.order_by(ContentQueue.scheduled_for.asc()).all()

    def get_backlog_depth(self, statuses: Optional[list[str]] = None) -> int:
        tracked_statuses = statuses or [
            QueueStatus.PENDING,
            QueueStatus.APPROVAL_PENDING,
            QueueStatus.IN_PROGRESS,
            QueueStatus.FAILED,
        ]
        return (
            self.db.query(ContentQueue)
            .filter(ContentQueue.status.in_(tracked_statuses))
            .count()
        )

    def pause_item(self, queue_id: int):
        item = self.db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()
        if item:
            item.status = QueueStatus.PAUSED
            self.db.commit()

    def resume_item(self, queue_id: int):
        item = self.db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()
        if item:
            item.status = QueueStatus.PENDING
            self.db.commit()
