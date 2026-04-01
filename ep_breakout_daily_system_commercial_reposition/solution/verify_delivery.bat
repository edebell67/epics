@echo off
setlocal

set "ROOT=%~dp0"
set "FRONTEND=%ROOT%frontend"
set "PASS=1"

echo Verifying required delivery files...

call :check "%ROOT%README.md"
call :check "%ROOT%generate_market_snapshot.bat"
call :check "%ROOT%refresh_market_snapshot_loop.bat"
call :check "%ROOT%run_frontend_dev.bat"
call :check "%ROOT%open_demo.bat"
call :check "%ROOT%install_frontend_deps.bat"
call :check "%ROOT%scripts\build-market-snapshot.mjs"
call :check "%ROOT%frontend\package.json"
call :check "%ROOT%frontend\src\App.tsx"
call :check "%ROOT%frontend\public\leaderboard.json"
call :check "%ROOT%content\launch_copy.md"

echo Running market snapshot generation as part of verification...
call "%ROOT%generate_market_snapshot.bat"
if errorlevel 1 (
  set "PASS=0"
)

if "%PASS%"=="1" (
  echo Delivery verification passed.
  exit /b 0
)

echo Delivery verification failed.
exit /b 1

:check
if exist "%~1" (
  echo OK  %~1
  goto :eof
)

echo MISS %~1
set "PASS=0"
goto :eof
