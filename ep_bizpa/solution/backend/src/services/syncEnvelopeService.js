const {
  validateArchiveRequest,
  validateItemUpdate
} = require('./monetaryIntegrityService');

const DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000000';
const DEFAULT_SYNC_STATUS = 'pending';
const CONFLICT_STATUS = 'conflict';
const STALE_WRITE_CODE = 'stale_write_discarded';

const buildSyncEnvelope = ({
  tenantId = DEFAULT_TENANT_ID,
  deviceId = 'unknown',
  since = null,
  serverTimestamp = new Date().toISOString(),
  changes = [],
  results = []
} = {}) => ({
  tenant_id: tenantId,
  device_id: deviceId,
  since,
  server_timestamp: serverTimestamp,
  changes,
  results
});

const buildQueueChangeEnvelope = ({
  syncItemId,
  tenantId = DEFAULT_TENANT_ID,
  tableName,
  entityId,
  entityVersion = null,
  operationType,
  queuedAt = new Date().toISOString(),
  syncStatus = DEFAULT_SYNC_STATUS,
  retryCount = 0,
  data = {}
}) => ({
  sync_item_id: syncItemId || `${tableName}:${entityId}:${queuedAt}`,
  tenant_id: tenantId,
  table_name: tableName,
  entity_id: entityId,
  entity_version: entityVersion,
  operation_type: operationType,
  queued_at: queuedAt,
  sync_status: syncStatus,
  retry_count: retryCount,
  data
});

const buildPullChangeEnvelope = (row, tenantId, serverTimestamp) => {
  const action = row.operation_type || row.action || 'upsert';
  const data = action === 'delete' ? {} : (row.data || {});
  const entityVersion =
    row.entity_version ||
    data.last_synced_at ||
    data.updated_at ||
    data.created_at ||
    serverTimestamp;

  return buildQueueChangeEnvelope({
    syncItemId: `${row.table_name}:${row.entity_id}:${entityVersion || serverTimestamp}`,
    tenantId,
    tableName: row.table_name,
    entityId: row.entity_id,
    entityVersion,
    operationType: action,
    queuedAt: serverTimestamp,
    syncStatus: 'synced',
    retryCount: 0,
    data
  });
};

const buildResultEnvelope = (change, overrides = {}) => ({
  sync_item_id: change.sync_item_id,
  tenant_id: change.tenant_id,
  table_name: change.table_name,
  entity_id: change.entity_id,
  entity_version: overrides.entity_version || change.entity_version || new Date().toISOString(),
  operation_type: change.operation_type || change.action,
  sync_status: overrides.sync_status || DEFAULT_SYNC_STATUS,
  retry_count: overrides.retry_count ?? change.retry_count ?? 0,
  status: overrides.status || 'success',
  conflict_code: overrides.conflict_code || null,
  conflict_type: overrides.conflict_type || null,
  resolution_strategy: overrides.resolution_strategy || null,
  error: overrides.error || null,
  policy_hook: overrides.policy_hook || null
});

const resolveRecordVersion = (record = {}) =>
  record.last_synced_at ||
  record.updated_at ||
  record.created_at ||
  null;

const isOlderVersion = (incomingVersion, existingVersion) => {
  if (!incomingVersion || !existingVersion) {
    return false;
  }

  const incomingTs = Date.parse(incomingVersion);
  const existingTs = Date.parse(existingVersion);
  if (Number.isNaN(incomingTs) || Number.isNaN(existingTs)) {
    return false;
  }

  return incomingTs < existingTs;
};

const evaluateSyncConflict = ({ tenantId, change, existingRecord }) => {
  if (change.tenant_id && change.tenant_id !== tenantId) {
    return buildResultEnvelope(change, {
      status: CONFLICT_STATUS,
      sync_status: CONFLICT_STATUS,
      conflict_code: 'tenant_mismatch',
      conflict_type: 'tenant_scope',
      resolution_strategy: 'blocked_cross_tenant',
      error: `Sync item tenant ${change.tenant_id} does not match active tenant ${tenantId}.`,
      policy_hook: 'manual_review_required'
    });
  }

  const existingVersion = resolveRecordVersion(existingRecord);
  if (existingRecord && change.table_name !== 'capture_items' && isOlderVersion(change.entity_version, existingVersion)) {
    return buildResultEnvelope(change, {
      status: 'success',
      sync_status: 'synced',
      conflict_code: STALE_WRITE_CODE,
      conflict_type: 'last_write_wins',
      resolution_strategy: 'server_wins_lww',
      entity_version: existingVersion,
      error: null,
      policy_hook: 'stale_non_financial_update_discarded'
    });
  }

  if (change.table_name !== 'capture_items' || !existingRecord) {
    return null;
  }

  if ((change.operation_type || change.action) === 'delete') {
    const archiveValidation = validateArchiveRequest(existingRecord);
    if (!archiveValidation.valid) {
      return buildResultEnvelope(change, {
        status: CONFLICT_STATUS,
        sync_status: CONFLICT_STATUS,
        conflict_code: 'immutable_committed_truth',
        conflict_type: 'financially_sensitive',
        resolution_strategy: 'blocked_use_correction_flow',
        error: archiveValidation.errors[0],
        policy_hook: 'use_correction_flow'
      });
    }
    return null;
  }

  const updateValidation = validateItemUpdate(existingRecord, change.data || {});
  if (!updateValidation.valid) {
    return buildResultEnvelope(change, {
      status: CONFLICT_STATUS,
      sync_status: CONFLICT_STATUS,
      conflict_code: 'immutable_committed_truth',
      conflict_type: 'financially_sensitive',
      resolution_strategy: 'blocked_use_correction_flow',
      error: updateValidation.errors[0],
      policy_hook: 'use_correction_flow'
    });
  }

  return null;
};

module.exports = {
  DEFAULT_SYNC_STATUS,
  DEFAULT_TENANT_ID,
  buildPullChangeEnvelope,
  buildQueueChangeEnvelope,
  buildResultEnvelope,
  buildSyncEnvelope,
  evaluateSyncConflict
};
