const assert = require('assert');
const businessEventController = require('./src/controllers/businessEventController');
const businessEventRoutes = require('./src/routes/businessEventRoutes');
const {
  PLUGIN_TYPES,
  getRegistryEntry,
  listConnectorContracts,
  listIntegrationRegistry,
  upsertIntegrationRegistryEntry
} = require('./src/services/integrationRegistryService');
const { listBusinessEvents } = require('./src/services/businessEventLogService');

class MockExecutor {
  constructor() {
    this.registry = new Map();
    this.events = [];
    this.counter = 1;
  }

  key(userId, pluginId) {
    return `${userId}:${pluginId}`;
  }

  async query(text, params) {
    const sql = text.replace(/\s+/g, ' ').trim();

    if (sql.includes('FROM integration_plugin_registry WHERE user_id = $1 AND plugin_id = $2')) {
      const row = this.registry.get(this.key(params[0], params[1]));
      return { rows: row ? [{ ...row }] : [] };
    }

    if (sql.includes('FROM integration_plugin_registry WHERE')) {
      const rows = [...this.registry.values()]
        .filter((row) => row.user_id === params[0])
        .filter((row) => !sql.includes('plugin_type = $2') || row.plugin_type === params[1])
        .filter((row) => !sql.includes('enabled = $') || row.enabled === params[sql.includes('plugin_type = $2') ? 2 : 1])
        .filter((row) => !sql.includes('tenant_scope = $') || row.tenant_scope === params[params.length - 1])
        .sort((left, right) => {
          const typeCompare = String(left.plugin_type).localeCompare(String(right.plugin_type));
          if (typeCompare !== 0) {
            return typeCompare;
          }
          return String(left.plugin_id).localeCompare(String(right.plugin_id));
        });
      return { rows };
    }

    if (sql.includes('INSERT INTO integration_plugin_registry')) {
      const existing = this.registry.get(this.key(params[0], params[1]));
      const row = {
        id: existing?.id || `00000000-0000-0000-0000-${String(this.counter++).padStart(12, '0')}`,
        user_id: params[0],
        plugin_id: params[1],
        plugin_type: params[2],
        version: params[3],
        enabled: params[4],
        tenant_scope: params[5],
        rollout_stage: params[6],
        rollback_target: params[7],
        contract_version: params[8],
        metadata: JSON.parse(params[9] || '{}'),
        updated_at: new Date().toISOString(),
        updated_by: params[10]
      };
      this.registry.set(this.key(params[0], params[1]), row);
      return { rows: [{ ...row }] };
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

    if (sql.includes('SELECT event_id,')) {
      const rows = this.events
        .filter((row) => row.user_id === params[0])
        .sort((left, right) => String(right.created_at).localeCompare(String(left.created_at)))
        .map((row) => ({
          event_id: row.event_id,
          event_type: row.event_type,
          entity_id: row.entity_id,
          entity_type: row.entity_type,
          timestamp: row.created_at,
          actor_id: row.actor_id,
          description: row.description,
          metadata: row.metadata,
          quarter_reference: row.quarter_reference,
          status_from: row.status_from,
          status_to: row.status_to
        }));
      return { rows };
    }

    throw new Error(`Unsupported SQL in integration registry mock: ${sql}`);
  }
}

const userId = '00000000-0000-0000-0000-000000000000';

const routeExists = (method, path) => businessEventRoutes.stack.some((layer) => {
  if (!layer.route) {
    return false;
  }
  return Boolean(layer.route.methods[method]) && layer.route.path === path;
});

const runContractsScenario = () => {
  const contracts = listConnectorContracts();
  assert.strictEqual(contracts.schema_version, '2026-03-11.a1');
  assert.deepStrictEqual(contracts.plugin_types, PLUGIN_TYPES);
  assert.strictEqual(contracts.contracts.length, 4);
  assert(contracts.contracts.every((contract) => contract.required_capabilities.length === 3));
  assert(routeExists('get', '/governance/plugins/contracts'));
  assert(typeof businessEventController.getIntegrationContracts === 'function');

  return {
    plugin_types: contracts.plugin_types,
    contract_versions: contracts.contracts.map((contract) => `${contract.plugin_type}:${contract.contract_version}`)
  };
};

const runRegistryScenario = async () => {
  const executor = new MockExecutor();

  const created = await upsertIntegrationRegistryEntry(executor, {
    user_id: userId,
    actor_id: userId,
    plugin_id: 'xero_export',
    plugin_type: 'accounting_export',
    version: '1.0.0',
    enabled: false,
    tenant_scope: 'tenant:alpha',
    rollout_stage: 'planned',
    rollback_target: 'legacy_csv_export',
    metadata: { change_ticket: 'INT-101' }
  });

  const enabled = await upsertIntegrationRegistryEntry(executor, {
    user_id: userId,
    actor_id: userId,
    plugin_id: 'xero_export',
    plugin_type: 'accounting_export',
    version: '1.1.0',
    enabled: true,
    tenant_scope: 'tenant:alpha',
    rollout_stage: 'pilot',
    rollback_target: 'legacy_csv_export',
    metadata: { change_ticket: 'INT-102' }
  });

  await upsertIntegrationRegistryEntry(executor, {
    user_id: userId,
    actor_id: userId,
    plugin_id: 'sms_bridge',
    plugin_type: 'communications',
    version: '0.9.0',
    enabled: true,
    tenant_scope: 'tenant:beta',
    rollout_stage: 'beta',
    rollback_target: 'manual_sms',
    metadata: { change_ticket: 'INT-103' }
  });

  const registry = await listIntegrationRegistry(executor, { user_id: userId });
  const tenantAlphaOnly = await listIntegrationRegistry(executor, {
    user_id: userId,
    tenant_scope: 'tenant:alpha'
  });
  const stored = await getRegistryEntry(executor, {
    user_id: userId,
    plugin_id: 'xero_export'
  });
  const history = await listBusinessEvents(executor, { user_id: userId, limit: 20, offset: 0 });

  assert.strictEqual(created.enabled, false);
  assert.strictEqual(enabled.enabled, true);
  assert.strictEqual(enabled.version, '1.1.0');
  assert.strictEqual(enabled.rollout_stage, 'pilot');
  assert.strictEqual(enabled.rollback_target, 'legacy_csv_export');
  assert.strictEqual(registry.length, 2);
  assert.strictEqual(tenantAlphaOnly.length, 1);
  assert.strictEqual(stored.tenant_scope, 'tenant:alpha');
  assert(history.length >= 3);
  assert(history.every((event) => event.event_type === 'governance_policy_changed'));
  assert(history.some((event) => event.metadata.plugin_id === 'xero_export' && event.metadata.enabled === true));
  assert(history.some((event) => event.metadata.previous_state && event.metadata.previous_state.enabled === false));
  assert(routeExists('get', '/governance/plugins'));
  assert(routeExists('patch', '/governance/plugins/:pluginId'));
  assert(typeof businessEventController.getIntegrationRegistry === 'function');
  assert(typeof businessEventController.setIntegrationRegistryEntry === 'function');

  return {
    registry_size: registry.length,
    tenant_alpha_entries: tenantAlphaOnly.length,
    latest_versions: registry.map((entry) => `${entry.plugin_id}:${entry.version}`),
    audit_events: history.map((event) => `${event.metadata.plugin_id}:${event.metadata.enabled}`)
  };
};

const run = async () => {
  const mode = (process.argv[2] || 'all').toLowerCase();
  const results = {};

  if (!['contracts', 'registry', 'all'].includes(mode)) {
    throw new Error(`Unknown mode "${mode}". Use contracts, registry, or all.`);
  }

  if (mode === 'contracts' || mode === 'all') {
    results.contracts = runContractsScenario();
  }

  if (mode === 'registry' || mode === 'all') {
    results.registry = await runRegistryScenario();
  }

  console.log(`verify_integration_registry=${mode.toUpperCase()}=PASS`);
  console.log(JSON.stringify(results));
};

run().catch((error) => {
  console.error('verify_integration_registry=FAIL');
  console.error(error);
  process.exit(1);
});
