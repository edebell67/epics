import logging
import os
import requests
import json
from datetime import datetime
from src.models.TikTokAuth import TikTokAuth, TikTokConfig

class TikTokConnector:
    def __init__(self, config: TikTokConfig):
        self.config = config
        self.base_url = "https://open.tiktokapis.com/v2"
        self.logger = logging.getLogger("tiktok_connector")
        self._setup_logger()

    def _setup_logger(self):
        os.makedirs("logs", exist_ok=True)
        handler = logging.FileHandler("logs/tiktok_api.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def verify_auth(self):
        if not self.config.auth.access_token:
            self.logger.error("No access token provided")
            return False

        try:
            # Query user info to verify token
            headers = {"Authorization": f"Bearer {self.config.auth.access_token}"}
            response = requests.get(f"{self.base_url}/user/info/", headers=headers)
            if response.status_code == 200:
                self.logger.info("TikTok authentication verified")
                return True
            else:
                self.logger.error(f"TikTok verification failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error during TikTok verification: {str(e)}")    
            return False

    def refresh_access_token(self):
        if not self.config.auth.refresh_token:
            self.logger.error("No refresh token available")
            return None

        try:
            url = f"{self.base_url}/oauth/token/"
            data = {
                "client_key": self.config.auth.client_key,
                "client_secret": self.config.auth.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.config.auth.refresh_token
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.config.auth.access_token = token_data.get("access_token")  
                self.config.auth.refresh_token = token_data.get("refresh_token")
                self.logger.info("Successfully refreshed TikTok access token")  
                return self.config.auth.access_token
            else:
                self.logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error refreshing TikTok token: {str(e)}")       
            return None

    def upload_video(self, video_path: str, caption: str = None, hashtags: list = None, privacy_level: str = "PUBLIC_TO_EVERYONE"):
        # Implementation of TikTok Direct Post API
        # Step 1: Initiate upload
        if not self.verify_auth():
            self.logger.error("Authentication verification failed before upload")
            return None

        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found: {video_path}")
            return None

        try:
            url = f"{self.base_url}/post/publish/video/init/"
            headers = {
                "Authorization": f"Bearer {self.config.auth.access_token}",     
                "Content-Type": "application/json"
            }
            
            # Prepare caption with hashtags
            full_caption = caption or ""
            if hashtags:
                full_caption += " " + " ".join([f"#{h}" for h in hashtags])
            
            video_size = os.path.getsize(video_path)
            
            payload = {
                "post_info": {
                    "title": full_caption,
                    "privacy_level": privacy_level,
                    "disable_comment": False,
                    "disable_duet": False,
                    "disable_stitch": False
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": video_size,
                    "chunk_size": video_size,
                    "total_chunk_count": 1
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                upload_data = response.json()
                publish_id = upload_data.get("data", {}).get("publish_id")      
                upload_url = upload_data.get("data", {}).get("upload_url")      

                if not upload_url:
                    self.logger.error(f"No upload_url returned from TikTok: {upload_data}")
                    return None

                # Step 2: Upload the actual video binary
                with open(video_path, 'rb') as f:
                    upload_response = requests.put(upload_url, data=f, headers={"Content-Type": "video/mp4"})

                if upload_response.status_code == 200 or upload_response.status_code == 201:
                    self.logger.info(f"Successfully uploaded video to TikTok: {publish_id}")
                    # Update local rate limit tracking
                    self._update_local_rate_limit()
                    return publish_id
                else:
                    self.logger.error(f"Binary upload failed: {upload_response.status_code} - {upload_response.text}")

            self.logger.error(f"Failed to initiate upload: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            self.logger.error(f"Error during video upload: {str(e)}")
            return None

    def post_video(self, video_path: str, caption: str, hashtags: list = None, privacy_level: str = "PUBLIC_TO_EVERYONE"): 
        try:
            if not self.check_rate_limit():
                self.logger.warning("Rate limit reached, skipping post")
                return None

            publish_id = self.upload_video(video_path, caption, hashtags, privacy_level)
            if publish_id:
                self.logger.info(f"Video posted successfully with publish_id: {publish_id}")
                return publish_id
            return None
        except Exception as e:
            self.logger.error(f"Failed to post video: {str(e)}")
            return None

    def check_rate_limit(self):
        # Local rate limit check using a file for simplicity
        limit_file = "logs/tiktok_rate_limit.json"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if os.path.exists(limit_file):
            with open(limit_file, 'r') as f:
                data = json.load(f)
                if data.get("date") == today:
                    count = data.get("count", 0)
                    if count >= self.config.max_uploads_per_day:
                        self.logger.warning(f"TikTok rate limit reached for today: {count}/{self.config.max_uploads_per_day}")
                        return False
        return True

    def _update_local_rate_limit(self):
        limit_file = "logs/tiktok_rate_limit.json"
        today = datetime.now().strftime("%Y-%m-%d")
        
        count = 1
        if os.path.exists(limit_file):
            with open(limit_file, 'r') as f:
                data = json.load(f)
                if data.get("date") == today:
                    count = data.get("count", 0) + 1
        
        with open(limit_file, 'w') as f:
            json.dump({"date": today, "count": count}, f)
