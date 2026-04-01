const { createHash } = require('crypto');

const csvEscape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;

const asDateOnly = (value) => {
  if (!value) return '';
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return String(value).slice(0, 10);
};

const asIsoDateTime = (value) => {
  if (!value) return '';
  return new Date(value).toISOString();
};

const sha256 = (value) => createHash('sha256')
  .update(Buffer.isBuffer(value) ? value : Buffer.from(String(value), 'utf8'))
  .digest('hex');

const stableStringify = (value) => {
  if (Array.isArray(value)) {
    return `[${value.map((entry) => stableStringify(entry)).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
};

const buildTransactionsCsv = (rows = []) => {
  const header = [
    'txn_id', 'date', 'merchant', 'amount', 'direction', 'category_code', 'category_name', 'confidence',
    'business_personal', 'is_split', 'split_business_pct', 'matched_evidence_ids', 'bank_account_id', 'bank_txn_ref'
  ];
  const body = rows.map((row) => ([
    row.txn_id,
    asDateOnly(row.date),
    csvEscape(row.merchant),
    row.amount,
    row.direction,
    row.category_code || '',
    csvEscape(row.category_name),
    Number(row.confidence || 0).toFixed(3),
    row.business_personal || '',
    row.is_split === true,
    row.split_business_pct ?? '',
    csvEscape(row.matched_evidence_ids || ''),
    row.bank_account_id,
    row.bank_txn_ref
  ].join(',')));
  return [header.join(',')].concat(body).join('\n');
};

const buildEvidenceCsv = (rows = []) => {
  const header = ['evidence_id', 'type', 'captured_at', 'doc_date', 'merchant', 'amount', 'storage_link', 'extraction_confidence', 'matched_bank_txn_id', 'user_confirmed'];
  const body = rows.map((row) => ([
    row.evidence_id,
    row.type,
    asIsoDateTime(row.captured_at),
    row.doc_date || '',
    csvEscape(row.merchant),
    row.amount ?? '',
    csvEscape(row.storage_link),
    Number(row.extraction_confidence || 0).toFixed(3),
    row.matched_bank_txn_id || '',
    row.user_confirmed === true
  ].join(',')));
  return [header.join(',')].concat(body).join('\n');
};

const buildSummaryCsv = (rows = []) => {
  const header = ['period_start', 'period_end', 'category_code', 'category_name', 'total_in', 'total_out', 'count', 'unresolved_count'];
  const body = rows.map((row) => ([
    asDateOnly(row.period_start),
    asDateOnly(row.period_end),
    row.category_code || '',
    csvEscape(row.category_name),
    row.total_in || 0,
    row.total_out || 0,
    row.count || 0,
    row.unresolved_count || 0
  ].join(',')));
  return [header.join(',')].concat(body).join('\n');
};

const comparableSnapshotRow = (row = {}) => ({
  txn_id: row.txn_id,
  date: asDateOnly(row.date),
  merchant: row.merchant || null,
  amount: row.amount ?? null,
  direction: row.direction || null,
  category_code: row.category_code || null,
  business_personal: row.business_personal || null,
  is_split: row.is_split === true,
  split_business_pct: row.split_business_pct ?? null
});

const buildSnapshotDiff = (previousRows = [], nextRows = []) => {
  const previous = new Map(previousRows.map((row) => [String(row.txn_id), comparableSnapshotRow(row)]));
  const next = new Map(nextRows.map((row) => [String(row.txn_id), comparableSnapshotRow(row)]));

  const added = [];
  const removed = [];
  const changed = [];
  let unchangedCount = 0;

  for (const [txnId, currentRow] of next.entries()) {
    if (!previous.has(txnId)) {
      added.push(txnId);
      continue;
    }

    const previousRow = previous.get(txnId);
    const changedFields = Object.keys(currentRow).filter((field) => stableStringify(previousRow[field]) !== stableStringify(currentRow[field]));
    if (changedFields.length > 0) {
      changed.push({ txn_id: txnId, changed_fields: changedFields.sort() });
    } else {
      unchangedCount += 1;
    }
  }

  for (const txnId of previous.keys()) {
    if (!next.has(txnId)) {
      removed.push(txnId);
    }
  }

  return {
    added: added.sort(),
    removed: removed.sort(),
    changed: changed.sort((left, right) => left.txn_id.localeCompare(right.txn_id)),
    unchanged_count: unchangedCount
  };
};

const buildQuarterlyPackArtifacts = ({
  periodStart,
  periodEnd,
  transactions = [],
  evidenceRows = [],
  summaryRows = [],
  previousSnapshotRows = [],
  nextSnapshotRows = transactions
}) => {
  const transactionsCsv = buildTransactionsCsv(transactions);
  const evidenceCsv = buildEvidenceCsv(evidenceRows);
  const summaryCsv = buildSummaryCsv(summaryRows);
  const snapshotDiff = buildSnapshotDiff(previousSnapshotRows, nextSnapshotRows);
  const manifest = {
    period_start: periodStart,
    period_end: periodEnd,
    file_checksums: {
      Transactions_csv: sha256(transactionsCsv),
      EvidenceIndex_csv: sha256(evidenceCsv),
      QuarterlySummary_csv: sha256(summaryCsv)
    },
    counts: {
      transactions: transactions.length,
      evidence: evidenceRows.length,
      summary_rows: summaryRows.length
    },
    snapshot_diff: snapshotDiff
  };
  manifest.pack_checksum = sha256(stableStringify(manifest.file_checksums) + stableStringify(manifest.counts) + stableStringify(snapshotDiff));

  return {
    transactionsCsv,
    evidenceCsv,
    summaryCsv,
    manifest,
    manifestJson: `${JSON.stringify(manifest, null, 2)}\n`
  };
};

module.exports = {
  buildEvidenceCsv,
  buildQuarterlyPackArtifacts,
  buildSnapshotDiff,
  buildSummaryCsv,
  buildTransactionsCsv,
  csvEscape,
  sha256,
  stableStringify
};
