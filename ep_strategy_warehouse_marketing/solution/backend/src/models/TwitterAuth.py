from pydantic import BaseModel, Field


class TwitterAuth(BaseModel):
    api_key: str = Field(..., description="Twitter API Key")
    api_secret: str = Field(..., description="Twitter API Secret")
    access_token: str = Field(..., description="Twitter Access Token")
    access_secret: str = Field(..., description="Twitter Access Token Secret")
    bearer_token: str = Field(None, description="Twitter Bearer Token (optional for OAuth 1.1)")


class TwitterConfig(BaseModel):
    auth: TwitterAuth
    max_tweets_per_window: int = 15
    window_minutes: int = 15
    max_tweet_length: int = 280
    max_media_per_tweet: int = 4
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
