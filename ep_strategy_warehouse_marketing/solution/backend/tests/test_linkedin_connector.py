import unittest
from unittest.mock import patch, MagicMock
from src.connectors.linkedinConnector import LinkedInConnector
from src.models.LinkedInAuth import LinkedInAuth, LinkedInConfig
import requests

class TestLinkedInConnector(unittest.TestCase):
    def setUp(self):
        self.auth = LinkedInAuth(
            client_id="test_id",
            client_secret="test_secret",
            access_token="test_token",
            person_id="urn:li:person:123",
            organization_id="urn:li:organization:456"
        )
        self.config = LinkedInConfig(auth=self.auth)
        self.connector = LinkedInConnector(self.config)

    @patch('src.connectors.linkedinConnector.requests.request')
    def test_get_user_profile(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "localizedFirstName": "Test"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        profile_id = self.connector.get_user_profile()
        self.assertEqual(profile_id, "urn:li:person:123")
        self.assertEqual(mock_request.call_args[0][0], "GET")

    @patch('src.connectors.linkedinConnector.requests.request')
    def test_post_text(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "urn:li:ugcPost:456"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        post_id = self.connector.post_text("Hello LinkedIn")
        self.assertEqual(post_id, "urn:li:ugcPost:456")
        self.assertEqual(mock_request.call_args[0][0], "POST")

    @patch('src.connectors.linkedinConnector.requests.request')
    def test_post_text_organization(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "urn:li:ugcPost:org_post"}     
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        post_id = self.connector.post_text("Hello LinkedIn from Org", on_behalf_of_org=True)
        self.assertEqual(post_id, "urn:li:ugcPost:org_post")
        
        # Verify that the author in the request body is the organization_id
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs['json']['author'], "urn:li:organization:456")   

    @patch('src.connectors.linkedinConnector.requests.request')
    def test_post_media(self, mock_request):
        # Mock register upload
        mock_reg_response = MagicMock()
        mock_reg_response.status_code = 201
        mock_reg_response.json.return_value = {
            "value": {
                "uploadMechanism": {
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                        "uploadUrl": "https://upload.url"
                    }
                },
                "asset": "urn:li:digitalmediaAsset:789"
            }
        }
        mock_reg_response.raise_for_status.return_value = None

        # Mock create post
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"id": "urn:li:ugcPost:999"}     
        mock_post_response.raise_for_status.return_value = None

        # Mock file upload
        mock_put_response = MagicMock()
        mock_put_response.status_code = 201
        mock_put_response.raise_for_status.return_value = None

        mock_request.side_effect = [mock_reg_response, mock_put_response, mock_post_response]

        # Create a dummy file for testing
        with open("test_image.png", "w") as f:
            f.write("dummy")

        try:
            post_id = self.connector.post_media("Post with media", ["test_image.png"])
            self.assertEqual(post_id, "urn:li:ugcPost:999")
            self.assertEqual(mock_request.call_count, 3) # register, put, post
        finally:
            import os
            if os.path.exists("test_image.png"):
                os.remove("test_image.png")

    @patch('src.connectors.linkedinConnector.requests.request')
    def test_post_article(self, mock_request):
        m = MagicMock()
        m.status_code = 201
        m.json.return_value = {'id': 'urn:li:ugcPost:000'}
        m.raise_for_status.return_value = None
        mock_request.return_value = m
        pid = self.connector.post_article('Check this out', 'https://strategy-warehouse.com')
        self.assertEqual(pid, 'urn:li:ugcPost:000')
        self.assertEqual(mock_request.call_args[0][0], "POST")

    @patch('src.connectors.linkedinConnector.requests.request')
    @patch('src.connectors.linkedinConnector.time.sleep')
    def test_rate_limit_handling(self, mock_sleep, mock_request):
        # Mock 429 followed by 200
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"Retry-After": "1"}
        
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"id": "123"}
        
        mock_request.side_effect = [mock_429, mock_200]
        
        response = self.connector._make_request("GET", "https://api.linkedin.com/v2/me")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)
        mock_sleep.assert_called_once_with(1)

if __name__ == '__main__':
    unittest.main()
