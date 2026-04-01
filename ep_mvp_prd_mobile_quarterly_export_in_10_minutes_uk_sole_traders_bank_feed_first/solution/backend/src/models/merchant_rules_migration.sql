-- Merchant Categorisation Rules Migration [V20260322_1730]
-- Persists user-defined merchant patterns for recurring classification defaults.

CREATE TABLE IF NOT EXISTS merchant_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope TEXT NOT NULL CHECK (scope IN ('merchant_pattern')),
    merchant_pattern TEXT NOT NULL,
    category_code TEXT NOT NULL,
    default_business_personal TEXT CHECK (default_business_personal IN ('BUSINESS', 'PERSONAL')),
    default_split_business_pct INTEGER CHECK (default_split_business_pct >= 0 AND default_split_business_pct <= 100),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_merchant_rules_user_id ON merchant_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_merchant_rules_pattern ON merchant_rules(merchant_pattern);

-- Unique constraint per user and pattern to prevent duplicate rules
CREATE UNIQUE INDEX IF NOT EXISTS idx_merchant_rules_user_pattern ON merchant_rules(user_id, merchant_pattern);

CREATE TRIGGER trg_merchant_rules_updated_at
    BEFORE UPDATE ON merchant_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
