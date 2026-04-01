from datetime import UTC, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint

from .database import Base


class EngagementMetric(Base):
    __tablename__ = "engagement_metrics"
    __table_args__ = (
        UniqueConstraint("queue_item_id", "platform", "metric_date", name="uq_engagement_metrics_queue_platform_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    queue_item_id = Column(Integer, ForeignKey("content_queue.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    metric_date = Column(Date, nullable=False, index=True)
    impressions = Column(Integer, default=0, nullable=False)
    reactions = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    saves = Column(Integer, default=0, nullable=False)
    watch_seconds = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
