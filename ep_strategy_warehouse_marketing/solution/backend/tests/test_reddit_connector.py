import unittest
from unittest.mock import MagicMock, patch
from src.models.RedditAuth import RedditAuth, RedditConfig
from src.connectors.redditConnector import RedditConnector

class TestRedditConnector(unittest.TestCase):
    def setUp(self):
        auth = RedditAuth(
            client_id='test_id',
            client_secret='test_secret',
            user_agent='test_agent',
            username='test_user',
            password='test_password'
        )
        self.config = RedditConfig(auth=auth)

    @patch('praw.Reddit')
    def test_verify_auth_success(self, mock_reddit_class):
        mock_reddit = mock_reddit_class.return_value
        mock_user = MagicMock()
        mock_user.name = 'test_user'
        mock_reddit.user.me.return_value = mock_user

        connector = RedditConnector(self.config)
        self.assertTrue(connector.verify_auth())
        mock_reddit.user.me.assert_called_once()

    @patch('praw.Reddit')
    def test_post_text_success(self, mock_reddit_class):
        mock_reddit = mock_reddit_class.return_value
        mock_subreddit = MagicMock()
        mock_submission = MagicMock()
        mock_submission.id = 'abc123'
        mock_subreddit.submit.return_value = mock_submission
        mock_reddit.subreddit.return_value = mock_subreddit

        connector = RedditConnector(self.config)
        post_id = connector.post_text('Title', 'Content', 'test_sub')
        self.assertEqual(post_id, 'abc123')
        mock_reddit.subreddit.assert_called_with('test_sub')
        mock_subreddit.submit.assert_called_with('Title', selftext='Content')

    @patch('praw.Reddit')
    def test_post_comment_success(self, mock_reddit_class):
        mock_reddit = mock_reddit_class.return_value
        mock_submission = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = 'xyz789'
        mock_submission.reply.return_value = mock_comment
        mock_reddit.submission.return_value = mock_submission

        connector = RedditConnector(self.config)
        comment_id = connector.post_comment('abc123', 'Nice post!')
        self.assertEqual(comment_id, 'xyz789')
        mock_reddit.submission.assert_called_with(id='abc123')
        mock_submission.reply.assert_called_with('Nice post!')

    @patch('praw.Reddit')
    def test_check_karma_success(self, mock_reddit_class):
        mock_reddit = mock_reddit_class.return_value
        mock_user = MagicMock()
        mock_user.link_karma = 50
        mock_user.comment_karma = 50
        mock_reddit.user.me.return_value = mock_user

        connector = RedditConnector(self.config)
        self.assertTrue(connector.check_karma_requirements(min_karma=10))

    @patch('praw.Reddit')
    def test_check_karma_low(self, mock_reddit_class):
        mock_reddit = mock_reddit_class.return_value
        mock_user = MagicMock()
        mock_user.link_karma = 1
        mock_user.comment_karma = 1
        mock_reddit.user.me.return_value = mock_user

        connector = RedditConnector(self.config)
        self.assertFalse(connector.check_karma_requirements(min_karma=10))
