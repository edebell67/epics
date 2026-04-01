@echo off
setlocal

set "ROOT=%~dp0"

echo Launching Breakout Daily demo workflow...
start "" cmd /k "%ROOT%run_frontend_dev.bat"
timeout /t 5 /nobreak >nul
start "" http://localhost:3012

echo Browser launch requested for http://localhost:3012
endlocal
