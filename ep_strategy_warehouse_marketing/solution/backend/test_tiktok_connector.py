import unittest
import os
import json
from unittest.mock import patch, MagicMock, mock_open
from src.connectors.tiktokConnector import TikTokConnector
from src.models.TikTokAuth import TikTokAuth, TikTokConfig

class TestTikTokConnector(unittest.TestCase):
    def setUp(self):
        self.auth = TikTokAuth(
            client_key="test_key",
            client_secret="test_secret",
            access_token="initial_access_token",
            refresh_token="initial_refresh_token"
        )
        self.config = TikTokConfig(auth=self.auth, max_uploads_per_day=2)
        self.connector = TikTokConnector(self.config)

    @patch('requests.get')
    def test_verify_auth_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        self.assertTrue(self.connector.verify_auth())
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_verify_auth_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        self.assertFalse(self.connector.verify_auth())

    @patch('requests.post')
    def test_refresh_access_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token"
        }
        mock_post.return_value = mock_response

        new_token = self.connector.refresh_access_token()
        self.assertEqual(new_token, "new_access_token")

    @patch('requests.post')
    @patch('requests.put')
    @patch('src.connectors.tiktokConnector.TikTokConnector.verify_auth')        
    @patch('src.connectors.tiktokConnector.TikTokConnector._update_local_rate_limit')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b"test video data")
    def test_upload_video_success(self, mock_file_open, mock_getsize, mock_exists, mock_rate_limit, mock_verify, mock_put, mock_post):
        mock_verify.return_value = True
        mock_exists.return_value = True
        mock_getsize.return_value = 1024

        mock_init_response = MagicMock()
        mock_init_response.status_code = 200
        mock_init_response.json.return_value = {
            "data": {
                "publish_id": "pub_123",
                "upload_url": "https://test.upload.url"
            }
        }

        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 200

        mock_post.return_value = mock_init_response
        mock_put.return_value = mock_upload_response

        publish_id = self.connector.upload_video("dummy_path.mp4", caption="Test")
        self.assertEqual(publish_id, "pub_123")
        mock_rate_limit.assert_called_once()
        
    def test_rate_limit(self):
        # Use a real file for the rate limit test but in a temp location if needed
        # Or just mock the file operations in check_rate_limit
        with patch('os.path.exists') as mock_exists:
            with patch('builtins.open', mock_open(read_data=json.dumps({"date": __import__('datetime').datetime.now().strftime("%Y-%m-%d"), "count": 2}))):
                mock_exists.return_value = True
                self.assertFalse(self.connector.check_rate_limit())

if __name__ == '__main__':
    unittest.main()
