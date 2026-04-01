-- Notification Engine additive migration [V20260311_1638]
-- Project: bizPA MVP Workstream G

ALTER TABLE notification_events
  ADD COLUMN IF NOT EXISTS severity TEXT,
  ADD COLUMN IF NOT EXISTS delivery_status TEXT NOT NULL DEFAULT 'queued',
  ADD COLUMN IF NOT EXISTS displayed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS linked_target JSONB,
  ADD COLUMN IF NOT EXISTS condition_key TEXT,
  ADD COLUMN IF NOT EXISTS trace JSONB;

UPDATE notification_events
SET
  severity = COALESCE(severity, priority),
  delivery_status = CASE
    WHEN is_dismissed = TRUE THEN 'dismissed'
    ELSE COALESCE(delivery_status, 'queued')
  END,
  linked_target = COALESCE(
    linked_target,
    CASE
      WHEN action_link IS NOT NULL THEN jsonb_build_object(
        'kind', 'screen',
        'route', action_link,
        'workflow', action_link,
        'label', 'Review',
        'entity_id', source_entity_id,
        'entity_type', source_entity_name
      )
      ELSE NULL
    END
  ),
  condition_key = COALESCE(
    condition_key,
    lower(
      regexp_replace(
        concat_ws(':', category, source_entity_id::text, coalesce(source_entity_name, ''), coalesce(title, '')),
        '[^a-zA-Z0-9:]+',
        '_',
        'g'
      )
    )
  ),
  trace = COALESCE(trace, '{}'::jsonb)
WHERE TRUE;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'notification_events_delivery_status_chk'
  ) THEN
    ALTER TABLE notification_events
      ADD CONSTRAINT notification_events_delivery_status_chk
      CHECK (delivery_status IN ('queued', 'displayed', 'dismissed', 'failed'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_notification_events_condition_active
  ON notification_events(user_id, condition_key)
  WHERE is_dismissed = FALSE;
