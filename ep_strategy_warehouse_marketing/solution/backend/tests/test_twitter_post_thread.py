import unittest
from unittest.mock import MagicMock, patch
from src.models.TwitterAuth import TwitterAuth, TwitterConfig
from src.connectors.twitterConnector import TwitterConnector

class TestTwitterPostThread(unittest.TestCase):
    def setUp(self):
        auth = TwitterAuth(
            api_key='key',
            api_secret='secret',
            access_token='token',
            access_secret='access_secret'
        )
        self.config = TwitterConfig(auth=auth)

    @patch('tweepy.Client')
    @patch('tweepy.OAuth1UserHandler')
    @patch('tweepy.API')
    def test_post_thread_success(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        
        mock_response1 = MagicMock()
        mock_response1.data = {'id': '1001'}
        mock_response2 = MagicMock()
        mock_response2.data = {'id': '1002'}
        
        mock_client.create_tweet.side_effect = [mock_response1, mock_response2]

        connector = TwitterConnector(self.config)
        tweet_ids = connector.post_thread(['First tweet', 'Second tweet'])
        
        self.assertEqual(tweet_ids, ['1001', '1002'])
        mock_client.create_tweet.assert_any_call(text='First tweet')
        mock_client.create_tweet.assert_any_call(text='Second tweet', in_reply_to_tweet_id='1001')

    @patch('tweepy.Client')
    @patch('tweepy.OAuth1UserHandler')
    @patch('tweepy.API')
    def test_post_thread_fail(self, mock_api, mock_oauth, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.create_tweet.side_effect = Exception('API Error')

        connector = TwitterConnector(self.config)
        tweet_ids = connector.post_thread(['First', 'Second'])
        self.assertIsNone(tweet_ids)
