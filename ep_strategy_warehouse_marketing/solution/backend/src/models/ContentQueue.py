from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, JSON, String, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import enum
import uuid
from .database import Base

class QueueStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVAL_PENDING = "approval_pending"
    IN_PROGRESS = "in_progress"
    PUBLISHED = "published"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELED = "canceled"

class ContentQueue(Base):
    __tablename__ = "content_queue"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Uuid, default=uuid.uuid4, index=True)
    platform = Column(String(50), nullable=False, index=True)
    status = Column(SQLEnum(QueueStatus), default=QueueStatus.PENDING, index=True)
    
    # The actual content for the platform (VariantContent + common fields)
    content_data = Column(JSON, nullable=False)
    
    # Scheduling and Priority
    scheduled_for = Column(DateTime, nullable=False, index=True)
    priority = Column(Integer, default=0, index=True) # Higher number = Higher priority
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(String(500), nullable=True)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    published_at = Column(DateTime, nullable=True)

    variants = relationship(
        "ContentVariant",
        back_populates="queue_item",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ContentQueue(id={self.id}, platform='{self.platform}', status='{self.status}', scheduled_for='{self.scheduled_for}')>"
