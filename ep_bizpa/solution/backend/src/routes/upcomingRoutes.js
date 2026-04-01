const express = require('express');
const router = express.Router();
const db = require('../config/db');
const { deriveQuarterBounds, buildReadinessReport } = require('../services/readinessService');
const { getQuarterSnapshotStatus } = require('../services/snapshotVersioningService');
const { loadSyncHealthSnapshot } = require('../services/syncHealthService');
const { buildNotificationEngine } = require('../services/notificationService');

const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000000';

const listReadinessTransactions = async (userId, quarterBounds) => {
  const result = await db.query(
    `
    SELECT
      id,
      type,
      status,
      payment_status,
      amount,
      net_amount,
      gross_amount,
      vat_amount,
      vat_rate,
      vat_type,
      txn_date,
      due_date,
      merchant,
      counterparty_reference,
      client_id,
      supplier_id,
      category_code,
      business_personal,
      is_split,
      split_business_pct,
      duplicate_flag,
      duplicate_resolution,
      correction_pending,
      changed_since_snapshot,
      post_snapshot_change_pending,
      reference_number,
      extracted_text,
      notes
    FROM capture_items
    WHERE user_id = $1
      AND deleted_at IS NULL
      AND txn_date >= $2
      AND txn_date <= $3
    `,
    [userId, quarterBounds.period_start, quarterBounds.period_end]
  );
  return result.rows;
};

const loadLatestReadinessSnapshot = async (userId, quarterReference) => {
  const result = await db.query(
    `
    SELECT metadata, created_at
    FROM business_event_log
    WHERE user_id = $1
      AND event_type = 'readiness_recalculated'
      AND quarter_reference = $2
    ORDER BY created_at DESC
    LIMIT 1
    `,
    [userId, quarterReference]
  );

  if (!result.rows[0]) {
    return null;
  }

  return {
    ...(result.rows[0].metadata || {}),
    created_at: result.rows[0].created_at
  };
};

const listOverdueInvoices = async (userId) => {
  const result = await db.query(
    `
    SELECT id, reference_number, amount, gross_amount, due_date, payment_status
    FROM capture_items
    WHERE user_id = $1
      AND type = 'invoice'
      AND deleted_at IS NULL
      AND due_date IS NOT NULL
      AND due_date < CURRENT_DATE
      AND COALESCE(payment_status, '') <> 'paid'
    `,
    [userId]
  );
  return result.rows;
};

const listNotificationDeadlines = async (userId) => {
  const result = await db.query(
    `
    SELECT 'event' AS source, id, title, title AS description, start_at AS date, event_type AS type
    FROM calendar_events
    WHERE user_id = $1
      AND deleted_at IS NULL
      AND start_at >= NOW()
      AND start_at <= NOW() + INTERVAL '72 hours'
    UNION ALL
    SELECT 'item' AS source, id, extracted_text AS title, extracted_text AS description, due_date::timestamptz AS date, type
    FROM capture_items
    WHERE user_id = $1
      AND deleted_at IS NULL
      AND due_date >= CURRENT_DATE
      AND due_date <= CURRENT_DATE + INTERVAL '3 days'
      AND COALESCE(status, '') <> 'archived'
    ORDER BY date ASC
    `,
    [userId]
  );
  return result.rows;
};

const listOperationalNotificationEvents = async (userId, quarterReference) => {
  const result = await db.query(
    `
    SELECT event_id, event_type, entity_id, entity_type, created_at, description
    FROM business_event_log
    WHERE user_id = $1
      AND quarter_reference = $2
      AND event_type = ANY($3)
    ORDER BY created_at DESC
    LIMIT 6
    `,
    [userId, quarterReference, ['snapshot_created', 'quarter_closed', 'quarter_reopened']]
  );
  return result.rows;
};

router.get('/', async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const eventsQuery = `
      SELECT 'event' as source, id, title as description, start_at as date, event_type as type
      FROM calendar_events
      WHERE start_at >= CURRENT_DATE AND user_id = $1 AND deleted_at IS NULL
      UNION ALL
      SELECT 'item' as source, id, extracted_text as description, due_date as date, type
      FROM capture_items
      WHERE due_date >= CURRENT_DATE AND user_id = $1 AND deleted_at IS NULL
      ORDER BY date ASC
    `;
    const result = await db.query(eventsQuery, [userId]);
    res.json(result.rows);
  } catch (err) {
    console.error('[UpcomingRoute] Error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

router.get('/notifications', async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const quarterBounds = deriveQuarterBounds(new Date().toISOString().slice(0, 10));
    const [
      overdueInvoices,
      readinessTransactions,
      previousReadiness,
      deadlines,
      syncHealth,
      snapshotStatus,
      operationalEvents
    ] = await Promise.all([
      listOverdueInvoices(userId),
      listReadinessTransactions(userId, quarterBounds),
      loadLatestReadinessSnapshot(userId, quarterBounds.quarter_reference),
      listNotificationDeadlines(userId),
      loadSyncHealthSnapshot(db, { tenantId: userId }),
      getQuarterSnapshotStatus(db, {
        userId,
        quarterReference: quarterBounds.quarter_reference
      }).catch(() => null),
      listOperationalNotificationEvents(userId, quarterBounds.quarter_reference)
    ]);

    const readiness = buildReadinessReport({
      periodStart: quarterBounds.period_start,
      periodEnd: quarterBounds.period_end,
      asOfDate: quarterBounds.as_of_date,
      transactions: readinessTransactions
    });

    const engine = buildNotificationEngine({
      now: new Date().toISOString(),
      overdueInvoices,
      readiness,
      previousReadiness,
      snapshotStatus,
      syncHealth,
      deadlines,
      operationalEvents
    });

    res.json(engine.notifications);
  } catch (err) {
    console.error('[NotificationRoute] Error:', err);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

module.exports = router;
