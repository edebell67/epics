const { appendBusinessEvent, quarterBoundsFromReference } = require('./businessEventLogService');

class QuarterGovernanceError extends Error {
  constructor(message, statusCode = 409, details = {}) {
    super(message);
    this.name = 'QuarterGovernanceError';
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

const buildQuarterLookup = (quarterReference) => {
  const { periodStart, periodEnd } = quarterBoundsFromReference(quarterReference);
  return {
    quarter_label: quarterReference,
    period_start: periodStart,
    period_end: periodEnd
  };
};

const mapQuarterRow = (row, fallbackQuarterReference) => {
  if (!row) {
    return null;
  }

  const metadata = normalizeMetadata(row.governance_metadata);
  const quarterState = row.quarter_state || row.status || 'open';
  return {
    id: row.id,
    quarter_label: row.quarter_label || fallbackQuarterReference,
    quarter_state: quarterState,
    status: row.status || quarterState,
    closed_at: row.closed_at || null,
    reopened_at: row.reopened_at || null,
    reopen_reason: row.reopen_reason || null,
    confirmation_reference: row.confirmation_reference || null,
    governance_metadata: metadata,
    period_start: row.period_start || null,
    period_end: row.period_end || null
  };
};

const getQuarterLifecycle = async (executor, { userId, quarterReference }) => {
  const client = ensureExecutor(executor);
  const lookup = buildQuarterLookup(quarterReference);
  const result = await client.query(
    `
    SELECT
      id,
      period_start,
      period_end,
      status,
      quarter_label,
      quarter_state,
      closed_at,
      reopened_at,
      reopen_reason,
      confirmation_reference,
      governance_metadata
    FROM quarters
    WHERE user_id = $1
      AND period_start = $2
      AND period_end = $3
    LIMIT 1
    `,
    [userId, lookup.period_start, lookup.period_end]
  );

  if (!result.rows.length) {
    return {
      id: null,
      quarter_label: quarterReference,
      quarter_state: 'open',
      status: 'open',
      closed_at: null,
      reopened_at: null,
      reopen_reason: null,
      confirmation_reference: null,
      governance_metadata: {},
      period_start: lookup.period_start,
      period_end: lookup.period_end
    };
  }

  return mapQuarterRow(result.rows[0], quarterReference);
};

const assertQuarterAllowsMonetaryActivity = async (executor, {
  userId,
  quarterReference,
  operation,
  entityId = null,
  entityType = null
}) => {
  const lifecycle = await getQuarterLifecycle(executor, { userId, quarterReference });
  if (lifecycle.quarter_state !== 'closed') {
    return lifecycle;
  }

  throw new QuarterGovernanceError(
    `Quarter ${quarterReference} is closed. ${operation} is blocked until the quarter is reopened.`,
    409,
    {
      quarter_reference: quarterReference,
      quarter_state: lifecycle.quarter_state,
      operation,
      entity_id: entityId,
      entity_type: entityType,
      closed_at: lifecycle.closed_at,
      confirmation_reference: lifecycle.confirmation_reference
    }
  );
};

const upsertQuarterLifecycleRow = async (executor, {
  userId,
  quarterReference,
  quarterState,
  closedAt,
  reopenedAt,
  reopenReason,
  confirmationReference,
  governanceMetadata = {}
}) => {
  const client = ensureExecutor(executor);
  const lookup = buildQuarterLookup(quarterReference);
  const result = await client.query(
    `
    INSERT INTO quarters (
      user_id,
      period_start,
      period_end,
      status,
      exported_at,
      quarter_label,
      quarter_state,
      closed_at,
      reopened_at,
      reopen_reason,
      confirmation_reference,
      governance_metadata
    )
    VALUES ($1, $2, $3, $4, NULL, $5, $6, $7, $8, $9, $10, $11::jsonb)
    ON CONFLICT (user_id, period_start, period_end)
    DO UPDATE SET
      status = EXCLUDED.status,
      quarter_label = EXCLUDED.quarter_label,
      quarter_state = EXCLUDED.quarter_state,
      closed_at = EXCLUDED.closed_at,
      reopened_at = EXCLUDED.reopened_at,
      reopen_reason = EXCLUDED.reopen_reason,
      confirmation_reference = EXCLUDED.confirmation_reference,
      governance_metadata = EXCLUDED.governance_metadata,
      updated_at = CURRENT_TIMESTAMP
    RETURNING
      id,
      period_start,
      period_end,
      status,
      quarter_label,
      quarter_state,
      closed_at,
      reopened_at,
      reopen_reason,
      confirmation_reference,
      governance_metadata
    `,
    [
      userId,
      lookup.period_start,
      lookup.period_end,
      quarterState,
      quarterReference,
      quarterState,
      closedAt,
      reopenedAt,
      reopenReason,
      confirmationReference,
      JSON.stringify(governanceMetadata)
    ]
  );

  return mapQuarterRow(result.rows[0], quarterReference);
};

const closeQuarterLifecycle = async (executor, {
  user_id,
  actor_id,
  source_type = 'manual',
  quarter_reference,
  reason = null,
  metadata = {}
}) => {
  const existing = await getQuarterLifecycle(executor, {
    userId: user_id,
    quarterReference: quarter_reference
  });

  if (existing.quarter_state === 'closed') {
    throw new QuarterGovernanceError(`Quarter ${quarter_reference} is already closed.`, 409, existing);
  }

  const closedAt = new Date().toISOString();
  const quarter = await upsertQuarterLifecycleRow(executor, {
    userId: user_id,
    quarterReference: quarter_reference,
    quarterState: 'closed',
    closedAt,
    reopenedAt: existing.reopened_at,
    reopenReason: existing.reopen_reason,
    confirmationReference: existing.confirmation_reference,
    governanceMetadata: {
      ...existing.governance_metadata,
      close_reason: reason || null,
      close_metadata: metadata || {}
    }
  });

  await appendBusinessEvent(executor, {
    user_id,
    actor_id,
    source_type,
    event_type: 'quarter_closed',
    entity_id: quarter.id,
    entity_type: 'quarter',
    quarter_reference,
    status_from: existing.quarter_state,
    status_to: 'closed',
    description: `${quarter_reference} manually closed`,
    metadata: {
      quarter_label: quarter_reference,
      quarter_state: 'closed',
      closed_at: closedAt,
      reason: reason || null,
      confirmation_reference: quarter.confirmation_reference,
      ...metadata
    }
  });

  return quarter;
};

const reopenQuarterLifecycle = async (executor, {
  user_id,
  actor_id,
  source_type = 'manual',
  quarter_reference,
  reason,
  confirmation_reference,
  metadata = {}
}) => {
  if (!reason || !String(reason).trim()) {
    throw new QuarterGovernanceError('Reopen reason is required.', 400, {
      quarter_reference,
      field: 'reason'
    });
  }

  if (!confirmation_reference || !String(confirmation_reference).trim()) {
    throw new QuarterGovernanceError('confirmation_reference is required to reopen a quarter.', 400, {
      quarter_reference,
      field: 'confirmation_reference'
    });
  }

  const existing = await getQuarterLifecycle(executor, {
    userId: user_id,
    quarterReference: quarter_reference
  });

  if (existing.quarter_state !== 'closed') {
    throw new QuarterGovernanceError(
      `Quarter ${quarter_reference} must be closed before it can be reopened.`,
      409,
      existing
    );
  }

  const reopenedAt = new Date().toISOString();
  const quarter = await upsertQuarterLifecycleRow(executor, {
    userId: user_id,
    quarterReference: quarter_reference,
    quarterState: 'open',
    closedAt: existing.closed_at,
    reopenedAt,
    reopenReason: String(reason).trim(),
    confirmationReference: String(confirmation_reference).trim(),
    governanceMetadata: {
      ...existing.governance_metadata,
      reopen_reason: String(reason).trim(),
      reopen_metadata: metadata || {}
    }
  });

  await appendBusinessEvent(executor, {
    user_id,
    actor_id,
    source_type,
    event_type: 'quarter_reopened',
    entity_id: quarter.id,
    entity_type: 'quarter',
    quarter_reference,
    status_from: 'closed',
    status_to: 'open',
    description: `${quarter_reference} reopened`,
    metadata: {
      quarter_label: quarter_reference,
      quarter_state: 'open',
      closed_at: quarter.closed_at,
      reopened_at: reopenedAt,
      reopen_reason: String(reason).trim(),
      confirmation_reference: String(confirmation_reference).trim(),
      ...metadata
    }
  });

  return quarter;
};

module.exports = {
  QuarterGovernanceError,
  assertQuarterAllowsMonetaryActivity,
  closeQuarterLifecycle,
  getQuarterLifecycle,
  reopenQuarterLifecycle
};
