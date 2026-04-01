from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class ContentVariant(Base):
    __tablename__ = "content_variants"
    __table_args__ = (
        UniqueConstraint("queue_item_id", "platform", name="uq_content_variants_queue_platform"),
    )

    id = Column(Integer, primary_key=True, index=True)
    queue_item_id = Column(Integer, ForeignKey("content_queue.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    headline = Column(String(300), nullable=False)
    body = Column(String, nullable=False)
    hashtags = Column(JSON, nullable=True)
    call_to_action = Column(String(255), nullable=False)
    variant_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    queue_item = relationship("ContentQueue", back_populates="variants")
