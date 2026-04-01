import logging
import os
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Optional

import tweepy

from src.models.TwitterAuth import TwitterConfig


class TwitterConnector:
    def __init__(self, config: TwitterConfig):
        self.config = config
        self.client = tweepy.Client(
            bearer_token=config.auth.bearer_token,
            consumer_key=config.auth.api_key,
            consumer_secret=config.auth.api_secret,
            access_token=config.auth.access_token,
            access_token_secret=config.auth.access_secret,
            wait_on_rate_limit=True,
        )

        auth = tweepy.OAuth1UserHandler(
            config.auth.api_key,
            config.auth.api_secret,
            config.auth.access_token,
            config.auth.access_secret,
        )
        self.api_v1 = tweepy.API(auth)
        self.logger = logging.getLogger("twitter_connector")
        self._setup_logger()
        self.request_timestamps: deque[datetime] = deque()
        self.queued_requests: deque[dict[str, Any]] = deque()
        self.posted_tweet_ids: list[str] = []

    def _setup_logger(self) -> None:
        os.makedirs("logs", exist_ok=True)
        if not self.logger.handlers:
            handler = logging.FileHandler("logs/twitter_api.log")
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _prune_rate_limit_window(self) -> None:
        cutoff = self._now() - timedelta(minutes=self.config.window_minutes)
        while self.request_timestamps and self.request_timestamps[0] <= cutoff:
            self.request_timestamps.popleft()

    def _consume_rate_limit_slot(self) -> bool:
        self._prune_rate_limit_window()
        if len(self.request_timestamps) >= self.config.max_tweets_per_window:
            return False
        self.request_timestamps.append(self._now())
        return True

    def _enqueue_request(self, request_type: str, payload: dict[str, Any]) -> None:
        self.queued_requests.append({"type": request_type, "payload": payload})
        self.logger.warning(
            "Rate limit reached. Queued %s request. Queue size=%s",
            request_type,
            len(self.queued_requests),
        )

    def _extract_tweet_id(self, response: Any) -> Optional[str]:
        if not response or not getattr(response, "data", None):
            return None
        tweet_id = response.data.get("id")
        return str(tweet_id) if tweet_id is not None else None

    def _record_posted_tweet(self, tweet_id: str) -> str:
        self.posted_tweet_ids.append(tweet_id)
        return tweet_id

    def _execute_with_retries(self, action: Callable[[], Any], operation_name: str) -> Any:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                return action()
            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    "Twitter operation %s failed on attempt %s/%s: %s",
                    operation_name,
                    attempt,
                    self.config.max_retries,
                    str(exc),
                )
                if attempt == self.config.max_retries:
                    break
                time.sleep(self.config.retry_backoff_seconds)

        if last_error is not None:
            raise last_error
        return None

    def verify_auth(self) -> bool:
        try:
            me = self.client.get_me()
            if me and me.data:
                self.logger.info("Successfully authenticated as %s", me.data.username)
                return True
            return False
        except Exception as exc:
            self.logger.error("Authentication failed: %s", str(exc))
            return False

    def post_text(self, text: str) -> Optional[str]:
        if len(text) > self.config.max_tweet_length:
            self.logger.error("Tweet exceeds %s characters", self.config.max_tweet_length)
            return None
        if not self._consume_rate_limit_slot():
            self._enqueue_request("text", {"text": text})
            return None

        try:
            response = self._execute_with_retries(
                lambda: self.client.create_tweet(text=text),
                "post_text",
            )
            tweet_id = self._extract_tweet_id(response)
            if tweet_id:
                self.logger.info("Successfully posted tweet: %s", tweet_id)
                return self._record_posted_tweet(tweet_id)
            return None
        except Exception as exc:
            self.logger.error("Failed to post tweet: %s", str(exc))
            return None

    def post_media(self, text: str, media_paths: list[str]) -> Optional[str]:
        if len(text) > self.config.max_tweet_length:
            self.logger.error("Tweet exceeds %s characters", self.config.max_tweet_length)
            return None
        if not media_paths or len(media_paths) > self.config.max_media_per_tweet:
            self.logger.error(
                "Media tweet requires between 1 and %s media items",
                self.config.max_media_per_tweet,
            )
            return None
        if not self._consume_rate_limit_slot():
            self._enqueue_request("media", {"text": text, "media_paths": list(media_paths)})
            return None

        try:
            media_ids = []
            for path in media_paths:
                media = self._execute_with_retries(
                    lambda path=path: self.api_v1.media_upload(path),
                    f"media_upload:{path}",
                )
                media_ids.append(media.media_id)

            response = self._execute_with_retries(
                lambda: self.client.create_tweet(text=text, media_ids=media_ids),
                "post_media",
            )
            tweet_id = self._extract_tweet_id(response)
            if tweet_id:
                self.logger.info("Successfully posted tweet with media: %s", tweet_id)
                return self._record_posted_tweet(tweet_id)
            return None
        except Exception as exc:
            self.logger.error("Failed to post tweet with media: %s", str(exc))
            return None

    def post_thread(self, tweets: list[str]) -> Optional[list[str]]:
        if not tweets:
            self.logger.error("Thread posting requires at least one tweet")
            return None
        if any(len(tweet_text) > self.config.max_tweet_length for tweet_text in tweets):
            self.logger.error("Thread tweet exceeds %s characters", self.config.max_tweet_length)
            return None

        try:
            previous_tweet_id = None
            tweet_ids: list[str] = []

            for index, tweet_text in enumerate(tweets):
                if not self._consume_rate_limit_slot():
                    self._enqueue_request("thread", {"tweets": tweets[index:]})
                    return tweet_ids
                if previous_tweet_id:
                    response = self._execute_with_retries(
                        lambda text=tweet_text, reply_to=previous_tweet_id: self.client.create_tweet(
                            text=text,
                            in_reply_to_tweet_id=reply_to,
                        ),
                        "post_thread_reply",
                    )
                else:
                    response = self._execute_with_retries(
                        lambda text=tweet_text: self.client.create_tweet(text=text),
                        "post_thread_root",
                    )

                current_tweet_id = self._extract_tweet_id(response)
                if not current_tweet_id:
                    self.logger.error("Thread posting interrupted at tweet")
                    return tweet_ids

                previous_tweet_id = current_tweet_id
                self._record_posted_tweet(current_tweet_id)
                tweet_ids.append(current_tweet_id)

            self.logger.info("Successfully posted thread: %s", tweet_ids)
            return tweet_ids
        except Exception as exc:
            self.logger.error("Failed to post thread: %s", str(exc))
            return None

    def flush_queue(self) -> int:
        processed = 0
        while self.queued_requests:
            self._prune_rate_limit_window()
            if len(self.request_timestamps) >= self.config.max_tweets_per_window:
                break

            queued_request = self.queued_requests.popleft()
            request_type = queued_request["type"]
            payload = queued_request["payload"]

            if request_type == "text":
                self.post_text(payload["text"])
            elif request_type == "media":
                self.post_media(payload["text"], payload["media_paths"])
            elif request_type == "thread":
                self.post_thread(payload["tweets"])
            else:
                self.logger.error("Unknown queued Twitter request type: %s", request_type)
                continue

            processed += 1

        self.logger.info("Flushed %s queued Twitter requests", processed)
        return processed

    def check_rate_limit(self, endpoint: str) -> bool:
        try:
            self._prune_rate_limit_window()
            remaining = self.config.max_tweets_per_window - len(self.request_timestamps)
            self.logger.info(
                "Checking rate limit status for %s. Remaining=%s, queued=%s",
                endpoint,
                remaining,
                len(self.queued_requests),
            )
            return True
        except Exception as exc:
            self.logger.error("Error checking rate limit: %s", str(exc))
            return False
