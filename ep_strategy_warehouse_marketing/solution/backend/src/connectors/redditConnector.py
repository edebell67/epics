import praw
import logging
import os
from typing import Optional, List
from src.models.RedditAuth import RedditAuth, RedditConfig

class RedditConnector:
    def __init__(self, config: RedditConfig):
        self.config = config
        self.reddit = praw.Reddit(
            client_id=config.auth.client_id,
            client_secret=config.auth.client_secret,
            user_agent=config.auth.user_agent,
            username=config.auth.username,
            password=config.auth.password
        )
        self.logger = logging.getLogger("reddit_connector")
        self._setup_logger()

    def _setup_logger(self):
        os.makedirs("logs", exist_ok=True)
        handler = logging.FileHandler("logs/reddit_api.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def verify_auth(self) -> bool:
        try:
            user = self.reddit.user.me()
            if user:
                self.logger.info(f"Successfully authenticated as u/{user.name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False

    def check_karma_requirements(self, min_karma: int = 10) -> bool:
        try:
            user = self.reddit.user.me()
            total_karma = user.link_karma + user.comment_karma
            self.logger.info(f"User u/{user.name} has {total_karma} total karma")
            if total_karma < min_karma:
                self.logger.warning(f"Karma ({total_karma}) is below recommended minimum ({min_karma})")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to check karma: {str(e)}")
            return False

    def post_text(self, title: str, text: str, subreddit_name: Optional[str] = None) -> Optional[str]:
        try:
            subreddit_name = subreddit_name or self.config.default_subreddit
            subreddit = self.reddit.subreddit(subreddit_name)
            submission = subreddit.submit(title, selftext=text)
            self.logger.info(f"Successfully posted text to r/{subreddit_name}: {submission.id}")
            return submission.id
        except Exception as e:
            self.logger.error(f"Failed to post text to r/{subreddit_name}: {str(e)}")
            return None

    def post_link(self, title: str, url: str, subreddit_name: Optional[str] = None) -> Optional[str]:
        try:
            subreddit_name = subreddit_name or self.config.default_subreddit
            subreddit = self.reddit.subreddit(subreddit_name)
            submission = subreddit.submit(title, url=url)
            self.logger.info(f"Successfully posted link to r/{subreddit_name}: {submission.id}")
            return submission.id
        except Exception as e:
            self.logger.error(f"Failed to post link to r/{subreddit_name}: {str(e)}")
            return None

    def post_image(self, title: str, image_path: str, subreddit_name: Optional[str] = None) -> Optional[str]:
        try:
            subreddit_name = subreddit_name or self.config.default_subreddit
            subreddit = self.reddit.subreddit(subreddit_name)
            submission = subreddit.submit_image(title, image_path)
            self.logger.info(f"Successfully posted image to r/{subreddit_name}: {submission.id}")
            return submission.id
        except Exception as e:
            self.logger.error(f"Failed to post image to r/{subreddit_name}: {str(e)}")
            return None

    def post_comment(self, submission_id: str, text: str) -> Optional[str]:
        try:
            submission = self.reddit.submission(id=submission_id)
            comment = submission.reply(text)
            self.logger.info(f"Successfully posted comment to submission {submission_id}: {comment.id}")
            return comment.id
        except Exception as e:
            self.logger.error(f"Failed to post comment to submission {submission_id}: {str(e)}")
            return None

    def handle_rate_limit(self, func, *args, **kwargs):
        # PRAW handles rate limits automatically if configured, 
        # but we can add custom retry logic here if needed.
        # For now, we rely on PRAW's internal handling and our error logging.
        pass
