const { createHash } = require('crypto');

const {
  canonicalSchemas,
  validateEntityPayload
} = require('./canonicalSchemaService');
const {
  CANONICAL_EXPORT_FIELDS,
  buildCompatibilityArtifacts
} = require('./exportCompatibilityService');

const STRUCTURED_EXPORT_FIELDS = CANONICAL_EXPORT_FIELDS;

const STRUCTURED_EXPORT_COLUMNS = STRUCTURED_EXPORT_FIELDS.map(
  (field) => canonicalSchemas.field_dictionary[field].export_column
);

const DECIMAL_FIELDS = new Set(['net_amount', 'vat_amount', 'gross_amount', 'vat_rate']);

const isPresent = (value) => value !== undefined && value !== null && value !== '';

const stableSortObject = (value) => {
  if (Array.isArray(value)) {
    return value.map(stableSortObject);
  }
  if (!value || typeof value !== 'object') {
    return value;
  }

  return Object.keys(value)
    .sort()
    .reduce((acc, key) => {
      acc[key] = stableSortObject(value[key]);
      return acc;
    }, {});
};

const stableStringify = (value, spacing = 2) => JSON.stringify(stableSortObject(value), null, spacing);

const hashContent = (value) => createHash('sha256').update(value).digest('hex');

const toIsoDate = (value) => {
  if (!isPresent(value)) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toISOString().slice(0, 10);
};

const toIsoTimestamp = (value) => {
  if (!isPresent(value)) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toISOString();
};

const toFixedNumber = (value, digits = 2) => {
  if (!isPresent(value)) {
    return '';
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  return numeric.toFixed(digits);
};

const csvEscape = (value) => {
  const stringValue = value === undefined || value === null ? '' : String(value);
  if (!/[",\n]/.test(stringValue)) {
    return stringValue;
  }
  return `"${stringValue.replace(/"/g, '""')}"`;
};

const buildSimplePdf = (lines) => {
  const safe = lines.map((line) => String(line).replace(/[()\\]/g, ''));
  const text = safe.map((line, index) => `BT 40 ${760 - index * 16} Td (${line}) Tj`).join('\n');
  const stream = `BT /F1 12 Tf\n${text}\nET`;
  const objects = [];
  objects.push('1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj');
  objects.push('2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj');
  objects.push('3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj');
  objects.push(`4 0 obj << /Length ${stream.length} >> stream\n${stream}\nendstream endobj`);
  objects.push('5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj');

  let body = '%PDF-1.4\n';
  const offsets = [0];
  for (const obj of objects) {
    offsets.push(body.length);
    body += `${obj}\n`;
  }
  const xrefStart = body.length;
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let index = 1; index <= objects.length; index += 1) {
    body += `${String(offsets[index]).padStart(10, '0')} 00000 n \n`;
  }
  body += `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;
  return Buffer.from(body, 'utf8');
};

const aggregateSnapshotTotals = (transactions) => transactions.reduce((acc, transaction) => {
  acc.net_amount += Number(transaction.net_amount || 0);
  acc.vat_amount += Number(transaction.vat_amount || 0);
  acc.gross_amount += Number(transaction.gross_amount || 0);
  return acc;
}, {
  net_amount: 0,
  vat_amount: 0,
  gross_amount: 0
});

const aggregateVatTotals = (transactions) => transactions.reduce((acc, transaction) => {
  const vatAmount = Number(transaction.vat_amount || 0);
  const vatRate = isPresent(transaction.vat_rate) ? toFixedNumber(transaction.vat_rate) : '0.00';
  const vatType = transaction.vat_type || 'outside_scope';

  acc.total_vat += vatAmount;
  acc.by_rate[vatRate] = Number((Number(acc.by_rate[vatRate] || 0) + vatAmount).toFixed(2));
  acc.by_type[vatType] = Number((Number(acc.by_type[vatType] || 0) + vatAmount).toFixed(2));
  return acc;
}, {
  total_vat: 0,
  by_rate: {},
  by_type: {}
});

const normalizeIntegrityWarnings = (value) => {
  if (!value) {
    return [];
  }
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === 'string' ? item : stableStringify(item, 0)));
  }
  if (typeof value === 'string') {
    return [value];
  }
  return [stableStringify(value, 0)];
};

const normalizeTransactionRecord = (transaction, snapshotRecord) => ({
  unique_id: transaction.unique_id || transaction.id || transaction.record_id,
  entity_type: transaction.entity_type || transaction.type,
  transaction_date: transaction.transaction_date || transaction.date,
  created_at: transaction.created_at || snapshotRecord.created_at,
  created_by: transaction.created_by || snapshotRecord.created_by,
  quarter_reference: transaction.quarter_reference || transaction.quarter_label || snapshotRecord.quarter_reference,
  counterparty_reference: transaction.counterparty_reference || transaction.counterparty_name || transaction.client_name || transaction.merchant || '',
  description: transaction.description || transaction.note || transaction.raw_note || '',
  category: transaction.category || transaction.category_name || transaction.category_code || '',
  net_amount: transaction.net_amount,
  vat_amount: transaction.vat_amount,
  gross_amount: transaction.gross_amount,
  vat_rate: transaction.vat_rate,
  vat_type: transaction.vat_type,
  status: transaction.status || 'committed',
  commit_mode: transaction.commit_mode || 'manual',
  source_type: transaction.source_type || snapshotRecord.source_type || 'system'
});

const normalizeSnapshotRecord = (snapshotRecord) => {
  if (!snapshotRecord || typeof snapshotRecord !== 'object') {
    throw new Error('Snapshot payload is required.');
  }

  const rawTransactions = Array.isArray(snapshotRecord.transactions)
    ? snapshotRecord.transactions
    : Array.isArray(snapshotRecord.records)
      ? snapshotRecord.records
      : [];

  const normalized = {
    unique_id: snapshotRecord.unique_id || snapshotRecord.snapshot_id || snapshotRecord.id,
    entity_type: 'snapshot',
    transaction_date: snapshotRecord.transaction_date
      || snapshotRecord.period_end
      || snapshotRecord.included_period?.end
      || snapshotRecord.created_at,
    created_at: toIsoTimestamp(snapshotRecord.created_at),
    created_by: snapshotRecord.created_by,
    quarter_reference: snapshotRecord.quarter_reference || snapshotRecord.quarter_label,
    description: snapshotRecord.description || 'Quarter snapshot generated',
    status: snapshotRecord.status || 'generated',
    commit_mode: snapshotRecord.commit_mode || 'manual',
    source_type: snapshotRecord.source_type || 'system',
    version_number: Number(snapshotRecord.version_number || 1),
    transactions: rawTransactions,
    included_transaction_ids: snapshotRecord.included_transaction_ids
      || snapshotRecord.transaction_ids
      || rawTransactions.map((transaction) => transaction.unique_id || transaction.id || transaction.record_id).filter(Boolean),
    totals: snapshotRecord.totals || null,
    vat_totals: snapshotRecord.vat_totals || null,
    readiness_score: Number(
      snapshotRecord.readiness_score
      ?? snapshotRecord.readiness_pct
      ?? snapshotRecord.readiness_report?.readiness_pct
      ?? 0
    ),
    integrity_warning_summary: normalizeIntegrityWarnings(snapshotRecord.integrity_warning_summary),
    generated_files: Array.isArray(snapshotRecord.generated_files)
      ? snapshotRecord.generated_files
      : Array.isArray(snapshotRecord.files_generated)
        ? snapshotRecord.files_generated
        : [],
    checksum: snapshotRecord.checksum || null,
    notes: snapshotRecord.notes || null
  };

  if (!normalized.unique_id) {
    throw new Error('Snapshot unique_id is required.');
  }
  if (!normalized.created_by) {
    throw new Error('Snapshot created_by is required.');
  }
  if (!normalized.quarter_reference) {
    throw new Error('Snapshot quarter_reference is required.');
  }
  if (!rawTransactions.length) {
    throw new Error('Snapshot transactions are required to build the export package.');
  }

  const snapshotValidation = validateEntityPayload('snapshot', {
    unique_id: normalized.unique_id,
    entity_type: normalized.entity_type,
    transaction_date: normalized.transaction_date,
    created_at: normalized.created_at,
    created_by: normalized.created_by,
    quarter_reference: normalized.quarter_reference,
    description: normalized.description,
    status: normalized.status,
    commit_mode: normalized.commit_mode,
    source_type: normalized.source_type,
    version_number: normalized.version_number,
    included_transaction_ids: normalized.included_transaction_ids,
    totals: normalized.totals || {},
    vat_totals: normalized.vat_totals || {},
    readiness_score: normalized.readiness_score,
    integrity_warning_summary: normalized.integrity_warning_summary,
    generated_files: normalized.generated_files
  });

  if (!snapshotValidation.valid) {
    throw new Error(`Invalid snapshot payload: ${snapshotValidation.errors.join('; ')}`);
  }

  normalized.transactions = rawTransactions.map((transaction) => normalizeTransactionRecord(transaction, normalized));
  normalized.totals = normalized.totals || aggregateSnapshotTotals(normalized.transactions);
  normalized.vat_totals = normalized.vat_totals || aggregateVatTotals(normalized.transactions);

  return normalized;
};

const buildStructuredCsv = (snapshotRecord) => {
  const rows = [STRUCTURED_EXPORT_COLUMNS.join(',')];

  snapshotRecord.transactions.forEach((transaction) => {
    const row = STRUCTURED_EXPORT_FIELDS.map((field) => {
      let value = transaction[field];
      if (field === 'transaction_date') {
        value = toIsoDate(value);
      } else if (field === 'created_at') {
        value = toIsoTimestamp(value);
      } else if (DECIMAL_FIELDS.has(field)) {
        value = field === 'vat_rate' ? toFixedNumber(value, 2) : toFixedNumber(value, 2);
      }
      return csvEscape(value);
    });
    rows.push(row.join(','));
  });

  return Buffer.from(`${rows.join('\n')}\n`, 'utf8');
};

const compareRounded = (left, right) => Number(Number(left || 0).toFixed(2)) === Number(Number(right || 0).toFixed(2));

const buildIntegrityReport = (snapshotRecord) => {
  const invalidRecords = snapshotRecord.transactions
    .map((transaction) => ({
      record_id: transaction.unique_id,
      entity_type: transaction.entity_type,
      validation: validateEntityPayload(transaction.entity_type, transaction)
    }))
    .filter((entry) => !entry.validation.valid)
    .map((entry) => ({
      record_id: entry.record_id,
      entity_type: entry.entity_type,
      errors: entry.validation.errors
    }));

  const duplicateRecordIds = [];
  const seenIds = new Set();
  snapshotRecord.transactions.forEach((transaction) => {
    if (seenIds.has(transaction.unique_id)) {
      duplicateRecordIds.push(transaction.unique_id);
    }
    seenIds.add(transaction.unique_id);
  });

  const computedTotals = aggregateSnapshotTotals(snapshotRecord.transactions);
  const computedVatTotals = aggregateVatTotals(snapshotRecord.transactions);

  return {
    snapshot_id: snapshotRecord.unique_id,
    version_number: snapshotRecord.version_number,
    quarter_label: snapshotRecord.quarter_reference,
    readiness_score: snapshotRecord.readiness_score,
    warnings: snapshotRecord.integrity_warning_summary,
    transaction_count: snapshotRecord.transactions.length,
    duplicate_record_ids: duplicateRecordIds,
    invalid_records: invalidRecords,
    checks: {
      canonical_columns: STRUCTURED_EXPORT_COLUMNS,
      totals_match: {
        net_amount: compareRounded(snapshotRecord.totals.net_amount, computedTotals.net_amount),
        vat_amount: compareRounded(snapshotRecord.totals.vat_amount, computedTotals.vat_amount),
        gross_amount: compareRounded(snapshotRecord.totals.gross_amount, computedTotals.gross_amount)
      },
      vat_totals_match: compareRounded(snapshotRecord.vat_totals.total_vat, computedVatTotals.total_vat)
    },
    declared_totals: {
      net_amount: Number(Number(snapshotRecord.totals.net_amount || 0).toFixed(2)),
      vat_amount: Number(Number(snapshotRecord.totals.vat_amount || 0).toFixed(2)),
      gross_amount: Number(Number(snapshotRecord.totals.gross_amount || 0).toFixed(2))
    },
    computed_totals: {
      net_amount: Number(computedTotals.net_amount.toFixed(2)),
      vat_amount: Number(computedTotals.vat_amount.toFixed(2)),
      gross_amount: Number(computedTotals.gross_amount.toFixed(2))
    },
    declared_vat_totals: stableSortObject(snapshotRecord.vat_totals),
    computed_vat_totals: stableSortObject({
      total_vat: Number(computedVatTotals.total_vat.toFixed(2)),
      by_rate: computedVatTotals.by_rate,
      by_type: computedVatTotals.by_type
    })
  };
};

const buildVatSummaryPdf = (snapshotRecord) => {
  const lines = [
    'VAT Summary Document',
    `Quarter: ${snapshotRecord.quarter_reference}`,
    `Snapshot: ${snapshotRecord.unique_id}`,
    `Version: ${String(snapshotRecord.version_number).padStart(3, '0')}`,
    `Readiness score: ${snapshotRecord.readiness_score}`,
    `Transactions: ${snapshotRecord.transactions.length}`,
    `Net total: GBP ${toFixedNumber(snapshotRecord.totals.net_amount)}`,
    `VAT total: GBP ${toFixedNumber(snapshotRecord.vat_totals.total_vat)}`,
    `Gross total: GBP ${toFixedNumber(snapshotRecord.totals.gross_amount)}`
  ];

  Object.entries(snapshotRecord.vat_totals.by_rate || {})
    .sort(([left], [right]) => left.localeCompare(right))
    .forEach(([rate, total]) => {
      lines.push(`VAT rate ${rate}%: GBP ${toFixedNumber(total)}`);
    });

  return buildSimplePdf(lines);
};

const buildSnapshotMetadata = (snapshotRecord, generatedFiles) => ({
  snapshot_id: snapshotRecord.unique_id,
  version_number: snapshotRecord.version_number,
  quarter_label: snapshotRecord.quarter_reference,
  created_at: snapshotRecord.created_at,
  created_by: snapshotRecord.created_by,
  transaction_count: snapshotRecord.transactions.length,
  included_transaction_ids: snapshotRecord.included_transaction_ids,
  totals: {
    net_amount: Number(Number(snapshotRecord.totals.net_amount || 0).toFixed(2)),
    vat_amount: Number(Number(snapshotRecord.totals.vat_amount || 0).toFixed(2)),
    gross_amount: Number(Number(snapshotRecord.totals.gross_amount || 0).toFixed(2))
  },
  vat_totals: stableSortObject(snapshotRecord.vat_totals),
  readiness_score: snapshotRecord.readiness_score,
  integrity_warning_summary: snapshotRecord.integrity_warning_summary,
  generated_files: generatedFiles,
  files_generated: generatedFiles,
  checksum: snapshotRecord.checksum || null,
  schema_version: canonicalSchemas.schema_version,
  compatibility_validation_file: 'compatibility_validation.json'
});

const buildAccountantReadyPackage = (inputSnapshot) => {
  const snapshotRecord = normalizeSnapshotRecord(inputSnapshot);
  const structuredCsv = buildStructuredCsv(snapshotRecord);
  const integrityReport = buildIntegrityReport(snapshotRecord);
  const compatibilityArtifacts = buildCompatibilityArtifacts(snapshotRecord);
  const integrityReportBuffer = Buffer.from(`${stableStringify(integrityReport)}\n`, 'utf8');
  const vatSummaryDocument = buildVatSummaryPdf(snapshotRecord);

  const files = [
    {
      name: 'integrity_report.json',
      content: integrityReportBuffer,
      content_type: 'application/json'
    },
    {
      name: 'structured_csv.csv',
      content: structuredCsv,
      content_type: 'text/csv'
    },
    {
      name: 'vat_summary_document.pdf',
      content: vatSummaryDocument,
      content_type: 'application/pdf'
    },
    ...compatibilityArtifacts.files
  ];

  const generatedFiles = files
    .slice()
    .sort((left, right) => left.name.localeCompare(right.name))
    .map((file) => ({
      name: file.name,
      sha256: hashContent(file.content),
      bytes: file.content.length,
      content_type: file.content_type
    }));

  const snapshotMetadata = buildSnapshotMetadata(snapshotRecord, generatedFiles);
  const snapshotMetadataBuffer = Buffer.from(`${stableStringify(snapshotMetadata)}\n`, 'utf8');
  files.push({
    name: 'snapshot_metadata.json',
    content: snapshotMetadataBuffer,
    content_type: 'application/json'
  });

  const packageManifest = {
    snapshot_id: snapshotRecord.unique_id,
    quarter_label: snapshotRecord.quarter_reference,
    version_number: snapshotRecord.version_number,
    file_checksums: files
      .slice()
      .sort((left, right) => left.name.localeCompare(right.name))
      .reduce((acc, file) => {
        acc[file.name] = hashContent(file.content);
        return acc;
      }, {}),
    package_checksum: null
  };
  packageManifest.package_checksum = hashContent(stableStringify(packageManifest.file_checksums, 0));
  const packageManifestBuffer = Buffer.from(`${stableStringify(packageManifest)}\n`, 'utf8');
  files.push({
    name: 'package_manifest.json',
    content: packageManifestBuffer,
    content_type: 'application/json'
  });

  return {
    snapshot: snapshotRecord,
    filename: `Quarterly_Pack_${snapshotRecord.quarter_reference}_v${String(snapshotRecord.version_number).padStart(3, '0')}.zip`,
    files: files
      .map((file) => ({
        ...file,
        sha256: hashContent(file.content),
        bytes: file.content.length
      }))
      .sort((left, right) => left.name.localeCompare(right.name)),
    manifest: packageManifest
  };
};

const fetchSnapshotEvent = async (executor, { userId, snapshotId }) => {
  if (!snapshotId) {
    throw new Error('snapshotId is required.');
  }

  const result = await executor.query(
    `
    SELECT
      entity_id AS snapshot_id,
      created_at,
      actor_id,
      source_type,
      description,
      quarter_reference,
      metadata
    FROM business_event_log
    WHERE user_id = $1
      AND event_type = 'snapshot_created'
      AND entity_id = $2
    ORDER BY created_at DESC
    LIMIT 1
    `,
    [userId, snapshotId]
  );

  if (!result.rows.length) {
    return null;
  }

  const row = result.rows[0];
  const metadata = row.metadata || {};
  const metadataSnapshot = metadata.snapshot && typeof metadata.snapshot === 'object'
    ? metadata.snapshot
    : metadata;

  return {
    ...metadataSnapshot,
    unique_id: row.snapshot_id,
    snapshot_id: row.snapshot_id,
    created_at: metadataSnapshot.created_at || row.created_at,
    created_by: metadataSnapshot.created_by || row.actor_id,
    source_type: metadataSnapshot.source_type || row.source_type,
    description: metadataSnapshot.description || row.description,
    quarter_reference: metadataSnapshot.quarter_reference || metadataSnapshot.quarter_label || row.quarter_reference
  };
};

module.exports = {
  STRUCTURED_EXPORT_COLUMNS,
  buildAccountantReadyPackage,
  fetchSnapshotEvent,
  normalizeSnapshotRecord,
  stableStringify
};
