-- Sync Layer Migration [V20260222_2230]
-- Project: bizPA (Cloud Sync Layer)

-- 1. Create users table for multi-tenant support
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create sync_devices table
CREATE TABLE IF NOT EXISTS sync_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL,
    device_name TEXT,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, device_id)
);

-- 3. Add user_id and last_synced_at to core tables
-- Also add deleted_at for soft deletes (essential for delta sync)

-- clients
ALTER TABLE clients ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- jobs
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- capture_items
ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- calendar_events
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- diary_entries
ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE diary_entries ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- outreach_logs
ALTER TABLE outreach_logs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE outreach_logs ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE outreach_logs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- message_templates (can be global or per user, let's make it per user for now)
ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE message_templates ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- trigger_rules
ALTER TABLE trigger_rules ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE trigger_rules ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE trigger_rules ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 4. Create indexes for sync performance
CREATE INDEX IF NOT EXISTS idx_clients_user_sync ON clients(user_id, last_synced_at);
CREATE INDEX IF NOT EXISTS idx_jobs_user_sync ON jobs(user_id, last_synced_at);
CREATE INDEX IF NOT EXISTS idx_capture_items_user_sync ON capture_items(user_id, last_synced_at);
CREATE INDEX IF NOT EXISTS idx_calendar_events_user_sync ON calendar_events(user_id, last_synced_at);

-- 5. Helper to get delta changes for a user/device
-- This function will be used by the API to fetch changes since last sync
CREATE OR REPLACE FUNCTION get_delta_changes(p_user_id UUID, p_since TIMESTAMPTZ)
RETURNS TABLE (
    table_name TEXT,
    entity_id UUID,
    action TEXT,
    data JSONB
) AS $$
BEGIN
    -- This is a conceptual implementation. 
    -- In a real delta sync, we might want to query each table and union the results.
    -- For now, we'll return an empty set or a simplified union.
    RETURN QUERY
    SELECT 'clients'::TEXT, id, 'upsert'::TEXT, to_jsonb(c) FROM clients c WHERE user_id = p_user_id AND (updated_at > p_since OR created_at > p_since) AND deleted_at IS NULL
    UNION ALL
    SELECT 'clients'::TEXT, id, 'delete'::TEXT, NULL::JSONB FROM clients WHERE user_id = p_user_id AND deleted_at > p_since
    UNION ALL
    SELECT 'jobs'::TEXT, id, 'upsert'::TEXT, to_jsonb(j) FROM jobs j WHERE user_id = p_user_id AND (updated_at > p_since OR created_at > p_since) AND deleted_at IS NULL
    UNION ALL
    SELECT 'jobs'::TEXT, id, 'delete'::TEXT, NULL::JSONB FROM jobs WHERE user_id = p_user_id AND deleted_at > p_since
    UNION ALL
    SELECT 'capture_items'::TEXT, id, 'upsert'::TEXT, to_jsonb(ci) FROM capture_items ci WHERE user_id = p_user_id AND (updated_at > p_since OR created_at > p_since) AND deleted_at IS NULL
    UNION ALL
    SELECT 'capture_items'::TEXT, id, 'delete'::TEXT, NULL::JSONB FROM capture_items WHERE user_id = p_user_id AND deleted_at > p_since;
END;
$$ LANGUAGE plpgsql;
