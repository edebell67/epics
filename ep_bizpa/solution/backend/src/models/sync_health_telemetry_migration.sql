-- Sync Health Telemetry Migration [V20260311_2028]
-- Project: bizPA (Sync guardrails and governance telemetry)

CREATE TABLE IF NOT EXISTS sync_run_telemetry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('push', 'pull')),
    status TEXT NOT NULL CHECK (status IN ('success', 'partial', 'error')),
    total_changes INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    conflict_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    backlog_size INTEGER NOT NULL DEFAULT 0,
    error_rate NUMERIC(8,4) NOT NULL DEFAULT 0,
    last_successful_sync TIMESTAMPTZ,
    conflict_samples JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_samples JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sync_run_telemetry_user_completed
    ON sync_run_telemetry(user_id, completed_at DESC);

CREATE INDEX IF NOT EXISTS idx_sync_run_telemetry_user_device_completed
    ON sync_run_telemetry(user_id, device_id, completed_at DESC);
