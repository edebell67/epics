const { randomUUID } = require('crypto');
const { isMonetaryItemType } = require('./monetaryIntegrityService');
const { quarterBoundsFromReference, recordSnapshotCreated } = require('./businessEventLogService');
const { buildAccountantReadyPackage } = require('./exportPackageBuilderService');
const { buildReadinessReport } = require('./readinessService');
const { sha256, stableStringify } = require('./quarterlyExportService');
const { assertQuarterAllowsMonetaryActivity } = require('./quarterLifecycleService');

const SNAPSHOT_ELIGIBLE_TYPES = ['invoice', 'receipt', 'payment', 'quote'];
const ACTIVE_CORRECTION_EVENT_STATUS = {
  entity_voided: 'voided',
  entity_superseded: 'superseded'
};
const ACTIVE_ITEM_STATUSES = ['confirmed', 'reconciled'];
const ADJUSTMENT_FIELDS = [
  'date',
  'entity_type',
  'merchant',
  'description',
  'amount',
  'net_amount',
  'vat_amount',
  'gross_amount',
  'vat_rate',
  'vat_type',
  'counterparty_reference'
];

class SnapshotVersioningError extends Error {
  constructor(message, statusCode = 409, details = {}) {
    super(message);
    this.name = 'SnapshotVersioningError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

const roundCurrency = (value) => Number(Number(value || 0).toFixed(2));

const asDateOnly = (value) => {
  if (!value) return null;
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString().slice(0, 10);
};

const normalizeMetadata = (value) => {
  if (!value) return {};
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch (error) {
      return {};
    }
  }
  if (typeof value === 'object') {
    return value;
  }
  return {};
};

const dedupeStrings = (values = []) => [...new Set(
  values
    .filter((value) => value !== undefined && value !== null && value !== '')
    .map((value) => String(value))
)];

const normalizeSnapshotTransaction = (row = {}) => ({
  txn_id: String(row.txn_id || row.id || ''),
  entity_type: row.entity_type || row.type || null,
  date: asDateOnly(row.date || row.transaction_date || row.captured_at || row.created_at),
  merchant: row.merchant || row.client_name || null,
  description: row.description || row.extracted_text || row.raw_note || null,
  amount: roundCurrency(row.amount),
  net_amount: roundCurrency(row.net_amount),
  vat_amount: roundCurrency(row.vat_amount),
  gross_amount: roundCurrency(row.gross_amount ?? row.amount),
  vat_rate: row.vat_rate ?? null,
  vat_type: row.vat_type || null,
  counterparty_reference: row.counterparty_reference || row.client_id || null,
  quarter_reference: row.quarter_reference || row.quarter_ref || null,
  status: row.status || row.effective_status || 'confirmed'
});

const mapSnapshotTransactionToReadinessInput = (row = {}) => ({
  id: row.txn_id,
  txn_id: row.txn_id,
  txn_date: row.date,
  date: row.date,
  merchant: row.merchant,
  amount: row.gross_amount ?? row.amount ?? 0,
  gross_amount: row.gross_amount ?? row.amount ?? 0,
  direction: isFinancialInflow(row) ? 'in' : 'out',
  category_code: row.category_code || null,
  business_personal: row.business_personal || null,
  is_split: row.is_split === true,
  split_business_pct: row.split_business_pct ?? null,
  duplicate_flag: row.duplicate_flag === true,
  duplicate_resolution: row.duplicate_resolution || null,
  status: row.status,
  vat_rate: row.vat_rate,
  vat_type: row.vat_type,
  net_amount: row.net_amount,
  quarter_reference: row.quarter_reference
});

const buildIntegrityWarningSummary = (metadata = {}, readinessReport = null) => {
  const explicitWarnings = Array.isArray(metadata.integrity_warning_summary)
    ? metadata.integrity_warning_summary
    : Array.isArray(metadata.warnings)
      ? metadata.warnings
      : metadata.integrity_warning_summary
        ? [metadata.integrity_warning_summary]
        : [];

  if (explicitWarnings.length > 0) {
    return dedupeStrings(explicitWarnings);
  }

  if (!Array.isArray(readinessReport?.issue_summary)) {
    return [];
  }

  return dedupeStrings(
    readinessReport.issue_summary.map((issue) => `${issue.label} (${issue.count})`)
  );
};

const buildSnapshotFileReferences = (exportPackage) => exportPackage.files.map((file) => ({
  name: file.name,
  sha256: file.sha256,
  bytes: file.bytes,
  content_type: file.content_type
}));

const resolveSnapshotReadiness = ({ metadata = {}, liveTransactions = [], quarterReference }) => {
  const providedReport = metadata.readiness_report && typeof metadata.readiness_report === 'object'
    ? metadata.readiness_report
    : null;

  const fallbackReport = buildReadinessReport({
    asOfDate: quarterBoundsFromReference(quarterReference).periodEnd,
    transactions: liveTransactions.map((row) => mapSnapshotTransactionToReadinessInput(row))
  });

  const readinessReport = providedReport || fallbackReport;
  const readinessScore = Number(
    metadata.readiness_score
    ?? metadata.readiness_pct
    ?? readinessReport.readiness_score
    ?? readinessReport.readiness_pct
    ?? 0
  );

  return {
    readiness_report: readinessReport,
    readiness_score: readinessScore,
    integrity_warning_summary: buildIntegrityWarningSummary(metadata, readinessReport)
  };
};

const isFinancialInflow = (row = {}) => row.entity_type === 'invoice';

const calculateSignedRevenue = (row = {}) => {
  const magnitude = row.gross_amount || row.amount || 0;
  return roundCurrency(isFinancialInflow(row) ? magnitude : magnitude * -1);
};

const calculateSignedVat = (row = {}) => {
  const magnitude = row.vat_amount || 0;
  return roundCurrency(isFinancialInflow(row) ? magnitude : magnitude * -1);
};

const hashTransactions = (rows = []) => sha256(stableStringify(
  rows
    .map((row) => normalizeSnapshotTransaction(row))
    .sort((left, right) => left.txn_id.localeCompare(right.txn_id))
));

const buildAdjustmentRecord = (previousRow, currentRow) => {
  const changedFields = ADJUSTMENT_FIELDS.filter(
    (field) => stableStringify(previousRow[field]) !== stableStringify(currentRow[field])
  );

  if (!changedFields.length) {
    return null;
  }

  return {
    txn_id: currentRow.txn_id,
    changed_fields: changedFields.sort(),
    previous_transaction: previousRow,
    current_transaction: currentRow,
    revenue_impact: roundCurrency(calculateSignedRevenue(currentRow) - calculateSignedRevenue(previousRow)),
    vat_impact: roundCurrency(calculateSignedVat(currentRow) - calculateSignedVat(previousRow))
  };
};

const summarizeImpact = (rows = [], key) => roundCurrency(
  rows.reduce((total, row) => total + Number(row[key] || 0), 0)
);

const buildSnapshotVersionDiff = (previousRows = [], currentRows = [], options = {}) => {
  const previous = previousRows
    .map((row) => normalizeSnapshotTransaction(row))
    .filter((row) => row.txn_id);
  const current = currentRows
    .map((row) => normalizeSnapshotTransaction(row))
    .filter((row) => row.txn_id);

  const previousMap = new Map(previous.map((row) => [row.txn_id, row]));
  const currentMap = new Map(current.map((row) => [row.txn_id, row]));
  const currentById = new Map((options.currentAllRows || currentRows)
    .map((row) => normalizeSnapshotTransaction(row))
    .filter((row) => row.txn_id)
    .map((row) => [row.txn_id, row]));

  const addedTransactions = [];
  const voidedTransactions = [];
  const adjustments = [];

  for (const [txnId, currentRow] of currentMap.entries()) {
    if (!previousMap.has(txnId)) {
      addedTransactions.push({
        ...currentRow,
        revenue_impact: calculateSignedRevenue(currentRow),
        vat_impact: calculateSignedVat(currentRow)
      });
      continue;
    }

    const adjustment = buildAdjustmentRecord(previousMap.get(txnId), currentRow);
    if (adjustment) {
      adjustments.push(adjustment);
    }
  }

  for (const [txnId, previousRow] of previousMap.entries()) {
    if (currentMap.has(txnId)) {
      continue;
    }

    const currentVersion = currentById.get(txnId);
    voidedTransactions.push({
      ...previousRow,
      status: currentVersion?.status || 'removed',
      revenue_impact: roundCurrency(calculateSignedRevenue(previousRow) * -1),
      vat_impact: roundCurrency(calculateSignedVat(previousRow) * -1)
    });
  }

  addedTransactions.sort((left, right) => left.txn_id.localeCompare(right.txn_id));
  voidedTransactions.sort((left, right) => left.txn_id.localeCompare(right.txn_id));
  adjustments.sort((left, right) => left.txn_id.localeCompare(right.txn_id));

  const revenueImpact = roundCurrency(
    summarizeImpact(addedTransactions, 'revenue_impact')
    + summarizeImpact(voidedTransactions, 'revenue_impact')
    + summarizeImpact(adjustments, 'revenue_impact')
  );
  const vatImpact = roundCurrency(
    summarizeImpact(addedTransactions, 'vat_impact')
    + summarizeImpact(voidedTransactions, 'vat_impact')
    + summarizeImpact(adjustments, 'vat_impact')
  );

  return {
    added_transactions: addedTransactions,
    voided_transactions: voidedTransactions,
    adjustments,
    revenue_impact: revenueImpact,
    vat_impact: vatImpact,
    changed_since_snapshot: addedTransactions.length > 0 || voidedTransactions.length > 0 || adjustments.length > 0,
    current_dataset_hash: hashTransactions(current),
    previous_dataset_hash: hashTransactions(previous)
  };
};

const aggregateSnapshotTotals = (rows = []) => rows.reduce((totals, row) => ({
  net_amount: roundCurrency(totals.net_amount + Number(row.net_amount || 0)),
  vat_amount: roundCurrency(totals.vat_amount + Number(row.vat_amount || 0)),
  gross_amount: roundCurrency(totals.gross_amount + Number(row.gross_amount || row.amount || 0))
}), {
  net_amount: 0,
  vat_amount: 0,
  gross_amount: 0
});

const aggregateVatTotals = (rows = []) => {
  const totals = {
    total_vat: 0,
    by_rate: {},
    by_type: {}
  };

  rows.forEach((row) => {
    const vatAmount = roundCurrency(row.vat_amount);
    totals.total_vat = roundCurrency(totals.total_vat + vatAmount);

    const rateKey = row.vat_rate === null || row.vat_rate === undefined ? 'unknown' : String(row.vat_rate);
    const typeKey = row.vat_type || 'unknown';
    totals.by_rate[rateKey] = roundCurrency((totals.by_rate[rateKey] || 0) + vatAmount);
    totals.by_type[typeKey] = roundCurrency((totals.by_type[typeKey] || 0) + vatAmount);
  });

  return totals;
};

const buildSnapshotSummary = (rows = [], diff) => ({
  transaction_count: rows.length,
  included_transaction_ids: rows.map((row) => row.txn_id),
  totals: aggregateSnapshotTotals(rows),
  vat_totals: aggregateVatTotals(rows),
  diff_summary: {
    added_transactions: diff.added_transactions,
    voided_transactions: diff.voided_transactions,
    adjustments: diff.adjustments,
    revenue_impact: diff.revenue_impact,
    vat_impact: diff.vat_impact,
    changed_since_snapshot: diff.changed_since_snapshot
  },
  snapshot_base_hash: diff.current_dataset_hash
});

const fetchLatestSnapshotRecord = async (executor, { userId, quarterReference }) => {
  const result = await executor.query(
    `
    SELECT
      event_id,
      entity_id AS snapshot_id,
      created_at,
      actor_id,
      source_type,
      description,
      quarter_reference,
      metadata
    FROM business_event_log
    WHERE user_id = $1
      AND quarter_reference = $2
      AND event_type = 'snapshot_created'
    ORDER BY created_at DESC, event_id DESC
    LIMIT 1
    `,
    [userId, quarterReference]
  );

  if (!result.rows.length) {
    return null;
  }

  const row = result.rows[0];
  const metadata = normalizeMetadata(row.metadata);
  const snapshot = metadata.snapshot && typeof metadata.snapshot === 'object'
    ? metadata.snapshot
    : metadata;

  return {
    snapshot_id: row.snapshot_id,
    event_id: row.event_id,
    created_at: row.created_at,
    actor_id: row.actor_id,
    source_type: row.source_type,
    description: row.description,
    quarter_reference: row.quarter_reference,
    version_number: Number(snapshot.version_number || 1),
    transactions: Array.isArray(snapshot.transactions) ? snapshot.transactions : [],
    metadata: snapshot
  };
};

const listQuarterTransactions = async (executor, { userId, quarterReference }) => {
  const result = await executor.query(
    `
    SELECT
      ci.id,
      ci.type,
      ci.status,
      ci.amount,
      ci.net_amount,
      ci.vat_amount,
      ci.gross_amount,
      ci.vat_rate,
      ci.vat_type,
      ci.quarter_ref,
      ci.client_id,
      c.name AS client_name,
      ci.extracted_text,
      ci.raw_note,
      COALESCE(ci.captured_at, ci.due_date, ci.created_at) AS transaction_date,
      correction.event_type AS correction_event_type
    FROM capture_items ci
    LEFT JOIN clients c
      ON c.id = ci.client_id
    LEFT JOIN LATERAL (
      SELECT bel.event_type
      FROM business_event_log bel
      WHERE bel.user_id = ci.user_id
        AND bel.entity_id = ci.id
        AND bel.event_type IN ('entity_voided', 'entity_superseded')
      ORDER BY bel.created_at DESC, bel.event_id DESC
      LIMIT 1
    ) correction ON TRUE
    WHERE ci.user_id = $1
      AND ci.quarter_ref = $2
      AND ci.deleted_at IS NULL
      AND ci.type = ANY($3)
      AND ci.status = ANY($4)
    ORDER BY ci.id ASC
    `,
    [userId, quarterReference, SNAPSHOT_ELIGIBLE_TYPES, ACTIVE_ITEM_STATUSES]
  );

  return result.rows
    .filter((row) => isMonetaryItemType(row.type))
    .map((row) => ({
      txn_id: row.id,
      entity_type: row.type,
      date: row.transaction_date,
      merchant: row.client_name || null,
      description: row.extracted_text || row.raw_note || null,
      amount: row.amount,
      net_amount: row.net_amount,
      vat_amount: row.vat_amount,
      gross_amount: row.gross_amount,
      vat_rate: row.vat_rate,
      vat_type: row.vat_type,
      counterparty_reference: row.client_id,
      quarter_reference: row.quarter_ref,
      status: ACTIVE_CORRECTION_EVENT_STATUS[row.correction_event_type] || row.status
    }));
};

const getQuarterSnapshotStatus = async (executor, { userId, quarterReference }) => {
  const [latestSnapshot, allCurrentRows] = await Promise.all([
    fetchLatestSnapshotRecord(executor, { userId, quarterReference }),
    listQuarterTransactions(executor, { userId, quarterReference })
  ]);

  const activeCurrentRows = allCurrentRows.filter((row) => !['voided', 'superseded'].includes(row.status));
  const previousRows = latestSnapshot?.transactions || [];
  const diff = buildSnapshotVersionDiff(previousRows, activeCurrentRows, { currentAllRows: allCurrentRows });
  const nextVersionNumber = latestSnapshot ? latestSnapshot.version_number + 1 : 1;
  const canCreateSnapshotVersion = !latestSnapshot || diff.changed_since_snapshot;

  return {
    quarter_reference: quarterReference,
    latest_snapshot: latestSnapshot
      ? {
          snapshot_id: latestSnapshot.snapshot_id,
          version_number: latestSnapshot.version_number,
          created_at: latestSnapshot.created_at,
          description: latestSnapshot.description
        }
      : null,
    baseline_exists: Boolean(latestSnapshot),
    changed_since_snapshot: Boolean(latestSnapshot) && diff.changed_since_snapshot,
    can_create_snapshot_version: canCreateSnapshotVersion,
    next_version_number: nextVersionNumber,
    no_change_reason: canCreateSnapshotVersion || !latestSnapshot
      ? null
      : `No changes since Snapshot ${String(latestSnapshot.version_number).padStart(3, '0')} for ${quarterReference}.`,
    diff,
    live_transactions: activeCurrentRows
  };
};

const createQuarterSnapshotVersion = async (executor, {
  user_id,
  actor_id,
  source_type,
  quarter_reference,
  description = 'Quarter snapshot generated',
  metadata = {}
}) => {
  await assertQuarterAllowsMonetaryActivity(executor, {
    userId: user_id,
    quarterReference: quarter_reference,
    operation: 'Snapshot creation',
    entityType: 'snapshot'
  });

  const snapshotStatus = await getQuarterSnapshotStatus(executor, {
    userId: user_id,
    quarterReference: quarter_reference
  });

  if (!snapshotStatus.can_create_snapshot_version) {
    throw new SnapshotVersioningError(
      snapshotStatus.no_change_reason || `No changes since the last snapshot for ${quarter_reference}.`,
      409,
      snapshotStatus
    );
  }

  const summary = buildSnapshotSummary(snapshotStatus.live_transactions, snapshotStatus.diff);
  const snapshotId = randomUUID();
  const createdAt = new Date().toISOString();
  const includedPeriod = quarterBoundsFromReference(quarter_reference);
  const readinessState = resolveSnapshotReadiness({
    metadata,
    liveTransactions: snapshotStatus.live_transactions,
    quarterReference: quarter_reference
  });

  const provisionalSnapshotRecord = {
    ...metadata,
    snapshot_id: snapshotId,
    unique_id: snapshotId,
    entity_type: 'snapshot',
    transaction_date: includedPeriod.periodEnd,
    created_at: createdAt,
    created_by: actor_id,
    quarter_reference,
    quarter_label: quarter_reference,
    description,
    status: 'generated',
    commit_mode: 'manual',
    source_type,
    version_number: snapshotStatus.next_version_number,
    previous_snapshot_id: snapshotStatus.latest_snapshot?.snapshot_id || null,
    previous_snapshot_version_number: snapshotStatus.latest_snapshot?.version_number || null,
    changed_since_snapshot: snapshotStatus.changed_since_snapshot,
    transactions: snapshotStatus.live_transactions,
    transaction_ids: summary.included_transaction_ids,
    included_transaction_ids: summary.included_transaction_ids,
    totals: summary.totals,
    vat_totals: summary.vat_totals,
    readiness_score: readinessState.readiness_score,
    readiness_pct: readinessState.readiness_score,
    readiness_report: readinessState.readiness_report,
    integrity_warning_summary: readinessState.integrity_warning_summary,
    warning_count: readinessState.integrity_warning_summary.length,
    files_generated: [],
    generated_files: [],
    included_period: {
      start: includedPeriod.periodStart,
      end: includedPeriod.periodEnd
    },
    export_filename: null,
    package_checksum: null,
    ...summary
  };
  provisionalSnapshotRecord.checksum = sha256(stableStringify(provisionalSnapshotRecord));

  const exportPackage = buildAccountantReadyPackage(provisionalSnapshotRecord);
  const fileReferences = buildSnapshotFileReferences(exportPackage);
  const snapshotRecord = {
    ...provisionalSnapshotRecord,
    files_generated: fileReferences,
    generated_files: fileReferences,
    export_filename: exportPackage.filename,
    package_checksum: exportPackage.manifest.package_checksum
  };
  snapshotRecord.checksum = sha256(stableStringify(snapshotRecord));

  const snapshotMetadata = {
    snapshot: snapshotRecord,
    snapshot_id: snapshotRecord.snapshot_id,
    unique_id: snapshotRecord.unique_id,
    quarter_reference: snapshotRecord.quarter_reference,
    quarter_label: snapshotRecord.quarter_label,
    version_number: snapshotRecord.version_number,
    previous_snapshot_id: snapshotRecord.previous_snapshot_id,
    previous_snapshot_version_number: snapshotRecord.previous_snapshot_version_number,
    changed_since_snapshot: snapshotRecord.changed_since_snapshot,
    created_at: snapshotRecord.created_at,
    created_by: snapshotRecord.created_by,
    transaction_ids: snapshotRecord.transaction_ids,
    included_transaction_ids: snapshotRecord.included_transaction_ids,
    totals: snapshotRecord.totals,
    vat_totals: snapshotRecord.vat_totals,
    readiness_score: snapshotRecord.readiness_score,
    readiness_pct: snapshotRecord.readiness_pct,
    readiness_report: snapshotRecord.readiness_report,
    integrity_warning_summary: snapshotRecord.integrity_warning_summary,
    files_generated: snapshotRecord.files_generated,
    generated_files: snapshotRecord.generated_files,
    checksum: snapshotRecord.checksum,
    export_filename: snapshotRecord.export_filename,
    package_checksum: snapshotRecord.package_checksum
  };

  const event = await recordSnapshotCreated(executor, {
    user_id,
    actor_id,
    source_type,
    quarter_reference,
    snapshot_id: snapshotId,
    created_at: createdAt,
    description,
    metadata: snapshotMetadata
  });

  return {
    ...event,
    snapshot_id: snapshotRecord.snapshot_id,
    version_number: snapshotMetadata.version_number,
    changed_since_snapshot: snapshotMetadata.changed_since_snapshot,
    diff: snapshotStatus.diff,
    snapshot_summary: summary,
    snapshot_record: snapshotRecord
  };
};

module.exports = {
  ACTIVE_ITEM_STATUSES,
  SNAPSHOT_ELIGIBLE_TYPES,
  SnapshotVersioningError,
  buildSnapshotVersionDiff,
  createQuarterSnapshotVersion,
  fetchLatestSnapshotRecord,
  getQuarterSnapshotStatus,
  hashTransactions,
  listQuarterTransactions,
  normalizeSnapshotTransaction
};
