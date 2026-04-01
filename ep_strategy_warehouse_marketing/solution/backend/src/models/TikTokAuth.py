from pydantic import BaseModel, Field
from typing import Optional

class TikTokAuth(BaseModel):
    client_key: str = Field(..., description="TikTok Client Key")
    client_secret: str = Field(..., description="TikTok Client Secret")
    access_token: Optional[str] = Field(None, description="TikTok Access Token")
    refresh_token: Optional[str] = Field(None, description="TikTok Refresh Token")
    open_id: Optional[str] = Field(None, description="TikTok Open ID")

class TikTokConfig(BaseModel):
    auth: TikTokAuth
    max_uploads_per_day: int = 10
