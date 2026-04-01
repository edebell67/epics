const db = require('../config/db');
const { normalizeVatType } = require('../services/vatQuarterClassificationService');
const { buildQuarterlyPackArtifacts } = require('../services/quarterlyExportService');
const {
  buildAccountantReadyPackage,
  fetchSnapshotEvent
} = require('../services/exportPackageBuilderService');

/**
 * Generate Structured CSV Export
 * GET /api/v1/export?format=xero&start=2026-01-01&end=2026-03-31
 */
const exportTransactions = async (req, res) => {
  const { format = 'generic', start, end, quarter_ref } = req.query;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    let queryText = `
      SELECT ci.*, c.name as client_name 
      FROM capture_items ci
      LEFT JOIN clients c ON ci.client_id = c.id
      WHERE ci.user_id = $1 AND ci.deleted_at IS NULL
    `;
    let params = [userId];
    let count = 2;

    if (start) {
      queryText += ` AND ci.created_at >= $${count++}`;
      params.push(start);
    }
    if (end) {
      queryText += ` AND ci.created_at <= $${count++}`;
      params.push(end);
    }
    if (quarter_ref) {
      queryText += ` AND ci.quarter_ref = $${count++}`;
      params.push(quarter_ref);
    }

    queryText += ` ORDER BY ci.created_at ASC`;

    const result = await db.query(queryText, params);
    const transactions = result.rows;

    let csvContent = '';
    let filename = `export_${format}_${new Date().toISOString().split('T')[0]}.csv`;

    if (format === 'xero') {
      csvContent = 'Date,Amount,Payee,Description,Reference,Check Number\n';
      transactions.forEach(t => {
        const date = new Date(t.created_at).toLocaleDateString('en-GB');
        const amount = (normalizeVatType(t.vat_type) === 'input' ? -t.gross_amount : t.gross_amount);
        const payee = t.client_name || 'Misc';
        const desc = t.extracted_text || t.raw_note || '';
        const ref = t.reference_number || '';
        csvContent += `"${date}","${amount}","${payee}","${desc}","${ref}",""\n`;
      });
    } else if (format === 'quickbooks') {
      csvContent = 'Date,Description,Amount\n';
      transactions.forEach(t => {
        const date = new Date(t.created_at).toLocaleDateString('en-US');
        const amount = (normalizeVatType(t.vat_type) === 'input' ? -t.gross_amount : t.gross_amount);
        const desc = `${t.type.toUpperCase()}: ${t.client_name || ''} ${t.reference_number || ''}`;
        csvContent += `"${date}","${desc}","${amount}"\n`;
      });
    } else {
      // Generic
      csvContent = 'ID,Date,Type,Status,Reference,Client,Net,VAT,Gross,Currency,Labels,Note\n';
      transactions.forEach(t => {
        const date = new Date(t.created_at).toISOString();
        csvContent += `"${t.id}","${date}","${t.type}","${t.status}","${t.reference_number || ''}","${t.client_name || ''}","${t.net_amount}","${t.vat_amount}","${t.gross_amount}","${t.currency}","","${t.raw_note || ''}"\n`;
      });
    }

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', `attachment; filename=${filename}`);
    res.status(200).send(csvContent);

  } catch (err) {
    console.error('[ExportController] Export Error:', err);
    res.status(500).json({ error: 'Failed to generate export' });
  }
};

const archiver = require('archiver');
const fs = require('fs');
const path = require('path');

/**
 * Generate VAT Pack (ZIP containing CSV + Attachments)
 * GET /api/v1/export/vat-pack?quarter_ref=Q1-2026
 */
const exportVATPack = async (req, res) => {
  const { quarter_ref } = req.query;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  if (!quarter_ref) {
    return res.status(400).json({ error: 'Missing quarter_ref' });
  }

  try {
    const queryText = `
      SELECT ci.*, c.name as client_name, ca.file_path as attachment_path 
      FROM capture_items ci
      LEFT JOIN clients c ON ci.client_id = c.id
      LEFT JOIN capture_item_attachments ca ON ci.id = ca.item_id
      WHERE ci.user_id = $1 AND ci.quarter_ref = $2 AND ci.deleted_at IS NULL
      ORDER BY ci.created_at ASC
    `;
    const result = await db.query(queryText, [userId, quarter_ref]);
    const transactions = result.rows;

    const archive = archiver('zip', { zlib: { level: 9 } });
    const filename = `VAT_Pack_${quarter_ref}_${new Date().toISOString().split('T')[0]}.zip`;

    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename=${filename}`);

    archive.pipe(res);

    // 1. Add CSV
    let csvContent = 'Date,Type,Status,Reference,Client,Net,VAT,Gross,Attachment\n';
    transactions.forEach(t => {
      const date = new Date(t.created_at).toLocaleDateString('en-GB');
      const attachmentName = t.attachment_path ? path.basename(t.attachment_path) : '';
      csvContent += `"${date}","${t.type}","${t.status}","${t.reference_number || ''}","${t.client_name || ''}","${t.net_amount}","${t.vat_amount}","${t.gross_amount}","${attachmentName}"\n`;
      
      // 2. Add Attachment file if exists
      if (t.attachment_path && fs.existsSync(t.attachment_path)) {
        archive.file(t.attachment_path, { name: `attachments/${attachmentName}` });
      }
    });

    archive.append(csvContent, { name: 'transactions.csv' });
    await archive.finalize();

  } catch (err) {
    console.error('[ExportController] VAT Pack Error:', err);
    res.status(500).json({ error: 'Failed to generate VAT pack' });
  }
};

const buildSimplePdf = (lines) => {
  const safe = lines.map((line) => String(line).replace(/[()\\]/g, ''));
  const text = safe.map((line, i) => `BT 40 ${760 - i * 16} Td (${line}) Tj`).join('\n');
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
  for (let i = 1; i <= objects.length; i += 1) {
    body += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  body += `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;
  return Buffer.from(body, 'utf8');
};

const exportQuarterlyPack = async (req, res) => {
  const { period_start, period_end, snapshot_id } = req.query;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  if (snapshot_id) {
    try {
      const snapshotRecord = await fetchSnapshotEvent(db, {
        userId,
        snapshotId: snapshot_id
      });

      if (!snapshotRecord) {
        return res.status(404).json({ error: 'Snapshot not found.' });
      }

      const exportPackage = buildAccountantReadyPackage(snapshotRecord);
      const archive = archiver('zip', { zlib: { level: 9 } });

      res.setHeader('Content-Type', 'application/zip');
      res.setHeader('Content-Disposition', `attachment; filename=${exportPackage.filename}`);

      archive.pipe(res);
      exportPackage.files.forEach((file) => {
        archive.append(file.content, { name: file.name });
      });
      await archive.finalize();
      return;
    } catch (err) {
      console.error('[ExportController] Snapshot Quarterly Pack Error:', err);
      return res.status(500).json({ error: 'Failed to generate snapshot quarterly pack.' });
    }
  }

  if (!period_start || !period_end) {
    return res.status(400).json({ error: 'period_start and period_end are required.' });
  }

  try {
    const readiness = await db.query(
      `
      SELECT
        COUNT(*)::int AS total_txns,
        COUNT(*) FILTER (
          WHERE tc.category_code IS NULL
            OR tc.business_personal IS NULL
            OR (tc.is_split = TRUE AND tc.split_business_pct IS NULL)
            OR (bt.duplicate_flag = TRUE AND bt.duplicate_resolution IS NULL)
        )::int AS blocking
      FROM bank_transactions bt
      LEFT JOIN transaction_classifications tc ON tc.bank_txn_id = bt.id
      WHERE bt.user_id = $1 AND bt.txn_date BETWEEN $2::date AND $3::date
      `,
      [userId, period_start, period_end]
    );
    const total = Number(readiness.rows[0]?.total_txns || 0);
    const blocking = Number(readiness.rows[0]?.blocking || 0);
    if (blocking > 0) {
      return res.status(400).json({ error: 'Export blocked. Resolve all blocking items first.', total_txns: total, blocking_txns_count: blocking });
    }

    const data = await db.query(
      `
      SELECT
        bt.id AS txn_id,
        bt.txn_date AS date,
        bt.merchant,
        bt.amount,
        bt.direction,
        tc.category_code,
        COALESCE(tc.category_name, tc.category_code) AS category_name,
        COALESCE(tc.confidence, 0) AS confidence,
        tc.business_personal,
        COALESCE(tc.is_split, false) AS is_split,
        tc.split_business_pct,
        bt.bank_account_id,
        bt.bank_txn_ref,
        COALESCE(STRING_AGG(el.evidence_id::text, ','), '') AS matched_evidence_ids,
        COUNT(*) FILTER (WHERE el.user_confirmed = TRUE) AS evidence_match_count
      FROM bank_transactions bt
      LEFT JOIN transaction_classifications tc ON tc.bank_txn_id = bt.id
      LEFT JOIN evidence_links el ON el.bank_txn_id = bt.id
      WHERE bt.user_id = $1 AND bt.txn_date BETWEEN $2::date AND $3::date
      GROUP BY bt.id, bt.txn_date, bt.merchant, bt.amount, bt.direction, tc.category_code, tc.category_name, tc.confidence, tc.business_personal, tc.is_split, tc.split_business_pct, bt.bank_account_id, bt.bank_txn_ref
      ORDER BY bt.txn_date ASC
      `,
      [userId, period_start, period_end]
    );
    const rows = data.rows;

    const evidenceRows = await db.query(
      `
      SELECT
        e.id AS evidence_id,
        e.type,
        e.captured_at,
        e.doc_date,
        e.merchant,
        e.amount,
        e.storage_link,
        COALESCE(e.extraction_confidence, 0) AS extraction_confidence,
        el.bank_txn_id AS matched_bank_txn_id,
        COALESCE(el.user_confirmed, false) AS user_confirmed
      FROM evidence e
      LEFT JOIN evidence_links el ON el.evidence_id = e.id
      WHERE e.user_id = $1
        AND e.captured_at::date BETWEEN $2::date AND $3::date
      ORDER BY e.captured_at ASC
      `,
      [userId, period_start, period_end]
    );
    const summary = await db.query(
      `
      SELECT
        $2::date AS period_start,
        $3::date AS period_end,
        tc.category_code,
        COALESCE(tc.category_name, tc.category_code) AS category_name,
        SUM(CASE WHEN bt.direction='in' THEN bt.amount ELSE 0 END)::numeric(18,2) AS total_in,
        SUM(CASE WHEN bt.direction='out' THEN bt.amount ELSE 0 END)::numeric(18,2) AS total_out,
        COUNT(*)::int AS count,
        0::int AS unresolved_count
      FROM bank_transactions bt
      LEFT JOIN transaction_classifications tc ON tc.bank_txn_id = bt.id
      WHERE bt.user_id = $1 AND bt.txn_date BETWEEN $2::date AND $3::date
      GROUP BY tc.category_code, COALESCE(tc.category_name, tc.category_code)
      ORDER BY tc.category_code
      `,
      [userId, period_start, period_end]
    );
    const exportArtifacts = buildQuarterlyPackArtifacts({
      periodStart: period_start,
      periodEnd: period_end,
      transactions: rows,
      evidenceRows: evidenceRows.rows,
      summaryRows: summary.rows
    });

    const autoCount = rows.filter((r) => r.confidence && Number(r.confidence) > 0).length;
    const manualCount = rows.length - autoCount;
    const matchedEvidence = evidenceRows.rows.filter((r) => r.user_confirmed && r.matched_bank_txn_id).length;
    const pdf = buildSimplePdf([
      'Quarterly Pack Summary',
      `Period: ${period_start} to ${period_end}`,
      `Readiness: 100%`,
      `Total transactions: ${rows.length}`,
      `Auto-categorised: ${autoCount}`,
      `Manual overrides: ${manualCount}`,
      `Evidence matched: ${matchedEvidence}`,
      `Bank-only transactions: ${Math.max(0, rows.length - matchedEvidence)}`
    ]);

    const archive = archiver('zip', { zlib: { level: 9 } });
    const filename = `Quarterly_Pack_${period_start}_to_${period_end}.zip`;
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename=${filename}`);
    res.setHeader('X-Quarterly-Pack-Checksum', exportArtifacts.manifest.pack_checksum);
    archive.pipe(res);
    archive.append(exportArtifacts.transactionsCsv, { name: 'Transactions.csv' });
    archive.append(exportArtifacts.evidenceCsv, { name: 'EvidenceIndex.csv' });
    archive.append(exportArtifacts.summaryCsv, { name: 'QuarterlySummary.csv' });
    archive.append(pdf, { name: 'QuarterlyPack.pdf' });
    archive.append(exportArtifacts.manifestJson, { name: 'Manifest.json' });
    await archive.finalize();
  } catch (err) {
    console.error('[ExportController] Quarterly Pack Error:', err);
    res.status(500).json({ error: 'Failed to generate quarterly pack.' });
  }
};

module.exports = {
  exportTransactions,
  exportVATPack,
  exportQuarterlyPack
};
