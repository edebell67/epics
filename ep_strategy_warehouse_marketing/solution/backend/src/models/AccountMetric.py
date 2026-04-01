from datetime import UTC, datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, UniqueConstraint

from .database import Base


class AccountMetric(Base):
    __tablename__ = "account_metrics"
    __table_args__ = (
        UniqueConstraint("platform", "metric_date", name="uq_account_metrics_platform_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    metric_date = Column(Date, nullable=False, index=True)
    follower_count = Column(Integer, default=0, nullable=False)
    reach = Column(Integer, default=0, nullable=False)
    profile_views = Column(Integer, default=0, nullable=False)
    subscriber_count = Column(Integer, default=0, nullable=False)
    conversion_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
