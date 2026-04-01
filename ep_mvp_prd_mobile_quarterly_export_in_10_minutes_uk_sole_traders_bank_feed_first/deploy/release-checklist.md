# Release Checklist

Use this checklist before promoting the MVP quarterly export epic into a shared environment.

## Validation Gate

- Confirm `.github/workflows/ci.yml` passed on the target commit.
- Confirm markdown and contract validation covered the latest docs under `solution/docs` and `deploy/`.
- Confirm backend validation completed successfully via:
  - `npm run validate:mvp-domain-schemas`
  - `npm run verify:transaction-import`
- Confirm `docker-compose.yml` validation passed if that file exists for the release.
- Confirm OpenAPI lint passed if API contracts were added for this release.

## Artifact Gate

- Confirm the backend image was built from `solution/backend/` once `solution/backend/Dockerfile` exists.
- Confirm the frontend image was built from `solution/frontend/` once `solution/frontend/Dockerfile` exists.
- Record the promoted image tags and commit SHA in the release ticket or deployment log.

## Verification Evidence Gate

- Link the evidence artifacts stored under `verification/`.
- Confirm the evidence set includes the latest user-flow proof, smoke logs, and any release-specific screenshots.
- Verify existing screenshots still match the released behavior where applicable:
  - `verification/finish_now_queue_zero_blockers.png`
  - `verification/quarter_readiness_screen.png`
  - `verification/20260318_184500_mobile_inbox_exception_queue_screen.png`

## Smoke-Test Gate

Once the runtime API exists and is reachable in the target environment, run smoke checks against:

- `POST /api/v1/imports`
- `POST /api/v1/exports/quarterly`

Record request/response summaries and any generated logs under `verification/`.

## Deployment Decision

- Promote only if validation, artifact, and verification evidence gates all pass.
- If a gate is skipped because the relevant asset does not exist yet, record that explicitly in the release notes.
- If smoke tests fail, stop the release and attach the failure output under `verification/` before reattempting.
