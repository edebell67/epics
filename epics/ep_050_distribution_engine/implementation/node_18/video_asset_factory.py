# epics/ep_050_distribution_engine/implementation/node_18/video_asset_factory.py
# EP050 Node 18 — Video Asset Factory.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds automated ingestion: generate_and_register_from_live_chain() takes
#   only cluster_id/target_id/signal_id plus the real Node 05 signal registry, Node 15 cluster
#   registry, and Node 16 knowledge store, and automatically re-derives the classification/
#   selection (by re-running the real, deterministic Node 11->12->13->14 chain on the real Node
#   05 signal) and fetches the real registered facts for the target -- no human manually
#   selects/passes the classification/selection/facts/asset objects that generate_and_register()
#   used to require. Facts themselves are NOT fabricated: they must already be registered in
#   Node 16 by whatever process owns canonical business-knowledge curation; this only removes
#   the manual step of finding and passing them. Per the user-mandated CORE REQUIREMENT
#   (2026-08-17): Node 18 was previously accepted at 100% against the prior manual-assembly
#   requirement; this adds the automation that requirement now demands.
# v1.0.0 · 2026-08-17 · Initial deterministic, offline, fixture-only video asset factory.
#
# Scope: EP050 Node 18 only, per allocation 20260817T094732322_codex_877fdf88, activated
# after Node 15's 100% acceptance and release.
# Fail-closed, deterministic, no network access, no actual video rendering, no paid media/LLM
# APIs, no uploads, publishing, or credentials. external_action is a literal False guarantee.
# The automated path re-runs Node 11-14's own real, deterministic functions and queries the real
# Node 16 store -- it does not add any new network access or change what those functions compute.
#
# Produces a script/storyboard/shot-list/caption/branding/CTA/render-manifest PACKAGE
# describing what a video asset would contain -- never an actual rendered video file, never a
# live API call. Consumes the real (non-mocked) output of Node 11 (Intent Classification),
# Node 14 (Channel/Placement Selection), Node 16 (Canonical Knowledge Store facts), Node 17
# (Content & Utility Factory AssetPayload), and the relevant Node 15 (Campaign Cluster) that
# this asset belongs to, with exact cross-record lineage verification.

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_05"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_11"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_12"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_13"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_14"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_15"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_16"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node_17"))
from intent_classification import classify_demand_signal  # noqa: E402
from opportunity_scoring import score_demand_opportunity  # noqa: E402
from demand_path_discovery import discover_demand_path  # noqa: E402
from channel_placement_selection import select_channel_placements  # noqa: E402
from content_utility_factory import generate_asset_payload, resolve_campaign_context  # noqa: E402

# Fixture-only licensing/source metadata: documents what the licensing model WOULD be for a
# real render, never a claim that real media exists. Pinned constants, not caller-suppliable.
LICENSING_METADATA: dict[str, str] = {
    "broll_source": "synthetic_fixture_stock_library",
    "music_license": "royalty_free_fixture_track",
    "narration_voice": "synthetic_fixture_tts_voice",
    "license_type": "fixture_only_no_real_asset_license",
}

MIN_TOTAL_DURATION_SECONDS = 10.0
MAX_TOTAL_DURATION_SECONDS = 180.0
DEFAULT_TEMPLATE_VERSION = "1.0.0"

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s\-.]?){7,}\d")


class VideoAssetFactoryError(RuntimeError):
    """Base class for Node 18 failures. Fail-closed: never partially writes."""


class ValidationError(VideoAssetFactoryError):
    """Raised when required fields are missing, malformed, out of bounds, or contain prohibited PII."""


class LineageError(VideoAssetFactoryError):
    """Raised when required upstream Node11/14/15/16/17 lineage is missing or mismatched."""


class ConflictError(VideoAssetFactoryError):
    """Raised when a video_asset_id already exists with different field values."""


def _check_no_pii(name: str, value: str) -> None:
    if EMAIL_PATTERN.search(value):
        raise ValidationError(f"{name} appears to contain an email address; prohibited PII rejected fail-closed")
    if PHONE_PATTERN.search(value):
        raise ValidationError(f"{name} appears to contain a phone number; prohibited PII rejected fail-closed")


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise ValidationError(f"Input must be a dict or have a to_dict() method, got: {type(value).__name__}")


@dataclass(frozen=True)
class VideoScene:
    scene_index: int
    shot_type: str
    duration_seconds: float
    visual_description: str
    voiceover_text: str
    on_screen_text: str
    source_fact_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VideoAssetRecord:
    video_asset_id: str
    cluster_id: str
    asset_id: str
    target_id: str
    signal_id: str
    classification_id: str
    opportunity_id: str
    path_id: str
    selection_id: str
    script: str
    storyboard: list[VideoScene]
    shot_list: list[dict[str, Any]]
    caption: str
    branding: dict[str, str]
    call_to_action: str
    safety_disclaimer: str
    total_duration_seconds: float
    licensing_metadata: dict[str, str]
    render_manifest: dict[str, Any]
    external_action: bool
    fact_ids: list[str]
    template_version: str
    created_at: str
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["storyboard"] = [s.to_dict() if isinstance(s, VideoScene) else s for s in self.storyboard]
        return data


def _validate_scene(index: int, scene: dict[str, Any], approved_fact_ids: set[str]) -> VideoScene:
    required = ("scene_index", "shot_type", "duration_seconds", "visual_description", "voiceover_text", "source_fact_ids")
    for field_name in required:
        if field_name not in scene:
            raise ValidationError(f"scene[{index}] is missing required field '{field_name}'")

    scene_index = scene["scene_index"]
    if not isinstance(scene_index, int) or isinstance(scene_index, bool) or scene_index != index + 1:
        raise ValidationError(f"scene[{index}] has invalid scene_index; expected {index + 1}, got {scene_index!r}")

    duration = scene["duration_seconds"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
        raise ValidationError(f"scene[{index}].duration_seconds must be a positive number, got: {duration!r}")

    for text_field in ("shot_type", "visual_description", "voiceover_text"):
        value = scene[text_field]
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"scene[{index}].{text_field} is required and must be a non-empty string")
        _check_no_pii(f"scene[{index}].{text_field}", value)

    on_screen_text = str(scene.get("on_screen_text", ""))
    if on_screen_text:
        _check_no_pii(f"scene[{index}].on_screen_text", on_screen_text)

    source_fact_ids = scene["source_fact_ids"]
    if not isinstance(source_fact_ids, list):
        raise ValidationError(f"scene[{index}].source_fact_ids must be a list")
    for fact_id in source_fact_ids:
        if fact_id not in approved_fact_ids:
            raise LineageError(
                f"scene[{index}] references fact_id {fact_id!r} not present in the asset's approved fact_ids "
                "(exact factual lineage violation, rejected fail-closed)"
            )

    return VideoScene(
        scene_index=scene_index,
        shot_type=str(scene["shot_type"]).strip(),
        duration_seconds=round(float(duration), 2),
        visual_description=str(scene["visual_description"]).strip(),
        voiceover_text=str(scene["voiceover_text"]).strip(),
        on_screen_text=on_screen_text.strip(),
        source_fact_ids=list(source_fact_ids),
    )


def _humanize(token: str) -> str:
    return " ".join(part for part in str(token).replace("_", " ").split() if part).title()


def _default_scenes(video_title: str, video_cta: str, fact_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # video_title/video_cta are the locality-neutral variants (see generate_and_register) --
    # never asset["title"]/asset["call_to_action"] directly, which name a specific town/city.
    # A rendered video is reusable across every locality its applicability tag covers (see
    # server.py's applicability/reuse mechanism), so it must never claim to be about one place.
    scenes: list[dict[str, Any]] = [
        {
            "scene_index": 1,
            "shot_type": "hook_closeup",
            "duration_seconds": 3.0,
            "visual_description": f"Close-up establishing shot introducing the problem: {video_title}",
            "voiceover_text": video_title,
            "on_screen_text": video_title,
            "source_fact_ids": [],
        }
    ]
    for idx, fact in enumerate(fact_records, start=2):
        scenes.append(
            {
                "scene_index": idx,
                "shot_type": "diagnostic_insert",
                "duration_seconds": 4.0,
                "visual_description": f"Diagnostic visual illustrating: {fact['claim']}",
                "voiceover_text": fact["claim"],
                "on_screen_text": fact["claim"][:80],
                "source_fact_ids": [fact["fact_id"]],
            }
        )
    scenes.append(
        {
            "scene_index": len(scenes) + 1,
            "shot_type": "cta_end_card",
            "duration_seconds": 5.0,
            "visual_description": "Branded end card with contact CTA overlay",
            "voiceover_text": video_cta,
            "on_screen_text": video_cta,
            "source_fact_ids": [],
        }
    )
    return scenes


def _compute_deterministic_video_asset_id(cluster_id: str, asset_id: str, template_version: str) -> str:
    token = f"{cluster_id}:{asset_id}:{template_version}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"vid_{digest}"


class VideoAssetRegistry:
    """Local, JSON-file-backed, fixture-only Node 18 registry. No network I/O, no rendering.

    generate_and_register() consumes the real (non-mocked) Node 11 classification, Node 14
    selection, Node 16 facts, Node 17 asset payload, and the Node 15 cluster this asset
    belongs to, verifies exact lineage across all of them, and produces a deterministic
    script/storyboard/shot-list/caption/branding/CTA/render-manifest package. No real video is
    ever rendered; render_manifest and licensing_metadata describe intent only.
    """

    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, dict[str, Any]]:
        raw = self.storage_path.read_text(encoding="utf-8")
        return json.loads(raw) if raw.strip() else {}

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        temp_path = self.storage_path.with_suffix(f".tmp{id(self)}")
        temp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self.storage_path)

    def generate_and_register(
        self,
        *,
        classification: Any,
        selection: Any,
        facts: list[Any],
        asset: Any,
        cluster: Any,
        custom_scenes: list[dict[str, Any]] | None = None,
        template_version: str = DEFAULT_TEMPLATE_VERSION,
        service_scope: str | list[str] | None = None,
    ) -> VideoAssetRecord:
        """service_scope declares which services this video's own copy should speak to -- it is
        the content-side counterpart of server.py's applicability.service_scope tag, so a video
        tagged reusable across multiple services actually says so, instead of always naming the
        one service the originating campaign happened to be about. None/omitted (default) keeps
        the original single-service copy. "all" or an explicit list of >1 service produces
        category-wide copy (2026-08-20, direct user instruction/example: "for your boiler
        service, repair, emergencies... we have [professionals] ready locally... register here
        for immediate contact from one of our professionals")."""
        classification_d = _to_dict(classification)
        selection_d = _to_dict(selection)
        asset_d = _to_dict(asset)
        cluster_d = _to_dict(cluster)

        if not isinstance(facts, list) or not facts:
            raise LineageError("facts must be a non-empty list of Node 16 CanonicalFactRecord")
        fact_records = [_to_dict(f) for f in facts]

        # Exact lineage verification across Node11/14/16/17.
        for id_field in ("target_id", "signal_id", "classification_id"):
            values = {str(classification_d.get(id_field)), str(selection_d.get(id_field)), str(asset_d.get(id_field))}
            if not all(values) or len(values) != 1:
                raise LineageError(
                    f"Mismatched or missing '{id_field}' across Node11/14/17 lineage: {sorted(values)}"
                )
        if str(selection_d.get("selection_id")) != str(asset_d.get("selection_id")):
            raise LineageError("selection_id mismatch between Node14 selection and Node17 asset")
        if not asset_d.get("opportunity_id") or not asset_d.get("path_id"):
            raise LineageError("Node17 asset is missing opportunity_id/path_id lineage")

        asset_fact_ids = set(asset_d.get("fact_ids") or [])
        if not asset_fact_ids:
            raise LineageError("Node17 asset has no fact_ids; cannot verify factual lineage")
        for fact in fact_records:
            fact_id = fact.get("fact_id")
            if not fact_id or fact_id not in asset_fact_ids:
                raise LineageError(
                    f"fact_id {fact_id!r} is not present in the Node17 asset's approved fact_ids "
                    "(exact factual lineage violation, rejected fail-closed)"
                )

        cluster_member_selection_ids = {m.get("selection_id") for m in (cluster_d.get("members") or [])}
        if str(selection_d.get("selection_id")) not in cluster_member_selection_ids:
            raise LineageError(
                "This asset's selection_id is not a member of the supplied Node15 cluster "
                "(the video asset must belong to the campaign cluster it is generated for)"
            )

        metadata = asset_d.get("metadata") or {}
        if metadata.get("external_action") not in (False, "false"):
            raise ValidationError("Node17 asset metadata.external_action must be literal False")

        safety_disclaimer = str(asset_d.get("safety_disclaimer", "")).strip()
        asset_call_to_action = str(asset_d.get("call_to_action", "")).strip()
        if not safety_disclaimer:
            raise ValidationError("Node17 asset is missing a mandatory safety_disclaimer")
        if not asset_call_to_action:
            raise ValidationError("Node17 asset is missing a mandatory call_to_action")

        # A video is reusable across every locality/region its applicability tag covers (server.py
        # _find_reusable_video_publication), so its own title/CTA must never name a specific town
        # or city -- unlike asset_d's title/call_to_action, which Node 17 deliberately DOES
        # localise for channels (maps listings, local search) where a place claim is correct.
        # Re-resolves service_label the same way Node 17 does, but never includes locality/region.
        video_context = resolve_campaign_context(classification_d)
        video_service_label = video_context["service_label"]
        if not video_service_label:
            raise ValidationError(
                "Cannot build locality-neutral video copy: service_label not resolvable from classification"
            )

        if service_scope == "all":
            raw_service_name = str((classification_d.get("service_context") or {}).get("service_name") or "")
            category_label = _humanize(raw_service_name.split("_", 1)[0]) if raw_service_name else video_service_label
            video_title = f"{category_label} Service, Repair & Emergencies"
            call_to_action = f"We have {category_label.lower()} professionals ready locally. Register here for immediate contact."
        elif isinstance(service_scope, list) and len(service_scope) > 1:
            labels = [_humanize(s) for s in service_scope]
            joined = ", ".join(labels[:-1]) + f" & {labels[-1]}" if len(labels) > 1 else labels[0]
            video_title = joined
            call_to_action = f"We have {joined.lower()} professionals ready locally. Register here for immediate contact."
        else:
            video_title = video_service_label
            call_to_action = f"Enquire about {video_service_label}."

        scenes_input = custom_scenes if custom_scenes is not None else _default_scenes(video_title, call_to_action, fact_records)
        if not isinstance(scenes_input, list) or not scenes_input:
            raise ValidationError("storyboard must contain at least one scene")

        storyboard = [_validate_scene(i, scene, asset_fact_ids) for i, scene in enumerate(scenes_input)]
        total_duration = round(sum(s.duration_seconds for s in storyboard), 2)
        if not (MIN_TOTAL_DURATION_SECONDS <= total_duration <= MAX_TOTAL_DURATION_SECONDS):
            raise ValidationError(
                f"total_duration_seconds must be in [{MIN_TOTAL_DURATION_SECONDS}, {MAX_TOTAL_DURATION_SECONDS}], "
                f"got: {total_duration}"
            )

        script = "\n\n".join(f"[Scene {s.scene_index} - {s.shot_type}] {s.voiceover_text}" for s in storyboard)
        caption = " ".join(s.voiceover_text for s in storyboard) + f" {safety_disclaimer}"
        shot_list = [
            {"shot_index": s.scene_index, "shot_type": s.shot_type, "duration_seconds": s.duration_seconds}
            for s in storyboard
        ]
        branding = {
            "watermark_text": "Verified Local Service",
            "end_card_cta": call_to_action,
        }
        render_manifest = {
            "target_resolution": "1080x1920",
            "target_format": "mp4_manifest_only",
            "scene_count": len(storyboard),
            "estimated_render_seconds": total_duration,
            "renderer": "not_executed_fixture_only",
        }

        cluster_id = str(cluster_d.get("cluster_id", "")).strip()
        asset_id = str(asset_d.get("asset_id", "")).strip()
        if not cluster_id or not asset_id:
            raise LineageError("cluster_id and asset_id are both required to derive a stable video_asset_id")
        video_asset_id = _compute_deterministic_video_asset_id(cluster_id, asset_id, template_version)

        candidate = VideoAssetRecord(
            video_asset_id=video_asset_id,
            cluster_id=cluster_id,
            asset_id=asset_id,
            target_id=str(asset_d["target_id"]),
            signal_id=str(asset_d["signal_id"]),
            classification_id=str(asset_d["classification_id"]),
            opportunity_id=str(asset_d["opportunity_id"]),
            path_id=str(asset_d["path_id"]),
            selection_id=str(asset_d["selection_id"]),
            script=script,
            storyboard=storyboard,
            shot_list=shot_list,
            caption=caption,
            branding=branding,
            call_to_action=call_to_action,
            safety_disclaimer=safety_disclaimer,
            total_duration_seconds=total_duration,
            licensing_metadata=dict(LICENSING_METADATA),
            render_manifest=render_manifest,
            external_action=False,
            fact_ids=sorted({fid for s in storyboard for fid in s.source_fact_ids}),
            template_version=template_version,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return self._persist(candidate)

    def generate_and_register_from_live_chain(
        self,
        *,
        cluster_id: str,
        target_id: str,
        signal_id: str,
        demand_signal_registry: Any,
        cluster_registry: Any,
        knowledge_store: Any,
        custom_scenes: list[dict[str, Any]] | None = None,
        template_version: str = DEFAULT_TEMPLATE_VERSION,
        service_scope: str | list[str] | None = None,
    ) -> VideoAssetRecord:
        """Automated ingestion path: re-derives classification/selection by re-running the real
        Node 11->12->13->14 chain on the real Node 05 signal, fetches the real registered Node 16
        facts for target_id, and builds the Node 17 asset -- no human manually selects/passes
        those objects. Facts are queried, never fabricated: they must already exist in
        knowledge_store from whatever process owns canonical business-knowledge curation.
        Writes through the same validated generate_and_register() contract, so every existing
        invariant (exact lineage, mandatory disclaimer/CTA, external_action=False, duration
        bounds, PII screen, idempotency, conflict detection) is enforced unchanged.
        """
        cluster = cluster_registry.get(cluster_id)
        if cluster is None:
            raise LineageError(f"cluster_id {cluster_id!r} is not registered in the Node 15 cluster registry")

        signal = demand_signal_registry.get(signal_id)
        if signal is None:
            raise LineageError(f"signal_id {signal_id!r} is not registered in the Node 05 demand signal registry")
        if signal.target_id != target_id:
            raise LineageError(
                f"signal_id {signal_id!r} belongs to target_id {signal.target_id!r}, not the requested {target_id!r}"
            )

        classification = classify_demand_signal(signal.to_contract_payload())
        opportunity = score_demand_opportunity(classification)
        path = discover_demand_path(opportunity)
        selection = select_channel_placements(path)

        facts = knowledge_store.list_facts(target_id=target_id)
        if not facts:
            raise LineageError(
                f"target_id {target_id!r} has no registered Node 16 facts; register canonical "
                "facts before an automated video asset can be generated for it"
            )

        asset = generate_asset_payload(selection, facts=facts, intent_input=classification)

        return self.generate_and_register(
            classification=classification,
            selection=selection,
            facts=facts,
            asset=asset,
            cluster=cluster,
            custom_scenes=custom_scenes,
            template_version=template_version,
            service_scope=service_scope,
        )

    def _persist(self, candidate: VideoAssetRecord) -> VideoAssetRecord:
        data = self._load()
        existing = data.get(candidate.video_asset_id)
        if existing is not None:
            non_identity_fields = ("created_at", "recorded_at")
            comparable_existing = {k: v for k, v in existing.items() if k not in non_identity_fields}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k not in non_identity_fields}
            if comparable_existing == comparable_candidate:
                return self._record_from_dict(existing)  # idempotent
            raise ConflictError(
                f"video_asset_id {candidate.video_asset_id!r} already registered with different field values; "
                "conflicting duplicate registrations are rejected fail-closed"
            )
        data[candidate.video_asset_id] = candidate.to_dict()
        self._save(data)
        return candidate

    @staticmethod
    def _record_from_dict(data: dict[str, Any]) -> VideoAssetRecord:
        payload = dict(data)
        payload["storyboard"] = [VideoScene(**s) for s in payload["storyboard"]]
        return VideoAssetRecord(**payload)

    def get(self, video_asset_id: str) -> VideoAssetRecord | None:
        data = self._load()
        record = data.get(video_asset_id)
        return self._record_from_dict(record) if record is not None else None

    def list(self) -> list[VideoAssetRecord]:
        return [self._record_from_dict(record) for record in self._load().values()]
