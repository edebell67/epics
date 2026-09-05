"""Owner-instructed intelligence agent.

Closes the loop the owner workspace UI already half-implies: the owner
writes free-text guidance into the existing Feedback box ("Share guidance
or ask for an update..."); this agent polls its own feedback inbox
(GET /v1/me/feedback - already-existing Arena API, no new endpoint needed),
interprets that free text into a query against the real intelligence
provider (POST /v1/queries on the DNA Strategy Directory, built earlier
today), submits it as the agent (POST /participant/v1/me/queries so the
$0.01 fee/receipt flow is exercised for real), then acknowledges the
feedback and replies with a plain-English summary of what it queried and
found - visible to the owner in the same Feedback history panel.

Both base URLs are CLI/env-driven, never hardcoded to localhost: this
Arena and directory are both slated for a real hosted deployment later, so
nothing here should need editing when that happens - only --arena-url/
--directory-url (or ARENA_BASE_URL/DIRECTORY_BASE_URL) change.

VERSION HISTORY
v1.0.0 - Initial: rule-based instruction interpreter (no external LLM
dependency - deterministic, unit-testable, same tolerant-fallback spirit
as arena_provider.py's own unrecognized-kind handling), single-pass and
polling-loop modes.
"""
from __future__ import annotations
import argparse, json, os, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx

KIND_KEYWORDS = [
    (re.compile(r"\b(drawdown|safe|safest|risk.?averse|low.risk)\b", re.I), "low_drawdown"),
    (re.compile(r"\b(win.?rate|consistent|reliable|steady)\b", re.I), "high_win_rate"),
    (re.compile(r"\b(perform\w*|profit\w*|return\w*|gain\w*)\b", re.I), "top_performers"),
    (re.compile(r"\b(quality|overall|balanced)\b", re.I), "quality"),
]
LIMIT_RE = re.compile(r"\btop\s+(\d+)\b|\b(\d+)\s+strateg", re.I)
STRATEGY_ID_RE = re.compile(r"\bDNA_\d+\b")
WINDOW_KEYWORDS = [
    (re.compile(r"\btoday\b", re.I), lambda now: (now.replace(hour=0, minute=0, second=0, microsecond=0), now)),
    (re.compile(r"\bthis week\b", re.I), lambda now: (now - timedelta(days=7), now)),
    (re.compile(r"\blast (\d+) hours?\b", re.I), None),  # handled separately, needs the captured number
    (re.compile(r"\blast (\d+) days?\b", re.I), None),
]
DEFAULT_KIND = "quality"
DEFAULT_LIMIT = 5


def interpret_instruction(text: str, now: datetime | None = None) -> dict:
    """Rule-based, deterministic translation of an owner's free-text
    instruction into ArenaQueryRequest fields. Never raises and never
    produces an unusable request - an instruction that matches nothing
    falls back to the provider's own default (quality, no window, limit 5),
    same tolerant spirit as arena_provider.py's unrecognized-kind handling."""
    now = now or datetime.now(timezone.utc)
    kind = DEFAULT_KIND
    for pattern, name in KIND_KEYWORDS:
        if pattern.search(text):
            kind = name
            break
    limit = DEFAULT_LIMIT
    limit_match = LIMIT_RE.search(text)
    if limit_match:
        limit = int(limit_match.group(1) or limit_match.group(2))
    strategy_ids = sorted(set(STRATEGY_ID_RE.findall(text)))
    window_start = window_end = None
    hours_match = re.search(r"\blast (\d+) hours?\b", text, re.I)
    days_match = re.search(r"\blast (\d+) days?\b", text, re.I)
    if hours_match:
        window_start, window_end = now - timedelta(hours=int(hours_match.group(1))), now
    elif days_match:
        window_start, window_end = now - timedelta(days=int(days_match.group(1))), now
    elif re.search(r"\btoday\b", text, re.I):
        window_start, window_end = now.replace(hour=0, minute=0, second=0, microsecond=0), now
    elif re.search(r"\bthis week\b", text, re.I):
        window_start, window_end = now - timedelta(days=7), now
    return {"kind": kind, "limit": limit, "strategy_ids": strategy_ids,
            "window_start": window_start.isoformat() if window_start else None,
            "window_end": window_end.isoformat() if window_end else None}


def summarize(interpreted: dict, delivery: dict) -> str:
    window = ""
    if interpreted["window_start"] or interpreted["window_end"]:
        window = f" over [{interpreted['window_start'] or 'inception'}, {interpreted['window_end'] or 'now'}]"
    ids = delivery["strategy_ids"]
    listing = ", ".join(ids) if ids else "no matching strategies"
    return (f"Understood as: kind='{interpreted['kind']}', limit={interpreted['limit']}{window}. "
            f"Queried the real intelligence provider and found: {listing}. {delivery.get('notice', '')}")


def run_once(arena_url: str, arena_token: str, cursor_path: Path) -> int:
    """Poll for new feedback since the last processed cursor, interpret and
    query for each, ack + reply. Returns the count processed."""
    cursor = json.loads(cursor_path.read_text())["cursor"] if cursor_path.exists() else 0
    headers = {"Authorization": f"Bearer {arena_token}"}
    with httpx.Client(timeout=30) as client:
        feedback = client.get(f"{arena_url}/v1/me/feedback", params={"after": cursor}, headers=headers)
        feedback.raise_for_status()
        payload = feedback.json()
        processed = 0
        for item in payload["items"]:
            interpreted = interpret_instruction(item["message"])
            query_body = {"request_id": str(uuid4()), "kind": interpreted["kind"], "limit": interpreted["limit"]}
            if interpreted["strategy_ids"]:
                query_body["strategy_ids"] = interpreted["strategy_ids"]
            if interpreted["window_start"]:
                query_body["window_start"] = interpreted["window_start"]
            if interpreted["window_end"]:
                query_body["window_end"] = interpreted["window_end"]
            query_response = client.post(f"{arena_url}/participant/v1/me/queries", json=query_body, headers=headers)
            if query_response.status_code == 200:
                delivery = query_response.json()["delivery"]
                message = summarize(interpreted, delivery)
            else:
                message = f"Could not complete that query ({query_response.status_code}): {query_response.text[:300]}"
            client.post(f"{arena_url}/v1/me/feedback/{item['id']}/ack", headers=headers)
            client.post(f"{arena_url}/v1/me/feedback/{item['id']}/responses",
                        json={"request_id": str(uuid4()), "message": message[:2000]}, headers=headers)
            processed += 1
        cursor_path.write_text(json.dumps({"cursor": payload.get("next_cursor", cursor)}))
    return processed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arena-url", default=os.environ.get("ARENA_BASE_URL", "http://127.0.0.1:8056"),
                        help="Base URL of the Arena API. Env: ARENA_BASE_URL. Update this (not the code) when the Arena moves to its hosted URL.")
    parser.add_argument("--agent-secret", required=True, help="Path to agent.secret.json")
    parser.add_argument("--cursor-file", default=None, help="Where to persist the feedback cursor (default: alongside agent-secret)")
    parser.add_argument("--poll-seconds", type=int, default=None, help="If set, loop forever polling at this interval instead of a single pass")
    args = parser.parse_args()
    secret = json.loads(Path(args.agent_secret).read_text())
    cursor_path = Path(args.cursor_file) if args.cursor_file else Path(args.agent_secret).with_name("intelligence_agent_cursor.json")
    while True:
        processed = run_once(args.arena_url, secret["token"], cursor_path)
        print(json.dumps({"processed": processed, "at": datetime.now(timezone.utc).isoformat()}))
        if args.poll_seconds is None:
            break
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
