-- Transaction import checkpoint and diagnostics migration [V20260318_1835]
-- Additive schema changes for idempotent 90-day bank-feed backfill and refresh behavior.

ALTER TABLE bank_transactions
    ADD COLUMN IF NOT EXISTS provider_txn_id TEXT,
    ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'GBP',
    ADD COLUMN IF NOT EXISTS booking_status TEXT,
    ADD COLUMN IF NOT EXISTS source_hash TEXT;

UPDATE bank_transactions
SET source_hash = md5(
    concat_ws(
        '|',
        bank_account_id::text,
        coalesce(bank_txn_ref, ''),
        coalesce(txn_date::text, ''),
        coalesce(amount::text, ''),
        coalesce(direction, ''),
        coalesce(merchant, ''),
        coalesce(description, ''),
        coalesce(posted_at::text, '')
    )
)
WHERE source_hash IS NULL;

ALTER TABLE bank_transactions
    ALTER COLUMN source_hash SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_transactions_account_source_hash
    ON bank_transactions (bank_account_id, source_hash);

CREATE TABLE IF NOT EXISTS bank_import_checkpoints (
    bank_account_id UUID PRIMARY KEY REFERENCES bank_accounts(id) ON DELETE CASCADE,
    last_attempt_at TIMESTAMPTZ,
    last_successful_import_at TIMESTAMPTZ,
    last_status TEXT NOT NULL DEFAULT 'never' CHECK (last_status IN ('never', 'completed', 'failed')),
    last_error TEXT,
    last_requested_window_days INTEGER NOT NULL DEFAULT 90,
    last_backfill_start_date DATE,
    last_successful_cursor TEXT,
    last_received_count INTEGER NOT NULL DEFAULT 0,
    last_inserted_count INTEGER NOT NULL DEFAULT 0,
    last_duplicate_suppressed_count INTEGER NOT NULL DEFAULT 0,
    last_skipped_invalid_count INTEGER NOT NULL DEFAULT 0,
    latest_transaction_date DATE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bank_import_runs (
    import_run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bank_account_id UUID NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider_name TEXT NOT NULL,
    import_triggered_by TEXT NOT NULL,
    requested_window_days INTEGER NOT NULL DEFAULT 90,
    from_date DATE,
    cursor_used TEXT,
    fetch_started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    received_count INTEGER NOT NULL DEFAULT 0,
    normalized_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    duplicate_suppressed_count INTEGER NOT NULL DEFAULT 0,
    skipped_invalid_count INTEGER NOT NULL DEFAULT 0,
    skipped_reasons JSONB NOT NULL DEFAULT '{}'::jsonb,
    latest_transaction_date DATE,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_bank_import_runs_account_started
    ON bank_import_runs (bank_account_id, fetch_started_at DESC);
