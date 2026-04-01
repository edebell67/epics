-- Notification Governance Migration [V20260223_0015]
-- Project: bizPA (Notification Triggers)

-- 1. Create notification_events table
CREATE TABLE IF NOT EXISTS notification_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT,
    priority TEXT NOT NULL CHECK (priority IN ('critical', 'important', 'informational')),
    category TEXT NOT NULL CHECK (category IN ('payment', 'quote', 'tax', 'milestone', 'system')),
    source_entity_name TEXT,
    source_entity_id UUID,
    is_dismissed BOOLEAN DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,
    action_link TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Add index for active notifications
CREATE INDEX IF NOT EXISTS idx_notifications_active ON notification_events(user_id, is_dismissed, priority DESC, created_at DESC);

-- 3. Function to trigger a notification
CREATE OR REPLACE FUNCTION trigger_notification(
    p_user_id UUID,
    p_title TEXT,
    p_message TEXT,
    p_priority TEXT,
    p_category TEXT,
    p_entity_name TEXT DEFAULT NULL,
    p_entity_id UUID DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_notif_id UUID;
BEGIN
    -- Avoid duplicate active notifications for the same entity and category
    IF p_entity_id IS NOT NULL THEN
        SELECT id INTO v_notif_id FROM notification_events 
        WHERE user_id = p_user_id AND source_entity_id = p_entity_id AND category = p_category AND is_dismissed = FALSE;
        
        IF v_notif_id IS NOT NULL THEN
            RETURN v_notif_id;
        END IF;
    END IF;

    INSERT INTO notification_events (user_id, title, message, priority, category, source_entity_name, source_entity_id)
    VALUES (p_user_id, p_title, p_message, p_priority, p_category, p_entity_name, p_entity_id)
    RETURNING id INTO v_notif_id;

    RETURN v_notif_id;
END;
$$ LANGUAGE plpgsql;

-- 4. Logic for Overdue Invoices
CREATE OR REPLACE FUNCTION check_and_trigger_overdue_notifications()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
    v_rec RECORD;
BEGIN
    FOR v_rec IN 
        SELECT id, user_id, reference_number, amount, due_date 
        FROM capture_items 
        WHERE type = 'invoice' AND payment_status = 'overdue' 
        AND deleted_at IS NULL
    LOOP
        PERFORM trigger_notification(
            v_rec.user_id,
            'Overdue Invoice: ' || v_rec.reference_number,
            'Invoice for £' || v_rec.amount || ' was due on ' || v_rec.due_date,
            'critical',
            'payment',
            'capture_items',
            v_rec.id
        );
        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- 5. Logic for Milestone (simplified)
CREATE OR REPLACE FUNCTION check_revenue_milestones(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
    v_total DECIMAL;
    v_triggered INTEGER := 0;
BEGIN
    SELECT SUM(amount) INTO v_total FROM capture_items 
    WHERE user_id = p_user_id AND type IN ('payment', 'invoice') AND status = 'confirmed' AND deleted_at IS NULL;

    IF v_total >= 10000 THEN
        PERFORM trigger_notification(
            p_user_id,
            'Goal Achieved! 🎉',
            'You have reached £10,000 in total revenue. Great job!',
            'informational',
            'milestone'
        );
        v_triggered := 1;
    END IF;
    
    RETURN v_triggered;
END;
$$ LANGUAGE plpgsql;
