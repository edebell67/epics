const assert = require('assert');
const { buildReadinessReport } = require('./src/services/readinessService');
const {
  SnapshotVersioningError,
  createQuarterSnapshotVersion,
  getQuarterSnapshotStatus
} = require('./src/services/snapshotVersioningService');

class MockExecutor {
  constructor(items = []) {
    this.items = items;
    this.events = [];
    this.quarters = new Map();
  }

  async query(text, params) {
    const sql = text.replace(/\s+/g, ' ').trim();

    if (sql.includes('FROM quarters') && sql.includes('period_start = $2') && sql.includes('period_end = $3')) {
      const key = `${params[0]}:${params[1]}:${params[2]}`;
      const row = this.quarters.get(key);
      return { rows: row ? [row] : [] };
    }

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

    if (sql.includes('FROM business_event_log') && sql.includes("event_type = 'snapshot_created'")) {
      const [userId, quarterReference] = params;
      const rows = this.events
        .filter((event) => event.user_id === userId && event.quarter_reference === quarterReference && event.event_type === 'snapshot_created')
        .sort((left, right) => {
          if (left.created_at === right.created_at) {
            return String(right.event_id).localeCompare(String(left.event_id));
          }
          return String(right.created_at).localeCompare(String(left.created_at));
        })
        .slice(0, 1)
        .map((event) => ({
          event_id: event.event_id,
          snapshot_id: event.entity_id,
          created_at: event.created_at,
          actor_id: event.actor_id,
          source_type: event.source_type,
          description: event.description,
          quarter_reference: event.quarter_reference,
          metadata: event.metadata
        }));
      return { rows };
    }

    if (sql.includes('FROM capture_items ci')) {
      const [userId, quarterReference] = params;
      const rows = this.items
        .filter((item) => item.user_id === userId && item.quarter_ref === quarterReference && item.deleted_at === null)
        .map((item) => {
          const latestCorrection = this.events
            .filter((event) => event.user_id === userId && event.entity_id === item.id && ['entity_voided', 'entity_superseded'].includes(event.event_type))
            .sort((left, right) => {
              if (left.created_at === right.created_at) {
                return String(right.event_id).localeCompare(String(left.event_id));
              }
              return String(right.created_at).localeCompare(String(left.created_at));
            })[0];

          return {
            id: item.id,
            type: item.type,
            status: item.status,
            amount: item.amount,
            net_amount: item.net_amount,
            vat_amount: item.vat_amount,
            gross_amount: item.gross_amount,
            vat_rate: item.vat_rate,
            vat_type: item.vat_type,
            quarter_ref: item.quarter_ref,
            client_id: item.client_id,
            client_name: item.client_name,
            extracted_text: item.extracted_text,
            raw_note: item.raw_note,
            transaction_date: item.transaction_date,
            correction_event_type: latestCorrection?.event_type || null
          };
        });
      return { rows };
    }

    throw new Error(`Unsupported SQL in mock executor: ${sql}`);
  }
}

const run = async () => {
  const userId = '00000000-0000-0000-0000-000000000000';
  const executor = new MockExecutor([
    {
      id: 'inv-1',
      user_id: userId,
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
      client_name: 'Alpha Builders',
      extracted_text: 'Invoice Alpha Builders',
      raw_note: null,
      transaction_date: '2026-01-10',
      deleted_at: null
    },
    {
      id: 'rec-1',
      user_id: userId,
      type: 'receipt',
      status: 'confirmed',
      amount: 60,
      net_amount: 50,
      vat_amount: 10,
      gross_amount: 60,
      vat_rate: 20,
      vat_type: 'input',
      quarter_ref: 'Q1-2026',
      client_id: 'supplier-1',
      client_name: 'Fuel Stop',
      extracted_text: 'Fuel receipt',
      raw_note: null,
      transaction_date: '2026-01-12',
      deleted_at: null
    }
  ]);

  const initialStatus = await getQuarterSnapshotStatus(executor, {
    userId,
    quarterReference: 'Q1-2026'
  });
  assert.strictEqual(initialStatus.baseline_exists, false);
  assert.strictEqual(initialStatus.can_create_snapshot_version, true);
  assert.strictEqual(initialStatus.next_version_number, 1);

  const unresolvedReadiness = buildReadinessReport({
    asOfDate: '2026-03-11',
    transactions: [
      {
        id: 'warn-1',
        txn_date: '2026-01-15',
        merchant: 'Fuel Stop',
        amount: 60,
        direction: 'out',
        category_code: null,
        business_personal: 'BUSINESS',
        is_split: false,
        split_business_pct: null,
        duplicate_flag: false,
        duplicate_resolution: null
      }
    ]
  });

  const firstSnapshot = await createQuarterSnapshotVersion(executor, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quarter_reference: 'Q1-2026',
    metadata: {
      readiness_report: unresolvedReadiness
    }
  });

  assert.strictEqual(firstSnapshot.version_number, 1);
  assert.strictEqual(firstSnapshot.snapshot_summary.transaction_count, 2);
  assert.strictEqual(firstSnapshot.changed_since_snapshot, false);
  assert(firstSnapshot.snapshot_record.integrity_warning_summary.length > 0);
  assert.strictEqual(firstSnapshot.snapshot_record.quarter_label, 'Q1-2026');
  assert.strictEqual(firstSnapshot.snapshot_record.transaction_ids.length, 2);
  assert(firstSnapshot.snapshot_record.files_generated.length >= 2);
  assert.strictEqual(executor.events.filter((event) => event.event_type === 'snapshot_created').length, 1);
  const firstEvent = executor.events.filter((event) => event.event_type === 'snapshot_created')[0];
  assert.strictEqual(firstEvent.metadata.readiness_pct, unresolvedReadiness.readiness_pct);
  assert.strictEqual(firstEvent.metadata.snapshot.created_by, userId);
  assert.deepStrictEqual(firstEvent.metadata.snapshot.transaction_ids, ['inv-1', 'rec-1']);
  assert(firstEvent.metadata.snapshot.files_generated.some((file) => file.name === 'snapshot_metadata.json'));
  assert(firstEvent.metadata.integrity_warning_summary.length > 0);

  const unchangedStatus = await getQuarterSnapshotStatus(executor, {
    userId,
    quarterReference: 'Q1-2026'
  });
  assert.strictEqual(unchangedStatus.baseline_exists, true);
  assert.strictEqual(unchangedStatus.changed_since_snapshot, false);
  assert.strictEqual(unchangedStatus.can_create_snapshot_version, false);
  assert(unchangedStatus.no_change_reason.includes('Snapshot 001'));

  executor.items[0].amount = 144;
  executor.items[0].net_amount = 120;
  executor.items[0].vat_amount = 24;
  executor.items[0].gross_amount = 144;
  executor.items[0].extracted_text = 'Adjusted invoice Alpha Builders';
  executor.items.push({
    id: 'inv-2',
    user_id: userId,
    type: 'invoice',
    status: 'confirmed',
    amount: 240,
    net_amount: 200,
    vat_amount: 40,
    gross_amount: 240,
    vat_rate: 20,
    vat_type: 'output',
    quarter_ref: 'Q1-2026',
    client_id: 'client-2',
    client_name: 'Bravo Joinery',
    extracted_text: 'Late invoice Bravo Joinery',
    raw_note: null,
    transaction_date: '2026-01-20',
    deleted_at: null
  });
  executor.events.push({
    event_id: 'evt-void-rec-1',
    user_id: userId,
    event_type: 'entity_voided',
    entity_id: 'rec-1',
    entity_type: 'receipt',
    created_at: '2026-03-11T20:35:00.000Z',
    actor_id: userId,
    source_type: 'manual',
    description: 'Receipt rec-1 voided',
    metadata: { reason: 'duplicate' },
    quarter_reference: 'Q1-2026',
    status_from: 'confirmed',
    status_to: 'voided'
  });

  const changedStatus = await getQuarterSnapshotStatus(executor, {
    userId,
    quarterReference: 'Q1-2026'
  });
  assert.strictEqual(changedStatus.changed_since_snapshot, true);
  assert.strictEqual(changedStatus.can_create_snapshot_version, true);
  assert.deepStrictEqual(changedStatus.diff.added_transactions.map((entry) => entry.txn_id), ['inv-2']);
  assert.deepStrictEqual(changedStatus.diff.voided_transactions.map((entry) => entry.txn_id), ['rec-1']);
  assert.deepStrictEqual(changedStatus.diff.adjustments.map((entry) => entry.txn_id), ['inv-1']);
  assert.notStrictEqual(changedStatus.diff.revenue_impact, 0);
  assert.notStrictEqual(changedStatus.diff.vat_impact, 0);

  const secondSnapshot = await createQuarterSnapshotVersion(executor, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quarter_reference: 'Q1-2026',
    metadata: {
      readiness_pct: 97
    }
  });

  assert.strictEqual(secondSnapshot.version_number, 2);
  assert.strictEqual(executor.events.filter((event) => event.event_type === 'snapshot_created').length, 2);
  const snapshotEvents = executor.events.filter((event) => event.event_type === 'snapshot_created');
  assert.strictEqual(snapshotEvents[0].metadata.readiness_pct, unresolvedReadiness.readiness_pct);
  assert.strictEqual(snapshotEvents[1].metadata.readiness_pct, 97);
  assert.deepStrictEqual(
    snapshotEvents[0].metadata.snapshot.integrity_warning_summary,
    firstSnapshot.snapshot_record.integrity_warning_summary
  );
  assert.deepStrictEqual(snapshotEvents[0].metadata.snapshot.transaction_ids, ['inv-1', 'rec-1']);
  assert.notDeepStrictEqual(
    snapshotEvents[0].metadata.snapshot.transaction_ids,
    snapshotEvents[1].metadata.snapshot.transaction_ids
  );
  assert.strictEqual(snapshotEvents[0].metadata.snapshot.version_number, 1);
  assert.strictEqual(snapshotEvents[1].metadata.snapshot.version_number, 2);

  await assert.rejects(
    () => createQuarterSnapshotVersion(executor, {
      user_id: userId,
      actor_id: userId,
      source_type: 'manual',
      quarter_reference: 'Q1-2026'
    }),
    (error) => {
      assert(error instanceof SnapshotVersioningError);
      assert(error.message.includes('Snapshot 002'));
      return true;
    }
  );

  console.log('verify_snapshot_versioning=PASS');
  console.log(JSON.stringify({
    first_snapshot_version: firstSnapshot.version_number,
    second_snapshot_version: secondSnapshot.version_number,
    added_transactions: changedStatus.diff.added_transactions.length,
    voided_transactions: changedStatus.diff.voided_transactions.length,
    adjustments: changedStatus.diff.adjustments.length,
    revenue_impact: changedStatus.diff.revenue_impact,
    vat_impact: changedStatus.diff.vat_impact
  }));
};

run().catch((error) => {
  console.error('verify_snapshot_versioning=FAIL');
  console.error(error.stack || error.message);
  process.exit(1);
});
