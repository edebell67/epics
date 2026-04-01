const assert = require('assert');
const { listBusinessEvents } = require('./src/services/businessEventLogService');
const { reconstructAuditTrace } = require('./src/services/auditTraceService');
const {
  QuarterGovernanceError,
  assertQuarterAllowsMonetaryActivity,
  closeQuarterLifecycle,
  getQuarterLifecycle,
  reopenQuarterLifecycle
} = require('./src/services/quarterLifecycleService');
const { createQuarterSnapshotVersion } = require('./src/services/snapshotVersioningService');

class MockExecutor {
  constructor() {
    this.events = [];
    this.quarters = new Map();
    this.captureItems = [
      {
        id: 'invoice-1',
        user_id: '00000000-0000-0000-0000-000000000000',
        type: 'invoice',
        status: 'confirmed',
        amount: 120,
        net_amount: 100,
        vat_amount: 20,
        gross_amount: 120,
        vat_rate: 20,
        vat_type: 'output',
        quarter_ref: 'Q1-2026',
        client_id: 'client-1',
        client_name: 'Acme Ltd',
        extracted_text: 'Invoice 1',
        raw_note: 'Invoice 1',
        captured_at: '2026-03-10T09:00:00.000Z',
        created_at: '2026-03-10T09:00:00.000Z',
        deleted_at: null
      }
    ];
  }

  quarterKey(userId, periodStart, periodEnd) {
    return `${userId}:${periodStart}:${periodEnd}`;
  }

  async query(text, params) {
    const sql = text.replace(/\s+/g, ' ').trim();

    if (sql.includes('SELECT id, period_start, period_end, status, quarter_label, quarter_state')) {
      const key = this.quarterKey(params[0], params[1], params[2]);
      const row = this.quarters.get(key);
      return { rows: row ? [row] : [] };
    }

    if (sql.includes('INSERT INTO quarters (')) {
      const key = this.quarterKey(params[0], params[1], params[2]);
      const existing = this.quarters.get(key);
      const row = {
        id: existing?.id || `quarter-${this.quarters.size + 1}`,
        period_start: params[1],
        period_end: params[2],
        status: params[3],
        quarter_label: params[4],
        quarter_state: params[5],
        closed_at: params[6],
        reopened_at: params[7],
        reopen_reason: params[8],
        confirmation_reference: params[9],
        governance_metadata: JSON.parse(params[10] || '{}')
      };
      this.quarters.set(key, row);
      return { rows: [row] };
    }

    if (sql.includes('INSERT INTO business_event_log')) {
      const row = {
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
      this.events.push(row);
      return { rows: [row] };
    }

    if (sql.includes('FROM business_event_log') && sql.includes("event_type = 'snapshot_created'")) {
      const [userId, quarterReference] = params;
      const rows = this.events
        .filter((event) => event.user_id === userId && event.quarter_reference === quarterReference && event.event_type === 'snapshot_created')
        .sort((left, right) => String(right.created_at).localeCompare(String(left.created_at)));
      return {
        rows: rows.slice(0, 1).map((event) => ({
          event_id: event.event_id,
          snapshot_id: event.entity_id,
          created_at: event.created_at,
          actor_id: event.actor_id,
          source_type: event.source_type,
          description: event.description,
          quarter_reference: event.quarter_reference,
          metadata: event.metadata
        }))
      };
    }

    if (sql.includes('FROM capture_items ci')) {
      const [userId, quarterReference] = params;
      const rows = this.captureItems
        .filter((item) => item.user_id === userId && item.quarter_ref === quarterReference && item.deleted_at === null)
        .map((item) => ({
          ...item,
          transaction_date: item.captured_at,
          correction_event_type: null
        }));
      return { rows };
    }

    if (sql.includes('SELECT event_id,')) {
      const [userId] = params;
      return {
        rows: this.events
          .filter((event) => event.user_id === userId)
          .sort((left, right) => {
            const timeCompare = String(right.created_at).localeCompare(String(left.created_at));
            if (timeCompare !== 0) {
              return timeCompare;
            }
            return String(right.event_id).localeCompare(String(left.event_id));
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
          }))
      };
    }

    throw new Error(`Unsupported SQL in quarter governance mock: ${sql}`);
  }
}

const userId = '00000000-0000-0000-0000-000000000000';

const run = async () => {
  const executor = new MockExecutor();

  const initial = await getQuarterLifecycle(executor, {
    userId,
    quarterReference: 'Q1-2026'
  });
  assert.strictEqual(initial.quarter_state, 'open');

  const closed = await closeQuarterLifecycle(executor, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quarter_reference: 'Q1-2026',
    reason: 'Quarter review completed'
  });
  assert.strictEqual(closed.quarter_state, 'closed');
  assert(closed.closed_at, 'close should timestamp closed_at');

  await assert.rejects(
    () => assertQuarterAllowsMonetaryActivity(executor, {
      userId,
      quarterReference: 'Q1-2026',
      operation: 'New monetary entry',
      entityType: 'invoice'
    }),
    (error) => {
      assert(error instanceof QuarterGovernanceError);
      assert(error.message.includes('Quarter Q1-2026 is closed'));
      return true;
    }
  );

  await assert.rejects(
    () => createQuarterSnapshotVersion(executor, {
      user_id: userId,
      actor_id: userId,
      source_type: 'manual',
      quarter_reference: 'Q1-2026'
    }),
    (error) => {
      assert(error instanceof QuarterGovernanceError);
      assert.strictEqual(error.details.operation, 'Snapshot creation');
      return true;
    }
  );

  await assert.rejects(
    () => reopenQuarterLifecycle(executor, {
      user_id: userId,
      actor_id: userId,
      source_type: 'manual',
      quarter_reference: 'Q1-2026',
      reason: 'Late invoice received'
    }),
    /confirmation_reference is required/
  );

  const reopened = await reopenQuarterLifecycle(executor, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quarter_reference: 'Q1-2026',
    reason: 'Late invoice received',
    confirmation_reference: 'mgr-approval-42',
    metadata: {
      confirmed_by: 'finance-manager'
    }
  });
  assert.strictEqual(reopened.quarter_state, 'open');
  assert.strictEqual(reopened.reopen_reason, 'Late invoice received');
  assert.strictEqual(reopened.confirmation_reference, 'mgr-approval-42');
  assert(reopened.reopened_at, 'reopen should timestamp reopened_at');

  const snapshot = await createQuarterSnapshotVersion(executor, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quarter_reference: 'Q1-2026',
    metadata: {
      source_type: 'manual'
    }
  });
  assert.strictEqual(snapshot.version_number, 1);

  const history = await listBusinessEvents(executor, {
    user_id: userId,
    quarter_reference: 'Q1-2026',
    limit: 20,
    offset: 0
  });
  const reopenEvent = history.find((event) => event.event_type === 'quarter_reopened');
  const closeEvent = history.find((event) => event.event_type === 'quarter_closed');
  assert(reopenEvent, 'quarter_reopened event should be visible in business history');
  assert(closeEvent, 'quarter_closed event should be visible in business history');
  assert.strictEqual(reopenEvent.metadata.reopen_reason, 'Late invoice received');
  assert.strictEqual(reopenEvent.metadata.confirmation_reference, 'mgr-approval-42');

  const auditTrace = reconstructAuditTrace({
    events: history,
    snapshots: history
      .filter((event) => event.event_type === 'snapshot_created')
      .map((event) => ({
        snapshot_id: event.entity_id,
        created_at: event.timestamp,
        quarter_reference: event.quarter_reference,
        description: event.description,
        included_transaction_ids: event.metadata.included_transaction_ids || []
      }))
  });

  assert(auditTrace.event_types.includes('quarter_closed'));
  assert(auditTrace.event_types.includes('quarter_reopened'));
  assert(auditTrace.timeline.some((entry) => entry.kind === 'event' && entry.event_type === 'quarter_reopened'));

  console.log('verify_quarter_governance_flow=PASS');
  console.log(JSON.stringify({
    blocked_new_entry: true,
    blocked_snapshot_while_closed: true,
    reopen_reason_stored: reopenEvent.metadata.reopen_reason,
    confirmation_reference: reopenEvent.metadata.confirmation_reference,
    audit_timeline_entries: auditTrace.timeline.length
  }));
};

run().catch((error) => {
  console.error('verify_quarter_governance_flow=FAIL');
  console.error(error);
  process.exit(1);
});
