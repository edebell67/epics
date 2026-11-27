@echo off
REM epics/ep_064_business_solutions/deploy_agents_to_github.bat — push the EP064 agent demos to GitHub (edebell67/epics), next to SiteLedger
REM VERSION HISTORY
REM v1.0.0 · 2026-11-27 · Initial version: stages only the new EP064 folders/files, commits, rebases on the remote and pushes.
cd /d "%~dp0.."
git status --short ep_064_business_solutions
git add ep_064_business_solutions/agent_01_scout ep_064_business_solutions/agent_02_frontdesk ep_064_business_solutions/agent_03_closer ep_064_business_solutions/agent_04_collector ep_064_business_solutions/agent_05_keeper ep_064_business_solutions/agent_06_bookkeeper ep_064_business_solutions/app_01_chaseup ep_064_business_solutions/research/reddit_opportunity_scan_20261127.md ep_064_business_solutions/deploy_agents_to_github.bat
git commit -m "EP064: six agent demos (Scout, Frontdesk, Closer, Collector, Keeper, Bookkeeper), ChaseUp, Reddit scan #3; trades agents link to SiteLedger"
git pull --rebase
git push
pause
