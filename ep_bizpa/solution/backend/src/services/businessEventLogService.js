const { randomUUID } = require('crypto');
const {
  canonicalSchemas,
  deriveQuarterReference,
  validateEventPayload
} = require('./canonicalSchemaService');

const EVENT_TYPE_CATALOG = canonicalSchemas.event_schema.allowed_event_types.slice();

const DEFAULT_SOURCE_TYPE = 'system';
const DEFAULT_ACTOR_ID = 'system';

const ITEM_ENTITY_TYPE_ALIASES = {
  receipt: 'receipt_expense',
  image: 'attachment'
};

const ensureExecutor = (executor) => {
  if (!executor || typeof executor.query !== 'function') {
    throw new Error('A database executor with query(text, params) is required.');
  }
  return executor;
};

const mapItemEntityType = (itemType) => ITEM_ENTITY_TYPE_ALIASES[itemType] || itemType || 'record';

const normalizeActorId = (actorId) => String(actorId || DEFAULT_ACTOR_ID);

const normalizeSourceType = (sourceType) => sourceType || DEFAULT_SOURCE_TYPE;

const buildTimestamp = (input) => (input ? new Date(input).toISOString() : new Date().toISOString());

const appendBusinessEvent = async (executor, payload) => {
  const client = ensureExecutor(executor);
  const eventId = payload.event_id || randomUUID();
  const actorId = normalizeActorId(payload.actor_id || payload.created_by);
  const createdAt = buildTimestamp(payload.timestamp || payload.created_at);
  const sourceType = normalizeSourceType(payload.source_type);
  const metadata = payload.metadata || {};

  const eventRecord = {
    event_id: eventId,
    user_id: payload.user_id,
    event_type: payload.event_type,
    entity_id: payload.entity_id || payload.linked_entity_id || null,
    entity_type: payload.entity_type || payload.linked_entity_type || null,
    created_at: createdAt,
    actor_id: actorId,
    source_type: sourceType,
    description: payload.description,
    metadata,
    quarter_reference: payload.quarter_reference || null,
    status_from: payload.status_from || null,
    status_to: payload.status_to || null
  };

  const validation = validateEventPayload({
    unique_id: eventId,
    event_type: eventRecord.event_type,
    created_at: eventRecord.created_at,
    created_by: actorId,
    source_type: sourceType,
    description: eventRecord.description,
    linked_entity_id: eventRecord.entity_id,
    linked_entity_type: eventRecord.entity_type,
    quarter_reference: eventRecord.quarter_reference,
    status_from: eventRecord.status_from,
    status_to: eventRecord.status_to,
    metadata
  });

  if (!validation.valid) {
    throw new Error(`Invalid business event payload: ${validation.errors.join('; ')}`);
  }

  await client.query(
    `
    INSERT INTO business_event_log (
      event_id, user_id, event_type, entity_id, entity_type, created_at,
      actor_id, source_type, description, metadata, quarter_reference, status_from, status_to
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11,$12,$13)
    `,
    [
      eventRecord.event_id,
      eventRecord.user_id,
      eventRecord.event_type,
      eventRecord.entity_id,
      eventRecord.entity_type,
      eventRecord.created_at,
      eventRecord.actor_id,
      eventRecord.source_type,
      eventRecord.description,
      JSON.stringify(eventRecord.metadata),
      eventRecord.quarter_reference,
      eventRecord.status_from,
      eventRecord.status_to
    ]
  );

  return eventRecord;
};

const listBusinessEvents = async (executor, filters = {}) => {
  const client = ensureExecutor(executor);
  const limit = Math.max(1, Math.min(500, Number(filters.limit || 100)));
  const offset = Math.max(0, Number(filters.offset || 0));
  const params = [filters.user_id];
  const clauses = ['user_id = $1'];
  let index = 2;

  if (filters.entity_id) {
    clauses.push(`entity_id = $${index++}`);
    params.push(filters.entity_id);
  }
  if (filters.entity_type) {
    clauses.push(`entity_type = $${index++}`);
    params.push(filters.entity_type);
  }
  if (filters.event_type) {
    clauses.push(`event_type = $${index++}`);
    params.push(filters.event_type);
  }
  if (filters.quarter_reference) {
    clauses.push(`quarter_reference = $${index++}`);
    params.push(filters.quarter_reference);
  }

  params.push(limit, offset);
  const limitIndex = index++;
  const offsetIndex = index++;

  const result = await client.query(
    `
    SELECT
      event_id,
      event_type,
      entity_id,
      entity_type,
      created_at AS timestamp,
      actor_id,
      description,
      metadata,
      quarter_reference,
      status_from,
      status_to
    FROM business_event_log
    WHERE ${clauses.join(' AND ')}
    ORDER BY created_at DESC, event_id DESC
    LIMIT $${limitIndex} OFFSET $${offsetIndex}
    `,
    params
  );

  return result.rows;
};

const recordEntityCreated = async (executor, {
  user_id,
  actor_id,
  source_type,
  entity_id,
  entity_type,
  quarter_reference = null,
  description,
  metadata = {},
  status_to = null
}) => appendBusinessEvent(executor, {
  user_id,
  actor_id,
  source_type,
  event_type: 'entity_created',
  entity_id,
  entity_type,
  quarter_reference,
  description,
  metadata,
  status_to
});

const recordStatusChange = async (executor, {
  user_id,
  actor_id,
  source_type,
  entity_id,
  entity_type,
  quarter_reference = null,
  status_from,
  status_to,
  description,
  metadata = {}
}) => appendBusinessEvent(executor, {
  user_id,
  actor_id,
  source_type,
  event_type: 'entity_status_changed',
  entity_id,
  entity_type,
  quarter_reference,
  status_from,
  status_to,
  description,
  metadata
});

const recordEntityUpdated = async (executor, {
  user_id,
  actor_id,
  source_type,
  entity_id,
  entity_type,
  quarter_reference = null,
  description,
  metadata = {}
}) => appendBusinessEvent(executor, {
  user_id,
  actor_id,
  source_type,
  event_type: 'entity_updated',
  entity_id,
  entity_type,
  quarter_reference,
  description,
  metadata
});

const recordPaymentRecorded = async (executor, {
  user_id,
  actor_id,
  source_type,
  entity_id,
  entity_type = 'invoice',
  quarter_reference = null,
  status_from = null,
  status_to = 'paid',
  description,
  metadata = {}
}) => appendBusinessEvent(executor, {
  user_id,
  actor_id,
  source_type,
  event_type: 'payment_recorded',
  entity_id,
  entity_type,
  quarter_reference,
  status_from,
  status_to,
  description,
  metadata
});

const recordEntityCommitted = async (executor, {
  user_id,
  actor_id,
  source_type,
  entity_id,
  entity_type,
  quarter_reference = null,
  status_from = 'draft',
  status_to = 'confirmed',
  description,
  metadata = {}
}) => appendBusinessEvent(executor, {
  user_id,
  actor_id,
  source_type,
  event_type: 'entity_committed',
  entity_id,
  entity_type,
  quarter_reference,
  status_from,
  status_to,
  description,
  metadata
});

const recordCorrectionEvent = async (executor, {
  user_id,
  actor_id,
  source_type,
  entity_id,
  entity_type,
  quarter_reference = null,
  action,
  status_from = null,
  status_to = null,
  description,
  metadata = {}
}) => {
  const eventType = action === 'void' ? 'entity_voided' : 'entity_superseded';
  return appendBusinessEvent(executor, {
    user_id,
    actor_id,
    source_type,
    event_type: eventType,
    entity_id,
    entity_type,
    quarter_reference,
    status_from,
    status_to,
    description,
    metadata
  });
};

const recordQuoteConverted = async (executor, {
  user_id,
  actor_id,
  source_type,
  quote_id,
  invoice_id,
  quarter_reference = null,
  metadata = {}
}) => appendBusinessEvent(executor, {
  user_id,
  actor_id,
  source_type,
  event_type: 'quote_converted',
  entity_id: quote_id,
  entity_type: 'quote',
  quarter_reference,
  status_from: 'confirmed',
  status_to: 'converted',
  description: `Quote ${quote_id} converted to invoice ${invoice_id}`,
  metadata: {
    invoice_id,
    ...metadata
  }
});

const recordSnapshotCreated = async (executor, {
  user_id,
  actor_id,
  source_type,
  quarter_reference,
  snapshot_id = randomUUID(),
  created_at = null,
  description,
  metadata = {}
}) => appendBusinessEvent(executor, {
  user_id,
  actor_id,
  source_type,
  event_type: 'snapshot_created',
  entity_id: snapshot_id,
  entity_type: 'snapshot',
  created_at,
  quarter_reference,
  status_to: 'generated',
  description,
  metadata
});

const quarterBoundsFromReference = (quarterReference) => {
  const match = /^Q([1-4])-(\d{4})$/.exec(quarterReference || '');
  if (!match) {
    throw new Error(`Invalid quarter reference "${quarterReference}"`);
  }
  const quarter = Number(match[1]);
  const year = Number(match[2]);
  const monthStart = (quarter - 1) * 3;
  const periodStart = new Date(Date.UTC(year, monthStart, 1));
  const periodEnd = new Date(Date.UTC(year, monthStart + 3, 0));
  return {
    periodStart: periodStart.toISOString().slice(0, 10),
    periodEnd: periodEnd.toISOString().slice(0, 10)
  };
};

const upsertQuarterStatus = async (executor, {
  user_id,
  actor_id,
  source_type,
  quarter_reference,
  next_status,
  event_type,
  reason = null,
  metadata = {}
}) => {
  const client = ensureExecutor(executor);
  const { periodStart, periodEnd } = quarterBoundsFromReference(quarter_reference);

  const quarterResult = await client.query(
    `
    INSERT INTO quarters (user_id, period_start, period_end, status)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (user_id, period_start, period_end)
    DO UPDATE SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
    RETURNING id, status
    `,
    [user_id, periodStart, periodEnd, next_status]
  );

  await appendBusinessEvent(client, {
    user_id,
    actor_id,
    source_type,
    event_type,
    entity_id: quarterResult.rows[0].id,
    entity_type: 'quarter',
    quarter_reference,
    status_to: next_status,
    description: `${quarter_reference} marked ${next_status}`,
    metadata: {
      reason,
      period_start: periodStart,
      period_end: periodEnd,
      ...metadata
    }
  });

  return quarterResult.rows[0];
};

const setAutoCommitPreference = async (executor, {
  user_id,
  actor_id,
  source_type,
  enabled,
  metadata = {}
}) => {
  const client = ensureExecutor(executor);
  await client.query(
    `
    INSERT INTO governance_settings (user_id, auto_commit_enabled, updated_by)
    VALUES ($1, $2, $3)
    ON CONFLICT (user_id)
    DO UPDATE SET
      auto_commit_enabled = EXCLUDED.auto_commit_enabled,
      updated_by = EXCLUDED.updated_by,
      updated_at = CURRENT_TIMESTAMP
    `,
    [user_id, enabled, normalizeActorId(actor_id)]
  );

  return appendBusinessEvent(client, {
    user_id,
    actor_id,
    source_type,
    event_type: enabled ? 'auto_commit_enabled' : 'auto_commit_disabled',
    entity_type: 'governance',
    description: `Auto-commit ${enabled ? 'enabled' : 'disabled'}`,
    metadata: {
      enabled,
      ...metadata
    }
  });
};

const recordReadinessRecalculated = async (executor, {
  user_id,
  actor_id,
  source_type,
  quarter_reference = null,
  entity_id = null,
  entity_type = 'readiness',
  description,
  metadata
}) => appendBusinessEvent(executor, {
  user_id,
  actor_id,
  source_type,
  event_type: 'readiness_recalculated',
  entity_id,
  entity_type,
  quarter_reference,
  description,
  metadata
});

const buildItemCreatedEvent = (item, actorId, sourceType = 'manual') => ({
  user_id: item.user_id,
  actor_id: actorId || item.user_id,
  source_type: sourceType,
  entity_id: item.id,
  entity_type: mapItemEntityType(item.type),
  quarter_reference: item.quarter_ref || null,
  description: `${mapItemEntityType(item.type)} created`,
  metadata: {
    item_type: item.type,
    amount: item.amount,
    gross_amount: item.gross_amount,
    currency: item.currency,
    client_id: item.client_id,
    job_id: item.job_id
  },
  status_to: item.status || null
});

const buildClientCreatedEvent = (clientRecord, actorId) => ({
  user_id: clientRecord.user_id,
  actor_id: actorId || clientRecord.user_id,
  source_type: 'manual',
  entity_id: clientRecord.id,
  entity_type: 'client',
  description: `Client ${clientRecord.name} created`,
  metadata: {
    client_name: clientRecord.name
  },
  status_to: 'active'
});

const deriveQuarterFromDate = (value) => {
  if (!value) {
    return null;
  }
  try {
    return deriveQuarterReference(value);
  } catch (err) {
    return null;
  }
};

module.exports = {
  EVENT_TYPE_CATALOG,
  appendBusinessEvent,
  buildClientCreatedEvent,
  buildItemCreatedEvent,
  deriveQuarterFromDate,
  listBusinessEvents,
  mapItemEntityType,
  quarterBoundsFromReference,
  recordCorrectionEvent,
  recordEntityCommitted,
  recordEntityCreated,
  recordEntityUpdated,
  recordPaymentRecorded,
  recordQuoteConverted,
  recordReadinessRecalculated,
  recordSnapshotCreated,
  recordStatusChange,
  setAutoCommitPreference,
  upsertQuarterStatus
};
