from src.models.TikTokAuth import TikTokAuth, TikTokConfig
import json

data = {
    "auth": {
        "client_key": "test_key",
        "client_secret": "test_secret"
    },
    "max_uploads_per_day": 5
}

try:
    config = TikTokConfig(**data)
    print("Model validation successful!")
    print(config.model_dump_json(indent=2))
except Exception as e:
    print(f"Model validation failed: {e}")
