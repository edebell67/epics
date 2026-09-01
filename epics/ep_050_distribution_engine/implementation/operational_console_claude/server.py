#!/usr/bin/env python3
# epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py
# EP050 Operational Console v2 — local-only backend, wiring real Nodes 01/02/03/11-18.
#
# VERSION HISTORY
# v1.13.0 · 2026-08-21 · Adds the persistent Discovery 00A–00F API and canonical contract handoff
#   into the existing Node 15 pipeline without bypassing Node 01–05/11 evidence records.
# v1.12.0 · 2026-08-19 · Two fixes to the gates added in v1.11.0, found by directly reviewing the
#   live effect on all 4 real geo campaigns rather than accepting the gate's stated intent at face
#   value: (1) Node 11's keyword lists (owned by Gemini, edited directly here because they were
#   actively blocking every real campaign) scored ZERO on troubleshooting/urgency/commercial for
#   two genuine real query texts, confirmed programmatically -- widened with words grounded in
#   those real queries or direct synonyms of words already present, see
#   node_11/intent_classification.py v1.2.0. (2) Even after widening, "restore hot water quickly"
#   still scores commercial_intent_score=0.0 by nature -- urgent problem-description language
#   inherently omits transactional words. Node 11 now correctly computes urgency_level=HIGH for
#   this query though (matching Node 03's own registered urgency, for the first time). Added
#   URGENT_INTENT_LEVELS: the commercial-intent gate now accepts EITHER a nonzero commercial score
#   OR a real high/critical urgency as evidence of genuine demand -- both are freshly computed by
#   the classifier from the real query text, so this is not a reversion to the manual-field
#   shortcut considered and rejected earlier the same day.
# v1.11.0 · 2026-08-19 · Commercial-intent gate. Live-tested a deliberately implausible campaign
#   (mars_spaceship_builder, Catford) end to end: Node 05's non-zero-results check cannot tell a
#   real target from a nonsense one, since a live search for almost any topic returns SOMETHING --
#   this one genuinely returned 10 HTTP-200 results (NASA/SpaceX/YouTube/STEM pages), and the
#   campaign sailed straight through Node 11/15 to the exact same needs_facts state as every real
#   boiler campaign. Node 11's commercial_intent_score is unconditionally computed on every
#   classification (never Optional) and was already the cheapest real signal available at that
#   point in the pipeline, just unused by any gate. User's explicit, considered decision:
#   classifications scoring 0 are now excluded (new "stopped_low_commercial_intent" state),
#   accepting this is a blunt threshold that also excludes real quiet-but-real demand -- Greenwich/
#   Lewisham/Charlton/Eltham/Blackheath's own real signals all score 0.0 on "restore hot water
#   quickly" (no COMMERCIAL_KEYWORDS hit; genuine urgent demand that just hasn't used a buy-intent
#   word). Considered and rejected a content-plausibility check (does a result look like a real
#   local business) as more accurate but requiring per-result judgment that does not scale to large
#   campaign volumes, versus a scalar threshold which does. User: "maybe later we make the gates
#   configurable if there is a need to vary" -- MIN_COMMERCIAL_INTENT_SCORE is a single named
#   constant for exactly that future change, not scattered through the function bodies.
# v1.10.0 · 2026-08-19 · Node 05 provider migration fallout, three real fixes:
#   (1) DEMAND GATE BUG (the significant one). handle_node01_approve_phase2 read
#   record_dict["total_results"]/["top_results"] at the top level, but a DemandSignalRecord stores
#   those under metadata.search_result_summary -- the top-level keys have never existed. So EVERY
#   successful live fetch evaluated to has_real_demand=False and the candidate was marked
#   stopped_no_demand, silently discarding genuinely good markets. It survived undetected for the
#   node's entire life because Node 05's live fetch had never once succeeded (Google's Custom
#   Search API 403'd from the day it was wired up), so this branch was only ever reached via the
#   park path. Switching to a working provider exposed it instantly: all four real parked
#   candidates returned "no demand" while their own stored records held 10 real results each.
#   Now reads the real path, with the top-level keys kept as a fallback.
#   (2) PARKING IS NO LONGER TERMINAL. approve_phase2 accepts a parked candidate as a retry, since
#   parking means "infrastructure could not run the fetch" -- a condition that gets fixed. Before
#   this, the four candidates parked on the Google 403 could only be revived by hand-editing
#   run.json. The stale park reason is cleared and the retry recorded in lineage.
#   (3) READINESS REFLECTS THE REAL PROVIDER. live_fetch_status no longer reports Node 05 against
#   EP050_GOOGLE_CSE_* (a dead dependency); it resolves the Firecrawl credential for real, which
#   matters because that credential may come from the Firecrawl CLI's own store rather than an env
#   var -- a plain env-var check would report "missing" and park every candidate on a machine
#   where the CLI is authenticated.
# v1.9.4 · 2026-08-19 · Closes a real gap found and confirmed via direct user question ("is it
#   assumed that default message will be via a video?"): Node 18's video_asset_factory.py
#   unconditionally forces every asset into a video, never reading Node 14's real recommended
#   format (verified_local_listing_with_emergency_hours / step_by_step_troubleshooting_guide /
#   callout_extension_ad_24_7_emergency / community_recommendation_post -- none of them video).
#   Added node_18/alternate_asset_factory.py (v1.0.0), a sibling factory that registers the SAME
#   real, already-validated Node 17 AssetPayload as the final asset for those four real formats
#   instead of forcing it through a renderer it was never meant for -- reuses Node 17's own
#   lineage/PII/disclaimer validation rather than re-deriving it, and flags
#   community_recommendation_post as requires_human_review (matching the existing Node 24
#   human-in-the-loop finding already on record). New handle_node18_generate_by_format endpoint
#   dispatches on the asset's own real format: routes to the alternate registry for the four real
#   non-video formats, falls back to the existing (unchanged) video path for anything else.
#   handle_node18_generate/node18/generate itself is untouched -- this is a new sibling endpoint,
#   not a behavior change to the existing one. Live-verified against the real live run: the real
#   fixture's top-ranked format (verified_local_listing_with_emergency_hours) correctly produced a
#   real listing asset with genuine content (not a video), not merely a schema-valid stub. 1 new
#   test in test_console_server.py; full suite 88/88.
# v1.9.3 · 2026-08-18 · Fixes a real bug found live while actually completing a service-axis
#   candidate's product definition: candidate_status stayed stuck at pending_product_definition
#   forever, even after Node 02/03/04 were genuinely completed for it, because nothing ever
#   re-evaluated the static field. handle_node04_register now advances candidate_status from
#   pending_product_definition to pending_phase2_approval when Node 04 completes (Phase 1 is
#   genuinely done at that point -- same real-data requirement a geo-axis candidate already
#   started at, just earned by hand instead of copied). 1 new pytest case; verified live by
#   re-submitting Node 04 for the real boiler_service candidate and confirming it correctly
#   advanced to pending_phase2_approval / Phase 2 / Node 05.
# v1.9.2 · 2026-08-18 · Adds the global phase/node position matrix requested directly by the user
#   ("need a page/summary that shows... at a global level" P1-P7 counts, drilling down to
#   campaign/status/action). derive_campaign_position(meta) walks the exact same real artifact
#   checks run_pipeline_headless() uses to decide what to run next (read-only -- reports where a
#   campaign stands, never runs anything), returning {phase, node, action} for every real state a
#   campaign can be in, including surfacing the real park reason (e.g. Node 05's actual HTTP 403
#   text) as the action instead of a canned label. campaign_queue_snapshot() now includes phase/
#   node/action per campaign plus a phase_counts summary (1-7). 5 new pytest cases.
# v1.9.1 · 2026-08-18 · Fixes a real race condition found live: two near-simultaneous real clicks
#   of "Propose one-hop candidate campaigns" against the same run produced 16 candidates instead
#   of 8, plus one orphaned run whose Node 01 registration never completed -- handle_node01_
#   propose_candidates' check-then-write (load_run_meta -> check last_proposed_winner_id -> create
#   -> save_run_meta) let two concurrent requests both pass the idempotency check before either
#   had saved. Fixed with a single global threading.Lock (_PROPOSE_CANDIDATES_LOCK) around the
#   whole function -- correct given this is a local, single-operator console and the action only
#   ever fires on a freshly-detected winner, not a high-throughput path. New regression test fires
#   5 concurrent real requests and asserts exactly 8 candidates created with no orphans; verified
#   it reliably fails without the lock (reproduced the exact 16-candidate/orphan bug and a Windows
#   file-write collision) before confirming it passes 5/5 with the fix. Cleaned up the 8 real
#   duplicate/orphaned runs this bug produced on the live console.
# v1.9.0 · 2026-08-18 · Winner-replication & scale-out build (plans/20260818_1645_ep050_winner_
#   replication_and_scale_out.md, approved by direct user instruction after a multi-turn design
#   review). Also folds in Phase 6/7 (Nodes 28-37) console handler wiring from earlier this
#   session, which had shipped without its own version entry.
#   - Nodes 28-37: handle_node28_generate..handle_node37_generate, each selecting its real
#     upstream record by ID from this run's own state (attribution/qualification/routing/
#     performance/winner/amplification/allocation), same pattern as Nodes 19-27.
#   - Node 18 winner replication: handle_node18_replicate_winner reruns the real Node11-17 chain
#     against the SAME proven cluster/facts, varying only template_version per amplification
#     format -- never geography (would need real demand data for a market with none yet).
#   - Winner-triggered candidate clustering: shared/candidate_expansion.py (curated real geo-
#     adjacency + service-taxonomy, one-hop only, never a compound jump) backs
#     handle_node01_propose_candidates. Geo-axis candidates copy the source run's real Node
#     02/03/04/16 (product/audience/conversion/facts) under their own new target_id -- legitimate
#     since only geography changed; service-axis candidates stop at pending_product_definition
#     rather than fabricate a differently-scoped product description. Idempotent per winner_id
#     (last_proposed_winner_id) so repeated calls never mint duplicates.
#   - Phase 2 candidate approval gate: handle_node01_approve_phase2 -- a candidate's real Node 05
#     live-fetch only fires on explicit approval, never auto-run and never a fixture fallback.
#     Two distinct fail-closed stop states: parked (live-fetch unavailable for that node --
#     missing credentials, or a known constraint like Node 05's real, already-documented Search
#     403) vs. stopped_no_demand (fetch worked, genuinely found nothing).
#   - Cost ledger: append_lineage(cost_gbp=...) is opt-in per call site, never estimated. As of
#     this build no handler passes it -- nothing in this pipeline has a confirmed real,
#     currently-billed rate yet (locked in by a regression test meant to start failing the day
#     one does).
#   - Campaign Queue: derive_campaign_state()/GET /api/campaign_queue/run_pipeline_headless()/
#     POST .../pipeline/run_all -- an in-process driver (not the DOM-click runAllInPanel) that
#     calls the exact same real handlers, so many campaigns can run genuinely concurrently across
#     run_ids via ordinary concurrent requests (the server is already ThreadingHTTPServer; every
#     run's storage is already isolated). Idempotent and fail-closed at needs_facts/pending states.
#   - Bulk import: handle_bulk_import / POST /api/bulk_import -- one CSV row -> one real campaign
#     through the same real Node 01-04 validation as manual entry, no relaxed bulk-mode rules; one
#     bad row is reported and skipped, never blocks the rest.
#   13 new pytest cases added to test_console_server.py this session (65->78, all passing), plus
#   11 new cases in shared/test_candidate_expansion.py (all passing).
# v1.8.0 · 2026-08-18 · Adds a real public consumer intake: GET /intake?run=<id> serves a real
#   HTML form (job details, name, email, phone, consent), POST /api/runs/{id}/node27/public_intake
#   takes a real submission, splits it (raw PII/job content stored separately in
#   data/runs/{id}/public_intake_pii.json; only session_id/source/consent ever reaches Node 27)
#   and calls the real build_structured_lead_record() against the run's most recent Node 26
#   route. Closes the "no real consumer can reach this" gap for the intake side specifically --
#   a real browser submitting this real form now produces a real lead record, not a
#   console-driven fixture. Publishing this page publicly (a real domain/hosting) is a separate,
#   much larger step not done here.
# v1.7.0 · 2026-08-18 · Wires real console controls for Node 19 (Quality & Compliance) and
#   Phase 5's accepted subset (Nodes 20, 21, 26 -- Node 27 gets a working form too but stays out
#   of console_controls since it remains pending_acceptance, not accepted, honoring the existing
#   console_controls<=accepted_nodes invariant). Each handler looks its structured input up from
#   this run's own state by ID (asset_id/publication_plan_id/search_distribution_id/route_id)
#   rather than accepting raw JSON, since Nodes 20/21/26/27 each consume the full schema object
#   the node before them produced, not a hand-typeable business fact -- same pattern Node 18
#   already used for cluster_id/fact_ids. Node 19 consumes an existing meta["assets"] entry
#   (already produced by handle_node18_generate's Node 17 call), so no new upstream step was
#   needed to reach it. Nodes 22-25 remain deliberately unwired (mvp_deferred_nodes, an existing
#   project decision, not touched here). Per direct user instruction ("proceed" after "why not
#   [Phase 5-7 automated]").
# v1.6.0 · 2026-08-18 · Fixes a stale/false status: Phase 6 (Nodes 28-31) and Phase 7 (Nodes
#   32-37) were listed as not_started_nodes ("no allocation or work has begun"), which is false
#   -- both are implemented with real, tested code (26/26 own-suite tests re-verified passing
#   this session, plus a full 37-node golden-path integration test that found and confirmed a
#   real cross-node bug fix in this exact range). Moved to pending_acceptance_nodes instead of
#   accepted_nodes: Gemini self-reported both phases "100% complete" on the board (events
#   20260817T214103320_gemini_7304ee52, 20260817T215450113_gemini_f28641b7), but unlike Node 27
#   (which has an explicit "ACCEPTED" event from the orchestrator), no formal acceptance event
#   exists for Nodes 28-37 -- confirmed by grepping the board directly. Same class of status-page
#   bug the CHANGE REQUIRED fix (v1.2.0) already corrected for Phase 2; never applied to 6/7.
# v1.5.0 · 2026-08-18 · Adds GET /api/known_values, scanning every run's Node 01/02/03/04 storage
#   for previously-used target_type/service/market/geography/segment_name/problem/solution/
#   commercial_model/customer_outcome/success_criteria values (merged with a small curated seed
#   list), so console.js can render select-with-add-new controls instead of blank text boxes
#   across all of Phase 1 registration. Per direct user request ("the input not intuitive" /
#   "apply same to rest of Phase 1").
# v1.4.0 · 2026-08-17 · Wires the real automated live-ingestion methods added to Nodes 05-10/15/18
#   (register_from_live_source / register_from_live_aggregation / generate_and_register_from_
#   live_signals / generate_and_register_from_live_chain) as new /live POST endpoints alongside
#   the existing manual-entry endpoints, plus a GET /api/live_fetch_status endpoint reporting
#   whether EP050_LIVE_FETCH_ENABLED is set and which per-node credentials are present, without
#   exposing values. No manual endpoint's behavior changed; this only adds new routes.
# v1.3.0 · 2026-08-17 · URGENT ALLOCATION (board event 20260817T122525918_codex_phase2ops):
#   the user's live review rejected Phase 2 as status-only. Added real operational controls for
#   Node 04 (conversion definition, a hard constructor dependency of Node 05) and Nodes 05-10
#   (demand signal, question, social/video, competitor, community, trend), each wired to its
#   real registry class per-run with the same fail-closed lineage checks each node's own
#   contract already requires. Nodes 04-10 moved from "accepted, not wired" into console_controls.
# v1.2.0 · 2026-08-17 · CHANGE REQUIRED fix (board event 20260817T113648989_codex_781e7f99):
#   replaced the misleading implemented_nodes/locked_nodes binary in PHASES with five explicit
#   states (accepted_nodes/console_controls/pending_acceptance_nodes/mvp_deferred_nodes/
#   not_started_nodes), reconciled against board/workstream acceptance evidence for all 37
#   nodes. Phase 2 (Nodes 05-10) and Phase 1's Node 04 were previously falsely rendered as
#   "not implemented" when they are accepted at 100%, simply not wired as console controls.
# v1.1.0 · 2026-08-17 · Reactivated per allocation 20260817T095239426_codex_f21198e1, after
#   Node 15 and Node 18 both accepted at 100%. Added real Node 12/13/14 (internal pipeline
#   steps run deterministically from an existing classification, no dedicated form), Node 15
#   (campaign cluster generation), Node 16 (canonical fact registration), Node 17 (asset
#   payload generation, internal step of Node 18), and Node 18 (video asset factory) wiring.
#   Phase 3 and Phase 4 completion recalculated from real child evidence.
# v1.0.0 · 2026-08-17 · Initial local-only console backend for the seven-phase operator run.
#
# Scope: EP050 Operational UI v2 only, per allocation 20260817T001150693_codex_cd0dd339,
# reactivated by 20260817T095239426_codex_f21198e1. Local-only (127.0.0.1), fixture-only
# storage under data/runs/<run_id>/, no network call, no production datastore, no external
# side effect. Every route that touches a node imports the real Node 01/02/03/11-18 modules
# directly -- nothing is reimplemented here. Node 12/13/14 pipeline steps use each module's
# own deterministic default weights/candidates, so recomputing them from the same
# classification always yields the same opportunity/path/selection IDs and content.

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
IMPLEMENTATION_ROOT = ROOT.parent
DATA_ROOT = ROOT / "data" / "runs"
_DISCOVERY_SEARCH_SLOTS = threading.BoundedSemaphore(10)

for node_dir in (
    "node_01", "node_02", "node_03", "node_04", "node_05", "node_06", "node_07", "node_08",
    "node_09", "node_10", "node_11", "node_12", "node_13", "node_14",
    "node_15", "node_16", "node_17", "node_18", "node_19", "node_20", "node_21", "node_26",
    "node_27", "node_28", "node_29", "node_30", "node_31", "node_32", "node_33", "node_34",
    "node_35", "node_36", "node_37", "shared",
):
    sys.path.insert(0, str(IMPLEMENTATION_ROOT / node_dir))

import live_fetch  # noqa: E402
import candidate_expansion  # noqa: E402
import target_parameter_derivation  # noqa: E402
from discovery_engine import DiscoveryError, DiscoveryStore  # noqa: E402
import registration as node01  # noqa: E402
import product_intelligence as node02  # noqa: E402
import audience_definition as node03  # noqa: E402
import conversion_definition as node04  # noqa: E402
import search_demand_discovery as node05  # noqa: E402
import question_discovery as node06  # noqa: E402
import social_video_discovery as node07  # noqa: E402
import competitor_intelligence as node08  # noqa: E402
import community_intelligence as node09  # noqa: E402
import trend_detection as node10  # noqa: E402
import intent_classification as node11  # noqa: E402
import opportunity_scoring as node12  # noqa: E402
import demand_path_discovery as node13  # noqa: E402
import channel_placement_selection as node14  # noqa: E402
import campaign_cluster_generation as node15  # noqa: E402
import canonical_knowledge_store as node16  # noqa: E402
import content_utility_factory as node17  # noqa: E402
import video_asset_factory as node18  # noqa: E402
import alternate_asset_factory as node18b  # noqa: E402
import ep048_render_publish_trigger as node18_publish  # noqa: E402
import quality_compliance as node19  # noqa: E402
import publishing_scheduler as node20  # noqa: E402
import search_distribution as node21  # noqa: E402
import smart_destination_router as node26  # noqa: E402
import structured_lead_capture as node27  # noqa: E402
import offline_attribution as node28  # noqa: E402
import lead_qualification as node29  # noqa: E402
import lead_routing as node30  # noqa: E402
import lead_lifecycle_tracker as node31  # noqa: E402
import performance_warehouse as node32  # noqa: E402
import outcome_feedback as node33  # noqa: E402
import winner_detection as node34  # noqa: E402
import winner_amplification as node35  # noqa: E402
import effort_allocation as node36  # noqa: E402
import distribution_knowledge_base as node37  # noqa: E402

RUN_ID_PATTERN = re.compile(r"^run_[0-9]{8}_[0-9]{6}_[0-9a-f]{8}$")


class ApiError(Exception):
    def __init__(self, status: int, error: str, message: str):
        super().__init__(message)
        self.status = status
        self.error = error
        self.message = message


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_run_id() -> str:
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def run_dir(run_id: str) -> Path:
    if not RUN_ID_PATTERN.match(run_id):
        raise ApiError(400, "invalid_run_id", f"run_id {run_id!r} does not match the expected format")
    return DATA_ROOT / run_id


def run_meta_path(run_id: str) -> Path:
    return run_dir(run_id) / "run.json"


def load_run_meta(run_id: str) -> dict[str, Any]:
    path = run_meta_path(run_id)
    if not path.exists():
        raise ApiError(404, "run_not_found", f"run_id {run_id!r} does not exist")
    return json.loads(path.read_text(encoding="utf-8"))


def save_run_meta(run_id: str, meta: dict[str, Any]) -> None:
    path = run_meta_path(run_id)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def append_lineage(
    meta: dict[str, Any], *, phase: int, node: str, action: str, summary: str, cost_gbp: float | None = None,
) -> None:
    """cost_gbp is opt-in per call site, never inferred or estimated -- a real paid action stamps
    its own real, provider-published rate here; every other action simply omits it, exactly as
    today. See plans/20260818_1645_ep050_winner_replication_and_scale_out.md §7. As of 2026-08-18
    no call site in this file passes cost_gbp: nothing in this pipeline has a confirmed real,
    currently-billed rate to attach yet (Node 05's live Google Custom Search call errors with a
    403 before any confirmed billable request completes) -- the field exists so the moment one
    does, it has somewhere real to go, without a schema change."""
    event: dict[str, Any] = {"phase": phase, "node": node, "action": action, "summary": summary, "at": now_iso()}
    if cost_gbp is not None:
        event["cost_gbp"] = round(float(cost_gbp), 2)
    meta.setdefault("lineage", []).append(event)


def create_run() -> dict[str, Any]:
    run_id = new_run_id()
    directory = run_dir(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_id": run_id,
        "created_at": now_iso(),
        "target": None,
        "product": None,
        "audience": [],
        "classifications": [],
        "lineage": [],
    }
    append_lineage(meta, phase=0, node="run", action="created", summary="Run created")
    save_run_meta(run_id, meta)
    return meta


def list_runs() -> list[dict[str, Any]]:
    if not DATA_ROOT.exists():
        return []
    results = []
    for path in sorted(DATA_ROOT.glob("*/run.json")):
        try:
            results.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return results


def known_values() -> dict[str, list[str]]:
    """Distinct values previously used for the free-text-but-usually-repeated Node 01/03 fields,
    scanned across every run's real storage, merged with a small curated seed list so the
    console can offer a select-with-add-new instead of a blank text box on first use. Historical
    values only -- nothing here is invented."""
    seeds: dict[str, set[str]] = {
        "target_type": {"service_market", "local_service_business", "product_category"},
        "service": set(),
        "market": set(),
        "locality": set(),
        "region": {"London", "South East England", "South West England", "North West England", "Scotland", "Wales"},
        "country": {"UK", "Ireland", "USA"},
        "segment_name": set(),
        "problem": set(),
        "solution": set(),
        "commercial_model": set(),
        "customer_outcome": set(),
        "success_criteria": set(),
    }
    if DATA_ROOT.exists():
        for path in DATA_ROOT.glob("*/node_01_targets.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for record in data.values():
                if not isinstance(record, dict):
                    continue
                for key in ("target_type", "service", "market"):
                    value = record.get(key)
                    if isinstance(value, str) and value.strip():
                        seeds[key].add(value)
                geography = record.get("geography") or {}
                if isinstance(geography, dict):
                    for key in ("locality", "region", "country"):
                        value = geography.get(key)
                        if isinstance(value, str) and value.strip():
                            seeds[key].add(value)
        for path in DATA_ROOT.glob("*/node_03_audience_segments.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for record in data.values():
                if not isinstance(record, dict):
                    continue
                value = record.get("segment_name")
                if isinstance(value, str) and value.strip():
                    seeds["segment_name"].add(value)
                geography = record.get("eligibility_geography") or {}
                if isinstance(geography, dict):
                    for key in ("locality", "region", "country"):
                        value = geography.get(key)
                        if isinstance(value, str) and value.strip():
                            seeds[key].add(value)
        for path in DATA_ROOT.glob("*/node_02_product_intelligence.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for record in data.values():
                if not isinstance(record, dict):
                    continue
                for key in ("problem", "solution", "commercial_model", "customer_outcome"):
                    value = record.get(key)
                    if isinstance(value, str) and value.strip():
                        seeds[key].add(value)
        for path in DATA_ROOT.glob("*/node_04_conversion.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for record in data.values():
                if not isinstance(record, dict):
                    continue
                value = record.get("success_criteria")
                if isinstance(value, str) and value.strip():
                    seeds["success_criteria"].add(value)
    return {key: sorted(values) for key, values in seeds.items()}


def node01_registry(run_id: str) -> node01.TargetRegistry:
    return node01.TargetRegistry(run_dir(run_id) / "node_01_targets.json")


def node02_registry(run_id: str) -> node02.ProductIntelligenceRegistry:
    return node02.ProductIntelligenceRegistry(run_dir(run_id) / "node_02_product_intelligence.json", node01_registry(run_id))


def node03_registry(run_id: str) -> node03.AudienceSegmentRegistry:
    return node03.AudienceSegmentRegistry(
        run_dir(run_id) / "node_03_audience_segments.json", node01_registry(run_id), node02_registry(run_id)
    )


def node04_registry(run_id: str) -> node04.ConversionDefinitionRegistry:
    return node04.ConversionDefinitionRegistry(
        run_dir(run_id) / "node_04_conversion.json", node01_registry(run_id), node02_registry(run_id), node03_registry(run_id)
    )


def node05_registry(run_id: str) -> node05.DemandSignalRegistry:
    return node05.DemandSignalRegistry(
        run_dir(run_id) / "node_05_demand_signals.json",
        node01_registry(run_id), node02_registry(run_id), node03_registry(run_id), node04_registry(run_id),
    )


def node06_registry(run_id: str) -> node06.QuestionRegistry:
    return node06.QuestionRegistry(
        run_dir(run_id) / "node_06_questions.json",
        node01_registry(run_id), node02_registry(run_id), node03_registry(run_id), node04_registry(run_id),
        node05_registry(run_id),
    )


def node07_registry(run_id: str) -> node07.SocialVideoSignalRegistry:
    return node07.SocialVideoSignalRegistry(
        run_dir(run_id) / "node_07_social_video.json",
        node01_registry(run_id), node02_registry(run_id), node03_registry(run_id), node04_registry(run_id),
        node05_registry(run_id), node06_registry(run_id),
    )


def node08_registry(run_id: str) -> node08.CompetitorSignalRegistry:
    return node08.CompetitorSignalRegistry(
        run_dir(run_id) / "node_08_competitor.json",
        node01_registry(run_id), node02_registry(run_id), node03_registry(run_id), node04_registry(run_id),
        node05_registry(run_id), node06_registry(run_id), node07_registry(run_id),
    )


def node09_registry(run_id: str) -> node09.CommunitySignalRegistry:
    return node09.CommunitySignalRegistry(
        run_dir(run_id) / "node_09_community.json",
        node01_registry(run_id), node02_registry(run_id), node03_registry(run_id), node04_registry(run_id),
        node05_registry(run_id), node06_registry(run_id), node07_registry(run_id), node08_registry(run_id),
    )


def node10_registry(run_id: str) -> node10.TrendSignalRegistry:
    return node10.TrendSignalRegistry(
        run_dir(run_id) / "node_10_trends.json",
        node01_registry(run_id), node02_registry(run_id), node03_registry(run_id), node04_registry(run_id),
        node05_registry(run_id), node06_registry(run_id), node07_registry(run_id), node08_registry(run_id),
        node09_registry(run_id),
    )


def handle_node01_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    registry = node01_registry(run_id)
    try:
        record = registry.register(**body)
    except node01.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node01.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    meta["target"] = record.to_dict()
    append_lineage(meta, phase=1, node="node_01", action="register_target", summary=f"Registered {record.target_id}")
    save_run_meta(run_id, meta)
    return record.to_dict()


def handle_node02_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("target"):
        raise ApiError(409, "no_target", "Register a Node 01 target before describing the product")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    registry = node02_registry(run_id)
    try:
        record = registry.register(**body)
    except node02.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node02.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node02.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    meta["product"] = record.to_dict()
    append_lineage(meta, phase=1, node="node_02", action="register_product", summary=f"Described product for {record.target_id}")
    save_run_meta(run_id, meta)
    return record.to_dict()


def handle_node03_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("target"):
        raise ApiError(409, "no_target", "Register a Node 01 target before defining an audience")
    if not meta.get("product"):
        raise ApiError(409, "no_product", "Describe the product (Node 02) before defining an audience")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    registry = node03_registry(run_id)
    try:
        record = registry.register(**body)
    except node03.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node03.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node03.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    meta.setdefault("audience", [])
    existing_ids = {segment["segment_id"] for segment in meta["audience"]}
    if record.segment_id not in existing_ids:
        meta["audience"].append(record.to_dict())
    append_lineage(meta, phase=1, node="node_03", action="register_audience", summary=f"Defined segment {record.segment_id}")
    save_run_meta(run_id, meta)
    return record.to_dict()


# Standard master-spec conversion funnel, used as the Node 04 default so the console form only
# needs to ask for success_criteria -- the funnel itself is not something an operator should be
# free-typing per run.
_NODE04_DEFAULT_TRANSITIONS = [
    ["visit", "engage"], ["engage", "tool_use"], ["tool_use", "enquiry"], ["enquiry", "lead"],
    ["lead", "qualified_lead"], ["qualified_lead", "booking"], ["booking", "sale"], ["sale", "revenue"],
]


def handle_node04_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("target"):
        raise ApiError(409, "no_target", "Register a Node 01 target before defining conversion stages")
    if not meta.get("product"):
        raise ApiError(409, "no_product", "Describe the product (Node 02) before defining conversion stages")
    if not meta.get("audience"):
        raise ApiError(409, "no_audience", "Define an audience segment (Node 03) before defining conversion stages")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    body.setdefault("stages", node04.MASTER_SPEC_STAGES)
    body.setdefault("allowed_transitions", _NODE04_DEFAULT_TRANSITIONS)
    body.setdefault("success_stage_id", "sale")
    body.setdefault("success_criteria", "A lead reaches the sale stage with a recorded outcome.")
    registry = node04_registry(run_id)
    try:
        record = registry.register(**body)
    except node04.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node04.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node04.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    meta["conversion"] = record.to_dict()
    # A service-axis candidate starts pending_product_definition (plan §4: never auto-copy a
    # differently-scoped product description). Completing Node 04 means Phase 1 is now genuinely
    # done for it -- the SAME real-data requirement a geo-axis candidate already had, just earned
    # by hand instead of copied -- so it advances to the same pending_phase2_approval gate a
    # geo-axis candidate starts at. Real bug found live 2026-08-18: without this, candidate_status
    # stayed stuck at pending_product_definition forever even after Node 02/03/04 were genuinely
    # completed, since nothing ever re-evaluated the static field.
    if meta.get("candidate_status") == CANDIDATE_STATUS_PENDING_PRODUCT:
        meta["candidate_status"] = CANDIDATE_STATUS_PENDING_PHASE2_APPROVAL
    append_lineage(meta, phase=1, node="node_04", action="define_conversion", summary=f"Defined conversion funnel for {record.target_id}")
    save_run_meta(run_id, meta)
    return record.to_dict()


# --- Winner-triggered candidate clustering (plan: 20260818_1645_ep050_winner_replication_and_scale_out.md §4) ---
# A candidate is a NEW, independent campaign (its own run_id), never a relabeled copy of the
# winner's content. Geo-axis candidates (same service, adjacent real geo) reuse the winner's real
# Node 02/03/04 definitions verbatim -- legitimate, since only the location changed, not the
# offering -- except Node 03's eligibility_geography, which must reflect the candidate's own real
# geography. Service-axis candidates (same geo, adjacent real service) stop after Node 01: a
# "boiler_service" product/audience description is not truthfully the same as "boiler_repair"'s,
# so it is never auto-copied -- the candidate waits in pending_product_definition for a human (or a
# future bulk-import row) to describe it for real before Phase 2 can even be requested.

CANDIDATE_STATUS_PENDING_PRODUCT = "pending_product_definition"
CANDIDATE_STATUS_PENDING_PHASE2_APPROVAL = "pending_phase2_approval"
CANDIDATE_STATUS_PARKED = "parked"
CANDIDATE_STATUS_STOPPED_NO_DEMAND = "stopped_no_demand"

_NODE02_COPYABLE_FIELDS = (
    "problem", "solution", "features", "benefits", "differentiators", "commercial_model",
    "customer_outcome", "evidence_sources",
)
_NODE03_COPYABLE_FIELDS = ("segment_name", "needs", "pains", "urgency", "exclusions", "evidence_sources")
_NODE16_COPYABLE_FIELDS = ("topic", "claim", "verification_source")


def _register_candidate_run(source_meta: dict[str, Any], candidate_payload: dict[str, Any], axis: str, winner: dict[str, Any]) -> dict[str, Any]:
    new_meta = create_run()
    new_run_id = new_meta["run_id"]
    handle_node01_register(new_run_id, candidate_payload)  # real Node 01 validation, no bypass
    if axis == "geo":
        product_body = {k: v for k, v in source_meta["product"].items() if k in _NODE02_COPYABLE_FIELDS}
        handle_node02_register(new_run_id, product_body)
        segment_body = {k: v for k, v in source_meta["audience"][0].items() if k in _NODE03_COPYABLE_FIELDS}
        segment_body["eligibility_geography"] = candidate_payload["geography"]
        handle_node03_register(new_run_id, segment_body)
        handle_node04_register(new_run_id, {})
        # Node 16 facts describe the service/product itself (e.g. real boiler pressure specs),
        # not the geography -- true regardless of which London borough, so legitimate to copy
        # verbatim under the candidate's own new target_id (same rationale as Node 02/03 above).
        for fact in source_meta.get("facts", []):
            handle_node16_fact(new_run_id, {k: v for k, v in fact.items() if k in _NODE16_COPYABLE_FIELDS})
        status = CANDIDATE_STATUS_PENDING_PHASE2_APPROVAL
    else:
        status = CANDIDATE_STATUS_PENDING_PRODUCT
    new_meta = load_run_meta(new_run_id)
    new_meta["candidate_source"] = {
        "source_run_id": source_meta["run_id"], "source_target_id": source_meta["target"]["target_id"],
        "winner_channel": winner.get("channel"), "axis": axis,
    }
    new_meta["candidate_status"] = status
    append_lineage(
        new_meta, phase=1, node="node_01", action="candidate_registered",
        summary=f"Candidate ({axis} axis) spawned from winner in {source_meta['run_id']}",
    )
    save_run_meta(new_run_id, new_meta)
    return new_meta


# Guards the whole check-then-write in handle_node01_propose_candidates below: load_run_meta,
# check last_proposed_winner_id, create candidates, save_run_meta are four separate steps against
# a plain JSON file, so two concurrent requests for the same run can both pass the check before
# either has saved -- observed for real (2026-08-18): two near-simultaneous clicks produced 16
# candidates instead of 8, plus one orphaned run whose Node 01 registration didn't complete. A
# single global lock is enough here (not a per-run lock dict): this is a local, single-operator
# console, and propose_candidates only ever fires when a winner is freshly detected -- a rare,
# human-triggered action, not a high-throughput path -- so serializing it entirely costs nothing
# real while removing the race outright.
_PROPOSE_CANDIDATES_LOCK = threading.Lock()


def handle_node01_propose_candidates(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    with _PROPOSE_CANDIDATES_LOCK:
        meta = load_run_meta(run_id)
        if not meta.get("target"):
            raise ApiError(409, "no_target", "Register a Node 01 target before proposing candidates")
        winners = meta.get("winners") or []
        winner = next((w for w in winners if w.get("is_winner")), None)
        if winner is None:
            raise ApiError(409, "no_winner", "Run Node 34 (winner detection) before proposing replication candidates")
        if not meta.get("product") or not meta.get("audience"):
            raise ApiError(409, "no_product_or_audience", "Geo-axis candidates need this run's own Node 02/03 already registered")
        if meta.get("last_proposed_winner_id") == winner["winner_id"]:
            # Idempotent, not an error: repeated calls for the same winner (e.g. runFullPipeline
            # re-run after candidates already exist) must not keep minting duplicate campaigns.
            return {"source_run_id": run_id, "winner_channel": winner.get("channel"), "created": [], "failed": [],
                    "note": f"Candidates already proposed for winner {winner['winner_id']!r}"}

        try:
            geo_candidates = candidate_expansion.derive_adjacent_geo_candidates(meta["target"])
        except candidate_expansion.DerivationError:
            geo_candidates = []
        try:
            service_candidates = candidate_expansion.derive_adjacent_service_candidates(meta["target"])
        except candidate_expansion.DerivationError:
            service_candidates = []
        created: list[dict[str, Any]] = []
        failed: list[dict[str, str]] = []
        for axis, candidates in (("geo", geo_candidates), ("service", service_candidates)):
            for payload in candidates:
                try:
                    created.append(_register_candidate_run(meta, payload, axis, winner))
                except ApiError as exc:
                    failed.append({"axis": axis, "candidate": f"{payload['service']}_{payload['geography']['locality']}", "error": exc.message})

        meta["last_proposed_winner_id"] = winner["winner_id"]
        append_lineage(
            meta, phase=1, node="node_01", action="propose_candidates",
            summary=f"Proposed {len(created)} candidate(s) from winning channel {winner.get('channel')}; {len(failed)} failed",
        )
        save_run_meta(run_id, meta)
        return {
            "source_run_id": run_id, "winner_channel": winner.get("channel"),
            "created": [{"run_id": m["run_id"], "target": m["target"], "candidate_status": m["candidate_status"], "axis": m["candidate_source"]["axis"]} for m in created],
            "failed": failed,
        }


_RETRYABLE_APPROVAL_STATUSES = (CANDIDATE_STATUS_PENDING_PHASE2_APPROVAL, CANDIDATE_STATUS_PARKED)


def _park_candidate(run_id: str, meta: dict[str, Any], reason: str) -> dict[str, Any]:
    meta["candidate_status"] = CANDIDATE_STATUS_PARKED
    meta["candidate_park_reason"] = reason
    append_lineage(meta, phase=2, node="node_05", action="phase2_approval_parked", summary=f"Parked: {reason}")
    save_run_meta(run_id, meta)
    return {"run_id": run_id, "candidate_status": meta["candidate_status"], "reason": reason}


def handle_node01_approve_phase2(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """The one human approval point before a candidate's real Node 05 live-fetch fires (plan §4
    correction, §9 gate 1). Never falls back to a synthetic/fixture signal: a node that isn't
    ready (missing credentials, or a known constraint like Node 05's own documented Search 403)
    parks the candidate; a fetch that succeeds but genuinely finds no demand stops it,
    fail-closed -- both distinct from a real signal, which lets the candidate proceed."""
    meta = load_run_meta(run_id)
    if meta.get("candidate_status") not in _RETRYABLE_APPROVAL_STATUSES:
        raise ApiError(
            409, "not_pending_approval",
            f"run_id {run_id!r} is not awaiting Phase 2 approval (candidate_status={meta.get('candidate_status')!r})",
        )
    was_parked = meta.get("candidate_status") == CANDIDATE_STATUS_PARKED
    if was_parked:
        # A parked candidate is one whose real live-fetch could not run for an infrastructure
        # reason (missing credential, provider outage, provider refusing the request). That reason
        # can be fixed -- as it was on 2026-08-19, when Node 05 moved off Google's closed Custom
        # Search API to Firecrawl -- so parking must not be terminal. Retrying re-runs the same
        # real fetch and can only reach a real outcome: proceed, park again, or stop_no_demand.
        # The previous park reason is cleared here so a stale one can never be read as current.
        meta.pop("candidate_park_reason", None)
        append_lineage(meta, phase=2, node="node_05", action="phase2_approval_retried",
                       summary="Previously parked candidate retried after the blocking condition was resolved")

    status = live_fetch_status()
    node05_status = status["nodes"]["05"]
    if not node05_status["ready"]:
        reason = "live_fetch_disabled (EP050_LIVE_FETCH_ENABLED is not set)" if not status["live_fetch_enabled"] \
            else f"missing credentials: {node05_status['missing_vars']}"
        return _park_candidate(run_id, meta, reason)

    topic = body.get("topic")
    if not topic:
        try:
            topic = target_parameter_derivation.derive_primary_topic(meta["audience"][0])
        except target_parameter_derivation.DerivationError as exc:
            raise ApiError(400, "validation_error", str(exc)) from exc

    try:
        record_dict = handle_node05_live(run_id, {"topic": topic})
    except ApiError as exc:
        if exc.error in ("live_fetch_disabled", "missing_credential", "live_fetch_failed"):
            meta = load_run_meta(run_id)  # handle_node05_live doesn't persist on a raised error
            return _park_candidate(run_id, meta, exc.message)
        raise

    meta = load_run_meta(run_id)
    # The demand gate must read where Node 05 actually stores its search summary. handle_node05_live
    # returns a DemandSignalRecord dict, whose search results live under
    # metadata.search_result_summary -- NOT at the top level. Reading the top level (as this did
    # until 2026-08-19) always yielded total_results="0" and no top_results, so EVERY successful
    # fetch was classified stopped_no_demand, silently killing genuinely good candidates. The bug
    # survived undetected because Node 05's live fetch had never once succeeded: Google's Custom
    # Search API returned 403 from the day it was wired up, so this branch was only ever reached
    # via the park path. The first working fetch (Firecrawl) exposed it immediately -- all four
    # real parked candidates came back "no demand" while their stored records held 10 real results.
    # Top-level keys are still honoured as a fallback so any other caller shape keeps working.
    summary = (record_dict.get("metadata") or {}).get("search_result_summary") or {}
    total_results_raw = summary.get("total_results") or record_dict.get("total_results") or "0"
    top_results = summary.get("top_results") or record_dict.get("top_results") or []
    try:
        total_results_count = int(str(total_results_raw).strip())
    except ValueError:
        total_results_count = 0
    # Explicit numeric > 0, not a string inequality against "0" -- a string check would (in
    # principle) treat "00" or "0.0" as non-zero. real value today (str(len(items))) never
    # produces those, but the numeric comparison is the actually-correct rule and costs nothing.
    has_real_demand = total_results_count > 0 or bool(top_results)
    if not has_real_demand:
        meta["candidate_status"] = CANDIDATE_STATUS_STOPPED_NO_DEMAND
        append_lineage(meta, phase=2, node="node_05", action="phase2_stopped_no_demand", summary="Live-fetch succeeded but found no real demand for this candidate")
        save_run_meta(run_id, meta)
        return {"run_id": run_id, "candidate_status": meta["candidate_status"], "signal": record_dict}

    meta["candidate_status"] = None
    append_lineage(meta, phase=2, node="node_05", action="phase2_approved", summary=f"Real demand signal {record_dict['signal_id']} confirmed; candidate proceeds")
    save_run_meta(run_id, meta)
    return {"run_id": run_id, "candidate_status": meta["candidate_status"], "signal": record_dict}


def handle_node05_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("conversion"):
        raise ApiError(409, "no_conversion", "Define conversion stages (Node 04) before recording a demand signal")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    registry = node05_registry(run_id)
    try:
        record = registry.register(**body)
    except node05.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node05.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node05.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("demand_signals", [])
    if not any(s["signal_id"] == record_dict["signal_id"] for s in meta["demand_signals"]):
        meta["demand_signals"].append(record_dict)
    append_lineage(meta, phase=2, node="node_05", action="register_demand_signal", summary=f"Recorded demand signal {record_dict['signal_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node06_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("demand_signals"):
        raise ApiError(409, "no_demand_signal", "Record a demand signal (Node 05) before recording a question")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    registry = node06_registry(run_id)
    try:
        record = registry.register(**body)
    except node06.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node06.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node06.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("questions", [])
    if not any(q["question_id"] == record_dict["question_id"] for q in meta["questions"]):
        meta["questions"].append(record_dict)
    append_lineage(meta, phase=2, node="node_06", action="register_question", summary=f"Recorded question {record_dict['question_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node07_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("questions"):
        raise ApiError(409, "no_question", "Record a question (Node 06) before recording a social/video signal")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    registry = node07_registry(run_id)
    try:
        record = registry.register(**body)
    except node07.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node07.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node07.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("social_video_signals", [])
    if not any(s["signal_id"] == record_dict["signal_id"] for s in meta["social_video_signals"]):
        meta["social_video_signals"].append(record_dict)
    append_lineage(meta, phase=2, node="node_07", action="register_social_video_signal", summary=f"Recorded social/video signal {record_dict['signal_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node08_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("social_video_signals"):
        raise ApiError(409, "no_social_video_signal", "Record a social/video signal (Node 07) before recording a competitor signal")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    registry = node08_registry(run_id)
    try:
        record = registry.register(**body)
    except node08.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node08.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node08.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("competitor_signals", [])
    if not any(s["signal_id"] == record_dict["signal_id"] for s in meta["competitor_signals"]):
        meta["competitor_signals"].append(record_dict)
    append_lineage(meta, phase=2, node="node_08", action="register_competitor_signal", summary=f"Recorded competitor signal {record_dict['signal_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node09_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("competitor_signals"):
        raise ApiError(409, "no_competitor_signal", "Record a competitor signal (Node 08) before recording a community signal")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    registry = node09_registry(run_id)
    try:
        record = registry.register(**body)
    except node09.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node09.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node09.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("community_signals", [])
    if not any(s["signal_id"] == record_dict["signal_id"] for s in meta["community_signals"]):
        meta["community_signals"].append(record_dict)
    append_lineage(meta, phase=2, node="node_09", action="register_community_signal", summary=f"Recorded community signal {record_dict['signal_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node10_register(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("community_signals"):
        raise ApiError(409, "no_community_signal", "Record a community signal (Node 09) before recording a trend")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    registry = node10_registry(run_id)
    try:
        record = registry.register(**body)
    except node10.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node10.UnknownTargetError as exc:
        raise ApiError(409, "unknown_target", str(exc)) from exc
    except node10.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("trends", [])
    if not any(t["trend_id"] == record_dict["trend_id"] for t in meta["trends"]):
        meta["trends"].append(record_dict)
    append_lineage(meta, phase=2, node="node_10", action="register_trend", summary=f"Recorded trend {record_dict['trend_id']}")
    save_run_meta(run_id, meta)
    return record_dict


# --- Live-fetch endpoints (Nodes 05-10): wire the automated ingestion methods added to each
# node's registry, alongside (not replacing) the manual-entry endpoints above. Every one of
# these is fail-closed off by default behind EP050_LIVE_FETCH_ENABLED=1 -- see live_fetch.py.

LIVE_FETCH_CREDENTIAL_VARS: dict[str, list[str]] = {
    # Node 05 moved off Google Custom Search to Firecrawl on 2026-08-19 (Google closed that API to
    # new customers). Its credential is deliberately NOT listed here: resolve_firecrawl_credentials()
    # accepts either EP050_FIRECRAWL_API_KEY or the Firecrawl CLI's own stored credentials, so a
    # plain env-var presence check would wrongly report "missing" -- and therefore park every
    # candidate -- on a machine where the CLI is authenticated. See _node05_readiness().
    "05": [],
    "06": [],  # EP050_STACKEXCHANGE_KEY is optional, raises quota only
    "07": ["EP050_YOUTUBE_API_KEY"],
    "08": [],
    "09": ["EP050_REDDIT_CLIENT_ID", "EP050_REDDIT_CLIENT_SECRET"],
    "10": [],
}


def _node05_readiness() -> tuple[bool, list[str]]:
    """Resolve Node 05's Firecrawl credential for real rather than probing an env var name.

    Returns (credential_available, missing_vars). Performs no network call -- it only asks whether
    a credential can be found at all, which is exactly what the approval gate needs to decide
    between "park this candidate, we cannot search" and "go and search".
    """
    try:
        live_fetch.resolve_firecrawl_credentials()
    except live_fetch.MissingCredentialError:
        return False, [live_fetch.FIRECRAWL_API_KEY_ENV]
    return True, []


def live_fetch_status() -> dict[str, Any]:
    enabled = os.environ.get(live_fetch.LIVE_FETCH_ENABLED_ENV) == "1"
    nodes: dict[str, Any] = {}
    for node_id, required_vars in LIVE_FETCH_CREDENTIAL_VARS.items():
        missing = [v for v in required_vars if not os.environ.get(v)]
        if node_id == "05":
            has_credential, missing = _node05_readiness()
            nodes[node_id] = {
                "required_vars": [live_fetch.FIRECRAWL_API_KEY_ENV],
                "missing_vars": missing,
                "ready": enabled and has_credential,
                "provider": "firecrawl",
            }
            continue
        nodes[node_id] = {"required_vars": required_vars, "missing_vars": missing, "ready": enabled and not missing}
    return {"live_fetch_enabled": enabled, "nodes": nodes}


def _map_live_fetch_error(exc: Exception) -> ApiError:
    if isinstance(exc, live_fetch.LiveFetchDisabledError):
        return ApiError(503, "live_fetch_disabled", str(exc))
    if isinstance(exc, live_fetch.MissingCredentialError):
        return ApiError(503, "missing_credential", str(exc))
    if isinstance(exc, live_fetch.LiveFetchRequestError):
        return ApiError(502, "live_fetch_failed", str(exc))
    return ApiError(500, "live_fetch_error", str(exc))


def handle_node05_live(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("conversion"):
        raise ApiError(409, "no_conversion", "Define conversion stages (Node 04) before a live demand fetch")
    topic = body.get("topic")
    if not topic:
        raise ApiError(400, "validation_error", "topic is required")
    target = meta["target"]
    geography = body.get("geography") or target["geography"]
    service_context = body.get("service_context") or {
        "service_name": target.get("service", ""), "market_segment": target.get("market", ""),
    }
    registry = node05_registry(run_id)
    try:
        record = registry.register_from_live_source(
            signal_id=body.get("signal_id") or f"sig_live_{uuid.uuid4().hex[:8]}",
            target_id=target["target_id"], topic=topic, geography=geography, service_context=service_context,
        )
    except live_fetch.LiveFetchError as exc:
        raise _map_live_fetch_error(exc) from exc
    except node05.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("demand_signals", [])
    if not any(s["signal_id"] == record_dict["signal_id"] for s in meta["demand_signals"]):
        meta["demand_signals"].append(record_dict)
    append_lineage(meta, phase=2, node="node_05", action="register_demand_signal_live", summary=f"Live-fetched demand signal {record_dict['signal_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node06_live(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("demand_signals"):
        raise ApiError(409, "no_demand_signal", "Record a demand signal (Node 05) before a live question fetch")
    topic = body.get("topic")
    if not topic:
        raise ApiError(400, "validation_error", "topic is required")
    target = meta["target"]
    geography = body.get("geography") or target["geography"]
    registry = node06_registry(run_id)
    try:
        record = registry.register_from_live_source(
            question_id=body.get("question_id") or f"q_live_{uuid.uuid4().hex[:8]}",
            target_id=target["target_id"], topic=topic, geography=geography,
            site=body.get("site", "diy.stackexchange.com"),
        )
    except live_fetch.LiveFetchError as exc:
        raise _map_live_fetch_error(exc) from exc
    except node06.NoLiveResultsError as exc:
        raise ApiError(404, "no_live_results", str(exc)) from exc
    except node06.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("questions", [])
    if not any(q["question_id"] == record_dict["question_id"] for q in meta["questions"]):
        meta["questions"].append(record_dict)
    append_lineage(meta, phase=2, node="node_06", action="register_question_live", summary=f"Live-fetched question {record_dict['question_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node07_live(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("questions"):
        raise ApiError(409, "no_question", "Record a question (Node 06) before a live social/video fetch")
    topic = body.get("topic")
    if not topic:
        raise ApiError(400, "validation_error", "topic is required")
    target = meta["target"]
    geography = body.get("geography") or target["geography"]
    registry = node07_registry(run_id)
    try:
        record = registry.register_from_live_source(
            signal_id=body.get("signal_id") or f"sv_live_{uuid.uuid4().hex[:8]}",
            target_id=target["target_id"], topic=topic, geography=geography,
        )
    except live_fetch.LiveFetchError as exc:
        raise _map_live_fetch_error(exc) from exc
    except node07.NoLiveResultsError as exc:
        raise ApiError(404, "no_live_results", str(exc)) from exc
    except node07.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("social_video_signals", [])
    if not any(s["signal_id"] == record_dict["signal_id"] for s in meta["social_video_signals"]):
        meta["social_video_signals"].append(record_dict)
    append_lineage(meta, phase=2, node="node_07", action="register_social_video_signal_live", summary=f"Live-fetched social/video signal {record_dict['signal_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node08_live(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("social_video_signals"):
        raise ApiError(409, "no_social_video_signal", "Record a social/video signal (Node 07) before a live competitor fetch")
    competitor_url = body.get("competitor_url")
    topic = body.get("topic")
    query = body.get("query")
    if not competitor_url:
        raise ApiError(400, "validation_error", "competitor_url is required")
    if not topic:
        raise ApiError(400, "validation_error", "topic is required")
    if not query:
        raise ApiError(400, "validation_error", "query is required")
    target = meta["target"]
    geography = body.get("geography") or target["geography"]
    registry = node08_registry(run_id)
    try:
        record = registry.register_from_live_source(
            signal_id=body.get("signal_id") or f"cp_live_{uuid.uuid4().hex[:8]}",
            target_id=target["target_id"], competitor_url=competitor_url, topic=topic, query=query,
            geography=geography, channel=body.get("channel", "website"),
        )
    except live_fetch.LiveFetchError as exc:
        raise _map_live_fetch_error(exc) from exc
    except node08.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("competitor_signals", [])
    if not any(s["signal_id"] == record_dict["signal_id"] for s in meta["competitor_signals"]):
        meta["competitor_signals"].append(record_dict)
    append_lineage(meta, phase=2, node="node_08", action="register_competitor_signal_live", summary=f"Live-fetched competitor signal {record_dict['signal_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node09_live(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("competitor_signals"):
        raise ApiError(409, "no_competitor_signal", "Record a competitor signal (Node 08) before a live community fetch")
    topic = body.get("topic")
    subreddit = body.get("subreddit")
    if not topic:
        raise ApiError(400, "validation_error", "topic is required")
    if not subreddit:
        raise ApiError(400, "validation_error", "subreddit is required")
    target = meta["target"]
    geography = body.get("geography") or target["geography"]
    registry = node09_registry(run_id)
    try:
        record = registry.register_from_live_source(
            signal_id=body.get("signal_id") or f"cm_live_{uuid.uuid4().hex[:8]}",
            target_id=target["target_id"], topic=topic, subreddit=subreddit, geography=geography,
        )
    except live_fetch.LiveFetchError as exc:
        raise _map_live_fetch_error(exc) from exc
    except node09.NoLiveResultsError as exc:
        raise ApiError(404, "no_live_results", str(exc)) from exc
    except node09.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("community_signals", [])
    if not any(s["signal_id"] == record_dict["signal_id"] for s in meta["community_signals"]):
        meta["community_signals"].append(record_dict)
    append_lineage(meta, phase=2, node="node_09", action="register_community_signal_live", summary=f"Live-fetched community signal {record_dict['signal_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def _default_trend_window() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    fmt = lambda dt: dt.isoformat(timespec="milliseconds")  # noqa: E731
    return {
        "baseline_start": fmt(now - timedelta(days=14)),
        "baseline_end": fmt(now - timedelta(days=7)),
        "current_start": fmt(now - timedelta(days=7)),
        "current_end": fmt(now),
    }


def handle_node10_live(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("community_signals"):
        raise ApiError(409, "no_community_signal", "Record a community signal (Node 09) before a live trend aggregation")
    topic = body.get("topic")
    if not topic:
        raise ApiError(400, "validation_error", "topic is required")
    target = meta["target"]
    geography = body.get("geography") or target["geography"]
    window = body.get("window") or _default_trend_window()
    registry = node10_registry(run_id)
    try:
        record = registry.register_from_live_aggregation(
            trend_id=body.get("trend_id") or f"trend_live_{uuid.uuid4().hex[:8]}",
            target_id=target["target_id"], topic=topic, geography=geography, window=window,
            metric_name=body.get("metric_name", "combined_demand_signal_count"),
        )
    except node10.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("trends", [])
    if not any(t["trend_id"] == record_dict["trend_id"] for t in meta["trends"]):
        meta["trends"].append(record_dict)
    append_lineage(meta, phase=2, node="node_10", action="register_trend_live", summary=f"Live-aggregated trend {record_dict['trend_id']}")
    save_run_meta(run_id, meta)
    return record_dict


DEMAND_SCAN_SOURCES = {"search", "questions", "social_video", "competitors", "communities", "trend"}
DEMAND_SCAN_STATUSES = {"running", "collected", "failed", "unavailable", "blocked", "not_run"}


def handle_demand_scan_status(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Persist operator-visible scan outcomes, including failures that node handlers cannot store."""
    source = str(body.get("source") or "").strip()
    status = str(body.get("status") or "").strip()
    if source not in DEMAND_SCAN_SOURCES:
        raise ApiError(400, "validation_error", f"source must be one of {sorted(DEMAND_SCAN_SOURCES)}")
    if status not in DEMAND_SCAN_STATUSES:
        raise ApiError(400, "validation_error", f"status must be one of {sorted(DEMAND_SCAN_STATUSES)}")
    meta = load_run_meta(run_id)
    scan = meta.setdefault("demand_scan", {"sources": {}})
    scan.setdefault("sources", {})[source] = {
        "status": status,
        "message": str(body.get("message") or "").strip()[:1000],
        "updated_at": now_iso(),
    }
    scan["updated_at"] = now_iso()
    if body.get("attempt_id"):
        scan["attempt_id"] = str(body["attempt_id"])[:100]
    save_run_meta(run_id, meta)
    return scan


def handle_node11_classify(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    payload = dict(body)
    if "target_id" not in payload or not payload.get("target_id"):
        if not meta.get("target"):
            raise ApiError(409, "no_target", "Register a Node 01 target, or supply target_id, before classifying a signal")
        payload["target_id"] = meta["target"]["target_id"]
    try:
        result = node11.classify_demand_signal(payload)
    except node11.ContractViolationError as exc:
        raise ApiError(400, "contract_violation", str(exc)) from exc
    except node11.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    record = result.to_dict()
    meta.setdefault("classifications", []).append(record)
    append_lineage(
        meta, phase=3, node="node_11", action="classify_signal",
        summary=f"Classified {record['signal_id']} as {record['primary_intent']}",
    )
    save_run_meta(run_id, meta)
    return record


def _pipeline_from_classification(classification: dict[str, Any]) -> dict[str, Any]:
    """Runs the real Node 12->13->14 chain from a classification, using each module's own
    deterministic default weights/candidates. Deterministic: the same classification always
    yields the same opportunity_id/path_id/selection_id and content, so this is safe to
    recompute on demand rather than persist as separate run state."""
    opportunity = node12.score_demand_opportunity(classification)
    path = node13.discover_demand_path(opportunity)
    selection = node14.select_channel_placements(path)
    return {
        "classification": classification,
        "opportunity": opportunity.to_dict(),
        "path": path.to_dict(),
        "selection": selection.to_dict(),
    }


def node15_registry(run_id: str) -> node15.CampaignClusterRegistry:
    return node15.CampaignClusterRegistry(run_dir(run_id) / "node_15_clusters.json")


def node16_store(run_id: str) -> node16.CanonicalKnowledgeStore:
    return node16.CanonicalKnowledgeStore(run_dir(run_id) / "node_16_facts.json", target_registry=node01_registry(run_id))


def node18_registry(run_id: str) -> node18.VideoAssetRegistry:
    return node18.VideoAssetRegistry(run_dir(run_id) / "node_18_videos.json")


def node18b_registry(run_id: str) -> node18b.AlternateAssetRegistry:
    return node18b.AlternateAssetRegistry(run_dir(run_id) / "node_18_alternate_assets.json")


def handle_node15_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    classifications = meta.get("classifications") or []
    if not classifications:
        raise ApiError(409, "no_classifications", "Classify at least one signal (Node 11) before generating a campaign cluster")
    # Reclassification is append-only for auditability. Node 15 must consume the latest decision
    # for each signal, not treat prior decisions for that same signal as duplicate members.
    latest_by_signal: dict[str, dict[str, Any]] = {}
    for classification in classifications:
        latest_by_signal[str(classification.get("signal_id", ""))] = classification
    members = [_pipeline_from_classification(c) for c in latest_by_signal.values()]
    registry = node15_registry(run_id)
    try:
        clusters = registry.generate_and_register(members, campaign_context=body.get("campaign_context"))
    except node15.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node15.LineageError as exc:
        raise ApiError(409, "lineage_error", str(exc)) from exc
    except node15.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    cluster_dicts = [c.to_dict() for c in clusters]
    meta.setdefault("clusters", [])
    existing_ids = {c["cluster_id"] for c in meta["clusters"]}
    for cluster_dict in cluster_dicts:
        if cluster_dict["cluster_id"] not in existing_ids:
            meta["clusters"].append(cluster_dict)
    append_lineage(
        meta, phase=3, node="node_15", action="generate_clusters",
        summary=f"Generated {len(cluster_dicts)} campaign cluster(s) from {len(members)} classified signal(s)",
    )
    save_run_meta(run_id, meta)
    return {"clusters": cluster_dicts}


def handle_node15_live_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("target"):
        raise ApiError(409, "no_target", "Register a Node 01 target before live-generating clusters")
    registry = node15_registry(run_id)
    signal_registry = node05_registry(run_id)
    try:
        clusters = registry.generate_and_register_from_live_signals(
            meta["target"]["target_id"], signal_registry, campaign_context=body.get("campaign_context"),
        )
    except node15.LineageError as exc:
        raise ApiError(409, "lineage_error", str(exc)) from exc
    except node15.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node15.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    cluster_dicts = [c.to_dict() for c in clusters]
    meta.setdefault("clusters", [])
    existing_ids = {c["cluster_id"] for c in meta["clusters"]}
    for cluster_dict in cluster_dicts:
        if cluster_dict["cluster_id"] not in existing_ids:
            meta["clusters"].append(cluster_dict)
    append_lineage(
        meta, phase=3, node="node_15", action="generate_clusters_live",
        summary=f"Live-generated {len(cluster_dicts)} campaign cluster(s) from real Node 05 signals",
    )
    save_run_meta(run_id, meta)
    return {"clusters": cluster_dicts}


def handle_node16_fact(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    if not meta.get("target"):
        raise ApiError(409, "no_target", "Register a Node 01 target before recording a canonical fact")
    body = dict(body)
    body.setdefault("target_id", meta["target"]["target_id"])
    store = node16_store(run_id)
    try:
        record = store.register_fact(**body)
    except node16.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node16.LineageError as exc:
        raise ApiError(409, "lineage_error", str(exc)) from exc
    except node16.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("facts", [])
    if not any(f["fact_id"] == record_dict["fact_id"] for f in meta["facts"]):
        meta["facts"].append(record_dict)
    append_lineage(meta, phase=4, node="node_16", action="register_fact", summary=f"Registered fact {record_dict['fact_id']}")
    save_run_meta(run_id, meta)
    return record_dict


def handle_node18_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    cluster_id = body.get("cluster_id")
    fact_ids = body.get("fact_ids") or []
    if not cluster_id:
        raise ApiError(400, "validation_error", "cluster_id is required")
    if not fact_ids:
        raise ApiError(400, "validation_error", "fact_ids is required and must be a non-empty list")

    cluster = next((c for c in meta.get("clusters", []) if c["cluster_id"] == cluster_id), None)
    if cluster is None:
        raise ApiError(404, "cluster_not_found", f"cluster_id {cluster_id!r} not found in this run")

    facts_by_id = {f["fact_id"]: f for f in meta.get("facts", [])}
    missing = [fid for fid in fact_ids if fid not in facts_by_id]
    if missing:
        raise ApiError(404, "fact_not_found", f"fact_id(s) not found in this run: {missing}")
    selected_facts = [facts_by_id[fid] for fid in fact_ids]

    member = cluster["members"][0]
    classification = next((c for c in meta.get("classifications", []) if c["signal_id"] == member["signal_id"]), None)
    if classification is None:
        raise ApiError(409, "missing_classification", "The classification underlying this cluster's member is missing")
    pipeline = _pipeline_from_classification(classification)
    selection = pipeline["selection"]

    try:
        asset = node17.generate_asset_payload(selection, facts=selected_facts, intent_input=classification)
    except node17.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node17.LineageError as exc:
        raise ApiError(409, "lineage_error", str(exc)) from exc

    registry = node18_registry(run_id)
    try:
        record = registry.generate_and_register(
            classification=classification, selection=selection, facts=selected_facts, asset=asset, cluster=cluster,
            service_scope=body.get("service_scope"),
        )
    except node18.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node18.LineageError as exc:
        raise ApiError(409, "lineage_error", str(exc)) from exc
    except node18.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc

    record_dict = record.to_dict()
    asset_dict = asset.to_dict()
    meta.setdefault("assets", [])
    if not any(a["asset_id"] == asset_dict["asset_id"] for a in meta["assets"]):
        meta["assets"].append(asset_dict)
    meta.setdefault("video_assets", [])
    if not any(v["video_asset_id"] == record_dict["video_asset_id"] for v in meta["video_assets"]):
        meta["video_assets"].append(record_dict)
    append_lineage(
        meta, phase=4, node="node_18", action="generate_video_asset",
        summary=f"Generated video asset {record_dict['video_asset_id']}",
    )
    save_run_meta(run_id, meta)
    return record_dict


def handle_node18_generate_by_format(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Format-aware sibling of handle_node18_generate: builds the exact same real Node 17
    AssetPayload, then dispatches on its OWN real recommended_format (computed by Node 14, not
    guessed here) -- the three non-video formats plus community-post go to node18b's
    AlternateAssetRegistry; anything else (including a genuinely video-shaped format, should Node
    14 ever add one) falls back to the existing video registry, unchanged. Closes the real gap
    found 2026-08-18: handle_node18_generate always forced a video regardless of what Node 14
    actually recommended."""
    meta = load_run_meta(run_id)
    cluster_id = body.get("cluster_id")
    fact_ids = body.get("fact_ids") or []
    if not cluster_id:
        raise ApiError(400, "validation_error", "cluster_id is required")
    if not fact_ids:
        raise ApiError(400, "validation_error", "fact_ids is required and must be a non-empty list")

    cluster = next((c for c in meta.get("clusters", []) if c["cluster_id"] == cluster_id), None)
    if cluster is None:
        raise ApiError(404, "cluster_not_found", f"cluster_id {cluster_id!r} not found in this run")

    facts_by_id = {f["fact_id"]: f for f in meta.get("facts", [])}
    missing = [fid for fid in fact_ids if fid not in facts_by_id]
    if missing:
        raise ApiError(404, "fact_not_found", f"fact_id(s) not found in this run: {missing}")
    selected_facts = [facts_by_id[fid] for fid in fact_ids]

    member = cluster["members"][0]
    classification = next((c for c in meta.get("classifications", []) if c["signal_id"] == member["signal_id"]), None)
    if classification is None:
        raise ApiError(409, "missing_classification", "The classification underlying this cluster's member is missing")
    pipeline = _pipeline_from_classification(classification)
    selection = pipeline["selection"]

    try:
        asset = node17.generate_asset_payload(selection, facts=selected_facts, intent_input=classification)
    except node17.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node17.LineageError as exc:
        raise ApiError(409, "lineage_error", str(exc)) from exc

    asset_dict = asset.to_dict()
    meta.setdefault("assets", [])
    if not any(a["asset_id"] == asset_dict["asset_id"] for a in meta["assets"]):
        meta["assets"].append(asset_dict)

    asset_format = asset_dict["metadata"]["format"]
    if asset_format in node18b.ALLOWED_FORMATS:
        registry_b = node18b_registry(run_id)
        try:
            record = registry_b.generate_and_register(asset=asset, cluster=cluster)
        except node18b.ValidationError as exc:
            raise ApiError(400, "validation_error", str(exc)) from exc
        except node18b.LineageError as exc:
            raise ApiError(409, "lineage_error", str(exc)) from exc
        except node18b.ConflictError as exc:
            raise ApiError(409, "conflict", str(exc)) from exc
        record_dict = record.to_dict()
        meta.setdefault("alternate_assets", [])
        if not any(a["alternate_asset_id"] == record_dict["alternate_asset_id"] for a in meta["alternate_assets"]):
            meta["alternate_assets"].append(record_dict)
        append_lineage(
            meta, phase=4, node="node_18b", action="generate_alternate_asset",
            summary=f"Generated {asset_format} asset {record_dict['alternate_asset_id']}"
                    + (" (requires human review)" if record.requires_human_review else ""),
        )
        save_run_meta(run_id, meta)
        return record_dict

    registry = node18_registry(run_id)
    try:
        record = registry.generate_and_register(
            classification=classification, selection=selection, facts=selected_facts, asset=asset, cluster=cluster,
            service_scope=body.get("service_scope"),
        )
    except node18.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node18.LineageError as exc:
        raise ApiError(409, "lineage_error", str(exc)) from exc
    except node18.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("video_assets", [])
    if not any(v["video_asset_id"] == record_dict["video_asset_id"] for v in meta["video_assets"]):
        meta["video_assets"].append(record_dict)
    append_lineage(
        meta, phase=4, node="node_18", action="generate_video_asset",
        summary=f"Generated video asset {record_dict['video_asset_id']}",
    )
    save_run_meta(run_id, meta)
    return record_dict


def _derive_product_category(service: str) -> str:
    # "boiler_repair" / "boiler_service" -> "boiler". Matches the user's own tag shorthand
    # ("boiler_{all_service}_{London}") rather than inventing a separate taxonomy.
    return service.split("_", 1)[0] if service else ""


def _default_applicability(target: dict[str, Any]) -> dict[str, Any]:
    # Narrowest possible scope: this exact service, this exact locality. Callers that want a
    # video to be reusable across services/localities must say so explicitly -- an untagged
    # render is never assumed reusable, to avoid a video honestly made for one place/service
    # silently being reused somewhere it doesn't apply.
    service = target.get("service", "")
    locality = target.get("geography", {}).get("locality", "")
    return {
        "product_category": _derive_product_category(service),
        "service_scope": [service] if service else [],
        "locality_scope": [locality] if locality else [],
    }


def _applicability_covers(applicability: dict[str, Any], product_category: str, service: str, locality: str) -> bool:
    if applicability.get("product_category") != product_category:
        return False
    service_scope = applicability.get("service_scope")
    if service_scope != "all" and service not in (service_scope or []):
        return False
    locality_scope = applicability.get("locality_scope")
    if locality_scope != "all" and locality not in (locality_scope or []):
        return False
    return True


def _find_reusable_video_publication(product_category: str, service: str, locality: str, exclude_run_id: str) -> dict[str, Any] | None:
    """Scans every run's real video_publications for one whose applicability tag already covers
    this (product_category, service, locality) -- reuse saves a real render + real upload cost.
    Only ever matches an explicitly-tagged applicability (see _default_applicability); an
    untagged/legacy publication is never treated as reusable."""
    for meta in list_runs():
        if meta.get("run_id") == exclude_run_id:
            continue
        for pub in meta.get("video_publications", []):
            applicability = pub.get("applicability")
            if not applicability:
                continue
            if _applicability_covers(applicability, product_category, service, locality):
                return pub
    return None


def handle_node18_trigger_render_and_publish(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Triggers the REAL EP048 render + REAL YouTube upload for a video asset already produced
    by Node 18 (handle_node18_generate / _by_format / _live_generate / _replicate_winner). This
    is a genuine external action (network calls, a real public-platform upload) -- per direct
    user instruction (2026-08-20): "the ep048 process goes off and generates the video and
    uploads to necessary platforms.... the node 18 then confirms when the video is uploaded and
    then proceeds to next node." Requires an explicit confirm_publish=true in the request body on
    every call; this handler does not infer or remember prior consent.

    Cost control (2026-08-20, direct user instruction): "due to cost we do not want to generate
    separate boiler_service_catford video to boiler_service_lewisham... a video is created it can
    be marked as applies boiler_{all service}_{all London} / boiler_{some service}_{south
    London}". Before spending on a real render, checks every other run for an already-published
    real video whose `applicability` tag (product_category/service_scope/locality_scope, caller-
    supplied or defaulted to this exact service+locality) already covers this campaign. If found,
    reuses that video_id/watch_url -- no render, no upload, no external action, no cost. The
    reused publication is stamped reused=True and reused_from so this is never silently hidden.
    """
    meta = load_run_meta(run_id)
    video_asset_id = body.get("video_asset_id")
    if not video_asset_id:
        raise ApiError(400, "validation_error", "video_asset_id is required")
    if body.get("confirm_publish") is not True:
        raise ApiError(400, "confirmation_required", "confirm_publish must be true -- this triggers a real render and a real YouTube upload")

    video_record = next((v for v in meta.get("video_assets", []) if v["video_asset_id"] == video_asset_id), None)
    if video_record is None:
        raise ApiError(404, "video_asset_not_found", f"video_asset_id {video_asset_id!r} not found in this run")

    already = next((p for p in meta.get("video_publications", []) if p["video_asset_id"] == video_asset_id), None)
    if already is not None:
        raise ApiError(409, "already_published", f"video_asset_id {video_asset_id!r} already has a real publication record: {already.get('video_id')}")

    target = meta.get("target", {})
    applicability = body.get("applicability") or _default_applicability(target)
    service = target.get("service", "")
    locality = target.get("geography", {}).get("locality", "")
    product_category = applicability.get("product_category") or _derive_product_category(service)

    reusable = _find_reusable_video_publication(product_category, service, locality, exclude_run_id=run_id)
    if reusable is not None:
        result_dict = {
            "video_asset_id": video_asset_id,
            "run_id": run_id,
            "script_path": None,
            "render_output_path": None,
            "rendered_at": reusable.get("rendered_at"),
            "render_stdout_tail": "",
            "video_id": reusable["video_id"],
            "watch_url": reusable["watch_url"],
            "privacy_status": reusable.get("privacy_status", "unlisted"),
            "uploaded_at": reusable.get("uploaded_at"),
            "upload_stdout_tail": "",
            "external_action": False,
            "applicability": applicability,
            "reused": True,
            "reused_from": {"run_id": reusable["run_id"], "video_asset_id": reusable["video_asset_id"]},
        }
        meta.setdefault("video_publications", [])
        meta["video_publications"].append(result_dict)
        append_lineage(
            meta, phase=4, node="node_18", action="reuse_video_publication",
            summary=f"Reused existing video {reusable['video_id']} from run {reusable['run_id']} "
                    f"(applicability covers {product_category}/{service}/{locality}) -- no new render or upload",
        )
        save_run_meta(run_id, meta)
        return result_dict

    asset = next((a for a in meta.get("assets", []) if a["asset_id"] == video_record["asset_id"]), None)
    asset_title = asset["title"] if asset else video_record.get("caption", "Automated Upload")

    work_dir = run_dir(run_id) / "node18_render"
    try:
        result = node18_publish.trigger_render_and_publish(
            run_id=run_id, video_record=video_record, asset_title=asset_title, work_dir=work_dir,
        )
    except node18_publish.RenderFailedError as exc:
        raise ApiError(502, "render_failed", str(exc)) from exc
    except node18_publish.UploadFailedError as exc:
        raise ApiError(502, "upload_failed", str(exc)) from exc
    except node18_publish.Ep048TriggerError as exc:
        raise ApiError(500, "ep048_trigger_error", str(exc)) from exc

    result_dict = result.to_dict()
    result_dict["applicability"] = applicability
    result_dict["reused"] = False
    result_dict["reused_from"] = None
    meta.setdefault("video_publications", [])
    meta["video_publications"].append(result_dict)
    append_lineage(
        meta, phase=4, node="node_18", action="render_and_publish_video_asset",
        summary=f"Rendered and uploaded video asset {video_asset_id} -- video_id={result.video_id} ({result.watch_url})",
    )
    save_run_meta(run_id, meta)
    return result_dict


def handle_node18_live_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    cluster_id = body.get("cluster_id")
    signal_id = body.get("signal_id")
    if not cluster_id:
        raise ApiError(400, "validation_error", "cluster_id is required")
    if not signal_id:
        raise ApiError(400, "validation_error", "signal_id is required")
    if not meta.get("target"):
        raise ApiError(409, "no_target", "Register a Node 01 target before live-generating a video asset")
    target_id = meta["target"]["target_id"]
    registry = node18_registry(run_id)
    signal_registry = node05_registry(run_id)
    cluster_registry = node15_registry(run_id)
    knowledge_store = node16_store(run_id)
    try:
        record = registry.generate_and_register_from_live_chain(
            cluster_id=cluster_id, target_id=target_id, signal_id=signal_id,
            demand_signal_registry=signal_registry, cluster_registry=cluster_registry, knowledge_store=knowledge_store,
        )
    except node18.LineageError as exc:
        raise ApiError(409, "lineage_error", str(exc)) from exc
    except node18.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    except node18.ConflictError as exc:
        raise ApiError(409, "conflict", str(exc)) from exc
    record_dict = record.to_dict()
    meta.setdefault("video_assets", [])
    if not any(v["video_asset_id"] == record_dict["video_asset_id"] for v in meta["video_assets"]):
        meta["video_assets"].append(record_dict)
    append_lineage(
        meta, phase=4, node="node_18", action="generate_video_asset_live",
        summary=f"Live-generated video asset {record_dict['video_asset_id']}",
    )
    save_run_meta(run_id, meta)
    return record_dict


def handle_node18_replicate_winner(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Closes the amplification loop: reruns the real Node11->17 chain against the SAME winning
    cluster/target/signal, varying only template_version per format, so a proven campaign can be
    replicated into several new real, distinct video assets fast -- "minor changes to the initial
    dataset and resubmitting" rather than one-at-a-time manual generation. Never touches geography:
    geographic_expansion would require real demand data for a new market that does not exist yet,
    so only format_diversification variants (same real facts/signal, different template) are minted.
    """
    meta = load_run_meta(run_id)
    winners = meta.get("winners") or []
    if not winners:
        raise ApiError(409, "no_winner", "Run Node 34 (winner detection) before replicating a winning campaign")
    winner = next((w for w in winners if w.get("is_winner")), None)
    if winner is None:
        raise ApiError(409, "no_winner", "No winner has been detected yet (is_winner is False for all evaluations)")

    clusters = meta.get("clusters") or []
    if not clusters:
        raise ApiError(409, "no_cluster", "This run has no Node 15 cluster to replicate from")
    cluster = clusters[-1]
    cluster_id = cluster["cluster_id"]
    signal_id = cluster["members"][0]["signal_id"]
    if not meta.get("target"):
        raise ApiError(409, "no_target", "Register a Node 01 target before replicating a video asset")
    target_id = meta["target"]["target_id"]

    amplifications = meta.get("amplifications") or []
    formats: list[str] = []
    for amp in reversed(amplifications):
        variant = next((v for v in amp.get("expansion_variants", []) if v.get("dimension") == "format_diversification"), None)
        if variant and variant.get("formats"):
            formats = variant["formats"]
            break
    if not formats:
        formats = ["short_video", "faq_schema", "local_directory_push"]

    registry = node18_registry(run_id)
    signal_registry = node05_registry(run_id)
    cluster_registry = node15_registry(run_id)
    knowledge_store = node16_store(run_id)
    meta.setdefault("video_assets", [])

    created: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    for fmt in formats:
        try:
            record = registry.generate_and_register_from_live_chain(
                cluster_id=cluster_id, target_id=target_id, signal_id=signal_id,
                demand_signal_registry=signal_registry, cluster_registry=cluster_registry, knowledge_store=knowledge_store,
                template_version=f"replicate_{fmt}_v1",
            )
        except (node18.LineageError, node18.ValidationError, node18.ConflictError) as exc:
            failed.append({"format": fmt, "error": str(exc)})
            continue
        record_dict = record.to_dict()
        if not any(v["video_asset_id"] == record_dict["video_asset_id"] for v in meta["video_assets"]):
            meta["video_assets"].append(record_dict)
        created.append(record_dict)

    append_lineage(
        meta, phase=7, node="node_18", action="replicate_winning_campaign",
        summary=f"Replicated {len(created)} variant(s) of winning channel {winner.get('channel')} "
                f"({', '.join(formats)}); {len(failed)} failed",
    )
    save_run_meta(run_id, meta)
    return {"winner_channel": winner.get("channel"), "created": created, "failed": failed}


# --- Phase 5 (Nodes 19 quality gate / 20-27 distribution, minus MVP-deferred 22-25) ----------
# Nodes 20/21/26/27 each consume the FULL structured output of the node before them (a schema
# object, not a hand-typeable business fact) -- so every handler here looks its inputs up from
# this run's own state (by ID selected in the console) rather than accepting raw JSON from the
# operator, exactly like Node 18 already does for cluster_id/fact_ids. Node 19 itself needs a
# real Node 17 AssetPayload, which handle_node18_generate already produces and stores in
# meta["assets"] -- so Node 19 selects an existing asset_id from that same list, no new upstream
# step required. Nodes 22-25 remain intentionally unwired: PHASES marks them mvp_deferred_nodes,
# a real project decision already encoded before this task, not an oversight to fix here.

def handle_node19_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    asset_id = body.get("asset_id")
    if not asset_id:
        raise ApiError(400, "validation_error", "asset_id is required")
    asset = next((a for a in meta.get("assets", []) if a["asset_id"] == asset_id), None)
    if asset is None:
        raise ApiError(404, "asset_not_found", f"asset_id {asset_id!r} not found in this run")

    knowledge_store = node16_store(run_id)
    try:
        check, package = node19.evaluate_asset_compliance(asset, knowledge_store=knowledge_store)
    except node19.ValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    check_dict = check.to_dict()
    meta.setdefault("compliance_checks", [])
    if not any(c["check_id"] == check_dict["check_id"] for c in meta["compliance_checks"]):
        meta["compliance_checks"].append(check_dict)

    if package is None:
        append_lineage(
            meta, phase=4, node="node_19", action="evaluate_asset_compliance",
            summary=f"Asset {asset_id} REJECTED at compliance review: {'; '.join(check.reasons)}",
        )
        save_run_meta(run_id, meta)
        raise ApiError(422, "compliance_rejected", "; ".join(check.reasons) or "Asset failed compliance review")

    package_dict = package.to_dict()
    meta.setdefault("approved_packages", [])
    if not any(p["asset_id"] == package_dict["asset_id"] for p in meta["approved_packages"]):
        meta["approved_packages"].append(package_dict)
    append_lineage(
        meta, phase=4, node="node_19", action="evaluate_asset_compliance",
        summary=f"Asset {asset_id} approved at compliance review ({check_dict['check_id']})",
    )
    save_run_meta(run_id, meta)
    return {"compliance_check": check_dict, "approved_package": package_dict}


def handle_node20_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    asset_id = body.get("asset_id")
    if not asset_id:
        raise ApiError(400, "validation_error", "asset_id is required")
    package = next((p for p in meta.get("approved_packages", []) if p["asset_id"] == asset_id), None)
    if package is None:
        raise ApiError(404, "approved_package_not_found", f"No Node 19 approved package for asset_id {asset_id!r} in this run")

    try:
        plan = node20.build_mock_publication_plan(package)
    except node20.PublicationPlanValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("publication_plans", [])
    if not any(p["publication_plan_id"] == plan["publication_plan_id"] for p in meta["publication_plans"]):
        meta["publication_plans"].append(plan)
    append_lineage(
        meta, phase=5, node="node_20", action="build_publication_plan",
        summary=f"Built publication plan {plan['publication_plan_id']} for asset {asset_id}",
    )
    save_run_meta(run_id, meta)
    return plan


def handle_node21_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    plan_id = body.get("publication_plan_id")
    if not plan_id:
        raise ApiError(400, "validation_error", "publication_plan_id is required")
    plan = next((p for p in meta.get("publication_plans", []) if p["publication_plan_id"] == plan_id), None)
    if plan is None:
        raise ApiError(404, "publication_plan_not_found", f"publication_plan_id {plan_id!r} not found in this run")
    package = next((p for p in meta.get("approved_packages", []) if p["asset_id"] == plan["asset_id"]), None)
    if package is None:
        raise ApiError(404, "approved_package_not_found", f"No Node 19 approved package for asset_id {plan['asset_id']!r}")

    try:
        search_package = node21.build_search_distribution_package(plan, package)
    except node21.SearchDistributionValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    search_distribution_id = search_package["manifest"]["search_distribution_id"]
    meta.setdefault("search_packages", [])
    if not any(s["manifest"]["search_distribution_id"] == search_distribution_id for s in meta["search_packages"]):
        meta["search_packages"].append(search_package)
    append_lineage(
        meta, phase=5, node="node_21", action="build_search_distribution_package",
        summary=f"Built search distribution package {search_distribution_id} for plan {plan_id}",
    )
    save_run_meta(run_id, meta)
    return search_package


def handle_node26_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    search_distribution_id = body.get("search_distribution_id")
    if not search_distribution_id:
        raise ApiError(400, "validation_error", "search_distribution_id is required")
    search_package = next(
        (s for s in meta.get("search_packages", []) if s["manifest"]["search_distribution_id"] == search_distribution_id), None
    )
    if search_package is None:
        raise ApiError(404, "search_package_not_found", f"search_distribution_id {search_distribution_id!r} not found in this run")
    plan = next((p for p in meta.get("publication_plans", []) if p["publication_plan_id"] == search_package["manifest"]["publication_plan_id"]), None)
    package = next((p for p in meta.get("approved_packages", []) if p["asset_id"] == search_package["manifest"]["asset_id"]), None)
    if plan is None or package is None:
        raise ApiError(409, "lineage_error", "The publication plan or approved package behind this search package is missing from run state")

    # Only Nodes 22-25 (deferred) plus the topic/intent/geography/service judgment fields are
    # operator-editable -- asset_id/target_id/opportunity_id/channel are taken verbatim from the
    # selected plan so the lineage checks Node 26 enforces can never be broken by a mistyped ID.
    # topic/geography/service default from THIS run's own real target and demand signal, not a
    # hardcoded example: they previously always defaulted to "blackheath"/"boiler_repair"/"safe
    # boiler pressure guide" regardless of the actual campaign, and node26._matching_rule required
    # an exact match against those same literals, so any other real campaign reaching this endpoint
    # without an operator manually overriding all three would either receive wrong-town routing
    # metadata or be rejected outright with "no approved routing rule matches".
    target = meta.get("target") or {}
    latest_signal = (meta.get("demand_signals") or [{}])[-1]
    routing_context = {
        "topic": body.get("topic") or latest_signal.get("topic") or "general_inquiry",
        "intent": body.get("intent", "diagnostic_quote"),
        "geography": body.get("geography") or target.get("geography", {}).get("locality") or "unspecified",
        "service": body.get("service") or target.get("service") or "unspecified",
        "channel": plan["channel"],
        "asset_id": plan["asset_id"],
        "target_id": plan["target_id"],
        "opportunity_id": plan["opportunity_id"],
        "external_action": False,
    }
    try:
        route = node26.build_route_recommendation(plan, package, search_package, routing_context)
    except node26.DestinationRoutingValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("routes", [])
    if not any(r["route_id"] == route["route_id"] for r in meta["routes"]):
        meta["routes"].append(route)
    append_lineage(
        meta, phase=5, node="node_26", action="build_route_recommendation",
        summary=f"Built route recommendation {route['route_id']} for search package {search_distribution_id}",
    )
    save_run_meta(run_id, meta)
    return route


def handle_node27_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    route_id = body.get("route_id")
    if not route_id:
        raise ApiError(400, "validation_error", "route_id is required")
    route = next((r for r in meta.get("routes", []) if r["route_id"] == route_id), None)
    if route is None:
        raise ApiError(404, "route_not_found", f"route_id {route_id!r} not found in this run")
    session_id = body.get("session_id")
    if not session_id:
        raise ApiError(400, "validation_error", "session_id is required")
    if body.get("consent_granted") is not True:
        raise ApiError(400, "validation_error", "consent_granted must be explicitly true -- this simulates a real consumer's consent checkbox")

    intake = {
        "session_id": session_id,
        "source": route["routing_context"]["channel"],
        "consent": {
            "granted": True,
            "timestamp": now_iso().replace("+00:00", "Z").split(".")[0] + "Z",
            "version": body.get("consent_version", "v1"),
            "basis": body.get("consent_basis", "explicit_opt_in"),
        },
    }
    try:
        lead = node27.build_structured_lead_record(route, intake)
    except node27.LeadCaptureValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("leads", [])
    if not any(l["lead_id"] == lead["lead_id"] for l in meta["leads"]):
        meta["leads"].append(lead)
    append_lineage(
        meta, phase=5, node="node_27", action="build_structured_lead_record",
        summary=f"Captured structured lead {lead['lead_id']} from route {route_id}",
    )
    save_run_meta(run_id, meta)
    return lead


# --- Public consumer intake (real form, real backend) --------------------------
# Closes the "no real consumer can reach this" gap: a real browser submitting this real form
# produces a real Node 26->27 call, not a console-driven fixture. Node 27's own contract is
# deliberately PII-free (_ALLOWED = {session_id, source, consent}) -- raw name/email/phone and
# the job-request content (trade/location/budget/details) are real business data EP050's pipeline
# was never designed to hold, so they're persisted separately, next to but never merged into the
# PII-free lead record Node 27 produces.

def public_pii_path(run_id: str) -> Path:
    return run_dir(run_id) / "public_intake_pii.json"


def render_intake_form(run_id: str, meta: dict[str, Any]) -> str:
    target = meta.get("target") or {}
    service = target.get("service", "the service")
    locality = (target.get("geography") or {}).get("locality", "")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Get matched with a local {service.replace('_', ' ')} pro</title>
<style>
body{{margin:0;background:#f7faf7;color:#14201a;font:16px/1.5 system-ui,sans-serif}}
main{{max-width:520px;margin:40px auto;padding:0 20px}}
h1{{font:700 26px Georgia,serif;margin:0 0 6px}}
p.sub{{color:#64716a;margin:0 0 24px}}
label{{display:block;font-weight:600;font-size:13px;margin:16px 0 6px}}
input,textarea{{width:100%;padding:10px 12px;border:1px solid #d7e2da;border-radius:8px;font:inherit;box-sizing:border-box}}
textarea{{min-height:70px;resize:vertical}}
.consent{{display:flex;gap:8px;align-items:flex-start;margin-top:18px;font-size:13px;color:#45554b}}
button{{margin-top:20px;min-height:46px;width:100%;background:#0fa15f;color:#05130c;border:0;border-radius:8px;font:700 16px inherit;cursor:pointer}}
#result{{margin-top:16px;padding:14px;border-radius:8px;display:none;font-size:14px}}
#result.ok{{display:block;background:#dff5e8;border-left:3px solid #087443}}
#result.err{{display:block;background:#ffebe8;border-left:3px solid #b3261e}}
</style></head><body><main>
<h1>Get matched with a local {service.replace('_', ' ')} pro</h1>
<p class="sub">{locality and f"Serving {locality} and the surrounding area." or ""}</p>
<form id="intake-form">
<label>Job details</label>
<textarea id="details" placeholder="What do you need done?" required></textarea>
<label>Full name</label>
<input id="name" required>
<label>Email address</label>
<input id="email" type="email" required>
<label>Phone (optional)</label>
<input id="phone">
<div class="consent">
<input id="consent" type="checkbox" required style="width:auto;margin-top:2px">
<label style="display:inline;font-weight:400;margin:0" for="consent">I consent to being contacted about this request and to my details being used to find a matching local business.</label>
</div>
<button type="submit">Request a quote</button>
</form>
<div id="result"></div>
<script>
document.getElementById('intake-form').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const result = document.getElementById('result');
  result.className = ''; result.style.display = 'none';
  try {{
    const response = await fetch('/api/runs/{run_id}/node27/public_intake', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        details: document.getElementById('details').value,
        consent_granted: document.getElementById('consent').checked,
      }}),
    }});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Submission failed');
    result.className = 'ok';
    result.textContent = 'Thanks -- your request has been received. Reference: ' + data.lead_id;
    result.style.display = 'block';
    e.target.reset();
  }} catch (err) {{
    result.className = 'err';
    result.textContent = err.message;
    result.style.display = 'block';
  }}
}});
</script>
</main></body></html>"""


def handle_node27_public_intake(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    routes = meta.get("routes") or []
    if not routes:
        raise ApiError(409, "no_route", "No Node 26 route exists for this run yet")
    route = routes[-1]

    name = str(body.get("name") or "").strip()
    email = str(body.get("email") or "").strip()
    if not name or not email:
        raise ApiError(400, "validation_error", "name and email are required")
    if body.get("consent_granted") is not True:
        raise ApiError(400, "validation_error", "consent_granted must be true")

    session_id = uuid.uuid4().hex

    # Raw PII + job content: real business data, stored separately, never merged into Node 27's
    # deliberately PII-free record.
    pii_path = public_pii_path(run_id)
    pii_records = json.loads(pii_path.read_text(encoding="utf-8")) if pii_path.exists() else []
    pii_records.append({
        "session_id": session_id,
        "name": name,
        "email": email,
        "phone": str(body.get("phone") or "").strip(),
        "details": str(body.get("details") or "").strip(),
        "submitted_at": now_iso(),
    })
    pii_path.write_text(json.dumps(pii_records, indent=2), encoding="utf-8")

    intake = {
        "session_id": session_id,
        "source": route["routing_context"]["channel"],
        "consent": {
            "granted": True,
            "timestamp": now_iso().replace("+00:00", "Z").split(".")[0] + "Z",
            "version": "v1",
            "basis": "explicit_opt_in",
        },
    }
    try:
        lead = node27.build_structured_lead_record(route, intake)
    except node27.LeadCaptureValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("leads", [])
    if not any(l["lead_id"] == lead["lead_id"] for l in meta["leads"]):
        meta["leads"].append(lead)
    append_lineage(
        meta, phase=5, node="node_27", action="build_structured_lead_record_public",
        summary=f"Real consumer intake captured structured lead {lead['lead_id']}",
    )
    save_run_meta(run_id, meta)
    return lead


# --- Phase 6 (Nodes 28-31, pending acceptance) and Phase 7 (Nodes 32-37, pending acceptance) --
# Real forms exist for all ten, same as Node 27 -- but none are added to any phase's
# console_controls, since none has a formal board ACCEPTED event yet (honoring the
# console_controls<=accepted_nodes invariant already enforced elsewhere in this file).

def handle_node28_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    lead_id = body.get("lead_id")
    if not lead_id:
        raise ApiError(400, "validation_error", "lead_id is required")
    lead = next((l for l in meta.get("leads", []) if l["lead_id"] == lead_id), None)
    if lead is None:
        raise ApiError(404, "lead_not_found", f"lead_id {lead_id!r} not found in this run")

    attribution_model = {"name": "deterministic_last_verified_touch", "version": "1.0.0", "confidence": 0.95}
    try:
        record = node28.build_attribution_record(lead, attribution_model)
    except node28.AttributionValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("attributions", [])
    if not any(a["attribution_id"] == record["attribution_id"] for a in meta["attributions"]):
        meta["attributions"].append(record)
    append_lineage(meta, phase=6, node="node_28", action="build_attribution_record", summary=f"Attributed lead {lead_id} as {record['attribution_id']}")
    save_run_meta(run_id, meta)
    return record


def handle_node29_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    attribution_id = body.get("attribution_id")
    if not attribution_id:
        raise ApiError(400, "validation_error", "attribution_id is required")
    attribution = next((a for a in meta.get("attributions", []) if a["attribution_id"] == attribution_id), None)
    if attribution is None:
        raise ApiError(404, "attribution_not_found", f"attribution_id {attribution_id!r} not found in this run")

    try:
        record = node29.evaluate_lead_qualification(
            attribution,
            service_match=bool(body.get("service_match", True)),
            geo_eligible=bool(body.get("geo_eligible", True)),
            urgency_level=body.get("urgency_level", "high"),
            estimated_value_gbp=float(body.get("estimated_value_gbp", 180.0)),
            duplicate_check_passed=bool(body.get("duplicate_check_passed", True)),
        )
    except node29.LeadQualificationValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    meta.setdefault("qualifications", [])
    if not any(q["qualification_id"] == record["qualification_id"] for q in meta["qualifications"]):
        meta["qualifications"].append(record)
    append_lineage(meta, phase=6, node="node_29", action="evaluate_lead_qualification", summary=f"Qualification {record['qualification_id']}: is_qualified={record['is_qualified']}")
    save_run_meta(run_id, meta)
    return record


def handle_node30_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    qualification_id = body.get("qualification_id")
    if not qualification_id:
        raise ApiError(400, "validation_error", "qualification_id is required")
    qualification = next((q for q in meta.get("qualifications", []) if q["qualification_id"] == qualification_id), None)
    if qualification is None:
        raise ApiError(404, "qualification_not_found", f"qualification_id {qualification_id!r} not found in this run")

    try:
        record = node30.route_qualified_lead(qualification)
    except node30.LeadRoutingValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("routings", [])
    if not any(r["routing_id"] == record["routing_id"] for r in meta["routings"]):
        meta["routings"].append(record)
    append_lineage(meta, phase=6, node="node_30", action="route_qualified_lead", summary=f"Routed lead to {record['allocated_provider']['name']} ({record['routing_id']})")
    save_run_meta(run_id, meta)
    return record


def handle_node31_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    routing_id = body.get("routing_id")
    if not routing_id:
        raise ApiError(400, "validation_error", "routing_id is required")
    routing = next((r for r in meta.get("routings", []) if r["routing_id"] == routing_id), None)
    if routing is None:
        raise ApiError(404, "routing_not_found", f"routing_id {routing_id!r} not found in this run")
    new_status = body.get("new_status")
    if not new_status:
        raise ApiError(400, "validation_error", "new_status is required")

    lifecycles = meta.get("lifecycles", [])
    existing = [l for l in lifecycles if l["routing_id"] == routing_id]
    current = existing[-1] if existing else None
    try:
        record = node31.transition_lead_lifecycle(
            current, routing_record=routing, new_status=new_status,
            outcome_reason=body.get("outcome_reason", "normal_progression"),
            revenue_amount_gbp=body.get("revenue_amount_gbp"),
        )
    except node31.LeadLifecycleValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("lifecycles", [])
    meta["lifecycles"].append(record)
    append_lineage(meta, phase=6, node="node_31", action="transition_lead_lifecycle", summary=f"Lead lifecycle -> {new_status} ({record['lifecycle_entry_id']})")
    save_run_meta(run_id, meta)
    return record


def handle_node32_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    target = meta.get("target")
    if not target:
        raise ApiError(409, "no_target", "Register a Node 01 target before recording performance")
    routes = meta.get("routes") or []
    if not routes:
        raise ApiError(409, "no_route", "Build a Node 26 route before recording performance")
    lineage = routes[-1]["lineage"]

    record = node32.build_performance_record(
        target_id=target["target_id"], opportunity_id=lineage["opportunity_id"],
        channel=routes[-1]["routing_context"]["channel"],
    )
    meta.setdefault("performance_records", [])
    if not any(p["performance_record_id"] == record["performance_record_id"] for p in meta["performance_records"]):
        meta["performance_records"].append(record)
    append_lineage(meta, phase=7, node="node_32", action="build_performance_record", summary=f"Recorded performance {record['performance_record_id']} (ROAS {record['metrics']['return_on_ad_spend']})")
    save_run_meta(run_id, meta)
    return record


def handle_node33_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    lead_id = body.get("lead_id")
    if not lead_id:
        raise ApiError(400, "validation_error", "lead_id is required")
    lead = next((l for l in meta.get("leads", []) if l["lead_id"] == lead_id), None)
    if lead is None:
        raise ApiError(404, "lead_not_found", f"lead_id {lead_id!r} not found in this run")
    target = meta.get("target") or {}

    try:
        record = node33.ingest_outcome_feedback(
            lead_id=lead_id, target_id=target.get("target_id", ""),
            feedback_source=body.get("feedback_source", "technician_app"),
        )
    except node33.OutcomeFeedbackValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("outcome_feedback", [])
    if not any(f["feedback_id"] == record["feedback_id"] for f in meta["outcome_feedback"]):
        meta["outcome_feedback"].append(record)
    append_lineage(meta, phase=7, node="node_33", action="ingest_outcome_feedback", summary=f"Ingested feedback {record['feedback_id']} for lead {lead_id}")
    save_run_meta(run_id, meta)
    return record


def handle_node34_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    performance_record_id = body.get("performance_record_id")
    if not performance_record_id:
        raise ApiError(400, "validation_error", "performance_record_id is required")
    performance = next((p for p in meta.get("performance_records", []) if p["performance_record_id"] == performance_record_id), None)
    if performance is None:
        raise ApiError(404, "performance_not_found", f"performance_record_id {performance_record_id!r} not found in this run")

    try:
        record = node34.detect_winning_strategy(performance)
    except node34.WinnerDetectionValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc
    meta.setdefault("winners", [])
    if not any(w["winner_id"] == record["winner_id"] for w in meta["winners"]):
        meta["winners"].append(record)
    append_lineage(meta, phase=7, node="node_34", action="detect_winning_strategy", summary=f"Winner detection {record['winner_id']}: is_winner={record['is_winner']}")
    save_run_meta(run_id, meta)
    return record


def handle_node35_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    winner_id = body.get("winner_id")
    if not winner_id:
        raise ApiError(400, "validation_error", "winner_id is required")
    winner = next((w for w in meta.get("winners", []) if w["winner_id"] == winner_id), None)
    if winner is None:
        raise ApiError(404, "winner_not_found", f"winner_id {winner_id!r} not found in this run")

    try:
        record = node35.generate_amplification_plan(winner)
    except node35.WinnerAmplificationValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("amplifications", [])
    if not any(a["amplification_id"] == record["amplification_id"] for a in meta["amplifications"]):
        meta["amplifications"].append(record)
    append_lineage(meta, phase=7, node="node_35", action="generate_amplification_plan", summary=f"Amplification plan {record['amplification_id']} generated")
    save_run_meta(run_id, meta)
    return record


def handle_node36_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    amplification_id = body.get("amplification_id")
    if not amplification_id:
        raise ApiError(400, "validation_error", "amplification_id is required")
    amplification = next((a for a in meta.get("amplifications", []) if a["amplification_id"] == amplification_id), None)
    if amplification is None:
        raise ApiError(404, "amplification_not_found", f"amplification_id {amplification_id!r} not found in this run")

    try:
        record = node36.plan_effort_allocation(amplification)
    except node36.EffortAllocationValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("allocations", [])
    if not any(a["allocation_id"] == record["allocation_id"] for a in meta["allocations"]):
        meta["allocations"].append(record)
    append_lineage(meta, phase=7, node="node_36", action="plan_effort_allocation", summary=f"Effort allocation {record['allocation_id']} planned")
    save_run_meta(run_id, meta)
    return record


def handle_node37_generate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    allocation_id = body.get("allocation_id")
    if not allocation_id:
        raise ApiError(400, "validation_error", "allocation_id is required")
    allocation = next((a for a in meta.get("allocations", []) if a["allocation_id"] == allocation_id), None)
    if allocation is None:
        raise ApiError(404, "allocation_not_found", f"allocation_id {allocation_id!r} not found in this run")

    # learning_summary/key_success_factors/recommended_rules have no default (see
    # node37.record_distribution_knowledge's docstring: the previous default was a specific
    # fabricated performance claim). The operator must supply what was genuinely observed.
    learning_summary = body.get("learning_summary")
    key_success_factors = body.get("key_success_factors")
    recommended_rules = body.get("recommended_rules")
    if not learning_summary:
        raise ApiError(400, "validation_error", "learning_summary is required -- describe what was genuinely observed")
    if not key_success_factors:
        raise ApiError(400, "validation_error", "key_success_factors is required -- list what genuinely drove the result")
    if not recommended_rules:
        raise ApiError(400, "validation_error", "recommended_rules is required -- state real rules derived from this outcome")

    try:
        record = node37.record_distribution_knowledge(
            allocation,
            learning_summary=learning_summary,
            key_success_factors=key_success_factors,
            recommended_rules=recommended_rules,
        )
    except node37.KnowledgeBaseValidationError as exc:
        raise ApiError(400, "validation_error", str(exc)) from exc

    meta.setdefault("knowledge_entries", [])
    if not any(k["knowledge_entry_id"] == record["knowledge_entry_id"] for k in meta["knowledge_entries"]):
        meta["knowledge_entries"].append(record)
    append_lineage(meta, phase=7, node="node_37", action="record_distribution_knowledge", summary=f"Knowledge entry {record['knowledge_entry_id']} recorded")
    save_run_meta(run_id, meta)
    return record


# --- Campaign Queue: headless pipeline driver (plan §5/§9) -----------------------------------
# runAllInPanel() in console.js drives the single loaded run by clicking real DOM buttons -- that
# is inherently one run at a time, since only one run's forms exist in the page at once. Running
# many campaigns in parallel needs a driver that never touches the DOM: this calls the exact same
# real handler functions above, in-process, picking each step's input from the run's OWN latest
# state (mirroring the "pick the latest applicable ID" pattern the console.js forms already use),
# so N of these can run concurrently across N different run_ids via ordinary concurrent HTTP
# requests -- the server is already a ThreadingHTTPServer and every run's storage is already
# isolated (see plan §2), so no new concurrency primitive is needed here.
#
# Stops immediately, without raising, on any real blocker: a candidate not yet through its Phase 2
# approval gate, missing canonical facts (never fabricated), or any genuine ApiError from a real
# handler. Nodes 31/33 (lifecycle transition / outcome feedback) and 35/36/37 (amplification/
# allocation/knowledge) are intentionally not included -- they are follow-up analysis/learning
# actions a human or the winner-detection flow triggers afterward.
#
# As of 2026-08-19 this driver also stops BEFORE Nodes 27-34. It takes a campaign from a real
# demand signal to distribution-ready assets and stops. Lead capture, attribution, qualification,
# routing, performance measurement and winner detection all describe real-world events, and a
# driver cannot manufacture those -- see the hard stop in run_pipeline_headless() below.

_BLOCKING_CANDIDATE_STATUSES = (
    CANDIDATE_STATUS_PENDING_PHASE2_APPROVAL, CANDIDATE_STATUS_PENDING_PRODUCT,
    CANDIDATE_STATUS_PARKED, CANDIDATE_STATUS_STOPPED_NO_DEMAND,
)

# Commercial-intent gate (added 2026-08-19). Node 05's non-zero-results check alone cannot tell a
# real target from a nonsense one: a live search for "mars_spaceship_builder Catford" genuinely
# returned 10 HTTP-200 results (NASA/SpaceX/YouTube/STEM content) and the campaign sailed straight
# through Node 11/15 to the exact same needs_facts stopping point as every real boiler campaign.
# Node 11's commercial_intent_score is unconditionally computed on every classification (it is a
# required constructor field, never Optional) and is the cheapest real signal already available at
# that point. User's explicit, deliberate call: exclude classifications scoring 0, understanding
# this excludes real campaigns too -- Greenwich/Lewisham/Charlton/Eltham/Blackheath's own signals
# all score 0.0 on "restore hot water quickly" (no COMMERCIAL_KEYWORDS hit; that query is genuine,
# urgent demand that just hasn't used a buy-intent word). This is a known, accepted false-negative
# cost of a blunt threshold, not a claim that 0 commercial intent means fake demand -- the user
# named it explicitly: "maybe later we make the gates configurable if there is a need to vary".
MIN_COMMERCIAL_INTENT_SCORE = 0.0  # score must be STRICTLY GREATER than this to proceed
# A real signal of genuine demand, not just commercial_intent_score. Found live 2026-08-19: after
# widening Node 11's keyword vocabulary (v1.2.0, see intent_classification.py), a real query --
# "restore hot water quickly [town]" -- correctly computed urgency_level=HIGH (matching Node 03's
# own registered urgency=high for the same campaign) but STILL scored commercial_intent_score=0.0,
# because someone in genuine distress describes their PROBLEM, not a transaction -- "restore hot
# water quickly" contains no commercial word by its very nature as urgent language, not because
# the demand isn't real. Real high/critical urgency is itself real evidence of intent to pay for a
# fix, so it is accepted as an alternative to a nonzero commercial score, not a replacement for it.
URGENT_INTENT_LEVELS = frozenset({"high", "critical"})


def _passes_commercial_intent_gate(classification: dict[str, Any] | None) -> bool:
    if classification is None:
        return False
    try:
        score = float(classification.get("commercial_intent_score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    if score > MIN_COMMERCIAL_INTENT_SCORE:
        return True
    urgency = str(classification.get("urgency_level", "")).lower()
    return urgency in URGENT_INTENT_LEVELS


# Service-relevance gate (added 2026-08-19, same day as the commercial-intent gate, after direct
# user testing found the first gate insufficient). Two further real, live tests: snowmobile_repair
# in Catford returned real Catford car-mechanic businesses (whocanfixmycar.com, checkatrade.com) --
# genuinely local, genuinely commercial, but not snowmobile repair, since no such trade exists
# there. audience_hunter (a non-existent service concept) returned "Hunters Catford", a real local
# ESTATE AGENT, purely because it shares the surname token "Hunter" -- confirmed via a controlled
# side-by-side Firecrawl probe that this was a keyword coincidence, not a genuine service match
# (the identical query against Reykjavik, where no such coincidental business exists, correctly
# returned only generic travel content instead). Both cases passed the commercial-intent gate,
# since their queries contained real commercial words ("engineer", "quote"). Neither should have
# passed: a car mechanic is not a snowmobile mechanic, and an estate agent is not an audience
# hunter. This gate requires the service's OWN real name tokens -- not generic commercial words, not
# the geography, not a coincidental brand-name match -- to appear together in at least one real
# result. User's own framing: "service = snowmobile_repair (not est[ate] agent)".
_SERVICE_TOKEN_STOPWORDS = frozenset({"service", "services", "repair", "market", "and", "the", "of", "for"})


def _service_relevance_tokens(service_name: str) -> list[str]:
    """Real, meaningful tokens from a service slug -- generic trade words dropped so 'boiler_repair'
    checks for 'boiler', not the word every trade shares. If every token is generic (nothing
    distinctive left), the full token set is kept rather than returning nothing to check against."""
    tokens = [t for t in str(service_name or "").lower().replace("-", "_").split("_") if len(t) > 2]
    distinctive = [t for t in tokens if t not in _SERVICE_TOKEN_STOPWORDS]
    return distinctive or tokens


def _passes_service_relevance_gate(signal: dict[str, Any] | None, service_name: str) -> bool:
    if signal is None:
        return False
    # Only meaningful against a REAL live search: a manually-curated signal (source_type ==
    # "manual_curation") was typed by a human and carries no search_result_summary at all -- there
    # is no "does the fetched result actually match" to check. Applying this gate to those would
    # fail-closed every offline/manually-entered signal for the wrong reason (no results to check),
    # not the real reason this gate exists (results that ARE checkable turning out irrelevant).
    if signal.get("source_type") != "search_query":
        return True
    tokens = _service_relevance_tokens(service_name)
    if not tokens:
        return False
    summary = (signal.get("metadata") or {}).get("search_result_summary") or {}
    results = summary.get("top_results") or []
    for result in results:
        haystack = " ".join(str(result.get(k) or "") for k in ("title", "snippet", "link")).lower()
        if all(token in haystack for token in tokens):
            return True
    return False


def derive_campaign_state(meta: dict[str, Any]) -> str:
    status = meta.get("candidate_status")
    if status in _BLOCKING_CANDIDATE_STATUSES:
        return status
    if not meta.get("target"):
        return "no_target"
    if any(w.get("is_winner") for w in meta.get("winners", [])):
        return "winner_detected"
    if meta.get("performance_records"):
        return "awaiting_winner_detection"
    if meta.get("leads"):
        return "lead_captured"
    if not meta.get("demand_signals"):
        return "no_signal"
    # needs_facts must only fire once Phase 3 (classify, cluster) has genuinely run -- otherwise a
    # campaign with only a real signal reports "needs_facts" and run_pipeline_headless short-
    # circuits on that state before ever attempting Node 11/15, even though nothing blocks them.
    # Found live 2026-08-19: Lewisham/Charlton/Eltham each held a real Phase 2 signal and nothing
    # else, called pipeline/run_all, and got state="needs_facts", steps=[] back -- the driver never
    # even tried Node 11, despite it being fully runnable. Same root-ordering defect as
    # derive_campaign_position's Node 16/Node 11 misreport, in the sibling function that actually
    # gates execution rather than just display.
    if not meta.get("classifications"):
        return "running"
    if not _passes_commercial_intent_gate(meta["classifications"][-1]):
        return "stopped_low_commercial_intent"
    if not _passes_service_relevance_gate(meta["demand_signals"][-1], meta.get("target", {}).get("service", "")):
        return "stopped_service_not_locally_relevant"
    if not meta.get("clusters"):
        return "running"
    if not meta.get("facts"):
        return "needs_facts"
    published_ids = {p["video_asset_id"] for p in meta.get("video_publications", [])}
    if not any(v["video_asset_id"] in published_ids for v in meta.get("video_assets", [])):
        return "needs_real_render_and_publish"
    # Everything the pipeline can compute from real inputs is done; what remains needs real-world
    # events (a real enquiry, real spend). Named explicitly so this reads as a genuine resting
    # state rather than "running", which implied work was still progressing on its own.
    if meta.get("search_packages") or meta.get("routes"):
        return "distribution_ready_awaiting_real_events"
    return "running"


# Node-level position, for the global phase/node summary matrix: walks the SAME real artifact
# checks run_pipeline_headless() uses to decide what to run next (read-only here -- this never
# runs a node, only reports where a campaign already stands), so "current node" always reflects
# real state, never a guess. Each entry is (phase, node_label, action) -- action is a plain-
# English, real reason (the actual park reason where one exists, not a canned label).
def derive_campaign_position(meta: dict[str, Any]) -> dict[str, Any]:
    status = meta.get("candidate_status")
    if status == CANDIDATE_STATUS_PENDING_PRODUCT:
        return {"phase": 1, "node": "Node 02", "action": "Blocked: needs a real product description before Phase 2 can be requested"}
    if status == CANDIDATE_STATUS_PENDING_PHASE2_APPROVAL:
        return {"phase": 2, "node": "Node 05", "action": "Awaiting human approval before its real live-fetch can run"}
    if status == CANDIDATE_STATUS_PARKED:
        return {"phase": 2, "node": "Node 05", "action": meta.get("candidate_park_reason") or "Parked: live-fetch unavailable"}
    if status == CANDIDATE_STATUS_STOPPED_NO_DEMAND:
        return {"phase": 2, "node": "Node 05", "action": "Stopped: live-fetch ran but found no real demand"}

    if not meta.get("target"):
        return {"phase": 1, "node": "Node 01", "action": "Blocked: no target registered yet"}
    if not meta.get("demand_signals"):
        return {"phase": 2, "node": "Node 05", "action": "Blocked: no demand signal registered yet"}
    # Phase 3 (classify, cluster) runs before Phase 4 (facts), so those checks must come first --
    # checking facts here originally meant a campaign that had only reached Node 05 (real signal,
    # nothing else) was reported as blocked at Node 16, skipping straight past Nodes 11 and 15
    # which hadn't run yet either. Found live 2026-08-19: Lewisham/Charlton/Eltham each held zero
    # classifications and zero clusters but the console reported them all at "Phase 4 · Node 16".
    # Never exercised before because Node 05's live fetch had never previously succeeded, so no
    # real campaign had ever sat in this exact intermediate state.
    if not meta.get("classifications"):
        return {"phase": 3, "node": "Node 11", "action": "Next: classify the demand signal"}
    if not _passes_commercial_intent_gate(meta["classifications"][-1]):
        cls = meta["classifications"][-1]
        score, urgency = cls.get("commercial_intent_score"), cls.get("urgency_level")
        return {"phase": 3, "node": "Node 11", "action": f"Stopped: commercial_intent_score={score}, urgency_level={urgency} -- excluded, no real commercial or urgent intent detected in the real search query"}
    if not _passes_service_relevance_gate(meta["demand_signals"][-1], meta.get("target", {}).get("service", "")):
        return {"phase": 3, "node": "Node 11", "action": "Stopped: no real search result mentions this service -- excluded, real results found were for an unrelated business"}
    if not meta.get("clusters"):
        return {"phase": 3, "node": "Node 15", "action": "Next: generate a campaign cluster"}
    if not meta.get("facts"):
        return {"phase": 4, "node": "Node 16", "action": "Blocked: no canonical facts registered yet"}
    if not meta.get("video_assets"):
        return {"phase": 4, "node": "Node 18", "action": "Next: generate a video asset"}
    published_ids = {p["video_asset_id"] for p in meta.get("video_publications", [])}
    if not any(v["video_asset_id"] in published_ids for v in meta["video_assets"]):
        return {"phase": 4, "node": "Node 18", "action": "Next: trigger real EP048 render + YouTube upload for the generated video asset"}
    if not meta.get("approved_packages"):
        if meta.get("compliance_checks"):
            return {"phase": 4, "node": "Node 19", "action": "Stopped: rejected by quality/compliance review"}
        return {"phase": 4, "node": "Node 19", "action": "Next: quality & compliance review"}
    if not meta.get("publication_plans"):
        return {"phase": 5, "node": "Node 20", "action": "Next: build publication plan"}
    if not meta.get("search_packages"):
        return {"phase": 5, "node": "Node 21", "action": "Next: build search distribution package"}
    if not meta.get("routes"):
        return {"phase": 5, "node": "Node 26", "action": "Next: build route recommendation"}
    if not meta.get("leads"):
        return {"phase": 5, "node": "Node 27", "action": "Next: capture a lead"}
    if not meta.get("attributions"):
        return {"phase": 6, "node": "Node 28", "action": "Next: attribute the lead"}
    if not meta.get("qualifications"):
        return {"phase": 6, "node": "Node 29", "action": "Next: qualify the lead"}
    if not meta.get("routings"):
        return {"phase": 6, "node": "Node 30", "action": "Next: route the qualified lead"}
    if not meta.get("performance_records"):
        return {"phase": 7, "node": "Node 32", "action": "Next: record performance"}
    if not any(w.get("is_winner") for w in meta.get("winners", [])):
        return {"phase": 7, "node": "Node 34", "action": "Next: evaluate for a winning strategy"}
    return {"phase": 7, "node": "Node 34", "action": "Winner detected -- eligible for replication"}


def run_pipeline_headless(run_id: str) -> dict[str, Any]:
    meta = load_run_meta(run_id)
    state = derive_campaign_state(meta)
    if state in _BLOCKING_CANDIDATE_STATUSES or state in (
        "no_target", "no_signal", "needs_facts", "needs_real_render_and_publish",
        "stopped_low_commercial_intent", "stopped_service_not_locally_relevant",
    ):
        return {"run_id": run_id, "state": state, "steps": []}

    steps: list[str] = []
    try:
        signal = meta["demand_signals"][-1]
        already_classified = {c["signal_id"] for c in meta.get("classifications", [])}
        if signal["signal_id"] not in already_classified:
            handle_node11_classify(run_id, {
                "signal_id": signal["signal_id"], "raw_query": signal["raw_query"], "topic": signal["topic"],
                # Carry the signal's OWN source_type. This was hardcoded to "synthetic_fixture",
                # which stamped genuinely live search_query signals as fake in their permanent
                # classification record -- provenance corruption in the exact direction that
                # matters (real data mislabelled as synthetic). Harmless while every signal really
                # was a fixture; wrong the moment live fetch started working on 2026-08-19.
                # Node 11 already accepts "search_query", so nothing downstream needed changing.
                "source_type": signal.get("source_type") or "synthetic_fixture",
                "observed_at": signal.get("observed_at", now_iso()),
                "geography": signal["geography"], "service_context": signal.get("service_context", {}),
            })
            steps.append("node_11")
            meta = load_run_meta(run_id)

        # Commercial-intent gate: stop immediately after classification, before any clustering
        # spends further effort on a target with no detected commercial intent. Must be checked
        # here too (not just at the top of this function) because a campaign classified for the
        # FIRST TIME in this very call reaches this point with state not yet re-derived.
        if not _passes_commercial_intent_gate(meta["classifications"][-1]):
            return {"run_id": run_id, "state": "stopped_low_commercial_intent", "steps": steps}

        # Service-relevance gate: same checkpoint, same reasoning -- stop before clustering effort
        # is spent on a target whose real search results are for an unrelated business. Must also
        # be re-checked here for a campaign classified for the first time in this call.
        if not _passes_service_relevance_gate(signal, meta.get("target", {}).get("service", "")):
            return {"run_id": run_id, "state": "stopped_service_not_locally_relevant", "steps": steps}

        if not meta.get("clusters"):
            handle_node15_generate(run_id, {})
            steps.append("node_15")
            meta = load_run_meta(run_id)

        if not meta.get("facts"):
            # Genuinely stop here -- there is no real fact to build an asset from, and the driver
            # must never fabricate one. This case was previously unreachable: the caller-level
            # short-circuit on state=="needs_facts" used to fire before Node 11/15 ever ran, so
            # this point in the function was only ever reached with facts already present. Once
            # that short-circuit was corrected (2026-08-19) to let Node 11/15 run on a
            # signal-only campaign, this path became reachable for the first time and crashed with
            # KeyError: 'facts' on `meta["facts"]` below -- a genuine bug the earlier fix exposed,
            # not caused. Node 11/15's real progress is already saved and counted in `steps`.
            return {"run_id": run_id, "state": derive_campaign_state(meta), "steps": steps}

        if not meta.get("video_assets"):
            cluster_id = meta["clusters"][-1]["cluster_id"]
            fact_ids = [f["fact_id"] for f in meta["facts"]]
            handle_node18_generate(run_id, {"cluster_id": cluster_id, "fact_ids": fact_ids})
            steps.append("node_18")
            meta = load_run_meta(run_id)

        if not meta.get("approved_packages"):
            asset_id = meta["assets"][-1]["asset_id"]
            handle_node19_generate(run_id, {"asset_id": asset_id})
            steps.append("node_19")
            meta = load_run_meta(run_id)
        if not meta.get("approved_packages"):
            return {"run_id": run_id, "state": "rejected_by_node19", "steps": steps}

        if not meta.get("publication_plans"):
            asset_id = meta["approved_packages"][-1]["asset_id"]
            handle_node20_generate(run_id, {"asset_id": asset_id})
            steps.append("node_20")
            meta = load_run_meta(run_id)

        if not meta.get("search_packages"):
            plan_id = meta["publication_plans"][-1]["publication_plan_id"]
            handle_node21_generate(run_id, {"publication_plan_id": plan_id})
            steps.append("node_21")
            meta = load_run_meta(run_id)

        if not meta.get("routes"):
            search_distribution_id = meta["search_packages"][-1]["manifest"]["search_distribution_id"]
            handle_node26_generate(run_id, {"search_distribution_id": search_distribution_id})
            steps.append("node_26")
            meta = load_run_meta(run_id)

        # HARD STOP. The pipeline ends here, at distribution-ready.
        #
        # Everything above this line is DERIVED from real inputs the pipeline genuinely holds: a
        # real demand signal, real Node 16 facts, and content computed from them. Everything below
        # -- leads, attribution, qualification, routing, performance, winners -- describes things
        # that happen in the WORLD: a real person submitting a real form, real ad spend, real
        # revenue. No amount of computation can produce those, and a driver that calls those nodes
        # anyway does not "run the pipeline", it fabricates a business outcome.
        #
        # Removed 2026-08-19 on direct user instruction ("DO NOT INCLUDE FAKE data"). Until then
        # this driver called Nodes 27->34 with invented inputs and every campaign it touched ended
        # up reporting a lead, a performance record showing impressions/clicks/spend/revenue, and a
        # detected "winner" with a ROAS -- none of which had happened. Worst of all, Node 27 was
        # called with consent_granted=True: the runner manufactured a human being's consent, which
        # is not merely fake data but a fabricated compliance artifact.
        #
        # These nodes remain fully implemented and reachable through their own endpoints, where a
        # caller supplies real observed data. They are simply never driven from synthetic input.
        return {
            "run_id": run_id,
            "state": derive_campaign_state(load_run_meta(run_id)),
            "steps": steps,
            "stopped_at": "awaiting_real_world_events",
            "stop_reason": (
                "Distribution-ready. Nodes 27-34 (lead capture, attribution, qualification, routing, "
                "performance, winner detection) require real observed events -- a real enquiry, real "
                "spend, real revenue. They are never driven from generated input, so this campaign "
                "stops here until real data is recorded against it."
            ),
        }
    except ApiError as exc:
        return {"run_id": run_id, "state": f"error:{exc.error}", "message": exc.message, "steps": steps}

    return {"run_id": run_id, "state": derive_campaign_state(meta), "steps": steps}


def handle_pipeline_run_all(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return run_pipeline_headless(run_id)


def campaign_queue_snapshot() -> dict[str, Any]:
    campaigns = []
    for m in list_runs():
        position = derive_campaign_position(m)
        campaigns.append({
            "run_id": m["run_id"], "target": m.get("target"), "state": derive_campaign_state(m),
            "phase": position["phase"], "node": position["node"], "action": position["action"],
        })
    phase_counts = {p: 0 for p in range(1, 8)}
    for c in campaigns:
        phase_counts[c["phase"]] += 1
    return {"campaigns": campaigns, "phase_counts": phase_counts}


# --- Bulk campaign import (plan §6): one row -> one new real campaign --------------------------
# Same real Node 01/02/03/04 validation as manual entry, no bulk-only relaxed rules -- each row
# just calls the exact same handlers above. One bad row is reported and skipped, never aborts the
# rest of the batch. Comma-separated cell fields (features/benefits/differentiators/needs/pains)
# use the same convention the manual console form already uses -- a spreadsheet app quotes a cell
# containing a literal comma automatically, so csv.DictReader already hands back the field intact.

_BULK_IMPORT_REQUIRED_COLUMNS = (
    "target_type", "service", "market", "geography_locality", "geography_region", "geography_country",
    "product_problem", "product_solution", "product_features", "product_benefits", "product_differentiators",
    "product_commercial_model", "product_customer_outcome",
    "audience_segment_name", "audience_needs", "audience_pains", "audience_urgency",
)


def _split_csv_list(value: str) -> list[str]:
    return [s.strip() for s in (value or "").split(",") if s.strip()]


def handle_bulk_import(body: dict[str, Any]) -> dict[str, Any]:
    csv_text = body.get("csv")
    if not csv_text or not isinstance(csv_text, str):
        raise ApiError(400, "validation_error", "csv is required and must be a non-empty string")

    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise ApiError(400, "validation_error", "csv has no header row")
    missing_columns = [c for c in _BULK_IMPORT_REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing_columns:
        raise ApiError(400, "validation_error", f"csv is missing required column(s): {missing_columns}")

    created: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for row_num, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            geography = {
                "locality": row["geography_locality"], "region": row["geography_region"], "country": row["geography_country"],
            }
            new_meta = create_run()
            new_run_id = new_meta["run_id"]
            handle_node01_register(new_run_id, {
                "target_type": row["target_type"], "service": row["service"], "market": row["market"], "geography": geography,
            })
            handle_node02_register(new_run_id, {
                "problem": row["product_problem"], "solution": row["product_solution"],
                "features": _split_csv_list(row["product_features"]), "benefits": _split_csv_list(row["product_benefits"]),
                "differentiators": _split_csv_list(row["product_differentiators"]),
                "commercial_model": row["product_commercial_model"], "customer_outcome": row["product_customer_outcome"],
            })
            handle_node03_register(new_run_id, {
                "segment_name": row["audience_segment_name"], "needs": _split_csv_list(row["audience_needs"]),
                "pains": _split_csv_list(row["audience_pains"]), "urgency": row["audience_urgency"],
                "eligibility_geography": geography,
            })
            handle_node04_register(new_run_id, {})
        except ApiError as exc:
            failed.append({"row": row_num, "error": exc.message})
            continue
        new_meta = load_run_meta(new_run_id)
        append_lineage(new_meta, phase=1, node="node_01", action="bulk_import_row", summary=f"Imported from CSV row {row_num}")
        save_run_meta(new_run_id, new_meta)
        created.append({"row": row_num, "run_id": new_run_id, "target": new_meta["target"]})

    return {"created": created, "failed": failed}


# --- Demand-first Discovery 00A-00F -----------------------------------------

def discovery_store() -> DiscoveryStore:
    return DiscoveryStore(DATA_ROOT.parent / "discovery")


def _raise_discovery(exc: DiscoveryError) -> None:
    raise ApiError(404 if "not found" in str(exc).lower() else 400, "discovery_error", str(exc)) from exc


def handle_discovery_create(body: dict[str, Any]) -> dict[str, Any]:
    try:
        return discovery_store().create(body)
    except DiscoveryError as exc:
        _raise_discovery(exc)


def handle_discovery_signals(discovery_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        return discovery_store().add_signals(discovery_id, list(body.get("signals") or []))
    except DiscoveryError as exc:
        _raise_discovery(exc)


def handle_discovery_collect(discovery_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Run bounded, read-only discovery searches through the configured Firecrawl adapter."""
    store = discovery_store()
    try:
        record = store.load(discovery_id)
    except DiscoveryError as exc:
        _raise_discovery(exc)
    brief = record["brief"]
    geography = {"locality": brief["geography"], "region": brief["geography"], "country": "UK"}
    topics = [
        f"{brief['audience']} {brief['problem_territory']} complaints urgent cost pay",
        f"{brief['audience']} alternatives reviews problems price subscription",
        f"{brief['problem_territory']} workaround deadline penalty budget",
    ]
    gathered: list[dict[str, Any]] = []
    def fetch(topic: str) -> tuple[dict[str, Any], Any]:
        with _DISCOVERY_SEARCH_SLOTS:
            return node05.fetch_search_demand(topic, geography)
    try:
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="ep050-discovery") as pool:
            futures = {pool.submit(fetch, topic): topic for topic in topics}
            for future in as_completed(futures):
                result, receipt = future.result()
                for item in result["top_results"]:
                    if not item.get("link") or not item.get("snippet"):
                        continue
                    gathered.append({"source_url": item["link"], "source_type": "web_search", "observed_at": receipt.fetched_at, "problem_statement": item["snippet"], "evidence_excerpt": item["snippet"], "urgency_cues": [], "payment_cues": []})
    except live_fetch.LiveFetchDisabledError as exc:
        raise ApiError(503, "live_fetch_disabled", str(exc)) from exc
    except live_fetch.MissingCredentialError as exc:
        raise ApiError(503, "missing_credential", str(exc)) from exc
    except live_fetch.LiveFetchError as exc:
        raise ApiError(502, "live_fetch_error", str(exc)) from exc
    try:
        return store.add_signals(discovery_id, gathered)
    except DiscoveryError as exc:
        _raise_discovery(exc)


def handle_discovery_validation(discovery_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        return discovery_store().add_validation(discovery_id, list(body.get("outcomes") or []))
    except DiscoveryError as exc:
        _raise_discovery(exc)


def handle_discovery_evaluate(discovery_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        return discovery_store().evaluate(discovery_id)
    except DiscoveryError as exc:
        _raise_discovery(exc)


def _discovery_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:80] or "discovered_offer"


def handle_discovery_merge(discovery_id: str, body: dict[str, Any]) -> dict[str, Any]:
    store = discovery_store()
    try:
        discovery = store.load(discovery_id)
    except DiscoveryError as exc:
        _raise_discovery(exc)
    if discovery.get("run_id"):
        return {"discovery": discovery, "run": load_run_meta(discovery["run_id"]), "idempotent": True}
    if discovery.get("state") != "validated_ready_to_merge" or not discovery.get("contract"):
        raise ApiError(409, "not_merge_ready", "Discovery must pass 00F before entering Node 15")
    contract = discovery["contract"];offer = contract["offer"];geo_name = contract["geography"]
    service = _discovery_slug(offer["name"]);geography = {"locality": geo_name, "region": geo_name, "country": "UK"}
    run_id = create_run()["run_id"]
    handle_node01_register(run_id, {"target_type": "service_market", "service": service, "market": _discovery_slug(contract["problem"]), "geography": geography})
    handle_node02_register(run_id, {"problem": contract["problem"], "solution": offer["value_proposition"], "features": offer["minimum_features"], "benefits": [offer["value_proposition"]], "differentiators": ["Evidence-led concept"], "commercial_model": contract["commercial_model"], "customer_outcome": contract["conversion_objective"]})
    handle_node03_register(run_id, {"segment_name": contract["audience"], "needs": [contract["problem"]], "pains": [contract["problem"]], "urgency": "high", "eligibility_geography": geography})
    handle_node04_register(run_id, {"success_criteria": contract["success_criteria"]})
    for signal in discovery["signals"]:
        node_signal = handle_node05_register(run_id, {"signal_id": signal["signal_id"], "raw_query": signal["problem_statement"], "topic": _discovery_slug(contract["problem"]), "source_type": "manual_curation", "observed_at": signal["observed_at"], "geography": geography, "service_context": {"service_name": service, "market_segment": _discovery_slug(contract["problem"])}, "metadata": {"discovery_id": discovery_id, "source_url": signal["source_url"], "source_domain": signal["source_domain"], "evidence_excerpt": signal["evidence_excerpt"]}})
        handle_node11_classify(run_id, {"signal_id": node_signal["signal_id"], "raw_query": node_signal["raw_query"], "topic": node_signal["topic"], "source_type": node_signal["source_type"], "observed_at": node_signal["observed_at"], "geography": node_signal["geography"], "service_context": node_signal["service_context"]})
    clusters = handle_node15_generate(run_id, {"campaign_context": "Validated demand discovery branch"})
    run_meta = load_run_meta(run_id);run_meta["validated_opportunity_offer_contract"] = contract;run_meta["originating_branch"] = "discovery"
    append_lineage(run_meta, phase=3, node="node_15", action="discovery_contract_merged", summary=f"Discovery {discovery_id} entered the shared pipeline")
    save_run_meta(run_id, run_meta)
    discovery = store.load(discovery_id);discovery["run_id"] = run_id;discovery["state"] = "merged_to_node15";discovery["lineage"].append({"stage": "MERGE", "at": now_iso(), "action": "node15_handoff", "run_id": run_id});store.save(discovery)
    return {"discovery": discovery, "run": load_run_meta(run_id), "clusters": clusters["clusters"], "idempotent": False}


# Five explicit, mutually exclusive states per node, reconciled against board/workstream
# acceptance evidence at the time of writing (see board event 20260817T113648989_codex_781e7f99,
# the CHANGE REQUIRED that replaced the prior misleading implemented_nodes/locked_nodes binary):
#   accepted_nodes        -- EP050-accepted at 100% (board evidence), regardless of console wiring.
#   console_controls      -- subset of accepted_nodes wired as an executable control in THIS console
#                             (a dedicated form, or run for real as an internal pipeline step).
#   pending_acceptance_nodes -- evidenced but not yet accepted (e.g. awaiting a lifecycle-mirror gate).
#   mvp_deferred_nodes    -- explicitly deferred under the approved MVP classification; never
#                             implemented and never claimed complete.
#   not_started_nodes     -- no allocation or work has begun.
# Every node in a phase's range appears in exactly one of these five lists.
PHASES = [
    {
        "phase": 1, "id": "ingestion", "title": "Product/Market Ingestion", "nodes": "01-04",
        "accepted_nodes": ["01", "02", "03", "04"], "console_controls": ["01", "02", "03", "04"],
        "pending_acceptance_nodes": [], "mvp_deferred_nodes": [], "not_started_nodes": [],
    },
    {
        "phase": 2, "id": "demand_intelligence", "title": "Demand Intelligence", "nodes": "05-10",
        "accepted_nodes": ["05", "06", "07", "08", "09", "10"],
        "console_controls": ["05", "06", "07", "08", "09", "10"],
        "pending_acceptance_nodes": [], "mvp_deferred_nodes": [], "not_started_nodes": [],
    },
    {
        "phase": 3, "id": "strategy", "title": "Strategy", "nodes": "11-15",
        "accepted_nodes": ["11", "12", "13", "14", "15"], "console_controls": ["11", "12", "13", "14", "15"],
        "pending_acceptance_nodes": [], "mvp_deferred_nodes": [], "not_started_nodes": [],
    },
    {
        "phase": 4, "id": "assets", "title": "Content & Assets", "nodes": "16-19",
        "accepted_nodes": ["16", "17", "18", "19"], "console_controls": ["16", "17", "18", "19"],
        "pending_acceptance_nodes": [], "mvp_deferred_nodes": [], "not_started_nodes": [],
    },
    {
        "phase": 5, "id": "distribution_conversion", "title": "Distribution & Conversion", "nodes": "20-27",
        "accepted_nodes": ["20", "21", "26"], "console_controls": ["20", "21", "26"],
        "pending_acceptance_nodes": ["27"], "mvp_deferred_nodes": ["22", "23", "24", "25"], "not_started_nodes": [],
    },
    {
        "phase": 6, "id": "lead_lifecycle", "title": "Lead Lifecycle", "nodes": "28-31",
        "accepted_nodes": [], "console_controls": [],
        "pending_acceptance_nodes": ["28", "29", "30", "31"], "mvp_deferred_nodes": [], "not_started_nodes": [],
    },
    {
        "phase": 7, "id": "learning", "title": "Learning & Optimization", "nodes": "32-37",
        "accepted_nodes": [], "console_controls": [],
        "pending_acceptance_nodes": ["32", "33", "34", "35", "36", "37"], "mvp_deferred_nodes": [], "not_started_nodes": [],
    },
]

STATIC_FILES = {
    "/demand-operations.css": ("text/css; charset=utf-8", ROOT / "demand-operations.css"),
    "/demand-operations.js": ("application/javascript; charset=utf-8", ROOT / "demand-operations.js"),
    "/console.css": ("text/css; charset=utf-8", ROOT / "console.css"),
    "/console.js": ("application/javascript; charset=utf-8", ROOT / "console.js"),
}


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "EP050OperationalConsole/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        pass  # keep console output quiet; readiness/tests read HTTP responses, not logs

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, content_type: str, path: Path) -> None:
        if not path.exists():
            self._send_json(404, {"error": "not_found", "message": str(path.name)})
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            raise ApiError(400, "invalid_json", str(exc)) from exc

    # --- routing -----------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/" or path == "/console.html" or path == "/demand-operations.html":
                self._send_file("text/html; charset=utf-8", ROOT / "demand-operations.html")
                return
            if path in STATIC_FILES:
                content_type, file_path = STATIC_FILES[path]
                self._send_file(content_type, file_path)
                return
            if path == "/api/status":
                self._send_json(200, {"status": "ok", "phases": len(PHASES), "external_action": False})
                return
            if path == "/api/phases":
                self._send_json(200, {"phases": PHASES})
                return
            if path == "/api/live_fetch_status":
                self._send_json(200, live_fetch_status())
                return
            if path == "/api/known_values":
                self._send_json(200, known_values())
                return
            if path == "/api/runs":
                self._send_json(200, {"runs": list_runs()})
                return
            if path == "/api/campaign_queue":
                self._send_json(200, campaign_queue_snapshot())
                return
            if path == "/api/discoveries":
                self._send_json(200, {"discoveries": discovery_store().list()})
                return
            match = re.match(r"^/api/discoveries/([^/]+)$", path)
            if match:
                try:
                    self._send_json(200, discovery_store().load(match.group(1)))
                except DiscoveryError as exc:
                    _raise_discovery(exc)
                return
            if path == "/intake":
                run_id = parse_qs(parsed.query).get("run", [""])[0]
                if not run_id:
                    self._send_html(400, "<p>Missing ?run=&lt;run_id&gt;</p>")
                    return
                meta = load_run_meta(run_id)
                self._send_html(200, render_intake_form(run_id, meta))
                return
            match = re.match(r"^/api/runs/([^/]+)$", path)
            if match:
                self._send_json(200, load_run_meta(match.group(1)))
                return
            self._send_json(404, {"error": "not_found", "message": path})
        except ApiError as exc:
            self._send_json(exc.status, {"error": exc.error, "message": exc.message})

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/runs":
                self._send_json(201, create_run())
                return
            if path == "/api/bulk_import":
                self._send_json(200, handle_bulk_import(self._read_json_body()))
                return
            if path == "/api/discoveries":
                self._send_json(201, handle_discovery_create(self._read_json_body()))
                return
            body = self._read_json_body()
            discovery_match = re.match(r"^/api/discoveries/([^/]+)/(signals|collect|validation|evaluate|merge)$", path)
            if discovery_match:
                discovery_id, action = discovery_match.groups()
                discovery_handlers = {"signals": handle_discovery_signals, "collect": handle_discovery_collect, "validation": handle_discovery_validation, "evaluate": handle_discovery_evaluate, "merge": handle_discovery_merge}
                self._send_json(200, discovery_handlers[action](discovery_id, body))
                return
            match = re.match(
                r"^/api/runs/([^/]+)/(node0[1-9]|node10|node0[5-9]/live|node10/live|"
                r"node11/classify|node15/generate|node15/live|node16/fact|node18/generate|node18/live|"
                r"node18/replicate_winner|node18/generate_by_format|node18/trigger_render_and_publish|"
                r"node01/propose_candidates|node01/approve_phase2|pipeline/run_all|demand_scan/status|"
                r"node19/generate|node20/generate|node21/generate|node26/generate|node27/generate|"
                r"node27/public_intake|node28/generate|node29/generate|node30/generate|"
                r"node31/generate|node32/generate|node33/generate|node34/generate|node35/generate|"
                r"node36/generate|node37/generate)$",
                path,
            )
            if match:
                run_id, action = match.group(1), match.group(2)
                handlers = {
                    "node01": handle_node01_register,
                    "node02": handle_node02_register,
                    "node03": handle_node03_register,
                    "node04": handle_node04_register,
                    "node05": handle_node05_register,
                    "node06": handle_node06_register,
                    "node07": handle_node07_register,
                    "node08": handle_node08_register,
                    "node09": handle_node09_register,
                    "node10": handle_node10_register,
                    "node05/live": handle_node05_live,
                    "node06/live": handle_node06_live,
                    "node07/live": handle_node07_live,
                    "node08/live": handle_node08_live,
                    "node09/live": handle_node09_live,
                    "node10/live": handle_node10_live,
                    "node11/classify": handle_node11_classify,
                    "node15/generate": handle_node15_generate,
                    "node15/live": handle_node15_live_generate,
                    "node16/fact": handle_node16_fact,
                    "node18/generate": handle_node18_generate,
                    "node18/live": handle_node18_live_generate,
                    "node18/replicate_winner": handle_node18_replicate_winner,
                    "node18/generate_by_format": handle_node18_generate_by_format,
                    "node18/trigger_render_and_publish": handle_node18_trigger_render_and_publish,
                    "node01/propose_candidates": handle_node01_propose_candidates,
                    "node01/approve_phase2": handle_node01_approve_phase2,
                    "pipeline/run_all": handle_pipeline_run_all,
                    "demand_scan/status": handle_demand_scan_status,
                    "node19/generate": handle_node19_generate,
                    "node20/generate": handle_node20_generate,
                    "node21/generate": handle_node21_generate,
                    "node26/generate": handle_node26_generate,
                    "node27/generate": handle_node27_generate,
                    "node27/public_intake": handle_node27_public_intake,
                    "node28/generate": handle_node28_generate,
                    "node29/generate": handle_node29_generate,
                    "node30/generate": handle_node30_generate,
                    "node31/generate": handle_node31_generate,
                    "node32/generate": handle_node32_generate,
                    "node33/generate": handle_node33_generate,
                    "node34/generate": handle_node34_generate,
                    "node35/generate": handle_node35_generate,
                    "node36/generate": handle_node36_generate,
                    "node37/generate": handle_node37_generate,
                }
                self._send_json(200, handlers[action](run_id, body))
                return
            self._send_json(404, {"error": "not_found", "message": path})
        except ApiError as exc:
            self._send_json(exc.status, {"error": exc.error, "message": exc.message})


def run(port: int = 8060, host: str = "127.0.0.1") -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), ConsoleHandler)
    print(f"EP050 Operational Console v2 listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    # Render (and most PaaS hosts) assign the port via $PORT and require binding
    # 0.0.0.0; local runs keep the existing 127.0.0.1 default so nothing changes
    # for the desktop workflow. A positional CLI arg still overrides the port.
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8060))
    host_arg = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    run(port_arg, host_arg)
