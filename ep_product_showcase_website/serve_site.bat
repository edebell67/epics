@echo off
setlocal
cd /d "%~dp0"
set PORT=4173
echo Serving product showcase website at http://localhost:%PORT%/
python -m http.server %PORT%
