# API Usage Guide

This package documents the contract-first API surface for the bank-feed-first quarterly
export MVP. Service code will later live under `solution/backend/`, while expected
consumers include mobile and web clients under `solution/frontend/`.

## Authentication

- Every endpoint requires a bearer token for the authenticated sole-trader user.
- Every `POST` request should send an `Idempotency-Key` header so mobile retries do not
  create duplicate connection sessions, import runs, or export jobs.

## Workflow Sequence

1. `POST /api/v1/bank-feeds/connect`
   Start a consent session for a bank provider and receive the redirect URL.
2. `POST /api/v1/imports`
   After connection, request the first 90-day transaction backfill for the connected account.
3. `POST /api/v1/exports/quarterly`
   Once quarter readiness reaches zero blockers, request an asynchronous quarterly pack export.
4. `GET /api/v1/exports/{exportId}`
   Poll until the export completes, then use the returned signed download URL.

## Example Client Sequence

### 1. Connect a bank account

```http
POST /api/v1/bank-feeds/connect
Authorization: Bearer <token>
Idempotency-Key: connect-usr_54cf9c9f-2026-q1
Content-Type: application/json

{
  "provider": {
    "provider_name": "monzo",
    "institution_id": "monzo-uk-retail"
  },
  "business_profile_id": "bpf_8fe52c9d",
  "redirect_uri": "https://mobile.example.com/open-banking/callback",
  "consent": {
    "access_scope": ["accounts", "transactions"],
    "valid_for_days": 90
  }
}
```

The response returns a `connection_id`, a provisional `bank_account`, and an
`authorization_url` for the client redirect step.

### 2. Trigger the first import

```http
POST /api/v1/imports
Authorization: Bearer <token>
Idempotency-Key: import-ba_71a79f54-first-connect
Content-Type: application/json

{
  "bank_account_id": "ba_71a79f54",
  "import_triggered_by": "first_connect",
  "requested_window_days": 90,
  "from_date": "2025-12-19",
  "quarter_hint": "2026-Q1"
}
```

The service returns `202 Accepted` with an `import_run_id`. The import is intentionally
asynchronous because provider fetch + normalization may span multiple pages and duplicate
suppression checks.

Integration note:
The future backend implementation should map provider transactions into the canonical
`BankTransaction` shape already defined in
`solution/backend/src/models/mvp_domain_schemas.json`, using the same source-hash and
dedupe semantics already established in `solution/backend/src/services/openBankingAdapter.js`
and `solution/backend/src/services/transactionImportService.js`.

### 3. Request quarterly export generation

```http
POST /api/v1/exports/quarterly
Authorization: Bearer <token>
Idempotency-Key: export-qtr_2026_q1
Content-Type: application/json

{
  "quarter_id": "qtr_2026_q1",
  "export_format": "quarterly_pack",
  "include_files": [
    "Transactions.csv",
    "EvidenceIndex.csv",
    "QuarterlySummary.csv",
    "QuarterlyPack.pdf"
  ],
  "requested_by": {
    "channel": "mobile_app",
    "actor_id": "usr_54cf9c9f"
  },
  "delivery": {
    "mode": "download_url",
    "expires_in_minutes": 30
  }
}
```

This request should fail with `409 Conflict` if the quarter still has unresolved blockers
or an identical export is already in progress.

### 4. Poll export status and download

```http
GET /api/v1/exports/exp_8b91e9a2
Authorization: Bearer <token>
```

When the export is complete, the response includes:

- `file_bundle.download_url` for the zip archive
- `file_bundle.expires_at` for signed URL expiry
- `files[]` metadata so clients can confirm all deliverables are present

## Error Semantics

- `401 Unauthorized`: bearer token missing, expired, or invalid.
- `404 Not Found`: referenced bank account, quarter, or export does not belong to the user.
- `409 Conflict`: duplicate in-flight request, unresolved quarter blockers, or connection state mismatch.
- `422 Validation Error`: malformed request body, unsupported provider, or missing required fields.
- `503 Service Unavailable`: bank provider outage, consent service outage, or export infrastructure unavailable.

## Idempotency Notes

- `POST /api/v1/bank-feeds/connect`
  Reusing the same idempotency key with the same payload should return the original pending consent session.
- `POST /api/v1/imports`
  Reusing the same idempotency key should return the original import job reference rather than create a second import run.
- `POST /api/v1/exports/quarterly`
  Reusing the same idempotency key should return the same `export_id` while the export request fingerprint remains unchanged.

## Consumer Notes

- Mobile clients can optimistically move the user from connect to import to quarter readiness, but should still rely on backend status fields as source of truth.
- Web clients may use the same contract without changes; the only client-specific field expected today is `requested_by.channel`.
- The contract is stable enough for frontend mocks, QA harnesses, and future generated clients before full backend implementation lands.
