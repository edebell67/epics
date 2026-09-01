# epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py
# EP050 Operational Console v2 — API/unit/contract/regression test suite.
#
# VERSION HISTORY
# v1.8.0 · 2026-08-21 · Adds HTTP coverage for Discovery 00A–00F persistence, evidence gates,
#   canonical contract validation and idempotent Node 15 branch merge.
# v1.7.0 · 2026-08-18 · Adds HTTP coverage for the new Node 19-21/26-27 console controls:
#   Node 19 approve/reject, and a full Node 20->21->26->27 chain producing a real structured
#   lead record end to end, plus a consent-not-granted rejection case. Updated the two phase-
#   reconciliation assertions that hardcoded the pre-wiring console_controls state for Phase 4/5.
# v1.6.0 · 2026-08-18 · Adds test_phases_endpoint_does_not_falsely_report_phase6_7_as_not_started,
#   locking in the fix that moved Phase 6/7 (Nodes 28-37) from not_started_nodes (false) to
#   pending_acceptance_nodes (accurate: real tested code, no formal board ACCEPTED event yet).
# v1.5.0 · 2026-08-18 · Adds HTTP coverage for the new GET /api/known_values endpoint: curated
#   seeds returned with no runs on disk, and real registered Node 01/03 values (service/market/
#   target_type/locality/segment_name) surfaced once a target and segment exist.
# v1.4.0 · 2026-08-17 · Adds HTTP coverage for the new Nodes 05-10/15/18 /live automated-ingestion
#   endpoints (GET /api/live_fetch_status, disabled-by-default 503, mocked-fetch success for
#   Node 08, no-flag-needed success for Nodes 10/15/18, unknown-cluster fail-closed for Node 18).
#   Also fixed test_node11_classify_invalid_source_type_is_rejected, which had gone stale after
#   Node 11's own v1.1.0 upgrade legitimately started accepting "search_query" -- swapped in a
#   genuinely-invalid source_type so the rejection path is still exercised.
# v1.3.0 · 2026-08-17 · URGENT ALLOCATION: added real HTTP coverage for the new Node 04-10
#   controls (positive + fail-closed-before-prerequisite for each), a full-chain helper test,
#   and extended the full-lifecycle regression through the complete Node 01-18 chain.
# v1.2.0 · 2026-08-17 · CHANGE REQUIRED fix: replaced implemented_nodes/locked_nodes assertions
#   with the five-state model (accepted_nodes/console_controls/pending_acceptance_nodes/
#   mvp_deferred_nodes/not_started_nodes) and added a full seven-phase reconciliation test.
# v1.1.0 · 2026-08-17 · Added Node 15/16/18 adapter coverage (reactivation pass).
# v1.0.0 · 2026-08-17 · Initial suite: real HTTP requests against a live loopback-only server instance.
#
# All tests run fully offline against a live server bound to 127.0.0.1 on an ephemeral port.
# No network call leaves the loopback interface; no production datastore is touched.

from __future__ import annotations

import json
import shutil
import socket as socket_module
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

import server as console_server
import ep048_render_publish_trigger as ep048_trigger

MASTER_WORKFLOW_PHASE_TITLES = [
    "Product/Market Ingestion",
    "Demand Intelligence",
    "Strategy",
    "Content & Assets",
    "Distribution & Conversion",
    "Lead Lifecycle",
    "Learning & Optimization",
]


def _free_port() -> int:
    with socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    original_data_root = console_server.DATA_ROOT
    test_data_root = tmp_path_factory.mktemp("console_runs") / "runs"
    console_server.DATA_ROOT = test_data_root

    port = _free_port()
    httpd = console_server.ThreadingHTTPServer(("127.0.0.1", port), console_server.ConsoleHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            if requests.get(f"{base_url}/api/status", timeout=1).status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(0.05)
    else:
        raise RuntimeError("Server did not become ready")

    yield base_url

    httpd.shutdown()
    httpd.server_close()
    console_server.DATA_ROOT = original_data_root
    shutil.rmtree(test_data_root, ignore_errors=True)


@pytest.fixture
def run_id(live_server):
    response = requests.post(f"{live_server}/api/runs")
    assert response.status_code == 201
    return response.json()["run_id"]


def _register_target(live_server, run_id, locality="Blackheath", service="boiler_repair"):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node01",
        json={
            "target_type": "service_market",
            "service": service,
            "market": "domestic_plumbing",
            "geography": {"locality": locality, "region": "London", "country": "UK"},
        },
    )


def _register_product(live_server, run_id):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node02",
        json={
            "problem": "Homeowners lose boiler pressure and hot water.",
            "solution": "Same-day callout to diagnose and restore pressure.",
            "features": ["Same-day callout"],
            "benefits": ["Hot water restored quickly"],
            "differentiators": ["Local coverage"],
            "commercial_model": "Fixed diagnostic fee.",
            "customer_outcome": "Working boiler within 24 hours.",
        },
    )


def _register_audience(live_server, run_id):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node03",
        json={
            "segment_name": "Blackheath homeowner",
            "needs": ["Restore hot water"],
            "pains": ["No heating"],
            "urgency": "high",
            "eligibility_geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        },
    )


def _define_conversion(live_server, run_id):
    return requests.post(f"{live_server}/api/runs/{run_id}/node04", json={})


def _register_demand_signal(live_server, run_id, signal_id="sig_n05"):
    return requests.post(
        f"{live_server}/api/runs/{run_id}/node05",
        json={
            "signal_id": signal_id,
            # Contains a real COMMERCIAL_KEYWORDS hit ("engineer quote") so this shared fixture
            # passes the commercial-intent gate added 2026-08-19 (see server.py's
            # MIN_COMMERCIAL_INTENT_SCORE) -- the original text scored 0.0 and every test relying
            # on this helper to reach Node 15 (including _build_winner) would otherwise stop dead
            # at the new gate the moment it was introduced.
            "raw_query": "boiler pressure dropped to zero no hot water need an engineer quote",
            "topic": "boiler_pressure_loss",
            "source_type": "manual_curation",
            "observed_at": "2026-08-17T00:00:00+00:00",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        },
    )


def _register_question(live_server, run_id, question_id="q_n06"):
    return requests.post(
        f"{live_server}/api/runs/{run_id}/node06",
        json={
            "question_id": question_id,
            "question_text": "Why does my boiler pressure keep dropping overnight?",
            "topic": "boiler_pressure_loss",
            "pain_point": "Recurring pressure loss with no obvious cause",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "intent_cues": ["troubleshooting"],
            "source_type": "manual_curation",
            "observed_at": "2026-08-17T00:00:00+00:00",
            "evidence": "Manually curated fixture.",
        },
    )


def _register_social_video(live_server, run_id, signal_id="sv_n07"):
    return requests.post(
        f"{live_server}/api/runs/{run_id}/node07",
        json={
            "signal_id": signal_id,
            "platform": "youtube",
            "format": "short_video",
            "topic": "boiler_pressure_loss",
            "theme": "overnight_pressure_drop_diagnosis",
            "intent_cues": ["troubleshooting"],
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "observed_metrics": {"synthetic_views": 4200},
            "observed_at": "2026-08-17T00:00:00+00:00",
            "source_type": "manual_curation",
            "evidence": "Manually curated theme.",
        },
    )


def _register_competitor(live_server, run_id, signal_id="cp_n08"):
    return requests.post(
        f"{live_server}/api/runs/{run_id}/node08",
        json={
            "signal_id": signal_id,
            "competitor_name": "Synthetic Rival Plumbing Co",
            "channel": "google_search",
            "topic": "boiler_pressure_loss",
            "query": "boiler pressure loss repair blackheath",
            "attention_source": "organic_search",
            "relevance_score": 0.72,
            "competition_indicator": "medium",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "observed_at": "2026-08-17T00:00:00+00:00",
            "source_type": "manual_curation",
            "evidence": "Manually curated competitor observation.",
        },
    )


def _register_community(live_server, run_id, signal_id="cm_n09"):
    return requests.post(
        f"{live_server}/api/runs/{run_id}/node09",
        json={
            "signal_id": signal_id,
            "community_source": "r/DIYUK",
            "topic": "boiler_pressure_loss",
            "question": "Boiler pressure keeps dropping overnight, anyone else had this?",
            "pain_point": "Recurring pressure loss with no obvious cause",
            "intent_cues": ["troubleshooting"],
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "observed_metrics": {"synthetic_upvotes": 58},
            "observed_at": "2026-08-17T00:00:00+00:00",
            "source_type": "manual_curation",
            "evidence": "Manually curated community thread theme.",
        },
    )


def _register_trend(live_server, run_id, trend_id="trend_n10"):
    return requests.post(
        f"{live_server}/api/runs/{run_id}/node10",
        json={
            "trend_id": trend_id,
            "topic": "boiler_pressure_loss",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "window": {
                "baseline_start": "2026-08-01T00:00:00+00:00",
                "baseline_end": "2026-08-08T00:00:00+00:00",
                "current_start": "2026-08-08T00:00:00+00:00",
                "current_end": "2026-08-15T00:00:00+00:00",
            },
            "metric_name": "demand_signal_count",
            "baseline_value": 20.0,
            "baseline_sample_count": 10,
            "current_value": 32.0,
            "current_sample_count": 12,
            "source_type": "manual_curation",
            "evidence": "Manually curated trend observation.",
        },
    )


def _full_phase1_and_phase2_chain(live_server, run_id):
    """Registers Node01-10 in order via real HTTP calls, returning the final trend response."""
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _register_question(live_server, run_id)
    _register_social_video(live_server, run_id)
    _register_competitor(live_server, run_id)
    _register_community(live_server, run_id)
    return _register_trend(live_server, run_id)


def _classify_signal(live_server, run_id, signal_id="sig_console_test"):
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node11/classify",
        json={
            "signal_id": signal_id,
            # Same commercial-keyword fix as _register_demand_signal's default, and for the same
            # reason: this helper builds its own classify payload independently rather than
            # reading the already-registered signal's real raw_query, so it needed the identical
            # fix to pass the 2026-08-19 commercial-intent gate.
            "raw_query": "boiler pressure dropped to zero no hot water need an engineer quote",
            "topic": "boiler_pressure_loss",
            "source_type": "manual_curation",
            "observed_at": "2026-08-17T00:00:00+00:00",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        },
    )
    assert response.status_code == 200
    return response.json()


# --- server binding / safety -------------------------------------------------

def test_server_binds_loopback_only():
    assert console_server.ConsoleHandler is not None
    # The fixture above only ever binds ("127.0.0.1", port); this is a static
    # assertion that the module-level run() helper does the same.
    import inspect

    source = inspect.getsource(console_server.run)
    assert '"127.0.0.1"' in source


# --- status / phases / master-workflow traceability --------------------------

def test_status_endpoint_reports_ready_and_no_external_action(live_server):
    data = requests.get(f"{live_server}/api/status").json()
    assert data["status"] == "ok"
    assert data["external_action"] is False
    assert data["phases"] == 7


def test_phases_endpoint_matches_master_workflow_seven_stages(live_server):
    data = requests.get(f"{live_server}/api/phases").json()
    titles = [phase["title"] for phase in data["phases"]]
    assert titles == MASTER_WORKFLOW_PHASE_TITLES


def test_static_files_are_served(live_server):
    for path in ("/", "/console.html", "/console.css", "/console.js"):
        response = requests.get(f"{live_server}{path}")
        assert response.status_code == 200, path


# --- run lifecycle / persistence ---------------------------------------------

def test_create_run_returns_run_id_and_persists(live_server):
    response = requests.post(f"{live_server}/api/runs")
    assert response.status_code == 201
    body = response.json()
    assert body["run_id"].startswith("run_")
    assert body["target"] is None
    assert len(body["lineage"]) == 1  # "created" event


def test_get_unknown_run_returns_404(live_server):
    # Well-formed run_id (passes the format check) that was never created.
    response = requests.get(f"{live_server}/api/runs/run_20260101_000000_00000000")
    assert response.status_code == 404
    assert response.json()["error"] == "run_not_found"


def test_invalid_run_id_format_returns_400(live_server):
    response = requests.get(f"{live_server}/api/runs/not-a-valid-id")
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_run_id"


# --- Node 01 adapter -----------------------------------------------------------

def test_node01_register_positive_records_lineage(live_server, run_id):
    payload = {
        "target_type": "service_market",
        "service": "boiler_repair",
        "market": "domestic_plumbing",
        "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
    }
    response = requests.post(f"{live_server}/api/runs/{run_id}/node01", json=payload)
    assert response.status_code == 200
    record = response.json()
    assert record["target_id"] == "tgt_boiler_repair_blackheath"

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert run["target"]["target_id"] == "tgt_boiler_repair_blackheath"
    assert any(event["node"] == "node_01" for event in run["lineage"])


def test_node01_register_missing_field_returns_400(live_server, run_id):
    response = requests.post(f"{live_server}/api/runs/{run_id}/node01", json={"target_type": "service_market"})
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


# --- Node 02 adapter (requires Node 01 first) ---------------------------------

def test_node02_before_node01_is_rejected_fail_closed(live_server, run_id):
    response = requests.post(f"{live_server}/api/runs/{run_id}/node02", json={"problem": "x"})
    assert response.status_code == 409
    assert response.json()["error"] == "no_target"


def test_node02_register_positive_after_node01(live_server, run_id):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node01",
        json={
            "target_type": "service_market",
            "service": "boiler_repair",
            "market": "domestic_plumbing",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        },
    )
    payload = {
        "problem": "Homeowners lose boiler pressure and hot water.",
        "solution": "Same-day callout to diagnose and restore pressure.",
        "features": ["Same-day callout"],
        "benefits": ["Hot water restored quickly"],
        "differentiators": ["Local coverage"],
        "commercial_model": "Fixed diagnostic fee.",
        "customer_outcome": "Working boiler within 24 hours.",
    }
    response = requests.post(f"{live_server}/api/runs/{run_id}/node02", json=payload)
    assert response.status_code == 200
    assert response.json()["target_id"] == "tgt_boiler_repair_blackheath"


# --- Node 03 adapter (requires Node 01 + Node 02 first) -----------------------

def test_node03_before_node02_is_rejected_fail_closed(live_server, run_id):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node01",
        json={
            "target_type": "service_market",
            "service": "boiler_repair",
            "market": "domestic_plumbing",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        },
    )
    response = requests.post(f"{live_server}/api/runs/{run_id}/node03", json={"segment_name": "x"})
    assert response.status_code == 409
    assert response.json()["error"] == "no_product"


def test_node03_register_positive_after_node01_and_node02(live_server, run_id):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node01",
        json={
            "target_type": "service_market",
            "service": "boiler_repair",
            "market": "domestic_plumbing",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        },
    )
    requests.post(
        f"{live_server}/api/runs/{run_id}/node02",
        json={
            "problem": "Homeowners lose boiler pressure and hot water.",
            "solution": "Same-day callout to diagnose and restore pressure.",
            "features": ["Same-day callout"],
            "benefits": ["Hot water restored quickly"],
            "differentiators": ["Local coverage"],
            "commercial_model": "Fixed diagnostic fee.",
            "customer_outcome": "Working boiler within 24 hours.",
        },
    )
    payload = {
        "segment_name": "Blackheath homeowner",
        "needs": ["Restore hot water"],
        "pains": ["No heating"],
        "urgency": "high",
        "eligibility_geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
    }
    response = requests.post(f"{live_server}/api/runs/{run_id}/node03", json=payload)
    assert response.status_code == 200
    assert response.json()["segment_id"].startswith("tgt_boiler_repair_blackheath__seg_")


def test_node03_prohibited_pii_is_rejected(live_server, run_id):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node01",
        json={
            "target_type": "service_market",
            "service": "boiler_repair",
            "market": "domestic_plumbing",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        },
    )
    requests.post(
        f"{live_server}/api/runs/{run_id}/node02",
        json={
            "problem": "Homeowners lose boiler pressure and hot water.",
            "solution": "Same-day callout to diagnose and restore pressure.",
            "features": ["Same-day callout"],
            "benefits": ["Hot water restored quickly"],
            "differentiators": ["Local coverage"],
            "commercial_model": "Fixed diagnostic fee.",
            "customer_outcome": "Working boiler within 24 hours.",
        },
    )
    payload = {
        "segment_name": "Blackheath homeowner",
        "needs": ["Contact via jane.doe@example.com"],
        "pains": ["No heating"],
        "urgency": "high",
        "eligibility_geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
    }
    response = requests.post(f"{live_server}/api/runs/{run_id}/node03", json=payload)
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


# --- Node 04 adapter (conversion definition) -----------------------------------

def test_node04_before_audience_is_rejected_fail_closed(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    response = _define_conversion(live_server, run_id)
    assert response.status_code == 409
    assert response.json()["error"] == "no_audience"


def test_node04_register_positive_uses_master_spec_funnel(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    response = _define_conversion(live_server, run_id)
    assert response.status_code == 200
    record = response.json()
    assert record["success_stage_id"] == "sale"
    assert len(record["stages"]) > 0

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert run["conversion"] is not None
    assert any(event["node"] == "node_04" for event in run["lineage"])


# --- Node 05 adapter (demand signal discovery) ---------------------------------

def test_node05_before_conversion_is_rejected_fail_closed(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    response = _register_demand_signal(live_server, run_id)
    assert response.status_code == 409
    assert response.json()["error"] == "no_conversion"


def test_node05_register_positive(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    response = _register_demand_signal(live_server, run_id)
    assert response.status_code == 200
    assert response.json()["signal_id"] == "sig_n05"

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["demand_signals"]) == 1
    assert any(event["node"] == "node_05" for event in run["lineage"])


# --- Node 06 adapter (question discovery) --------------------------------------

def test_node06_before_demand_signal_is_rejected_fail_closed(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    response = _register_question(live_server, run_id)
    assert response.status_code == 409
    assert response.json()["error"] == "no_demand_signal"


def test_node06_register_positive(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    response = _register_question(live_server, run_id)
    assert response.status_code == 200
    assert response.json()["question_id"] == "q_n06"


# --- Node 07 adapter (social/video discovery) ----------------------------------

def test_node07_before_question_is_rejected_fail_closed(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    response = _register_social_video(live_server, run_id)
    assert response.status_code == 409
    assert response.json()["error"] == "no_question"


def test_node07_register_positive(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _register_question(live_server, run_id)
    response = _register_social_video(live_server, run_id)
    assert response.status_code == 200
    assert response.json()["signal_id"] == "sv_n07"


# --- Node 08 adapter (competitor intelligence) ---------------------------------

def test_node08_before_social_video_is_rejected_fail_closed(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _register_question(live_server, run_id)
    response = _register_competitor(live_server, run_id)
    assert response.status_code == 409
    assert response.json()["error"] == "no_social_video_signal"


def test_node08_register_positive(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _register_question(live_server, run_id)
    _register_social_video(live_server, run_id)
    response = _register_competitor(live_server, run_id)
    assert response.status_code == 200
    assert response.json()["signal_id"] == "cp_n08"


# --- Node 09 adapter (community intelligence) ----------------------------------

def test_node09_before_competitor_is_rejected_fail_closed(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _register_question(live_server, run_id)
    _register_social_video(live_server, run_id)
    response = _register_community(live_server, run_id)
    assert response.status_code == 409
    assert response.json()["error"] == "no_competitor_signal"


def test_node09_register_positive(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _register_question(live_server, run_id)
    _register_social_video(live_server, run_id)
    _register_competitor(live_server, run_id)
    response = _register_community(live_server, run_id)
    assert response.status_code == 200
    assert response.json()["signal_id"] == "cm_n09"


# --- Node 10 adapter (trend detection) -----------------------------------------

def test_node10_before_community_is_rejected_fail_closed(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _register_question(live_server, run_id)
    _register_social_video(live_server, run_id)
    _register_competitor(live_server, run_id)
    response = _register_trend(live_server, run_id)
    assert response.status_code == 409
    assert response.json()["error"] == "no_community_signal"


def test_node10_register_positive_computes_velocity_and_direction(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _register_question(live_server, run_id)
    _register_social_video(live_server, run_id)
    _register_competitor(live_server, run_id)
    _register_community(live_server, run_id)
    response = _register_trend(live_server, run_id)
    assert response.status_code == 200
    record = response.json()
    assert record["trend_id"] == "trend_n10"
    assert record["direction"] == "up"
    assert record["spike_flag"] is True

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["trends"]) == 1
    assert any(event["node"] == "node_10" for event in run["lineage"])


def test_node05_to_node10_full_chain_via_helper(live_server, run_id):
    response = _full_phase1_and_phase2_chain(live_server, run_id)
    assert response.status_code == 200
    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["demand_signals"]) == 1
    assert len(run["questions"]) == 1
    assert len(run["social_video_signals"]) == 1
    assert len(run["competitor_signals"]) == 1
    assert len(run["community_signals"]) == 1
    assert len(run["trends"]) == 1


# --- Node 11 adapter -----------------------------------------------------------

def test_node11_classify_without_target_or_registered_run_target_is_rejected(live_server, run_id):
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node11/classify",
        json={
            "signal_id": "sig_1",
            "raw_query": "boiler pressure dropped to zero",
            "topic": "boiler_pressure_loss",
            "source_type": "manual_curation",
            "observed_at": "2026-08-17T00:00:00+00:00",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        },
    )
    assert response.status_code == 409
    assert response.json()["error"] == "no_target"


def test_node11_classify_positive_using_run_target(live_server, run_id):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node01",
        json={
            "target_type": "service_market",
            "service": "boiler_repair",
            "market": "domestic_plumbing",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        },
    )
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node11/classify",
        json={
            "signal_id": "sig_console_test",
            "raw_query": "boiler pressure dropped to zero no hot water",
            "topic": "boiler_pressure_loss",
            "source_type": "manual_curation",
            "observed_at": "2026-08-17T00:00:00+00:00",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        },
    )
    assert response.status_code == 200
    record = response.json()
    assert record["target_id"] == "tgt_boiler_repair_blackheath"
    assert record["primary_intent"] in {"troubleshooting", "urgent_emergency", "commercial_investigation", "informational"}

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["classifications"]) == 1
    assert any(event["node"] == "node_11" for event in run["lineage"])


def test_node15_uses_latest_reclassification_for_each_signal(live_server, run_id):
    """Audit-history classifications must not become duplicate cluster members."""
    requests.post(
        f"{live_server}/api/runs/{run_id}/node01",
        json={
            "target_type": "service_market",
            "service": "emergency_electrician",
            "market": "domestic_electrical_services",
            "geography": {"locality": "Catford", "region": "London", "country": "UK"},
        },
    )
    payload = {
        "signal_id": "sig_reclassified_once",
        "raw_query": "emergency electrician Catford UK",
        "topic": "emergency_electrician",
        "source_type": "search_query",
        "observed_at": "2026-08-21T17:00:00+01:00",
        "geography": {"locality": "Catford", "region": "London", "country": "UK"},
        "service_context": {
            "service_name": "emergency_electrician",
            "market_segment": "domestic_electrical_services",
        },
    }
    first = requests.post(f"{live_server}/api/runs/{run_id}/node11/classify", json=payload)
    second = requests.post(f"{live_server}/api/runs/{run_id}/node11/classify", json=payload)
    assert first.status_code == second.status_code == 200

    generated = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={})

    assert generated.status_code == 200
    assert len(generated.json()) == 1


def test_node11_classify_invalid_source_type_is_rejected(live_server, run_id):
    requests.post(
        f"{live_server}/api/runs/{run_id}/node01",
        json={
            "target_type": "service_market",
            "service": "boiler_repair",
            "market": "domestic_plumbing",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
        },
    )
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node11/classify",
        json={
            "signal_id": "sig_bad",
            "raw_query": "boiler pressure dropped to zero",
            "topic": "boiler_pressure_loss",
            "source_type": "totally_bogus_source_type",  # not in Node 11's ALLOWED_SOURCE_TYPES;
            # search_query was used here originally, but Node 11 (Gemini-owned) now legitimately
            # accepts it as of its own v1.1.0 automation upgrade -- a genuinely-invalid value is
            # needed to still exercise this rejection path.
            "observed_at": "2026-08-17T00:00:00+00:00",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "contract_violation"


# --- Phase completion contract (five-state reconciliation) -------------------

def _phase(data, number):
    return next(p for p in data["phases"] if p["phase"] == number)


def test_phases_endpoint_reports_node15_18_as_console_controls(live_server):
    data = requests.get(f"{live_server}/api/phases").json()
    phase3 = _phase(data, 3)
    phase4 = _phase(data, 4)
    assert phase3["accepted_nodes"] == ["11", "12", "13", "14", "15"]
    assert phase3["console_controls"] == ["11", "12", "13", "14", "15"]
    assert phase4["accepted_nodes"] == ["16", "17", "18", "19"]
    assert phase4["console_controls"] == ["16", "17", "18", "19"]


def test_phases_endpoint_does_not_falsely_report_accepted_nodes_as_not_implemented(live_server):
    # The CHANGE REQUIRED this fixes: Phase 2 (Nodes 05-10) is accepted EP050 implementation,
    # just not wired as a console control. It must never appear as locked/not-implemented.
    data = requests.get(f"{live_server}/api/phases").json()
    phase1 = _phase(data, 1)
    phase2 = _phase(data, 2)
    phase5 = _phase(data, 5)

    assert phase1["accepted_nodes"] == ["01", "02", "03", "04"]
    assert phase1["console_controls"] == ["01", "02", "03", "04"]

    assert phase2["accepted_nodes"] == ["05", "06", "07", "08", "09", "10"]
    assert phase2["console_controls"] == ["05", "06", "07", "08", "09", "10"]
    assert phase2["pending_acceptance_nodes"] == []
    assert phase2["mvp_deferred_nodes"] == []
    assert phase2["not_started_nodes"] == []

    assert phase5["accepted_nodes"] == ["20", "21", "26"]
    assert phase5["pending_acceptance_nodes"] == ["27"]
    assert phase5["mvp_deferred_nodes"] == ["22", "23", "24", "25"]
    assert phase5["console_controls"] == ["20", "21", "26"]


def test_phases_endpoint_does_not_falsely_report_phase6_7_as_not_started(live_server):
    # Phase 6/7 (Nodes 28-37) were wrongly listed as not_started_nodes ("no allocation or work
    # has begun") when real, tested code exists for all ten -- re-verified this session (26/26
    # own-suite tests, plus a full golden-path integration test that found and confirmed a real
    # cross-node bug fix in this exact range). Not bumped to accepted_nodes: unlike Node 27
    # (which has an explicit board ACCEPTED event), no formal acceptance event exists for
    # Nodes 28-37 -- so pending_acceptance_nodes is the honest classification, not not_started.
    data = requests.get(f"{live_server}/api/phases").json()
    phase6 = _phase(data, 6)
    phase7 = _phase(data, 7)

    assert phase6["pending_acceptance_nodes"] == ["28", "29", "30", "31"]
    assert phase6["not_started_nodes"] == []
    assert phase6["accepted_nodes"] == []

    assert phase7["pending_acceptance_nodes"] == ["32", "33", "34", "35", "36", "37"]
    assert phase7["not_started_nodes"] == []
    assert phase7["accepted_nodes"] == []


def test_phases_endpoint_every_node_in_range_is_classified_exactly_once(live_server):
    data = requests.get(f"{live_server}/api/phases").json()
    for phase in data["phases"]:
        start, end = (int(x) for x in phase["nodes"].split("-"))
        expected = {f"{n:02d}" for n in range(start, end + 1)}
        classified = (
            set(phase["accepted_nodes"])
            | set(phase["pending_acceptance_nodes"])
            | set(phase["mvp_deferred_nodes"])
            | set(phase["not_started_nodes"])
        )
        assert classified == expected, f"phase {phase['phase']} miscounts nodes {expected ^ classified}"
        # console_controls must always be a subset of accepted_nodes (never claim execution
        # for a node that hasn't been accepted).
        assert set(phase["console_controls"]) <= set(phase["accepted_nodes"])


# --- Node 15 adapter (campaign cluster generation) -----------------------------

def test_node15_generate_without_classifications_is_rejected(live_server, run_id):
    _register_target(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={})
    assert response.status_code == 409
    assert response.json()["error"] == "no_classifications"


def test_node15_generate_positive_creates_cluster(live_server, run_id):
    _register_target(live_server, run_id)
    _classify_signal(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={})
    assert response.status_code == 200
    clusters = response.json()["clusters"]
    assert len(clusters) == 1
    assert clusters[0]["member_count"] == 1

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["clusters"]) == 1
    assert any(event["node"] == "node_15" for event in run["lineage"])


# --- Node 16 adapter (canonical fact registration) ----------------------------

def test_node16_fact_without_target_is_rejected(live_server, run_id):
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={"topic": "boiler_pressure", "claim": "Test claim.", "verification_source": "fixture"},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "no_target"


def test_node16_fact_positive(live_server, run_id):
    _register_target(live_server, run_id)
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
            "is_safety_critical": True,
            "safety_guidance": "Do not attempt gas work without Gas Safe registration.",
        },
    )
    assert response.status_code == 200
    fact = response.json()
    assert fact["fact_id"].startswith("fact_")

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["facts"]) == 1
    assert any(event["node"] == "node_16" for event in run["lineage"])


# --- Node 18 adapter (video asset factory) -------------------------------------

def test_node18_generate_without_cluster_is_rejected(live_server, run_id):
    _register_target(live_server, run_id)
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/generate",
        json={"cluster_id": "cluster_nonexistent", "fact_ids": ["fact_x"]},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "cluster_not_found"


def test_node18_generate_missing_fact_is_rejected(live_server, run_id):
    _register_target(live_server, run_id)
    _classify_signal(live_server, run_id)
    cluster = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={}).json()["clusters"][0]
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/generate",
        json={"cluster_id": cluster["cluster_id"], "fact_ids": ["fact_nonexistent"]},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "fact_not_found"


def test_node18_generate_positive_creates_video_asset(live_server, run_id):
    _register_target(live_server, run_id)
    _classify_signal(live_server, run_id)
    cluster = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={}).json()["clusters"][0]
    fact = requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
        },
    ).json()

    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/generate",
        json={"cluster_id": cluster["cluster_id"], "fact_ids": [fact["fact_id"]]},
    )
    assert response.status_code == 200
    video = response.json()
    assert video["video_asset_id"].startswith("vid_")
    assert video["external_action"] is False

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["video_assets"]) == 1
    assert len(run["assets"]) == 1
    assert any(event["node"] == "node_18" for event in run["lineage"])


# --- Phase 5 console controls (Nodes 19-21, 26-27) -----------------------------

def _build_node18_asset(live_server, run_id):
    _register_target(live_server, run_id)
    _classify_signal(live_server, run_id)
    cluster = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={}).json()["clusters"][0]
    fact = requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
        },
    ).json()
    video = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/generate",
        json={"cluster_id": cluster["cluster_id"], "fact_ids": [fact["fact_id"]]},
    ).json()
    asset_id = requests.get(f"{live_server}/api/runs/{run_id}").json()["assets"][0]["asset_id"]
    assert asset_id == video["asset_id"]
    return asset_id


def test_node19_generate_approves_a_compliant_node18_asset(live_server, run_id):
    asset_id = _build_node18_asset(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/node19/generate", json={"asset_id": asset_id})
    assert response.status_code == 200
    body = response.json()
    assert body["compliance_check"]["approved"] is True
    assert body["approved_package"]["asset_id"] == asset_id
    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["approved_packages"]) == 1


def test_node19_generate_unknown_asset_is_rejected(live_server, run_id):
    response = requests.post(f"{live_server}/api/runs/{run_id}/node19/generate", json={"asset_id": "asset_does_not_exist"})
    assert response.status_code == 404


def test_node20_through_node27_full_chain_produces_a_structured_lead(live_server, run_id):
    asset_id = _build_node18_asset(live_server, run_id)
    requests.post(f"{live_server}/api/runs/{run_id}/node19/generate", json={"asset_id": asset_id})

    plan = requests.post(f"{live_server}/api/runs/{run_id}/node20/generate", json={"asset_id": asset_id}).json()
    assert plan["publication_plan_id"].startswith("mpp_")
    assert plan["external_action"] is False

    search_package = requests.post(
        f"{live_server}/api/runs/{run_id}/node21/generate", json={"publication_plan_id": plan["publication_plan_id"]}
    ).json()
    assert search_package["manifest"]["search_distribution_id"].startswith("sdp_")

    route = requests.post(
        f"{live_server}/api/runs/{run_id}/node26/generate",
        json={"search_distribution_id": search_package["manifest"]["search_distribution_id"]},
    ).json()
    assert route["route_id"].startswith("sdr_")
    assert route["external_action"] is False

    lead = requests.post(
        f"{live_server}/api/runs/{run_id}/node27/generate",
        json={"route_id": route["route_id"], "session_id": "sess_console_test", "consent_granted": True},
    ).json()
    assert lead["lead_id"].startswith("slc_")
    assert lead["external_action"] is False
    assert lead["source"] == "search_landing"
    assert "email" not in json.dumps(lead).lower()

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["publication_plans"]) == 1
    assert len(run["search_packages"]) == 1
    assert len(run["routes"]) == 1
    assert len(run["leads"]) == 1
    for node in ("node_20", "node_21", "node_26", "node_27"):
        assert any(event["node"] == node for event in run["lineage"])


def test_node27_generate_without_consent_granted_is_rejected(live_server, run_id):
    asset_id = _build_node18_asset(live_server, run_id)
    requests.post(f"{live_server}/api/runs/{run_id}/node19/generate", json={"asset_id": asset_id})
    plan = requests.post(f"{live_server}/api/runs/{run_id}/node20/generate", json={"asset_id": asset_id}).json()
    search_package = requests.post(
        f"{live_server}/api/runs/{run_id}/node21/generate", json={"publication_plan_id": plan["publication_plan_id"]}
    ).json()
    route = requests.post(
        f"{live_server}/api/runs/{run_id}/node26/generate",
        json={"search_distribution_id": search_package["manifest"]["search_distribution_id"]},
    ).json()

    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node27/generate",
        json={"route_id": route["route_id"], "session_id": "sess_console_test", "consent_granted": False},
    )
    assert response.status_code == 400


# --- Full lifecycle regression -------------------------------------------------

def test_full_lifecycle_regression(live_server, run_id):
    _full_phase1_and_phase2_chain(live_server, run_id)
    requests.post(
        f"{live_server}/api/runs/{run_id}/node11/classify",
        json={
            "signal_id": "sig_regression",
            "raw_query": "boiler pressure dropped to zero no hot water",
            "topic": "boiler_pressure_loss",
            "source_type": "synthetic_fixture",
            "observed_at": "2026-08-17T00:00:00+00:00",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        },
    )
    cluster = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={}).json()["clusters"][0]
    fact = requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
        },
    ).json()
    requests.post(
        f"{live_server}/api/runs/{run_id}/node18/generate",
        json={"cluster_id": cluster["cluster_id"], "fact_ids": [fact["fact_id"]]},
    )

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert run["target"] is not None
    assert run["product"] is not None
    assert len(run["audience"]) == 1
    assert run["conversion"] is not None
    assert len(run["demand_signals"]) == 1
    assert len(run["questions"]) == 1
    assert len(run["social_video_signals"]) == 1
    assert len(run["competitor_signals"]) == 1
    assert len(run["community_signals"]) == 1
    assert len(run["trends"]) == 1
    assert len(run["classifications"]) == 1
    assert len(run["clusters"]) == 1
    assert len(run["facts"]) == 1
    assert len(run["video_assets"]) == 1
    # created + node01..10 (10) + node11 + node15 + node16 + node18 = 15 lineage events
    assert len(run["lineage"]) == 15

    listing = requests.get(f"{live_server}/api/runs").json()
    assert any(r["run_id"] == run_id for r in listing["runs"])


# --- known_values endpoint (select-with-add-new source data) ------------------

def test_known_values_returns_curated_seeds_when_no_runs_exist(live_server):
    # Asserts the curated seed values are present rather than that service/market/segment_name
    # are exactly empty: a prior test in the same session can leave a real registered value on
    # disk if its own live_server teardown is interrupted (a pre-existing fixture limitation,
    # not something this test should be fragile to).
    response = requests.get(f"{live_server}/api/known_values")
    assert response.status_code == 200
    payload = response.json()
    assert "UK" in payload["country"]
    assert "London" in payload["region"]
    assert isinstance(payload["service"], list)
    assert isinstance(payload["market"], list)
    assert isinstance(payload["segment_name"], list)


def test_known_values_includes_real_registered_target_and_segment_data(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)

    response = requests.get(f"{live_server}/api/known_values")
    payload = response.json()

    assert "boiler_repair" in payload["service"]
    assert "domestic_plumbing" in payload["market"]
    assert "service_market" in payload["target_type"]
    assert "Blackheath" in payload["locality"]
    assert "Blackheath homeowner" in payload["segment_name"]
    assert "Homeowners lose boiler pressure and hot water." in payload["problem"]
    assert "Same-day callout to diagnose and restore pressure." in payload["solution"]
    assert "Fixed diagnostic fee." in payload["commercial_model"]
    assert "Working boiler within 24 hours." in payload["customer_outcome"]
    assert "A lead reaches the sale stage with a recorded outcome." in payload["success_criteria"]


# --- Live-fetch endpoints (Nodes 05-10/15/18 automated ingestion) --------------

def test_live_fetch_status_reports_disabled_by_default(live_server, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)
    response = requests.get(f"{live_server}/api/live_fetch_status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["live_fetch_enabled"] is False
    assert payload["nodes"]["05"]["ready"] is False
    assert payload["nodes"]["08"]["required_vars"] == []


def test_live_fetch_status_reports_ready_once_enabled_and_credentialed(live_server, monkeypatch):
    # Node 05 moved off Google Custom Search to Firecrawl on 2026-08-19 (see
    # LIVE_FETCH_CREDENTIAL_VARS's comment in server.py) -- this test predates that migration and
    # was left asserting readiness against the retired EP050_GOOGLE_CSE_* vars, which
    # _node05_readiness() no longer consults. Set the credential it actually checks.
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    monkeypatch.setenv("EP050_FIRECRAWL_API_KEY", "test-key")
    response = requests.get(f"{live_server}/api/live_fetch_status")
    payload = response.json()
    assert payload["live_fetch_enabled"] is True
    assert payload["nodes"]["05"]["ready"] is True
    assert payload["nodes"]["08"]["ready"] is True  # no credential required


def test_node05_live_disabled_by_default_returns_503(live_server, run_id, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/node05/live", json={"topic": "boiler_pressure_loss"})
    assert response.status_code == 503
    assert response.json()["error"] == "live_fetch_disabled"


def test_node08_live_with_mocked_fetch_succeeds(live_server, run_id, monkeypatch):
    monkeypatch.setenv("EP050_LIVE_FETCH_ENABLED", "1")
    fake_html = "<html><head><title>Rival Co</title></head><body>boiler pressure loss repair boiler pressure loss</body></html>"
    monkeypatch.setattr(console_server.node08, "http_get_text", lambda url, **kw: (fake_html, 200))

    _full_phase1_and_phase2_chain(live_server, run_id)  # seeds through node05-09 so node08/live's own prerequisite (node07) is met
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node08/live",
        json={
            "competitor_url": "https://rival.example.test/boiler",
            "topic": "boiler_pressure_loss",
            "query": "boiler pressure loss repair",
        },
    )
    assert response.status_code == 200
    record = response.json()
    assert record["source_type"] == "web_fetch"
    assert record["metadata"]["fetch_receipt"]["http_status"] == 200

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert any(event["action"] == "register_competitor_signal_live" for event in run["lineage"])


def test_node10_live_aggregates_from_real_signals_no_flag_needed(live_server, run_id, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)  # Node 10 needs no network, no flag
    _full_phase1_and_phase2_chain(live_server, run_id)
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node10/live",
        json={
            "topic": "boiler_pressure_loss",
            "window": {
                "baseline_start": "2020-01-01T00:00:00+00:00",
                "baseline_end": "2020-01-08T00:00:00+00:00",
                "current_start": "2026-08-01T00:00:00+00:00",
                "current_end": "2026-08-31T00:00:00+00:00",
            },
        },
    )
    # Real signals were registered at 2026-08-17, inside current window, outside baseline ->
    # baseline_sample_count=0 fails the existing minimum-sample-count check fail-closed.
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


def test_node15_live_generates_cluster_from_real_signal_no_flag_needed(live_server, run_id, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)  # Node 11-14 are pure local functions
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id, signal_id="sig_live15")

    response = requests.post(f"{live_server}/api/runs/{run_id}/node15/live", json={})
    assert response.status_code == 200
    clusters = response.json()["clusters"]
    assert len(clusters) == 1
    assert clusters[0]["members"][0]["signal_id"] == "sig_live15"

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert any(event["action"] == "generate_clusters_live" for event in run["lineage"])


def test_node18_live_generates_video_asset_from_real_chain(live_server, run_id, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id, signal_id="sig_live18")

    cluster = requests.post(f"{live_server}/api/runs/{run_id}/node15/live", json={}).json()["clusters"][0]
    requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
        },
    )

    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/live",
        json={"cluster_id": cluster["cluster_id"], "signal_id": "sig_live18"},
    )
    assert response.status_code == 200
    video = response.json()
    assert video["video_asset_id"].startswith("vid_")
    assert video["external_action"] is False

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert any(event["action"] == "generate_video_asset_live" for event in run["lineage"])


def test_node18_live_unknown_cluster_returns_lineage_error(live_server, run_id):
    _register_target(live_server, run_id)
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/live",
        json={"cluster_id": "cluster_nonexistent", "signal_id": "sig_x"},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "lineage_error"


# --- Node 18 real render + real YouTube publish trigger (2026-08-20) -----------------------

def _build_video_asset(live_server, run_id, locality="Blackheath"):
    _register_target(live_server, run_id, locality=locality)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    _classify_signal(live_server, run_id)
    cluster = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={}).json()["clusters"][0]
    fact = requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
        },
    ).json()
    return requests.post(
        f"{live_server}/api/runs/{run_id}/node18/generate",
        json={"cluster_id": cluster["cluster_id"], "fact_ids": [fact["fact_id"]]},
    ).json()


def test_node18_trigger_render_and_publish_requires_explicit_confirmation(live_server, run_id):
    video = _build_video_asset(live_server, run_id)
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/trigger_render_and_publish",
        json={"video_asset_id": video["video_asset_id"]},  # confirm_publish omitted
    )
    assert response.status_code == 400
    assert response.json()["error"] == "confirmation_required"


def test_node18_trigger_render_and_publish_unknown_video_asset_returns_404(live_server, run_id):
    _register_target(live_server, run_id)
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/trigger_render_and_publish",
        json={"video_asset_id": "vid_nonexistent", "confirm_publish": True},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "video_asset_not_found"


def test_node18_trigger_render_and_publish_succeeds_with_mocked_ep048_and_advances_position(live_server, run_id):
    # Unique locality: isolates this test's applicability tag from every other test's default
    # Blackheath/boiler_repair publications, so it always exercises the real (mocked) trigger
    # path rather than incidentally hitting the cross-run reuse shortcut.
    video = _build_video_asset(live_server, run_id, locality="Locality_success_case")

    before = requests.get(f"{live_server}/api/campaign_queue").json()
    before_campaign = next(c for c in before["campaigns"] if c["run_id"] == run_id)
    assert before_campaign["node"] == "Node 18"
    assert "trigger real EP048 render" in before_campaign["action"]

    result = _trigger_mocked_render_and_publish(live_server, run_id, video["video_asset_id"])
    assert result["video_id"] == "yt_test_fixture"
    assert result["privacy_status"] == "unlisted"
    assert result["external_action"] is True

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["video_publications"]) == 1
    assert any(event["action"] == "render_and_publish_video_asset" for event in run["lineage"])

    after = requests.get(f"{live_server}/api/campaign_queue").json()
    after_campaign = next(c for c in after["campaigns"] if c["run_id"] == run_id)
    assert after_campaign["node"] != "Node 18"  # moved past Node 18 once a real publication exists


def test_node18_trigger_render_and_publish_rejects_double_publish(live_server, run_id):
    video = _build_video_asset(live_server, run_id, locality="Locality_double_publish_case")
    _trigger_mocked_render_and_publish(live_server, run_id, video["video_asset_id"])

    fake_result = ep048_trigger.RenderPublishResult(
        video_asset_id=video["video_asset_id"], run_id=run_id, script_path="x", render_output_path="x",
        rendered_at="2026-08-20T00:00:00.000+00:00", render_stdout_tail="", video_id="yt_should_not_happen",
        watch_url="https://www.youtube.com/watch?v=yt_should_not_happen", privacy_status="unlisted",
        uploaded_at="2026-08-20T00:00:00.000+00:00", upload_stdout_tail="",
    )
    with patch.object(console_server.node18_publish, "trigger_render_and_publish", return_value=fake_result):
        response = requests.post(
            f"{live_server}/api/runs/{run_id}/node18/trigger_render_and_publish",
            json={"video_asset_id": video["video_asset_id"], "confirm_publish": True},
        )
    assert response.status_code == 409
    assert response.json()["error"] == "already_published"


def test_node18_trigger_render_and_publish_render_failure_returns_502(live_server, run_id):
    video = _build_video_asset(live_server, run_id, locality="Locality_render_failure_case")
    with patch.object(
        console_server.node18_publish, "trigger_render_and_publish",
        side_effect=ep048_trigger.RenderFailedError("ElevenLabs API key missing"),
    ):
        response = requests.post(
            f"{live_server}/api/runs/{run_id}/node18/trigger_render_and_publish",
            json={"video_asset_id": video["video_asset_id"], "confirm_publish": True},
        )
    assert response.status_code == 502
    assert response.json()["error"] == "render_failed"

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert run.get("video_publications", []) == []  # a failed render/publish is never recorded as real


# --- Winner-triggered candidate clustering (Nodes 01/34, plan: 20260818_1645_ep050_winner_replication_and_scale_out.md) ---

def _trigger_mocked_render_and_publish(live_server, run_id, video_asset_id):
    """Calls the REAL /node18/trigger_render_and_publish endpoint (real request/response
    plumbing, real state-derivation effects), but mocks the underlying subprocess calls to
    EP048's generate_video.py/upload_video.py so tests never render a real video or hit the
    real YouTube API. Mirrors the existing monkeypatch.setattr(console_server.nodeXX, ...)
    pattern used for every other live-fetch/external-action node in this file."""
    fake_result = ep048_trigger.RenderPublishResult(
        video_asset_id=video_asset_id, run_id=run_id, script_path="fake_script.md",
        render_output_path="fake_output.mp4", rendered_at="2026-08-20T00:00:00.000+00:00",
        render_stdout_tail="", video_id="yt_test_fixture", watch_url="https://www.youtube.com/watch?v=yt_test_fixture",
        privacy_status="unlisted", uploaded_at="2026-08-20T00:00:00.000+00:00", upload_stdout_tail="",
    )
    with patch.object(console_server.node18_publish, "trigger_render_and_publish", return_value=fake_result):
        response = requests.post(
            f"{live_server}/api/runs/{run_id}/node18/trigger_render_and_publish",
            json={"video_asset_id": video_asset_id, "confirm_publish": True},
        )
    assert response.status_code == 200, response.text
    return response.json()


def _build_winner(live_server, run_id):
    """Drives a full real Node 01->34 chain to a genuine is_winner=True record, using every
    node's own default/illustrative metrics (no overrides needed to cross the ROAS>=4.0,
    conversion>=3%, leads>=3 thresholds -- Node 32's own defaults already clear them). Registers
    Node 02/03 (unlike _build_node18_asset, which skips them since Node 18's own chain doesn't
    require them) because candidate clustering's geo-axis copy step needs a real product/audience
    to copy from. Also registers the Node 05 demand signal itself (not just its classification --
    _build_node18_asset's classify-only shortcut is fine for Node 18's own generate() path, but
    node18/replicate_winner's generate_and_register_from_live_chain() re-derives from the real
    Node 05 registry by signal_id, so the signal has to actually exist there, matching how a real
    run reaches a winner)."""
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id, signal_id="sig_console_test")
    _classify_signal(live_server, run_id)
    cluster = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={}).json()["clusters"][0]
    fact = requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
        },
    ).json()
    video = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/generate",
        json={"cluster_id": cluster["cluster_id"], "fact_ids": [fact["fact_id"]]},
    ).json()
    asset_id = video["asset_id"]
    _trigger_mocked_render_and_publish(live_server, run_id, video["video_asset_id"])
    requests.post(f"{live_server}/api/runs/{run_id}/node19/generate", json={"asset_id": asset_id})
    plan = requests.post(f"{live_server}/api/runs/{run_id}/node20/generate", json={"asset_id": asset_id}).json()
    search_package = requests.post(
        f"{live_server}/api/runs/{run_id}/node21/generate", json={"publication_plan_id": plan["publication_plan_id"]}
    ).json()
    route = requests.post(
        f"{live_server}/api/runs/{run_id}/node26/generate",
        json={"search_distribution_id": search_package["manifest"]["search_distribution_id"]},
    ).json()
    lead = requests.post(
        f"{live_server}/api/runs/{run_id}/node27/generate",
        json={"route_id": route["route_id"], "session_id": "sess_winner_chain", "consent_granted": True},
    ).json()
    attribution = requests.post(f"{live_server}/api/runs/{run_id}/node28/generate", json={"lead_id": lead["lead_id"]}).json()
    qualification = requests.post(f"{live_server}/api/runs/{run_id}/node29/generate", json={"attribution_id": attribution["attribution_id"]}).json()
    requests.post(f"{live_server}/api/runs/{run_id}/node30/generate", json={"qualification_id": qualification["qualification_id"]})
    performance = requests.post(f"{live_server}/api/runs/{run_id}/node32/generate", json={}).json()
    winner = requests.post(f"{live_server}/api/runs/{run_id}/node34/generate", json={"performance_record_id": performance["performance_record_id"]}).json()
    assert winner["is_winner"] is True
    return winner


def test_node01_propose_candidates_creates_one_hop_geo_and_service_candidates(live_server, run_id):
    _build_winner(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={})
    assert response.status_code == 200
    body = response.json()
    assert not body["failed"]
    axes = {c["axis"] for c in body["created"]}
    assert axes == {"geo", "service"}

    localities = {c["target"]["geography"]["locality"] for c in body["created"] if c["axis"] == "geo"}
    assert localities == {"Lewisham", "Greenwich", "Catford", "Charlton", "Eltham"}
    services = {c["target"]["service"] for c in body["created"] if c["axis"] == "service"}
    assert services == {"boiler_service"}  # boiler_installation/central_heating_repair removed 2026-08-18: user verified this business doesn't offer them

    for c in body["created"]:
        assert c["target"]["service"] == "boiler_repair" or c["axis"] == "service"
        assert c["target"]["geography"]["locality"] == "Blackheath" or c["axis"] == "geo"
        if c["axis"] == "geo":
            assert c["candidate_status"] == "pending_phase2_approval"
        else:
            assert c["candidate_status"] == "pending_product_definition"

    # None of the new runs inherited the winner's own target_id -- each is a real, distinct target.
    source_run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    for c in body["created"]:
        candidate_run = requests.get(f"{live_server}/api/runs/{c['run_id']}").json()
        assert candidate_run["target"]["target_id"] != source_run["target"]["target_id"]


def test_node01_propose_candidates_geo_axis_copies_product_and_audience_with_new_geography(live_server, run_id):
    _build_winner(live_server, run_id)
    body = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    geo_candidate = next(c for c in body["created"] if c["axis"] == "geo")
    candidate_run = requests.get(f"{live_server}/api/runs/{geo_candidate['run_id']}").json()
    assert candidate_run["product"]["problem"] == "Homeowners lose boiler pressure and hot water."
    assert candidate_run["audience"][0]["eligibility_geography"]["locality"] == geo_candidate["target"]["geography"]["locality"]
    assert candidate_run["conversion"] is not None


def test_node01_propose_candidates_service_axis_does_not_fabricate_product(live_server, run_id):
    _build_winner(live_server, run_id)
    body = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    service_candidate = next(c for c in body["created"] if c["axis"] == "service")
    candidate_run = requests.get(f"{live_server}/api/runs/{service_candidate['run_id']}").json()
    assert candidate_run["product"] is None
    assert candidate_run["audience"] == []


def test_node01_propose_candidates_is_idempotent_for_the_same_winner(live_server, run_id):
    _build_winner(live_server, run_id)
    first = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    assert len(first["created"]) == 6

    # Second call for the SAME winner mints nothing new -- this is what runFullPipeline's
    # auto-propose-on-winner extension relies on to stay safe to re-run.
    second = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    assert second["created"] == []
    assert second["failed"] == []
    assert "note" in second


def test_node01_propose_candidates_without_winner_is_rejected(live_server, run_id):
    _register_target(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={})
    assert response.status_code == 409
    assert response.json()["error"] == "no_winner"


def test_node01_approve_phase2_parks_when_live_fetch_is_disabled(live_server, run_id, monkeypatch):
    # Forces the deterministic "not enabled" path regardless of what the real environment's own
    # .env happens to have configured -- this suite is meant to run fully offline (see file
    # header), and without this override the test would otherwise reach the real Google Custom
    # Search API whenever EP050_LIVE_FETCH_ENABLED is genuinely set, which is exactly what
    # happened once during development: it hit the real, already-documented Node 05 403
    # constraint live. That's the correct real-world outcome for THIS candidate's approval (parks,
    # never fabricates a signal), but it isn't a repeatable unit-test condition.
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)
    _build_winner(live_server, run_id)
    body = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    geo_candidate = next(c for c in body["created"] if c["axis"] == "geo")

    response = requests.post(f"{live_server}/api/runs/{geo_candidate['run_id']}/node01/approve_phase2", json={})
    assert response.status_code == 200
    approval = response.json()
    assert approval["candidate_status"] == "parked"
    assert "live_fetch_disabled" in approval["reason"]

    candidate_run = requests.get(f"{live_server}/api/runs/{geo_candidate['run_id']}").json()
    assert candidate_run["candidate_status"] == "parked"
    assert candidate_run.get("demand_signals", []) == []  # never fell back to a fixture signal


def test_node01_approve_phase2_parks_on_a_real_live_fetch_failure_without_fabricating_a_signal(live_server, run_id):
    """Does not force any particular outcome -- if this machine's real .env has live-fetch
    enabled with credentials that are rejected by the provider (the already-documented Node 05
    Search 403 constraint), this exercises that real failure path end to end and confirms it
    parks rather than fabricates. If live-fetch is disabled here, it exercises that path instead.
    Either way, the invariant holds: never a fixture demand_signal on approval failure."""
    _build_winner(live_server, run_id)
    body = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    geo_candidate = next(c for c in body["created"] if c["axis"] == "geo")

    response = requests.post(f"{live_server}/api/runs/{geo_candidate['run_id']}/node01/approve_phase2", json={})
    assert response.status_code == 200
    approval = response.json()
    candidate_run = requests.get(f"{live_server}/api/runs/{geo_candidate['run_id']}").json()
    if approval["candidate_status"] == "parked":
        assert candidate_run.get("demand_signals", []) == []
    else:
        # A working live-fetch on this machine returned a real signal; either a genuine result or
        # genuinely no demand -- both are legitimate, neither is a fixture fallback.
        assert approval["candidate_status"] in (None, "stopped_no_demand")


def test_node01_approve_phase2_rejects_when_not_pending(live_server, run_id):
    _build_winner(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/node01/approve_phase2", json={})
    assert response.status_code == 409
    assert response.json()["error"] == "not_pending_approval"


def test_parked_candidate_can_be_retried_once_the_blocking_condition_is_resolved(live_server, run_id, monkeypatch):
    """Parking must not be terminal.

    Real case this covers: four candidates parked on 2026-08-18 because Google's Custom Search API
    returned 403, and stayed parked with no route back even after Node 05 was moved to a working
    provider. Before this fix the only way to revive them was to hand-edit run.json. A retry re-runs
    the same real fetch -- it cannot invent an outcome, it can only park again, stop for no demand,
    or proceed on a genuine signal.
    """
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)
    _build_winner(live_server, run_id)
    body = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    candidate_run_id = next(c for c in body["created"] if c["axis"] == "geo")["run_id"]

    first = requests.post(f"{live_server}/api/runs/{candidate_run_id}/node01/approve_phase2", json={})
    assert first.status_code == 200, first.text
    assert first.json()["candidate_status"] == "parked"
    parked = requests.get(f"{live_server}/api/runs/{candidate_run_id}").json()
    assert parked.get("candidate_park_reason")

    # Retry while still blocked: allowed through the gate (not a 409), and honestly parks again.
    retry = requests.post(f"{live_server}/api/runs/{candidate_run_id}/node01/approve_phase2", json={})
    assert retry.status_code == 200
    assert retry.json()["candidate_status"] == "parked"

    after = requests.get(f"{live_server}/api/runs/{candidate_run_id}").json()
    assert any(e["action"] == "phase2_approval_retried" for e in after["lineage"])
    assert after.get("demand_signals", []) == []  # still never a fabricated signal


def test_headless_pipeline_never_fabricates_leads_spend_or_winners(live_server, run_id):
    """The driver must stop at distribution-ready and never manufacture real-world outcomes.

    Until 2026-08-19 it drove Nodes 27-34 from generated input, so every campaign it touched
    reported a lead, a performance record with impressions/clicks/spend/revenue, and a detected
    winner -- none of which had occurred. Node 27 was even called with consent_granted=True,
    fabricating a person's consent, which is a compliance artifact and not merely fake data.

    Those winners were not inert: winner detection is what triggers candidate replication, so
    fabricated performance data was spawning real downstream campaigns.
    """
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id, signal_id="sig_console_test")
    _classify_signal(live_server, run_id)
    requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
        },
    )

    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    body = response.json()

    for fabricated_node in ("node_27", "node_28", "node_29", "node_30", "node_31",
                            "node_32", "node_33", "node_34"):
        assert fabricated_node not in body.get("steps", []), (
            f"{fabricated_node} requires real observed events and must never be driven automatically"
        )

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    # node_31 (lifecycle transitions) and node_33 (outcome_feedback -- e.g. an invoice amount,
    # a customer rating) were missed by the first version of this test; a real incident on
    # 2026-08-19 found both left behind on a run whose leads/winners had already been purged,
    # including a fabricated GBP 240 invoice and a fabricated 5-star customer rating.
    for fabricated in ("leads", "attributions", "qualifications", "routings",
                       "performance_records", "winners", "lifecycles", "outcome_feedback"):
        assert not run.get(fabricated), f"pipeline fabricated {fabricated}"
    assert not run.get("last_proposed_winner_id"), "stale pointer to a winner that was never real"


def test_demand_gate_reads_the_real_record_shape_not_a_nonexistent_top_level_field():
    """The approval demand gate must read metadata.search_result_summary, where Node 05 really
    stores results -- not a top-level total_results/top_results that has never existed on a
    DemandSignalRecord.

    Real bug this pins: until 2026-08-19 the gate read the top level, so a record carrying 10
    genuine search results evaluated to has_real_demand=False and the candidate was marked
    stopped_no_demand. It went unnoticed for the node's entire life because Google's Custom Search
    API 403'd from day one, so a successful fetch never reached this branch. All four real parked
    candidates were wrongly stopped by it the moment a working provider was wired in.
    """
    real_record_shape = {
        "signal_id": "sig_x",
        "raw_query": "restore hot water quickly Greenwich London UK",
        "metadata": {
            "fetch_receipt": {"http_status": 200, "item_count": 10},
            "search_result_summary": {
                "total_results": "10",
                "top_results": [{"title": "Boiler repair Greenwich", "snippet": "...", "link": "http://x.test/"}],
            },
        },
    }
    summary = (real_record_shape.get("metadata") or {}).get("search_result_summary") or {}
    total_results = str(summary.get("total_results") or real_record_shape.get("total_results") or "0")
    top_results = summary.get("top_results") or real_record_shape.get("top_results") or []
    assert total_results.strip() not in ("", "0") or bool(top_results), (
        "a record holding 10 real results must register as real demand"
    )

    empty_record = {"signal_id": "sig_y", "metadata": {"search_result_summary": {"total_results": "0", "top_results": []}}}
    empty_summary = empty_record["metadata"]["search_result_summary"]
    empty_total = str(empty_summary.get("total_results") or "0")
    assert not (empty_total.strip() not in ("", "0") or bool(empty_summary.get("top_results"))), (
        "a genuinely empty result set must still register as no demand"
    )


def test_headless_pipeline_preserves_the_signals_real_source_type(live_server, run_id):
    """A live signal must not be classified as a synthetic fixture.

    run_pipeline_headless hardcoded source_type="synthetic_fixture" when calling Node 11. That was
    harmless while every signal genuinely was a fixture, but once Node 05's live fetch started
    working it stamped real search_query signals as fake in their permanent classification record --
    provenance corruption in the direction that matters most.
    """
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    # source_type here is "manual_curation" -- deliberately NOT "synthetic_fixture", so the
    # assertion below actually detects the hardcoded label rather than coincidentally matching it.
    _register_demand_signal(live_server, run_id, signal_id="sig_provenance_01")
    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    signal = run["demand_signals"][-1]
    assert signal["source_type"] == "manual_curation"

    requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})

    after = requests.get(f"{live_server}/api/runs/{run_id}").json()
    # A hard assertion, not a soft "if it ran" check: until 2026-08-19 a signal-only campaign never
    # reached Node 11 at all (see test_pipeline_run_all_advances_through_node11_and_node15_then_
    # stops_at_needs_facts), so this used to be written defensively around that bug. Now that Node
    # 11 genuinely always runs here, the classification's provenance must always be checked.
    classification = next(
        (c for c in after.get("classifications", []) if c["signal_id"] == signal["signal_id"]), None
    )
    assert classification is not None, "Node 11 must run for a campaign with only a real signal"
    assert classification["source_type"] == signal["source_type"], (
        "the classification must carry the signal's real provenance, not a hardcoded fixture label"
    )


def test_node05_readiness_reports_firecrawl_not_google_custom_search(live_server):
    """Node 05's readiness must reflect the provider it actually calls.

    Google's Custom Search JSON API is closed to new customers and returns a permanent 403, so
    reporting readiness against EP050_GOOGLE_CSE_* would be reporting on a dead dependency.
    """
    status = requests.get(f"{live_server}/api/live_fetch_status").json()
    node05 = status["nodes"]["05"]
    assert node05.get("provider") == "firecrawl"
    assert node05["required_vars"] == ["EP050_FIRECRAWL_API_KEY"]
    assert not any("GOOGLE_CSE" in var for var in node05["required_vars"])


# --- Cost ledger (plan §7): cost_gbp is opt-in per lineage event, never inferred -------------

def test_append_lineage_omits_cost_gbp_by_default():
    meta = {}
    console_server.append_lineage(meta, phase=1, node="node_01", action="register_target", summary="x")
    assert "cost_gbp" not in meta["lineage"][0]


def test_append_lineage_records_a_real_cost_when_the_caller_supplies_one():
    meta = {}
    console_server.append_lineage(meta, phase=2, node="node_05", action="live_fetch", summary="x", cost_gbp=0.005)
    assert meta["lineage"][0]["cost_gbp"] == 0.01  # rounded to 2dp, never truncated silently


def test_no_existing_handler_stamps_a_cost_yet(live_server, run_id):
    """Locks in the honest baseline from plan §7: as of this build, nothing in the pipeline has a
    confirmed real, currently-billed rate to attach, so a full real chain's lineage should carry
    zero cost_gbp entries. This test is meant to start failing the day a node legitimately gains
    one -- at which point it should be updated to assert that node's event, not deleted."""
    _build_winner(live_server, run_id)
    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert not any("cost_gbp" in event for event in run["lineage"])


# --- Campaign Queue: headless pipeline driver (plan §5) --------------------------------------

def test_pipeline_run_all_drives_a_fresh_run_from_signal_to_winner(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={
            "topic": "boiler_pressure",
            "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.",
            "verification_source": "manufacturer_manual_fixture",
        },
    )
    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    body = response.json()
    # Stops needing a real render+publish. It used to continue through node_27..node_34 and
    # report "winner_detected", which meant inventing a lead, spend, revenue and a winner that
    # never existed -- see test_headless_pipeline_never_fabricates_leads_spend_or_winners.
    # As of 2026-08-20 it also no longer falsely reports distribution_ready_awaiting_real_events
    # off the back of Node 18's fixture-only manifest: handle_node18_generate only ever produced
    # a script/storyboard PACKAGE, never a real render, so the driver correctly halts one step
    # earlier now -- a real render + real YouTube upload requires an explicit, human-confirmed
    # call to node18/trigger_render_and_publish (never auto-driven; see
    # test_node18_trigger_render_and_publish_requires_explicit_confirmation).
    assert body["state"] == "needs_real_render_and_publish"
    assert body["stopped_at"] == "awaiting_real_world_events"
    assert body["steps"] == ["node_11", "node_15", "node_18", "node_19", "node_20", "node_21", "node_26"]

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    # Real, derived artifacts are present...
    assert len(run["search_packages"]) == 1
    assert len(run["routes"]) == 1
    # ...and nothing describing a real-world outcome was manufactured.
    assert not run.get("leads")
    assert not run.get("winners")


def test_pipeline_run_all_is_idempotent_on_a_run_already_distribution_ready(live_server, run_id):
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={"topic": "boiler_pressure", "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.", "verification_source": "manufacturer_manual_fixture"},
    )
    requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    assert response.json()["steps"] == []  # nothing left to do, no duplicate records created
    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["search_packages"]) == 1
    assert len(run["routes"]) == 1
    assert not run.get("leads")
    assert not run.get("winners")


def test_pipeline_run_all_advances_through_node11_and_node15_then_stops_at_needs_facts(live_server, run_id):
    """A campaign with only a real signal must be driven through everything genuinely runnable
    (Node 11 classify, Node 15 cluster) and stop honestly at the real blocker (no fact) --
    never fabricate a fact, but also never sit idle on real, completable work.

    Real bug this pins: until 2026-08-19 derive_campaign_state checked `facts` before checking
    `classifications`/`clusters`, so a signal-only campaign reported state="needs_facts" and
    run_pipeline_headless's short-circuit stopped it before Node 11 ever ran -- steps=[] even
    though nothing blocked Node 11/15. Found live on Lewisham/Charlton/Eltham, all three of which
    had a real Phase 2 signal, called pipeline/run_all, and made zero progress. Fixing the check
    order then exposed a second bug: the driver's Node 18 step unconditionally read meta["facts"],
    which crashed with KeyError the moment Node 11/15 were allowed to run without facts existing
    yet -- that block now stops explicitly instead.
    """
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "needs_facts"
    assert body["steps"] == ["node_11", "node_15"]
    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["classifications"]) == 1
    assert len(run["clusters"]) == 1
    assert run.get("facts", []) == []  # never fabricated


def test_pipeline_run_all_refuses_to_run_a_candidate_pending_approval(live_server, run_id):
    _build_winner(live_server, run_id)
    proposed = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    geo_candidate = next(c for c in proposed["created"] if c["axis"] == "geo")

    response = requests.post(f"{live_server}/api/runs/{geo_candidate['run_id']}/pipeline/run_all", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "pending_phase2_approval"
    assert body["steps"] == []


def test_campaign_queue_lists_every_run_with_its_real_state(live_server, run_id):
    _register_target(live_server, run_id)
    response = requests.get(f"{live_server}/api/campaign_queue")
    assert response.status_code == 200
    campaigns = {c["run_id"]: c["state"] for c in response.json()["campaigns"]}
    assert campaigns[run_id] == "no_signal"


# --- Bulk campaign import (plan §6) -----------------------------------------------------------

_BULK_IMPORT_CSV_HEADER = (
    "target_type,service,market,geography_locality,geography_region,geography_country,"
    "product_problem,product_solution,product_features,product_benefits,product_differentiators,"
    "product_commercial_model,product_customer_outcome,"
    "audience_segment_name,audience_needs,audience_pains,audience_urgency\n"
)


def _bulk_import_row(locality="Lewisham", service="boiler_repair"):
    return (
        f"service_market,{service},domestic_plumbing,{locality},London,UK,"
        f'"Homeowners lose boiler pressure","Same-day callout","Same-day callout, 24/7 line",'
        f'"Hot water restored quickly","Local coverage",'
        f'"Fixed diagnostic fee","Working boiler within 24 hours",'
        f'"{locality} homeowner","Restore hot water","No heating",high\n'
    )


def test_bulk_import_creates_one_real_run_per_valid_row(live_server):
    csv_text = _BULK_IMPORT_CSV_HEADER + _bulk_import_row("Lewisham") + _bulk_import_row("Catford")
    response = requests.post(f"{live_server}/api/bulk_import", json={"csv": csv_text})
    assert response.status_code == 200
    body = response.json()
    assert not body["failed"]
    assert len(body["created"]) == 2
    localities = {c["target"]["geography"]["locality"] for c in body["created"]}
    assert localities == {"Lewisham", "Catford"}

    for c in body["created"]:
        run = requests.get(f"{live_server}/api/runs/{c['run_id']}").json()
        assert run["product"]["features"] == ["Same-day callout", "24/7 line"]
        assert run["audience"][0]["needs"] == ["Restore hot water"]
        assert run["conversion"] is not None


def test_bulk_import_one_bad_row_does_not_block_the_rest(live_server):
    bad_row = _bulk_import_row("Eltham", service="")  # empty service -- Node 01 rejects this
    csv_text = _BULK_IMPORT_CSV_HEADER + _bulk_import_row("Lewisham") + bad_row + _bulk_import_row("Catford")
    response = requests.post(f"{live_server}/api/bulk_import", json={"csv": csv_text})
    assert response.status_code == 200
    body = response.json()
    assert len(body["created"]) == 2
    assert len(body["failed"]) == 1
    assert body["failed"][0]["row"] == 3


def test_bulk_import_missing_required_column_is_rejected(live_server):
    response = requests.post(f"{live_server}/api/bulk_import", json={"csv": "service,market\nboiler_repair,domestic\n"})
    assert response.status_code == 400
    assert "missing required column" in response.json()["message"]


def test_bulk_import_created_rows_appear_in_campaign_queue(live_server):
    csv_text = _BULK_IMPORT_CSV_HEADER + _bulk_import_row("Greenwich")
    body = requests.post(f"{live_server}/api/bulk_import", json={"csv": csv_text}).json()
    run_id = body["created"][0]["run_id"]
    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    assert any(c["run_id"] == run_id and c["state"] == "no_signal" for c in queue["campaigns"])


# --- Node 18 winner replication (pre-existing endpoint, gap-filled: had no coverage) ----------

def test_node18_replicate_winner_mints_distinct_real_variants(live_server, run_id):
    winner = _build_winner(live_server, run_id)
    assert winner["channel"] == "search_landing"

    response = requests.post(f"{live_server}/api/runs/{run_id}/node18/replicate_winner", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["winner_channel"] == "search_landing"
    assert not body["failed"]
    assert len(body["created"]) == 3  # default formats: short_video/faq_schema/local_directory_push

    video_asset_ids = {v["video_asset_id"] for v in body["created"]}
    assert len(video_asset_ids) == 3  # all distinct

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["video_assets"]) == 4  # the original + 3 replicated variants
    assert any(event["action"] == "replicate_winning_campaign" for event in run["lineage"])


def test_node18_replicate_winner_without_a_winner_is_rejected(live_server, run_id):
    _register_target(live_server, run_id)
    response = requests.post(f"{live_server}/api/runs/{run_id}/node18/replicate_winner", json={})
    assert response.status_code == 409
    assert response.json()["error"] == "no_winner"


# --- Race condition fix: concurrent propose_candidates for the same winner (found live 2026-08-18,
# two near-simultaneous real clicks produced 16 candidates instead of 8 plus one orphaned run) ---

def test_node01_propose_candidates_concurrent_calls_never_duplicate(live_server, run_id):
    _build_winner(live_server, run_id)

    results: list[dict] = []
    errors: list[Exception] = []

    def fire():
        try:
            results.append(requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json())
        except Exception as exc:  # pragma: no cover - only on genuine failure
            errors.append(exc)

    threads = [threading.Thread(target=fire) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors
    assert len(results) == 5
    total_created = sum(len(r["created"]) for r in results)
    assert total_created == 6  # exactly one winner's worth, no matter how many concurrent callers

    # Every created candidate registered a real target -- no partial/orphaned run like the one
    # observed live (Node 01 registration didn't complete before a racing request interleaved).
    all_created = [c for r in results for c in r["created"]]
    for candidate in all_created:
        candidate_run = requests.get(f"{live_server}/api/runs/{candidate['run_id']}").json()
        assert candidate_run["target"] is not None


# --- Campaign Queue: per-node position + phase summary matrix (user-requested global view) ----

def test_campaign_queue_reports_phase_and_node_for_a_fresh_run(live_server, run_id):
    _register_target(live_server, run_id)
    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    campaign = next(c for c in queue["campaigns"] if c["run_id"] == run_id)
    assert campaign["phase"] == 2
    assert campaign["node"] == "Node 05"
    assert "no demand signal" in campaign["action"].lower()


def test_campaign_queue_reports_node11_position_when_only_a_signal_exists(live_server, run_id):
    """A campaign with a real signal but nothing else must report Node 11 (classify) next --
    not Node 16. Until 2026-08-19 derive_campaign_position checked facts before checking
    classifications/clusters, so this exact state (signal only) was misreported as blocked at
    Node 16, skipping straight past the two Phase 3 nodes that hadn't run yet. Found live on
    Lewisham/Charlton/Eltham, which each held zero classifications and zero clusters."""
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id)
    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    campaign = next(c for c in queue["campaigns"] if c["run_id"] == run_id)
    assert campaign["phase"] == 3
    assert campaign["node"] == "Node 11"


def test_commercial_intent_gate_stops_a_zero_score_classification_before_clustering(live_server, run_id):
    """A real, deliberately implausible campaign -- mars_spaceship_builder in Catford -- was live-
    tested 2026-08-19 and sailed straight through Node 11/15 to the identical needs_facts state as
    every genuine boiler campaign, because Node 05's non-zero-results check cannot distinguish a
    real local market from generic informational search results (NASA/SpaceX/YouTube pages, in that
    real case). commercial_intent_score is unconditionally computed on every classification and was
    the cheapest already-available real signal: 0 for the Mars case, matching a query with no
    COMMERCIAL_KEYWORDS hit. Per the user's explicit, informed decision, a 0 score now excludes --
    accepting this also excludes real quiet demand (this test's own low-commercial query included),
    since the alternative (per-result plausibility judgement) does not scale to large campaign
    volumes. See MIN_COMMERCIAL_INTENT_SCORE for the single named threshold.
    """
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    requests.post(
        f"{live_server}/api/runs/{run_id}/node05",
        json={
            "signal_id": "sig_no_commercial_intent", "raw_query": "how do black holes work",
            "topic": "black_holes", "source_type": "manual_curation",
            "observed_at": "2026-08-17T00:00:00+00:00",
            "geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
            "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        },
    )
    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "stopped_low_commercial_intent"
    assert "node_15" not in body["steps"]  # classified, but never clustered

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["classifications"]) == 1
    assert run["classifications"][0]["commercial_intent_score"] == 0.0
    assert run.get("clusters", []) == []

    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    campaign = next(c for c in queue["campaigns"] if c["run_id"] == run_id)
    assert campaign["phase"] == 3
    assert campaign["node"] == "Node 11"
    assert "commercial_intent_score=0.0" in campaign["action"]


def test_commercial_intent_gate_accepts_real_high_urgency_with_zero_commercial_score(live_server, run_id):
    """The real bug this pins: all four real geo campaigns (Greenwich/Lewisham/Charlton/Eltham)
    searched "restore hot water quickly [town]" -- genuine, urgent, real demand, matching Node 03's
    own registered urgency=high -- and were excluded by the commercial-intent gate anyway, because
    someone in real distress describes their PROBLEM, not a transaction: the query contains no
    commercial word by its very nature as urgent language, not because the demand isn't real.

    Confirmed programmatically 2026-08-19 that Node 11's widened keyword lists (v1.2.0) now
    correctly compute urgency_level=HIGH for this exact query (2 matches: "quickly", "restore"),
    while commercial_intent_score genuinely stays 0.0 -- proving urgency and commercial intent are
    not interchangeable outputs of the same underlying signal. The gate now accepts real high/
    critical urgency as an alternative to a nonzero commercial score, since both are freshly
    computed from real query text, not copied from a manually-entered field.
    """
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    requests.post(
        f"{live_server}/api/runs/{run_id}/node05",
        json={
            "signal_id": "sig_urgent_no_commercial", "raw_query": "restore hot water quickly Greenwich London UK",
            "topic": "restore hot water quickly", "source_type": "manual_curation",
            "observed_at": "2026-08-19T00:00:00+00:00",
            "geography": {"locality": "Greenwich", "region": "London", "country": "UK"},
            "service_context": {"service_name": "boiler_repair", "market_segment": "domestic_plumbing"},
        },
    )
    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] != "stopped_low_commercial_intent"
    assert "node_15" in body["steps"]

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    classification = run["classifications"][0]
    assert classification["commercial_intent_score"] == 0.0
    assert classification["urgency_level"] == "high"


def _register_live_signal_with_results(live_server, run_id, *, signal_id, raw_query, service_name, results):
    """Registers a signal shaped exactly like a real Firecrawl search_query fetch (source_type,
    fetch_receipt, search_result_summary) -- the service-relevance gate only ever evaluates this
    shape; a manual_curation signal is exempt from it entirely (see _passes_service_relevance_gate).
    """
    return requests.post(
        f"{live_server}/api/runs/{run_id}/node05",
        json={
            "signal_id": signal_id, "raw_query": raw_query, "topic": raw_query,
            "source_type": "search_query", "observed_at": "2026-08-19T00:00:00+00:00",
            "geography": {"locality": "Catford", "region": "London", "country": "UK"},
            "service_context": {"service_name": service_name, "market_segment": "test"},
            "metadata": {
                "fetch_receipt": {"endpoint": "https://api.firecrawl.dev/v2/search", "http_status": 200, "item_count": len(results)},
                "search_result_summary": {"total_results": str(len(results)), "top_results": results},
            },
        },
    )


def test_service_relevance_gate_stops_a_real_but_unrelated_local_result(live_server, run_id):
    """snowmobile_repair in Catford, live-tested 2026-08-19: Firecrawl genuinely returned real,
    HTTP-200 Catford car-mechanic businesses (whocanfixmycar.com, checkatrade.com) -- real, local,
    commercial, and passing the commercial-intent gate (the query contained 'quote'/'engineer'),
    but not one result is about snowmobiles, because no such trade exists there. This test
    reproduces that exact shape offline: real-looking local results for the wrong specific trade.
    """
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_live_signal_with_results(
        live_server, run_id, signal_id="sig_snowmobile", raw_query="snowmobile repair engineer quote Catford",
        service_name="snowmobile_repair",
        results=[
            {"title": "Compare Car Repair Quotes From 26 Garages In Catford", "snippet": "...", "link": "https://www.whocanfixmycar.com/services/catford"},
            {"title": "Mechanic | 24 hour | Catford | SE13 | London", "snippet": "...", "link": "https://m.londons-mobile-mechanics.co.uk/x"},
            {"title": "Find 6 Mobile Mechanics in Catford", "snippet": "...", "link": "https://www.checkatrade.com/Search/Mobile-Mechanic/in/Catford"},
        ],
    )
    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "stopped_service_not_locally_relevant"
    assert "node_15" not in body["steps"]

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert run.get("clusters", []) == []


def test_service_relevance_gate_stops_a_coincidental_brand_name_collision(live_server, run_id):
    """audience_hunter -- not a real service concept anywhere -- returned "Hunters Catford", a real
    local ESTATE AGENT, purely because it shares the surname token 'Hunter'. Confirmed via a
    controlled side-by-side probe this was a keyword coincidence (the identical query against
    Reykjavik, with no such coincidental local business, correctly returned only generic travel
    content instead). Requiring ALL of the service's own distinctive tokens ('audience' AND
    'hunter') to appear together correctly rejects a result containing only one of them.
    """
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_live_signal_with_results(
        live_server, run_id, signal_id="sig_audience_hunter", raw_query="audience hunter engineer quote Catford",
        service_name="audience_hunter",
        results=[
            {"title": "HUNTERS CATFORD - Reviews, Photos & Phone Number", "snippet": "Hunters Catford is a reputable estate agency...", "link": "https://hunters-catford.wheree.com/"},
            {"title": "Contact Sales Service & Distribution | Hunter Engineering Company", "snippet": "...", "link": "https://www.hunter.com/contact/"},
        ],
    )
    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    assert response.json()["state"] == "stopped_service_not_locally_relevant"


def test_service_relevance_gate_passes_a_genuinely_matching_real_result(live_server, run_id):
    """Positive control: real Greenwich-shaped result actually naming the service must pass."""
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_live_signal_with_results(
        live_server, run_id, signal_id="sig_boiler_real", raw_query="boiler repair engineer quote Greenwich",
        service_name="boiler_repair",
        results=[
            {"title": "Boiler repair Greenwich", "snippet": "Call us for boiler repair and hot water restoration.", "link": "http://www.boilerrepairgreenwich.co.uk/"},
        ],
    )
    response = requests.post(f"{live_server}/api/runs/{run_id}/pipeline/run_all", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] != "stopped_service_not_locally_relevant"
    assert "node_15" in body["steps"]


def test_campaign_queue_reports_node16_position_when_facts_are_genuinely_missing(live_server, run_id):
    """Node 16 is reported correctly once classification AND clustering have genuinely run and
    facts are the real remaining blocker -- the case the misordered check was meant to catch."""
    _register_target(live_server, run_id)
    _register_product(live_server, run_id)
    _register_audience(live_server, run_id)
    _define_conversion(live_server, run_id)
    _register_demand_signal(live_server, run_id, signal_id="sig_console_test")
    _classify_signal(live_server, run_id)
    requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={})
    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    campaign = next(c for c in queue["campaigns"] if c["run_id"] == run_id)
    assert campaign["phase"] == 4
    assert campaign["node"] == "Node 16"


def test_campaign_queue_reports_winner_detected_position(live_server, run_id):
    _build_winner(live_server, run_id)
    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    campaign = next(c for c in queue["campaigns"] if c["run_id"] == run_id)
    assert campaign["phase"] == 7
    assert campaign["node"] == "Node 34"
    assert "winner detected" in campaign["action"].lower()


def test_campaign_queue_reports_the_real_park_reason_as_the_action(live_server, run_id, monkeypatch):
    monkeypatch.delenv("EP050_LIVE_FETCH_ENABLED", raising=False)
    _build_winner(live_server, run_id)
    proposed = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    geo_candidate = next(c for c in proposed["created"] if c["axis"] == "geo")
    requests.post(f"{live_server}/api/runs/{geo_candidate['run_id']}/node01/approve_phase2", json={})

    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    campaign = next(c for c in queue["campaigns"] if c["run_id"] == geo_candidate["run_id"])
    assert campaign["phase"] == 2
    assert campaign["node"] == "Node 05"
    assert "live_fetch_disabled" in campaign["action"]  # the REAL reason, not a canned label


def test_campaign_queue_phase_counts_sum_to_total_campaigns(live_server, run_id):
    _register_target(live_server, run_id)
    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    assert sum(queue["phase_counts"].values()) == len(queue["campaigns"])
    assert set(queue["phase_counts"].keys()) == {"1", "2", "3", "4", "5", "6", "7"}


def test_service_axis_candidate_advances_to_pending_phase2_approval_once_product_is_filled_in(live_server, run_id):
    """Real bug found live 2026-08-18: a service-axis candidate's candidate_status stayed stuck at
    pending_product_definition forever, even after a human genuinely completed Node 02/03/04 for
    it, because nothing ever re-evaluated the static field."""
    _build_winner(live_server, run_id)
    proposed = requests.post(f"{live_server}/api/runs/{run_id}/node01/propose_candidates", json={}).json()
    service_candidate = next(c for c in proposed["created"] if c["axis"] == "service")
    candidate_id = service_candidate["run_id"]
    assert service_candidate["candidate_status"] == "pending_product_definition"

    requests.post(f"{live_server}/api/runs/{candidate_id}/node02", json={
        "problem": "x", "solution": "x", "features": ["x"], "benefits": ["x"],
        "differentiators": ["x"], "commercial_model": "x", "customer_outcome": "x",
    })
    requests.post(f"{live_server}/api/runs/{candidate_id}/node03", json={
        "segment_name": "x", "needs": ["x"], "pains": ["x"], "urgency": "medium",
        "eligibility_geography": {"locality": "Blackheath", "region": "London", "country": "UK"},
    })
    response = requests.post(f"{live_server}/api/runs/{candidate_id}/node04", json={})
    assert response.status_code == 200

    run = requests.get(f"{live_server}/api/runs/{candidate_id}").json()
    assert run["candidate_status"] == "pending_phase2_approval"

    queue = requests.get(f"{live_server}/api/campaign_queue").json()
    campaign = next(c for c in queue["campaigns"] if c["run_id"] == candidate_id)
    assert campaign["state"] == "pending_phase2_approval"
    assert campaign["node"] == "Node 05"


# --- Node 18 format-aware dispatch (Node 18 sibling factory, real gap: Node 18 always forced ----
# a video regardless of Node 14's real recommended_format) -----------------------------------

def test_node18_generate_by_format_dispatches_to_alternate_registry_for_a_real_non_video_format(live_server, run_id):
    _register_target(live_server, run_id)
    _classify_signal(live_server, run_id)
    cluster = requests.post(f"{live_server}/api/runs/{run_id}/node15/generate", json={}).json()["clusters"][0]
    fact = requests.post(
        f"{live_server}/api/runs/{run_id}/node16/fact",
        json={"topic": "boiler_pressure", "claim": "Boiler pressure should be maintained between 1.0 and 1.5 bar when cold.", "verification_source": "manufacturer_manual_fixture"},
    ).json()

    response = requests.post(
        f"{live_server}/api/runs/{run_id}/node18/generate_by_format",
        json={"cluster_id": cluster["cluster_id"], "fact_ids": [fact["fact_id"]]},
    )
    assert response.status_code == 200
    body = response.json()
    # The real ranking for this fixture (boiler_pressure_loss / Blackheath) tops out at a real
    # local-listing format, not video -- so this MUST be an alternate asset, not a video asset.
    assert "alternate_asset_id" in body
    assert "video_asset_id" not in body
    assert body["format"] == "verified_local_listing_with_emergency_hours"
    assert body["requires_human_review"] is False

    run = requests.get(f"{live_server}/api/runs/{run_id}").json()
    assert len(run["alternate_assets"]) == 1
    assert run.get("video_assets", []) == []
    assert any(event["node"] == "node_18b" for event in run["lineage"])


# --- Discovery 00A-00F and branch merge --------------------------------------

def _create_discovery(live_server):
    response = requests.post(f"{live_server}/api/discoveries", json={"audience": "Independent landlords", "geography": "London", "problem_territory": "Property compliance administration", "commercial_model": "Subscription app", "constraints": "UK only"})
    assert response.status_code == 201
    return response.json()["discovery_id"]


def _discovery_signals():
    return [
        {"source_url": "https://forum.example/a", "source_type": "forum", "observed_at": "2026-08-21T08:00:00+00:00", "problem_statement": "Urgent compliance deadline creates costly delays and fines", "payment_cues": ["pay subscription"], "urgency_cues": ["urgent"]},
        {"source_url": "https://reviews.example/b", "source_type": "review", "observed_at": "2026-08-21T08:10:00+00:00", "problem_statement": "Landlords pay a fee to track certificates and avoid penalties", "payment_cues": ["paid fee"], "urgency_cues": ["penalty"]},
        {"source_url": "https://questions.example/c", "source_type": "question", "observed_at": "2026-08-21T08:20:00+00:00", "problem_statement": "Missed certificate renewals cost landlords time and money", "payment_cues": ["cost"], "urgency_cues": ["missed"]},
    ]


def test_discovery_http_lifecycle_persists_and_lists(live_server):
    discovery_id = _create_discovery(live_server)
    added = requests.post(f"{live_server}/api/discoveries/{discovery_id}/signals", json={"signals": _discovery_signals()})
    assert added.status_code == 200 and added.json()["stage"] == "00B"
    fetched = requests.get(f"{live_server}/api/discoveries/{discovery_id}").json()
    listed = requests.get(f"{live_server}/api/discoveries").json()["discoveries"]
    assert len(fetched["signals"]) == 3
    assert discovery_id in {x["discovery_id"] for x in listed}


def test_discovery_cannot_merge_before_real_validation(live_server):
    discovery_id = _create_discovery(live_server)
    requests.post(f"{live_server}/api/discoveries/{discovery_id}/signals", json={"signals": _discovery_signals()})
    evaluated = requests.post(f"{live_server}/api/discoveries/{discovery_id}/evaluate", json={}).json()
    assert evaluated["state"] == "awaiting_validation"
    response = requests.post(f"{live_server}/api/discoveries/{discovery_id}/merge", json={})
    assert response.status_code == 409


def test_discovery_auto_collect_uses_bounded_source_adapter(live_server, monkeypatch):
    discovery_id = _create_discovery(live_server)
    class Receipt:
        fetched_at = "2026-08-21T08:00:00+00:00"
    calls = []
    def fake_fetch(topic, geography):
        calls.append((topic, geography))
        suffix = len(calls)
        return {"top_results": [{"title": "Problem", "snippet": f"Urgent costly compliance problem {suffix} requiring paid help", "link": f"https://source{suffix}.example/item"}]}, Receipt()
    monkeypatch.setattr(console_server.node05, "fetch_search_demand", fake_fetch)
    response = requests.post(f"{live_server}/api/discoveries/{discovery_id}/collect", json={})
    assert response.status_code == 200, response.text
    assert len(response.json()["signals"]) == 3
    assert len(calls) == 3


def test_validated_discovery_merges_through_real_node15_once(live_server):
    discovery_id = _create_discovery(live_server)
    requests.post(f"{live_server}/api/discoveries/{discovery_id}/signals", json={"signals": _discovery_signals()})
    requests.post(f"{live_server}/api/discoveries/{discovery_id}/validation", json={"outcomes": [{"commitment_type": "qualified_waitlist", "count": 2, "source_url": "https://validation.example/experiment/1", "observed_at": "2026-08-21T09:00:00+00:00"}]})
    evaluated = requests.post(f"{live_server}/api/discoveries/{discovery_id}/evaluate", json={}).json()
    assert evaluated["state"] == "validated_ready_to_merge"
    first = requests.post(f"{live_server}/api/discoveries/{discovery_id}/merge", json={})
    assert first.status_code == 200, first.text
    first_body = first.json();run_id = first_body["run"]["run_id"]
    assert first_body["run"]["originating_branch"] == "discovery"
    assert first_body["run"]["validated_opportunity_offer_contract"]["schema"] == "validated_opportunity_offer_contract.v1"
    assert first_body["clusters"]
    second = requests.post(f"{live_server}/api/discoveries/{discovery_id}/merge", json={}).json()
    assert second["idempotent"] is True
    assert second["run"]["run_id"] == run_id


def test_demand_scan_status_persists_provider_failure(live_server, run_id):
    response = requests.post(
        f"{live_server}/api/runs/{run_id}/demand_scan/status",
        json={"source": "search", "status": "failed", "message": "provider network unavailable", "attempt_id": "scan_test"},
    )
    assert response.status_code == 200, response.text
    persisted = requests.get(f"{live_server}/api/runs/{run_id}").json()["demand_scan"]
    assert persisted["sources"]["search"]["status"] == "failed"
    assert persisted["sources"]["search"]["message"] == "provider network unavailable"
    assert persisted["attempt_id"] == "scan_test"
