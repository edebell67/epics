# EP050 Node 01 — Evidence Bundle (20260816_215549)

> VERSION HISTORY
> - v1.0.0 · 2026-08-16 · Initial timestamped evidence bundle for Node 01 registration.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/node_01/test_registration.py -v --basetemp=<scratchpad>/pytest_tmp_node01
```

**Result:** 19 passed, 0 failed, 0 errors, 0.18s. Full output in `pytest_output.txt`.

**Coverage:**
- Positive registration (1 test)
- Deterministic/stable identity, including cross-check against the already-published Node 05->11 contract seed fixture (3 tests)
- Required-field failures, all 4 required fields individually (4 parametrized cases + 1 subfield case)
- Invalid enum/type rejection: target_type format, status enum, geography type, app_id type (4 tests)
- Duplicate idempotency: identical re-registration does not create a second record (1 test)
- Conflicting duplicate rejection: same derived target_id, different field values, fail-closed, original record unmodified (1 test)
- Serialization/persistence round trip via a fresh registry instance against the same local JSON fixture file (2 tests)
- No-network assertion: `socket.socket` is monkeypatched to raise if called; registration still succeeds without it (1 test)
- Full-lifecycle regression pass combining register/idempotent-reregister/list/get/conflict/validation-failure/not-found in one sequence (1 test)

**External side effects:** none. No network call, no production datastore, no write outside the pytest `tmp_path`/`--basetemp` fixture directories used by the tests themselves.
