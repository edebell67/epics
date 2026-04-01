from pydantic import BaseModel, Field
from typing import Optional

class RedditAuth(BaseModel):
    client_id: str = Field(..., description="Reddit Client ID")
    client_secret: str = Field(..., description="Reddit Client Secret")
    user_agent: str = Field(..., description="Reddit User Agent")
    username: str = Field(..., description="Reddit Username")
    password: str = Field(..., description="Reddit Password")

class RedditConfig(BaseModel):
    auth: RedditAuth
    default_subreddit: str = Field("algotrading", description="Default subreddit for posting")
    max_posts_per_day: int = 5
