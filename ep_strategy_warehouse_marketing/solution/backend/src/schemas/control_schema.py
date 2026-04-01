from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PauseRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=255)
    paused: bool
    reason: str | None = Field(default=None, max_length=500)


class EmergencyStopRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=255)
    mode: Literal["freeze", "clear"] = "freeze"
    reason: str | None = Field(default=None, max_length=500)


class QueueApprovalRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=255)
    reason: str | None = Field(default=None, max_length=500)


class ManualControlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope_type: str
    scope_key: str
    is_paused: bool
    emergency_stop_active: bool
    emergency_mode: str | None
    reason: str | None
    updated_by: str | None
    updated_at: datetime | None


class InterventionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    scope_type: str
    scope_key: str
    actor: str
    reason: str | None
    target_queue_id: int | None
    metadata_json: str | None
    created_at: datetime


class KillSwitchStatusResponse(BaseModel):
    global_control: ManualControlResponse
    platform_controls: list[ManualControlResponse]
    pending_approvals: list[int]
    emergency_stop_active: bool


class QueueActionResponse(BaseModel):
    queue_id: int
    status: str
    detail: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueueItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_id: UUID
    platform: str
    status: str
    content_data: dict[str, Any]
    scheduled_for: datetime
    priority: int
    retry_count: int
    max_retries: int
    last_error: str | None
    next_retry_at: datetime | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
