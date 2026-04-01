const PRIORITY_RANK = {
  critical: 0,
  important: 1,
  informational: 2
};

const DELIVERY_STATUS_RANK = {
  queued: 0,
  displayed: 1,
  delivered: 1,
  dismissed: 2,
  failed: 3
};

const SEVERITY_ALIAS = {
  critical: 'critical',
  urgent: 'critical',
  high: 'critical',
  important: 'important',
  warning: 'important',
  medium: 'important',
  info: 'informational',
  informational: 'informational',
  low: 'informational'
};

const CATEGORY_DEFAULT_LINKS = {
  overdue_invoice: '/activity',
  readiness_change: '/quarter',
  stale_snapshot: '/quarter',
  deadline: '/calendar',
  sync_health: '/control',
  operational_signal: '/activity',
  system: '/control'
};

const hasValue = (value) => value !== null && value !== undefined && value !== '';

const toNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const toIsoTimestamp = (value, fallback = null) => {
  if (!value) return fallback;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return fallback;
  return parsed.toISOString();
};

const slugify = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '_')
  .replace(/^_+|_+$/g, '');

const normalizeSeverity = (value) => SEVERITY_ALIAS[String(value || '').trim().toLowerCase()] || 'informational';

const normalizeDeliveryStatus = (value) => {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized in DELIVERY_STATUS_RANK) {
    return normalized;
  }
  return 'queued';
};

const getPriorityRank = (priority) => PRIORITY_RANK[normalizeSeverity(priority)] ?? 99;

const compareNotificationPriority = (left, right) => {
  const severityDiff = getPriorityRank(left.severity || left.priority) - getPriorityRank(right.severity || right.priority);
  if (severityDiff !== 0) return severityDiff;

  const statusDiff = (DELIVERY_STATUS_RANK[normalizeDeliveryStatus(left.delivery_status)] ?? 99)
    - (DELIVERY_STATUS_RANK[normalizeDeliveryStatus(right.delivery_status)] ?? 99);
  if (statusDiff !== 0) return statusDiff;

  const leftDate = new Date(left.created_at || left.date || 0).getTime();
  const rightDate = new Date(right.created_at || right.date || 0).getTime();
  if (leftDate !== rightDate) return rightDate - leftDate;

  return String(left.notification_id || left.id || '').localeCompare(String(right.notification_id || right.id || ''));
};

const sortNotifications = (notifications = []) => notifications
  .slice()
  .sort(compareNotificationPriority);

const buildConditionKey = (...parts) => {
  const normalized = parts
    .flat()
    .filter(hasValue)
    .map((part) => slugify(part))
    .filter(Boolean);
  return normalized.join(':');
};

const buildLinkedTarget = ({
  route = null,
  kind = 'screen',
  workflow = null,
  label = null,
  entityId = null,
  entityType = null
} = {}) => ({
  kind,
  route: route || '/inbox',
  workflow: workflow || route || '/inbox',
  label: label || 'Review',
  entity_id: entityId,
  entity_type: entityType
});

const buildNotificationPayload = (notification = {}) => {
  const severity = normalizeSeverity(notification.severity || notification.priority);
  const notificationId = notification.notification_id || notification.id || buildConditionKey(
    notification.category,
    notification.condition_key,
    notification.title,
    notification.created_at
  );
  const linkedTarget = notification.linked_target && typeof notification.linked_target === 'object'
    ? {
        ...notification.linked_target,
        route: notification.linked_target.route || CATEGORY_DEFAULT_LINKS[notification.category] || '/inbox'
      }
    : buildLinkedTarget({
        route: notification.action_link || CATEGORY_DEFAULT_LINKS[notification.category] || '/inbox',
        label: notification.action_label || 'Review',
        entityId: notification.source_entity_id || notification.linked_entity_id || null,
        entityType: notification.source_entity_name || notification.linked_entity_type || null
      });

  return {
    notification_id: notificationId,
    id: notificationId,
    category: notification.category || 'system',
    severity,
    priority: severity,
    title: notification.title || 'Business notification',
    message: notification.message || notification.description || 'A business condition requires review.',
    linked_target: linkedTarget,
    created_at: toIsoTimestamp(notification.created_at || notification.date, new Date(0).toISOString()),
    delivery_status: normalizeDeliveryStatus(
      notification.delivery_status
      || (notification.is_dismissed ? 'dismissed' : 'queued')
    ),
    dismissed_at: toIsoTimestamp(notification.dismissed_at),
    condition_key: notification.condition_key || buildConditionKey(
      notification.category,
      notification.source,
      notification.source_entity_id || notification.linked_entity_id,
      notification.linked_target?.route || linkedTarget.route,
      notification.title
    ),
    source: notification.source || 'notification_engine',
    trace: {
      source_entity_id: notification.source_entity_id || notification.linked_entity_id || null,
      source_entity_name: notification.source_entity_name || null,
      metadata: notification.trace?.metadata || notification.metadata || null
    }
  };
};

const dedupeNotifications = (notifications = [], existingConditions = new Set()) => {
  const selected = new Map();

  notifications.forEach((rawNotification) => {
    const payload = buildNotificationPayload(rawNotification);
    if (existingConditions.has(payload.condition_key)) {
      return;
    }

    const existing = selected.get(payload.condition_key);
    if (!existing || compareNotificationPriority(payload, existing) < 0) {
      selected.set(payload.condition_key, payload);
    }
  });

  return sortNotifications(Array.from(selected.values()));
};

const summarizeNotificationHealth = (notifications = []) => notifications.reduce((summary, notification) => {
  const severity = normalizeSeverity(notification.severity || notification.priority);
  const deliveryStatus = normalizeDeliveryStatus(notification.delivery_status);
  summary.total += 1;
  summary.by_severity[severity] = (summary.by_severity[severity] || 0) + 1;
  summary.by_delivery_status[deliveryStatus] = (summary.by_delivery_status[deliveryStatus] || 0) + 1;
  return summary;
}, {
  total: 0,
  by_severity: {
    critical: 0,
    important: 0,
    informational: 0
  },
  by_delivery_status: {}
});

const buildOverdueInvoiceNotifications = ({ now, overdueInvoices = [] }) => overdueInvoices.map((invoice) => {
  const dueDate = toIsoTimestamp(invoice.due_date, null);
  const invoiceRef = invoice.reference_number || invoice.id || 'invoice';

  return {
    category: 'overdue_invoice',
    severity: 'critical',
    title: `Overdue invoice ${invoiceRef}`,
    message: `Invoice ${invoiceRef} is overdue${dueDate ? ` since ${dueDate.slice(0, 10)}` : ''}.`,
    created_at: dueDate || now,
    linked_target: buildLinkedTarget({
      route: '/activity',
      workflow: '/activity',
      label: 'Review invoice',
      entityId: invoice.id || null,
      entityType: 'invoice'
    }),
    delivery_status: 'queued',
    condition_key: buildConditionKey('overdue_invoice', invoice.id || invoice.reference_number || invoiceRef),
    source: 'capture_items',
    source_entity_id: invoice.id || null,
    source_entity_name: 'capture_items',
    trace: {
      metadata: {
        amount: toNumber(invoice.amount ?? invoice.gross_amount, null),
        due_date: invoice.due_date || null
      }
    }
  };
});

const buildReadinessNotifications = ({ now, readiness = null, previousReadiness = null }) => {
  if (!readiness) return [];

  const notifications = [];
  const quarterReference = readiness.quarter_reference || 'active quarter';
  const blockerCount = toNumber(readiness.blocking_txns_count);
  const readinessPct = toNumber(readiness.readiness_pct);
  const previousPct = previousReadiness ? toNumber(previousReadiness.readiness_pct) : null;
  const previousBlockers = previousReadiness ? toNumber(previousReadiness.blocking_txns_count) : null;

  if (blockerCount > 0) {
    notifications.push({
      category: 'readiness_change',
      severity: blockerCount >= 3 || readinessPct < 85 ? 'critical' : 'important',
      title: `${quarterReference} readiness is blocked`,
      message: `${blockerCount} blocking transaction${blockerCount === 1 ? '' : 's'} still prevent export readiness.`,
      created_at: now,
      linked_target: buildLinkedTarget({
        route: '/quarter',
        workflow: '/inbox/finish-now',
        label: 'Resolve blockers',
        entityType: 'readiness'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('readiness_blocked', quarterReference),
      source: 'readiness_report',
      trace: {
        metadata: {
          readiness_pct: readinessPct,
          blocking_txns_count: blockerCount
        }
      }
    });
  }

  if (previousPct !== null && previousPct !== readinessPct) {
    const dropped = readinessPct < previousPct;
    notifications.push({
      category: 'readiness_change',
      severity: dropped ? 'important' : 'informational',
      title: dropped ? `${quarterReference} readiness dropped` : `${quarterReference} readiness improved`,
      message: `Readiness moved from ${previousPct}% to ${readinessPct}%${previousBlockers !== null ? ` and blockers moved from ${previousBlockers} to ${blockerCount}` : ''}.`,
      created_at: now,
      linked_target: buildLinkedTarget({
        route: '/quarter',
        workflow: '/quarter',
        label: 'Review readiness',
        entityType: 'readiness'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('readiness_delta', quarterReference, dropped ? 'down' : 'up', readinessPct),
      source: 'readiness_report',
      trace: {
        metadata: {
          previous_readiness_pct: previousPct,
          readiness_pct: readinessPct,
          previous_blocking_txns_count: previousBlockers,
          blocking_txns_count: blockerCount
        }
      }
    });
  }

  if (readiness.can_export === true && blockerCount === 0) {
    notifications.push({
      category: 'readiness_change',
      severity: 'informational',
      title: `${quarterReference} is export-ready`,
      message: `Readiness is ${readinessPct}% and no blocking transactions are open.`,
      created_at: now,
      linked_target: buildLinkedTarget({
        route: '/quarter',
        workflow: '/quarter',
        label: 'Open quarter view',
        entityType: 'readiness'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('readiness_export_ready', quarterReference),
      source: 'readiness_report',
      trace: {
        metadata: {
          readiness_pct: readinessPct
        }
      }
    });
  }

  return notifications;
};

const buildSnapshotNotifications = ({ now, snapshotStatus = null, readiness = null }) => {
  if (!snapshotStatus) return [];

  const notifications = [];
  const quarterReference = snapshotStatus.quarter_reference || readiness?.quarter_reference || 'active quarter';
  const latestSnapshot = snapshotStatus.latest_snapshot || null;

  if (!latestSnapshot && toNumber(readiness?.total_txns_in_period) > 0) {
    notifications.push({
      category: 'stale_snapshot',
      severity: 'important',
      title: `No snapshot recorded for ${quarterReference}`,
      message: 'Create the first quarter snapshot to anchor exports and audit review.',
      created_at: now,
      linked_target: buildLinkedTarget({
        route: '/quarter',
        workflow: '/quarter',
        label: 'Create snapshot',
        entityType: 'snapshot'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('missing_snapshot', quarterReference),
      source: 'snapshot_status'
    });
    return notifications;
  }

  if (snapshotStatus.changed_since_snapshot === true) {
    notifications.push({
      category: 'stale_snapshot',
      severity: snapshotStatus.quarter_lifecycle?.status === 'closed' ? 'critical' : 'important',
      title: `Snapshot is stale for ${quarterReference}`,
      message: 'Live quarter data changed after the latest snapshot and needs a fresh version.',
      created_at: now,
      linked_target: buildLinkedTarget({
        route: '/quarter',
        workflow: '/quarter',
        label: 'Review snapshot diff',
        entityId: latestSnapshot?.snapshot_id || null,
        entityType: 'snapshot'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('stale_snapshot', quarterReference, latestSnapshot?.snapshot_id || 'current'),
      source: 'snapshot_status',
      source_entity_id: latestSnapshot?.snapshot_id || null,
      source_entity_name: 'business_event_log'
    });
  }

  if (latestSnapshot?.created_at) {
    notifications.push({
      category: 'operational_signal',
      severity: 'informational',
      title: `Latest snapshot ${latestSnapshot.snapshot_id || ''}`.trim(),
      message: `Snapshot version ${latestSnapshot.version_number || 1} is the current baseline for ${quarterReference}.`,
      created_at: latestSnapshot.created_at,
      linked_target: buildLinkedTarget({
        route: '/quarter',
        workflow: '/quarter',
        label: 'Open snapshot',
        entityId: latestSnapshot.snapshot_id || null,
        entityType: 'snapshot'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('snapshot_current', quarterReference, latestSnapshot.snapshot_id || latestSnapshot.version_number || 'latest'),
      source: 'snapshot_status',
      source_entity_id: latestSnapshot.snapshot_id || null,
      source_entity_name: 'business_event_log'
    });
  }

  return notifications;
};

const buildDeadlineNotifications = ({ now, deadlines = [] }) => deadlines.map((entry) => {
  const title = entry.title || entry.description || entry.name || 'Upcoming deadline';
  const date = toIsoTimestamp(entry.date || entry.start_at || entry.due_date, now);
  const severity = entry.source === 'event' ? 'important' : 'informational';

  return {
    category: 'deadline',
    severity,
    title,
    message: entry.description || `Scheduled for ${date.slice(0, 10)}.`,
    created_at: date,
    linked_target: buildLinkedTarget({
      route: entry.source === 'event' ? '/calendar' : '/activity',
      workflow: entry.source === 'event' ? '/calendar' : '/activity',
      label: entry.source === 'event' ? 'Open calendar' : 'Open item',
      entityId: entry.id || null,
      entityType: entry.type || entry.source || null
    }),
    delivery_status: 'queued',
    condition_key: buildConditionKey('deadline', entry.source || 'unknown', entry.id || title, date.slice(0, 10)),
    source: entry.source || 'calendar'
  };
});

const buildSyncHealthNotifications = ({ now, syncHealth = null }) => {
  if (!syncHealth) return [];

  const notifications = [];
  const backlogSize = toNumber(syncHealth.backlog_size);
  const errorRate = toNumber(syncHealth.error_rate);
  const lastSuccessfulSync = syncHealth.last_successful_sync ? new Date(syncHealth.last_successful_sync) : null;
  const lastSuccessAgeHours = lastSuccessfulSync
    ? (new Date(now).getTime() - lastSuccessfulSync.getTime()) / (1000 * 60 * 60)
    : null;

  if (backlogSize >= 10 || errorRate >= 0.2 || (lastSuccessAgeHours !== null && lastSuccessAgeHours >= 24)) {
    notifications.push({
      category: 'sync_health',
      severity: 'critical',
      title: 'Sync health needs intervention',
      message: `Backlog ${backlogSize}, error rate ${(errorRate * 100).toFixed(0)}%, last successful sync ${lastSuccessfulSync ? syncHealth.last_successful_sync : 'unknown'}.`,
      created_at: now,
      linked_target: buildLinkedTarget({
        route: '/control',
        workflow: '/control',
        label: 'Open control centre',
        entityType: 'sync'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('sync_health_critical', backlogSize >= 10 ? 'backlog' : 'stale'),
      source: 'sync_health'
    });
  } else if (backlogSize > 0 || errorRate > 0 || toNumber(syncHealth.recent_conflicts?.length) > 0) {
    notifications.push({
      category: 'sync_health',
      severity: 'important',
      title: 'Sync queue is not clean',
      message: `Backlog ${backlogSize}, error rate ${(errorRate * 100).toFixed(0)}%, recent conflicts ${toNumber(syncHealth.recent_conflicts?.length)}.`,
      created_at: now,
      linked_target: buildLinkedTarget({
        route: '/control',
        workflow: '/control',
        label: 'Inspect sync health',
        entityType: 'sync'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('sync_health_warning', backlogSize, errorRate),
      source: 'sync_health'
    });
  } else if (syncHealth.last_successful_sync) {
    notifications.push({
      category: 'sync_health',
      severity: 'informational',
      title: 'Sync health is stable',
      message: `Latest successful sync completed at ${syncHealth.last_successful_sync}.`,
      created_at: syncHealth.last_successful_sync,
      linked_target: buildLinkedTarget({
        route: '/control',
        workflow: '/control',
        label: 'View sync telemetry',
        entityType: 'sync'
      }),
      delivery_status: 'queued',
      condition_key: buildConditionKey('sync_health_ok', syncHealth.last_successful_sync),
      source: 'sync_health'
    });
  }

  return notifications;
};

const buildOperationalSignalNotifications = ({ events = [] }) => events.map((event) => {
  const eventType = String(event.event_type || '').toLowerCase();
  const severity = eventType === 'quarter_reopened'
    ? 'important'
    : 'informational';
  const titleMap = {
    quarter_closed: 'Quarter closed',
    quarter_reopened: 'Quarter reopened',
    snapshot_created: 'Quarter snapshot created'
  };

  return {
    category: 'operational_signal',
    severity,
    title: titleMap[eventType] || (event.description || 'Operational signal'),
    message: event.description || `${eventType.replace(/_/g, ' ')} recorded.`,
    created_at: event.created_at || event.timestamp,
    linked_target: buildLinkedTarget({
      route: eventType === 'snapshot_created' ? '/quarter' : '/activity',
      workflow: eventType === 'snapshot_created' ? '/quarter' : '/activity',
      label: eventType === 'snapshot_created' ? 'Review snapshot' : 'Open timeline',
      entityId: event.entity_id || null,
      entityType: event.entity_type || null
    }),
    delivery_status: 'queued',
    condition_key: buildConditionKey('operational_signal', eventType, event.entity_id || event.event_id || event.created_at),
    source: 'business_event_log',
    source_entity_id: event.entity_id || null,
    source_entity_name: 'business_event_log'
  };
});

const buildNotificationEngine = ({
  now = new Date().toISOString(),
  overdueInvoices = [],
  readiness = null,
  previousReadiness = null,
  snapshotStatus = null,
  syncHealth = null,
  deadlines = [],
  operationalEvents = [],
  existingNotifications = []
} = {}) => {
  const existingConditions = new Set(
    (existingNotifications || [])
      .map((notification) => buildNotificationPayload(notification).condition_key)
      .filter(Boolean)
  );

  const notifications = dedupeNotifications([
    ...buildOverdueInvoiceNotifications({ now, overdueInvoices }),
    ...buildReadinessNotifications({ now, readiness, previousReadiness }),
    ...buildSnapshotNotifications({ now, snapshotStatus, readiness }),
    ...buildDeadlineNotifications({ now, deadlines }),
    ...buildSyncHealthNotifications({ now, syncHealth }),
    ...buildOperationalSignalNotifications({ events: operationalEvents })
  ], existingConditions);

  return {
    notifications,
    queue: notifications.filter((notification) => notification.delivery_status === 'queued'),
    health: summarizeNotificationHealth(notifications)
  };
};

module.exports = {
  PRIORITY_RANK,
  buildConditionKey,
  buildDeliveryQueue: (notifications = []) => ({
    items: sortNotifications(notifications.map(buildNotificationPayload)),
    health: summarizeNotificationHealth(notifications.map(buildNotificationPayload))
  }),
  buildLinkedTarget,
  buildNotificationEngine,
  buildNotificationPayload,
  compareNotificationPriority,
  dedupeNotifications,
  getPriorityRank,
  normalizeDeliveryStatus,
  normalizeSeverity,
  sortNotifications,
  summarizeNotificationHealth
};
