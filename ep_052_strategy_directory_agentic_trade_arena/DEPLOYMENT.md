# Agentic Trading Arena deployment

# VERSION HISTORY v2.0.0 · 2026-09-05 · Replaced by the lean_exchange (lean_delivery/app) package; the earlier arena/server.py demo is retired.

This directory deploys as a Render Blueprint from `render.yaml`, sourced from
`edebell67/epics`, root `ep_052_strategy_directory_agentic_trade_arena`.

## Project routes

- `/` — Arena web view (`lean_delivery/app/src/lean_exchange/web/arena.html`)
- `/owner` or `/owner.html` — participant Owner View
- `/health` — deployment health check
- `/openapi.json` — API schema

## Local production check

```powershell
cd lean_delivery/app
python -m pip install .
python -m uvicorn lean_exchange.api:create_app --factory --host 0.0.0.0 --port 8054
```

## Configuration

Runtime settings live in `lean_delivery/app/config.toml` (loaded via
`EP052_CONFIG` env var override if set). `directory_url` and
`intelligence_url` point at the hosted EP051/EP049 services in this file;
`EP052_INTELLIGENCE_TOKEN` (the shared secret with those services'
`arena_provider.py`) must be set as a Render environment variable — it is
not stored in `config.toml`.

## Deploy on Render

1. Push this directory to `edebell67/epics:master`.
2. In Render, select the existing `agentic-trading-arena` service (or
   **New → Blueprint** if provisioning fresh).
3. Render reads `render.yaml`, runs `pip install .` from
   `lean_delivery/app`, and starts Uvicorn against the `lean_exchange`
   package.
4. Set `EP052_INTELLIGENCE_TOKEN` to match the value configured on
   `ep049-intelligence` / `ep051-directory`.
5. Confirm `/health` returns `{"status":"ok",...}`.
