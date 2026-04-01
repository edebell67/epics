-- MVP Quarterly Export Pivot Migration [V20260305_1930]
-- Additive migration aligned to:
-- workstream/000_backlog/mvp_prd_quarterly_export_10min.md

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Bank connection metadata
CREATE TABLE IF NOT EXISTS bank_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider_name TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    account_name TEXT,
    currency TEXT NOT NULL DEFAULT 'GBP',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'error')),
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, provider_name, provider_account_id)
);

-- Canonical transaction store from bank feeds
CREATE TABLE IF NOT EXISTS bank_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bank_account_id UUID NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    bank_txn_ref TEXT NOT NULL,
    txn_date DATE NOT NULL,
    posted_at TIMESTAMPTZ,
    merchant TEXT,
    amount NUMERIC(18,2) NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('in', 'out')),
    description TEXT,
    balance NUMERIC(18,2),
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw_payload JSONB,
    duplicate_flag BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_resolution TEXT CHECK (duplicate_resolution IN ('dismiss', 'merge')),
    duplicate_of_txn_id UUID REFERENCES bank_transactions(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (bank_account_id, bank_txn_ref)
);

-- PRD classification model
CREATE TABLE IF NOT EXISTS transaction_classifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bank_txn_id UUID NOT NULL REFERENCES bank_transactions(id) ON DELETE CASCADE,
    category_code TEXT,
    category_name TEXT,
    business_personal TEXT CHECK (business_personal IN ('BUSINESS', 'PERSONAL')),
    is_split BOOLEAN NOT NULL DEFAULT FALSE,
    split_business_pct SMALLINT CHECK (split_business_pct BETWEEN 0 AND 100),
    confidence NUMERIC(4,3) CHECK (confidence >= 0 AND confidence <= 1),
    review_required BOOLEAN NOT NULL DEFAULT FALSE,
    source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'rule', 'model', 'import')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (bank_txn_id)
);

-- Explicit edit history for user changes
CREATE TABLE IF NOT EXISTS transaction_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bank_txn_id UUID NOT NULL REFERENCES bank_transactions(id) ON DELETE CASCADE,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    field_name TEXT NOT NULL,
    previous_value JSONB,
    new_value JSONB,
    change_source TEXT NOT NULL DEFAULT 'ui' CHECK (change_source IN ('ui', 'voice', 'rule', 'system'))
);

-- Evidence capture
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('RECEIPT', 'INVOICE', 'OTHER')),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    doc_date DATE,
    merchant TEXT,
    amount NUMERIC(18,2),
    storage_link TEXT NOT NULL,
    extraction_confidence NUMERIC(4,3) CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
    extraction_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Evidence->bank matching with confirmation
CREATE TABLE IF NOT EXISTS evidence_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    bank_txn_id UUID REFERENCES bank_transactions(id) ON DELETE SET NULL,
    link_confidence NUMERIC(4,3) CHECK (link_confidence >= 0 AND link_confidence <= 1),
    user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_at TIMESTAMPTZ,
    method TEXT NOT NULL DEFAULT 'suggested' CHECK (method IN ('suggested', 'manual', 'voice')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (evidence_id, bank_txn_id)
);

-- Quarter tracking and metrics
CREATE TABLE IF NOT EXISTS quarters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'ready', 'exported')),
    exported_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, period_start, period_end)
);

ALTER TABLE quarters
    DROP CONSTRAINT IF EXISTS quarters_status_check;

ALTER TABLE quarters
    ADD COLUMN IF NOT EXISTS quarter_label TEXT,
    ADD COLUMN IF NOT EXISTS quarter_state TEXT NOT NULL DEFAULT 'open',
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reopened_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reopen_reason TEXT,
    ADD COLUMN IF NOT EXISTS confirmation_reference TEXT,
    ADD COLUMN IF NOT EXISTS governance_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE quarters
    ALTER COLUMN status SET DEFAULT 'open';

DO $$
BEGIN
    ALTER TABLE quarters
        ADD CONSTRAINT quarters_status_check CHECK (status IN ('open', 'ready', 'exported', 'closed'));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE quarters
        ADD CONSTRAINT quarters_quarter_state_check CHECK (quarter_state IN ('open', 'closed', 'ready', 'exported'));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

UPDATE quarters
SET
    quarter_label = COALESCE(
        quarter_label,
        CONCAT(
            'Q',
            EXTRACT(QUARTER FROM period_start)::INT,
            '-',
            EXTRACT(YEAR FROM period_start)::INT
        )
    ),
    quarter_state = CASE
        WHEN status = 'closed' THEN 'closed'
        ELSE COALESCE(quarter_state, status, 'open')
    END
WHERE quarter_label IS NULL
   OR quarter_state IS NULL;

CREATE TABLE IF NOT EXISTS quarter_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quarter_id UUID NOT NULL REFERENCES quarters(id) ON DELETE CASCADE,
    total_txns_in_period INTEGER NOT NULL DEFAULT 0,
    blocking_txns_count INTEGER NOT NULL DEFAULT 0,
    readiness_pct SMALLINT NOT NULL DEFAULT 0 CHECK (readiness_pct BETWEEN 0 AND 100),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (quarter_id)
);

-- Merchant and default action rules
CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    merchant_pattern TEXT NOT NULL,
    category_code TEXT,
    category_name TEXT,
    default_business_personal TEXT CHECK (default_business_personal IN ('BUSINESS', 'PERSONAL')),
    default_split_business_pct SMALLINT CHECK (default_split_business_pct BETWEEN 0 AND 100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance and queue operations
CREATE INDEX IF NOT EXISTS idx_bank_accounts_user_status ON bank_accounts(user_id, status);
CREATE INDEX IF NOT EXISTS idx_bank_txn_user_date ON bank_transactions(user_id, txn_date DESC);
CREATE INDEX IF NOT EXISTS idx_bank_txn_duplicate ON bank_transactions(user_id, duplicate_flag, duplicate_resolution);
CREATE INDEX IF NOT EXISTS idx_classifications_blockers ON transaction_classifications(user_id, category_code, business_personal, is_split, split_business_pct);
CREATE INDEX IF NOT EXISTS idx_quarter_metrics_user ON quarter_metrics(user_id, quarter_id);
CREATE INDEX IF NOT EXISTS idx_evidence_user_captured ON evidence(user_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_rules_user_active ON rules(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_bank_txn_merchant_trgm ON bank_transactions USING gin (merchant gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_evidence_merchant_trgm ON evidence USING gin (merchant gin_trgm_ops);
