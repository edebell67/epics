-- Master PostgreSQL Schema [V20260219_1500]
-- Project: bizPA (Voice-First Small Trader Capture App)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core Schema (Milestone 1)

-- 1. clients
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    consent_to_contact BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_contacted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. jobs
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    service_category TEXT,
    status TEXT NOT NULL DEFAULT 'lead' CHECK (status IN ('lead', 'quoted', 'booked', 'in_progress', 'completed', 'lost')),
    value_estimate DECIMAL(18,2),
    next_due_date DATE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. capture_items
CREATE TABLE IF NOT EXISTS capture_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    captured_at TIMESTAMPTZ,
    type TEXT NOT NULL CHECK (type IN ('invoice', 'receipt', 'payment', 'image', 'note', 'voice', 'misc', 'booking', 'quote', 'reminder')),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'confirmed', 'reconciled', 'archived')),
    amount DECIMAL(18,2),
    currency TEXT DEFAULT 'GBP',
    tax_flag BOOLEAN DEFAULT FALSE,
    vat_amount DECIMAL(18,2),
    due_date DATE,
    counterparty_id UUID,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    extracted_text TEXT,
    extraction_confidence REAL,
    raw_note TEXT,
    location TEXT,
    device_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    voice_command_source_text TEXT,
    voice_action_confidence REAL
);

-- 4. capture_item_labels
CREATE TABLE IF NOT EXISTS capture_item_labels (
    item_id UUID NOT NULL REFERENCES capture_items(id) ON DELETE CASCADE,
    label_name TEXT NOT NULL,
    PRIMARY KEY (item_id, label_name)
);

-- 5. capture_item_attachments
CREATE TABLE IF NOT EXISTS capture_item_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID NOT NULL REFERENCES capture_items(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('image', 'pdf', 'audio')),
    file_path TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. voice_events
CREATE TABLE IF NOT EXISTS voice_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    intent_transcript TEXT NOT NULL,
    intent_name TEXT NOT NULL,
    slot_data JSONB,
    confidence REAL NOT NULL,
    action_result TEXT NOT NULL CHECK (action_result IN ('success', 'clarification_needed', 'failure', 'canceled')),
    confirmation_text TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. job_queue
CREATE TABLE IF NOT EXISTS job_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type TEXT NOT NULL CHECK (task_type IN ('ocr', 'transcription', 'sync_push', 'sync_pull')),
    item_id UUID REFERENCES capture_items(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    retry_count INTEGER DEFAULT 0,
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    run_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 8. audit_events
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    entity_id UUID NOT NULL,
    user_id UUID NOT NULL,
    device_id TEXT NOT NULL,
    diff_log JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Plugin-ready Tables

-- 9. calendar_events
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'canceled')),
    client_id UUID REFERENCES clients(id),
    job_id UUID REFERENCES jobs(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 10. diary_entries
CREATE TABLE IF NOT EXISTS diary_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_date DATE NOT NULL,
    content TEXT NOT NULL,
    client_id UUID REFERENCES clients(id),
    job_id UUID REFERENCES jobs(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 11. message_templates
CREATE TABLE IF NOT EXISTS message_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('reservice', 'payment_chase', 'referral')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 12. trigger_rules
CREATE TABLE IF NOT EXISTS trigger_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('time_since_last_job', 'seasonal', 'unpaid_invoice')),
    trigger_config JSONB NOT NULL,
    action_template_id UUID REFERENCES message_templates(id),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 13. outreach_logs
CREATE TABLE IF NOT EXISTS outreach_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id),
    job_id UUID REFERENCES jobs(id),
    channel TEXT NOT NULL CHECK (channel IN ('sms', 'whatsapp', 'email', 'phone')),
    message_content TEXT NOT NULL,
    outcome TEXT CHECK (outcome IN ('replied', 'booked', 'declined', 'no_response')),
    sent_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    follow_up_due_at TIMESTAMPTZ
);

-- 14. teams
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_user_id UUID NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 15. team_members
CREATE TABLE IF NOT EXISTS team_members (
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'field_staff', 'office_manager')),
    PRIMARY KEY (team_id, user_id)
);

-- 16. assignment_links
CREATE TABLE IF NOT EXISTS assignment_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('job', 'capture_item')),
    entity_id UUID NOT NULL,
    assigned_to_user_id UUID NOT NULL,
    assigned_by_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 17. voice_sessions
CREATE TABLE IF NOT EXISTS voice_sessions (
    device_id TEXT PRIMARY KEY,
    pending_intent TEXT,
    pending_slots JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 18. integration_plugin_registry
CREATE TABLE IF NOT EXISTS integration_plugin_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
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
    UNIQUE (user_id, plugin_id)
);

-- Indexes

CREATE INDEX IF NOT EXISTS idx_capture_items_created ON capture_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_capture_items_status ON capture_items(status, type);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_jobs_due ON jobs(next_due_date, status);
CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status, run_at);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_name, entity_id);
CREATE INDEX IF NOT EXISTS idx_integration_plugin_registry_user_type ON integration_plugin_registry(user_id, plugin_type, enabled, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_integration_plugin_registry_scope ON integration_plugin_registry(user_id, tenant_scope, updated_at DESC);

-- Triggers for updated_at

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER tr_update_clients BEFORE UPDATE ON clients FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_update_jobs BEFORE UPDATE ON jobs FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_update_capture_items BEFORE UPDATE ON capture_items FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_update_job_queue BEFORE UPDATE ON job_queue FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_update_calendar_events BEFORE UPDATE ON calendar_events FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_update_diary_entries BEFORE UPDATE ON diary_entries FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_update_trigger_rules BEFORE UPDATE ON trigger_rules FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER tr_update_integration_plugin_registry BEFORE UPDATE ON integration_plugin_registry FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Audit Triggers

CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    entity_id UUID;
    action_type TEXT;
    old_data JSONB := NULL;
    new_data JSONB := NULL;
BEGIN
    IF (TG_OP = 'INSERT') THEN
        entity_id = NEW.id;
        action_type = 'create';
        new_data = to_jsonb(NEW);
    ELSIF (TG_OP = 'UPDATE') THEN
        entity_id = NEW.id;
        action_type = 'update';
        old_data = to_jsonb(OLD);
        new_data = to_jsonb(NEW);
    ELSIF (TG_OP = 'DELETE') THEN
        entity_id = OLD.id;
        action_type = 'delete';
        old_data = to_jsonb(OLD);
    END IF;

    INSERT INTO audit_events (action_type, entity_name, entity_id, user_id, device_id, diff_log)
    VALUES (
        action_type, 
        TG_TABLE_NAME, 
        entity_id, 
        COALESCE(((COALESCE(new_data, old_data))->>'user_id')::UUID, '00000000-0000-0000-0000-000000000000'), 
        COALESCE((COALESCE(new_data, old_data))->>'device_id', 'system'),
        jsonb_build_object('old', old_data, 'new', new_data)
    );

    IF (TG_OP = 'DELETE') THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER tr_audit_capture_items AFTER INSERT OR UPDATE OR DELETE ON capture_items FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
CREATE TRIGGER tr_audit_clients AFTER INSERT OR UPDATE OR DELETE ON clients FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
CREATE TRIGGER tr_audit_jobs AFTER INSERT OR UPDATE OR DELETE ON jobs FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Full-Text Search (FTS) Support

ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE INDEX IF NOT EXISTS idx_capture_items_search ON capture_items USING GIN(search_vector);

CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = 
        setweight(to_tsvector('english', COALESCE(NEW.extracted_text, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.raw_note, '')), 'B');
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER tr_search_vector_update BEFORE INSERT OR UPDATE ON capture_items FOR EACH ROW EXECUTE FUNCTION update_search_vector();
