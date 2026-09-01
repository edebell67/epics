# EP050 Node 21 — Offline Search Distribution Regression Procedure

## Preconditions
- Run locally from repository root with Python and Node 19/20 implementation files present.
- No network, CMS, credentials, publishing, upload, or indexing access is allowed.

## Procedure
1. Compile `implementation/node_21/search_distribution.py` and `test_search_distribution.py`.
   - Expected: exit code 0.
   - Stop-on-failure: stop; do not generate or dispatch any artifact.
2. Run `python epics/ep_050_distribution_engine/implementation/node_21/test_search_distribution.py`.
   - Expected: all 12 tests pass while socket construction raises an assertion if attempted.
   - Stop-on-failure: stop; retain output and do not continue to any external system.
3. Confirm the real Node 19 fixture is evaluated and consumed through Node 20 to create Node 21 package artifacts.
   - Expected: manifest has literal `external_action: false`, sitemap support has `indexing_request: false`, and all generated URLs are HTTPS `.test` URLs.
4. Confirm negative coverage rejects non-`.test` destinations, external action, broken lineage, incomplete compliance, missing disclaimer/CTA, malformed mappings, and local record conflicts.

## Evidence Requirements
- Save compile/test output under `evidence/node_21/<timestamp>/`.
- Record the test count and no-network gate result in the lifecycle and report.
