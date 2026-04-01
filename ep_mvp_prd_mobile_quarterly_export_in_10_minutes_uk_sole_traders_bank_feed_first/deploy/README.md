# Deployment Overview

This folder defines how the MVP quarterly export epic will move from validation into release once runtime containers are added.

## Current Scope

The repository currently ships contract and backend validation assets under `solution/backend`, documentation under `solution/docs`, and review evidence under `verification/`.

The CI workflow at `.github/workflows/ci.yml` already validates:

- markdown documentation across the epic workspace
- OpenAPI contracts when they are added
- backend contract scripts in `solution/backend`
- `docker-compose.yml` when that file is introduced

## Future Build Outputs

Release packaging is designed around two image outputs:

- `quarterly-export-backend:ci` from `solution/backend/`
- `quarterly-export-frontend:ci` from `solution/frontend/`

The workflow only attempts those builds when a corresponding `Dockerfile` exists, so implementation work can land incrementally without breaking CI before the runtime layers are ready.

## Deployment Flow

1. Run the CI workflow and confirm the validation job passes for docs, contracts, and any available infrastructure assets.
2. Build backend and frontend images once their Dockerfiles exist.
3. Promote the validated image tags into the target environment using the release checklist in this folder.
4. Attach or reference release evidence from `verification/` so the deployment record shows the tested user flows and contract coverage used for the release decision.

## Runtime Contract Hooks

When the API implementation is live, deployment smoke tests should call these contract endpoints after rollout:

- `POST /api/v1/imports`
- `POST /api/v1/exports/quarterly`

Those endpoint hooks are already reserved in the CI workflow under the manual smoke-test stage so the future release process can reuse the same contract addresses without redesigning the pipeline.

## Verification Evidence

Use `verification/` as the release evidence ledger for this epic. Current examples already include user-flow screenshots such as:

- `verification/finish_now_queue_zero_blockers.png`
- `verification/quarter_readiness_screen.png`
- `verification/20260318_184500_mobile_inbox_exception_queue_screen.png`

Add future smoke outputs, logs, and screenshots to the same folder so deployment review can reference one consistent evidence location.
