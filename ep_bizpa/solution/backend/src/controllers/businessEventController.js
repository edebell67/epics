const db = require('../config/db');
const {
  EVENT_TYPE_CATALOG,
  deriveQuarterFromDate,
  listBusinessEvents,
  recordReadinessRecalculated
} = require('../services/businessEventLogService');
const { listBusinessActivityInbox } = require('../services/businessActivityInboxService');
const {
  InboxActionError,
  applyInboxAction
} = require('../services/inboxActionService');
const {
  AutoCommitGovernanceError,
  disableAutoCommit,
  enableAutoCommit,
  getAutoCommitState,
  updateAutoCommitPolicy
} = require('../services/autoCommitGovernanceService');
const {
  IntegrationRegistryError,
  listConnectorContracts,
  listIntegrationRegistry,
  upsertIntegrationRegistryEntry
} = require('../services/integrationRegistryService');
const {
  SnapshotVersioningError,
  createQuarterSnapshotVersion,
  getQuarterSnapshotStatus
} = require('../services/snapshotVersioningService');
const {
  QuarterGovernanceError,
  closeQuarterLifecycle,
  getQuarterLifecycle,
  reopenQuarterLifecycle
} = require('../services/quarterLifecycleService');
const { getEntityDetailView } = require('../services/entityDetailViewService');

const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000000';

const getEventCatalog = async (req, res) => res.status(200).json({
  event_types: EVENT_TYPE_CATALOG
});

const getBusinessHistory = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const rows = await listBusinessEvents(db, {
      user_id: userId,
      entity_id: req.query.entity_id,
      entity_type: req.query.entity_type,
      event_type: req.query.event_type,
      quarter_reference: req.query.quarter_reference,
      limit: req.query.limit,
      offset: req.query.offset
    });
    return res.status(200).json(rows);
  } catch (err) {
    console.error('[BusinessEventController] getBusinessHistory failed:', err);
    return res.status(500).json({ error: 'Failed to load business history.' });
  }
};

const getBusinessActivityInbox = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const payload = await listBusinessActivityInbox(db, {
      user_id: userId,
      filter: req.query.filter,
      quarter_reference: req.query.quarter_reference,
      entity_id: req.query.entity_id,
      entity_type: req.query.entity_type,
      limit: req.query.limit,
      offset: req.query.offset
    });
    return res.status(200).json(payload);
  } catch (err) {
    console.error('[BusinessEventController] getBusinessActivityInbox failed:', err);
    return res.status(500).json({ error: 'Failed to load business activity inbox.' });
  }
};

const getEntityDeepDiveView = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const payload = await getEntityDetailView(db, {
      user_id: userId,
      entity_id: req.params.entityId,
      entity_type: req.params.entityType
    });
    return res.status(200).json(payload);
  } catch (err) {
    console.error('[BusinessEventController] getEntityDeepDiveView failed:', err);
    const statusCode = err.statusCode || 500;
    return res.status(statusCode).json({ error: err.message || 'Failed to load entity detail view.' });
  }
};

const postBusinessActivityInboxAction = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const result = await applyInboxAction(db, {
      ...req.body,
      user_id: userId,
      actor_id: req.user?.id || userId,
      source_type: req.body?.source_type || 'manual'
    });
    return res.status(result.statusCode || 200).json(result);
  } catch (err) {
    console.error('[BusinessEventController] postBusinessActivityInboxAction failed:', err);
    if (err instanceof InboxActionError) {
      return res.status(err.statusCode).json({
        error: err.message,
        details: err.details
      });
    }
    return res.status(500).json({ error: 'Failed to apply inbox action.' });
  }
};

const createSnapshot = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const {
    quarter_reference,
    transaction_date,
    description = 'Quarter snapshot generated',
    metadata = {}
  } = req.body || {};

  const quarterReference = quarter_reference || deriveQuarterFromDate(transaction_date);
  if (!quarterReference) {
    return res.status(400).json({ error: 'quarter_reference or transaction_date is required.' });
  }

  try {
    const event = await createQuarterSnapshotVersion(db, {
      user_id: userId,
      actor_id: req.user?.id || userId,
      source_type: metadata.source_type || 'manual',
      quarter_reference: quarterReference,
      description,
      metadata
    });
    return res.status(201).json(event);
  } catch (err) {
    if (err instanceof SnapshotVersioningError) {
      return res.status(err.statusCode).json({
        error: err.message,
        details: err.details
      });
    }
    console.error('[BusinessEventController] createSnapshot failed:', err);
    return res.status(500).json({ error: 'Failed to create snapshot event.' });
  }
};

const getQuarterSnapshotVersionStatus = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const [status, lifecycle] = await Promise.all([
      getQuarterSnapshotStatus(db, {
        userId,
        quarterReference: req.params.quarterReference
      }),
      getQuarterLifecycle(db, {
        userId,
        quarterReference: req.params.quarterReference
      })
    ]);
    return res.status(200).json({
      ...status,
      quarter_lifecycle: lifecycle
    });
  } catch (err) {
    console.error('[BusinessEventController] getQuarterSnapshotVersionStatus failed:', err);
    return res.status(500).json({ error: 'Failed to load quarter snapshot status.' });
  }
};

const getQuarterLifecycleStatus = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const lifecycle = await getQuarterLifecycle(db, {
      userId,
      quarterReference: req.params.quarterReference
    });
    return res.status(200).json(lifecycle);
  } catch (err) {
    console.error('[BusinessEventController] getQuarterLifecycleStatus failed:', err);
    return res.status(500).json({ error: 'Failed to load quarter lifecycle status.' });
  }
};

const closeQuarter = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const quarter = await closeQuarterLifecycle(db, {
      user_id: userId,
      actor_id: req.user?.id || userId,
      source_type: 'manual',
      quarter_reference: req.params.quarterReference,
      reason: req.body?.reason || null,
      metadata: req.body?.metadata || {}
    });
    return res.status(200).json({
      quarter_reference: req.params.quarterReference,
      ...quarter
    });
  } catch (err) {
    if (err instanceof QuarterGovernanceError) {
      return res.status(err.statusCode).json({
        error: err.message,
        details: err.details
      });
    }
    console.error('[BusinessEventController] closeQuarter failed:', err);
    return res.status(500).json({ error: 'Failed to close quarter.' });
  }
};

const reopenQuarter = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const quarter = await reopenQuarterLifecycle(db, {
      user_id: userId,
      actor_id: req.user?.id || userId,
      source_type: 'manual',
      quarter_reference: req.params.quarterReference,
      reason: req.body?.reason,
      confirmation_reference: req.body?.confirmation_reference,
      metadata: req.body?.metadata || {}
    });
    return res.status(200).json({
      quarter_reference: req.params.quarterReference,
      ...quarter
    });
  } catch (err) {
    if (err instanceof QuarterGovernanceError) {
      return res.status(err.statusCode).json({
        error: err.message,
        details: err.details
      });
    }
    console.error('[BusinessEventController] reopenQuarter failed:', err);
    return res.status(500).json({ error: 'Failed to reopen quarter.' });
  }
};

const setAutoCommit = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    if (Object.prototype.hasOwnProperty.call(req.body || {}, 'owner_policy_allows_auto_commit')
      || Object.prototype.hasOwnProperty.call(req.body || {}, 'max_allowed_duration')
      || Object.prototype.hasOwnProperty.call(req.body || {}, 'max_auto_commit_amount')
      || Object.prototype.hasOwnProperty.call(req.body || {}, 'threshold_override_limit')
      || Object.prototype.hasOwnProperty.call(req.body || {}, 'low_confidence_threshold')) {
      const policy = await updateAutoCommitPolicy(db, {
        user_id: userId,
        actor_id: req.user?.id || userId,
        source_type: 'manual',
        owner_policy_allows_auto_commit: req.body?.owner_policy_allows_auto_commit,
        max_allowed_duration: req.body?.max_allowed_duration,
        max_auto_commit_amount: req.body?.max_auto_commit_amount,
        threshold_override_limit: req.body?.threshold_override_limit,
        low_confidence_threshold: req.body?.low_confidence_threshold,
        metadata: req.body?.metadata || {}
      });
      return res.status(200).json(policy);
    }

    if (Boolean(req.body?.enabled)) {
      const state = await enableAutoCommit(db, {
        user_id: userId,
        actor_id: req.user?.id || userId,
        source_type: 'manual',
        duration: req.body?.duration,
        risk_acknowledged: req.body?.risk_acknowledged,
        confirmation_reference: req.body?.confirmation_reference,
        threshold_override: req.body?.threshold_override,
        metadata: req.body?.metadata || {}
      });
      return res.status(200).json(state);
    }

    const state = await disableAutoCommit(db, {
      user_id: userId,
      actor_id: req.user?.id || userId,
      source_type: 'manual',
      reason: req.body?.reason || 'manual_disable',
      metadata: req.body?.metadata || {}
    });
    return res.status(200).json(state);
  } catch (err) {
    console.error('[BusinessEventController] setAutoCommit failed:', err);
    if (err instanceof AutoCommitGovernanceError) {
      return res.status(err.statusCode).json({ error: err.message, details: err.details });
    }
    return res.status(500).json({ error: 'Failed to update auto-commit setting.' });
  }
};

const getAutoCommit = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const state = await getAutoCommitState(db, {
      userId
    });
    return res.status(200).json(state);
  } catch (err) {
    console.error('[BusinessEventController] getAutoCommit failed:', err);
    return res.status(500).json({ error: 'Failed to load auto-commit setting.' });
  }
};

const getIntegrationContracts = async (req, res) => {
  try {
    return res.status(200).json(listConnectorContracts());
  } catch (err) {
    console.error('[BusinessEventController] getIntegrationContracts failed:', err);
    return res.status(500).json({ error: 'Failed to load integration contracts.' });
  }
};

const getIntegrationRegistry = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const rows = await listIntegrationRegistry(db, {
      user_id: userId,
      plugin_type: req.query.plugin_type,
      enabled: Object.prototype.hasOwnProperty.call(req.query, 'enabled')
        ? req.query.enabled === 'true'
        : null,
      tenant_scope: req.query.tenant_scope
    });
    return res.status(200).json({
      contracts: listConnectorContracts(),
      registry: rows
    });
  } catch (err) {
    console.error('[BusinessEventController] getIntegrationRegistry failed:', err);
    if (err instanceof IntegrationRegistryError) {
      return res.status(err.statusCode).json({ error: err.message, details: err.details });
    }
    return res.status(500).json({ error: 'Failed to load integration registry.' });
  }
};

const setIntegrationRegistryEntry = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const entry = await upsertIntegrationRegistryEntry(db, {
      user_id: userId,
      actor_id: req.user?.id || userId,
      source_type: 'manual',
      plugin_id: req.params.pluginId,
      plugin_type: req.body?.plugin_type,
      version: req.body?.version,
      enabled: req.body?.enabled,
      tenant_scope: req.body?.tenant_scope,
      rollout_stage: req.body?.rollout_stage,
      rollback_target: req.body?.rollback_target,
      metadata: req.body?.metadata || {}
    });
    return res.status(200).json(entry);
  } catch (err) {
    console.error('[BusinessEventController] setIntegrationRegistryEntry failed:', err);
    if (err instanceof IntegrationRegistryError) {
      return res.status(err.statusCode).json({ error: err.message, details: err.details });
    }
    return res.status(500).json({ error: 'Failed to update integration registry entry.' });
  }
};

const recordReadinessSnapshot = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const {
    quarter_reference = null,
    total_txns_in_period,
    blocking_txns_count,
    readiness_pct,
    can_export
  } = req.body || {};

  try {
    const event = await recordReadinessRecalculated(db, {
      user_id: userId,
      actor_id: req.user?.id || userId,
      source_type: 'system',
      quarter_reference,
      description: `Readiness recalculated${quarter_reference ? ` for ${quarter_reference}` : ''}`,
      metadata: {
        total_txns_in_period,
        blocking_txns_count,
        readiness_pct,
        can_export
      }
    });
    return res.status(201).json(event);
  } catch (err) {
    console.error('[BusinessEventController] recordReadinessSnapshot failed:', err);
    return res.status(500).json({ error: 'Failed to record readiness event.' });
  }
};

module.exports = {
  closeQuarter,
  createSnapshot,
  getBusinessActivityInbox,
  getBusinessHistory,
  getEntityDeepDiveView,
  postBusinessActivityInboxAction,
  getAutoCommit,
  getEventCatalog,
  getIntegrationContracts,
  getIntegrationRegistry,
  getQuarterLifecycleStatus,
  getQuarterSnapshotVersionStatus,
  recordReadinessSnapshot,
  reopenQuarter,
  setIntegrationRegistryEntry,
  setAutoCommit
};
