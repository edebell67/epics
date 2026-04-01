import unittest
from unittest.mock import MagicMock, patch
from src.models.TwitterAuth import TwitterAuth, TwitterConfig
from src.connectors.twitterConnector import TwitterConnector

class TestTwitterConnectorInit(unittest.TestCase):
    def setUp(self):
        auth = TwitterAuth(
            api_key="key",
            api_secret="secret",
            access_token="token",
            access_secret="access_secret"
        )
        self.config = TwitterConfig(auth=auth)

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_init(self, mock_api, mock_oauth, mock_client):
        connector = TwitterConnector(self.config)
        self.assertIsNotNone(connector.client)
        self.assertIsNotNone(connector.api_v1)

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_verify_auth_success(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_me = MagicMock()
        mock_me.data.username = "testuser"
        mock_client.get_me.return_value = mock_me
        
        connector = TwitterConnector(self.config)
        self.assertTrue(connector.verify_auth())
        mock_client.get_me.assert_called_once()

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_verify_auth_fail(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.get_me.side_effect = Exception("API Error")
        
        connector = TwitterConnector(self.config)
        self.assertFalse(connector.verify_auth())
