# epics/ep_050_distribution_engine/implementation/node_18/ep048_script_adapter.py
# EP050 Node 18 -> EP048 markdown script adapter.
#
# VERSION HISTORY
# v1.0.0 · 2026-08-17 · Initial version: translates a Node 18 VideoAssetRecord's storyboard into
#   the markdown format epics/ep_048_YTA/scripts/script_parser.py expects. Pure string
#   transformation only -- no file I/O, no network access, no external API call, and no render
#   is ever triggered by this module. Building the schema adapter and triggering a real render
#   are deliberately separate: EP050's own safety boundary requires "approval gate, rights
#   validation and explicit external-action authorization" before any render or API call, and
#   this file stops well short of that line.
#
# Scope: read-only translation of an already-generated, already-validated VideoAssetRecord
# (Node 18's own register()/generate_and_register_from_live_chain() output) into the exact
# markdown shape EP048's ScriptParser.parse_script() consumes:
#
#   ## SECTION <n>
#
#   [Visual: <free-text description -- EP048's own keyword extractor narrows this>]
#
#   **Narration:** <voiceover text>
#   ---
#
# Design notes (read before changing the mapping):
# - One storyboard scene -> one "## SECTION" block, in scene order. scene.visual_description
#   becomes the [Visual: ...] cue text verbatim; EP048's ScriptParser.extract_search_keywords()
#   does its own keyword reduction, so no filtering happens here.
# - scene.on_screen_text has nowhere to go: EP048's pipeline auto-generates burned-in captions
#   from the narration audio (VideoEngine.build_captions), it does not accept separate on-screen
#   text. This is a known, one-way lossy translation -- documented, not silently dropped.
# - safety_disclaimer is NOT part of any Node 18 scene by default (it is a separate top-level
#   mandatory field). EP048 has no first-class concept of a disclaimer. To avoid silently
#   dropping legally-mandatory content, this adapter appends it as one additional trailing
#   SECTION so it ends up narrated (and therefore captioned) in the rendered video. If that
#   placement is wrong for a given campaign, override via disclaimer_placement="omit" and
#   handle it out of band -- but the default is "never lose it silently".

from __future__ import annotations

from typing import Any


class Ep048AdapterError(ValueError):
    """Raised when the input VideoAssetRecord cannot be translated (missing/empty storyboard)."""


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise Ep048AdapterError(f"video_asset must be a dict or have a to_dict() method, got: {type(value).__name__}")


def _section(index: int, visual_text: str, narration_text: str) -> str:
    return (
        f"## SECTION {index}\n\n"
        f"[Visual: {visual_text}]\n\n"
        f"**Narration:** {narration_text}\n"
        "---\n"
    )


def build_ep048_markdown_script(
    video_asset: Any,
    *,
    disclaimer_placement: str = "trailing_section",
) -> str:
    """Translates a Node 18 VideoAssetRecord into an EP048-compatible markdown script string.

    Pure function: no file I/O, no network access, no external API call. Does not trigger a
    render -- the caller decides separately, with explicit authorization, whether and when to
    hand the returned string to EP048's generate_video.py.

    Args:
        video_asset: a VideoAssetRecord (or its .to_dict()) from
            epics/ep_050_distribution_engine/implementation/node_18/video_asset_factory.py.
        disclaimer_placement: "trailing_section" (default) appends the mandatory
            safety_disclaimer as one final narrated SECTION so it is never silently dropped.
            "omit" skips it -- only use this if the disclaimer will be attached to the finished
            video by some other explicit, reviewed process.

    Returns:
        A markdown string parseable by epics/ep_048_YTA/scripts/script_parser.py's
        ScriptParser.parse_script() (write it to a .md file before invoking that pipeline).

    Raises:
        Ep048AdapterError: if the record has no storyboard scenes to translate, or an unknown
            disclaimer_placement is supplied.
    """
    if disclaimer_placement not in ("trailing_section", "omit"):
        raise Ep048AdapterError(f"Unknown disclaimer_placement: {disclaimer_placement!r}")

    asset = _to_dict(video_asset)
    storyboard = asset.get("storyboard") or []
    if not storyboard:
        raise Ep048AdapterError("video_asset.storyboard is empty; nothing to translate")

    sections: list[str] = []
    for index, raw_scene in enumerate(storyboard, start=1):
        scene = _to_dict(raw_scene)
        visual_text = str(scene.get("visual_description", "")).strip()
        narration_text = str(scene.get("voiceover_text", "")).strip()
        if not visual_text or not narration_text:
            raise Ep048AdapterError(
                f"storyboard scene {index} is missing visual_description or voiceover_text"
            )
        sections.append(_section(index, visual_text, narration_text))

    if disclaimer_placement == "trailing_section":
        disclaimer_text = str(asset.get("safety_disclaimer", "")).strip()
        if disclaimer_text:
            sections.append(
                _section(len(storyboard) + 1, "clean branded end card, neutral background", disclaimer_text)
            )

    return "\n".join(sections)
