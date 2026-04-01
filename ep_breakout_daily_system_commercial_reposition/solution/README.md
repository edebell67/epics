# Breakout Daily System Commercial Reposition

This folder contains the launch-ready commercial solution for repositioning the breakout system as a daily trading intelligence product with weekly consistency proof.

## Structure

- `frontend/`: Vite + React landing page and subscriber-facing showcase
- `scripts/`: data preparation scripts that transform local breakout JSON into app-ready snapshot data
- `content/`: launch copy, email copy, and social assets
- `docs/`: implementation notes and generated market snapshot data

## Core Message

Daily breakout intelligence with weekly proof of consistency.

## Intended Launch Scope

- Public landing page
- Daily market board teaser
- Weekly proof section
- Pricing and offer positioning
- Launch copy and subscriber messaging

## Data Source

The source data comes from:

- `C:\Users\edebe\eds\TradeApps\breakout\fs\json\live`

## Build Flow

1. Run `generate_market_snapshot.bat`
2. Run `install_frontend_deps.bat`
3. Run `run_frontend_dev.bat`
4. Or use `open_demo.bat` to start the dev server and open the page

## Delivery Wrappers

- `install_frontend_deps.bat`: installs frontend packages in `frontend`
- `generate_market_snapshot.bat`: regenerates the app-ready market snapshot from local breakout JSON
- `refresh_market_snapshot_loop.bat`: keeps regenerating the leaderboard snapshot every 60 seconds for the live board/demo flow
- `run_frontend_dev.bat`: regenerates the snapshot and starts the frontend dev server
- `open_demo.bat`: launches the dev server in a new terminal and opens `http://localhost:3012`
- `verify_delivery.bat`: checks required files and runs snapshot generation as a review-oriented verification step

## Notes

- The frontend reads generated data from `frontend/src/data/generated/marketSnapshot.ts`.
- The focused live board polls `frontend/public/leaderboard.json` every 60 seconds.
- The generator script detects the latest dated folder for each product type and the latest weekly consistency file.
- `run_frontend_dev.bat` starts a background refresh loop so the polled leaderboard file can change during local review.
- `install_frontend_deps.bat` may require internet access to download frontend packages.
