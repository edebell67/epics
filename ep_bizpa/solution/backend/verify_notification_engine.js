const assert = require('assert');
const {
  buildNotificationEngine,
  sortNotifications
} = require('./src/services/notificationService');

const fixture = {
  now: '2026-03-11T16:40:00.000Z',
  overdueInvoices: [
    {
      id: 'inv-200',
      reference_number: 'INV-200',
      gross_amount: 1200,
      due_date: '2026-03-05T00:00:00.000Z'
    }
  ],
  readiness: {
    quarter_reference: 'Q1-2026',
    readiness_pct: 82,
    blocking_txns_count: 3,
    total_txns_in_period: 18,
    can_export: false
  },
  previousReadiness: {
    readiness_pct: 96,
    blocking_txns_count: 1
  },
  snapshotStatus: {
    quarter_reference: 'Q1-2026',
    changed_since_snapshot: true,
    quarter_lifecycle: {
      status: 'closed'
    },
    latest_snapshot: {
      snapshot_id: 'snap-q1-v2',
      version_number: 2,
      created_at: '2026-03-08T10:00:00.000Z'
    }
  },
  syncHealth: {
    backlog_size: 12,
    error_rate: 0.25,
    last_successful_sync: '2026-03-10T08:00:00.000Z',
    recent_conflicts: [{ id: 'c1' }]
  },
  deadlines: [
    {
      source: 'event',
      id: 'evt-1',
      title: 'VAT review meeting',
      description: 'Review Q1 VAT pack before submission handoff.',
      date: '2026-03-12T09:00:00.000Z',
      type: 'meeting'
    },
    {
      source: 'item',
      id: 'quote-9',
      title: 'Quote follow-up',
      description: 'Customer quote expires soon.',
      date: '2026-03-13T12:00:00.000Z',
      type: 'quote'
    }
  ],
  operationalEvents: [
    {
      event_id: 'be-1',
      event_type: 'quarter_reopened',
      entity_id: 'quarter-q1',
      entity_type: 'quarter',
      created_at: '2026-03-11T15:00:00.000Z',
      description: 'Quarter reopened after late supplier invoice.'
    },
    {
      event_id: 'be-2',
      event_type: 'snapshot_created',
      entity_id: 'snap-q1-v2',
      entity_type: 'snapshot',
      created_at: '2026-03-08T10:00:00.000Z',
      description: 'Quarter snapshot generated.'
    }
  ]
};

const verifyNotificationEngine = () => {
  const engine = buildNotificationEngine(fixture);
  const notifications = engine.notifications;

  assert(notifications.length >= 6, `Expected multiple notifications, received ${notifications.length}`);
  assert(engine.health.by_severity.critical > 0, 'Expected at least one critical notification');
  assert(engine.health.by_severity.important > 0, 'Expected at least one important notification');
  assert(engine.health.by_severity.informational > 0, 'Expected at least one informational notification');

  const overdueInvoice = notifications.find((entry) => entry.category === 'overdue_invoice');
  assert(overdueInvoice, 'Expected overdue invoice notification');
  assert.strictEqual(overdueInvoice.severity, 'critical');
  assert(overdueInvoice.linked_target?.route, 'Expected actionable linked target on overdue invoice notification');

  const snapshotStale = notifications.find((entry) => entry.category === 'stale_snapshot');
  assert(snapshotStale, 'Expected stale snapshot notification');
  assert.strictEqual(snapshotStale.severity, 'critical');

  const readinessBlocked = notifications.find((entry) => entry.condition_key === 'readiness_blocked:q1_2026');
  assert(readinessBlocked, 'Expected readiness-blocked notification');

  const queueStatuses = new Set(engine.queue.map((entry) => entry.delivery_status));
  assert.deepStrictEqual(Array.from(queueStatuses), ['queued']);

  const deduped = buildNotificationEngine({
    ...fixture,
    deadlines: fixture.deadlines.concat({
      source: 'event',
      id: 'evt-1',
      title: 'VAT review meeting',
      description: 'Review Q1 VAT pack before submission handoff.',
      date: '2026-03-12T09:00:00.000Z',
      type: 'meeting'
    })
  });
  const deadlineConditionKeys = deduped.notifications
    .filter((entry) => entry.category === 'deadline')
    .map((entry) => entry.condition_key);
  assert.strictEqual(new Set(deadlineConditionKeys).size, deadlineConditionKeys.length, 'Expected deadline notifications to be deduped by condition');

  const sorted = sortNotifications(notifications);
  assert.strictEqual(sorted[0].severity, 'critical', 'Expected critical items to sort first');

  return {
    notification_count: notifications.length,
    queue_count: engine.queue.length
  };
};

try {
  const result = verifyNotificationEngine();
  console.log('verify_notification_engine=PASS');
  console.log(JSON.stringify(result));
} catch (error) {
  console.error('verify_notification_engine=FAIL');
  console.error(error.message);
  process.exit(1);
}
