const assert = require('assert');

const {
  buildSyncHealthSnapshot,
  buildSyncRunTelemetry
} = require('./src/services/syncHealthService');

const TENANT_ID = '00000000-0000-0000-0000-000000000000';
const DEVICE_ID = 'mobile-app-001';

const pushTelemetry = buildSyncRunTelemetry({
  tenantId: TENANT_ID,
  deviceId: DEVICE_ID,
  direction: 'push',
  startedAt: '2026-03-11T20:00:00.000Z',
  completedAt: '2026-03-11T20:01:00.000Z',
  results: [
    {
      sync_item_id: 'sync-1',
      entity_id: 'client-1',
      table_name: 'clients',
      status: 'success'
    },
    {
      sync_item_id: 'sync-2',
      entity_id: 'item-2',
      table_name: 'capture_items',
      status: 'conflict',
      conflict_code: 'immutable_committed_truth',
      conflict_type: 'financially_sensitive',
      resolution_strategy: 'blocked_use_correction_flow'
    },
    {
      sync_item_id: 'sync-3',
      entity_id: 'job-1',
      table_name: 'jobs',
      status: 'error',
      error: 'deadlock detected'
    }
  ],
  backlogSize: 2,
  lastSuccessfulSync: '2026-03-11T19:55:00.000Z'
});

assert.strictEqual(pushTelemetry.tenant_scope, TENANT_ID);
assert.strictEqual(pushTelemetry.backlog_size, 2);
assert.strictEqual(pushTelemetry.error_rate, 0.3333);
assert.strictEqual(pushTelemetry.last_successful_sync, '2026-03-11T19:55:00.000Z');
assert.strictEqual(pushTelemetry.conflict_samples.length, 1);
assert.strictEqual(pushTelemetry.error_samples.length, 1);

const successTelemetry = buildSyncRunTelemetry({
  tenantId: TENANT_ID,
  deviceId: DEVICE_ID,
  direction: 'pull',
  startedAt: '2026-03-11T20:05:00.000Z',
  completedAt: '2026-03-11T20:05:30.000Z',
  changes: [{ entity_id: 'client-2' }],
  status: 'success',
  backlogSize: 0
});

const healthSnapshot = buildSyncHealthSnapshot({
  tenantId: TENANT_ID,
  deviceId: DEVICE_ID,
  recentRuns: [pushTelemetry, successTelemetry],
  latestBacklogSize: pushTelemetry.backlog_size,
  lastSuccessfulSync: successTelemetry.last_successful_sync
});

assert.strictEqual(healthSnapshot.tenant_scope, TENANT_ID);
assert.strictEqual(healthSnapshot.device_id, DEVICE_ID);
assert.strictEqual(healthSnapshot.backlog_size, 2);
assert.strictEqual(healthSnapshot.error_rate, 0.25);
assert.strictEqual(healthSnapshot.last_successful_sync, '2026-03-11T20:05:30.000Z');
assert.strictEqual(healthSnapshot.recent_conflicts.length, 1);
assert.strictEqual(healthSnapshot.recent_errors.length, 1);

console.log('verify_sync_health_telemetry=PASS');
console.log(JSON.stringify({
  backlog_size: healthSnapshot.backlog_size,
  error_rate: healthSnapshot.error_rate,
  last_successful_sync: healthSnapshot.last_successful_sync,
  tenant_scope: healthSnapshot.tenant_scope
}));
