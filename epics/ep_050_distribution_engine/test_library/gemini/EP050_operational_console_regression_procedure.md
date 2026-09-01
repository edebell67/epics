# EP050 Operational Console Regression Procedure

> VERSION HISTORY
> - v1.0.0 · 2026-08-16 · Initial version: reusable deterministic regression procedure for EP050 Operational Console.

## 1. Purpose & Scope
Validates the local offline HTTP server, REST endpoints, static assets, live Node 11 classification integration, and local audit logging for the EP050 Operational Console.

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/implementation/operational_console/test_console_server.py
```

## 3. Launching for User Acceptance Review
Execute:
```cmd
epics\ep_050_distribution_engine\implementation\operational_console\open_console.bat
```
or directly in terminal:
```powershell
python epics/ep_050_distribution_engine/implementation/operational_console/server.py 8050
```
Open browser at: `http://127.0.0.1:8050/`

## 4. Expected Acceptance Criteria
- Total tests: 8
- Passed: 8
- Failed: 0
- Server binds to `127.0.0.1` only.
- 21-node status board displays accurate owner, class (14A/7B), and evidenced percentages.
- Live offline classification executes smoothly and outputs valid JSON.
- All outbound publishing, scraping, routing, and payment controls remain visibly locked and disabled.
