@echo off
setlocal

set "ROOT=%~dp0"
set "FRONTEND=%ROOT%frontend"

echo [1/2] Changing to frontend folder
cd /d "%FRONTEND%" || (
  echo Failed to access frontend folder: %FRONTEND%
  exit /b 1
)

echo [2/2] Installing frontend dependencies
npm install
if errorlevel 1 (
  echo npm install failed.
  exit /b 1
)

echo Frontend dependencies installed successfully.
endlocal
