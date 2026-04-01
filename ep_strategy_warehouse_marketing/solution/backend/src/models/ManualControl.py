from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint

from .database import Base


class ManualControl(Base):
    __tablename__ = "manual_controls"
    __table_args__ = (
        UniqueConstraint("scope_type", "scope_key", name="uq_manual_controls_scope"),
    )

    id = Column(Integer, primary_key=True, index=True)
    scope_type = Column(String(32), nullable=False, index=True)
    scope_key = Column(String(64), nullable=False, index=True)
    is_paused = Column(Boolean, default=False, nullable=False)
    emergency_stop_active = Column(Boolean, default=False, nullable=False)
    emergency_mode = Column(String(32), nullable=True)
    reason = Column(String(500), nullable=True)
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class InterventionLog(Base):
    __tablename__ = "intervention_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    scope_type = Column(String(32), nullable=False, index=True)
    scope_key = Column(String(64), nullable=False, index=True)
    actor = Column(String(255), nullable=False, index=True)
    reason = Column(String(500), nullable=True)
    target_queue_id = Column(Integer, nullable=True, index=True)
    metadata_json = Column("metadata", String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
