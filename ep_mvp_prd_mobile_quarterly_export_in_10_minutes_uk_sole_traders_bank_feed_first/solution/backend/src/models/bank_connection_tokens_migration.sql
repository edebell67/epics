-- Bank connection token storage [V20260321_1215]
-- Securely persists connection credentials required for read-only transaction sync.

CREATE TABLE IF NOT EXISTS bank_connection_tokens (
    bank_account_id UUID PRIMARY KEY REFERENCES bank_accounts(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    scopes TEXT[],
    provider_consent_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bank_tokens_expires_at ON bank_connection_tokens(expires_at);
