@echo off
setlocal

set "ROOT=%~dp0"

echo Generating latest market snapshot from local breakout JSON...
node "%ROOT%scripts\build-market-snapshot.mjs"
if errorlevel 1 (
  echo Market snapshot generation failed.
  exit /b 1
)

echo Market snapshot generated successfully.
endlocal
