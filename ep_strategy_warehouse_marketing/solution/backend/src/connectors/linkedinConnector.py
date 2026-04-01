import requests
import logging
import os
import json
import time
from datetime import datetime
from typing import Optional, List
from src.models.LinkedInAuth import LinkedInAuth, LinkedInConfig

class LinkedInConnector:
    BASE_URL = "https://api.linkedin.com/v2"
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

    def __init__(self, config: LinkedInConfig):
        self.config = config
        self.logger = logging.getLogger("linkedin_connector")
        self._setup_logger()
        self.access_token = config.auth.access_token
        self.person_id = config.auth.person_id
        self.organization_id = config.auth.organization_id

    def _setup_logger(self):
        os.makedirs("logs", exist_ok=True)
        handler = logging.FileHandler("logs/linkedin_api.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def get_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.config.auth.client_id,
            "redirect_uri": self.config.callback_url,
            "state": state,
            "scope": " ".join(self.config.scopes)
        }
        req = requests.Request("GET", self.AUTH_URL, params=params).prepare()   
        return req.url

    def exchange_code_for_token(self, code: str) -> Optional[str]:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.callback_url,
            "client_id": self.config.auth.client_id,
            "client_secret": self.config.auth.client_secret
        }
        try:
            response = self._make_request("POST", self.TOKEN_URL, data=data)     
            response.raise_for_status()
            res_data = response.json()
            self.access_token = res_data.get("access_token")
            self.logger.info("Successfully exchanged code for access token")    
            return self.access_token
        except Exception as e:
            self.logger.error(f"Failed to exchange code for token: {str(e)}")   
            return None

    def get_user_profile(self) -> Optional[str]:
        if not self.access_token:
            self.logger.error("No access token available")
            return None

        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            # v2/me returns the lite profile
            response = self._make_request("GET", f"{self.BASE_URL}/me", headers=headers)
            response.raise_for_status()
            data = response.json()
            self.person_id = f"urn:li:person:{data.get('id')}"
            self.logger.info(f"Successfully retrieved profile for {data.get('localizedFirstName')} (ID: {self.person_id})")
            return self.person_id
        except Exception as e:
            self.logger.error(f"Failed to get user profile: {str(e)}")
            return None

    def verify_auth(self) -> bool:
        return self.get_user_profile() is not None

    def post_text(self, text: str, on_behalf_of_org: bool = False) -> Optional[str]:
        author = self.organization_id if on_behalf_of_org and self.organization_id else self.person_id
        if not author:
            if not self.get_user_profile():
                return None
            author = self.person_id

        if not self.access_token:
            return None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        # LinkedIn UGC Post (User Generated Content) API
        post_data = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        try:
            response = self._make_request("POST", f"{self.BASE_URL}/ugcPosts", headers=headers, json=post_data)
            response.raise_for_status()
            res_data = response.json()
            post_id = res_data.get("id")
            self.logger.info(f"Successfully posted to LinkedIn: {post_id}")     
            return post_id
        except Exception as e:
            self.logger.error(f"Failed to post to LinkedIn: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"Response: {e.response.text}")
            return None

    def post_media(self, text: str, media_paths: List[str], on_behalf_of_org: bool = False) -> Optional[str]:
        # LinkedIn media upload is a 3-step process
        # 1. Register an upload
        # 2. Upload the file
        # 3. Create the post referencing the media URN
        
        author = self.organization_id if on_behalf_of_org and self.organization_id else self.person_id
        if not author:
            if not self.get_user_profile():
                return None
            author = self.person_id

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        media_urns = []
        for path in media_paths:
            urn = self._upload_image(path, author)
            if urn:
                media_urns.append(urn)

        if not media_urns:
            self.logger.error("No media uploaded successfully, falling back to text post or failing")
            return self.post_text(text, on_behalf_of_org)

        post_data = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "description": {
                                "text": "Marketing content from Strategy Warehouse"
                            },
                            "media": urn,
                            "title": {
                                "text": "Strategy Warehouse Performance"        
                            }
                        } for urn in media_urns
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        try:
            response = self._make_request("POST", f"{self.BASE_URL}/ugcPosts", headers=headers, json=post_data)
            response.raise_for_status()
            res_data = response.json()
            post_id = res_data.get("id")
            self.logger.info(f"Successfully posted to LinkedIn with media: {post_id}")
            return post_id
        except Exception as e:
            self.logger.error(f"Failed to post to LinkedIn with media: {str(e)}")
            return None

    def _upload_image(self, path: str, author: str) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        # Step 1: Register upload
        register_data = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],       
                "owner": author,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }

        try:
            response = self._make_request("POST", f"{self.BASE_URL}/assets?action=registerUpload", headers=headers, json=register_data)
            response.raise_for_status()
            res_data = response.json()
            upload_url = res_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_urn = res_data['value']['asset']

            # Step 2: Upload file
            with open(path, 'rb') as f:
                upload_headers = {"Authorization": f"Bearer {self.access_token}"}
                upload_response = self._make_request("PUT", upload_url, headers=upload_headers, data=f)
                upload_response.raise_for_status()

            self.logger.info(f"Successfully uploaded media: {asset_urn}")       
            return asset_urn
        except Exception as e:
            self.logger.error(f"Failed to upload media {path}: {str(e)}")       
            return None

    def check_rate_limit(self) -> bool:
        return True

    def post_article(self, text: str, url: str, title: str = None, description: str = None, on_behalf_of_org: bool = False) -> Optional[str]:
        author = self.organization_id if on_behalf_of_org and self.organization_id else self.person_id
        if not author:
            if not self.get_user_profile():
                return None
            author = self.person_id

        if not self.access_token:
            return None

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

        post_data = {
            'author': author,
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {
                        'text': text
                    },
                    'shareMediaCategory': 'ARTICLE',
                    'media': [
                        {
                            'status': 'READY',
                            'originalUrl': url,
                            'title': {
                                'text': title if title else 'Strategy Warehouse Market Insights'
                            }
                        }
                    ]
                }
            },
            'visibility': {
                'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
            }
        }

        if description:
            post_data['specificContent']['com.linkedin.ugc.ShareContent']['media'][0]['description'] = {
                'text': description
            }

        try:
            response = self._make_request("POST", f'{self.BASE_URL}/ugcPosts', headers=headers, json=post_data)
            response.raise_for_status()
            res_data = response.json()
            post_id = res_data.get('id')
            self.logger.info(f'Successfully posted article to LinkedIn: {post_id}')
            return post_id
        except Exception as e:
            self.logger.error(f'Failed to post article to LinkedIn: {str(e)}')  
            if hasattr(e, 'response') and e.response:
                self.logger.error(f'Response: {e.response.text}')
            return None

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        max_retries = 3
        for attempt in range(max_retries):
            response = requests.request(method, url, **kwargs)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))       
                self.logger.warning(f"Rate limited. Retrying after {retry_after} seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(retry_after)
                continue
            return response
        return response
