# EP050 Operational Console Test Evidence Bundle

- Timestamp: `2026-08-16T22:35:00+01:00`
- Target URL: `http://127.0.0.1:8050/`
- Launcher: `epics/ep_050_distribution_engine/implementation/operational_console/open_console.bat`
- Test Suite: `epics/ep_050_distribution_engine/implementation/operational_console/test_console_server.py`
- Test Results: 8 passed in 0.91s (0 failures, 0 warnings)
- Test Categories:
  - 21-node status board model verification (14A/7B split, total 37 nodes)
  - Node 01 Target inspector endpoint
  - Contract gates endpoint (Stage 2->3 and Stage 4->5)
  - Live Node 11 demand signal classification execution (positive case)
  - Missing required field 422 fail-closed validation
  - Contract violation 400 fail-closed validation
  - Local operator audit log workflow
  - Static assets serving (console.html, console.css, console.js)
