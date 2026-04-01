from pydantic import BaseModel, Field
from typing import Optional

class LinkedInAuth(BaseModel):
    client_id: str
    client_secret: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    person_id: Optional[str] = None  # e.g., "urn:li:person:ABC123"
    organization_id: Optional[str] = None  # e.g., "urn:li:organization:456789"

class LinkedInConfig(BaseModel):
    auth: LinkedInAuth
    callback_url: str = "http://localhost:8000/auth/linkedin/callback"
    scopes: list[str] = ["w_member_social", "rw_ads", "w_organization_social", "r_liteprofile", "r_ads"]
