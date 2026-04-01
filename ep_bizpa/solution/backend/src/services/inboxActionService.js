const {
  buildClientCreatedEvent,
  mapItemEntityType,
  recordEntityCreated,
  recordEntityUpdated,
  recordPaymentRecorded
} = require('./businessEventLogService');
const { convertQuoteToInvoiceInternal } = require('../controllers/itemController');

const SUPPORTED_ACTIONS = new Set([
  'mark_paid',
  'update_due_date',
  'add_missing_category',
  'add_missing_counterparty',
  'convert_quote_to_invoice'
]);

class InboxActionError extends Error {
  constructor(message, statusCode = 400, details = null) {
    super(message);
    this.name = 'InboxActionError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj || {}, key);
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const ensureExecutor = async (executor) => {
  if (executor?.pool?.connect) {
    const client = await executor.pool.connect();
    return { client, managesTransaction: true };
  }
  if (executor && typeof executor.query === 'function') {
    return { client: executor, managesTransaction: false };
  }
  throw new Error('A database executor with query(text, params) is required.');
};

const ensureSingleEntityPayload = (payload = {}) => {
  if (Array.isArray(payload.entity_id) || Array.isArray(payload.entity_ids) || Array.isArray(payload.actions)) {
    throw new InboxActionError('Inbox actions support one entity at a time. Bulk edits are not supported.', 409);
  }
  if (hasOwn(payload, 'amount') || hasOwn(payload, 'gross_amount') || hasOwn(payload, 'net_amount') || hasOwn(payload, 'vat_amount')) {
    throw new InboxActionError('Inbox actions cannot rewrite committed monetary values.', 409);
  }
};

const validateActionType = (actionType) => {
  const normalized = String(actionType || '').trim().toLowerCase();
  if (!SUPPORTED_ACTIONS.has(normalized)) {
    throw new InboxActionError(`Unsupported inbox action "${actionType}".`, 400, {
      supported_actions: Array.from(SUPPORTED_ACTIONS)
    });
  }
  return normalized;
};

const loadItem = async (client, userId, entityId) => {
  const result = await client.query(
    `
    SELECT ci.*, c.name AS client_name
    FROM capture_items ci
    LEFT JOIN clients c ON c.id = ci.client_id
    WHERE ci.id = $1 AND ci.user_id = $2 AND ci.deleted_at IS NULL
    `,
    [entityId, userId]
  );
  if (result.rows.length === 0) {
    throw new InboxActionError('Target entity not found or access denied.', 404);
  }
  return result.rows[0];
};

const loadLabels = async (client, entityId) => {
  const result = await client.query(
    'SELECT label_name FROM capture_item_labels WHERE item_id = $1 ORDER BY label_name ASC',
    [entityId]
  );
  return result.rows.map((row) => row.label_name);
};

const writeAuditEvent = async (client, payload) => {
  await client.query(
    `INSERT INTO audit_events (action_type, entity_name, entity_id, user_id, device_id, diff_log)
     VALUES ($1, $2, $3, $4, $5, $6)`,
    [
      payload.action_type,
      payload.entity_name,
      payload.entity_id,
      payload.user_id,
      payload.device_id,
      JSON.stringify(payload.diff_log)
    ]
  );
};

const normalizeDateInput = (value) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new InboxActionError('new_due_date must be a valid date.', 400);
  }
  return parsed.toISOString().slice(0, 10);
};

const normalizeCategory = (value) => {
  const category = String(value || '').trim();
  if (!category) {
    throw new InboxActionError('category is required for add_missing_category.', 400);
  }
  return category;
};

const resolveCounterparty = async (client, userId, counterpartyReference) => {
  const normalized = String(counterpartyReference || '').trim();
  if (!normalized) {
    throw new InboxActionError('counterparty_reference is required for add_missing_counterparty.', 400);
  }

  if (UUID_PATTERN.test(normalized)) {
    const existingById = await client.query(
      'SELECT id, name FROM clients WHERE id = $1 AND user_id = $2',
      [normalized, userId]
    );
    if (existingById.rows.length === 0) {
      throw new InboxActionError('Referenced counterparty was not found.', 404);
    }
    return { clientId: existingById.rows[0].id, clientName: existingById.rows[0].name, created: false };
  }

  const existingByName = await client.query(
    'SELECT id, name FROM clients WHERE name ILIKE $1 AND user_id = $2',
    [normalized, userId]
  );
  if (existingByName.rows.length > 0) {
    return { clientId: existingByName.rows[0].id, clientName: existingByName.rows[0].name, created: false };
  }

  const created = await client.query(
    'INSERT INTO clients (name, user_id) VALUES ($1, $2) RETURNING id, name',
    [normalized, userId]
  );

  await recordEntityCreated(client, buildClientCreatedEvent({
    id: created.rows[0].id,
    user_id: userId,
    name: created.rows[0].name
  }, userId));

  return { clientId: created.rows[0].id, clientName: created.rows[0].name, created: true };
};

const buildActionResponse = ({
  actionType,
  item,
  metadata = {},
  eventType,
  statusCode = 200,
  linkedEntityType = null
}) => ({
  statusCode,
  action_type: actionType,
  entity_id: item?.id || null,
  entity_type: linkedEntityType || mapItemEntityType(item?.type),
  event_type: eventType,
  metadata
});

const applyMarkPaid = async (client, item, context) => {
  if (item.type !== 'invoice') {
    throw new InboxActionError('mark_paid is only supported for invoices.', 409);
  }
  if ((item.payment_status || 'draft') === 'paid') {
    throw new InboxActionError('Invoice is already marked paid.', 409);
  }

  await client.query(
    `
    UPDATE capture_items
    SET payment_status = 'paid', updated_at = CURRENT_TIMESTAMP
    WHERE id = $1 AND user_id = $2
    `,
    [item.id, context.userId]
  );

  await writeAuditEvent(client, {
    action_type: 'inbox_mark_paid',
    entity_name: 'capture_items',
    entity_id: item.id,
    user_id: context.userId,
    device_id: item.device_id || 'system',
    diff_log: {
      payment_status: {
        from: item.payment_status || 'draft',
        to: 'paid'
      },
      inbox_action: 'mark_paid'
    }
  });

  await recordPaymentRecorded(client, {
    user_id: context.userId,
    actor_id: context.actorId,
    source_type: context.sourceType,
    entity_id: item.id,
    entity_type: 'invoice',
    quarter_reference: item.quarter_ref || null,
    status_from: item.payment_status || 'draft',
    status_to: 'paid',
    description: `Invoice ${item.reference_number || item.id} marked paid from inbox`,
    metadata: {
      action_type: 'mark_paid',
      previous_payment_status: item.payment_status || 'draft',
      new_payment_status: 'paid',
      counterparty: item.client_name || null
    }
  });

  return buildActionResponse({
    actionType: 'mark_paid',
    item,
    eventType: 'payment_recorded',
    metadata: {
      new_status: 'paid'
    }
  });
};

const applyDueDateUpdate = async (client, item, payload, context) => {
  if (!new Set(['invoice', 'quote']).has(item.type)) {
    throw new InboxActionError('update_due_date is only supported for invoices and quotes.', 409);
  }

  const nextDueDate = normalizeDateInput(payload.new_due_date);
  if (item.due_date && String(item.due_date).slice(0, 10) === nextDueDate) {
    throw new InboxActionError('Due date is already set to that value.', 409);
  }

  await client.query(
    `
    UPDATE capture_items
    SET due_date = $3, updated_at = CURRENT_TIMESTAMP
    WHERE id = $1 AND user_id = $2
    `,
    [item.id, context.userId, nextDueDate]
  );

  await writeAuditEvent(client, {
    action_type: 'inbox_update_due_date',
    entity_name: 'capture_items',
    entity_id: item.id,
    user_id: context.userId,
    device_id: item.device_id || 'system',
    diff_log: {
      due_date: {
        from: item.due_date || null,
        to: nextDueDate
      },
      inbox_action: 'update_due_date'
    }
  });

  await recordEntityUpdated(client, {
    user_id: context.userId,
    actor_id: context.actorId,
    source_type: context.sourceType,
    entity_id: item.id,
    entity_type: mapItemEntityType(item.type),
    quarter_reference: item.quarter_ref || null,
    description: `${item.type} ${item.reference_number || item.id} due date updated from inbox`,
    metadata: {
      action_type: 'update_due_date',
      updated_field: 'due_date',
      previous_value: item.due_date || null,
      new_value: nextDueDate
    }
  });

  return buildActionResponse({
    actionType: 'update_due_date',
    item,
    eventType: 'entity_updated',
    metadata: {
      new_due_date: nextDueDate
    }
  });
};

const applyCategoryUpdate = async (client, item, payload, context) => {
  const nextCategory = normalizeCategory(payload.category);
  const labels = await loadLabels(client, item.id);
  const currentCategory = labels[0] || null;

  if (currentCategory && currentCategory !== nextCategory) {
    throw new InboxActionError('Existing category cannot be rewritten through the inbox action.', 409);
  }
  if (currentCategory === nextCategory) {
    throw new InboxActionError('Category is already set to that value.', 409);
  }

  await client.query(
    'INSERT INTO capture_item_labels (item_id, label_name) VALUES ($1, $2)',
    [item.id, nextCategory]
  );

  await writeAuditEvent(client, {
    action_type: 'inbox_add_missing_category',
    entity_name: 'capture_item_labels',
    entity_id: item.id,
    user_id: context.userId,
    device_id: item.device_id || 'system',
    diff_log: {
      category: {
        from: currentCategory,
        to: nextCategory
      },
      inbox_action: 'add_missing_category'
    }
  });

  await recordEntityUpdated(client, {
    user_id: context.userId,
    actor_id: context.actorId,
    source_type: context.sourceType,
    entity_id: item.id,
    entity_type: mapItemEntityType(item.type),
    quarter_reference: item.quarter_ref || null,
    description: `${item.type} ${item.reference_number || item.id} category added from inbox`,
    metadata: {
      action_type: 'add_missing_category',
      updated_field: 'category',
      previous_value: currentCategory,
      new_value: nextCategory
    }
  });

  return buildActionResponse({
    actionType: 'add_missing_category',
    item,
    eventType: 'entity_updated',
    metadata: {
      category: nextCategory
    }
  });
};

const applyCounterpartyUpdate = async (client, item, payload, context) => {
  const resolvedCounterparty = await resolveCounterparty(client, context.userId, payload.counterparty_reference);

  if (item.client_id && item.client_id !== resolvedCounterparty.clientId) {
    throw new InboxActionError('Existing counterparty cannot be rewritten through the inbox action.', 409);
  }
  if (item.client_id === resolvedCounterparty.clientId) {
    throw new InboxActionError('Counterparty is already set to that value.', 409);
  }

  await client.query(
    `
    UPDATE capture_items
    SET client_id = $3, updated_at = CURRENT_TIMESTAMP
    WHERE id = $1 AND user_id = $2
    `,
    [item.id, context.userId, resolvedCounterparty.clientId]
  );

  await writeAuditEvent(client, {
    action_type: 'inbox_add_missing_counterparty',
    entity_name: 'capture_items',
    entity_id: item.id,
    user_id: context.userId,
    device_id: item.device_id || 'system',
    diff_log: {
      counterparty: {
        from: item.client_id || null,
        to: resolvedCounterparty.clientId
      },
      inbox_action: 'add_missing_counterparty'
    }
  });

  await recordEntityUpdated(client, {
    user_id: context.userId,
    actor_id: context.actorId,
    source_type: context.sourceType,
    entity_id: item.id,
    entity_type: mapItemEntityType(item.type),
    quarter_reference: item.quarter_ref || null,
    description: `${item.type} ${item.reference_number || item.id} counterparty added from inbox`,
    metadata: {
      action_type: 'add_missing_counterparty',
      updated_field: 'counterparty',
      previous_value: item.client_id || item.client_name || null,
      new_value: resolvedCounterparty.clientId,
      counterparty_name: resolvedCounterparty.clientName,
      counterparty_created: resolvedCounterparty.created
    }
  });

  return buildActionResponse({
    actionType: 'add_missing_counterparty',
    item,
    eventType: 'entity_updated',
    metadata: {
      counterparty_reference: resolvedCounterparty.clientId,
      counterparty_name: resolvedCounterparty.clientName
    }
  });
};

const applyQuoteConversion = async (client, item, context) => {
  if (item.type !== 'quote') {
    throw new InboxActionError('convert_quote_to_invoice is only supported for quotes.', 409);
  }

  const invoice = await convertQuoteToInvoiceInternal(item.id, {
    user_id: context.userId,
    actor_id: context.actorId,
    source_type: context.sourceType,
    dbClient: client
  });

  await writeAuditEvent(client, {
    action_type: 'inbox_convert_quote_to_invoice',
    entity_name: 'capture_items',
    entity_id: item.id,
    user_id: context.userId,
    device_id: item.device_id || 'system',
    diff_log: {
      conversion: {
        from_quote_id: item.id,
        to_invoice_id: invoice.id
      },
      inbox_action: 'convert_quote_to_invoice'
    }
  });

  return buildActionResponse({
    actionType: 'convert_quote_to_invoice',
    item,
    eventType: 'quote_converted',
    statusCode: 201,
    linkedEntityType: 'quote',
    metadata: {
      invoice_id: invoice.id
    }
  });
};

const applyInboxAction = async (executor, payload = {}) => {
  ensureSingleEntityPayload(payload);
  const actionType = validateActionType(payload.action_type);
  const userId = String(payload.user_id || '');
  const actorId = String(payload.actor_id || payload.user_id || 'system');
  const sourceType = payload.source_type || 'manual';

  if (!userId) {
    throw new InboxActionError('user_id is required.', 400);
  }
  if (!payload.entity_id || Array.isArray(payload.entity_id)) {
    throw new InboxActionError('entity_id is required.', 400);
  }

  const { client, managesTransaction } = await ensureExecutor(executor);
  try {
    if (managesTransaction) {
      await client.query('BEGIN');
    }

    const item = await loadItem(client, userId, payload.entity_id);
    const context = { userId, actorId, sourceType };
    let result;

    switch (actionType) {
      case 'mark_paid':
        result = await applyMarkPaid(client, item, context);
        break;
      case 'update_due_date':
        result = await applyDueDateUpdate(client, item, payload, context);
        break;
      case 'add_missing_category':
        result = await applyCategoryUpdate(client, item, payload, context);
        break;
      case 'add_missing_counterparty':
        result = await applyCounterpartyUpdate(client, item, payload, context);
        break;
      case 'convert_quote_to_invoice':
        result = await applyQuoteConversion(client, item, context);
        break;
      default:
        throw new InboxActionError(`Unsupported inbox action "${actionType}".`, 400);
    }

    if (managesTransaction) {
      await client.query('COMMIT');
    }
    return result;
  } catch (err) {
    if (managesTransaction) {
      await client.query('ROLLBACK');
    }
    if (err instanceof InboxActionError) {
      throw err;
    }
    throw new InboxActionError(err.message || 'Failed to apply inbox action.', 500);
  } finally {
    if (managesTransaction) {
      client.release();
    }
  }
};

module.exports = {
  InboxActionError,
  SUPPORTED_ACTIONS,
  applyInboxAction
};
