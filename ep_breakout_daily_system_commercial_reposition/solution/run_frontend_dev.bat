@echo off
setlocal

set "ROOT=%~dp0"
set "FRONTEND=%ROOT%frontend"

echo Ensuring latest market snapshot is generated...
call "%ROOT%generate_market_snapshot.bat"
if errorlevel 1 (
  echo Could not generate market snapshot.
  exit /b 1
)

echo Starting background snapshot refresh loop...
start "breakout-snapshot-refresh" /min cmd /c "%ROOT%refresh_market_snapshot_loop.bat"

echo Starting frontend dev server on port 3012...
cd /d "%FRONTEND%" || (
  echo Failed to access frontend folder: %FRONTEND%
  exit /b 1
)

npm run dev
if errorlevel 1 (
  echo Frontend dev server failed to start.
  exit /b 1
)

endlocal
