const assert = require('assert');

const db = require('./src/config/db');
const voiceController = require('./src/controllers/voiceController');
const itemController = require('./src/controllers/itemController');
const { listBusinessEvents, recordCorrectionEvent } = require('./src/services/businessEventLogService');
const { createQuarterSnapshotVersion, getQuarterSnapshotStatus } = require('./src/services/snapshotVersioningService');
const {
  QuarterGovernanceError,
  closeQuarterLifecycle,
  reopenQuarterLifecycle
} = require('./src/services/quarterLifecycleService');
const {
  enableAutoCommit,
  evaluateAutoCommitEligibility,
  updateAutoCommitPolicy
} = require('./src/services/autoCommitGovernanceService');
const {
  buildAccountantReadyPackage,
  fetchSnapshotEvent
} = require('./src/services/exportPackageBuilderService');

const USER_ID = '00000000-0000-0000-0000-000000000000';
const DEVICE_ID = 'workflow-suite-device';
const CURRENT_DATE = '2026-03-11T12:00:00.000Z';
const QUARTER_REFERENCE = 'Q1-2026';

class FakeWorkflowDb {
  constructor() {
    this.items = new Map();
    this.itemLabels = new Map();
    this.clients = new Map();
    this.businessEvents = [];
    this.auditEvents = [];
    this.jobQueue = [];
    this.governance = new Map();
    this.quarters = new Map();
    this.itemCounter = 0;
    this.clientCounter = 0;
    this.quarterCounter = 0;

    this.seedClient('Acme Ltd');
    this.seedClient('Fuel Stop');
    this.seedClient('Beta Joinery');
  }

  seedClient(name) {
    this.clientCounter += 1;
    const client = { id: `client-${this.clientCounter}`, name };
    this.clients.set(client.id, client);
    return client;
  }

  release() {}

  async query(sql, params = []) {
    const normalized = sql.replace(/\s+/g, ' ').trim();

    if (['BEGIN', 'COMMIT', 'ROLLBACK'].includes(normalized)) {
      return { rows: [] };
    }

    if (normalized.startsWith('SELECT id, name FROM clients WHERE LOWER(name) LIKE')) {
      const lookup = String(params[0] || '').replace(/%/g, '').toLowerCase();
      const match = [...this.clients.values()].find((client) => client.name.toLowerCase().includes(lookup));
      return { rows: match ? [{ ...match }] : [] };
    }

    if (normalized.startsWith('SELECT id, name FROM clients WHERE name ILIKE')) {
      const lookup = String(params[0] || '').replace(/%/g, '').toLowerCase();
      const match = [...this.clients.values()].find((client) => client.name.toLowerCase() === lookup);
      return { rows: match ? [{ ...match }] : [] };
    }

    if (normalized.startsWith('INSERT INTO clients (name, user_id) VALUES')) {
      const client = this.seedClient(params[0]);
      return { rows: [{ id: client.id }] };
    }

    if (normalized.startsWith('INSERT INTO audit_events')) {
      this.auditEvents.push({
        action_type: params[0],
        entity_name: params[1],
        entity_id: params[2],
        user_id: params[3],
        device_id: params[4],
        diff_log: JSON.parse(params[5] || '{}')
      });
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO job_queue')) {
      this.jobQueue.push({
        task_type: 'sync_push',
        item_id: params[0],
        status: 'pending'
      });
      return { rows: [] };
    }

    if (normalized.startsWith('INSERT INTO capture_items (')) {
      this.itemCounter += 1;
      const item = {
        id: `item-${this.itemCounter}`,
        type: params[0],
        status: params[1],
        amount: params[2],
        currency: params[3],
        tax_flag: params[4],
        vat_amount: params[5],
        due_date: params[6],
        client_id: params[7],
        job_id: params[8],
        extracted_text: params[9],
        raw_note: params[10],
        device_id: params[11],
        voice_command_source_text: params[12],
        voice_action_confidence: params[13],
        net_amount: params[14],
        gross_amount: params[15],
        vat_rate: params[16],
        vat_type: params[17],
        quarter_ref: params[18],
        user_id: params[19],
        captured_at: params[20],
        payment_status: params[21],
        created_at: CURRENT_DATE,
        updated_at: CURRENT_DATE,
        deleted_at: null
      };
      this.items.set(item.id, item);
      return { rows: [{ ...item }] };
    }

    if (normalized.startsWith('INSERT INTO capture_item_labels')) {
      const labels = this.itemLabels.get(params[0]) || [];
      labels.push(params[1]);
      this.itemLabels.set(params[0], labels);
      return { rows: [] };
    }

    if (normalized.startsWith('DELETE FROM capture_item_labels WHERE item_id = $1')) {
      this.itemLabels.set(params[0], []);
      return { rows: [] };
    }

    if (normalized.startsWith('SELECT ci.*, c.name AS client_name FROM capture_items ci')) {
      const item = this.items.get(params[0]);
      if (!item || item.user_id !== params[1] || item.deleted_at !== null) {
        return { rows: [] };
      }
      const client = item.client_id ? this.clients.get(item.client_id) : null;
      return {
        rows: [{
          ...item,
          client_name: client?.name || null
        }]
      };
    }

    if (normalized.startsWith('UPDATE capture_items SET amount = $3')) {
      const existing = this.items.get(params[0]);
      if (!existing || existing.user_id !== params[1]) {
        return { rows: [] };
      }
      const updated = {
        ...existing,
        amount: params[2],
        vat_amount: params[3],
        due_date: params[4],
        client_id: params[5],
        job_id: params[6],
        extracted_text: params[7],
        raw_note: params[8],
        voice_command_source_text: params[9],
        voice_action_confidence: params[10],
        net_amount: params[11],
        gross_amount: params[12],
        vat_rate: params[13],
        vat_type: params[14],
        quarter_ref: params[15],
        captured_at: params[16],
        status: 'confirmed',
        updated_at: CURRENT_DATE
      };
      this.items.set(updated.id, updated);
      return { rows: [{ ...updated }] };
    }

    if (normalized.includes('FROM capture_items ci') && normalized.includes('LEFT JOIN LATERAL')) {
      const [userId, quarterReference, eligibleTypes, activeStatuses] = params;
      const rows = [...this.items.values()]
        .filter((item) =>
          item.user_id === userId
          && item.quarter_ref === quarterReference
          && item.deleted_at === null
          && eligibleTypes.includes(item.type)
          && activeStatuses.includes(item.status)
        )
        .map((item) => {
          const client = item.client_id ? this.clients.get(item.client_id) : null;
          const latestCorrection = this.businessEvents
            .filter((event) =>
              event.user_id === userId
              && event.entity_id === item.id
              && ['entity_voided', 'entity_superseded'].includes(event.event_type)
            )
            .sort((left, right) => {
              const byTime = String(right.created_at).localeCompare(String(left.created_at));
              return byTime || String(right.event_id).localeCompare(String(left.event_id));
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
            client_name: client?.name || null,
            extracted_text: item.extracted_text,
            raw_note: item.raw_note,
            transaction_date: item.captured_at || item.created_at,
            correction_event_type: latestCorrection?.event_type || null
          };
        });
      return { rows };
    }

    if (normalized.includes('SELECT id, period_start, period_end, status, quarter_label, quarter_state')) {
      const key = `${params[0]}:${params[1]}:${params[2]}`;
      const row = this.quarters.get(key);
      return { rows: row ? [{ ...row }] : [] };
    }

    if (normalized.startsWith('INSERT INTO quarters (')) {
      const key = `${params[0]}:${params[1]}:${params[2]}`;
      const existing = this.quarters.get(key);
      if (!existing) {
        this.quarterCounter += 1;
      }
      const row = {
        id: existing?.id || `quarter-${this.quarterCounter}`,
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
      return { rows: [{ ...row }] };
    }

    if (normalized.startsWith('SELECT user_id, owner_policy_allows_auto_commit')) {
      const row = this.governance.get(params[0]);
      return { rows: row ? [{ ...row }] : [] };
    }

    if (normalized.startsWith('INSERT INTO governance_settings (')) {
      const row = {
        user_id: params[0],
        owner_policy_allows_auto_commit: params[1],
        auto_commit_enabled: params[2],
        enabled_by: params[3],
        duration: params[4],
        max_allowed_duration: params[5],
        risk_acknowledged: params[6],
        confirmation_reference: params[7],
        threshold_override: params[8],
        threshold_override_limit: params[9],
        max_auto_commit_amount: params[10],
        low_confidence_threshold: params[11],
        expires_at: params[12],
        policy_metadata: JSON.parse(params[13] || '{}'),
        updated_at: CURRENT_DATE,
        updated_by: params[14]
      };
      this.governance.set(params[0], row);
      return { rows: [{ ...row }] };
    }

    if (normalized.startsWith('INSERT INTO business_event_log (')) {
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
      this.businessEvents.push(row);
      return { rows: [{ ...row }] };
    }

    if (normalized.includes("FROM business_event_log") && normalized.includes("AND event_type = 'snapshot_created'") && normalized.includes('AND entity_id = $2')) {
      const [userId, snapshotId] = params;
      const rows = this.businessEvents
        .filter((event) => event.user_id === userId && event.event_type === 'snapshot_created' && event.entity_id === snapshotId)
        .sort((left, right) => String(right.created_at).localeCompare(String(left.created_at)))
        .slice(0, 1)
        .map((event) => ({
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

    if (normalized.includes("FROM business_event_log") && normalized.includes("AND event_type = 'snapshot_created'") && normalized.includes('AND quarter_reference = $2')) {
      const [userId, quarterReference] = params;
      const rows = this.businessEvents
        .filter((event) => event.user_id === userId && event.event_type === 'snapshot_created' && event.quarter_reference === quarterReference)
        .sort((left, right) => {
          const byTime = String(right.created_at).localeCompare(String(left.created_at));
          return byTime || String(right.event_id).localeCompare(String(left.event_id));
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

    if (normalized.startsWith('SELECT event_id,') && normalized.includes('FROM business_event_log')) {
      const userId = params[0];
      const limit = params[params.length - 2];
      const offset = params[params.length - 1];
      const entityIdParam = normalized.includes('entity_id = $') ? params[1] : null;
      const entityTypeParam = normalized.includes('entity_type = $') ? params[1 + Number(entityIdParam !== null)] : null;
      const eventTypeParam = normalized.includes('event_type = $')
        ? params[1 + Number(entityIdParam !== null) + Number(entityTypeParam !== null)]
        : null;
      const quarterParam = normalized.includes('quarter_reference = $')
        ? params[1 + Number(entityIdParam !== null) + Number(entityTypeParam !== null) + Number(eventTypeParam !== null)]
        : null;

      const filtered = this.businessEvents.filter((event) => {
        if (event.user_id !== userId) {
          return false;
        }
        if (entityIdParam !== null && event.entity_id !== entityIdParam) {
          return false;
        }
        if (entityTypeParam !== null && event.entity_type !== entityTypeParam) {
          return false;
        }
        if (eventTypeParam !== null && event.event_type !== eventTypeParam) {
          return false;
        }
        if (quarterParam !== null && event.quarter_reference !== quarterParam) {
          return false;
        }
        return true;
      });

      const rows = filtered
        .sort((left, right) => {
          const byTime = String(right.created_at).localeCompare(String(left.created_at));
          return byTime || String(right.event_id).localeCompare(String(left.event_id));
        })
        .slice(offset, offset + limit)
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
      return { rows };
    }

    throw new Error(`Unhandled SQL in fake workflow db: ${normalized}`);
  }
}

function createResponseCollector() {
  return {
    statusCode: 200,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    }
  };
}

async function runVoice(transcript) {
  const req = {
    body: {
      transcript,
      device_id: DEVICE_ID,
      current_date: CURRENT_DATE
    },
    user: { id: USER_ID }
  };
  const res = createResponseCollector();
  await voiceController.processVoice(req, res);
  return res;
}

function latestEvent(events, eventType, entityId = null) {
  return events.find((event) => event.event_type === eventType && (!entityId || event.entity_id === entityId));
}

async function main() {
  const fakeDb = new FakeWorkflowDb();
  const originalQuery = db.query;
  const originalConnect = db.pool.connect;

  db.query = fakeDb.query.bind(fakeDb);
  db.pool.connect = async () => fakeDb;

  try {
    const invoiceVoice = await runVoice('new invoice for Acme Ltd for 120 pounds today');
    assert.strictEqual(invoiceVoice.statusCode, 200);
    assert.strictEqual(invoiceVoice.body.intent, 'capture_invoice');
    assert.strictEqual(invoiceVoice.body.action_status, 'preview_required');
    assert.strictEqual(invoiceVoice.body.preview.entity_type, 'invoice');
    assert.strictEqual(invoiceVoice.body.preview.gross_amount, 120);

    const confirmedInvoice = await itemController.confirmCompositionInternal(invoiceVoice.body.composition_id, {
      dbClient: fakeDb,
      user_id: USER_ID,
      actor_id: USER_ID,
      source_type: 'voice',
      updates: {
        amount: 120,
        captured_at: '2026-03-11',
        labels: ['labour']
      }
    });
    assert.strictEqual(confirmedInvoice.status, 'confirmed');
    assert.strictEqual(confirmedInvoice.quarter_ref, QUARTER_REFERENCE);

    const receiptVoice = await runVoice('capture receipt 42 pounds for fuel today');
    assert.strictEqual(receiptVoice.statusCode, 200);
    assert.strictEqual(receiptVoice.body.intent, 'capture_receipt');
    assert.strictEqual(receiptVoice.body.action_status, 'preview_required');
    assert.strictEqual(receiptVoice.body.preview.entity_type, 'receipt');

    const confirmedReceipt = await itemController.confirmCompositionInternal(receiptVoice.body.composition_id, {
      dbClient: fakeDb,
      user_id: USER_ID,
      actor_id: USER_ID,
      source_type: 'voice',
      updates: {
        amount: 42,
        captured_at: '2026-03-11',
        labels: ['fuel']
      }
    });
    assert.strictEqual(confirmedReceipt.status, 'confirmed');
    assert.strictEqual(confirmedReceipt.quarter_ref, QUARTER_REFERENCE);

    const committedEvents = await listBusinessEvents(fakeDb, {
      user_id: USER_ID,
      quarter_reference: QUARTER_REFERENCE,
      limit: 50,
      offset: 0
    });

    assert(latestEvent(committedEvents, 'entity_committed', confirmedInvoice.id), 'Invoice confirm must emit entity_committed');
    assert(latestEvent(committedEvents, 'readiness_recalculated', confirmedInvoice.id), 'Invoice confirm must emit readiness recalculated');
    assert(latestEvent(committedEvents, 'entity_committed', confirmedReceipt.id), 'Receipt confirm must emit entity_committed');
    assert(latestEvent(committedEvents, 'readiness_recalculated', confirmedReceipt.id), 'Receipt confirm must emit readiness recalculated');
    assert(fakeDb.jobQueue.some((job) => job.item_id === confirmedInvoice.id), 'Invoice confirm must enqueue sync work');
    assert(fakeDb.jobQueue.some((job) => job.item_id === confirmedReceipt.id), 'Receipt confirm must enqueue sync work');

    const initialSnapshotStatus = await getQuarterSnapshotStatus(fakeDb, {
      userId: USER_ID,
      quarterReference: QUARTER_REFERENCE
    });
    assert.strictEqual(initialSnapshotStatus.baseline_exists, false);
    assert.strictEqual(initialSnapshotStatus.live_transactions.length, 2);

    const firstSnapshot = await createQuarterSnapshotVersion(fakeDb, {
      user_id: USER_ID,
      actor_id: USER_ID,
      source_type: 'manual',
      quarter_reference: QUARTER_REFERENCE,
      metadata: { readiness_pct: 100 }
    });
    assert.strictEqual(firstSnapshot.version_number, 1);
    assert.strictEqual(firstSnapshot.snapshot_summary.transaction_count, 2);
    assert.strictEqual(firstSnapshot.snapshot_record.quarter_label, QUARTER_REFERENCE);
    assert(firstSnapshot.snapshot_record.files_generated.some((file) => file.name === 'snapshot_metadata.json'));

    const firstSnapshotRecord = await fetchSnapshotEvent(fakeDb, {
      userId: USER_ID,
      snapshotId: firstSnapshot.entity_id
    });
    const firstExport = buildAccountantReadyPackage(firstSnapshotRecord);
    const firstExportRepeat = buildAccountantReadyPackage(firstSnapshotRecord);
    assert.strictEqual(firstExport.manifest.package_checksum, firstExportRepeat.manifest.package_checksum);
    assert.strictEqual(firstExport.files.find((file) => file.name === 'snapshot_metadata.json').sha256, firstExportRepeat.files.find((file) => file.name === 'snapshot_metadata.json').sha256);

    const closedQuarter = await closeQuarterLifecycle(fakeDb, {
      user_id: USER_ID,
      actor_id: USER_ID,
      source_type: 'manual',
      quarter_reference: QUARTER_REFERENCE,
      reason: 'Quarter review completed'
    });
    assert.strictEqual(closedQuarter.quarter_state, 'closed');

    await assert.rejects(
      () => itemController.createItemInternal({
        type: 'invoice',
        status: 'draft',
        amount: 10,
        device_id: DEVICE_ID,
        user_id: USER_ID,
        client_name: 'Blocked Client',
        transaction_date: '2026-03-11',
        voice_command_source_text: 'blocked while closed',
        voice_action_confidence: 0.99
      }, { dbClient: fakeDb, emitBusinessEvents: false }),
      (error) => {
        assert(error instanceof QuarterGovernanceError);
        assert(error.message.includes('Quarter Q1-2026 is closed'));
        return true;
      }
    );

    await assert.rejects(
      () => reopenQuarterLifecycle(fakeDb, {
        user_id: USER_ID,
        actor_id: USER_ID,
        source_type: 'manual',
        quarter_reference: QUARTER_REFERENCE,
        reason: 'Late invoice received'
      }),
      /confirmation_reference is required/
    );

    const reopenedQuarter = await reopenQuarterLifecycle(fakeDb, {
      user_id: USER_ID,
      actor_id: USER_ID,
      source_type: 'manual',
      quarter_reference: QUARTER_REFERENCE,
      reason: 'Late invoice received',
      confirmation_reference: 'mgr-approval-42',
      metadata: { confirmed_by: 'finance-manager' }
    });
    assert.strictEqual(reopenedQuarter.quarter_state, 'open');

    await updateAutoCommitPolicy(fakeDb, {
      user_id: USER_ID,
      actor_id: USER_ID,
      owner_policy_allows_auto_commit: true,
      max_allowed_duration: 'daily',
      max_auto_commit_amount: 100,
      threshold_override_limit: 150,
      low_confidence_threshold: 0.85
    });

    const enabledAutoCommit = await enableAutoCommit(fakeDb, {
      user_id: USER_ID,
      actor_id: USER_ID,
      duration: 'daily',
      risk_acknowledged: true,
      confirmation_reference: 'owner-approved-1',
      threshold_override: false,
      now: new Date(CURRENT_DATE)
    });
    assert.strictEqual(enabledAutoCommit.auto_commit_enabled, true);

    const autoCommitVoice = await runVoice('new invoice for Beta Joinery for 90 pounds today');
    assert.strictEqual(autoCommitVoice.statusCode, 200);
    assert.strictEqual(autoCommitVoice.body.action_status, 'committed');
    assert.strictEqual(autoCommitVoice.body.auto_commit.enabled, true);
    assert(autoCommitVoice.body.committed_entity_id, 'Auto-commit flow must return committed entity id');

    const blockedAutoCommitVoice = await runVoice('new invoice for Beta Joinery for 180 pounds today');
    assert.strictEqual(blockedAutoCommitVoice.statusCode, 200);
    assert.strictEqual(blockedAutoCommitVoice.body.action_status, 'preview_required');
    assert(blockedAutoCommitVoice.body.auto_commit.reasons_blocked.includes('over_threshold'));

    const autoEligibility = await evaluateAutoCommitEligibility(fakeDb, {
      user_id: USER_ID,
      entity_type: 'invoice',
      amount: 180,
      confidence_score: 0.98,
      now: new Date(CURRENT_DATE)
    });
    assert.strictEqual(autoEligibility.eligible, false);
    assert(autoEligibility.reasons.includes('over_threshold'));

    await recordCorrectionEvent(fakeDb, {
      user_id: USER_ID,
      actor_id: USER_ID,
      source_type: 'manual',
      entity_id: confirmedReceipt.id,
      entity_type: confirmedReceipt.type,
      quarter_reference: QUARTER_REFERENCE,
      action: 'void',
      status_from: 'confirmed',
      status_to: 'void_requested',
      description: `receipt ${confirmedReceipt.id} correction recorded: void`,
      metadata: {
        reason: 'Duplicate fuel receipt'
      }
    });

    const changedSnapshotStatus = await getQuarterSnapshotStatus(fakeDb, {
      userId: USER_ID,
      quarterReference: QUARTER_REFERENCE
    });
    assert.strictEqual(changedSnapshotStatus.changed_since_snapshot, true);
    assert.deepStrictEqual(changedSnapshotStatus.diff.added_transactions.map((entry) => entry.txn_id), [autoCommitVoice.body.committed_entity_id]);
    assert.deepStrictEqual(changedSnapshotStatus.diff.voided_transactions.map((entry) => entry.txn_id), [confirmedReceipt.id]);

    const secondSnapshot = await createQuarterSnapshotVersion(fakeDb, {
      user_id: USER_ID,
      actor_id: USER_ID,
      source_type: 'manual',
      quarter_reference: QUARTER_REFERENCE,
      metadata: { readiness_pct: 100, source: 'post-change' }
    });
    assert.strictEqual(secondSnapshot.version_number, 2);

    const secondSnapshotRecord = await fetchSnapshotEvent(fakeDb, {
      userId: USER_ID,
      snapshotId: secondSnapshot.entity_id
    });
    const secondExport = buildAccountantReadyPackage(secondSnapshotRecord);
    const secondExportRepeat = buildAccountantReadyPackage(secondSnapshotRecord);
    assert.strictEqual(secondExport.manifest.package_checksum, secondExportRepeat.manifest.package_checksum);
    assert.notStrictEqual(secondExport.manifest.package_checksum, firstExport.manifest.package_checksum);
    assert.notStrictEqual(secondExport.filename, firstExport.filename);

    const quarterHistory = await listBusinessEvents(fakeDb, {
      user_id: USER_ID,
      quarter_reference: QUARTER_REFERENCE,
      limit: 100,
      offset: 0
    });
    const fullHistory = await listBusinessEvents(fakeDb, {
      user_id: USER_ID,
      limit: 100,
      offset: 0
    });
    assert(latestEvent(quarterHistory, 'quarter_closed'), 'Quarter close must be logged');
    assert(latestEvent(quarterHistory, 'quarter_reopened'), 'Quarter reopen must be logged');
    assert(latestEvent(fullHistory, 'auto_commit_enabled'), 'Auto-commit enable must be logged');
    assert(latestEvent(quarterHistory, 'snapshot_created', secondSnapshot.entity_id), 'Second snapshot must be logged');

    const snapshotMetadata1 = JSON.parse(firstExport.files.find((file) => file.name === 'snapshot_metadata.json').content.toString('utf8'));
    const snapshotMetadata2 = JSON.parse(secondExport.files.find((file) => file.name === 'snapshot_metadata.json').content.toString('utf8'));

    assert.strictEqual(snapshotMetadata1.version_number, 1);
    assert.strictEqual(snapshotMetadata2.version_number, 2);
    assert(snapshotMetadata2.generated_files.length >= snapshotMetadata1.generated_files.length);
    assert(Array.isArray(snapshotMetadata1.files_generated));
    assert(Array.isArray(snapshotMetadata2.files_generated));

    console.log('verify_critical_path_workflow_suite=PASS');
    console.log(JSON.stringify({
      voice_invoice_preview_confirmed: true,
      voice_receipt_preview_confirmed: true,
      readiness_events_logged: fullHistory.filter((event) => event.event_type === 'readiness_recalculated').length,
      sync_jobs_enqueued: fakeDb.jobQueue.length,
      snapshot_versions: [firstSnapshot.version_number, secondSnapshot.version_number],
      post_snapshot_added_transactions: changedSnapshotStatus.diff.added_transactions.length,
      post_snapshot_voided_transactions: changedSnapshotStatus.diff.voided_transactions.length,
      quarter_governance_logged: quarterHistory.filter((event) => ['quarter_closed', 'quarter_reopened'].includes(event.event_type)).length,
      auto_commit_blocked_reason: blockedAutoCommitVoice.body.auto_commit.reasons_blocked,
      export_checksums: [
        firstExport.manifest.package_checksum,
        secondExport.manifest.package_checksum
      ]
    }));
  } finally {
    db.query = originalQuery;
    db.pool.connect = originalConnect;
  }
}

main().catch((error) => {
  console.error('verify_critical_path_workflow_suite=FAIL');
  console.error(error.stack || error.message);
  process.exit(1);
});
