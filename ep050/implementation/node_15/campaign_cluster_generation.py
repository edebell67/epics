# epics/ep_050_distribution_engine/implementation/node_15/campaign_cluster_generation.py
# EP050 Node 15 — Campaign / Cluster Generation.
#
# VERSION HISTORY
# v1.1.0 · 2026-08-17 · Adds automated ingestion: generate_and_register_from_live_signals() takes
#   only a target_id plus the real Node 05 and Node 11-14 callables/registries, automatically
#   pulls every real Node 05 demand signal for that target and runs the real (non-mocked) Node
#   11->12->13->14 chain on each one to build member bundles itself -- no human manually
#   assembles the member list that generate_and_register() used to require. Per the user-mandated
#   CORE REQUIREMENT (2026-08-17): Node 15 was previously accepted at 100% against the prior
#   manual-assembly requirement; this adds the automation that requirement now demands.
# v1.0.1 · 2026-08-17 · Fixed idempotency comparison: excluded created_at (not just recorded_at)
#   from the identity check, since it is also a fresh wall-clock stamp per build and was
#   causing an identical re-clustering rerun to be misclassified as a conflicting duplicate.
# v1.0.0 · 2026-08-17 · Initial deterministic, offline, fixture-only campaign cluster generation.
#
# Scope: EP050 Node 15 only, per allocation 20260817T094732186_codex_b3bc09ef, activated by
# user-authorized scope expansion 20260817T094731870_codex_9273b8d6.
# Fail-closed, deterministic, no network access, no live data collection, no external actions.
# The automated path re-runs Node 11-14's own real, deterministic functions against real Node 05
# signals -- it does not add any new network access or change what those functions compute.
#
# Groups multiple opportunities (each the real, non-mocked output of Node 11 Intent
# Classification -> Node 12 Opportunity Scoring -> Node 13 Demand Path Discovery -> Node 14
# Channel/Placement Selection) into coherent demand clusters via an explicit, versioned
# similarity rule: same primary_intent + same geography.locality + same primary_channel.
# Does NOT touch Node 18 or any other node/UI/owner.

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
from intent_classification import classify_demand_signal  # noqa: E402
from opportunity_scoring import score_demand_opportunity  # noqa: E402
from demand_path_discovery import discover_demand_path  # noqa: E402
from channel_placement_selection import select_channel_placements  # noqa: E402

# Explicit, versioned similarity/rule logic. Any change requires a new CLUSTER_RULE_VERSION
# and a full regression rerun per the Test Library procedure.
CLUSTER_RULE_VERSION = "cluster_rule_v1.0"

LINEAGE_SUB_RECORDS = ("classification", "opportunity", "path", "selection")
REQUIRED_LINEAGE_FIELDS_BY_SUBRECORD = {
    "classification": ("classification_id", "signal_id", "target_id", "primary_intent", "urgency_level", "geography"),
    "opportunity": ("opportunity_id", "target_id", "signal_id", "classification_id", "demand_opportunity_score", "priority_tier"),
    "path": ("path_id", "target_id", "signal_id", "classification_id", "opportunity_id"),
    "selection": ("selection_id", "target_id", "signal_id", "classification_id", "opportunity_id", "path_id", "primary_channel"),
}

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\s\-.]?){7,}\d")


class CampaignClusterError(RuntimeError):
    """Base class for Node 15 failures. Fail-closed: never partially writes."""


class ValidationError(CampaignClusterError):
    """Raised when required fields are missing, malformed, out of bounds, or contain prohibited PII."""


class LineageError(CampaignClusterError):
    """Raised when required upstream Node11-14 lineage sub-records are missing or mismatched."""


class ConflictError(CampaignClusterError):
    """Raised when a cluster_id already exists with different field values."""


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
    raise ValidationError(f"Sub-record must be a dict or have a to_dict() method, got: {type(value).__name__}")


def _validate_member_bundle(index: int, bundle: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(bundle, dict):
        raise ValidationError(f"member[{index}] must be an object with classification/opportunity/path/selection keys")

    resolved: dict[str, dict[str, Any]] = {}
    for sub_record_name in LINEAGE_SUB_RECORDS:
        if sub_record_name not in bundle:
            raise LineageError(f"member[{index}] is missing mandatory upstream lineage bundle '{sub_record_name}'")
        sub = _to_dict(bundle[sub_record_name])
        for required_field in REQUIRED_LINEAGE_FIELDS_BY_SUBRECORD[sub_record_name]:
            if not sub.get(required_field) and sub.get(required_field) != 0:
                raise LineageError(
                    f"member[{index}].{sub_record_name} is missing mandatory upstream lineage field '{required_field}'"
                )
        resolved[sub_record_name] = sub

    classification, opportunity, path, selection = (resolved[k] for k in LINEAGE_SUB_RECORDS)

    for id_field, records in (
        ("target_id", (classification, opportunity, path, selection)),
        ("signal_id", (classification, opportunity, path, selection)),
        ("classification_id", (classification, opportunity, path, selection)),
        ("opportunity_id", (opportunity, path, selection)),
        ("path_id", (path, selection)),
    ):
        values = {str(record[id_field]) for record in records}
        if len(values) != 1:
            raise LineageError(
                f"member[{index}] has mismatched '{id_field}' across its Node11-14 lineage sub-records: {sorted(values)}"
            )

    score = opportunity["demand_opportunity_score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValidationError(f"member[{index}].opportunity.demand_opportunity_score must be numeric, got: {score!r}")
    if not (0.0 <= float(score) <= 100.0):
        raise ValidationError(
            f"member[{index}].opportunity.demand_opportunity_score must be in [0.0, 100.0], got: {score!r}"
        )

    geography = classification["geography"]
    if not isinstance(geography, dict) or not str(geography.get("locality", "")).strip():
        raise ValidationError(f"member[{index}].classification.geography.locality is required and must be non-empty")

    return resolved


@dataclass(frozen=True)
class ClusterMemberRef:
    target_id: str
    signal_id: str
    classification_id: str
    opportunity_id: str
    path_id: str
    selection_id: str
    demand_opportunity_score: float
    priority_tier: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CampaignClusterRecord:
    cluster_id: str
    rule_version: str
    theme: str
    shared_traits: dict[str, Any]
    members: list[ClusterMemberRef]
    member_count: int
    cluster_score: float
    score_explanation: str
    provenance: dict[str, Any]
    created_at: str
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["members"] = [m.to_dict() if isinstance(m, ClusterMemberRef) else m for m in self.members]
        return data


def _cluster_key(classification: dict[str, Any], selection: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(classification["primary_intent"]),
        str(classification["geography"]["locality"]),
        str(selection["primary_channel"]),
    )


def _compute_deterministic_cluster_id(member_selection_ids: list[str], rule_version: str) -> str:
    token = f"{rule_version}:" + ",".join(sorted(member_selection_ids))
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"cluster_{digest}"


class CampaignClusterRegistry:
    """Local, JSON-file-backed, fixture-only Node 15 registry. No network I/O, no live data.

    generate_and_register() consumes a flat list of member bundles, each carrying the real
    (non-mocked) Node 11 (classification), Node 12 (opportunity), Node 13 (path), and Node 14
    (selection) records for one opportunity, verifies exact cross-sub-record lineage, groups
    members deterministically by (primary_intent, geography.locality, primary_channel) per
    CLUSTER_RULE_VERSION, and persists one CampaignClusterRecord per group.
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
        members: list[dict[str, Any]],
        campaign_context: str | None = None,
    ) -> list[CampaignClusterRecord]:
        if not isinstance(members, list) or not members:
            raise ValidationError("members must be a non-empty list of Node11-14 lineage bundles")
        if campaign_context is not None:
            if not isinstance(campaign_context, str):
                raise ValidationError("campaign_context must be a string if provided")
            _check_no_pii("campaign_context", campaign_context)

        resolved_members: list[dict[str, dict[str, Any]]] = []
        seen_signal_ids: set[str] = set()
        for index, bundle in enumerate(members):
            resolved = _validate_member_bundle(index, bundle)
            signal_id = resolved["classification"]["signal_id"]
            if signal_id in seen_signal_ids:
                raise ValidationError(
                    f"member[{index}] has duplicate signal_id {signal_id!r} within a single clustering run "
                    "(duplicate membership is rejected fail-closed)"
                )
            seen_signal_ids.add(signal_id)
            resolved_members.append(resolved)

        groups: dict[tuple[str, str, str], list[dict[str, dict[str, Any]]]] = {}
        for resolved in resolved_members:
            key = _cluster_key(resolved["classification"], resolved["selection"])
            groups.setdefault(key, []).append(resolved)

        results: list[CampaignClusterRecord] = []
        for (primary_intent, locality, primary_channel), group_members in sorted(groups.items()):
            results.append(
                self._persist(
                    self._build_cluster_record(primary_intent, locality, primary_channel, group_members, campaign_context)
                )
            )
        return results

    def generate_and_register_from_live_signals(
        self,
        target_id: str,
        demand_signal_registry: Any,
        campaign_context: str | None = None,
    ) -> list[CampaignClusterRecord]:
        """Automated ingestion path: pulls every real Node 05 demand signal for target_id and
        runs the real, non-mocked Node 11->12->13->14 chain on each one to build member bundles
        automatically -- no human assembles the member list. Writes through the same validated
        generate_and_register() contract, so every existing invariant (lineage, PII screen,
        idempotency, conflict detection) is enforced unchanged; the only difference is who
        assembles the input.
        """
        signals = demand_signal_registry.list_for_target(target_id)
        if not signals:
            raise LineageError(f"target_id {target_id!r} has no Node 05 demand signals to cluster")

        members: list[dict[str, Any]] = []
        for signal in signals:
            payload = signal.to_contract_payload()
            classification = classify_demand_signal(payload)
            opportunity = score_demand_opportunity(classification)
            path = discover_demand_path(opportunity)
            selection = select_channel_placements(path)
            members.append(
                {
                    "classification": classification,
                    "opportunity": opportunity,
                    "path": path,
                    "selection": selection,
                }
            )

        return self.generate_and_register(members, campaign_context=campaign_context)

    def _build_cluster_record(
        self,
        primary_intent: str,
        locality: str,
        primary_channel: str,
        group_members: list[dict[str, dict[str, Any]]],
        campaign_context: str | None,
    ) -> CampaignClusterRecord:
        member_refs = [
            ClusterMemberRef(
                target_id=m["classification"]["target_id"],
                signal_id=m["classification"]["signal_id"],
                classification_id=m["classification"]["classification_id"],
                opportunity_id=m["opportunity"]["opportunity_id"],
                path_id=m["path"]["path_id"],
                selection_id=m["selection"]["selection_id"],
                demand_opportunity_score=round(float(m["opportunity"]["demand_opportunity_score"]), 2),
                priority_tier=str(m["opportunity"]["priority_tier"]),
            )
            for m in group_members
        ]
        member_refs.sort(key=lambda ref: ref.selection_id)

        first_geo = group_members[0]["classification"]["geography"]
        urgency_levels = sorted({str(m["classification"]["urgency_level"]) for m in group_members})

        cluster_id = _compute_deterministic_cluster_id([ref.selection_id for ref in member_refs], CLUSTER_RULE_VERSION)
        scores = [ref.demand_opportunity_score for ref in member_refs]
        cluster_score = round(sum(scores) / len(scores), 2)
        theme = f"{primary_intent}_{locality}_{primary_channel}".lower().replace(" ", "_")
        score_explanation = (
            f"Average DOS {cluster_score} across {len(member_refs)} member(s) "
            f"(range {min(scores)}-{max(scores)}); {CLUSTER_RULE_VERSION} grouped by "
            f"primary_intent={primary_intent}, locality={locality}, primary_channel={primary_channel}."
        )
        shared_traits = {
            "primary_intent": primary_intent,
            "primary_channel": primary_channel,
            "geography": {
                "locality": first_geo.get("locality", ""),
                "region": first_geo.get("region", ""),
                "country": first_geo.get("country", ""),
            },
            "urgency_levels": urgency_levels,
        }
        provenance: dict[str, Any] = {
            "producer_node": "Node 15 (Campaign / Cluster Generation)",
            "upstream_nodes": ["Node 11", "Node 12", "Node 13", "Node 14"],
            "rule_version": CLUSTER_RULE_VERSION,
        }
        if campaign_context:
            provenance["campaign_context"] = campaign_context

        return CampaignClusterRecord(
            cluster_id=cluster_id,
            rule_version=CLUSTER_RULE_VERSION,
            theme=theme,
            shared_traits=shared_traits,
            members=member_refs,
            member_count=len(member_refs),
            cluster_score=cluster_score,
            score_explanation=score_explanation,
            provenance=provenance,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _persist(self, candidate: CampaignClusterRecord) -> CampaignClusterRecord:
        data = self._load()
        existing = data.get(candidate.cluster_id)
        if existing is not None:
            # created_at/recorded_at are wall-clock stamps, not part of cluster identity --
            # excluded so a byte-identical re-clustering run is recognized as idempotent.
            non_identity_fields = ("created_at", "recorded_at")
            comparable_existing = {k: v for k, v in existing.items() if k not in non_identity_fields}
            comparable_candidate = {k: v for k, v in candidate.to_dict().items() if k not in non_identity_fields}
            if comparable_existing == comparable_candidate:
                return self._record_from_dict(existing)  # idempotent
            raise ConflictError(
                f"cluster_id {candidate.cluster_id!r} already registered with different field values; "
                "conflicting duplicate registrations are rejected fail-closed"
            )
        data[candidate.cluster_id] = candidate.to_dict()
        self._save(data)
        return candidate

    @staticmethod
    def _record_from_dict(data: dict[str, Any]) -> CampaignClusterRecord:
        payload = dict(data)
        payload["members"] = [ClusterMemberRef(**m) for m in payload["members"]]
        return CampaignClusterRecord(**payload)

    def get(self, cluster_id: str) -> CampaignClusterRecord | None:
        data = self._load()
        record = data.get(cluster_id)
        return self._record_from_dict(record) if record is not None else None

    def list(self) -> list[CampaignClusterRecord]:
        return [self._record_from_dict(record) for record in self._load().values()]
