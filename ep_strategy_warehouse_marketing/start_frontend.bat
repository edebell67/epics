@echo off
setlocal
echo Starting Strategy Warehouse Marketing Frontend...
echo.
set PORT=3000
for /f %%P in ('powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue) { '3001' } else { '3000' }"') do set PORT=%%P
if "%PORT%"=="3001" (
  echo Port 3000 is already in use in this environment.
  echo Falling back to: http://localhost:3001/
) else (
  echo URL: http://localhost:3000/
)
echo.
cd solution\frontend
node .\node_modules\vite\bin\vite.js --configLoader native --config .\vite.config.js --host --strictPort --port %PORT%
