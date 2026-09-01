# epics/ep_050_distribution_engine/implementation/node_18/ep048_render_publish_trigger.py
# EP050 Node 18 -> EP048 real render + real YouTube upload trigger.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-20 · Initial version. Per direct user instruction: "we need node 18 to be
#   able to trigger that process (assuming that node 17 has already provided the necessary
#   copy)... the ep048 process goes off and generates the video and uploads to necessary
#   platforms.... the node 18 then confirms when the video is uploaded and then proceeds to
#   next node." Calls the REAL epics/ep_048_YTA/scripts/generate_video.py (ElevenLabs + Pexels +
#   MoviePy) and the REAL epics/ep_048_YTA/scripts/upload_video.py (YouTube Data API v3,
#   Unlisted-only per that script's own fixed privacyStatus gate -- verified real and working on
#   2026-08-18 via direct browser check of the user's YouTube channel, see agent_board event
#   20260818T105355664_claude_8302d9fd / 20260818T105719303_claude_786579d2).
#
# Scope: takes an already-generated, already-validated VideoAssetRecord (Node 18's own
# video_asset_factory.py output, itself built from Node 17's real AssetPayload) and the matching
# Node 17 asset (for its title), translates it via the existing ep048_script_adapter.py, then
# actually invokes EP048's real scripts as subprocesses -- a genuine external action (network
# calls to ElevenLabs/Pexels for render, and a real YouTube upload). This module performs a real
# publish; the API layer calling it MUST require an explicit per-call confirmation flag from the
# caller (see server.py handle_node18_trigger_render_and_upload) -- this module itself does not
# gate on confirmation, it trusts the caller already obtained it.
#
# Fail-closed: any subprocess non-zero exit, missing output file, or unparseable upload response
# raises a typed error. Nothing is ever reported as rendered or uploaded unless the real
# artifacts/response prove it (a real mp4 file for render, a real video_id for upload).

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ep048_script_adapter import build_ep048_markdown_script  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[4]
EP048_SCRIPTS_DIR = REPO_ROOT / "epics" / "ep_048_YTA" / "scripts"
DEFAULT_CLIENT_SECRETS_PATH = REPO_ROOT / "client_secrets.json"
DEFAULT_YOUTUBE_CATEGORY = "27"  # Education -- matches EP048's own generate_metadata.py default.
RENDER_TIMEOUT_SECONDS = 1800
UPLOAD_TIMEOUT_SECONDS = 900

_VIDEO_ID_RE = re.compile(r"Video ID:\s*(\S+)")
_WATCH_URL_RE = re.compile(r"(https://www\.youtube\.com/watch\?v=\S+)")


class Ep048TriggerError(RuntimeError):
    """Raised when the real render or real upload subprocess fails or returns no proof of success."""


class RenderFailedError(Ep048TriggerError):
    pass


class UploadFailedError(Ep048TriggerError):
    pass


@dataclass(frozen=True)
class RenderPublishResult:
    video_asset_id: str
    run_id: str
    script_path: str
    render_output_path: str
    rendered_at: str
    render_stdout_tail: str
    video_id: str
    watch_url: str
    privacy_status: str
    uploaded_at: str
    upload_stdout_tail: str
    external_action: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_asset_id": self.video_asset_id,
            "run_id": self.run_id,
            "script_path": self.script_path,
            "render_output_path": self.render_output_path,
            "rendered_at": self.rendered_at,
            "render_stdout_tail": self.render_stdout_tail,
            "video_id": self.video_id,
            "watch_url": self.watch_url,
            "privacy_status": self.privacy_status,
            "uploaded_at": self.uploaded_at,
            "upload_stdout_tail": self.upload_stdout_tail,
            "external_action": self.external_action,
        }


def _tail(text: str, n: int = 2000) -> str:
    return text[-n:] if text else ""


def _upload_env() -> dict[str, str]:
    # upload_video.py resolves YOUTUBE_CLIENT_SECRETS_FILE (default "client_secrets.json") as a
    # path relative to its own cwd (EP048_SCRIPTS_DIR here), but the real file lives at the repo
    # root -- confirmed live 2026-08-20 (first real trigger failed with "Client Secrets file not
    # found at: client_secrets.json"). Sets the absolute real path, without touching the shared
    # root .env (which other, correctly-cwd'd consumers of upload_video.py already rely on
    # working via its relative default). Respects a caller-supplied override if one is already
    # set in the environment.
    env = dict(os.environ)
    env.setdefault("YOUTUBE_CLIENT_SECRETS_FILE", str(DEFAULT_CLIENT_SECRETS_PATH))
    return env


def _build_metadata(video_record: dict[str, Any], asset_title: str) -> dict[str, Any]:
    description_parts = [
        video_record.get("caption", ""),
        "",
        video_record.get("call_to_action", ""),
        "",
        video_record.get("safety_disclaimer", ""),
    ]
    return {
        "title": asset_title[:100],
        "description": "\n".join(p for p in description_parts if p),
        "tags": [video_record.get("target_id", "")],
        "category": DEFAULT_YOUTUBE_CATEGORY,
    }


def trigger_render_and_publish(
    *,
    run_id: str,
    video_record: dict[str, Any],
    asset_title: str,
    work_dir: Path,
    video_source: str = "pexels",
) -> RenderPublishResult:
    """Runs the REAL EP048 render, then the REAL EP048 YouTube upload, for one video asset.

    Raises RenderFailedError / UploadFailedError fail-closed on any non-zero exit or missing
    proof of success. Never fabricates a video_id or watch_url.
    """
    if not EP048_SCRIPTS_DIR.exists():
        raise Ep048TriggerError(f"EP048 scripts directory not found: {EP048_SCRIPTS_DIR}")

    work_dir.mkdir(parents=True, exist_ok=True)
    video_asset_id = video_record["video_asset_id"]

    markdown_script = build_ep048_markdown_script(video_record)
    script_path = work_dir / f"{video_asset_id}_script.md"
    script_path.write_text(markdown_script, encoding="utf-8")

    output_path = work_dir / f"{video_asset_id}.mp4"

    render_proc = subprocess.run(
        [
            sys.executable, "generate_video.py",
            "--script", str(script_path),
            "--output", str(output_path),
            "--video-source", video_source,
        ],
        cwd=str(EP048_SCRIPTS_DIR),
        capture_output=True,
        text=True,
        timeout=RENDER_TIMEOUT_SECONDS,
    )
    render_stdout_tail = _tail(render_proc.stdout + "\n" + render_proc.stderr)
    if render_proc.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        raise RenderFailedError(
            f"generate_video.py failed for {video_asset_id} (exit={render_proc.returncode}, "
            f"output_exists={output_path.exists()}): {render_stdout_tail}"
        )
    rendered_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    metadata = _build_metadata(video_record, asset_title)
    metadata_path = work_dir / f"{video_asset_id}_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    upload_proc = subprocess.run(
        [
            sys.executable, "upload_video.py",
            "--video", str(output_path),
            "--metadata", str(metadata_path),
        ],
        cwd=str(EP048_SCRIPTS_DIR),
        capture_output=True,
        text=True,
        timeout=UPLOAD_TIMEOUT_SECONDS,
        env=_upload_env(),
    )
    upload_stdout_tail = _tail(upload_proc.stdout + "\n" + upload_proc.stderr)
    video_id_match = _VIDEO_ID_RE.search(upload_proc.stdout)
    if upload_proc.returncode != 0 or not video_id_match:
        raise UploadFailedError(
            f"upload_video.py failed for {video_asset_id} (exit={upload_proc.returncode}, "
            f"no video_id found in output): {upload_stdout_tail}"
        )
    video_id = video_id_match.group(1)
    watch_url_match = _WATCH_URL_RE.search(upload_proc.stdout)
    watch_url = watch_url_match.group(1) if watch_url_match else f"https://www.youtube.com/watch?v={video_id}"
    uploaded_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    return RenderPublishResult(
        video_asset_id=video_asset_id,
        run_id=run_id,
        script_path=str(script_path),
        render_output_path=str(output_path),
        rendered_at=rendered_at,
        render_stdout_tail=render_stdout_tail,
        video_id=video_id,
        watch_url=watch_url,
        privacy_status="unlisted",
        uploaded_at=uploaded_at,
        upload_stdout_tail=upload_stdout_tail,
    )
