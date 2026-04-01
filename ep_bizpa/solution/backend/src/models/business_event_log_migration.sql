-- Immutable business event log for MVP audit/history views

CREATE TABLE IF NOT EXISTS business_event_log (
    event_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    entity_id UUID,
    entity_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    quarter_reference TEXT,
    status_from TEXT,
    status_to TEXT,
    CONSTRAINT business_event_log_type_chk CHECK (
        event_type IN (
            'entity_created',
            'entity_committed',
            'entity_status_changed',
            'entity_updated',
            'entity_voided',
            'entity_superseded',
            'payment_recorded',
            'quote_converted',
            'snapshot_created',
            'quarter_closed',
            'quarter_reopened',
            'auto_commit_enabled',
            'auto_commit_disabled',
            'auto_commit_expired',
            'governance_policy_changed',
            'readiness_recalculated',
            'export_generated'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_business_event_log_user_created
    ON business_event_log (user_id, created_at DESC, event_id DESC);

CREATE INDEX IF NOT EXISTS idx_business_event_log_entity
    ON business_event_log (user_id, entity_type, entity_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_business_event_log_quarter
    ON business_event_log (user_id, quarter_reference, created_at DESC);

CREATE TABLE IF NOT EXISTS governance_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    owner_policy_allows_auto_commit BOOLEAN NOT NULL DEFAULT FALSE,
    auto_commit_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    enabled_by TEXT,
    duration TEXT,
    max_allowed_duration TEXT NOT NULL DEFAULT 'daily',
    risk_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    confirmation_reference TEXT,
    threshold_override BOOLEAN NOT NULL DEFAULT FALSE,
    threshold_override_limit NUMERIC(12,2),
    max_auto_commit_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    low_confidence_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.85,
    expires_at TIMESTAMPTZ,
    policy_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT NOT NULL DEFAULT 'system'
);
