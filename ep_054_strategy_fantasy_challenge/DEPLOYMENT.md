<!-- DEPLOYMENT.md — In-place EP054 PostgreSQL release and migration runbook.

VERSION HISTORY
v2.1.0 · 2026-09-01 · Adds the controlled one-time legacy importer so existing SQLite records are preserved before retirement.
v2.0.1 · 2026-09-01 · Narrows the release grep to executable SQLite hooks so historical documentation does not create false failures.
v2.0.0 · 2026-09-01 · Replaces SQLite/disk deployment with isolated PostgreSQL migrations on approved shared capacity.
v1.0.0 · 2026-09-01 · Initial release handoff for the persistent MVP.
-->
# EP054 hosted deployment

## Release boundary

Update the existing Render service `srv-da9hlaajnfac73dtq9g0` in place. Do not create a Blueprint, replacement service, PostgreSQL database, disk, or other resource. `render.yaml` documents the service contract; it is not authority to recreate infrastructure.

EP054 uses the approved shared PostgreSQL capacity through `DATABASE_URL`, but owns only the isolated `fantasy` schema. The runtime and migration role must not alter EP047/EP051 schemas or objects.

## Runtime configuration

- FastAPI/Uvicorn web service.
- `DATABASE_URL`: existing approved PostgreSQL connection, configured only in Render environment settings.
- `STRATEGY_DIRECTORY_URL=https://ep051-directory.onrender.com`.
- Health route: `/health`; acceptance requires `database.status=ok`, `database.engine=postgresql`, `database.schema=fantasy`, and `strategy_directory.status=ok`.
- SQLite and `FANTASY_DB_PATH` are unsupported. The old persistent disk must not be read by the application.

## Migration gate

At application startup, `database.apply_migrations()`:

1. validates that `DATABASE_URL` is PostgreSQL;
2. obtains a transaction-scoped advisory lock;
3. creates/reuses only the `fantasy` schema;
4. revokes public schema/table access;
5. applies each `migrations/*.up.sql` file transactionally and records it in `fantasy.schema_migrations`.

Before production promotion, rehearse both `001_fantasy_schema.up.sql` and `001_fantasy_schema.down.sql` against an isolated staging/scratch PostgreSQL database. Never run the down migration against the live shared database: it intentionally drops the complete `fantasy` schema.

If the existing service contains records in its retired SQLite disk, export/download that file and import it once after the PostgreSQL migration succeeds:

```powershell
C:\Python313\python.exe scripts\import_legacy_sqlite.py C:\secure\path\fantasy_mvp.sqlite3 --confirm
```

The importer opens SQLite read-only, maps each old entry to a first-class Portfolio Object and immutable competition entry, hashes invitation tokens, and uses conflict-safe PostgreSQL inserts. Reconcile source/target counts before retiring the disk. Do not delete the source database until that reconciliation is recorded.

## Release gate

Run from this folder:

```powershell
C:\Python313\python.exe -m pytest tests -q
node --test tests/fantasy.test.cjs
C:\Python313\python.exe -m compileall -q server.py database.py repository.py directory_client.py
node --check fantasy.js
rg -n -i "import sqlite3|sqlite3\.connect|FANTASY_DB_PATH" server.py database.py repository.py render.yaml requirements.txt
```

The final `rg` command must return no matches. Then:

1. Validate the scoped EP054 diff and migration SQL.
2. Confirm the existing service has the approved `DATABASE_URL`; never print its value.
3. Deploy the exact scoped revision to the existing service.
4. Confirm startup migrations finish successfully and no shared schema changes appear.
5. Verify `/health`, `/`, `/api/strategies`, portfolio/entry creation, leaderboard score-run persistence, and hashed invitation lifecycle.
6. Confirm no new Render resource was created and the legacy SQLite disk was not accessed.

Do not publish `fantasy_mvp.sqlite3`, `__pycache__`, `.playwright-cli`, local test artifacts, credentials, or database URLs.

## Current workflow boundary

This correction implements WF-020 persistence isolation and aligns current MVP storage with the Portfolio Object, immutable entry snapshot, auditable score-run, and hashed-invitation contracts. WF-010 remains dependent on the ecosystem's approved authentication mechanism; email supplied by the browser is not a substitute for trusted owner identity and must not be represented as final production authorisation.
