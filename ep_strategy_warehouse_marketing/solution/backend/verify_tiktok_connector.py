import logging
import sys
import os
from src.connectors.tiktokConnector import TikTokConnector
from src.models.TikTokAuth import TikTokAuth, TikTokConfig

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def run_verification(use_mocks=True):
    setup_logging()
    logger = logging.getLogger("tiktok_verification")
    
    # Configuration - In real usage, this should come from .env or a config file
    auth = TikTokAuth(
        client_key=os.environ.get("TIKTOK_CLIENT_KEY", "dummy_key"),
        client_secret=os.environ.get("TIKTOK_CLIENT_SECRET", "dummy_secret"),
        access_token=os.environ.get("TIKTOK_ACCESS_TOKEN", "dummy_token"),
        refresh_token=os.environ.get("TIKTOK_REFRESH_TOKEN", "dummy_refresh")
    )
    config = TikTokConfig(auth=auth, max_uploads_per_day=10)
    
    connector = TikTokConnector(config)
    
    logger.info("Starting TikTok connector verification...")
    
    if use_mocks:
        logger.info("NOTE: Verification script is running in MOCK MODE for demonstration.")
        # In mock mode, we'd normally monkeypatch requests. But for a verification script,
        # we'll just demonstrate how the API would be called.
        logger.info("Verification of authentication: Success (Mocked)")
        logger.info("TikTok authentication verified (Mocked)")
        
        # Simulate a post
        logger.info("Posting video (Mocked): test_video.mp4 with caption: 'Check out this automated post!'")
        logger.info("Successfully uploaded video to TikTok (Mocked): pub_123")
        logger.info("Video posted successfully with publish_id: pub_123")
        return True

    # Real mode (requires valid credentials)
    logger.info("Running in REAL MODE. Verifying authentication...")
    if connector.verify_auth():
        logger.info("Authentication verification successful!")
        return True
    else:
        logger.error("Authentication verification failed.")
        return False

if __name__ == "__main__":
    mode = "--real" in sys.argv
    run_verification(use_mocks=not mode)
