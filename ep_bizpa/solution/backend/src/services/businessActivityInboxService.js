const FINANCIAL_ENTITY_TYPES = new Set(['invoice', 'receipt_expense', 'payment', 'quote', 'booking']);
const ALERT_EVENT_TYPES = new Set([
  'snapshot_created',
  'quarter_closed',
  'quarter_reopened',
  'auto_commit_enabled',
  'auto_commit_disabled',
  'auto_commit_expired',
  'governance_policy_changed',
  'entity_voided',
  'entity_superseded'
]);
const SUPPORTED_FILTERS = new Set(['all', 'needs_review', 'financial', 'quotes', 'payments', 'alerts']);
const NOISE_EVENT_TYPES = new Set(['readiness_recalculated']);

const ensureExecutor = (executor) => {
  if (!executor || typeof executor.query !== 'function') {
    throw new Error('A database executor with query(text, params) is required.');
  }
  return executor;
};

const normalizeFilterMode = (value) => {
  const normalized = String(value || 'all').trim().toLowerCase().replace(/\s+/g, '_');
  return SUPPORTED_FILTERS.has(normalized) ? normalized : 'all';
};

const buildBaseClauses = (filters = {}) => {
  const clauses = ['user_id = $1'];
  const params = [filters.user_id];
  let index = 2;

  clauses.push(`event_type <> ALL($${index++})`);
  params.push(Array.from(NOISE_EVENT_TYPES));

  if (filters.quarter_reference) {
    clauses.push(`quarter_reference = $${index++}`);
    params.push(filters.quarter_reference);
  }

  if (filters.entity_id) {
    clauses.push(`entity_id = $${index++}`);
    params.push(filters.entity_id);
  }

  if (filters.entity_type) {
    clauses.push(`entity_type = $${index++}`);
    params.push(filters.entity_type);
  }

  return { clauses, params, nextIndex: index };
};

const listBaseEvents = async (executor, filters = {}) => {
  const client = ensureExecutor(executor);
  const limit = Math.max(1, Math.min(500, Number(filters.limit || 50)));
  const offset = Math.max(0, Number(filters.offset || 0));
  const base = buildBaseClauses(filters);
  const dataParams = base.params.slice();
  const countParams = base.params.slice();
  const limitIndex = base.nextIndex;
  const offsetIndex = base.nextIndex + 1;

  dataParams.push(limit, offset);

  const [dataResult, countResult] = await Promise.all([
    client.query(
      `
      SELECT
        event_id,
        event_type,
        entity_id,
        entity_type,
        created_at AS timestamp,
        actor_id,
        source_type,
        description,
        metadata,
        quarter_reference,
        status_from,
        status_to
      FROM business_event_log
      WHERE ${base.clauses.join(' AND ')}
      ORDER BY created_at DESC, event_id DESC
      LIMIT $${limitIndex} OFFSET $${offsetIndex}
      `,
      dataParams
    ),
    client.query(
      `
      SELECT COUNT(*)::int AS total
      FROM business_event_log
      WHERE ${base.clauses.join(' AND ')}
      `,
      countParams
    )
  ]);

  return {
    rows: dataResult.rows,
    total: countResult.rows[0]?.total || 0,
    limit,
    offset
  };
};

const extractAmount = (event, entity) => {
  const metadata = event.metadata || {};
  const rawValue = entity?.gross_amount
    ?? entity?.amount
    ?? metadata.gross_amount
    ?? metadata.amount
    ?? null;

  if (rawValue === null || rawValue === undefined) {
    return null;
  }

  const value = Number(rawValue);
  return {
    value: Number.isFinite(value) ? value : rawValue,
    currency: entity?.currency || metadata.currency || 'GBP'
  };
};

const extractCounterparty = (event, entity) => {
  const metadata = event.metadata || {};
  return entity?.client_name
    || metadata.counterparty
    || metadata.client_name
    || metadata.counterparty_name
    || null;
};

const deriveStatusBadge = (event, entity) => {
  const status = entity?.payment_status || event.status_to || entity?.status || null;
  if (!status) {
    if (ALERT_EVENT_TYPES.has(event.event_type)) {
      return { label: 'Alert', tone: 'warning' };
    }
    return null;
  }

  const toneMap = {
    draft: 'muted',
    confirmed: 'info',
    sent: 'info',
    paid: 'success',
    partial: 'warning',
    overdue: 'warning',
    archived: 'muted',
    converted: 'success',
    open: 'info',
    ready: 'success',
    void_requested: 'danger'
  };

  return {
    label: String(status).replace(/_/g, ' '),
    tone: toneMap[status] || 'info'
  };
};

const deriveNeedsReview = (event, entity) => {
  const metadata = event.metadata || {};
  if (metadata.needs_review === true || metadata.review_required === true) {
    return true;
  }
  if (typeof metadata.blocking_txns_count === 'number' && metadata.blocking_txns_count > 0) {
    return true;
  }
  if (['draft', 'overdue', 'partial', 'void_requested'].includes(event.status_to)) {
    return true;
  }
  if (['draft', 'overdue', 'partial', 'void_requested'].includes(entity?.status) || ['overdue', 'partial'].includes(entity?.payment_status)) {
    return true;
  }
  return ['quarter_reopened', 'entity_voided', 'entity_superseded'].includes(event.event_type);
};

const deriveAutoCommitBadge = (event) => {
  if (event.event_type === 'auto_commit_enabled') {
    return { label: 'Auto-Commit On', tone: 'warning' };
  }
  if (event.event_type === 'auto_commit_disabled') {
    return { label: 'Auto-Commit Off', tone: 'muted' };
  }
  if (event.event_type === 'auto_commit_expired') {
    return { label: 'Auto-Commit Expired', tone: 'warning' };
  }
  if (event.source_type === 'voice' && event.metadata?.commit_mode === 'auto') {
    return { label: 'Auto-Commit', tone: 'warning' };
  }
  return null;
};

const buildEventTitle = (event, entity, counterparty) => {
  const entityLabel = (entity?.type || event.entity_type || 'record').replace(/_/g, ' ');
  const statusTarget = event.status_to ? String(event.status_to).replace(/_/g, ' ') : null;

  switch (event.event_type) {
    case 'entity_created':
      return `${entityLabel} created`;
    case 'entity_committed':
      return `${entityLabel} committed`;
    case 'entity_status_changed':
      return statusTarget ? `${entityLabel} ${statusTarget}` : `${entityLabel} status updated`;
    case 'entity_updated':
      if (event.metadata?.updated_field === 'due_date') return `${entityLabel} due date updated`;
      if (event.metadata?.updated_field === 'category') return `${entityLabel} category added`;
      if (event.metadata?.updated_field === 'counterparty') return `${entityLabel} counterparty added`;
      return `${entityLabel} updated`;
    case 'entity_voided':
      return `${entityLabel} voided`;
    case 'entity_superseded':
      return `${entityLabel} corrected`;
    case 'payment_recorded':
      return counterparty ? `Payment recorded from ${counterparty}` : 'Payment recorded';
    case 'quote_converted':
      return 'Quote converted to invoice';
    case 'snapshot_created':
      return 'Quarter snapshot created';
    case 'quarter_closed':
      return 'Quarter closed';
    case 'quarter_reopened':
      return 'Quarter reopened';
    case 'auto_commit_enabled':
      return 'Auto-commit enabled';
    case 'auto_commit_disabled':
      return 'Auto-commit disabled';
    case 'auto_commit_expired':
      return 'Auto-commit expired';
    case 'governance_policy_changed':
      return 'Governance policy changed';
    default:
      return event.description || `${entityLabel} updated`;
  }
};

const buildFilterTags = (event, entity, needsReview) => {
  const tags = new Set(['all']);
  const entityType = entity?.type || event.entity_type;

  if (needsReview) tags.add('needs_review');
  if (FINANCIAL_ENTITY_TYPES.has(entityType)) tags.add('financial');
  if (entityType === 'quote' || event.event_type === 'quote_converted') tags.add('quotes');
  if (entityType === 'payment' || event.event_type === 'payment_recorded') tags.add('payments');
  if (ALERT_EVENT_TYPES.has(event.event_type)) tags.add('alerts');

  return Array.from(tags);
};

const shouldIncludeByFilter = (item, filterMode) => filterMode === 'all' || item.filter_tags.includes(filterMode);

const loadCaptureItems = async (executor, userId, entityIds) => {
  const ids = Array.from(new Set(entityIds.filter(Boolean)));
  if (ids.length === 0) {
    return new Map();
  }

  const result = await executor.query(
    `
    SELECT
      ci.id,
      ci.type,
      ci.status,
      ci.payment_status,
      ci.amount,
      ci.gross_amount,
      ci.currency,
      ci.client_id,
      ci.reference_number,
      c.name AS client_name
    FROM capture_items ci
    LEFT JOIN clients c ON c.id = ci.client_id
    WHERE ci.user_id = $1
      AND ci.id = ANY($2)
    `,
    [userId, ids]
  );

  return new Map(result.rows.map((row) => [row.id, row]));
};

const mapInboxItem = (event, entity) => {
  const counterparty = extractCounterparty(event, entity);
  const amount = extractAmount(event, entity);
  const needsReview = deriveNeedsReview(event, entity);
  const statusBadge = deriveStatusBadge(event, entity);
  const autoCommitBadge = deriveAutoCommitBadge(event);

  return {
    event_id: event.event_id,
    event_type: event.event_type,
    event_title: buildEventTitle(event, entity, counterparty),
    linked_entity_id: event.entity_id || null,
    linked_entity_type: entity?.type || event.entity_type || null,
    linked_entity: {
      id: event.entity_id || null,
      type: entity?.type || event.entity_type || null,
      reference_number: entity?.reference_number || null,
      status: entity?.payment_status || event.status_to || entity?.status || null,
      counterparty_id: entity?.client_id || null,
      counterparty_name: counterparty
    },
    amount,
    counterparty,
    status_badge: statusBadge,
    timestamp: event.timestamp,
    auto_commit_badge: autoCommitBadge,
    needs_review_badge: needsReview ? { label: 'Needs Review', tone: 'warning' } : null,
    description: event.description,
    source_type: event.source_type,
    quarter_reference: event.quarter_reference || null,
    filter_tags: buildFilterTags(event, entity, needsReview)
  };
};

const listBusinessActivityInbox = async (executor, filters = {}) => {
  const client = ensureExecutor(executor);
  const filterMode = normalizeFilterMode(filters.filter);
  const base = await listBaseEvents(client, filters);
  const captureItemIds = base.rows
    .filter((event) => Boolean(event.entity_id) && FINANCIAL_ENTITY_TYPES.has(event.entity_type))
    .map((event) => event.entity_id);
  const itemMap = await loadCaptureItems(client, filters.user_id, captureItemIds);

  const mapped = base.rows.map((event) => mapInboxItem(event, itemMap.get(event.entity_id)));
  const filteredItems = mapped.filter((item) => shouldIncludeByFilter(item, filterMode));

  return {
    items: filteredItems,
    pagination: {
      limit: base.limit,
      offset: base.offset,
      total: filterMode === 'all' ? base.total : filteredItems.length,
      has_more: base.offset + filteredItems.length < (filterMode === 'all' ? base.total : filteredItems.length)
    },
    applied_filter: filterMode,
    available_filters: Array.from(SUPPORTED_FILTERS)
  };
};

module.exports = {
  ALERT_EVENT_TYPES,
  FINANCIAL_ENTITY_TYPES,
  NOISE_EVENT_TYPES,
  SUPPORTED_FILTERS,
  listBusinessActivityInbox,
  mapInboxItem,
  normalizeFilterMode
};
