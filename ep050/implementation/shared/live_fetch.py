# epics/ep_050_distribution_engine/implementation/shared/live_fetch.py
# EP050 shared live-source fetch infrastructure, used by Nodes 05-10's automated ingestion path.
#
# VERSION HISTORY
# v1.3.0 · 2026-08-19 · Adds http_post_json() and resolve_firecrawl_credentials(), needed because
#   Node 05 had to change search provider: Google closed the Custom Search JSON API to new
#   customers (confirmed verbatim on developers.google.com/custom-search/v1/overview, with
#   service discontinuation set for 2027-01-01), so every call returned HTTP 403 "This project
#   does not have the access to Custom Search JSON API" regardless of project, key, or console
#   state -- proven by testing a brand-new GCP project with a fresh key and getting an identical
#   403. Firecrawl's search endpoint is POST-with-JSON rather than GET-with-query-string, hence
#   the new helper; its credential resolves from EP050_FIRECRAWL_API_KEY first, falling back to
#   the Firecrawl CLI's own stored credentials so the secret is read from where the user already
#   put it rather than duplicated into a second file. http_post_json() also surfaces the response
#   body on an HTTPError, which the existing helpers discard -- during the Google outage that
#   discarded body was the single most useful diagnostic and took a separate throwaway script to
#   recover; no future provider failure should require that again.
# v1.2.0 · 2026-08-18 · _load_dotenv_if_present() now checks the repo-root .env (eds/.env, where
#   ElevenLabs/Pexels/etc. credentials already live) FIRST, falling back to
#   epics/ep_050_distribution_engine/.env second -- the user confirmed they're adding EP050
#   credentials to the shared root file instead of the EP050-specific one, which the v1.1.0
#   loader never looked at. First path wins per-key, same as never overriding a real env var.
# v1.1.0 · 2026-08-18 · Adds _load_dotenv_if_present(), loading epics/ep_050_distribution_engine/
#   .env into os.environ at import time. Fixes a real bug found live: the .env file written
#   earlier this session had no loader anywhere, so EP050_LIVE_FETCH_ENABLED=1 and credentials
#   entered into it were silently ignored and every live-fetch call failed closed with
#   LiveFetchDisabledError regardless of what the file said. Never overrides a variable already
#   set in the real environment.
# v1.0.0 · 2026-08-17 · Initial version: opt-in gated, credential-driven live fetch helpers with
#   verifiable fetch receipts. Built to satisfy the user-mandated CORE REQUIREMENT (2026-08-17)
#   that Nodes 05-10 perform genuine automated, live acquisition of real demand data -- not
#   manual entry, and not an unverified source_type label change (see the reverted node_05
#   schema-only widening flagged on the agent message board, event 20260817T162311314).
#
# Safety model: every live fetch is OFF by default. A caller must set
# EP050_LIVE_FETCH_ENABLED=1 in the environment AND supply the relevant per-source credential
# env var before any network call is attempted. Missing either raises a typed, fail-closed
# error before any request is made -- this preserves the project's standing offline-by-default
# boundary; it does not silently start making live calls. Every successful fetch returns a
# FetchReceipt recording the real endpoint, HTTP status, timestamp and item count, so a
# record's source_type claim is independently verifiable, not just an unverified label.

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LIVE_FETCH_ENABLED_ENV = "EP050_LIVE_FETCH_ENABLED"
DEFAULT_TIMEOUT_SECONDS = 10
USER_AGENT = "EP050-DistributionEngine/1.0 (+demand-intelligence automated fetch; read-only)"


def parse_dotenv(text: str) -> dict[str, str]:
    """Pure KEY=value parser matching the .env file's own format: blank lines and lines starting
    with # are skipped, everything else is split on the first '='."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            values[key] = value
    return values


def _dotenv_search_paths() -> list[Path]:
    """Ordered candidates, first match wins per-key. The repo-root .env (shared across every
    epic -- ElevenLabs/Pexels/etc. already live there) is checked first since that's the user's
    stated primary credentials file; the EP050-specific .env is a fallback for anyone who still
    uses it standalone."""
    here = Path(__file__).resolve()
    return [
        here.parents[4] / ".env",  # repo root: eds/.env
        here.parents[2] / ".env",  # epics/ep_050_distribution_engine/.env
    ]


def _load_dotenv_if_present() -> None:
    """Loads .env files into os.environ, once, at import time, from _dotenv_search_paths().

    Writing EP050_LIVE_FETCH_ENABLED=1 and credentials into a .env file previously had no effect
    at all -- nothing read it, so os.environ.get() always saw them as unset regardless of what
    the file said, and every live-fetch call failed closed with LiveFetchDisabledError even
    after the file was filled in. No external dependency (python-dotenv isn't a guaranteed
    install here). A variable already set in the real environment, or already loaded from an
    earlier path in the search order, is never overridden -- `set EP050_X=...` before launching
    still takes precedence over any file, matching standard dotenv semantics.
    """
    for env_path in _dotenv_search_paths():
        if not env_path.exists():
            continue
        for key, value in parse_dotenv(env_path.read_text(encoding="utf-8")).items():
            if key not in os.environ:
                os.environ[key] = value


_load_dotenv_if_present()


class LiveFetchError(RuntimeError):
    """Base class for all live-fetch failures. Fail-closed: never returns partial/fabricated data."""


class LiveFetchDisabledError(LiveFetchError):
    """Raised when EP050_LIVE_FETCH_ENABLED is not set to '1'. This is the default state."""


class MissingCredentialError(LiveFetchError):
    """Raised when a required credential env var is not set."""


class LiveFetchRequestError(LiveFetchError):
    """Raised when the live HTTP request itself fails (network error, non-2xx status, bad payload)."""


@dataclass(frozen=True)
class FetchReceipt:
    """Verifiable proof that a live fetch actually happened, embedded in the resulting record's metadata."""

    endpoint: str
    http_status: int
    fetched_at: str
    item_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "http_status": self.http_status,
            "fetched_at": self.fetched_at,
            "item_count": self.item_count,
        }


def require_live_fetch_enabled() -> None:
    if os.environ.get(LIVE_FETCH_ENABLED_ENV) != "1":
        raise LiveFetchDisabledError(
            f"Live fetch is disabled by default. Set {LIVE_FETCH_ENABLED_ENV}=1 to enable it "
            "(fail-closed default; this repository never fetches live data unless explicitly opted in)."
        )


def require_credential(env_var: str) -> str:
    value = os.environ.get(env_var)
    if not value:
        raise MissingCredentialError(
            f"{env_var} is not set. Supply it in .env before live fetch can run for this source; "
            "credentials are always user-supplied, never entered or generated automatically."
        )
    return value


def http_get_json(
    url: str, *, headers: dict[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> tuple[Any, int]:
    """Perform a single read-only HTTP GET and parse the response as JSON. Fail-closed on any error."""
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit https callers only
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise LiveFetchRequestError(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise LiveFetchRequestError(f"Network error fetching {url}: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiveFetchRequestError(f"Non-JSON response from {url}") from exc
    return payload, status


def http_get_text(
    url: str, *, headers: dict[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> tuple[str, int]:
    """Perform a single read-only HTTP GET and return raw text. Fail-closed on any error."""
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit https callers only
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise LiveFetchRequestError(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise LiveFetchRequestError(f"Network error fetching {url}: {exc.reason}") from exc
    return raw, status


def http_post_json(
    url: str, *, body: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> tuple[Any, int]:
    """Perform a single POST with a JSON body, parse the response as JSON. Fail-closed on any error.

    Added for providers whose search endpoint is POST-with-JSON rather than GET-with-query-string
    (Firecrawl's /v2/search is the first such caller). Deliberately separate from http_post_form():
    the two encode their bodies differently and share no code path, so a change to one cannot
    silently alter the other.
    """
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json", "Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    payload_bytes = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=payload_bytes, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit https callers only
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:  # noqa: BLE001 - diagnostic best-effort only, never masks the original failure
            detail = ""
        suffix = f": {detail}" if detail.strip() else ""
        raise LiveFetchRequestError(f"HTTP {exc.code} posting to {url}: {exc.reason}{suffix}") from exc
    except urllib.error.URLError as exc:
        raise LiveFetchRequestError(f"Network error posting to {url}: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiveFetchRequestError(f"Non-JSON response from {url}") from exc
    return payload, status


FIRECRAWL_API_KEY_ENV = "EP050_FIRECRAWL_API_KEY"
FIRECRAWL_CLI_CREDENTIALS_PATH = Path(os.environ.get("APPDATA", "")) / "firecrawl-cli" / "credentials.json"
DEFAULT_FIRECRAWL_API_URL = "https://api.firecrawl.dev"


def resolve_firecrawl_credentials() -> tuple[str, str]:
    """Return (api_key, api_url) for Firecrawl, or raise MissingCredentialError fail-closed.

    Resolution order, first hit wins:
      1. EP050_FIRECRAWL_API_KEY in the environment (or .env, loaded above) -- the explicit,
         project-owned credential, consistent with every other source in this module.
      2. The Firecrawl CLI's own stored credentials file, written when the user ran
         `firecrawl config` themselves.

    The CLI fallback exists so the key is not duplicated into a second file: it is still a
    user-supplied credential (the user authenticated the CLI), it is simply read from where the
    user already put it rather than copied. Nothing here ever generates or requests a credential.
    """
    env_key = os.environ.get(FIRECRAWL_API_KEY_ENV)
    if env_key:
        return env_key, os.environ.get("EP050_FIRECRAWL_API_URL") or DEFAULT_FIRECRAWL_API_URL

    if FIRECRAWL_CLI_CREDENTIALS_PATH.exists():
        try:
            stored = json.loads(FIRECRAWL_CLI_CREDENTIALS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MissingCredentialError(
                f"{FIRECRAWL_API_KEY_ENV} is not set and the Firecrawl CLI credentials at "
                f"{FIRECRAWL_CLI_CREDENTIALS_PATH} could not be read: {exc}"
            ) from exc
        api_key = stored.get("apiKey")
        if api_key:
            return api_key, stored.get("apiUrl") or DEFAULT_FIRECRAWL_API_URL

    raise MissingCredentialError(
        f"{FIRECRAWL_API_KEY_ENV} is not set and no Firecrawl CLI credentials were found at "
        f"{FIRECRAWL_CLI_CREDENTIALS_PATH}. Either add {FIRECRAWL_API_KEY_ENV}=... to .env or run "
        "`firecrawl config` to authenticate the CLI; credentials are always user-supplied, never "
        "entered or generated automatically."
    )


def http_post_form(
    url: str, *, data: dict[str, str], headers: dict[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> tuple[Any, int]:
    """Perform a single POST with form-encoded body, parse the response as JSON. Used for OAuth token exchange."""
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    body = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit https callers only
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise LiveFetchRequestError(f"HTTP {exc.code} posting to {url}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise LiveFetchRequestError(f"Network error posting to {url}: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiveFetchRequestError(f"Non-JSON response from {url}") from exc
    return payload, status


def make_receipt(endpoint: str, http_status: int, item_count: int) -> FetchReceipt:
    return FetchReceipt(
        endpoint=endpoint,
        http_status=http_status,
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        item_count=item_count,
    )
