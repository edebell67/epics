from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Optional, Dict, Any
from datetime import datetime

class ConversionEventCreate(BaseModel):
    # V20260321_1445 - C7: Schema for client-side event submission
    event_type: str
    session_id: Optional[str] = None
    url: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None

class ConversionStatsResponse(BaseModel):
    utm_source: Optional[str] = None
    page_views: int
    form_impressions: int
    form_submits: int
    confirmations: int
    view_to_submit_ratio: float
    submit_to_confirm_ratio: float
