ALTER TABLE governance_settings
    ADD COLUMN IF NOT EXISTS owner_policy_allows_auto_commit BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS enabled_by TEXT,
    ADD COLUMN IF NOT EXISTS duration TEXT,
    ADD COLUMN IF NOT EXISTS max_allowed_duration TEXT NOT NULL DEFAULT 'daily',
    ADD COLUMN IF NOT EXISTS risk_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS confirmation_reference TEXT,
    ADD COLUMN IF NOT EXISTS threshold_override BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS threshold_override_limit NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS max_auto_commit_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS low_confidence_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.85,
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS policy_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE governance_settings
    ALTER COLUMN max_allowed_duration SET DEFAULT 'daily',
    ALTER COLUMN low_confidence_threshold SET DEFAULT 0.85,
    ALTER COLUMN max_auto_commit_amount SET DEFAULT 0;
