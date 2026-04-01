const assert = require('assert');
const { listBusinessActivityInbox } = require('./src/services/businessActivityInboxService');

class MockExecutor {
  constructor(events, items) {
    this.events = events;
    this.items = items;
  }

  async query(text, params) {
    const sql = text.replace(/\s+/g, ' ').trim();

    if (sql.includes('FROM business_event_log') && sql.includes('COUNT(*)::int AS total')) {
      const rows = this.filterEvents(params);
      return { rows: [{ total: rows.length }] };
    }

    if (sql.includes('FROM business_event_log') && sql.includes('SELECT event_id,')) {
      const rows = this.filterEvents(params);
      const limit = params[params.length - 2];
      const offset = params[params.length - 1];
      return {
        rows: rows
          .slice(offset, offset + limit)
          .map((event) => ({
            ...event,
            timestamp: event.created_at
          }))
      };
    }

    if (sql.includes('FROM capture_items ci')) {
      const userId = params[0];
      const ids = new Set(params[1]);
      return {
        rows: this.items.filter((item) => item.user_id === userId && ids.has(item.id))
      };
    }

    throw new Error(`Unsupported SQL in mock executor: ${sql}`);
  }

  filterEvents(params) {
    const userId = params[0];
    const excludedEventTypes = new Set(params[1] || []);

    return this.events
      .filter((event) => event.user_id === userId && !excludedEventTypes.has(event.event_type))
      .sort((a, b) => {
        if (a.created_at === b.created_at) {
          return String(b.event_id).localeCompare(String(a.event_id));
        }
        return String(b.created_at).localeCompare(String(a.created_at));
      });
  }
}

const userId = '00000000-0000-0000-0000-000000000000';

const events = [
  {
    event_id: 'evt-001',
    user_id: userId,
    event_type: 'entity_created',
    entity_id: 'inv-1',
    entity_type: 'invoice',
    created_at: '2026-03-11T12:00:00.000Z',
    actor_id: userId,
    source_type: 'manual',
    description: 'Invoice created',
    metadata: { commit_mode: 'manual' },
    quarter_reference: 'Q1-2026',
    status_from: null,
    status_to: 'draft'
  },
  {
    event_id: 'evt-002',
    user_id: userId,
    event_type: 'payment_recorded',
    entity_id: 'pay-1',
    entity_type: 'payment',
    created_at: '2026-03-11T12:05:00.000Z',
    actor_id: userId,
    source_type: 'manual',
    description: 'Payment received',
    metadata: {},
    quarter_reference: 'Q1-2026',
    status_from: null,
    status_to: 'confirmed'
  },
  {
    event_id: 'evt-002a',
    user_id: userId,
    event_type: 'entity_updated',
    entity_id: 'inv-1',
    entity_type: 'invoice',
    created_at: '2026-03-11T12:07:00.000Z',
    actor_id: userId,
    source_type: 'manual',
    description: 'Invoice due date updated',
    metadata: { updated_field: 'due_date', new_value: '2026-03-31' },
    quarter_reference: 'Q1-2026',
    status_from: null,
    status_to: null
  },
  {
    event_id: 'evt-003',
    user_id: userId,
    event_type: 'quote_converted',
    entity_id: 'quote-1',
    entity_type: 'quote',
    created_at: '2026-03-11T12:10:00.000Z',
    actor_id: userId,
    source_type: 'manual',
    description: 'Quote converted',
    metadata: { invoice_id: 'inv-2' },
    quarter_reference: 'Q1-2026',
    status_from: 'confirmed',
    status_to: 'converted'
  },
  {
    event_id: 'evt-004',
    user_id: userId,
    event_type: 'snapshot_created',
    entity_id: 'snap-1',
    entity_type: 'snapshot',
    created_at: '2026-03-11T12:15:00.000Z',
    actor_id: userId,
    source_type: 'system',
    description: 'Snapshot generated',
    metadata: {},
    quarter_reference: 'Q1-2026',
    status_from: null,
    status_to: 'generated'
  },
  {
    event_id: 'evt-005',
    user_id: userId,
    event_type: 'auto_commit_enabled',
    entity_id: null,
    entity_type: 'governance',
    created_at: '2026-03-11T12:20:00.000Z',
    actor_id: userId,
    source_type: 'manual',
    description: 'Auto-commit enabled',
    metadata: {},
    quarter_reference: null,
    status_from: null,
    status_to: null
  },
  {
    event_id: 'evt-006',
    user_id: userId,
    event_type: 'quarter_reopened',
    entity_id: 'quarter-1',
    entity_type: 'quarter',
    created_at: '2026-03-11T12:25:00.000Z',
    actor_id: userId,
    source_type: 'manual',
    description: 'Quarter reopened',
    metadata: { reason: 'Late invoice' },
    quarter_reference: 'Q1-2026',
    status_from: null,
    status_to: 'open'
  },
  {
    event_id: 'evt-007',
    user_id: userId,
    event_type: 'readiness_recalculated',
    entity_id: 'readiness-1',
    entity_type: 'readiness',
    created_at: '2026-03-11T12:30:00.000Z',
    actor_id: userId,
    source_type: 'system',
    description: 'Readiness recalculated',
    metadata: { blocking_txns_count: 0 },
    quarter_reference: 'Q1-2026',
    status_from: null,
    status_to: null
  }
];

const items = [
  {
    id: 'inv-1',
    user_id: userId,
    type: 'invoice',
    status: 'draft',
    payment_status: 'draft',
    amount: 500,
    gross_amount: 600,
    currency: 'GBP',
    client_id: 'client-1',
    reference_number: 'INV-001',
    client_name: 'Acme Ltd'
  },
  {
    id: 'pay-1',
    user_id: userId,
    type: 'payment',
    status: 'confirmed',
    payment_status: null,
    amount: 240,
    gross_amount: 240,
    currency: 'GBP',
    client_id: 'client-2',
    reference_number: 'PAY-001',
    client_name: 'John Smith'
  },
  {
    id: 'quote-1',
    user_id: userId,
    type: 'quote',
    status: 'confirmed',
    payment_status: null,
    amount: 1200,
    gross_amount: 1200,
    currency: 'GBP',
    client_id: 'client-3',
    reference_number: 'QT-001',
    client_name: 'Sarah Jones'
  }
];

const run = async () => {
  const mock = new MockExecutor(events, items);

  const all = await listBusinessActivityInbox(mock, {
    user_id: userId,
    filter: 'all',
    limit: 20,
    offset: 0
  });

  assert.strictEqual(all.items.length, 7, 'Expected 7 non-noise inbox items');
  assert(all.items.every((item, index) => index === 0 || item.timestamp <= all.items[index - 1].timestamp));
  assert(!all.items.some((item) => item.event_type === 'readiness_recalculated'));

  const newest = all.items[0];
  assert.strictEqual(newest.event_type, 'quarter_reopened');
  assert(newest.needs_review_badge, 'Quarter reopen should be flagged for review');

  const invoiceCreated = all.items.find((item) => item.linked_entity_id === 'inv-1' && item.event_type === 'entity_created');
  assert(invoiceCreated, 'Invoice-created event should be present');
  assert.strictEqual(invoiceCreated.event_title, 'invoice created');
  assert.strictEqual(invoiceCreated.linked_entity.reference_number, 'INV-001');
  assert.strictEqual(invoiceCreated.counterparty, 'Acme Ltd');
  assert.strictEqual(invoiceCreated.amount.value, 600);
  assert(invoiceCreated.needs_review_badge, 'Draft invoice should carry needs-review badge');
  assert(invoiceCreated.status_badge, 'Invoice should carry status badge');

  const dueDateUpdated = all.items.find((item) => item.event_id === 'evt-002a');
  assert(dueDateUpdated, 'Due-date update event should be present');
  assert.strictEqual(dueDateUpdated.event_title, 'invoice due date updated');

  const payments = await listBusinessActivityInbox(mock, {
    user_id: userId,
    filter: 'payments',
    limit: 20,
    offset: 0
  });
  assert.deepStrictEqual(payments.items.map((item) => item.event_type), ['payment_recorded']);

  const quotes = await listBusinessActivityInbox(mock, {
    user_id: userId,
    filter: 'quotes',
    limit: 20,
    offset: 0
  });
  assert.deepStrictEqual(quotes.items.map((item) => item.event_type), ['quote_converted']);

  const financial = await listBusinessActivityInbox(mock, {
    user_id: userId,
    filter: 'financial',
    limit: 20,
    offset: 0
  });
  assert.deepStrictEqual(
    financial.items.map((item) => item.event_type),
    ['quote_converted', 'entity_updated', 'payment_recorded', 'entity_created']
  );

  const alerts = await listBusinessActivityInbox(mock, {
    user_id: userId,
    filter: 'alerts',
    limit: 20,
    offset: 0
  });
  assert.deepStrictEqual(
    alerts.items.map((item) => item.event_type),
    ['quarter_reopened', 'auto_commit_enabled', 'snapshot_created']
  );

  const needsReview = await listBusinessActivityInbox(mock, {
    user_id: userId,
    filter: 'needs_review',
    limit: 20,
    offset: 0
  });
  assert.deepStrictEqual(
    needsReview.items.map((item) => item.event_type),
    ['quarter_reopened', 'entity_updated', 'entity_created']
  );

  const autoCommit = all.items.find((item) => item.event_type === 'auto_commit_enabled');
  assert(autoCommit.auto_commit_badge, 'Auto-commit event should expose auto-commit badge');

  console.log('Business activity inbox verification passed.');
  console.log(`All items: ${all.items.length}`);
  console.log(`Needs review items: ${needsReview.items.length}`);
  console.log(`Alerts items: ${alerts.items.length}`);
};

run().catch((err) => {
  console.error('Business activity inbox verification failed.');
  console.error(err);
  process.exit(1);
});
