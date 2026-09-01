# EP050 Node 02 product intelligence regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_02/product_intelligence.py`, or before promoting Node 02 past its current gate, or before any Node 03+ work that depends on Node 02's product-intelligence contract.

## Preconditions
- Changes stay fixture-only: no network call, no production datastore, no real customer identifiers.
- The suite must construct a real `TargetRegistry` (Node 01) instance and register the synthetic target through it — do not mock the Node01->02 dependency check away.
- Do not weaken fail-closed validation (missing/invalid fields, unregistered target, conflicting duplicates) to make a test pass.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_02/test_product_intelligence.py -v --basetemp=<a writable scratch dir>` (pass `--basetemp` explicitly; the default OS temp dir can be permission-restricted on Windows for `tmp_path`).
2. All tests must pass, covering:
   - Positive registration, including the `evidence_sources` default-empty case.
   - Node01->02 contract/integration: an unregistered `target_id` must raise `UnknownTargetError`; a target registered through a real `TargetRegistry` instance must be accepted.
   - Required-field failures for all 8 required fields (`target_id`, `problem`, `solution`, `features`, `benefits`, `differentiators`, `commercial_model`, `customer_outcome`), including a blank-string case.
   - Invalid enum/type: wrong-typed or empty list fields, non-string list items, wrong-typed `evidence_sources`.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original record unmodified).
   - Persistence round trip via a fresh registry instance against the same storage file.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_02/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 02 lifecycle record's Implementation Log, Evidence, and Validation sections with the new run, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- The Node01->02 dependency check is mocked/bypassed instead of using a real `TargetRegistry`.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened during registration.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 02's offline product-intelligence contract only. It does not authorize live network collection, production datastore access, or Node 03+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
