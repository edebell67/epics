from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator


class SubscriberBase(BaseModel):
    email: str
    preferences: Optional[Dict[str, Any]] = None
    source_tag: Optional[str] = None
    full_name: Optional[str] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if '@' not in normalized or normalized.startswith('@') or normalized.endswith('@'):
            raise ValueError('Invalid email address')

        local_part, domain = normalized.split('@', 1)
        if not local_part or '.' not in domain or domain.startswith('.') or domain.endswith('.'):
            raise ValueError('Invalid email address')

        return normalized


class SubscriberCreate(SubscriberBase):
    # V20260321_1445 - C7: Added UTM tracking fields for submission attribution
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    session_id: Optional[str] = None


class SubscriberUpdate(BaseModel):
    preferences: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class SubscriberResponse(SubscriberBase):
    id: int
    status: str
    confirmation_token: Optional[str] = None
    unsubscribe_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    unsubscribed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriberConfirmation(BaseModel):
    token: str


class SubscriberUnsubscribe(BaseModel):
    token: str
