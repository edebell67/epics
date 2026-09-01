// epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js
// EP050 Operational Console v2 — client logic, no external CDN/framework.
//
// VERSION HISTORY
// v1.10.5 · 2026-08-19 · Adds a second Node 18 button, "Generate (format-aware)", alongside the
//   existing always-video one -- calls the new server.py node18/generate_by_format endpoint
//   (v1.9.4 companion), which routes to whichever real asset type Node 14 actually recommended
//   instead of always forcing a video. The original "Generate Video Asset" button is unchanged
//   and still always produces a video, for whenever that's genuinely what's wanted. Live-verified
//   against the real live run: the format-aware button correctly produced a real, distinct
//   verified-local-listing asset (not a video) from the same cluster/facts.
// v1.10.4 · 2026-08-18 · Removes manual data entry from Nodes 05-10 entirely, per direct user
//   instruction ("the manual version is unworkable... good for testing... but not for real use...
//   we wont use them for real analysis... it has to be automated and work via searching +
//   automated process only"). Each of the six node blocks (buildNode05Block..buildNode10Block)
//   previously had a "Record X" manual-submit button pre-filled with demo/fixture values
//   (sig_demand_01, q_demo_01, etc.) sitting right next to its real Live fetch button --
//   indistinguishable at a glance, and exactly what let Catford's Phase 2 get fabricated earlier
//   this session. Now each block keeps only the fields its own Live fetch call actually needs
//   (e.g. Node 08 keeps competitor_url/channel/query since live fetch uses them; Node 06/07 need
//   no node-specific fields at all) and the Live fetch button -- manual submission is gone. Also
//   removed the now-fully-dead shared "source type" field (no live-fetch payload ever used it)
//   and the "Run all Phase 2" button (nothing left in this phase for it to click). Test fixtures
//   are unaffected -- test_console_server.py builds its fixtures via direct HTTP calls to the
//   still-present server-side manual endpoints, never through this UI. Live-verified: Node 06's
//   Live fetch still works end to end, pulling a real Stack Exchange question (real fetch_receipt,
//   HTTP 200, real diy.stackexchange.com URL) -- removing the manual path didn't touch the real one.
// v1.10.3 · 2026-08-18 · Fixes a real fabrication-prevention hole found live: Campaign Overview's
//   "Run Full Pipeline (Phase 2 -> 7)" button had zero awareness of candidate_status, so running
//   it on a candidate still at pending_phase2_approval clicked straight through Phase 2's manual-
//   entry forms using whatever demo/default values sat in them (sig_demand_01, q_demo_01, etc.),
//   fabricating a full Phase 2-4 chain under a candidate that was supposed to earn a real signal
//   first via Campaign Queue's approval gate -- the exact fabrication this session's whole design
//   was built to prevent, just reachable through a different button that never checked. Added
//   CANDIDATE_BLOCKING_STATUSES (mirrors server.py's _BLOCKING_CANDIDATE_STATUSES) and a guard at
//   the top of runFullPipeline() that refuses to run when the loaded run is a blocked candidate.
//   Live-verified: refuses correctly on a real pending candidate, still runs normally on a real
//   non-candidate run. The contaminated Catford run this bug produced was deleted, not salvaged.
// v1.10.2 · 2026-08-18 · Adds the global phase/node summary matrix to Campaign Queue (server.py
//   v1.9.2 companion), directly per user request for a global "P1|P2|...|P7" view with drill-down
//   to campaign/status/action. Seven clickable cells (PHASE_ORDER) show live counts from GET
//   /api/campaign_queue's phase_counts; clicking one filters the list below to just that phase.
//   Each campaign row now shows its real phase/node/action (e.g. the real Node 05 403 text) in
//   place of the old coarse state label. Live-verified: counts and filter both match real state.
// v1.10.1 · 2026-08-18 · Fixes a real UX gap found live: the "Approve real Phase 2 live-fetch"
//   action only ever appeared in the transient list rendered right after the original "Propose
//   candidates" click (buildCandidateApprovalRow, only called from that one handler) -- once
//   propose_candidates became idempotent (server.py v1.9.0), re-clicking Propose no longer
//   regenerated that list, so after any page reload a pending candidate had no way to be
//   approved at all. Campaign Queue's per-row rendering now shows the same approve button
//   whenever a row's state is pending_phase2_approval, persistent across reloads. Live-verified:
//   approved a real candidate (Greenwich) from the queue, confirmed it transitioned to parked
//   (hit the real Node 05 Search 403) and the button correctly disappeared once no longer pending.
// v1.10.0 · 2026-08-18 · Winner-replication & scale-out build (server.py v1.9.0 companion; see
//   that entry for the full server-side list). Also folds in the Phase 6/7 (Nodes 28-37)
//   node-block UI from earlier this session, which had shipped without its own version entry.
//   - buildNode28Block()..buildNode37Block(), refreshPhase6And7Selectors(), wired into
//     buildPhasePanel() for the lead_lifecycle/learning phases.
//   - Campaign Overview rebuilt: buildWhatWorkedSection() replaces the bare numeric grid with
//     real narrative (winning channel/ROAS, Node 37's recommended rules, amplification's
//     expansion variants, the qualification factors behind a real qualifying lead) -- the
//     numeric grid is kept as secondary "supporting detail", not removed.
//   - "⟳ Replicate this winning campaign" and "⤢ Propose one-hop candidate campaigns" buttons on
//     the winner card; buildCandidateApprovalRow() shows each candidate's real state with an
//     inline "Approve real Phase 2 live-fetch" action where applicable.
//   - buildSpendRollup(): renders nothing at all while no lineage event carries a real cost_gbp
//     (today's honest baseline), rather than showing a misleading £0.00.
//   - New Campaign Queue secondary panel: buildCampaignQueuePanel() lists every campaign with its
//     real state, per-row Load/Run Full Pipeline, "Run all runnable campaigns" (concurrent via
//     Promise.all against the new headless server endpoint), and a CSV bulk-import widget.
//   - runFullPipeline() extended to auto-propose candidates when Phase 7 detects a winner, and
//     -- a real pre-existing gap found while wiring this -- it had been fully built earlier this
//     session but never attached to any button; now wired as "▶ Run Full Pipeline (Phase 2 → 7)"
//     on Campaign Overview. Live-verified: correctly fails closed with a real conflict message
//     when re-run against an already-completed run, rather than corrupting anything.
// v1.9.0 · 2026-08-18 · Adds "Run all Phase N" to Phases 1-5: runAllInPanel() drives each
//   node-block's existing manual (.btn--secondary) submit button in DOM order, waiting for each
//   result box to settle before clicking the next, and stops with a status message naming the
//   node and error if one fails -- it does not duplicate or bypass any node's own validation.
//   Never clicks a .btn--live button, so live-fetch stays opt-in even when running a whole phase.
//   Auto-selects every option in an unselected <select multiple> first (Node 18's canonical-facts
//   picker), otherwise a "run all" would silently submit an empty list. Per direct user request
//   ("why am i having to click each button in each phase... can we have a run all phase 1").
// v1.8.0 · 2026-08-18 · Adds run resumption + a live Campaign Overview panel. loadRun()/
//   loadRunList() populate a header dropdown (#run-selector) of every existing run so state.runId
//   -- previously only ever set by createRun() and lost on page reload -- can be restored.
//   buildCampaignOverviewPanel()/renderCampaignOverviewBody() add a read-only dashboard (target
//   summary + a count per Node 03/05-10/11/15/16/18/19/20/21/26/27 artifact type) that
//   auto-refreshes from the same refreshRun() every other action already calls. Per direct user
//   request ("we need a view screen for actively running job/campaign").
// v1.7.0 · 2026-08-18 · Adds real forms for Node 19 (Quality & Compliance), Node 20 (Publishing
//   Scheduler), Node 21 (Search Distribution), Node 26 (Smart Destination Router), and Node 27
//   (Structured Lead Capture). Each selects its input from this run's own state (asset/package/
//   plan/search-package/route dropdowns, refreshed via refreshPhase5Selectors()) rather than
//   accepting typed JSON, since these nodes consume full upstream schema objects, not
//   hand-typeable facts -- same pattern Node 18 already used. Removed the now-dead
//   buildAcceptedUnwiredNodeBlock() helper (its one call site, Node 19, now has a real form).
//   Per direct user instruction ("proceed" after "why not [Phase 5-7 automated]").
// v1.6.0 · 2026-08-18 · Adds selectOrOther(): a select pre-populated with real previously-used
//   values from GET /api/known_values plus "+ Add new…" (swaps to a text input). Replaces the
//   free-text target_type/service/market/geography fields (Node 01), eligibility geography
//   (Node 03), problem/solution/commercial_model/customer_outcome (Node 02), and success_criteria
//   (Node 04) with it. features/benefits/differentiators/needs/pains stay free-text
//   comma-separated -- they're multi-value lists, not a single repeatable value, so a select
//   doesn't fit them the same way. Per direct user request ("the input not intuitive... suggest
//   selection list... apply same to rest of Phase 1").
// v1.5.0 · 2026-08-17 · Wires the new Nodes 05-10/15/18 automated live-fetch endpoints: a
//   "Live fetch"/"Live generate" button next to each existing manual submit button, posting to
//   the corresponding /live route, plus a live-fetch status banner at the top of Phase 2 reading
//   GET /api/live_fetch_status (whether EP050_LIVE_FETCH_ENABLED is set and which per-node
//   credentials are present, without exposing values). Manual entry remains available unchanged
//   for offline/fixture use; this only adds the automated path alongside it.
// v1.4.0 · 2026-08-17 · Deduplicated Node 05-10's shared fields (topic, geography, source type)
//   into one Common block at the top of Phase 2, entered once and reused by reference across all
//   six forms, instead of being repeated in each. Per direct user request.
// v1.3.0 · 2026-08-17 · URGENT ALLOCATION (board event 20260817T122525918_codex_phase2ops):
//   added real forms for Node 04 (conversion definition), and Node 05-10 (search demand
//   discovery, question discovery, social/video discovery, competitor intelligence, community
//   intelligence, trend detection) in a new dedicated Phase 2 panel, replacing the generic
//   status-only body the user's live review rejected. Each form posts to its real server.py
//   handler and renders the actual JSON result.
// v1.2.0 · 2026-08-17 · CHANGE REQUIRED fix (board event 20260817T113648989_codex_781e7f99):
//   render five distinct, honest node states (operable console control / accepted but unwired /
//   pending acceptance / deferred under the approved MVP classification / not started) instead
//   of a misleading operable-vs-locked binary. Phase 2 (Nodes 05-10) and Phase 1's Node 04 were
//   previously shown as "not implemented" when they are accepted at 100%.
// v1.1.0 · 2026-08-17 · Added Node 15 (campaign cluster generation) to Phase 3 and Node 16
//   (canonical fact registration) + Node 18 (video asset factory) to Phase 4. Node 12/13/14
//   run internally as part of the Node 15 action (no dedicated form); Node 17 runs internally
//   as part of the Node 18 action.
// v1.0.0 · 2026-08-17 · Initial seven-phase console client: run lifecycle, phase rail, node forms, lineage.

(function () {
  "use strict";

  const state = { runId: null, phases: [], run: null, knownValues: {} };
  let node18ClusterSelect = null;
  let node18FactSelect = null;
  let node18VideoAssetSelect = null;
  let node19AssetSelect = null;
  let node20PackageSelect = null;
  let node21PlanSelect = null;
  let node26SearchSelect = null;
  let node27RouteSelect = null;
  let node28LeadSelect = null;
  let node29AttributionSelect = null;
  let node30QualificationSelect = null;
  let node31RoutingSelect = null;
  let node33LeadSelect = null;
  let node34PerformanceSelect = null;
  let node35WinnerSelect = null;
  let node36AmplificationSelect = null;
  let node37AllocationSelect = null;

  const el = (tag, attrs, ...children) => {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([key, value]) => {
      if (key === "class") node.className = value;
      else if (key === "html") node.innerHTML = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value);
    });
    children.flat().forEach((child) => {
      if (child == null) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  };

  async function api(method, path, body) {
    const response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json();
    if (!response.ok) {
      const err = new Error(data.message || "Request failed");
      err.payload = data;
      throw err;
    }
    return data;
  }

  // --- run lifecycle -----------------------------------------------------

  async function createRun() {
    const run = await api("POST", "/api/runs");
    state.runId = run.run_id;
    state.run = run;
    renderRunIndicator();
    renderLineage();
    renderStage();
    renderCampaignOverviewBody();
    loadRunList();
  }

  async function loadRun(runId) {
    if (!runId) return;
    state.runId = runId;
    state.run = await api("GET", `/api/runs/${runId}`);
    renderRunIndicator();
    renderLineage();
    refreshNode18Selectors();
    refreshPhase5Selectors();
    refreshPhase6And7Selectors();
    renderCampaignOverviewBody();
    const selector = document.getElementById("run-selector");
    if (selector) selector.value = runId;
  }

  async function loadRunList() {
    const selector = document.getElementById("run-selector");
    if (!selector) return;
    let runs = [];
    try {
      const data = await api("GET", "/api/runs");
      runs = data.runs || [];
    } catch (err) {
      return;
    }
    const prev = state.runId || "";
    selector.innerHTML = "";
    selector.appendChild(el("option", { value: "" }, "Load existing run…"));
    [...runs].reverse().forEach((run) => {
      const target = run.target ? `${run.target.service} (${run.target.geography.locality})` : "no target yet";
      selector.appendChild(el("option", { value: run.run_id }, `${run.run_id} — ${target}`));
    });
    if (runs.some((r) => r.run_id === prev)) selector.value = prev;
  }

  async function refreshRun() {
    if (!state.runId) return;
    state.run = await api("GET", `/api/runs/${state.runId}`);
    renderLineage();
    refreshNode18Selectors();
    refreshPhase5Selectors();
    refreshPhase6And7Selectors();
    renderCampaignOverviewBody();
  }

  function _refreshSelect(select, items, valueKey, labelFn) {
    if (!select) return;
    const prev = select.value;
    select.innerHTML = "";
    items.forEach((item) => {
      select.appendChild(el("option", { value: item[valueKey] }, labelFn(item)));
    });
    if (items.some((item) => item[valueKey] === prev)) select.value = prev;
  }

  function refreshPhase5Selectors() {
    const run = state.run || {};
    _refreshSelect(node19AssetSelect, run.assets || [], "asset_id", (a) => `${a.asset_id} — ${a.title.slice(0, 50)}`);
    _refreshSelect(
      node20PackageSelect, run.approved_packages || [], "asset_id",
      (p) => `${p.asset_id} — ${p.headline.slice(0, 50)}`
    );
    _refreshSelect(
      node21PlanSelect, run.publication_plans || [], "publication_plan_id",
      (p) => `${p.publication_plan_id.slice(0, 24)}… (${p.channel}, asset ${p.asset_id})`
    );
    _refreshSelect(
      node26SearchSelect,
      (run.search_packages || []).map((s) => ({ ...s.manifest })),
      "search_distribution_id",
      (m) => `${m.search_distribution_id.slice(0, 24)}… (plan ${m.publication_plan_id.slice(0, 16)}…)`
    );
    _refreshSelect(
      node27RouteSelect, run.routes || [], "route_id",
      (r) => `${r.route_id.slice(0, 24)}… (${r.destination.cta_label})`
    );
  }

  function refreshPhase6And7Selectors() {
    const run = state.run || {};
    _refreshSelect(node28LeadSelect, run.leads || [], "lead_id", (l) => `${l.lead_id.slice(0, 20)}… (${l.source})`);
    _refreshSelect(
      node29AttributionSelect, run.attributions || [], "attribution_id",
      (a) => `${a.attribution_id.slice(0, 20)}… (lead ${a.lead_id.slice(0, 14)}…)`
    );
    _refreshSelect(
      node30QualificationSelect, run.qualifications || [], "qualification_id",
      (q) => `${q.qualification_id} (qualified=${q.is_qualified})`
    );
    _refreshSelect(
      node31RoutingSelect, run.routings || [], "routing_id",
      (r) => `${r.routing_id} → ${r.allocated_provider.name}`
    );
    _refreshSelect(node33LeadSelect, run.leads || [], "lead_id", (l) => `${l.lead_id.slice(0, 20)}… (${l.source})`);
    _refreshSelect(
      node34PerformanceSelect, run.performance_records || [], "performance_record_id",
      (p) => `${p.performance_record_id} (ROAS ${p.metrics.return_on_ad_spend})`
    );
    _refreshSelect(
      node35WinnerSelect, run.winners || [], "winner_id",
      (w) => `${w.winner_id} (is_winner=${w.is_winner})`
    );
    _refreshSelect(
      node36AmplificationSelect, run.amplifications || [], "amplification_id",
      (a) => `${a.amplification_id}`
    );
    _refreshSelect(
      node37AllocationSelect, run.allocations || [], "allocation_id",
      (a) => `${a.allocation_id}`
    );
  }

  function refreshNode18Selectors() {
    if (!node18ClusterSelect || !node18FactSelect) return;
    const clusters = (state.run && state.run.clusters) || [];
    const facts = (state.run && state.run.facts) || [];

    const prevCluster = node18ClusterSelect.value;
    node18ClusterSelect.innerHTML = "";
    clusters.forEach((c) => {
      node18ClusterSelect.appendChild(
        el("option", { value: c.cluster_id }, `${c.cluster_id} (${c.theme}, ${c.member_count} member${c.member_count === 1 ? "" : "s"})`)
      );
    });
    if (clusters.some((c) => c.cluster_id === prevCluster)) node18ClusterSelect.value = prevCluster;

    _refreshSelect(
      node18VideoAssetSelect, (state.run && state.run.video_assets) || [], "video_asset_id",
      (v) => `${v.video_asset_id.slice(0, 20)}… — ${(v.caption || "").slice(0, 40)}`
    );

    const prevSelected = new Set(Array.from(node18FactSelect.selectedOptions).map((o) => o.value));
    node18FactSelect.innerHTML = "";
    facts.forEach((f) => {
      const opt = el("option", { value: f.fact_id }, `${f.fact_id} — ${f.claim.slice(0, 60)}`);
      if (prevSelected.has(f.fact_id)) opt.selected = true;
      node18FactSelect.appendChild(opt);
    });
  }

  function renderRunIndicator() {
    const indicator = document.getElementById("run-indicator");
    if (state.runId) {
      indicator.textContent = `Run: ${state.runId}`;
      indicator.classList.remove("run-indicator--empty");
      indicator.classList.add("run-indicator--active");
    } else {
      indicator.textContent = "No active run";
      indicator.classList.add("run-indicator--empty");
      indicator.classList.remove("run-indicator--active");
    }
  }

  function renderLineage() {
    const list = document.getElementById("lineage-list");
    list.innerHTML = "";
    const entries = (state.run && state.run.lineage) || [];
    if (entries.length === 0) {
      list.appendChild(el("li", { class: "lineage-item" }, "No events yet."));
      return;
    }
    [...entries].reverse().forEach((entry) => {
      list.appendChild(
        el(
          "li",
          { class: "lineage-item" },
          el("time", {}, entry.at),
          el("strong", {}, `Phase ${entry.phase} · ${entry.node}`),
          entry.summary
        )
      );
    });
  }

  // --- phase rail + stage --------------------------------------------------

  async function loadPhases() {
    const data = await api("GET", "/api/phases");
    state.phases = data.phases;
  }

  function phaseState(phase) {
    if (phase.console_controls.length > 0) return "operable";
    if (phase.accepted_nodes.length > 0) return "accepted";
    if (phase.pending_acceptance_nodes.length > 0) return "pending";
    return "locked";
  }

  function railStateLabel(phase) {
    const parts = [];
    if (phase.console_controls.length) parts.push(`Operable: Node ${phase.console_controls.join(", ")}`);
    const acceptedUnwired = phase.accepted_nodes.filter((n) => !phase.console_controls.includes(n));
    if (acceptedUnwired.length) parts.push(`Accepted, not wired: Node ${acceptedUnwired.join(", ")}`);
    if (phase.pending_acceptance_nodes.length) parts.push(`Pending acceptance: Node ${phase.pending_acceptance_nodes.join(", ")}`);
    if (phase.mvp_deferred_nodes.length) parts.push(`Deferred (MVP): Node ${phase.mvp_deferred_nodes.join(", ")}`);
    if (phase.not_started_nodes.length) parts.push(`Not started: Node ${phase.not_started_nodes.join(", ")}`);
    return parts.length ? parts.join(" · ") : "Not started";
  }

  function renderRail() {
    const rail = document.getElementById("phase-rail");
    rail.innerHTML = "";
    state.phases.forEach((phase) => {
      const status = phaseState(phase);
      const btn = el(
        "button",
        {
          class: "rail-btn",
          "data-phase": phase.id,
          "data-state": status,
          onclick: () => selectPhase(phase.id),
        },
        el("span", { class: "rail-btn__tag" }, `PHASE ${phase.phase} · Nodes ${phase.nodes}`),
        el("span", { class: "rail-btn__title" }, phase.title),
        el("span", { class: "rail-btn__state" }, railStateLabel(phase))
      );
      rail.appendChild(btn);
    });
    rail.appendChild(
      el(
        "button",
        { class: "rail-btn rail-btn--secondary", "data-phase": "campaign-overview", onclick: () => selectPhase("campaign-overview") },
        el("span", { class: "rail-btn__tag" }, "SECONDARY"),
        el("span", { class: "rail-btn__title" }, "Campaign Overview")
      )
    );
    rail.appendChild(
      el(
        "button",
        { class: "rail-btn rail-btn--secondary", "data-phase": "campaign-queue", onclick: () => selectPhase("campaign-queue") },
        el("span", { class: "rail-btn__tag" }, "SECONDARY"),
        el("span", { class: "rail-btn__title" }, "Campaign Queue")
      )
    );
    rail.appendChild(
      el(
        "button",
        { class: "rail-btn rail-btn--secondary", "data-phase": "delivery-status", onclick: () => selectPhase("delivery-status") },
        el("span", { class: "rail-btn__tag" }, "SECONDARY"),
        el("span", { class: "rail-btn__title" }, "Delivery Status (historical)")
      )
    );
  }

  function selectPhase(phaseId) {
    document.querySelectorAll(".rail-btn").forEach((btn) => btn.classList.toggle("sel", btn.dataset.phase === phaseId));
    document.querySelectorAll(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === `panel-${phaseId}`));
  }

  function renderStage() {
    const stage = document.getElementById("stage");
    stage.innerHTML = "";
    state.phases.forEach((phase) => {
      stage.appendChild(buildPhasePanel(phase));
    });
    stage.appendChild(buildCampaignOverviewPanel());
    stage.appendChild(buildCampaignQueuePanel());
    stage.appendChild(buildDeliveryStatusPanel());
    selectPhase(state.phases[0].id);
  }

  function buildPhasePanel(phase) {
    const panel = el("section", { class: "panel", id: `panel-${phase.id}` }, el("h2", {}, `Phase ${phase.phase} — ${phase.title}`));
    if (phase.id === "ingestion") {
      panel.appendChild(el("p", { class: "panel-sub" }, "Operates Node 01 (target registration), Node 02 (product intelligence), Node 03 (audience definition), Node 04 (conversion definition)."));
      panel.appendChild(buildRunAllButton(phase.id, "Phase 1"));
      panel.appendChild(buildNode01Block());
      panel.appendChild(buildNode02Block());
      panel.appendChild(buildNode03Block());
      panel.appendChild(buildNode04Block());
    } else if (phase.id === "demand_intelligence") {
      panel.appendChild(el("p", { class: "panel-sub" }, "Operates Node 05 (search demand discovery), Node 06 (question discovery), Node 07 (social/video discovery), Node 08 (competitor intelligence), Node 09 (community intelligence), Node 10 (trend detection) -- each requires Node 01-04 from Phase 1 to already exist for this run. Topic and geography are entered once in the Common block and shared by all six. Manual entry has been removed for all six nodes: real campaigns must earn real data through each node's Live fetch button (a real automated fetch/aggregation against the real provider) -- see the status banner below for what's enabled."));
      panel.appendChild(buildLiveFetchStatusBanner());
      const demandCommon = buildDemandIntelligenceCommonBlock();
      panel.appendChild(demandCommon.el);
      panel.appendChild(buildNode05Block(demandCommon));
      panel.appendChild(buildNode06Block(demandCommon));
      panel.appendChild(buildNode07Block(demandCommon));
      panel.appendChild(buildNode08Block(demandCommon));
      panel.appendChild(buildNode09Block(demandCommon));
      panel.appendChild(buildNode10Block(demandCommon));
    } else if (phase.id === "strategy") {
      panel.appendChild(el("p", { class: "panel-sub" }, "Operates Node 11 (intent classification) against an offline demand-signal fixture, and Node 15 (campaign cluster generation). Node 12 (scoring), Node 13 (path discovery), and Node 14 (channel selection) run internally as part of the Node 15 action using each module's own deterministic defaults -- they have no dedicated form."));
      panel.appendChild(buildRunAllButton(phase.id, "Phase 3"));
      panel.appendChild(buildNode11Block());
      panel.appendChild(buildNode15Block());
    } else if (phase.id === "assets") {
      panel.appendChild(el("p", { class: "panel-sub" }, "Operates Node 16 (canonical fact registration), Node 18 (video asset factory), and Node 19 (Quality & Compliance). Node 17 (content/utility factory) runs internally as part of the Node 18 action."));
      panel.appendChild(buildRunAllButton(phase.id, "Phase 4"));
      panel.appendChild(buildNode16Block());
      panel.appendChild(buildNode18Block());
      panel.appendChild(buildNode19Block());
    } else if (phase.id === "distribution_conversion") {
      panel.appendChild(
        el(
          "p",
          { class: "panel-sub" },
          "Operates Node 20 (publishing scheduler), Node 21 (search distribution), Node 26 (smart destination router), and Node 27 (structured lead capture) -- each consumes the full structured output of the node before it, selected from this run's own state, not typed in by hand. Nodes 22-25 (video/social/community/syndication distribution) are shown below only as their deferred status -- they were explicitly deferred under the approved MVP classification, not built here."
        )
      );
      panel.appendChild(buildRunAllButton(phase.id, "Phase 5"));
      panel.appendChild(buildNode20Block());
      panel.appendChild(buildNode21Block());
      panel.appendChild(buildNode26Block());
      panel.appendChild(buildNode27Block());
      if (phase.mvp_deferred_nodes.length) {
        const wrap = el("div", { class: "locked-phase" });
        wrap.appendChild(el("p", { class: "locked-phase__lede" }, "Deferred under the approved MVP classification (not implemented, not claimed complete):"));
        const list = el("ul", { class: "locked-phase__nodes" });
        phase.mvp_deferred_nodes.forEach((n) => list.appendChild(el("li", {}, `Node ${n} — Deferred (MVP)`)));
        wrap.appendChild(list);
        panel.appendChild(wrap);
      }
    } else if (phase.id === "lead_lifecycle") {
      panel.appendChild(el("p", { class: "panel-sub" }, "Operates Node 28 (attribution), Node 29 (qualification), Node 30 (routing), Node 31 (lifecycle state machine) -- each consumes the real output of the node before it."));
      panel.appendChild(buildRunAllButton(phase.id, "Phase 6"));
      panel.appendChild(buildNode28Block());
      panel.appendChild(buildNode29Block());
      panel.appendChild(buildNode30Block());
      panel.appendChild(buildNode31Block());
    } else if (phase.id === "learning") {
      panel.appendChild(el("p", { class: "panel-sub" }, "Operates Node 32 (performance warehouse), Node 33 (outcome feedback), Node 34 (winner detection), Node 35 (amplification), Node 36 (effort allocation), Node 37 (knowledge base) -- the learning loop that turns a completed lead into a reusable pattern."));
      panel.appendChild(buildRunAllButton(phase.id, "Phase 7"));
      panel.appendChild(buildNode32Block());
      panel.appendChild(buildNode33Block());
      panel.appendChild(buildNode34Block());
      panel.appendChild(buildNode35Block());
      panel.appendChild(buildNode36Block());
      panel.appendChild(buildNode37Block());
    } else {
      panel.appendChild(el("p", { class: "panel-sub" }, "No node in this phase has a dedicated console control yet."));
      panel.appendChild(buildGenericPhaseBody(phase));
    }
    return panel;
  }

  function buildGenericPhaseBody(phase) {
    const wrap = el("div", { class: "locked-phase" });
    if (phase.accepted_nodes.length) {
      wrap.appendChild(el("p", { class: "locked-phase__lede" }, "Accepted EP050 implementation, not yet wired as a console control:"));
      const list = el("ul", { class: "locked-phase__nodes locked-phase__nodes--accepted" });
      phase.accepted_nodes.forEach((n) => list.appendChild(el("li", {}, `Node ${n} — Accepted (EP050 100%)`)));
      wrap.appendChild(list);
    }
    if (phase.pending_acceptance_nodes.length) {
      wrap.appendChild(el("p", { class: "locked-phase__lede" }, "Evidenced, pending explicit acceptance:"));
      const list = el("ul", { class: "locked-phase__nodes locked-phase__nodes--pending" });
      phase.pending_acceptance_nodes.forEach((n) => list.appendChild(el("li", {}, `Node ${n} — Pending acceptance`)));
      wrap.appendChild(list);
    }
    if (phase.mvp_deferred_nodes.length) {
      wrap.appendChild(el("p", { class: "locked-phase__lede" }, "Deferred under the approved MVP classification (not implemented, not claimed complete):"));
      const list = el("ul", { class: "locked-phase__nodes" });
      phase.mvp_deferred_nodes.forEach((n) => list.appendChild(el("li", {}, `Node ${n} — Deferred (MVP)`)));
      wrap.appendChild(list);
    }
    if (phase.not_started_nodes.length) {
      wrap.appendChild(el("p", { class: "locked-phase__lede" }, "Not started:"));
      const list = el("ul", { class: "locked-phase__nodes" });
      phase.not_started_nodes.forEach((n) => list.appendChild(el("li", {}, `Node ${n} — Not started`)));
      wrap.appendChild(list);
    }
    wrap.appendChild(
      el("button", { class: "btn btn--disabled", disabled: "disabled", title: "Locked: no console control implemented for this phase" }, "Execute Phase (Locked)")
    );
    return wrap;
  }

  function requireRun(runFn) {
    if (!state.runId) {
      alert("Start a New Run first.");
      return;
    }
    runFn();
  }

  // Drives the same manual submit buttons a human would click, in DOM order, one at a time --
  // it does not duplicate or bypass any node's own validation/handler logic. Only the manual
  // (.btn--secondary) button per node-block is clicked, never a .btn--live one, so live-fetch
  // stays opt-in even when running a whole phase at once. If a node-block has an unselected
  // <select multiple> (Node 18's canonical-facts picker), every option is selected first --
  // otherwise "run all" would silently submit an empty fact_ids list and fail.
  async function runAllInPanel(panelId, statusEl) {
    const panel = document.getElementById(panelId);
    const blocks = Array.from(panel.querySelectorAll(".node-block"));
    for (const block of blocks) {
      const btn = block.querySelector(".btn--secondary");
      if (!btn) continue; // e.g. the Phase 2 Common block has no submit button of its own
      const label = block.querySelector("h3")?.textContent || btn.textContent;
      block.querySelectorAll("select[multiple]").forEach((sel) => {
        if (!Array.from(sel.selectedOptions).length) {
          Array.from(sel.options).forEach((o) => (o.selected = true));
        }
      });
      if (statusEl) statusEl.textContent = `Running ${label}…`;
      const resultBox = block.querySelector(".result-box");
      const prevState = resultBox ? resultBox.className : null;
      btn.click();
      if (resultBox) {
        const deadline = Date.now() + 15000;
        while (resultBox.className === prevState && Date.now() < deadline) {
          await new Promise((r) => setTimeout(r, 100));
        }
        if (resultBox.classList.contains("result-box--err")) {
          if (statusEl) statusEl.textContent = `Stopped at ${label}: ${resultBox.textContent.trim().slice(0, 200)}`;
          return false;
        }
      }
    }
    if (statusEl) statusEl.textContent = "All steps in this phase completed.";
    return true;
  }

  function buildRunAllButton(phaseId, phaseTitle) {
    const status = el("span", { class: "field-hint" }, "");
    const btn = el("button", { class: "btn btn--primary", type: "button" }, `▶ Run all ${phaseTitle}`);
    btn.addEventListener("click", () =>
      requireRun(async () => {
        btn.disabled = true;
        status.textContent = "Starting…";
        try {
          await runAllInPanel(`panel-${phaseId}`, status);
        } finally {
          btn.disabled = false;
        }
      })
    );
    return el("div", { class: "btn-row" }, btn, status);
  }

  function buildResultBox() {
    return el("pre", { class: "result-box result-box--empty" });
  }

  function showResult(box, ok, data) {
    box.classList.remove("result-box--empty", "result-box--ok", "result-box--err");
    box.classList.add(ok ? "result-box--ok" : "result-box--err");
    box.textContent = JSON.stringify(data, null, 2);
  }

  function field(label, hint, inputEl) {
    return el("label", {}, `${label}`, hint ? el("span", { class: "field-hint" }, hint) : null, inputEl);
  }

  function knownList(key) {
    return (state.knownValues && state.knownValues[key]) || [];
  }

  const SELECT_OR_OTHER_VALUE = "__add_new__";

  // A <select> pre-populated with real previously-used values (server GET /api/known_values)
  // plus "+ Add new…", which swaps in a plain text input. Exposes a `.value` getter so callers
  // read it exactly like a normal <input>/<select> — no call site needs to know which mode it's in.
  function selectOrOther(options, initial) {
    const select = el("select", {});
    const otherInput = el("input", { type: "text" });
    otherInput.style.display = "none";

    const merged = [];
    const seen = new Set();
    [initial, ...(options || [])].forEach((value) => {
      if (value && !seen.has(value)) {
        seen.add(value);
        merged.push(value);
      }
    });
    merged.forEach((value) =>
      select.appendChild(el("option", { value, ...(value === initial ? { selected: "selected" } : {}) }, value))
    );
    select.appendChild(el("option", { value: SELECT_OR_OTHER_VALUE }, "+ Add new…"));
    if (!merged.length) select.value = SELECT_OR_OTHER_VALUE;

    function sync() {
      const isOther = select.value === SELECT_OR_OTHER_VALUE;
      otherInput.style.display = isOther ? "" : "none";
      if (isOther) otherInput.focus();
    }
    select.addEventListener("change", sync);
    sync();

    return {
      el: el("div", { class: "select-or-other" }, select, otherInput),
      get value() {
        return select.value === SELECT_OR_OTHER_VALUE ? otherInput.value.trim() : select.value;
      },
    };
  }

  function buildNode01Block() {
    const service = selectOrOther(knownList("service"), "boiler_repair");
    const market = selectOrOther(knownList("market"), "domestic_plumbing");
    const targetType = selectOrOther(knownList("target_type"), "service_market");
    const geo = geoInputs();
    const appId = el("input", { type: "text", value: "ep047_trades_directory" });
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Register Target");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node01`, {
            target_type: targetType.value,
            service: service.value,
            market: market.value,
            geography: geoPayload(geo),
            app_id: appId.value || null,
            status: "active",
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 01"),
      el("h3", {}, "App / Service Registration"),
      el("div", { class: "field-grid" },
        field("Target type", null, targetType.el),
        field("Service", null, service.el),
        field("Market", null, market.el),
        ...geoFields(geo),
        field("App ID (optional)", "Prospective consumer only, not the architectural boundary", appId)
      ),
      submit,
      result
    );
  }

  function buildNode02Block() {
    const problem = selectOrOther(knownList("problem"), "Homeowners lose boiler pressure and hot water with no clear diagnosis path.");
    const solution = selectOrOther(knownList("solution"), "A vetted local boiler-repair callout that diagnoses and restores pressure same-day.");
    const features = el("input", { type: "text", value: "Same-day callout, Fixed diagnostic fee, Vetted local engineers" });
    const benefits = el("input", { type: "text", value: "Hot water restored quickly, No guesswork on cause, Transparent pricing" });
    const differentiators = el("input", { type: "text", value: "Local Blackheath coverage, Vetted-only engineer network" });
    const commercialModel = selectOrOther(knownList("commercial_model"), "Fixed diagnostic fee plus quoted repair cost.");
    const customerOutcome = selectOrOther(knownList("customer_outcome"), "Working boiler and restored hot water within 24 hours.");
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Register Product Intelligence");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node02`, {
            problem: problem.value,
            solution: solution.value,
            features: features.value.split(",").map((s) => s.trim()).filter(Boolean),
            benefits: benefits.value.split(",").map((s) => s.trim()).filter(Boolean),
            differentiators: differentiators.value.split(",").map((s) => s.trim()).filter(Boolean),
            commercial_model: commercialModel.value,
            customer_outcome: customerOutcome.value,
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 02"),
      el("h3", {}, "Product Intelligence"),
      el("div", { class: "field-grid" },
        field("Problem", "pick a prior problem statement or add a new one", problem.el),
        field("Solution", "pick a prior solution statement or add a new one", solution.el),
        field("Features", "comma-separated", features),
        field("Benefits", "comma-separated", benefits),
        field("Differentiators", "comma-separated", differentiators),
        field("Commercial model", null, commercialModel.el),
        field("Customer outcome", null, customerOutcome.el)
      ),
      submit,
      result
    );
  }

  function buildNode03Block() {
    const segmentName = selectOrOther(knownList("segment_name"), "Blackheath homeowner, boiler pressure loss");
    const needs = el("input", { type: "text", value: "Restore hot water quickly, Understand the cause of pressure loss" });
    const pains = el("input", { type: "text", value: "No heating or hot water, Uncertainty over callout cost" });
    const urgency = el("select", {}, ["low", "medium", "high", "emergency"].map((v) => el("option", { value: v, ...(v === "high" ? { selected: "selected" } : {}) }, v)));
    const geo = geoInputs();
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Register Audience Segment");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node03`, {
            segment_name: segmentName.value,
            needs: needs.value.split(",").map((s) => s.trim()).filter(Boolean),
            pains: pains.value.split(",").map((s) => s.trim()).filter(Boolean),
            urgency: urgency.value,
            eligibility_geography: geoPayload(geo),
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 03"),
      el("h3", {}, "Audience Definition"),
      el("div", { class: "field-grid" },
        field("Segment name", "pick a prior segment or add a new one", segmentName.el),
        field("Needs", "comma-separated", needs),
        field("Pains", "comma-separated", pains),
        field("Urgency", null, urgency),
        ...geoFields(geo)
      ),
      submit,
      result
    );
  }

  // --- shared helpers for the Node 04-10 forms (Phase 1/2) ------------------

  function geoInputs(defaults) {
    defaults = defaults || {};
    return {
      locality: selectOrOther(knownList("locality"), defaults.locality || "Blackheath"),
      region: selectOrOther(knownList("region"), defaults.region || "London"),
      country: selectOrOther(knownList("country"), defaults.country || "UK"),
    };
  }

  function geoFields(geo) {
    return [
      field("Geography locality", null, geo.locality.el),
      field("Geography region", null, geo.region.el),
      field("Geography country", null, geo.country.el),
    ];
  }

  function geoPayload(geo) {
    return { locality: geo.locality.value, region: geo.region.value, country: geo.country.value };
  }

  // Builds a "Live fetch"/"Live generate" button that posts bodyFn()'s result to path and
  // renders into result, exactly like the manual submit buttons but hitting the /live route.
  function liveButton(label, path, bodyFn, result) {
    const btn = el("button", { class: "btn btn--live", type: "button" }, label);
    btn.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", path(), bodyFn());
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );
    return btn;
  }

  async function fetchLiveFetchStatus() {
    const response = await fetch("/api/live_fetch_status");
    return response.json();
  }

  function buildLiveFetchStatusBanner() {
    const banner = el("div", { class: "live-status" }, "Checking live-fetch status…");
    fetchLiveFetchStatus()
      .then((status) => {
        banner.innerHTML = "";
        banner.classList.toggle("live-status--enabled", status.live_fetch_enabled);
        banner.appendChild(
          el(
            "span",
            {},
            status.live_fetch_enabled
              ? "Live fetch: ENABLED (EP050_LIVE_FETCH_ENABLED=1)."
              : "Live fetch: DISABLED by default. Set "
          )
        );
        if (!status.live_fetch_enabled) banner.appendChild(el("code", {}, "EP050_LIVE_FETCH_ENABLED=1"));
        const nodeNotes = Object.entries(status.nodes || {})
          .map(([nodeId, info]) => {
            if (info.ready) return `Node ${nodeId} ready`;
            if (info.required_vars.length) return `Node ${nodeId} needs ${info.required_vars.join(", ")}`;
            return `Node ${nodeId} needs the flag only`;
          })
          .join(" · ");
        banner.appendChild(el("span", {}, ` — ${nodeNotes}`));
      })
      .catch(() => {
        banner.textContent = "Live-fetch status unavailable.";
      });
    return banner;
  }

  // Topic and geography appear in every Node 05-10 live-fetch call. Entered once here and reused
  // by reference across all six, instead of repeating the same fields six times. Manual entry
  // (and its source_type field) was removed for Nodes 05-10 specifically: it produces a record
  // that is structurally identical to real fetched demand but isn't -- unlike a live-fetch call,
  // which either gets a real result from the real provider or fails, a manually-typed value can
  // never be verified as genuine research versus something typed in to unblock a run. Fine for
  // building test fixtures (still done directly via the API in test_console_server.py), unworkable
  // for real campaign data -- per direct user instruction ("the manual version is unworkable...
  // good for testing... but not for real use... we wont use them for real analysis").
  function buildDemandIntelligenceCommonBlock() {
    const topic = el("input", { type: "text", value: "boiler_pressure_loss" });
    const geo = geoInputs();

    const blockEl = el(
      "div",
      { class: "node-block node-block--common" },
      el("span", { class: "node-tag" }, "COMMON"),
      el("h3", {}, "Shared Fields (Nodes 05-10)"),
      el(
        "p",
        {},
        "Topic and geography are the same across every Node 05-10 live-fetch call for this run. Set them once here; each live-fetch button below only asks for what's unique to it. Manual entry has been removed for Nodes 05-10 -- real campaigns must earn real data through live-fetch, never typed in by hand."
      ),
      el("div", { class: "field-grid" },
        field("Topic", null, topic),
        ...geoFields(geo)
      )
    );

    return { el: blockEl, topic, geo };
  }

  function buildNode04Block() {
    const successCriteria = selectOrOther(knownList("success_criteria"), "A lead reaches the sale stage with a recorded outcome.");
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Define Conversion Funnel");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node04`, {
            success_criteria: successCriteria.value || null,
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 04"),
      el("h3", {}, "Conversion Definition"),
      el(
        "p",
        {},
        "Applies the master spec's canonical 9-stage funnel (visit → … → revenue) to this run's target. Only the success criteria is operator-editable."
      ),
      el("div", { class: "field-grid" }, field("Success criteria", "pick a prior criteria or add a new one", successCriteria.el)),
      submit,
      result
    );
  }

  function buildNode05Block(common) {
    const serviceName = el("input", { type: "text", value: "boiler_repair" });
    const marketSegment = el("input", { type: "text", value: "domestic_plumbing" });
    const result = buildResultBox();

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 05"),
      el("h3", {}, "Search Demand Discovery"),
      el("p", {}, "Real demand data only -- manual entry removed. Live fetch calls the real Google Custom Search API; it either returns a real result or fails, never a typed-in guess."),
      el("div", { class: "field-grid" },
        field("Service name", null, serviceName),
        field("Market segment", null, marketSegment)
      ),
      el(
        "div", { class: "btn-row" },
        liveButton(
          "Live fetch (Google Custom Search)",
          () => `/api/runs/${state.runId}/node05/live`,
          () => ({
            topic: common.topic.value, geography: geoPayload(common.geo),
            service_context: { service_name: serviceName.value, market_segment: marketSegment.value },
          }),
          result
        )
      ),
      result
    );
  }

  function buildNode06Block(common) {
    const result = buildResultBox();

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 06"),
      el("h3", {}, "Question Discovery"),
      el("p", {}, "Real demand data only -- manual entry removed. Live fetch calls the real Stack Exchange API using the shared topic/geography above."),
      el(
        "div", { class: "btn-row" },
        liveButton(
          "Live fetch (Stack Exchange)",
          () => `/api/runs/${state.runId}/node06/live`,
          () => ({ topic: common.topic.value, geography: geoPayload(common.geo) }),
          result
        )
      ),
      result
    );
  }

  function buildNode07Block(common) {
    const result = buildResultBox();

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 07"),
      el("h3", {}, "Social/Video Discovery"),
      el("p", {}, "Real demand data only -- manual entry removed. Live fetch calls the real YouTube Data API using the shared topic/geography above."),
      el(
        "div", { class: "btn-row" },
        liveButton(
          "Live fetch (YouTube Data API)",
          () => `/api/runs/${state.runId}/node07/live`,
          () => ({ topic: common.topic.value, geography: geoPayload(common.geo) }),
          result
        )
      ),
      result
    );
  }

  function buildNode08Block(common) {
    const competitorUrl = el("input", { type: "text", value: "https://example.test/boiler-repair" });
    const channel = el("input", { type: "text", value: "google_search" });
    const query = el("input", { type: "text", value: "boiler pressure loss repair blackheath" });
    const result = buildResultBox();

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 08"),
      el("h3", {}, "Competitor Intelligence"),
      el("p", {}, "Real data only -- manual entry removed. Live fetch does a real page GET against the URL below (no credential needed) and derives the competitor name from the real page title."),
      el("div", { class: "field-grid" },
        field("Competitor URL", null, competitorUrl),
        field("Channel", null, channel),
        field("Query", null, query)
      ),
      el(
        "div", { class: "btn-row" },
        liveButton(
          "Live fetch (real page GET, no credential needed)",
          () => `/api/runs/${state.runId}/node08/live`,
          () => ({
            competitor_url: competitorUrl.value, topic: common.topic.value, query: query.value,
            geography: geoPayload(common.geo), channel: channel.value,
          }),
          result
        )
      ),
      result
    );
  }

  function buildNode09Block(common) {
    const subreddit = el("input", { type: "text", value: "DIYUK" });
    const result = buildResultBox();

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 09"),
      el("h3", {}, "Community Intelligence"),
      el("p", {}, "Real data only -- manual entry removed. Live fetch calls the real Reddit OAuth read-only API for the subreddit below."),
      el("div", { class: "field-grid" },
        field("Subreddit", "no leading r/", subreddit)
      ),
      el(
        "div", { class: "btn-row" },
        liveButton(
          "Live fetch (Reddit OAuth, read-only)",
          () => `/api/runs/${state.runId}/node09/live`,
          () => ({ topic: common.topic.value, subreddit: subreddit.value, geography: geoPayload(common.geo) }),
          result
        )
      ),
      result
    );
  }

  function buildNode10Block(common) {
    const baselineStart = el("input", { type: "text", value: "2026-08-01T00:00:00+00:00" });
    const baselineEnd = el("input", { type: "text", value: "2026-08-08T00:00:00+00:00" });
    const currentStart = el("input", { type: "text", value: "2026-08-08T00:00:00+00:00" });
    const currentEnd = el("input", { type: "text", value: "2026-08-15T00:00:00+00:00" });
    const metricName = el("input", { type: "text", value: "demand_signal_count" });
    const result = buildResultBox();

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 10"),
      el("h3", {}, "Trend Detection"),
      el(
        "p",
        {},
        "Real data only -- manual entry removed. Live aggregate computes velocity/direction/spike_flag/confidence from this run's own real Node 05-09 counts across the two windows below -- no fetch of its own needed."
      ),
      el("div", { class: "field-grid" },
        field("Baseline window start", "ISO 8601", baselineStart),
        field("Baseline window end", "ISO 8601", baselineEnd),
        field("Current window start", "ISO 8601", currentStart),
        field("Current window end", "ISO 8601", currentEnd),
        field("Metric name", null, metricName)
      ),
      el(
        "div", { class: "btn-row" },
        liveButton(
          "Live aggregate (real Node05-09 counts, no fetch needed)",
          () => `/api/runs/${state.runId}/node10/live`,
          () => ({
            topic: common.topic.value, geography: geoPayload(common.geo),
            window: {
              baseline_start: baselineStart.value, baseline_end: baselineEnd.value,
              current_start: currentStart.value, current_end: currentEnd.value,
            },
            metric_name: metricName.value,
          }),
          result
        )
      ),
      result
    );
  }

  function buildNode11Block() {
    const signalId = el("input", { type: "text", value: "sig_console_demo_01" });
    const rawQuery = el("textarea", {}, "boiler pressure dropped to zero no hot water how to fix");
    const topic = el("input", { type: "text", value: "boiler_pressure_loss" });
    const sourceType = el("select", {}, ["manual_curation", "synthetic_fixture"].map((v) => el("option", { value: v }, v)));
    const observedAt = el("input", { type: "text", value: new Date().toISOString() });
    const locality = el("input", { type: "text", value: "Blackheath" });
    const region = el("input", { type: "text", value: "London" });
    const country = el("input", { type: "text", value: "UK" });
    const serviceName = el("input", { type: "text", value: "boiler_repair" });
    const marketSegment = el("input", { type: "text", value: "domestic_plumbing" });
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Classify Signal");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node11/classify`, {
            signal_id: signalId.value,
            raw_query: rawQuery.value,
            topic: topic.value,
            source_type: sourceType.value,
            observed_at: observedAt.value,
            geography: { locality: locality.value, region: region.value, country: country.value },
            service_context: { service_name: serviceName.value, market_segment: marketSegment.value },
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 11"),
      el("h3", {}, "Intent Classification"),
      el("div", { class: "field-grid" },
        field("Signal ID", null, signalId),
        field("Raw query", null, rawQuery),
        field("Topic", null, topic),
        field("Source type", "MVP-pinned offline values only", sourceType),
        field("Observed at", "ISO 8601", observedAt),
        field("Geography locality", null, locality),
        field("Geography region", null, region),
        field("Geography country", null, country),
        field("Service name", null, serviceName),
        field("Market segment", null, marketSegment)
      ),
      submit,
      result
    );
  }

  function buildNode15Block() {
    const campaignContext = el("input", { type: "text", value: "" });
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Generate Campaign Cluster(s)");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node15/generate`, {
            campaign_context: campaignContext.value || null,
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 15"),
      el("h3", {}, "Campaign / Cluster Generation"),
      el(
        "p",
        {},
        "Runs the real Node 12 (scoring) → Node 13 (path discovery) → Node 14 (channel selection) chain over every classified signal in this run, then groups them into campaign clusters (Node 15) by shared intent, geography, and channel."
      ),
      el("div", { class: "field-grid" }, field("Campaign context (optional)", "Screened for prohibited PII", campaignContext)),
      el(
        "div", { class: "btn-row" },
        submit,
        liveButton(
          "Live generate (real Node05 signals → real Node11-14 chain, no manual classify step)",
          () => `/api/runs/${state.runId}/node15/live`,
          () => ({ campaign_context: campaignContext.value || null }),
          result
        )
      ),
      result
    );
  }

  function buildNode16Block() {
    const topic = el("input", { type: "text", value: "boiler_pressure" });
    const claim = el("textarea", {}, "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.");
    const verificationSource = el("input", { type: "text", value: "manufacturer_manual_fixture" });
    const isSafetyCritical = el("input", { type: "checkbox" });
    const safetyGuidance = el("textarea", {}, "Do not attempt gas work without Gas Safe registration.");
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Register Canonical Fact");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node16/fact`, {
            topic: topic.value,
            claim: claim.value,
            verification_source: verificationSource.value,
            is_safety_critical: isSafetyCritical.checked,
            safety_guidance: isSafetyCritical.checked ? safetyGuidance.value || null : null,
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 16"),
      el("h3", {}, "Canonical Knowledge Store"),
      el(
        "div",
        { class: "field-grid" },
        field("Topic", null, topic),
        field("Claim", null, claim),
        field("Verification source", null, verificationSource),
        field("Safety-critical?", null, isSafetyCritical),
        field("Safety guidance", "Required when safety-critical", safetyGuidance)
      ),
      submit,
      result
    );
  }

  function buildNode18Block() {
    const clusterSelect = el("select", {});
    const factSelect = el("select", { multiple: "multiple", size: "4" });
    const liveSignalId = el("input", { type: "text", value: "" });
    const allServicesCheckbox = el("input", { type: "checkbox" });
    node18ClusterSelect = clusterSelect;
    node18FactSelect = factSelect;
    refreshNode18Selectors();
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Generate Video Asset (always video)");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        const factIds = Array.from(factSelect.selectedOptions).map((o) => o.value);
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node18/generate`, {
            cluster_id: clusterSelect.value,
            fact_ids: factIds,
            service_scope: allServicesCheckbox.checked ? "all" : undefined,
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    const formatAwareResult = buildResultBox();
    const formatAwareSubmit = el("button", { class: "btn btn--secondary", type: "button" }, "Generate (format-aware -- respects Node 14's real recommendation)");
    formatAwareSubmit.addEventListener("click", () =>
      requireRun(async () => {
        const factIds = Array.from(factSelect.selectedOptions).map((o) => o.value);
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node18/generate_by_format`, {
            cluster_id: clusterSelect.value,
            fact_ids: factIds,
          });
          showResult(formatAwareResult, true, record);
          await refreshRun();
        } catch (err) {
          showResult(formatAwareResult, false, err.payload || { message: err.message });
        }
      })
    );

    // --- Real EP048 render + real YouTube publish trigger (2026-08-20) -----------------------
    const publishVideoAssetSelect = el("select", {});
    node18VideoAssetSelect = publishVideoAssetSelect;
    const applicabilityProductCategory = el("input", { type: "text", placeholder: "auto (derived from service)" });
    const applicabilityServiceScope = el("input", { type: "text", placeholder: '"all", or comma-separated service names' });
    const applicabilityLocalityScope = el("input", { type: "text", placeholder: '"all", or comma-separated localities' });
    const confirmPublishCheckbox = el("input", { type: "checkbox" });
    const publishResult = buildResultBox();

    const publishSubmit = el("button", { class: "btn btn--secondary", type: "button" }, "Trigger Real Render + Real YouTube Upload");
    publishSubmit.addEventListener("click", () =>
      requireRun(async () => {
        if (!publishVideoAssetSelect.value) {
          showResult(publishResult, false, { message: "Generate a video asset above first" });
          return;
        }
        const parseScope = (input) => {
          const raw = input.value.trim();
          if (!raw) return null;
          if (raw.toLowerCase() === "all") return "all";
          return raw.split(",").map((s) => s.trim()).filter(Boolean);
        };
        const serviceScope = parseScope(applicabilityServiceScope);
        const localityScope = parseScope(applicabilityLocalityScope);
        // Both scope axes are required together if either is set -- a partial applicability tag
        // (e.g. only product_category) would leave the other axis undefined, which the server's
        // matcher treats as "never matches", silently breaking future reuse on that axis. Leave
        // both blank to fall back to the server's own safe default (narrow: this exact service +
        // this exact locality only).
        let applicability;
        if (serviceScope !== null && localityScope !== null) {
          applicability = {
            product_category: applicabilityProductCategory.value.trim() || undefined,
            service_scope: serviceScope,
            locality_scope: localityScope,
          };
        } else if (serviceScope !== null || localityScope !== null) {
          showResult(publishResult, false, {
            message: "Fill in both \"service scope\" and \"locality scope\" together, or leave both blank for the safe per-campaign default.",
          });
          return;
        }
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node18/trigger_render_and_publish`, {
            video_asset_id: publishVideoAssetSelect.value,
            confirm_publish: confirmPublishCheckbox.checked,
            applicability,
          });
          showResult(publishResult, true, record);
          await refreshRun();
        } catch (err) {
          showResult(publishResult, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 18"),
      el("h3", {}, "Video Asset Factory"),
      el(
        "p",
        {},
        "Runs the real Node 17 (content/utility factory) internally to build the underlying asset, then Node 18 to produce a script/storyboard/shot-list/caption/branding/CTA/render-manifest package. This step alone never renders or uploads anything; external_action is always false here."
      ),
      el(
        "div",
        { class: "field-grid" },
        field("Campaign cluster", "Generate one first via Node 15", clusterSelect),
        field("Canonical facts", "Manual entry only; Live generate re-derives these from Node16, ctrl/cmd-click to multi-select", factSelect),
        field("Signal ID (Live generate only)", "The Node 05 signal this video is for -- re-derives classification/selection itself", liveSignalId),
        field("Applies to all services in this category?", "e.g. covers boiler repair + service + emergencies as one video, not just this campaign's single service. Video copy never names a town/city either way.", allServicesCheckbox)
      ),
      el(
        "div", { class: "btn-row" },
        submit,
        liveButton(
          "Live generate (re-derives the Node11-14 chain + real Node16 facts)",
          () => `/api/runs/${state.runId}/node18/live`,
          () => ({ cluster_id: clusterSelect.value, signal_id: liveSignalId.value }),
          result
        )
      ),
      result,
      el("h4", { style: "margin:14px 0 4px" }, "Format-aware generation (Node 18 sibling)"),
      el("p", { class: "field-hint" }, "Real gap found and closed 2026-08-18: the buttons above always force a video regardless of what Node 14 actually recommended. This one reads the SAME real Node 17 asset's own recommended format and routes to the matching real asset type instead -- a verified local listing, a step-by-step guide, a callout ad, or a community post (which comes back flagged requires_human_review) -- using the same cluster/facts selected above."),
      el("div", { class: "btn-row" }, formatAwareSubmit),
      formatAwareResult,
      el("h4", { style: "margin:14px 0 4px" }, "Real render + real YouTube publish (2026-08-20)"),
      el(
        "p",
        { class: "field-hint" },
        "Genuine external action: calls EP048's real generate_video.py (ElevenLabs + Pexels) then real upload_video.py (YouTube, Unlisted). Checks every other run first for an already-published video whose applicability tag already covers this campaign -- if found, reuses it (no new render, no new upload, no cost) instead. Requires the confirm checkbox on every call; nothing is inferred or remembered."
      ),
      el(
        "div",
        { class: "field-grid" },
        field("Video asset to publish", "Generate one above first", publishVideoAssetSelect),
        field("Applicability -- product category", "Leave blank to auto-derive from the service (e.g. \"boiler_repair\" -> \"boiler\")", applicabilityProductCategory),
        field("Applicability -- service scope", 'e.g. "all", or "boiler_repair, boiler_service"', applicabilityServiceScope),
        field("Applicability -- locality scope", 'e.g. "all", or "Greenwich, Lewisham, Charlton" (south London, etc.)', applicabilityLocalityScope),
        field("Confirm: trigger a real render + real public upload", "Required -- unchecked blocks the call", confirmPublishCheckbox)
      ),
      el("div", { class: "btn-row" }, publishSubmit),
      publishResult
    );
  }

  function buildNode19Block() {
    const assetSelect = el("select", {});
    node19AssetSelect = assetSelect;
    refreshPhase5Selectors();
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Evaluate Compliance");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node19/generate`, { asset_id: assetSelect.value });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 19"),
      el("h3", {}, "Quality & Compliance"),
      el(
        "p",
        {},
        "Runs the real Node 19 stop-gate against a Node 18-generated asset: lineage/field presence, safety-disclaimer wording, and fact verification against the Node 16 knowledge store. Rejects (422) with the specific reasons if any check fails -- it never silently approves."
      ),
      el("div", { class: "field-grid" }, field("Asset", "Generate one first via Node 18", assetSelect)),
      submit,
      result
    );
  }

  function buildNode20Block() {
    const packageSelect = el("select", {});
    node20PackageSelect = packageSelect;
    refreshPhase5Selectors();
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Build Publication Plan");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node20/generate`, { asset_id: packageSelect.value });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 20"),
      el("h3", {}, "Publishing Scheduler"),
      el("p", {}, "Projects a Node 19-approved asset package into a schema-valid, non-executing mock publication plan. external_action is always false -- nothing is ever actually scheduled or dispatched anywhere."),
      el("div", { class: "field-grid" }, field("Approved package", "Approve one first via Node 19", packageSelect)),
      submit,
      result
    );
  }

  function buildNode21Block() {
    const planSelect = el("select", {});
    node21PlanSelect = planSelect;
    refreshPhase5Selectors();
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Build Search Distribution Package");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node21/generate`, { publication_plan_id: planSelect.value });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 21"),
      el("h3", {}, "Search Distribution"),
      el("p", {}, "Builds the local article/landing-page/FAQ/structured-data/sitemap artifact set for a search_landing publication plan. Purely local file content generation -- no site is ever actually published to."),
      el("div", { class: "field-grid" }, field("Publication plan", "Build one first via Node 20 (channel must be search_landing)", planSelect)),
      submit,
      result
    );
  }

  function buildNode26Block() {
    const searchSelect = el("select", {});
    node26SearchSelect = searchSelect;
    refreshPhase5Selectors();
    const topic = el("input", { type: "text", value: "safe boiler pressure guide" });
    const intent = el("input", { type: "text", value: "diagnostic_quote" });
    const geography = el("input", { type: "text", value: "blackheath" });
    const service = el("input", { type: "text", value: "boiler_repair" });
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Build Route Recommendation");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node26/generate`, {
            search_distribution_id: searchSelect.value,
            topic: topic.value, intent: intent.value, geography: geography.value, service: service.value,
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block" },
      el("span", { class: "node-tag" }, "NODE 26"),
      el("h3", {}, "Smart Destination Router"),
      el(
        "p",
        {},
        "Matches a routing context against the router's one approved fixture rule (the values below are the only combination that currently matches -- changing them will correctly fail with “no approved routing rule matches”). Channel and lineage IDs are taken from the selected search package automatically, not typed here."
      ),
      el(
        "div", { class: "field-grid" },
        field("Search package", "Build one first via Node 21", searchSelect),
        field("Topic", null, topic),
        field("Intent", null, intent),
        field("Geography", null, geography),
        field("Service", null, service)
      ),
      submit,
      result
    );
  }

  function buildNode27Block() {
    const routeSelect = el("select", {});
    node27RouteSelect = routeSelect;
    refreshPhase5Selectors();
    const sessionId = el("input", { type: "text", value: "sess_demo_01" });
    const consentGranted = el("input", { type: "checkbox", checked: "checked" });
    const consentVersion = el("input", { type: "text", value: "v1" });
    const consentBasis = el("input", { type: "text", value: "explicit_opt_in" });
    const result = buildResultBox();

    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Capture Structured Lead");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node27/generate`, {
            route_id: routeSelect.value,
            session_id: sessionId.value,
            consent_granted: consentGranted.checked,
            consent_version: consentVersion.value,
            consent_basis: consentBasis.value,
          });
          showResult(result, true, record);
          await refreshRun();
        } catch (err) {
          showResult(result, false, err.payload || { message: err.message });
        }
      })
    );

    return el(
      "div",
      { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 27"),
      el("h3", {}, "Structured Lead Capture"),
      el(
        "p",
        {},
        "Pending acceptance, not yet formally accepted EP050 implementation -- this form is real and works, but the underlying node hasn't cleared the board's acceptance gate. Builds a deterministic, PII-free lead record (session_id/source/consent only) from a Node 26 route. Rejects anything containing PII. This is the artifact the whole pipeline exists to produce -- and, like every other node here, it captures a local fixture record only. No real consumer, no real contact, no real submission."
      ),
      el(
        "div", { class: "field-grid" },
        field("Route", "Build one first via Node 26", routeSelect),
        field("Session ID", null, sessionId),
        field("Consent granted", "Simulates a real consumer's consent checkbox", consentGranted),
        field("Consent version", null, consentVersion),
        field("Consent basis", null, consentBasis)
      ),
      submit,
      result
    );
  }

  function buildNode28Block() {
    const leadSelect = el("select", {});
    node28LeadSelect = leadSelect;
    refreshPhase6And7Selectors();
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Build Attribution Record");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node28/generate`, { lead_id: leadSelect.value });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 28"), el("h3", {}, "Offline Attribution"),
      el("p", {}, "Pending acceptance -- real, working form. Attributes a captured lead to its real acquisition lineage (route/plan/search-package/asset/target/opportunity) using the one allowlisted attribution model."),
      el("div", { class: "field-grid" }, field("Lead", "Capture one first via Node 27", leadSelect.el || leadSelect)),
      submit, result);
  }

  function buildNode29Block() {
    const attrSelect = el("select", {});
    node29AttributionSelect = attrSelect;
    refreshPhase6And7Selectors();
    const urgency = el("select", {}, ["low", "medium", "high", "emergency"].map((v) => el("option", { value: v, ...(v === "high" ? { selected: "selected" } : {}) }, v)));
    const value = el("input", { type: "text", value: "180" });
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Evaluate Lead Qualification");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node29/generate`, {
            attribution_id: attrSelect.value, urgency_level: urgency.value, estimated_value_gbp: Number(value.value) || 180,
          });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 29"), el("h3", {}, "Lead Qualification"),
      el("p", {}, "Pending acceptance -- real, working form. Scores service match, geo eligibility, urgency, and duplicate risk into a 0-1 qualification score; ≥70% with no disqualifiers approves the lead for routing."),
      el("div", { class: "field-grid" },
        field("Attribution", "Build one first via Node 28", attrSelect),
        field("Urgency", null, urgency),
        field("Estimated value (£)", null, value)),
      submit, result);
  }

  function buildNode30Block() {
    const qualSelect = el("select", {});
    node30QualificationSelect = qualSelect;
    refreshPhase6And7Selectors();
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Route Qualified Lead");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node30/generate`, { qualification_id: qualSelect.value });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 30"), el("h3", {}, "Smart Lead Allocation & Routing"),
      el("p", {}, "Pending acceptance -- real, working form. Matches a qualified lead to a service provider by remaining capacity. Rejects disqualified leads outright."),
      el("div", { class: "field-grid" }, field("Qualification", "Qualify one first via Node 29", qualSelect)),
      submit, result);
  }

  function buildNode31Block() {
    const routingSelect = el("select", {});
    node31RoutingSelect = routingSelect;
    refreshPhase6And7Selectors();
    const status = el("select", {}, [
      "qualified", "disqualified", "routed_dispatched", "rejected", "contacted", "unreachable",
      "appointment_booked", "lost_not_interested", "job_completed_won", "cancelled_lost", "revenue_realized",
    ].map((v) => el("option", { value: v, ...(v === "qualified" ? { selected: "selected" } : {}) }, v)));
    const revenue = el("input", { type: "text", value: "" });
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Advance Lifecycle");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node31/generate`, {
            routing_id: routingSelect.value, new_status: status.value,
            revenue_amount_gbp: revenue.value ? Number(revenue.value) : null,
          });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 31"), el("h3", {}, "Lead Lifecycle State Machine"),
      el("p", {}, "Pending acceptance -- real, working form. Real state machine (lead_created → qualified → routed_dispatched → contacted → appointment_booked → job_completed_won → revenue_realized). Rejects any transition not valid from the lead's current real state."),
      el("div", { class: "field-grid" },
        field("Routing", "Route one first via Node 30", routingSelect),
        field("New status", null, status),
        field("Revenue (£, only for revenue_realized)", null, revenue)),
      submit, result);
  }

  function buildNode32Block() {
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Record Performance");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node32/generate`, {});
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 32"), el("h3", {}, "Performance Warehouse"),
      el("p", {}, "Pending acceptance -- real, working form. Compiles impressions/clicks/leads/revenue into ROAS and conversion-rate metrics for this run's target/opportunity/channel. Uses illustrative default volumes (no real ad-spend tracking exists yet) -- the calculation itself is real."),
      submit, result);
  }

  function buildNode33Block() {
    const leadSelect = el("select", {});
    node33LeadSelect = leadSelect;
    refreshPhase6And7Selectors();
    const source = el("select", {}, ["technician_app", "crm_sync", "client_portal", "accounting_webhook"].map((v) => el("option", { value: v }, v)));
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Ingest Outcome Feedback");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node33/generate`, { lead_id: leadSelect.value, feedback_source: source.value });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 33"), el("h3", {}, "Outcome Feedback Ingestion"),
      el("p", {}, "Pending acceptance -- real, working form. Ingests real-world job outcome (status/rating/invoice) tied back to a specific lead."),
      el("div", { class: "field-grid" }, field("Lead", "Capture one first via Node 27", leadSelect), field("Feedback source", null, source)),
      submit, result);
  }

  function buildNode34Block() {
    const perfSelect = el("select", {});
    node34PerformanceSelect = perfSelect;
    refreshPhase6And7Selectors();
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Detect Winning Strategy");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node34/generate`, { performance_record_id: perfSelect.value });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 34"), el("h3", {}, "Winner Detection"),
      el("p", {}, "Pending acceptance -- real, working form. is_winner=true when ROAS ≥4.0 and conversion rate ≥3% and ≥3 leads captured, computed from the real Node 32 metrics."),
      el("div", { class: "field-grid" }, field("Performance record", "Record one first via Node 32", perfSelect)),
      submit, result);
  }

  function buildNode35Block() {
    const winnerSelect = el("select", {});
    node35WinnerSelect = winnerSelect;
    refreshPhase6And7Selectors();
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Generate Amplification Plan");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node35/generate`, { winner_id: winnerSelect.value });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 35"), el("h3", {}, "Winner Amplification"),
      el("p", {}, "Pending acceptance -- real, working form. Only accepts a Node 34 record with is_winner=true; generates geo-expansion and format-diversification variants for scaling it."),
      el("div", { class: "field-grid" }, field("Winner", "Must have is_winner=true (Node 34)", winnerSelect)),
      submit, result);
  }

  function buildNode36Block() {
    const ampSelect = el("select", {});
    node36AmplificationSelect = ampSelect;
    refreshPhase6And7Selectors();
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Plan Effort Allocation");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node36/generate`, { amplification_id: ampSelect.value });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 36"), el("h3", {}, "Distribution Effort Allocation"),
      el("p", {}, "Pending acceptance -- real, working form. Allocates capacity units to scale an amplified winner."),
      el("div", { class: "field-grid" }, field("Amplification plan", "Generate one first via Node 35", ampSelect)),
      submit, result);
  }

  function buildNode37Block() {
    const allocSelect = el("select", {});
    node37AllocationSelect = allocSelect;
    refreshPhase6And7Selectors();
    const result = buildResultBox();
    const submit = el("button", { class: "btn btn--secondary", type: "button" }, "Record Distribution Knowledge");
    submit.addEventListener("click", () =>
      requireRun(async () => {
        try {
          const record = await api("POST", `/api/runs/${state.runId}/node37/generate`, { allocation_id: allocSelect.value });
          showResult(result, true, record); await refreshRun();
        } catch (err) { showResult(result, false, err.payload || { message: err.message }); }
      })
    );
    return el("div", { class: "node-block node-block--pending" },
      el("span", { class: "node-tag" }, "NODE 37"), el("h3", {}, "Distribution Knowledge Base"),
      el("p", {}, "Pending acceptance -- real, working form. Records the durable learning_summary/key_success_factors/recommended_rules for this run's winning strategy -- the actual output the learning loop exists to produce."),
      el("div", { class: "field-grid" }, field("Effort allocation", "Plan one first via Node 36", allocSelect)),
      submit, result);
  }

  let campaignOverviewBodyEl = null;

  function overviewStat(label, count) {
    return el(
      "div", { class: `overview-stat${count === 0 ? " zero" : ""}` },
      el("span", { class: "n" }, String(count)),
      el("span", { class: "label" }, label)
    );
  }

  function renderCampaignOverviewBody() {
    const bodyEl = campaignOverviewBodyEl;
    if (!bodyEl) return;
    bodyEl.innerHTML = "";
    if (!state.runId) {
      bodyEl.appendChild(el("p", { class: "overview-empty" }, "No run loaded. Click New Run, or pick one from “Load existing run…” above."));
      return;
    }
    const run = state.run || {};

    if (run.target) {
      const t = run.target;
      bodyEl.appendChild(
        el(
          "div", { class: "overview-summary" },
          el("h3", {}, `${t.service} — ${t.geography.locality}, ${t.geography.region}, ${t.geography.country}`),
          el("p", {}, `Target: ${t.target_id} · Market: ${t.market} · Status: ${t.status}`),
          el("p", {}, run.product ? `Problem: ${run.product.problem}` : "Node 02 (product intelligence) not registered yet."),
          el("p", {}, `Run: ${run.run_id} · Created: ${run.created_at}`)
        )
      );
    } else {
      bodyEl.appendChild(
        el("div", { class: "overview-summary" }, el("h3", {}, "No target registered yet"), el("p", {}, `Run: ${run.run_id} · Created: ${run.created_at} · Register Node 01 in Phase 1 to begin.`))
      );
    }

    bodyEl.appendChild(buildWhatWorkedSection(run));
    bodyEl.appendChild(buildSpendRollup(run));

    const demandSignalCount =
      (run.demand_signals || []).length + (run.questions || []).length + (run.social_video_signals || []).length +
      (run.competitor_signals || []).length + (run.community_signals || []).length + (run.trends || []).length;

    bodyEl.appendChild(el("h4", { style: "margin:20px 0 8px;color:var(--muted);font-size:12px;letter-spacing:.08em;text-transform:uppercase" }, "Artifact counts (supporting detail)"));
    const grid = el(
      "div", { class: "overview-grid" },
      overviewStat("Audience segments (03)", (run.audience || []).length),
      overviewStat("Demand signals (05-10)", demandSignalCount),
      overviewStat("Classifications (11)", (run.classifications || []).length),
      overviewStat("Campaign clusters (15)", (run.clusters || []).length),
      overviewStat("Canonical facts (16)", (run.facts || []).length),
      overviewStat("Video assets (18)", (run.video_assets || []).length),
      overviewStat("Approved packages (19)", (run.approved_packages || []).length),
      overviewStat("Publication plans (20)", (run.publication_plans || []).length),
      overviewStat("Search packages (21)", (run.search_packages || []).length),
      overviewStat("Route recommendations (26)", (run.routes || []).length),
      overviewStat("Leads captured (27)", (run.leads || []).length),
      overviewStat("Attributions (28)", (run.attributions || []).length),
      overviewStat("Qualifications (29)", (run.qualifications || []).length),
      overviewStat("Routings (30)", (run.routings || []).length),
      overviewStat("Lifecycle transitions (31)", (run.lifecycles || []).length),
      overviewStat("Performance records (32)", (run.performance_records || []).length),
      overviewStat("Outcome feedback (33)", (run.outcome_feedback || []).length),
      overviewStat("Winner evaluations (34)", (run.winners || []).length),
      overviewStat("Amplification plans (35)", (run.amplifications || []).length),
      overviewStat("Effort allocations (36)", (run.allocations || []).length),
      overviewStat("Knowledge entries (37)", (run.knowledge_entries || []).length)
    );
    bodyEl.appendChild(grid);

    const events = run.lineage || [];
    bodyEl.appendChild(el("p", { class: "field-hint" }, `${events.length} lineage event${events.length === 1 ? "" : "s"} — full timeline in the Run lineage panel on the right.`));
  }

  // One row per candidate spawned by "Propose one-hop candidate campaigns": shows its real state
  // (pending_phase2_approval / pending_product_definition / parked / stopped_no_demand) and, only
  // for a geo-axis candidate awaiting approval, the single human approval gate before its real
  // Node 05 live-fetch fires (plan §4 correction, §9 gate 1) -- never an automatic/synthetic fetch.
  function buildCandidateApprovalRow(candidate) {
    const row = el("div", { class: "candidate-row", style: "display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--line)" });
    const label = el("span", {}, `${candidate.axis === "geo" ? "🌍" : "🔧"} ${candidate.target.service} · ${candidate.target.geography.locality} — ${candidate.run_id}`);
    row.appendChild(label);
    const statusEl = el("span", { class: "field-hint" }, candidate.candidate_status);
    row.appendChild(statusEl);
    if (candidate.candidate_status === "pending_phase2_approval") {
      const approveBtn = el("button", { class: "btn btn--secondary", type: "button" }, "Approve real Phase 2 live-fetch");
      approveBtn.addEventListener("click", async () => {
        approveBtn.disabled = true;
        try {
          const result = await api("POST", `/api/runs/${candidate.run_id}/node01/approve_phase2`, {});
          statusEl.textContent = result.candidate_status || "phase 2 confirmed — real signal found";
        } catch (err) {
          statusEl.textContent = `error: ${(err.payload && err.payload.message) || err.message}`;
        } finally {
          approveBtn.disabled = false;
        }
      });
      row.appendChild(approveBtn);
    } else if (candidate.candidate_status === "pending_product_definition") {
      row.appendChild(el("span", { class: "field-hint" }, `Describe this service's real product (Node 02) for ${candidate.run_id} via the run selector before requesting Phase 2.`));
    }
    return row;
  }

  // Real spend only -- every lineage event's cost_gbp is opt-in and stamped by the node itself
  // from its provider's actual published rate (see append_lineage in server.py); nothing here
  // estimates or invents a figure. Renders nothing at all while every node's cost_gbp is absent,
  // which is the real state of this pipeline today (no node has yet performed a confirmed
  // billed action) -- a permanent "£0.00" line would misrepresent that as tracked-and-zero
  // rather than not-yet-applicable.
  function buildSpendRollup(run) {
    const events = (run.lineage || []).filter((e) => typeof e.cost_gbp === "number");
    if (!events.length) return el("div", {});
    const total = events.reduce((sum, e) => sum + e.cost_gbp, 0);
    const leads = (run.leads || []).length;
    const wins = (run.winners || []).filter((w) => w.is_winner).length;
    const parts = [`Spend to date: £${total.toFixed(2)}`];
    if (leads > 0) parts.push(`£${(total / leads).toFixed(2)} per lead`);
    if (wins > 0) parts.push(`£${(total / wins).toFixed(2)} per win`);
    return el(
      "div", { class: "overview-summary", style: "border-color:var(--amber);background:var(--amber-bg)" },
      el("h3", {}, "Real spend"),
      el("p", {}, parts.join(" · "))
    );
  }

  // Surfaces WHAT WORKED, not just that something happened -- the actual input pattern behind a
  // successful qualification and the actual recommended rules behind a winning channel, so an
  // operator can see what to replicate, not just a count of activity.
  function buildWhatWorkedSection(run) {
    const wrap = el("div", {});
    const winners = (run.winners || []).filter((w) => w.is_winner);
    const knowledge = run.knowledge_entries || [];
    const amplifications = run.amplifications || [];
    const qualified = (run.qualifications || []).filter((q) => q.is_qualified);

    if (!winners.length && !qualified.length) {
      wrap.appendChild(el("p", { class: "overview-empty" }, "No successful path identified yet — run Phase 6 (qualify a lead) and Phase 7 (detect a winner) to populate this."));
      return wrap;
    }

    if (winners.length) {
      const w = winners[winners.length - 1];
      const a = w.performance_assessment;
      const replicateResult = buildResultBox();
      const replicateBtn = el("button", { class: "btn btn--primary", type: "button" }, "⟳ Replicate this winning campaign");
      const replicateStatus = el("span", { class: "field-hint" }, "Reruns the real Node 11→17 chain against the same proven cluster/facts to mint several new video-asset variants fast — the same underlying dataset, minor changes only.");
      replicateBtn.addEventListener("click", () =>
        requireRun(async () => {
          replicateBtn.disabled = true;
          try {
            const record = await api("POST", `/api/runs/${state.runId}/node18/replicate_winner`, {});
            showResult(replicateResult, true, record);
            replicateStatus.textContent = `Created ${record.created.length} new variant(s)${record.failed.length ? `, ${record.failed.length} failed` : ""}.`;
            await refreshRun();
          } catch (err) {
            showResult(replicateResult, false, err.payload || { message: err.message });
          } finally {
            replicateBtn.disabled = false;
          }
        })
      );
      const candidatesResult = buildResultBox();
      const candidatesList = el("div", {});
      const proposeBtn = el("button", { class: "btn btn--primary", type: "button" }, "⤢ Propose one-hop candidate campaigns");
      const proposeStatus = el("span", { class: "field-hint" }, "Auto-registers new, independent campaigns one hop away on the geo or service axis from a curated real adjacency/taxonomy source (never a compound jump) — each is its own new run, earning its own real Phase 2 data before it can proceed.");
      proposeBtn.addEventListener("click", () =>
        requireRun(async () => {
          proposeBtn.disabled = true;
          try {
            const record = await api("POST", `/api/runs/${state.runId}/node01/propose_candidates`, {});
            showResult(candidatesResult, true, record);
            proposeStatus.textContent = `Created ${record.created.length} candidate(s)${record.failed.length ? `, ${record.failed.length} failed` : ""}.`;
            candidatesList.innerHTML = "";
            record.created.forEach((c) => candidatesList.appendChild(buildCandidateApprovalRow(c)));
          } catch (err) {
            showResult(candidatesResult, false, err.payload || { message: err.message });
          } finally {
            proposeBtn.disabled = false;
          }
        })
      );
      wrap.appendChild(el(
        "div", { class: "overview-summary", style: "border-color:var(--blue);background:var(--blue-bg)" },
        el("h3", {}, `Winning channel: ${w.channel} (${a.winner_tier} tier)`),
        el("p", {}, `ROAS ${a.roas}× · Conversion rate ${(a.conversion_rate * 100).toFixed(1)}% · Confidence ${(a.confidence_score * 100).toFixed(0)}%`),
        el("p", {}, `Recommendation: ${w.recommendation}`),
        el("div", { class: "btn-row" }, replicateBtn, replicateStatus),
        replicateResult,
        el("div", { class: "btn-row" }, proposeBtn, proposeStatus),
        candidatesList,
        candidatesResult
      ));
    }

    const entry = knowledge.length ? knowledge[knowledge.length - 1] : null;
    if (entry) {
      wrap.appendChild(el("h4", { style: "margin:14px 0 6px" }, "Recommended rules to replicate this success"));
      wrap.appendChild(el("p", {}, entry.learning_summary));
      wrap.appendChild(el("p", { class: "field-hint" }, "Key success factors:"));
      wrap.appendChild(el("ul", { style: "margin:2px 0 10px" }, entry.key_success_factors.map((f) => el("li", {}, f))));
      wrap.appendChild(el("p", { class: "field-hint" }, "Rules for future campaigns:"));
      wrap.appendChild(el("ul", { style: "margin:2px 0 10px" }, entry.recommended_rules.map((r) => el("li", {}, r))));
    }

    if (amplifications.length) {
      const amp = amplifications[amplifications.length - 1];
      const geo = amp.expansion_variants.find((v) => v.dimension === "geographic_expansion");
      const fmt = amp.expansion_variants.find((v) => v.dimension === "format_diversification");
      wrap.appendChild(el("h4", { style: "margin:14px 0 6px" }, "How to build more inputs around this campaign"));
      if (geo) wrap.appendChild(el("p", {}, `Expand to: ${geo.target_markets.join(", ")}`));
      if (fmt) wrap.appendChild(el("p", {}, `Add formats: ${fmt.formats.join(", ")}`));
    }

    if (qualified.length) {
      const q = qualified[qualified.length - 1];
      wrap.appendChild(el("h4", { style: "margin:14px 0 6px" }, "What made this lead qualify"));
      wrap.appendChild(el(
        "p", {},
        `service_match=${q.factors.service_match} · geo_eligible=${q.factors.geo_eligible} · urgency=${q.factors.urgency_level} · duplicate_risk=${q.factors.duplicate_risk} · score=${q.qualification_score}`
      ));
    }
    return wrap;
  }

  // Blocking candidate_status values a candidate can sit in before it has earned real Phase 2
  // data -- must mirror server.py's _BLOCKING_CANDIDATE_STATUSES exactly. Real bug found live
  // 2026-08-18: this DOM-driven runner had no awareness of candidate_status at all, so running it
  // on a candidate still pending_phase2_approval clicked straight through Phase 2's manual-entry
  // forms using whatever demo/default values sat in them (sig_demand_01, q_demo_01, etc.) --
  // fabricating a full Phase 2-4 chain under a candidate that was supposed to earn a real signal
  // first. The server-side headless pipeline/run_all already refused this correctly; this button
  // did not, because it never checks server state before clicking through.
  const CANDIDATE_BLOCKING_STATUSES = new Set(["pending_product_definition", "pending_phase2_approval", "parked", "stopped_no_demand"]);

  async function runFullPipeline(statusEl) {
    if (state.run && CANDIDATE_BLOCKING_STATUSES.has(state.run.candidate_status)) {
      if (statusEl) statusEl.textContent = `Refused: this run is a candidate at "${state.run.candidate_status}" -- it must earn real Phase 2 data via Campaign Queue's approval action before Run Full Pipeline can proceed. Running this would fabricate Phase 2 data, not use a real signal.`;
      return false;
    }
    const phaseIds = ["demand_intelligence", "strategy", "assets", "distribution_conversion", "lead_lifecycle", "learning"];
    for (const phaseId of phaseIds) {
      if (statusEl) statusEl.textContent = `Running Phase ${phaseId.replace(/_/g, " ")}…`;
      const ok = await runAllInPanel(`panel-${phaseId}`, statusEl);
      if (!ok) return false;
    }

    // Closes the replication loop automatically: if Phase 7 detected a winner, propose its
    // one-hop candidates right away instead of waiting for a second manual click. Each candidate
    // still stops at its own real approval gate (PLAN §9 gate 1) before any real live-fetch --
    // this only ever registers new Node 01 targets, never a real external/paid action, so there
    // is nothing for a "gate 2" (real distribution/cost) to hold here today. The moment a real
    // paid or external-dispatch node exists, its check belongs right here, before any such
    // candidate advances past this point -- not before candidate registration itself.
    await refreshRun();
    const hasWinner = (state.run.winners || []).some((w) => w.is_winner);
    if (hasWinner) {
      if (statusEl) statusEl.textContent = "Winner detected — proposing one-hop candidate campaigns…";
      try {
        const record = await api("POST", `/api/runs/${state.runId}/node01/propose_candidates`, {});
        if (statusEl) statusEl.textContent = `Full pipeline complete — Phase 2 through Phase 7. Proposed ${record.created.length} candidate campaign(s), each awaiting its own Phase 2 approval.`;
      } catch (err) {
        if (statusEl) statusEl.textContent = "Full pipeline complete — Phase 2 through Phase 7. (Candidate proposal failed: " + ((err.payload && err.payload.message) || err.message) + ")";
      }
    } else if (statusEl) {
      statusEl.textContent = "Full pipeline complete — Phase 2 through Phase 7.";
    }
    renderCampaignOverviewBody();
    return true;
  }

  function buildCampaignOverviewPanel() {
    const runAllStatus = el("span", { class: "field-hint" }, "");
    const runAllBtn = el("button", { class: "btn btn--primary", type: "button" }, "▶ Run Full Pipeline (Phase 2 → 7)");
    runAllBtn.addEventListener("click", () =>
      requireRun(async () => {
        runAllBtn.disabled = true;
        try {
          await runFullPipeline(runAllStatus);
        } finally {
          runAllBtn.disabled = false;
        }
      })
    );
    const panel = el(
      "section", { class: "panel", id: "panel-campaign-overview" },
      el("h2", {}, "Campaign Overview"),
      el(
        "p", { class: "panel-sub" },
        "Read-only, live-refreshing snapshot of the currently loaded run: target, product, and per-phase artifact counts. Updates automatically after every action taken in the phase panels."
      ),
      el("div", { class: "btn-row" }, runAllBtn, runAllStatus)
    );
    const body = el("div", { id: "campaign-overview-body" });
    panel.appendChild(body);
    campaignOverviewBodyEl = body;
    renderCampaignOverviewBody();
    return panel;
  }

  // Genuinely parallel: unlike runAllInPanel() (which clicks real DOM buttons for the one loaded
  // run), this fires POST .../pipeline/run_all directly against N different run_ids at once --
  // the server-side headless driver reuses the exact same real handlers, so nothing here
  // duplicates or bypasses validation.
  const CAMPAIGN_QUEUE_RUNNABLE_STATES = new Set(["running", "lead_captured", "awaiting_winner_detection"]);
  const CAMPAIGN_QUEUE_STATE_LABELS = {
    no_target: "No target registered", no_signal: "No demand signal yet", needs_facts: "Needs Node 16 facts",
    pending_phase2_approval: "Pending Phase 2 approval", pending_product_definition: "Needs product definition (Node 02)",
    parked: "Parked", stopped_no_demand: "Stopped — no demand found", running: "Ready to run",
    lead_captured: "Lead captured — continuing", awaiting_winner_detection: "Awaiting winner detection",
    winner_detected: "Winner detected", rejected_by_node19: "Rejected by quality gate (Node 19)",
  };

  // Global phase/node summary matrix -- one cell per phase, click to drill into just that
  // phase's campaigns. Counts and per-campaign phase/node/action all come straight from
  // GET /api/campaign_queue's real, freshly-derived position (server.py derive_campaign_position),
  // never computed client-side, so this can never drift from what the server actually knows.
  const PHASE_ORDER = [
    { phase: 1, nodes: "Nodes 01-04" }, { phase: 2, nodes: "Nodes 05-10" }, { phase: 3, nodes: "Nodes 11-15" },
    { phase: 4, nodes: "Nodes 16-19" }, { phase: 5, nodes: "Nodes 20-27" }, { phase: 6, nodes: "Nodes 28-31" },
    { phase: 7, nodes: "Nodes 32-37" },
  ];

  function buildCampaignQueuePanel() {
    const body = el("div", {});
    const matrix = el("div", { style: "display:flex;gap:1px;margin:14px 0;border-radius:8px;overflow:hidden;border:1px solid var(--line)" });
    const status = el("span", { class: "field-hint" }, "");
    const refreshBtn = el("button", { class: "btn btn--secondary", type: "button" }, "↻ Refresh");
    const runAllBtn = el("button", { class: "btn btn--primary", type: "button" }, "▶ Run all runnable campaigns");
    let lastData = null;
    let selectedPhase = null;

    function renderMatrix() {
      matrix.innerHTML = "";
      PHASE_ORDER.forEach(({ phase, nodes }) => {
        const count = (lastData && lastData.phase_counts[String(phase)]) || 0;
        const sel = selectedPhase === phase;
        const cell = el(
          "button",
          { type: "button", style: `flex:1;min-width:0;padding:10px 4px;border:0;border-right:1px solid var(--line);cursor:pointer;background:${sel ? "var(--ink)" : "#fff"};color:${sel ? "#fff" : "inherit"}` },
          el("div", { style: "font-size:10px;letter-spacing:.06em;text-transform:uppercase;opacity:.75" }, `P${phase}`),
          el("div", { style: "font-size:10.5px;opacity:.75" }, nodes),
          el("div", { style: "font-size:22px;font-weight:700;margin-top:4px" }, String(count))
        );
        cell.addEventListener("click", () => { selectedPhase = sel ? null : phase; renderMatrix(); renderList(); updateStatus(); });
        matrix.appendChild(cell);
      });
    }

    function renderList() {
      body.innerHTML = "";
      if (!lastData || !lastData.campaigns.length) {
        body.appendChild(el("p", { class: "overview-empty" }, "No campaigns yet."));
        return;
      }
      const campaigns = selectedPhase ? lastData.campaigns.filter((c) => c.phase === selectedPhase) : lastData.campaigns;
      if (!campaigns.length) {
        body.appendChild(el("p", { class: "overview-empty" }, `No campaigns currently in Phase ${selectedPhase}.`));
        return;
      }
      campaigns.forEach((c) => {
        const target = c.target ? `${c.target.service} · ${c.target.geography.locality}` : "no target";
        const row = el("div", { class: "candidate-row", style: "display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--line)" });
        row.appendChild(el("span", {}, `${target} — ${c.run_id}`));
        row.appendChild(el("span", { class: "field-hint" }, `P${c.phase} · ${c.node} — ${c.action}`));
        const loadBtn = el("button", { class: "btn btn--secondary", type: "button" }, "Load");
        loadBtn.addEventListener("click", async () => { await loadRun(c.run_id); selectPhase("campaign-overview"); });
        row.appendChild(loadBtn);
        if (c.state === "pending_phase2_approval") {
          const approveBtn = el("button", { class: "btn btn--secondary", type: "button" }, "Approve real Phase 2 live-fetch");
          approveBtn.addEventListener("click", async () => {
            approveBtn.disabled = true;
            try {
              await api("POST", `/api/runs/${c.run_id}/node01/approve_phase2`, {});
            } catch (err) {
              status.textContent = `Approval failed for ${c.run_id}: ${(err.payload && err.payload.message) || err.message}`;
            } finally {
              approveBtn.disabled = false;
              await refreshQueue();
              if (state.runId === c.run_id) await refreshRun();
            }
          });
          row.appendChild(approveBtn);
        }
        if (CAMPAIGN_QUEUE_RUNNABLE_STATES.has(c.state)) {
          const runBtn = el("button", { class: "btn btn--secondary", type: "button" }, "Run Full Pipeline");
          runBtn.addEventListener("click", async () => {
            runBtn.disabled = true;
            try {
              await api("POST", `/api/runs/${c.run_id}/pipeline/run_all`, {});
            } finally {
              runBtn.disabled = false;
              await refreshQueue();
              if (state.runId === c.run_id) await refreshRun();
            }
          });
          row.appendChild(runBtn);
        }
        body.appendChild(row);
      });
    }

    function updateStatus() {
      if (!lastData) return;
      status.textContent = `${lastData.campaigns.length} campaign(s)${selectedPhase ? ` · showing Phase ${selectedPhase} only` : ""}.`;
    }

    async function refreshQueue() {
      status.textContent = "Loading…";
      lastData = await api("GET", "/api/campaign_queue");
      renderMatrix();
      renderList();
      updateStatus();
    }

    const importFile = el("input", { type: "file", accept: ".csv,text/csv" });
    const importBtn = el("button", { class: "btn btn--secondary", type: "button" }, "⇪ Import CSV");
    const importResult = buildResultBox();
    const importStatus = el(
      "span", { class: "field-hint" },
      "Columns: target_type, service, market, geography_locality, geography_region, geography_country, product_problem, product_solution, product_features, product_benefits, product_differentiators, product_commercial_model, product_customer_outcome, audience_segment_name, audience_needs, audience_pains, audience_urgency. One row per campaign -- same real Node 01/02/03/04 validation as manual entry, no bypass. One bad row is reported and skipped, never blocks the rest."
    );
    importBtn.addEventListener("click", () => {
      const file = importFile.files[0];
      if (!file) { importStatus.textContent = "Choose a .csv file first."; return; }
      importBtn.disabled = true;
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const record = await api("POST", "/api/bulk_import", { csv: reader.result });
          showResult(importResult, true, record);
          importStatus.textContent = `Imported ${record.created.length} campaign(s)${record.failed.length ? `, ${record.failed.length} row(s) failed` : ""}.`;
          await refreshQueue();
        } catch (err) {
          showResult(importResult, false, err.payload || { message: err.message });
        } finally {
          importBtn.disabled = false;
        }
      };
      reader.readAsText(file);
    });

    refreshBtn.addEventListener("click", refreshQueue);
    runAllBtn.addEventListener("click", async () => {
      runAllBtn.disabled = true;
      status.textContent = "Running all runnable campaigns…";
      try {
        const data = await api("GET", "/api/campaign_queue");
        const runnable = data.campaigns.filter((c) => CAMPAIGN_QUEUE_RUNNABLE_STATES.has(c.state));
        await Promise.all(runnable.map((c) => api("POST", `/api/runs/${c.run_id}/pipeline/run_all`, {})));
        status.textContent = `Ran ${runnable.length} campaign(s) concurrently.`;
      } finally {
        runAllBtn.disabled = false;
        await refreshQueue();
        if (state.runId) await refreshRun();
      }
    });

    const panel = el(
      "section", { class: "panel", id: "panel-campaign-queue" },
      el("h2", {}, "Campaign Queue"),
      el(
        "p", { class: "panel-sub" },
        "Every campaign on this machine, its real state, and one-click actions -- drives many campaigns concurrently via direct API calls (not the single-run DOM click-through), since every run already has its own isolated storage."
      ),
      el("div", { class: "btn-row" }, refreshBtn, runAllBtn, status),
      matrix,
      el("h4", { style: "margin:20px 0 6px" }, "Bulk import"),
      el("div", { class: "btn-row" }, importFile, importBtn),
      importStatus,
      importResult,
      body
    );
    refreshQueue();
    return panel;
  }

  function buildDeliveryStatusPanel() {
    return el(
      "section",
      { class: "panel", id: "panel-delivery-status" },
      el("h2", {}, "Delivery Status (historical reference)"),
      el(
        "p",
        { class: "delivery-status-note" },
        "This is secondary information only. The node-by-node implementation/evidence trail lives in the workstream checklists and reports under ",
        el("code", {}, "workstream/600_workflow/ep050/"),
        " and ",
        el("code", {}, "epics/ep_050_distribution_engine/reports/"),
        ". The prior delivery-dashboard build (frozen, not edited by this console) is preserved at ",
        el("code", {}, "implementation/operational_console/"),
        " for read-only historical reference."
      )
    );
  }

  // --- boot ---------------------------------------------------------------

  async function loadKnownValues() {
    try {
      const response = await fetch("/api/known_values");
      state.knownValues = await response.json();
    } catch (err) {
      state.knownValues = {};
    }
  }

  async function boot() {
    await Promise.all([loadPhases(), loadKnownValues()]);
    renderRail();
    renderStage();
    renderRunIndicator();
    document.getElementById("new-run-btn").addEventListener("click", () => createRun().catch((err) => alert(err.message)));
    document.getElementById("run-selector").addEventListener("change", (e) => loadRun(e.target.value).catch((err) => alert(err.message)));
    loadRunList();
  }

  boot().catch((err) => {
    document.getElementById("stage").textContent = `Failed to load console: ${err.message}`;
  });
})();
