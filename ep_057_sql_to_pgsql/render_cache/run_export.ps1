# epics/ep_057_sql_to_pgsql/render_cache/run_export.ps1 — Scheduled-task wrapper: export + publish the Top10 cache every 5 minutes.
# v1.0.1 · 2026-09-24 · Uses the full python.exe path (scheduled tasks may lack PATH) and logs a timestamped line.
# v1.0.0 · 2026-09-23
# Register (once):  schtasks /Create /SC MINUTE /MO 5 /TN "EP057 Top10 cache export" /TR "powershell -NoProfile -File <path>\run_export.ps1"
# Prereqs: PG* env vars (or repo .env) for local tradedb; git credentials for github.com/edebell67/epics (Git Credential Manager).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$lock = Join-Path $PSScriptRoot 'outbox_state.lock'
if (Test-Path $lock) { if ((Get-Item $lock).LastWriteTime -gt (Get-Date).AddMinutes(-20)) { Write-Host 'previous run still active'; exit 0 } }
New-Item -ItemType File -Force $lock | Out-Null
try {
    $log = Join-Path $PSScriptRoot 'export.log'
    "[$(Get-Date -Format s)] start" | Add-Content $log
    & 'C:\Python313\python.exe' export_cache.py *>> $log
} finally { Remove-Item $lock -ErrorAction SilentlyContinue }
