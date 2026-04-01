import unittest
from unittest.mock import MagicMock, patch
from src.models.DiscordAuth import DiscordAuth, DiscordConfig
from src.connectors.discordConnector import DiscordConnector

class TestDiscordConnector(unittest.TestCase):
    def setUp(self):
        auth = DiscordAuth(
            webhook_url="https://discord.com/api/webhooks/123/456"
        )
        self.config = DiscordConfig(auth=auth)

    @patch("requests.post")
    def test_post_message_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        connector = DiscordConnector(self.config)
        result = connector.post_message("Hello Discord!")
        self.assertTrue(result)
        mock_post.assert_called()

    @patch("requests.post")
    def test_post_message_fail(self, mock_post):
        mock_post.side_effect = Exception("Network Error")

        connector = DiscordConnector(self.config)
        result = connector.post_message("Hello Discord!")
        self.assertFalse(result)

    @patch("requests.post")
    def test_post_embed_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        connector = DiscordConnector(self.config)
        result = connector.post_embed(
            title="Test Title", 
            description="Test Description",
            color=0xff0000
        )
        self.assertTrue(result)
        # Check if json contains "embeds"
        call_args = mock_post.call_args
        self.assertIn("embeds", call_args.kwargs["json"])
        self.assertEqual(call_args.kwargs["json"]["embeds"][0]["title"], "Test Title")
