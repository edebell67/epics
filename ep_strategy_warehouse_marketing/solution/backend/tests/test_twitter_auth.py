import unittest
from src.models.TwitterAuth import TwitterAuth

class TestTwitterAuth(unittest.TestCase):
    def test_auth_model_init(self):
        auth = TwitterAuth(
            api_key="key123",
            api_secret="secret123",
            access_token="token123",
            access_secret="access_secret123"
        )
        self.assertEqual(auth.api_key, "key123")
        self.assertEqual(auth.api_secret, "secret123")

    def test_missing_fields(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            TwitterAuth(api_key="only_key")
