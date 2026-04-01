from pydantic import BaseModel, Field

class DiscordAuth(BaseModel):
    webhook_url: str = Field(..., description="Discord Webhook URL")
    bot_token: str = Field(None, description="Discord Bot Token (optional for webhook posting)")

class DiscordConfig(BaseModel):
    auth: DiscordAuth
    max_posts_per_window: int = 5
    window_minutes: int = 1
