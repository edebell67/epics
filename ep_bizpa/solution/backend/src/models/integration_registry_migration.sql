CREATE TABLE IF NOT EXISTS integration_plugin_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plugin_id TEXT NOT NULL,
    plugin_type TEXT NOT NULL CHECK (
        plugin_type IN ('accounting_export', 'payments', 'communications', 'calendar')
    ),
    version TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    tenant_scope TEXT NOT NULL,
    rollout_stage TEXT NOT NULL DEFAULT 'planned' CHECK (
        rollout_stage IN ('planned', 'internal', 'pilot', 'beta', 'general_availability', 'disabled', 'rollback')
    ),
    rollback_target TEXT,
    contract_version TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT NOT NULL DEFAULT 'system',
    CONSTRAINT integration_plugin_registry_user_plugin_key UNIQUE (user_id, plugin_id)
);

CREATE INDEX IF NOT EXISTS idx_integration_plugin_registry_user_type
    ON integration_plugin_registry (user_id, plugin_type, enabled, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_integration_plugin_registry_scope
    ON integration_plugin_registry (user_id, tenant_scope, updated_at DESC);
