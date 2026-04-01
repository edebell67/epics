const fs = require('fs');
const path = require('path');
const { appendBusinessEvent } = require('./businessEventLogService');

const contractsPath = path.join(__dirname, '..', 'models', 'integration_connector_contracts.json');
const integrationContracts = JSON.parse(fs.readFileSync(contractsPath, 'utf8'));

const PLUGIN_TYPES = Object.keys(integrationContracts.contracts);
const ROLLOUT_STAGES = ['planned', 'internal', 'pilot', 'beta', 'general_availability', 'disabled', 'rollback'];
const DEFAULT_SOURCE_TYPE = 'manual';

class IntegrationRegistryError extends Error {
  constructor(message, statusCode = 400, details = {}) {
    super(message);
    this.name = 'IntegrationRegistryError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

const ensureExecutor = (executor) => {
  if (!executor || typeof executor.query !== 'function') {
    throw new Error('A database executor with query(text, params) is required.');
  }
  return executor;
};

const normalizePluginId = (value) => String(value || '').trim().toLowerCase();

const normalizePluginType = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (!PLUGIN_TYPES.includes(normalized)) {
    throw new IntegrationRegistryError('plugin_type must be one of accounting_export, payments, communications, or calendar.', 400, {
      field: 'plugin_type',
      allowed_values: PLUGIN_TYPES
    });
  }
  return normalized;
};

const normalizeVersion = (value) => {
  const normalized = String(value || '').trim();
  if (!normalized || !/^[A-Za-z0-9._-]+$/.test(normalized)) {
    throw new IntegrationRegistryError('version is required and may contain only letters, numbers, dots, underscores, or hyphens.', 400, {
      field: 'version'
    });
  }
  return normalized;
};

const normalizeRolloutStage = (value = 'planned') => {
  const normalized = String(value || 'planned').trim().toLowerCase();
  if (!ROLLOUT_STAGES.includes(normalized)) {
    throw new IntegrationRegistryError('rollout_stage is invalid.', 400, {
      field: 'rollout_stage',
      allowed_values: ROLLOUT_STAGES
    });
  }
  return normalized;
};

const normalizeTenantScope = (value, userId) => {
  const normalized = String(value || `tenant:${userId}`).trim();
  if (!normalized) {
    throw new IntegrationRegistryError('tenant_scope is required.', 400, {
      field: 'tenant_scope'
    });
  }
  return normalized;
};

const normalizeMetadata = (value) => {
  if (!value) {
    return {};
  }
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch (error) {
      return {};
    }
  }
  return typeof value === 'object' ? value : {};
};

const normalizeRegistryRow = (row) => {
  if (!row) {
    return null;
  }

  const pluginType = row.plugin_type;
  const contract = integrationContracts.contracts[pluginType] || null;
  return {
    id: row.id,
    user_id: row.user_id,
    plugin_id: row.plugin_id,
    plugin_type: pluginType,
    version: row.version,
    enabled: Boolean(row.enabled),
    tenant_scope: row.tenant_scope,
    rollout_stage: row.rollout_stage,
    rollback_target: row.rollback_target || null,
    contract_version: row.contract_version,
    metadata: normalizeMetadata(row.metadata),
    updated_at: row.updated_at ? new Date(row.updated_at).toISOString() : null,
    updated_by: row.updated_by || 'system',
    contract
  };
};

const listConnectorContracts = () => ({
  schema_version: integrationContracts.schema_version,
  plugin_types: PLUGIN_TYPES,
  contracts: PLUGIN_TYPES.map((pluginType) => integrationContracts.contracts[pluginType])
});

const getRegistryEntry = async (executor, { user_id, plugin_id }) => {
  const client = ensureExecutor(executor);
  const normalizedPluginId = normalizePluginId(plugin_id);
  const result = await client.query(
    `
    SELECT
      id,
      user_id,
      plugin_id,
      plugin_type,
      version,
      enabled,
      tenant_scope,
      rollout_stage,
      rollback_target,
      contract_version,
      metadata,
      updated_at,
      updated_by
    FROM integration_plugin_registry
    WHERE user_id = $1 AND plugin_id = $2
    LIMIT 1
    `,
    [user_id, normalizedPluginId]
  );

  return normalizeRegistryRow(result.rows[0]);
};

const listIntegrationRegistry = async (executor, {
  user_id,
  plugin_type = null,
  enabled = null,
  tenant_scope = null
}) => {
  const client = ensureExecutor(executor);
  const params = [user_id];
  const clauses = ['user_id = $1'];
  let index = 2;

  if (plugin_type) {
    clauses.push(`plugin_type = $${index++}`);
    params.push(normalizePluginType(plugin_type));
  }

  if (enabled !== null && enabled !== undefined) {
    clauses.push(`enabled = $${index++}`);
    params.push(Boolean(enabled));
  }

  if (tenant_scope) {
    clauses.push(`tenant_scope = $${index++}`);
    params.push(String(tenant_scope).trim());
  }

  const result = await client.query(
    `
    SELECT
      id,
      user_id,
      plugin_id,
      plugin_type,
      version,
      enabled,
      tenant_scope,
      rollout_stage,
      rollback_target,
      contract_version,
      metadata,
      updated_at,
      updated_by
    FROM integration_plugin_registry
    WHERE ${clauses.join(' AND ')}
    ORDER BY plugin_type ASC, plugin_id ASC
    `,
    params
  );

  return result.rows.map(normalizeRegistryRow);
};

const upsertIntegrationRegistryEntry = async (executor, {
  user_id,
  actor_id,
  source_type = DEFAULT_SOURCE_TYPE,
  plugin_id,
  plugin_type,
  version,
  enabled = false,
  tenant_scope = null,
  rollout_stage = 'planned',
  rollback_target = null,
  metadata = {}
}) => {
  const client = ensureExecutor(executor);
  const normalizedPluginId = normalizePluginId(plugin_id);
  if (!normalizedPluginId) {
    throw new IntegrationRegistryError('plugin_id is required.', 400, {
      field: 'plugin_id'
    });
  }

  const normalizedPluginType = normalizePluginType(plugin_type);
  const normalizedVersion = normalizeVersion(version);
  const normalizedTenantScope = normalizeTenantScope(tenant_scope, user_id);
  const normalizedRolloutStage = normalizeRolloutStage(rollout_stage);
  const contract = integrationContracts.contracts[normalizedPluginType];
  const previousState = await getRegistryEntry(client, {
    user_id,
    plugin_id: normalizedPluginId
  });

  const result = await client.query(
    `
    INSERT INTO integration_plugin_registry (
      user_id,
      plugin_id,
      plugin_type,
      version,
      enabled,
      tenant_scope,
      rollout_stage,
      rollback_target,
      contract_version,
      metadata,
      updated_by
    )
    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11)
    ON CONFLICT (user_id, plugin_id)
    DO UPDATE SET
      plugin_type = EXCLUDED.plugin_type,
      version = EXCLUDED.version,
      enabled = EXCLUDED.enabled,
      tenant_scope = EXCLUDED.tenant_scope,
      rollout_stage = EXCLUDED.rollout_stage,
      rollback_target = EXCLUDED.rollback_target,
      contract_version = EXCLUDED.contract_version,
      metadata = EXCLUDED.metadata,
      updated_by = EXCLUDED.updated_by,
      updated_at = CURRENT_TIMESTAMP
    RETURNING
      id,
      user_id,
      plugin_id,
      plugin_type,
      version,
      enabled,
      tenant_scope,
      rollout_stage,
      rollback_target,
      contract_version,
      metadata,
      updated_at,
      updated_by
    `,
    [
      user_id,
      normalizedPluginId,
      normalizedPluginType,
      normalizedVersion,
      Boolean(enabled),
      normalizedTenantScope,
      normalizedRolloutStage,
      rollback_target ? String(rollback_target).trim() : null,
      contract.contract_version,
      JSON.stringify(metadata || {}),
      actor_id || 'system'
    ]
  );

  const nextState = normalizeRegistryRow(result.rows[0]);
  const changeAction = previousState ? 'updated' : 'created';
  const toggleAction = nextState.enabled ? 'enabled' : 'disabled';

  await appendBusinessEvent(client, {
    user_id,
    actor_id: actor_id || 'system',
    source_type,
    event_type: 'governance_policy_changed',
    entity_id: nextState.id,
    entity_type: 'integration_plugin',
    description: `Integration plugin ${nextState.plugin_id} ${changeAction} and ${toggleAction}`,
    metadata: {
      governance_domain: 'integration_registry',
      plugin_id: nextState.plugin_id,
      plugin_type: nextState.plugin_type,
      version: nextState.version,
      enabled: nextState.enabled,
      tenant_scope: nextState.tenant_scope,
      rollout_stage: nextState.rollout_stage,
      rollback_target: nextState.rollback_target,
      contract_version: nextState.contract_version,
      previous_state: previousState ? {
        plugin_type: previousState.plugin_type,
        version: previousState.version,
        enabled: previousState.enabled,
        tenant_scope: previousState.tenant_scope,
        rollout_stage: previousState.rollout_stage,
        rollback_target: previousState.rollback_target
      } : null,
      ...normalizeMetadata(metadata)
    }
  });

  return nextState;
};

module.exports = {
  IntegrationRegistryError,
  PLUGIN_TYPES,
  ROLLOUT_STAGES,
  getRegistryEntry,
  listConnectorContracts,
  listIntegrationRegistry,
  normalizePluginId,
  upsertIntegrationRegistryEntry
};
