@echo off
REM epics/ep_050_distribution_engine/implementation/operational_console_claude/open_console.bat
REM EP050 Operational Console v2 — deterministic Windows launcher.
REM
REM VERSION HISTORY
REM v1.0.0 · 2026-08-17 · Initial hardened launcher: persistent server window + readiness poll before browser open.

setlocal
set PORT=8060
set SCRIPT_DIR=%~dp0

start "EP050 Operational Console v2 (port %PORT%)" cmd /k python "%SCRIPT_DIR%server.py" %PORT%
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%open_console.ps1" -Port %PORT%
endlocal
