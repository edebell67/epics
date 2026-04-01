@echo off
setlocal
cd /d "%~dp0"
set PORT=4173
start "" cmd /c python -m http.server %PORT%
timeout /t 2 /nobreak >nul
start "" http://localhost:%PORT%/
