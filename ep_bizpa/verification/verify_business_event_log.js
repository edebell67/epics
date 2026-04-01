const assert = require('assert');
const {
  EVENT_TYPE_CATALOG,
  appendBusinessEvent,
  buildClientCreatedEvent,
  buildItemCreatedEvent,
  listBusinessEvents,
  recordCorrectionEvent,
  recordEntityCreated,
  recordEntityUpdated,
  recordPaymentRecorded,
  recordQuoteConverted,
  recordReadinessRecalculated,
  recordSnapshotCreated,
  recordStatusChange,
  setAutoCommitPreference,
  upsertQuarterStatus
} = require('./src/services/businessEventLogService');

class MockExecutor {
  constructor() {
    this.events = [];
    this.governance = new Map();
    this.quarters = new Map();
  }

  async query(text, params) {
    const sql = text.replace(/\s+/g, ' ').trim();

    if (sql.includes('INSERT INTO business_event_log')) {
      const record = {
        event_id: params[0],
        user_id: params[1],
        event_type: params[2],
        entity_id: params[3],
        entity_type: params[4],
        created_at: params[5],
        actor_id: params[6],
        source_type: params[7],
        description: params[8],
        metadata: JSON.parse(params[9] || '{}'),
        quarter_reference: params[10],
        status_from: params[11],
        status_to: params[12]
      };
      this.events.push(record);
      return { rows: [record] };
    }

    if (sql.includes('INSERT INTO governance_settings')) {
      this.governance.set(params[0], {
        user_id: params[0],
        auto_commit_enabled: params[1],
        updated_by: params[2]
      });
      return { rows: [] };
    }

    if (sql.includes('INSERT INTO quarters')) {
      const key = `${params[0]}:${params[1]}:${params[2]}`;
      const quarter = {
        id: `quarter-${this.quarters.size + 1}`,
        status: params[3]
      };
      this.quarters.set(key, quarter);
      return { rows: [quarter] };
    }

    if (sql.includes('SELECT event_id,')) {
      const [userId] = params;
      const filtered = this.events
        .filter((event) => event.user_id === userId)
        .sort((a, b) => {
          if (a.created_at === b.created_at) {
            return String(b.event_id).localeCompare(String(a.event_id));
          }
          return String(b.created_at).localeCompare(String(a.created_at));
        })
        .map((event) => ({
          event_id: event.event_id,
          event_type: event.event_type,
          entity_id: event.entity_id,
          entity_type: event.entity_type,
          timestamp: event.created_at,
          actor_id: event.actor_id,
          description: event.description,
          metadata: event.metadata,
          quarter_reference: event.quarter_reference,
          status_from: event.status_from,
          status_to: event.status_to
        }));
      return { rows: filtered };
    }

    throw new Error(`Unsupported SQL in mock executor: ${sql}`);
  }
}

const run = async () => {
  const mock = new MockExecutor();
  const userId = '00000000-0000-0000-0000-000000000000';

  assert(EVENT_TYPE_CATALOG.includes('entity_created'));
  assert(EVENT_TYPE_CATALOG.includes('entity_updated'));
  assert(EVENT_TYPE_CATALOG.includes('quarter_closed'));

  const createdItem = {
    id: 'item-1',
    user_id: userId,
    type: 'invoice',
    amount: 120,
    gross_amount: 120,
    currency: 'GBP',
    client_id: 'client-1',
    job_id: 'job-1',
    quarter_ref: 'Q1-2026',
    status: 'draft'
  };

  await recordEntityCreated(mock, buildItemCreatedEvent(createdItem, userId));
  await recordEntityCreated(mock, buildClientCreatedEvent({
    id: 'client-1',
    user_id: userId,
    name: 'Acme Ltd'
  }, userId));

  await recordStatusChange(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    entity_id: 'item-1',
    entity_type: 'invoice',
    quarter_reference: 'Q1-2026',
    status_from: 'draft',
    status_to: 'confirmed',
    description: 'Invoice item-1 moved from draft to confirmed',
    metadata: { field: 'status' }
  });

  await recordEntityUpdated(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    entity_id: 'item-1',
    entity_type: 'invoice',
    quarter_reference: 'Q1-2026',
    description: 'Invoice item-1 due date updated',
    metadata: { updated_field: 'due_date', previous_value: null, new_value: '2026-03-31' }
  });

  await recordPaymentRecorded(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    entity_id: 'item-1',
    entity_type: 'invoice',
    quarter_reference: 'Q1-2026',
    status_from: 'sent',
    status_to: 'paid',
    description: 'Invoice item-1 marked paid',
    metadata: { action_type: 'mark_paid' }
  });

  await recordCorrectionEvent(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    entity_id: 'item-1',
    entity_type: 'invoice',
    quarter_reference: 'Q1-2026',
    action: 'void',
    status_from: 'confirmed',
    status_to: 'void_requested',
    description: 'Invoice item-1 void requested',
    metadata: { reason: 'duplicate entry' }
  });

  await recordQuoteConverted(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quote_id: 'quote-1',
    invoice_id: 'invoice-2',
    quarter_reference: 'Q1-2026'
  });

  await recordSnapshotCreated(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'system',
    quarter_reference: 'Q1-2026',
    description: 'Quarter snapshot generated',
    metadata: {
      readiness_pct: 92,
      included_transaction_ids: ['txn-1', 'txn-2']
    }
  });

  await recordReadinessRecalculated(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'system',
    quarter_reference: 'Q1-2026',
    description: 'Readiness recalculated for Q1-2026',
    metadata: {
      total_txns_in_period: 12,
      blocking_txns_count: 1,
      readiness_pct: 92,
      can_export: false
    }
  });

  await upsertQuarterStatus(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quarter_reference: 'Q1-2026',
    next_status: 'ready',
    event_type: 'quarter_closed',
    reason: 'review complete'
  });

  await upsertQuarterStatus(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quarter_reference: 'Q1-2026',
    next_status: 'open',
    event_type: 'quarter_reopened',
    reason: 'late invoice arrived'
  });

  await setAutoCommitPreference(mock, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    enabled: true,
    metadata: { reason: 'admin preference updated' }
  });

  const history = await listBusinessEvents(mock, { user_id: userId, limit: 50, offset: 0 });
  assert(history.length >= 11, `Expected at least 11 business events, received ${history.length}`);
  assert(history.every((event, index) => index === 0 || event.timestamp <= history[index - 1].timestamp));
  assert(history.some((event) => event.event_type === 'entity_created'));
  assert(history.some((event) => event.event_type === 'entity_status_changed'));
  assert(history.some((event) => event.event_type === 'entity_updated'));
  assert(history.some((event) => event.event_type === 'entity_voided'));
  assert(history.some((event) => event.event_type === 'payment_recorded'));
  assert(history.some((event) => event.event_type === 'quote_converted'));
  assert(history.some((event) => event.event_type === 'snapshot_created'));
  assert(history.some((event) => event.event_type === 'readiness_recalculated'));
  assert(history.some((event) => event.event_type === 'quarter_closed'));
  assert(history.some((event) => event.event_type === 'quarter_reopened'));

  const auditShape = history.find((event) => event.event_type === 'readiness_recalculated');
  assert(auditShape.actor_id);
  assert(auditShape.timestamp);
  assert(auditShape.metadata);

  console.log('Business event log verification passed.');
  console.log(`Events written: ${history.length}`);
  console.log(`Latest event: ${history[0].event_type}`);
};

run().catch((err) => {
  console.error('Business event log verification failed.');
  console.error(err);
  process.exit(1);
});
