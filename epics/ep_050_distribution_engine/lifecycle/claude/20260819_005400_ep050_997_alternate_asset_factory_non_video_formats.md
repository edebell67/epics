# EP050 — Alternate (Non-Video) Asset Factory, Sibling to Node 18

Source: Direct user question ("is it assumed that default message will be via a video?"),
answered by tracing the real code (confirmed Node 18 ignores Node 14's real format
recommendation entirely), then explicit instruction: "add sibling asset factories for the
non-video formats."

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "Node 18 video asset factory (met, pre-existing) -- this is a sibling to it, not a replacement"

Task Summary: Confirmed a real, previously-undetected gap: `node_18/video_asset_factory.py`
never reads `asset.metadata.format` anywhere, so it renders every asset as a video regardless of
what Node 14 (Channel Placement Selection) actually recommended. Node 14 has four real recommended
formats, none of them video: `verified_local_listing_with_emergency_hours`,
`step_by_step_troubleshooting_guide`, `callout_extension_ad_24_7_emergency`,
`community_recommendation_post`. Built `node_18/alternate_asset_factory.py`, a sibling factory
that registers the same real, already-validated Node 17 `AssetPayload` (title/body_content/
disclaimer/CTA/full lineage, no PII, fact-traceable) as the final asset for these four formats
instead of forcing it through a video-specific renderer -- reusing Node 17's own validation rather
than re-deriving it, and structuring the same real content per format (never inventing a new
claim, e.g. no fabricated business hours for the listing format). `community_recommendation_post`
is flagged `requires_human_review=True`, matching the existing Node 24 human-in-the-loop finding
already on record from earlier this session. Wired a new `handle_node18_generate_by_format`
endpoint that dispatches on the asset's own real format -- the existing always-video
`node18/generate` endpoint is completely unchanged, this is an additive sibling, not a behavior
change.

Context:
- `epics/ep_050_distribution_engine/implementation/node_18/alternate_asset_factory.py` (new, v1.0.0)
- `epics/ep_050_distribution_engine/implementation/node_18/test_alternate_asset_factory.py` (new)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py` (v1.9.3 -> v1.9.4)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js` (v1.10.4 -> v1.10.5)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`

Destination Folder: `epics/ep_050_distribution_engine/implementation/`; this lifecycle record under `workstream/300_complete/`.

Dependency: Node 18 video asset factory, Node 17 content/utility factory (both met, pre-existing).

## Plan
- [x] 1. Confirmed the gap by direct code inspection (grepped video_asset_factory.py for any
      reference to `format`/`recommended_format` -- none found) rather than assuming, in response
      to the user's direct question.
  - [x] Test: Code inspection.
  - [x] Evidence: Implementation Log.
- [x] 2. Confirmed Node 17's `AssetPayload` is already format-agnostic real content (title, body,
      disclaimer, CTA, full lineage) before designing the sibling factory, to avoid re-deriving
      validation that already exists.
  - [x] Test: Code inspection of `content_utility_factory.py`.
  - [x] Evidence: Implementation Log.
- [x] 3. Built `alternate_asset_factory.py`: 4 format-specific content builders (listing/guide/
      ad/community-post), shared lineage/PII/disclaimer/CTA validation mirroring Node 18's own
      rigor, deterministic ID + idempotent/conflict registry pattern.
  - [x] Test: 16 new unit tests (positive per format, fail-closed negative cases, determinism,
        idempotency, conflict, persistence round-trip).
  - [x] Evidence: Implementation Log.
- [x] 4. Wired `handle_node18_generate_by_format` in server.py, dispatching on the asset's real
      format; added the route; left the existing `node18/generate` endpoint untouched.
  - [x] Test: New `test_node18_generate_by_format_dispatches_to_alternate_registry_for_a_real_non_video_format`,
        using the real deterministic ranking outcome for the standard fixture (confirmed via a
        direct script run before writing the assertion, not guessed).
  - [x] Evidence: Implementation Log.
- [x] 5. Added the console.js UI: a second "Generate (format-aware)" button alongside the
      existing always-video one.
  - [x] Test: Live browser -- both buttons render; format-aware button called for real against
        the live run, produced a genuine listing asset (not a video) with real content.
  - [x] Evidence: Implementation Log.
- [x] 6. Full regression pass, version bumps.
  - [x] Test: `pytest test_console_server.py -q` -- 88/88; `pytest node_18/ -q` -- 54/54 (both
        factories together, no collisions).
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the requested scope (sibling asset factories for the four
real non-video formats).
Auto-Acceptance: false (new asset-generation surface; verified live against real run data)
- Evidence-Type: manual_verification
  - Artifact: Live `POST /api/runs/run_20260818_102850_a3e4d29f/node18/generate_by_format` against
    the real live run's real cluster/fact -- returned a genuine `verified_local_listing_with_
    emergency_hours` asset with real content ("Emergency Boiler Repair Blackheath | 24/7 Local Gas
    Safe Engineers", real fact text embedded, real CTA/disclaimer), correctly NOT a video asset.
    Confirmed via the real ranking algorithm (run directly, not assumed) that this format is
    genuinely what Node 14 recommends top for this fixture.
  - Objective-Proved: The dispatch is real and correct, and the content is genuine, fact-derived
    text -- not a stub or placeholder.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest node_18/test_alternate_asset_factory.py -v` -- 16/16;
    `pytest test_console_server.py -q` -- 88/88; `pytest node_18/ -q` (both factories) -- 54/54.
  - Objective-Proved: Full positive/negative/determinism/idempotency/conflict coverage, no
    regression to the existing video path.
  - Status: captured

## Implementation Log
- 2026-08-19T00:35+01:00 -- User asked "is it assumed that default message will be via a video?";
  traced video_asset_factory.py directly, confirmed it never reads format at all; traced Node 14's
  real recommended_format values (4 real non-video formats).
- 2026-08-19T00:38+01:00 -- User instructed: "add sibling asset factories for the non-video
  formats." Read Node 17's AssetPayload in full, confirmed it's already real, format-agnostic,
  validated content -- narrowing the actual scope of what needed building.
- 2026-08-19T00:45+01:00 -- Built `alternate_asset_factory.py` (4 format builders, shared
  validation, registry).
- 2026-08-19T00:50+01:00 -- Built and ran `test_alternate_asset_factory.py` -- 16/16 passing.
- 2026-08-19T00:52+01:00 -- Wired `handle_node18_generate_by_format` in server.py; ran a direct
  script first to confirm which real format the standard test fixture naturally ranks top
  (`verified_local_listing_with_emergency_hours`), then wrote the server-level test against that
  confirmed real outcome.
- 2026-08-19T00:53+01:00 -- Full regression (88/88 + 54/54), added the console.js UI button.
- 2026-08-19T00:54+01:00 -- Restarted the dev server, live-verified against the real live run:
  real listing asset produced with genuine content, correctly not a video.
- 2026-08-19T00:55+01:00 -- Version bumps (server.py v1.9.4, console.js v1.10.5,
  alternate_asset_factory.py v1.0.0), filed this record.

## Changes Made
- Added `epics/ep_050_distribution_engine/implementation/node_18/alternate_asset_factory.py`.
- Added `epics/ep_050_distribution_engine/implementation/node_18/test_alternate_asset_factory.py`.
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py`
  (v1.9.3 -> v1.9.4): `import alternate_asset_factory as node18b`, `node18b_registry()`,
  `handle_node18_generate_by_format()`, new route `node18/generate_by_format`.
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js`
  (v1.10.4 -> v1.10.5): second button in `buildNode18Block()`.
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`:
  1 new test.

## Validation
- PASS -- `pytest node_18/test_alternate_asset_factory.py -v` -- 16/16.
- PASS -- `pytest test_console_server.py -q` -- 88/88.
- PASS -- `pytest node_18/ -q` (video + alternate together) -- 54/54, no collisions.
- PASS -- Live: real dispatch against the real live run produced genuine, correct, non-video
  content.

## Risks/Notes
- **The existing `node18/generate` endpoint is completely unchanged** -- this was a deliberate
  design choice to avoid any risk to the 15+ existing tests and console.js flows that depend on
  its always-video response shape. `node18/generate_by_format` is a new, additive sibling endpoint,
  not a migration.
- **No fabricated business facts**: the listing format's "availability_note" deliberately says
  "Contact for current availability" rather than inventing specific hours, since no node in this
  pipeline registers real business hours anywhere -- asserting specific hours would have been
  exactly the kind of fabrication this whole session has been correcting.
- **community_recommendation_post is gated**, not silently treated as auto-publish-ready, matching
  the existing Node 24 finding. No enforcement of that gate exists yet at the distribution layer
  (Phase 5 nodes) -- flagged for whoever wires real community distribution later, not built here.
- `node18/live` (the live-chain generator) was not extended with format-awareness in this task --
  it still always produces a video. Flagged as a natural follow-on if useful, not assumed to be in
  scope here.

## Completion Status
Complete for the requested scope: real sibling asset factories for all four non-video formats
Node 14 already recommends, dispatched automatically by real format, live-verified against the
real live run producing genuine (not stub) content.
