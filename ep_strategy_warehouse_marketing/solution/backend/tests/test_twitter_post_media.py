import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from src.connectors.twitterConnector import TwitterConnector
from src.models.TwitterAuth import TwitterAuth, TwitterConfig


class TestTwitterPostMedia(unittest.TestCase):
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
    def test_post_media_success(self, mock_api_class, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_api = mock_api_class.return_value

        mock_media = MagicMock()
        mock_media.media_id = "67890"
        mock_api.media_upload.return_value = mock_media

        mock_response = MagicMock()
        mock_response.data = {"id": "12345"}
        mock_client.create_tweet.return_value = mock_response

        connector = TwitterConnector(self.config)
        tweet_id = connector.post_media("Hello Media!", ["path/to/image.png"])

        self.assertEqual(tweet_id, "12345")
        mock_api.media_upload.assert_called_with("path/to/image.png")
        mock_client.create_tweet.assert_called_with(text="Hello Media!", media_ids=["67890"])

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_post_media_fail(self, mock_api_class, mock_oauth, mock_client_class):
        mock_api = mock_api_class.return_value
        mock_api.media_upload.side_effect = Exception("Upload Error")

        connector = TwitterConnector(self.config)
        tweet_id = connector.post_media("Hello Media!", ["path/to/image.png"])
        self.assertIsNone(tweet_id)

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_post_media_rejects_more_than_four_attachments(self, mock_api_class, mock_oauth, mock_client_class):
        connector = TwitterConnector(self.config)

        tweet_id = connector.post_media("Too much media", ["1.png", "2.png", "3.png", "4.png", "5.png"])

        self.assertIsNone(tweet_id)
        mock_api_class.return_value.media_upload.assert_not_called()
        mock_client_class.return_value.create_tweet.assert_not_called()

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_post_media_queues_when_rate_limit_reached(self, mock_api_class, mock_oauth, mock_client_class):
        connector = TwitterConnector(self.config)
        now = connector._now()
        connector.request_timestamps.extend(
            [now - timedelta(minutes=1)] * connector.config.max_tweets_per_window
        )

        tweet_id = connector.post_media("Queued media", ["path/to/image.png"])

        self.assertIsNone(tweet_id)
        self.assertEqual(len(connector.queued_requests), 1)
        mock_api_class.return_value.media_upload.assert_not_called()
