@echo off
setlocal

set "ROOT=%~dp0"

echo Starting market snapshot refresh loop...

:loop
call "%ROOT%generate_market_snapshot.bat"
if errorlevel 1 (
  echo Snapshot refresh failed. Retrying in 60 seconds...
) else (
  echo Snapshot refresh complete. Waiting 60 seconds...
)

timeout /t 60 /nobreak >nul
goto loop
