@echo off
REM epics/ep_064_reddit_oppourtunity/serve_demos_lan.bat — Serve EP064 mobile-first demos over local HTTP (port 8064) for phone/LAN testing or tunnel sharing
REM
REM VERSION HISTORY
REM v1.0.0 · 2026-10-19 · Initial version (V20261019_0347): starts Python HTTP server on port 8064 and opens the EP064 demo hub.
cd /d "%~dp0"
echo Starting EP064 Demo Server at http://localhost:8064 ...
start "" "http://localhost:8064/index.html"
python -m http.server 8064 --bind 0.0.0.0
