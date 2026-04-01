const SUPPORTED_ENTITY_TYPES = new Set(['invoice', 'receipt', 'quote', 'payment', 'note']);

const ensureExecutor = (executor) => {
  if (!executor || typeof executor.query !== 'function') {
    throw new Error('A database executor with query(text, params) is required.');
  }
  return executor;
};

const toDisplayText = (value, fallback = 'Not set') => {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  return String(value);
};

const titleCase = (value) => toDisplayText(value, 'Unknown')
  .replace(/_/g, ' ')
  .replace(/\b\w/g, (character) => character.toUpperCase());

const formatMoneyValue = (amount, currency = 'GBP') => {
  if (amount === null || amount === undefined || amount === '') {
    return null;
  }

  const numeric = Number(amount);
  if (!Number.isFinite(numeric)) {
    return `${currency} ${String(amount)}`;
  }
  return `${currency} ${numeric.toFixed(2)}`;
};

const deriveAvailableActions = (entity) => {
  const actions = [];
  const entityType = entity.type;
  const status = entity.status;
  const paymentStatus = entity.payment_status;

  if (entityType === 'invoice') {
    actions.push('Open correction flow', 'Add attachment');
    if (paymentStatus !== 'paid') actions.push('Mark as paid');
    if (status !== 'voided') actions.push('Send payment chase');
  } else if (entityType === 'receipt') {
    actions.push('Open correction flow', 'Add attachment', 'Categorise receipt');
  } else if (entityType === 'quote') {
    actions.push('Open correction flow', 'Add attachment');
    if (status !== 'converted') actions.push('Convert to invoice');
  } else if (entityType === 'payment') {
    actions.push('Open correction flow', 'Add attachment', 'Match against invoice');
  } else if (entityType === 'note') {
    actions.push('Archive note', 'Link follow-up evidence');
  }

  return actions;
};

const deriveCorrectionState = (entity, timeline) => {
  const eventTypes = new Set((timeline || []).map((event) => event.event_type));
  if (eventTypes.has('entity_superseded')) {
    return 'corrected';
  }
  if (eventTypes.has('entity_voided')) {
    return 'voided';
  }
  if (entity.converted_from_id) {
    return 'converted';
  }
  return 'original';
};

const mapTimeline = (rows) => rows.map((row) => ({
  event_id: row.event_id,
  event_type: row.event_type,
  created_at: row.created_at,
  source_type: row.source_type,
  description: row.description,
  status_from: row.status_from,
  status_to: row.status_to,
  metadata: row.metadata || {}
}));

const mapNotes = (entity, timeline) => {
  const notes = [];
  if (entity.raw_note) {
    notes.push({
      kind: entity.type === 'note' ? 'primary_note' : 'entity_note',
      text: entity.raw_note,
      created_at: entity.updated_at || entity.created_at
    });
  }
  if (entity.extracted_text && entity.extracted_text !== entity.raw_note) {
    notes.push({
      kind: 'extracted_text',
      text: entity.extracted_text,
      created_at: entity.updated_at || entity.created_at
    });
  }

  timeline.forEach((event) => {
    if (event.metadata?.reason) {
      notes.push({
        kind: 'correction_reason',
        text: String(event.metadata.reason),
        created_at: event.created_at
      });
    }
  });

  return notes;
};

const getEntityDetailView = async (executor, filters = {}) => {
  const client = ensureExecutor(executor);
  const entityType = String(filters.entity_type || '').trim().toLowerCase();
  const entityId = filters.entity_id;
  const userId = filters.user_id;

  if (!SUPPORTED_ENTITY_TYPES.has(entityType)) {
    const error = new Error(`Unsupported entity type: ${entityType || 'unknown'}`);
    error.statusCode = 400;
    throw error;
  }

  if (!entityId) {
    const error = new Error('entity_id is required.');
    error.statusCode = 400;
    throw error;
  }

  const entityResult = await client.query(
    `
    SELECT
      ci.*,
      c.name AS client_name,
      c.email AS client_email,
      c.phone AS client_phone
    FROM capture_items ci
    LEFT JOIN clients c ON c.id = ci.client_id
    WHERE ci.user_id = $1
      AND ci.id = $2
      AND ci.type = $3
      AND ci.deleted_at IS NULL
    LIMIT 1
    `,
    [userId, entityId, entityType]
  );

  if (entityResult.rows.length === 0) {
    const error = new Error('Entity not found or access denied.');
    error.statusCode = 404;
    throw error;
  }

  const entity = entityResult.rows[0];

  const [labelsResult, attachmentsResult, timelineResult] = await Promise.all([
    client.query(
      `
      SELECT label_name
      FROM capture_item_labels
      WHERE item_id = $1
      ORDER BY label_name ASC
      `,
      [entityId]
    ),
    client.query(
      `
      SELECT id, kind, file_path, metadata, created_at
      FROM capture_item_attachments
      WHERE item_id = $1
      ORDER BY created_at DESC, id DESC
      `,
      [entityId]
    ),
    client.query(
      `
      SELECT
        event_id,
        event_type,
        created_at,
        source_type,
        description,
        status_from,
        status_to,
        metadata
      FROM business_event_log
      WHERE user_id = $1
        AND entity_id = $2
        AND entity_type = $3
      ORDER BY created_at DESC, event_id DESC
      `,
      [userId, entityId, entityType]
    )
  ]);

  const timeline = mapTimeline(timelineResult.rows);
  const correctionState = deriveCorrectionState(entity, timeline);
  const notes = mapNotes(entity, timeline);
  const labels = labelsResult.rows.map((row) => row.label_name);

  return {
    entity_id: entity.id,
    entity_type: entity.type,
    reference_number: entity.reference_number || null,
    header_block: {
      title: `${titleCase(entity.type)} ${toDisplayText(entity.reference_number, entity.id)}`,
      subtitle: toDisplayText(entity.client_name, entity.counterparty_name || 'No counterparty linked'),
      description: toDisplayText(entity.extracted_text || entity.raw_note, 'No additional detail captured.'),
      labels
    },
    client_or_supplier: {
      name: entity.client_name || null,
      email: entity.client_email || null,
      phone: entity.client_phone || null
    },
    net_vat_gross: {
      net_amount: formatMoneyValue(entity.net_amount, entity.currency || 'GBP'),
      vat_amount: formatMoneyValue(entity.vat_amount, entity.currency || 'GBP'),
      gross_amount: formatMoneyValue(entity.gross_amount ?? entity.amount, entity.currency || 'GBP'),
      currency: entity.currency || 'GBP'
    },
    status: titleCase(entity.status),
    due_date: entity.due_date || null,
    payment_status: entity.payment_status ? titleCase(entity.payment_status) : null,
    correction_state: correctionState,
    attachments: attachmentsResult.rows.map((row) => ({
      id: row.id,
      kind: row.kind,
      file_path: row.file_path,
      created_at: row.created_at,
      metadata: row.metadata || {}
    })),
    notes,
    entity_timeline: timeline,
    available_actions: deriveAvailableActions(entity)
  };
};

module.exports = {
  SUPPORTED_ENTITY_TYPES,
  deriveAvailableActions,
  deriveCorrectionState,
  getEntityDetailView
};
