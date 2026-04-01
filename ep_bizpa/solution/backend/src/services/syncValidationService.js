const ALLOWED_SYNC_TABLES = new Set([
  'calendar_events',
  'capture_items',
  'clients',
  'diary_entries',
  'jobs',
  'message_templates',
  'outreach_logs',
  'trigger_rules'
]);

const ALLOWED_SYNC_ACTIONS = new Set(['upsert', 'delete']);
const FORBIDDEN_SYNC_FIELDS = new Set(['created_at', 'deleted_at', 'id', 'last_synced_at', 'updated_at', 'user_id']);
const ALLOWED_SYNC_STATUSES = new Set(['pending', 'syncing', 'retry_scheduled', 'conflict', 'synced', 'error']);

const normalizeSyncChange = (change = {}) => {
  const syncItemId = change.sync_item_id || change.id || null;
  const operationType = change.operation_type || change.action || null;
  const timestamp = change.queued_at || change.timestamp || null;
  const entityVersion = change.entity_version || change.timestamp || null;

  return {
    sync_item_id: syncItemId,
    tenant_id: change.tenant_id || null,
    table_name: change.table_name || null,
    entity_id: change.entity_id || null,
    entity_version: entityVersion,
    operation_type: operationType,
    queued_at: timestamp,
    sync_status: change.sync_status || 'pending',
    retry_count: Number.isInteger(change.retry_count) ? change.retry_count : Number(change.retry_count || 0),
    action: operationType,
    data: change.data
  };
};

const validateSyncChanges = (changes) => {
  const errors = [];
  const sanitizedChanges = [];
  const seenEntities = new Set();

  if (!Array.isArray(changes)) {
    return {
      valid: false,
      errors: ['changes must be an array.'],
      sanitizedChanges: []
    };
  }

  changes.forEach((change, index) => {
    if (!change || typeof change !== 'object') {
      errors.push(`changes[${index}] must be an object.`);
      return;
    }

    const normalizedChange = normalizeSyncChange(change);
    const {
      sync_item_id: syncItemId,
      tenant_id: tenantId,
      table_name: tableName,
      entity_id: entityId,
      entity_version: entityVersion,
      operation_type: action,
      queued_at: queuedAt,
      sync_status: syncStatus,
      retry_count: retryCount,
      data
    } = normalizedChange;

    if (!syncItemId) {
      errors.push(`changes[${index}] is missing sync_item_id.`);
    }
    if (!ALLOWED_SYNC_TABLES.has(tableName)) {
      errors.push(`changes[${index}] targets unsupported table "${tableName}".`);
    }
    if (!ALLOWED_SYNC_ACTIONS.has(action)) {
      errors.push(`changes[${index}] has unsupported action "${action}".`);
    }
    if (!entityId) {
      errors.push(`changes[${index}] is missing entity_id.`);
    }

    if (tenantId !== null && typeof tenantId !== 'string') {
      errors.push(`changes[${index}] tenant_id must be a string when provided.`);
    }
    if (entityVersion !== null && typeof entityVersion !== 'string') {
      errors.push(`changes[${index}] entity_version must be a string when provided.`);
    }
    if (queuedAt !== null && typeof queuedAt !== 'string') {
      errors.push(`changes[${index}] queued_at must be a string when provided.`);
    }
    if (!ALLOWED_SYNC_STATUSES.has(syncStatus)) {
      errors.push(`changes[${index}] has unsupported sync_status "${syncStatus}".`);
    }
    if (!Number.isFinite(retryCount) || retryCount < 0) {
      errors.push(`changes[${index}] retry_count must be a non-negative number.`);
    }

    const dedupeKey = syncItemId || `${tableName}:${entityId}`;
    if (seenEntities.has(dedupeKey)) {
      errors.push(`changes[${index}] duplicates entity "${dedupeKey}" in the same sync batch.`);
    } else {
      seenEntities.add(dedupeKey);
    }

    if (action === 'upsert') {
      if (!data || typeof data !== 'object' || Array.isArray(data)) {
        errors.push(`changes[${index}] must provide an object data payload for upsert.`);
        return;
      }

      const forbiddenFields = Object.keys(data).filter((field) => FORBIDDEN_SYNC_FIELDS.has(field));
      if (forbiddenFields.length > 0) {
        errors.push(`changes[${index}] attempts to modify server-managed fields: ${forbiddenFields.join(', ')}.`);
      }

      sanitizedChanges.push({
        sync_item_id: syncItemId,
        tenant_id: tenantId,
        table_name: tableName,
        entity_id: entityId,
        entity_version: entityVersion,
        operation_type: action,
        queued_at: queuedAt,
        sync_status: syncStatus,
        retry_count: retryCount,
        action,
        data: Object.fromEntries(Object.entries(data).filter(([, value]) => value !== undefined))
      });
      return;
    }

    if (data && Object.keys(data).length > 0) {
      errors.push(`changes[${index}] delete actions must not include a data payload.`);
    }

    sanitizedChanges.push({
      sync_item_id: syncItemId,
      tenant_id: tenantId,
      table_name: tableName,
      entity_id: entityId,
      entity_version: entityVersion,
      operation_type: action,
      queued_at: queuedAt,
      sync_status: syncStatus,
      retry_count: retryCount,
      action,
      data: {}
    });
  });

  return {
    valid: errors.length === 0,
    errors,
    sanitizedChanges
  };
};

module.exports = {
  ALLOWED_SYNC_ACTIONS,
  ALLOWED_SYNC_STATUSES,
  ALLOWED_SYNC_TABLES,
  FORBIDDEN_SYNC_FIELDS,
  normalizeSyncChange,
  validateSyncChanges
};
