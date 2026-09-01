# EP050 Node 20 Offline Publishing Scheduler Report

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial capped offline implementation report.

## Outcome
A deterministic local mock scheduler is implemented at `implementation/node_20/publishing_scheduler.py`. It consumes only the versioned v1.1.0 candidate, derives the specified SHA-256 plan ID, preserves asset/target/opportunity lineage, validates both schemas, rejects unsafe/malformed/unapproved inputs, persists only in memory, and always emits literal `external_action: false`.

## Validation
- PASS — Node 20 direct offline test runner: `7/7` passed (positive, idempotency/persistence, unsafe destination, unapproved compliance, lineage mismatch, malformed timestamp, socket prohibition).
- PASS — `node19_to_node20_candidate_v1_1_test.py`: `12/12` passed.
- PASS — `py_compile` completed.
- Note — `pytest` is unavailable in the Hermes venv (`No module named pytest`); direct deterministic tests were executed instead.

## Protected Gates
This is a 75% capped offline delivery, not a canonical Node 20 completion. Gemini producer review, Codex canonical promotion, and real Node 19→20 integration/regression remain required. No adapter, queue, credential, network, publication, scheduling, or external effect exists.
