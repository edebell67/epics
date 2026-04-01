import requests
import logging
import os
from datetime import datetime, UTC
from src.models.DiscordAuth import DiscordAuth, DiscordConfig

class DiscordConnector:
    def __init__(self, config: DiscordConfig):
        self.config = config
        self.webhook_url = config.auth.webhook_url
        self.logger = logging.getLogger("discord_connector")
        self._setup_logger()
        
    def _setup_logger(self):
        os.makedirs("logs", exist_ok=True)
        if not self.logger.handlers:
            handler = logging.FileHandler("logs/discord_api.log")
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def post_message(self, text: str):
        try:
            payload = {"content": text}
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            self.logger.info(f"Successfully posted message to Discord")
            return True
        except Exception as e:
            self.logger.error(f"Failed to post message to Discord: {str(e)}")
            return False

    def post_embed(self, title: str, description: str, color: int = 0x00ff00, image_url: str = None, fields: list = None):
        try:
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now(UTC).isoformat()
            }
            if image_url:
                embed["image"] = {"url": image_url}
            if fields:
                embed["fields"] = fields
                
            payload = {"embeds": [embed]}
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            self.logger.info(f"Successfully posted embed to Discord")
            return True
        except Exception as e:
            self.logger.error(f"Failed to post embed to Discord: {str(e)}")
            return False

    def check_rate_limit(self):
        self.logger.info(f"Checking rate limit status for Discord")
        return True
