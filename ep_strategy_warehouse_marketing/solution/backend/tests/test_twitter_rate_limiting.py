import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from src.connectors.twitterConnector import TwitterConnector
from src.models.TwitterAuth import TwitterAuth, TwitterConfig


class TestTwitterRateLimiting(unittest.TestCase):
    def setUp(self):
        auth = TwitterAuth(
            api_key="key",
            api_secret="secret",
            access_token="token",
            access_secret="access_secret",
        )
        self.config = TwitterConfig(auth=auth)

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_rate_limit_check(self, mock_api, mock_oauth, mock_client_class):
        connector = TwitterConnector(self.config)
        self.assertTrue(connector.check_rate_limit("create_tweet"))

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_flush_queue_processes_queued_text_post_when_window_clears(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_response = MagicMock()
        mock_response.data = {"id": "3001"}
        mock_client.create_tweet.return_value = mock_response

        connector = TwitterConnector(self.config)
        connector.queued_requests.append({"type": "text", "payload": {"text": "Queued tweet"}})
        connector.request_timestamps.extend(
            [connector._now() - timedelta(minutes=connector.config.window_minutes + 1)]
            * connector.config.max_tweets_per_window
        )

        processed = connector.flush_queue()

        self.assertEqual(processed, 1)
        self.assertEqual(connector.posted_tweet_ids, ["3001"])
        mock_client.create_tweet.assert_called_once_with(text="Queued tweet")
