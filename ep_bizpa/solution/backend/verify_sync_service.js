const assert = require('assert');
const {
  buildPullChangeEnvelope,
  buildSyncEnvelope,
  evaluateSyncConflict
} = require('./src/services/syncEnvelopeService');
const {
  validateSyncChanges
} = require('./src/services/syncValidationService');

const TENANT_ID = '00000000-0000-0000-0000-000000000000';

const verifyNormalization = () => {
  const legacyPayload = [
    {
      id: 'sync-1',
      tenant_id: TENANT_ID,
      table_name: 'capture_items',
      entity_id: 'item-1',
      action: 'upsert',
      timestamp: '2026-03-11T16:30:00.000Z',
      data: {
        type: 'note',
        status: 'draft',
        raw_note: 'Queued locally'
      }
    }
  ];

  const validation = validateSyncChanges(legacyPayload);
  assert.strictEqual(validation.valid, true);
  assert.strictEqual(validation.sanitizedChanges[0].sync_item_id, 'sync-1');
  assert.strictEqual(validation.sanitizedChanges[0].operation_type, 'upsert');
  assert.strictEqual(validation.sanitizedChanges[0].queued_at, '2026-03-11T16:30:00.000Z');
};

const verifyPullEnvelope = () => {
  const serverTimestamp = '2026-03-11T16:31:00.000Z';
  const change = buildPullChangeEnvelope({
    table_name: 'clients',
    entity_id: 'client-1',
    action: 'upsert',
    data: {
      name: 'Northside Roofing',
      updated_at: '2026-03-11T16:30:30.000Z'
    }
  }, TENANT_ID, serverTimestamp);

  assert.strictEqual(change.tenant_id, TENANT_ID);
  assert.strictEqual(change.operation_type, 'upsert');
  assert.strictEqual(change.sync_status, 'synced');
  assert.strictEqual(change.entity_version, '2026-03-11T16:30:30.000Z');

  const envelope = buildSyncEnvelope({
    tenantId: TENANT_ID,
    deviceId: 'mobile-app-001',
    since: '2026-03-11T16:00:00.000Z',
    serverTimestamp,
    changes: [change]
  });

  assert.strictEqual(envelope.tenant_id, TENANT_ID);
  assert.strictEqual(envelope.device_id, 'mobile-app-001');
  assert.strictEqual(envelope.changes.length, 1);
};

const verifyConflictPolicies = () => {
  const staleClientUpdate = evaluateSyncConflict({
    tenantId: TENANT_ID,
    existingRecord: {
      id: 'client-1',
      name: 'Northside Roofing',
      updated_at: '2026-03-11T16:35:00.000Z'
    },
    change: {
      sync_item_id: 'sync-stale-client',
      tenant_id: TENANT_ID,
      table_name: 'clients',
      entity_id: 'client-1',
      entity_version: '2026-03-11T16:30:00.000Z',
      operation_type: 'upsert',
      retry_count: 0,
      data: {
        name: 'Northside Roofing (Old)'
      }
    }
  });

  assert(staleClientUpdate);
  assert.strictEqual(staleClientUpdate.status, 'success');
  assert.strictEqual(staleClientUpdate.conflict_code, 'stale_write_discarded');
  assert.strictEqual(staleClientUpdate.conflict_type, 'last_write_wins');
  assert.strictEqual(staleClientUpdate.resolution_strategy, 'server_wins_lww');

  const committedMonetaryItem = {
    id: 'item-2',
    type: 'invoice',
    status: 'confirmed',
    amount: '120.00',
    net_amount: '100.00',
    gross_amount: '120.00',
    vat_amount: '20.00',
    vat_rate: '20',
    currency: 'GBP',
    quarter_ref: '2026-Q1'
  };

  const immutableUpdateConflict = evaluateSyncConflict({
    tenantId: TENANT_ID,
    existingRecord: committedMonetaryItem,
    change: {
      sync_item_id: 'sync-immutable',
      tenant_id: TENANT_ID,
      table_name: 'capture_items',
      entity_id: committedMonetaryItem.id,
      entity_version: '2026-03-11T16:32:00.000Z',
      operation_type: 'upsert',
      retry_count: 0,
      data: {
        gross_amount: '150.00'
      }
    }
  });

  assert(immutableUpdateConflict);
  assert.strictEqual(immutableUpdateConflict.status, 'conflict');
  assert.strictEqual(immutableUpdateConflict.conflict_code, 'immutable_committed_truth');
  assert.strictEqual(immutableUpdateConflict.conflict_type, 'financially_sensitive');
  assert.strictEqual(immutableUpdateConflict.resolution_strategy, 'blocked_use_correction_flow');

  const tenantConflict = evaluateSyncConflict({
    tenantId: TENANT_ID,
    existingRecord: null,
    change: {
      sync_item_id: 'sync-tenant',
      tenant_id: '11111111-1111-1111-1111-111111111111',
      table_name: 'clients',
      entity_id: 'client-2',
      entity_version: '2026-03-11T16:33:00.000Z',
      operation_type: 'upsert',
      retry_count: 0,
      data: {
        name: 'Tenant Mismatch Ltd'
      }
    }
  });

  assert(tenantConflict);
  assert.strictEqual(tenantConflict.conflict_code, 'tenant_mismatch');
  assert.strictEqual(tenantConflict.conflict_type, 'tenant_scope');
  assert.strictEqual(tenantConflict.resolution_strategy, 'blocked_cross_tenant');
};

const main = () => {
  verifyNormalization();
  verifyPullEnvelope();
  verifyConflictPolicies();
  console.log('verify_sync_service=PASS');
  console.log(JSON.stringify({
    normalized_changes: 1,
    conflict_checks: 3,
    envelope_changes: 1
  }));
};

try {
  main();
} catch (error) {
  console.error('verify_sync_service=FAIL');
  console.error(error.message);
  process.exit(1);
}
