# epics/ep_050_distribution_engine/implementation/shared/test_live_fetch.py
# EP050 shared — live_fetch test suite.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-18 · Adds test_dotenv_search_paths_checks_repo_root_before_ep050_specific_file,
#   covering the v1.2.0 change that checks the repo-root .env before the EP050-specific one.
# v1.0.0 · 2026-08-18 · Initial suite, covering parse_dotenv() -- added after the .env file
#   written earlier this session turned out to have no loader anywhere, so real credentials
#   entered into it were silently ignored (LiveFetchDisabledError regardless of file content).
#
# All tests are pure/offline -- no network, no filesystem beyond what pytest tmp_path provides.

from __future__ import annotations

from pathlib import Path

from live_fetch import _dotenv_search_paths, parse_dotenv


def test_parse_dotenv_reads_simple_key_value_pairs():
    text = "EP050_LIVE_FETCH_ENABLED=1\nEP050_GOOGLE_CSE_API_KEY=abc123\n"
    assert parse_dotenv(text) == {"EP050_LIVE_FETCH_ENABLED": "1", "EP050_GOOGLE_CSE_API_KEY": "abc123"}


def test_parse_dotenv_skips_comments_and_blank_lines():
    text = "# a comment\n\nEP050_LIVE_FETCH_ENABLED=1\n   \n# another\nEP050_YOUTUBE_API_KEY=xyz\n"
    assert parse_dotenv(text) == {"EP050_LIVE_FETCH_ENABLED": "1", "EP050_YOUTUBE_API_KEY": "xyz"}


def test_parse_dotenv_skips_lines_with_no_equals_sign():
    text = "EP050_LIVE_FETCH_ENABLED=1\nnot a valid line\nEP050_YOUTUBE_API_KEY=xyz\n"
    assert parse_dotenv(text) == {"EP050_LIVE_FETCH_ENABLED": "1", "EP050_YOUTUBE_API_KEY": "xyz"}


def test_parse_dotenv_treats_empty_value_as_unset_but_present_key():
    text = "EP050_GOOGLE_CSE_API_KEY=\n"
    assert parse_dotenv(text) == {"EP050_GOOGLE_CSE_API_KEY": ""}


def test_parse_dotenv_strips_surrounding_whitespace():
    text = "  EP050_LIVE_FETCH_ENABLED = 1  \n"
    assert parse_dotenv(text) == {"EP050_LIVE_FETCH_ENABLED": "1"}


def test_parse_dotenv_returns_empty_dict_for_empty_text():
    assert parse_dotenv("") == {}


def test_parse_dotenv_matches_the_real_env_file_shape():
    # Mirrors epics/ep_050_distribution_engine/.env's actual structure -- comment header,
    # section comments, blank separators, and a mix of filled/empty values.
    text = (
        "# EP050 Distribution Engine — live fetch credentials\n"
        "# Fail-closed: every value below is unset by default.\n\n"
        "EP050_LIVE_FETCH_ENABLED=0\n\n"
        "# Node 05\n"
        "EP050_GOOGLE_CSE_API_KEY=\n"
        "EP050_GOOGLE_CSE_CX=\n\n"
        "# Node 09\n"
        "EP050_REDDIT_CLIENT_ID=\n"
        "EP050_REDDIT_CLIENT_SECRET=\n"
        "EP050_REDDIT_USER_AGENT=\n"
    )
    result = parse_dotenv(text)
    assert result["EP050_LIVE_FETCH_ENABLED"] == "0"
    assert result["EP050_GOOGLE_CSE_API_KEY"] == ""
    assert set(result.keys()) == {
        "EP050_LIVE_FETCH_ENABLED", "EP050_GOOGLE_CSE_API_KEY", "EP050_GOOGLE_CSE_CX",
        "EP050_REDDIT_CLIENT_ID", "EP050_REDDIT_CLIENT_SECRET", "EP050_REDDIT_USER_AGENT",
    }


def test_dotenv_search_paths_checks_repo_root_before_ep050_specific_file():
    # The user confirmed they add EP050 credentials to the shared repo-root .env (where
    # ElevenLabs/Pexels/etc. already live) rather than the EP050-specific one -- root must be
    # checked first so it takes priority per the "first path wins" load order.
    paths = _dotenv_search_paths()
    assert len(paths) == 2
    assert all(isinstance(p, Path) for p in paths)
    assert paths[0].name == ".env"
    assert paths[1].name == ".env"
    assert paths[0] != paths[1]
    # Accepts either the canonical local epic folder name or the "ep050" name used by the
    # release-packaged deploy copy (see epics/ep_050_distribution_engine/render.yaml) -- both
    # layouts preserve the same relative depth, only the top-level folder name differs.
    assert paths[1].parent.name in ("ep_050_distribution_engine", "ep050")
    assert paths[0].parent.name not in ("ep_050_distribution_engine", "ep050")
