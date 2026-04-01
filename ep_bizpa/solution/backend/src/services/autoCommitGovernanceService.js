const { appendBusinessEvent } = require('./businessEventLogService');
const { isMonetaryItemType } = require('./monetaryIntegrityService');

class AutoCommitGovernanceError extends Error {
  constructor(message, statusCode = 409, details = {}) {
    super(message);
    this.name = 'AutoCommitGovernanceError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

const DURATION_ORDER = ['daily', 'weekly', 'monthly'];
const DEFAULT_MAX_DURATION = 'daily';
const DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.85;

const ensureExecutor = (executor) => {
  if (!executor || typeof executor.query !== 'function') {
    throw new Error('A database executor with query(text, params) is required.');
  }
  return executor;
};

const normalizeDuration = (value, fallback = DEFAULT_MAX_DURATION) => {
  const normalized = String(value || fallback).trim().toLowerCase();
  return DURATION_ORDER.includes(normalized) ? normalized : fallback;
};

const durationRank = (value) => DURATION_ORDER.indexOf(normalizeDuration(value));

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

const normalizeStateRow = (row, now = new Date()) => {
  const expiresAt = row?.expires_at ? new Date(row.expires_at).toISOString() : null;
  const expiryDate = expiresAt ? new Date(expiresAt) : null;

  return {
    user_id: row?.user_id || null,
    owner_policy_allows_auto_commit: Boolean(row?.owner_policy_allows_auto_commit),
    auto_commit_enabled: Boolean(row?.auto_commit_enabled),
    enabled_by: row?.enabled_by || null,
    duration: row?.duration ? normalizeDuration(row.duration) : null,
    max_allowed_duration: normalizeDuration(row?.max_allowed_duration, DEFAULT_MAX_DURATION),
    risk_acknowledged: Boolean(row?.risk_acknowledged),
    confirmation_reference: row?.confirmation_reference || null,
    threshold_override: Boolean(row?.threshold_override),
    threshold_override_limit: row?.threshold_override_limit === null || row?.threshold_override_limit === undefined
      ? null
      : Number(row.threshold_override_limit),
    max_auto_commit_amount: Number(row?.max_auto_commit_amount || 0),
    low_confidence_threshold: Number(row?.low_confidence_threshold || DEFAULT_LOW_CONFIDENCE_THRESHOLD),
    expires_at: expiresAt,
    is_expired: Boolean(expiryDate && expiryDate <= now),
    policy_metadata: normalizeMetadata(row?.policy_metadata),
    updated_at: row?.updated_at ? new Date(row.updated_at).toISOString() : null,
    updated_by: row?.updated_by || 'system'
  };
};

const calculateExpiry = (duration, now = new Date()) => {
  const expiry = new Date(now);
  switch (normalizeDuration(duration)) {
    case 'monthly':
      expiry.setUTCMonth(expiry.getUTCMonth() + 1);
      break;
    case 'weekly':
      expiry.setUTCDate(expiry.getUTCDate() + 7);
      break;
    case 'daily':
    default:
      expiry.setUTCDate(expiry.getUTCDate() + 1);
      break;
  }
  return expiry.toISOString();
};

const getAutoCommitState = async (executor, {
  userId,
  now = new Date(),
  processExpiry = true
}) => {
  const client = ensureExecutor(executor);
  const result = await client.query(
    `
    SELECT
      user_id,
      owner_policy_allows_auto_commit,
      auto_commit_enabled,
      enabled_by,
      duration,
      max_allowed_duration,
      risk_acknowledged,
      confirmation_reference,
      threshold_override,
      threshold_override_limit,
      max_auto_commit_amount,
      low_confidence_threshold,
      expires_at,
      policy_metadata,
      updated_at,
      updated_by
    FROM governance_settings
    WHERE user_id = $1
    LIMIT 1
    `,
    [userId]
  );

  const baseState = normalizeStateRow(result.rows[0], now);
  if (!processExpiry || !baseState.auto_commit_enabled || !baseState.is_expired) {
    return baseState;
  }

  await disableAutoCommit(executor, {
    user_id: userId,
    actor_id: 'system',
    source_type: 'system',
    reason: 'expired',
    metadata: {
      previous_duration: baseState.duration,
      expired_at: baseState.expires_at
    }
  });

  return {
    ...baseState,
    auto_commit_enabled: false,
    enabled_by: null,
    duration: null,
    risk_acknowledged: false,
    confirmation_reference: null,
    threshold_override: false,
    expires_at: null,
    is_expired: true
  };
};

const upsertGovernanceSettings = async (executor, params) => {
  const client = ensureExecutor(executor);
  const result = await client.query(
    `
    INSERT INTO governance_settings (
      user_id,
      owner_policy_allows_auto_commit,
      auto_commit_enabled,
      enabled_by,
      duration,
      max_allowed_duration,
      risk_acknowledged,
      confirmation_reference,
      threshold_override,
      threshold_override_limit,
      max_auto_commit_amount,
      low_confidence_threshold,
      expires_at,
      policy_metadata,
      updated_by
    )
    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14::jsonb,$15)
    ON CONFLICT (user_id)
    DO UPDATE SET
      owner_policy_allows_auto_commit = EXCLUDED.owner_policy_allows_auto_commit,
      auto_commit_enabled = EXCLUDED.auto_commit_enabled,
      enabled_by = EXCLUDED.enabled_by,
      duration = EXCLUDED.duration,
      max_allowed_duration = EXCLUDED.max_allowed_duration,
      risk_acknowledged = EXCLUDED.risk_acknowledged,
      confirmation_reference = EXCLUDED.confirmation_reference,
      threshold_override = EXCLUDED.threshold_override,
      threshold_override_limit = EXCLUDED.threshold_override_limit,
      max_auto_commit_amount = EXCLUDED.max_auto_commit_amount,
      low_confidence_threshold = EXCLUDED.low_confidence_threshold,
      expires_at = EXCLUDED.expires_at,
      policy_metadata = EXCLUDED.policy_metadata,
      updated_by = EXCLUDED.updated_by,
      updated_at = CURRENT_TIMESTAMP
    RETURNING
      user_id,
      owner_policy_allows_auto_commit,
      auto_commit_enabled,
      enabled_by,
      duration,
      max_allowed_duration,
      risk_acknowledged,
      confirmation_reference,
      threshold_override,
      threshold_override_limit,
      max_auto_commit_amount,
      low_confidence_threshold,
      expires_at,
      policy_metadata,
      updated_at,
      updated_by
    `,
    [
      params.user_id,
      params.owner_policy_allows_auto_commit,
      params.auto_commit_enabled,
      params.enabled_by,
      params.duration,
      params.max_allowed_duration,
      params.risk_acknowledged,
      params.confirmation_reference,
      params.threshold_override,
      params.threshold_override_limit,
      params.max_auto_commit_amount,
      params.low_confidence_threshold,
      params.expires_at,
      JSON.stringify(params.policy_metadata || {}),
      params.updated_by
    ]
  );

  return normalizeStateRow(result.rows[0]);
};

const disableAutoCommit = async (executor, {
  user_id,
  actor_id,
  source_type = 'manual',
  reason = 'manual_disable',
  metadata = {}
}) => {
  const client = ensureExecutor(executor);
  const state = await getAutoCommitState(client, { userId: user_id, processExpiry: false });
  const nextState = await upsertGovernanceSettings(client, {
    user_id,
    owner_policy_allows_auto_commit: state.owner_policy_allows_auto_commit,
    auto_commit_enabled: false,
    enabled_by: null,
    duration: null,
    max_allowed_duration: state.max_allowed_duration,
    risk_acknowledged: false,
    confirmation_reference: null,
    threshold_override: false,
    threshold_override_limit: state.threshold_override_limit,
    max_auto_commit_amount: state.max_auto_commit_amount,
    low_confidence_threshold: state.low_confidence_threshold,
    expires_at: null,
    policy_metadata: state.policy_metadata,
    updated_by: actor_id || 'system'
  });

  const eventType = reason === 'expired' ? 'auto_commit_expired' : 'auto_commit_disabled';
  const description = reason === 'expired' ? 'Auto-commit expired' : 'Auto-commit disabled';
  await appendBusinessEvent(client, {
    user_id,
    actor_id: actor_id || 'system',
    source_type,
    event_type: eventType,
    entity_type: 'governance',
    description,
    metadata: {
      reason,
      enabled: false,
      ...metadata
    }
  });

  return nextState;
};

const updateAutoCommitPolicy = async (executor, {
  user_id,
  actor_id,
  source_type = 'manual',
  owner_policy_allows_auto_commit,
  max_allowed_duration,
  max_auto_commit_amount,
  low_confidence_threshold = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
  threshold_override_limit = null,
  metadata = {}
}) => {
  const client = ensureExecutor(executor);
  const state = await getAutoCommitState(client, { userId: user_id, processExpiry: false });
  const nextPolicyAllowed = Boolean(owner_policy_allows_auto_commit);
  const nextMaxDuration = normalizeDuration(max_allowed_duration, state.max_allowed_duration);
  const nextAmountThreshold = Number(max_auto_commit_amount ?? state.max_auto_commit_amount ?? 0);
  const nextConfidenceThreshold = Number(low_confidence_threshold ?? state.low_confidence_threshold ?? DEFAULT_LOW_CONFIDENCE_THRESHOLD);
  const nextOverrideLimit = threshold_override_limit === null || threshold_override_limit === undefined
    ? state.threshold_override_limit
    : Number(threshold_override_limit);

  const shouldDisableActiveSession = state.auto_commit_enabled && (
    !nextPolicyAllowed ||
    durationRank(state.duration || DEFAULT_MAX_DURATION) > durationRank(nextMaxDuration)
  );

  const nextState = await upsertGovernanceSettings(client, {
    user_id,
    owner_policy_allows_auto_commit: nextPolicyAllowed,
    auto_commit_enabled: shouldDisableActiveSession ? false : state.auto_commit_enabled,
    enabled_by: shouldDisableActiveSession ? null : state.enabled_by,
    duration: shouldDisableActiveSession ? null : state.duration,
    max_allowed_duration: nextMaxDuration,
    risk_acknowledged: shouldDisableActiveSession ? false : state.risk_acknowledged,
    confirmation_reference: shouldDisableActiveSession ? null : state.confirmation_reference,
    threshold_override: shouldDisableActiveSession ? false : state.threshold_override,
    threshold_override_limit: nextOverrideLimit,
    max_auto_commit_amount: nextAmountThreshold,
    low_confidence_threshold: nextConfidenceThreshold,
    expires_at: shouldDisableActiveSession ? null : state.expires_at,
    policy_metadata: {
      ...state.policy_metadata,
      ...metadata
    },
    updated_by: actor_id || 'system'
  });

  await appendBusinessEvent(client, {
    user_id,
    actor_id: actor_id || 'system',
    source_type,
    event_type: 'governance_policy_changed',
    entity_type: 'governance',
    description: 'Governance policy changed',
    metadata: {
      owner_policy_allows_auto_commit: nextPolicyAllowed,
      max_allowed_duration: nextMaxDuration,
      max_auto_commit_amount: nextAmountThreshold,
      low_confidence_threshold: nextConfidenceThreshold,
      threshold_override_limit: nextOverrideLimit,
      auto_commit_session_disabled: shouldDisableActiveSession,
      ...metadata
    }
  });

  if (shouldDisableActiveSession) {
    await appendBusinessEvent(client, {
      user_id,
      actor_id: actor_id || 'system',
      source_type,
      event_type: 'auto_commit_disabled',
      entity_type: 'governance',
      description: 'Auto-commit disabled',
      metadata: {
        reason: 'policy_restricted',
        max_allowed_duration: nextMaxDuration
      }
    });
  }

  return nextState;
};

const enableAutoCommit = async (executor, {
  user_id,
  actor_id,
  source_type = 'manual',
  duration,
  risk_acknowledged,
  confirmation_reference,
  threshold_override = false,
  metadata = {},
  now = new Date()
}) => {
  const client = ensureExecutor(executor);
  const state = await getAutoCommitState(client, { userId: user_id, processExpiry: true, now });
  const requestedDuration = normalizeDuration(duration, state.max_allowed_duration);

  if (!state.owner_policy_allows_auto_commit) {
    throw new AutoCommitGovernanceError('Auto-commit cannot be enabled because owner policy disallows it.', 409, {
      policy_allows_auto_commit: false
    });
  }

  if (durationRank(requestedDuration) > durationRank(state.max_allowed_duration)) {
    throw new AutoCommitGovernanceError('Requested auto-commit duration exceeds the owner policy cap.', 409, {
      requested_duration: requestedDuration,
      max_allowed_duration: state.max_allowed_duration
    });
  }

  if (!risk_acknowledged) {
    throw new AutoCommitGovernanceError('risk_acknowledged must be true to enable auto-commit.', 400, {
      field: 'risk_acknowledged'
    });
  }

  if (!confirmation_reference || !String(confirmation_reference).trim()) {
    throw new AutoCommitGovernanceError('confirmation_reference is required to enable auto-commit.', 400, {
      field: 'confirmation_reference'
    });
  }

  const expiresAt = calculateExpiry(requestedDuration, now);
  const nextState = await upsertGovernanceSettings(client, {
    user_id,
    owner_policy_allows_auto_commit: state.owner_policy_allows_auto_commit,
    auto_commit_enabled: true,
    enabled_by: actor_id || user_id,
    duration: requestedDuration,
    max_allowed_duration: state.max_allowed_duration,
    risk_acknowledged: Boolean(risk_acknowledged),
    confirmation_reference: String(confirmation_reference).trim(),
    threshold_override: Boolean(threshold_override),
    threshold_override_limit: state.threshold_override_limit,
    max_auto_commit_amount: state.max_auto_commit_amount,
    low_confidence_threshold: state.low_confidence_threshold,
    expires_at: expiresAt,
    policy_metadata: state.policy_metadata,
    updated_by: actor_id || 'system'
  });

  await appendBusinessEvent(client, {
    user_id,
    actor_id: actor_id || user_id,
    source_type,
    event_type: 'auto_commit_enabled',
    entity_type: 'governance',
    description: 'Auto-commit enabled',
    metadata: {
      enabled: true,
      enabled_by: actor_id || user_id,
      duration: requestedDuration,
      risk_acknowledged: Boolean(risk_acknowledged),
      confirmation_reference: String(confirmation_reference).trim(),
      threshold_override: Boolean(threshold_override),
      expires_at: expiresAt,
      ...metadata
    }
  });

  return nextState;
};

const evaluateAutoCommitEligibility = async (executor, {
  user_id,
  entity_type,
  amount,
  confidence_score,
  now = new Date()
}) => {
  const state = await getAutoCommitState(executor, { userId: user_id, now, processExpiry: true });
  const numericAmount = Number(amount || 0);
  const numericConfidence = confidence_score === null || confidence_score === undefined
    ? null
    : Number(confidence_score);
  const reasons = [];

  if (!isMonetaryItemType(entity_type)) {
    reasons.push('non_monetary_entity');
  }
  if (!state.owner_policy_allows_auto_commit) {
    reasons.push('owner_policy_disallows');
  }
  if (!state.auto_commit_enabled) {
    reasons.push('user_opt_in_missing');
  }
  if (state.is_expired) {
    reasons.push('auto_commit_expired');
  }
  if (numericConfidence === null || Number.isNaN(numericConfidence) || numericConfidence < state.low_confidence_threshold) {
    reasons.push('low_confidence');
  }

  const thresholdLimit = state.threshold_override
    ? (state.threshold_override_limit ?? state.max_auto_commit_amount)
    : state.max_auto_commit_amount;
  const thresholdApplied = Number(thresholdLimit || 0);
  if (numericAmount > thresholdApplied) {
    reasons.push(state.threshold_override ? 'threshold_override_exceeded' : 'over_threshold');
  }

  return {
    eligible: reasons.length === 0,
    commit_mode: reasons.length === 0 ? 'auto' : 'manual',
    action_status: reasons.length === 0 ? 'committed' : 'preview_required',
    reasons,
    threshold_applied: thresholdApplied,
    confidence_threshold: state.low_confidence_threshold,
    state
  };
};

module.exports = {
  AutoCommitGovernanceError,
  DEFAULT_LOW_CONFIDENCE_THRESHOLD,
  DURATION_ORDER,
  calculateExpiry,
  disableAutoCommit,
  enableAutoCommit,
  evaluateAutoCommitEligibility,
  getAutoCommitState,
  normalizeDuration,
  updateAutoCommitPolicy
};
