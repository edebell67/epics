# EP052 recovery operations

Version 1.0.0 · 2026-09-02. Local recovery verified; hosted deployment and dual-writer synchronisation are not delivered.

## Repeatable acceptance check

From `C:\Users\edebe\eds\epics\ep_052_strategy_directory_agentic_trade_arena` in PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'lean_delivery/app/src'
python scripts/test_recovery.py --review-dir evidence/trading/review_20260902_162516_687
```

Prerequisites: the isolated review API is healthy on port8056, and its existing private owner/agent credentials have not expired or been revoked. Do not rerun the original trade-creation scenario to repair a failed prerequisite. Inspect the failure first.

The command backs up the live review database using SQLite's online backup API, restores to a newly created private directory, compares all20 table hashes, replays existing receipts only on the restored copy and verifies fees, cursors and revocation persistence. It does not trade on the running exchange or revoke its credentials. It writes a sanitized `report.json` and two **private** database files under `evidence/recovery/run_*`. These databases contain private participant records and credential hashes: never publish them or copy them into shared test reports.

Expected output: PASS, integrity `ok`, exact_restore true, duplicate_fees false, live_credential_unchanged true. Stop on any failure. This is an HTTP/test-client recovery test, not an autonomous Hermes demonstration or proof of a new operating-system process restart.

## Backup and restore CLI

From the epic's `lean_delivery/app` directory, using the installed package or `PYTHONPATH=src`:

```powershell
python -m lean_exchange.recovery backup --source 'C:\private\source.sqlite' --destination 'C:\private\new-backup.sqlite'
python -m lean_exchange.recovery inspect --source 'C:\private\new-backup.sqlite'
python -m lean_exchange.recovery restore --source 'C:\private\new-backup.sqlite' --destination 'C:\private\new-restored.sqlite'
```

Replace the example paths with actual private paths. Both destination files must not exist. Existing files are never overwritten. Failed operations may leave a new partial destination for inspection; use a new filename after diagnosing failure. Do not copy just a live `.sqlite` file while omitting its WAL. The backup command includes committed WAL data and excludes uncommitted changes. Schema5 and database integrity are checked; a future schema is rejected rather than downgraded.

The printed manifest contains hashes/counts, not row contents. Protect the database directory with platform access controls; Python's file mode is not a substitute for Windows ACL configuration or encryption.

## Future hosted cutover boundary

Maintain **one writable exchange authority**. This delivery supports a verified snapshot for migration, not merging two independently writable inventories.

1. Before cutover, configure the host, TLS, private storage, backups and owner access. Keep non-local access disabled until those checks pass.
2. Quiesce visiting clients and stop source writes through an approved operating procedure. Take a final online backup and verify its manifest. A backup taken while writes continue is a valid snapshot, but does not contain later transactions.
3. Transfer the private backup securely; restore to a new path and verify identity, schema and table hashes. Preserve request IDs, receipt IDs and cursors. Do not seed participants again.
4. Transfer configuration and secrets separately. The intelligence service has its own database/receipt state and service credential; the exchange-only backup does **not** protect those. Coordinate its backup/restore separately before charging queries on a migrated installation.
5. Verify receipt recovery, owner isolation and revocation before reopening writes. Point clients at the new API only after acceptance; keep the old exchange read-only/offline.
6. If rollback is needed after hosted writes, first stop writes and reconcile/transfer that authoritative state. Do not reactivate an older local snapshot and silently discard newer trades.

No hosted deployment, TLS termination, cross-host incremental sync or automatic failover has been tested here. Those limitations must remain visible at handoff.
