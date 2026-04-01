import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from src.connectors.twitterConnector import TwitterConnector
from src.models.TwitterAuth import TwitterAuth, TwitterConfig


class TestTwitterPostText(unittest.TestCase):
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
    def test_post_text_success(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_response = MagicMock()
        mock_response.data = {"id": "12345"}
        mock_client.create_tweet.return_value = mock_response

        connector = TwitterConnector(self.config)
        tweet_id = connector.post_text("Hello Twitter!")
        self.assertEqual(tweet_id, "12345")
        mock_client.create_tweet.assert_called_with(text="Hello Twitter!")

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_post_text_fail(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.create_tweet.side_effect = Exception("API Error")

        connector = TwitterConnector(self.config)
        tweet_id = connector.post_text("Hello Twitter!")
        self.assertIsNone(tweet_id)

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_post_text_tracks_posted_id(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_response = MagicMock()
        mock_response.data = {"id": "12345"}
        mock_client.create_tweet.return_value = mock_response

        connector = TwitterConnector(self.config)
        connector.post_text("Track me")

        self.assertEqual(connector.posted_tweet_ids, ["12345"])

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_post_text_rejects_too_long_tweet(self, mock_api, mock_oauth, mock_client_class):
        connector = TwitterConnector(self.config)

        tweet_id = connector.post_text("x" * 281)

        self.assertIsNone(tweet_id)
        mock_client_class.return_value.create_tweet.assert_not_called()

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_post_text_queues_when_rate_limit_reached(self, mock_api, mock_oauth, mock_client_class):
        connector = TwitterConnector(self.config)
        now = connector._now()
        connector.request_timestamps.extend(
            [now - timedelta(minutes=1)] * connector.config.max_tweets_per_window
        )

        tweet_id = connector.post_text("Queued tweet")

        self.assertIsNone(tweet_id)
        self.assertEqual(len(connector.queued_requests), 1)
        mock_client_class.return_value.create_tweet.assert_not_called()

    @patch("tweepy.Client")
    @patch("tweepy.OAuth1UserHandler")
    @patch("tweepy.API")
    def test_post_text_retries_transient_failure(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_response = MagicMock()
        mock_response.data = {"id": "2001"}
        mock_client.create_tweet.side_effect = [Exception("Temporary error"), mock_response]

        config = TwitterConfig(auth=self.config.auth, retry_backoff_seconds=0)
        connector = TwitterConnector(config)

        tweet_id = connector.post_text("Retry me")

        self.assertEqual(tweet_id, "2001")
        self.assertEqual(mock_client.create_tweet.call_count, 2)
