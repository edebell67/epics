-- Fix Data Entry and Isolation [V20260223_0945]
-- Project: bizPA (Data Entry Fix)

-- 1. Ensure the default user exists to satisfy foreign key constraints
INSERT INTO users (id, email, password_hash, full_name)
VALUES ('00000000-0000-0000-0000-000000000000', 'default@bizpa.local', 'n/a', 'Default User')
ON CONFLICT (id) DO NOTHING;

-- 2. Backfill existing data with the default user ID so it becomes visible under the new isolation rules
UPDATE clients SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE jobs SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE capture_items SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE calendar_events SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE diary_entries SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE outreach_logs SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE message_templates SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
UPDATE trigger_rules SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;

-- 3. Ensure tenant_config exists for the default user
INSERT INTO tenant_config (user_id)
VALUES ('00000000-0000-0000-0000-000000000000')
ON CONFLICT (user_id) DO NOTHING;
