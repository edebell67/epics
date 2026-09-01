# EP050 Node 01 registration regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_01/registration.py`, or before promoting Node 01 past its current 90% gate, or before any Node 02+ work that depends on Node 01's `target_id` contract.

## Preconditions
- Changes stay fixture-only: no network call, no production datastore, no real customer identifiers. Only the confirmed synthetic target (`service=boiler_repair`, `market=domestic_plumbing`, `geography={locality:Blackheath, region:London, country:UK}`, `target_type=service_market`) or an equivalent synthetic fixture is used.
- Do not weaken fail-closed validation (missing/invalid fields, conflicting duplicates) to make a test pass.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_01/test_registration.py -v --basetemp=<a writable scratch dir>`. On Windows, the default OS temp dir can be permission-restricted for `tmp_path`; pass `--basetemp` explicitly if `PermissionError` on `pytest-of-<user>` occurs.
2. All tests must pass, covering every category below with zero skips:
   - Positive registration.
   - Deterministic/stable identity — `derive_target_id("boiler_repair", {"locality": "Blackheath", ...})` must equal `tgt_boiler_repair_blackheath`, matching the value already published in the Node 05→11 downstream contract fixture. If this value ever needs to change, the downstream contract owner (Gemini) must be notified via the message board before merging.
   - Required-field failures for `target_type`, `service`, `market`, `geography` (and its subfields `locality`/`region`/`country`) must raise `ValidationError`, never a raw `TypeError`.
   - Invalid enum/type: malformed `target_type`, out-of-set `status`, wrong-typed `geography`/`app_id`.
   - Duplicate idempotency: registering identical fields twice must not create a second record.
   - Conflicting duplicate: same derived `target_id` with different field values must raise `ConflictError` and leave the original record unmodified.
   - Persistence round trip: a second `TargetRegistry` instance opened against the same storage file must read back an identical record.
   - No-network assertion: monkeypatching `socket.socket` to raise must not break registration.
   - Full-lifecycle regression (register → idempotent re-register → list → get → conflict → validation failure → not-found).
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_01/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest describing command, result, and coverage.
4. Update the Node 01 lifecycle record's Implementation Log, Evidence, and Validation sections with the new run, and re-verify byte-equality between the canonical `workstream/200_inprogress/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror (`cmp` on Windows, or `fc.exe` per other owners' convention).

## Fail conditions
- Any test fails, errors, or is skipped.
- `derive_target_id` output changes without a corresponding board notification to the downstream contract owner.
- A required-field or type-validation case raises anything other than `ValidationError`/`ConflictError` (e.g. a raw `TypeError`, silent pass, or partial write).
- Any network socket is opened during registration.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 01's offline registration contract only. It does not authorize live network collection, production datastore access, or Node 02+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
