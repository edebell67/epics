/**
 * Export service for generating quarterly pack artifacts.
 * Version: V20260322_1915
 * Datetime: 2026-03-22 19:15
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

function escapeCsv(value) {
  if (value === null || value === undefined) return "";
  const stringValue = String(value);
  if (stringValue.includes(",") || stringValue.includes('"') || stringValue.includes("\n")) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

async function generateTransactionsCsv(store, userId, periodStart, periodEnd) {
  const transactions = await store.getTransactionsByDateRange(userId, periodStart, periodEnd);
  
  const headers = [
    "txn_id", "date", "merchant", "amount", "direction", 
    "category_code", "category_name", "confidence", "business_personal", 
    "is_split", "split_business_pct", "matched_evidence_ids", 
    "bank_account_id", "bank_txn_ref"
  ];

  const lines = [headers.join(",")];

  for (const txn of transactions) {
    const classification = await store.getClassificationByTxnId(txn.txn_id) || {};
    const evidenceLinks = await store.getEvidenceLinksForTransaction(txn.txn_id);

    const confirmedEvidenceIds = evidenceLinks
      .filter(l => l.user_confirmed)
      .map(l => l.evidence_id)
      .join(",");

    const row = [
      txn.txn_id,
      txn.date,
      txn.merchant,
      txn.amount,
      txn.direction,
      classification.category_code || "",
      classification.category_name || "",
      classification.confidence || "",
      classification.business_personal || "",
      classification.is_split ? "true" : "false",
      classification.split_business_pct || "",
      confirmedEvidenceIds,
      txn.bank_account_id,
      txn.bank_txn_ref
    ];
    lines.push(row.map(escapeCsv).join(","));
  }

  return lines.join("\n");
}

async function generateEvidenceIndexCsv(store, userId, periodStart, periodEnd) {
  const allEvidence = await store.listEvidence(userId);

  const periodEvidence = allEvidence.filter(e => {
    const date = e.doc_date || e.captured_at.split("T")[0];
    return date >= periodStart && date <= periodEnd;
  });

  const headers = [
    "evidence_id", "type", "captured_at", "doc_date", "merchant",
    "amount", "storage_link", "extraction_confidence",
    "matched_bank_txn_id", "user_confirmed"
  ];

  const lines = [headers.join(",")];

  for (const evidence of periodEvidence) {
    const links = await store.getEvidenceLinksForEvidence(evidence.evidence_id);
    const firstConfirmedLink = links.find(l => l.user_confirmed);

    const row = [
      evidence.evidence_id,
      evidence.type,
      evidence.captured_at,
      evidence.doc_date || "",
      evidence.merchant || "",
      evidence.amount || "",
      evidence.storage_link,
      evidence.extraction_confidence,
      firstConfirmedLink ? firstConfirmedLink.bank_txn_id : "",
      firstConfirmedLink ? "true" : "false"
    ];
    lines.push(row.map(escapeCsv).join(","));
  }

  return lines.join("\n");
}

async function generateQuarterlySummaryCsv(store, quarterId) {
  const quarter = await store.getQuarter(quarterId);
  const metrics = await store.getQuarterMetrics(quarterId);
  const transactions = await store.getTransactionsByDateRange(quarter.user_id, quarter.period_start, quarter.period_end);

  const categoryTotals = new Map();

  for (const txn of transactions) {
    const classification = await store.getClassificationByTxnId(txn.txn_id) || {};
    const code = classification.category_code || "UNCATEGORIZED";
    const name = classification.category_name || "Uncategorized";

    if (!categoryTotals.has(code)) {
      categoryTotals.set(code, {
        code,
        name,
        total_in: 0,
        total_out: 0,
        count: 0,
        unresolved_count: 0
      });
    }

    const totals = categoryTotals.get(code);
    totals.count++;

    const amount = parseFloat(txn.amount);
    if (txn.direction === "in") {
      totals.total_in += amount;
    } else {
      totals.total_out += amount;
    }
  }

  if (metrics && metrics.blocking_queue) {
    for (const item of metrics.blocking_queue) {
      const txn = transactions.find(t => t.txn_id === item.txn_id);
      if (txn) {
        const classification = await store.getClassificationByTxnId(txn.txn_id) || {};
        const code = classification.category_code || "UNCATEGORIZED";
        if (categoryTotals.has(code)) {
          categoryTotals.get(code).unresolved_count++;
        }
      }
    }
  }

  const headers = ["period_start", "period_end", "category_code", "category_name", "total_in", "total_out", "count", "unresolved_count"];
  const lines = [headers.join(",")];

  for (const totals of categoryTotals.values()) {
    const row = [
      quarter.period_start,
      quarter.period_end,
      totals.code,
      totals.name,
      totals.total_in.toFixed(2),
      totals.total_out.toFixed(2),
      totals.count,
      totals.unresolved_count
    ];
    lines.push(row.map(escapeCsv).join(","));
  }

  return lines.join("\n");
}

async function generateQuarterlyPackHtml(store, quarterId) {
  const quarter = await store.getQuarter(quarterId);
  const metrics = await store.getQuarterMetrics(quarterId);
  const transactions = await store.getTransactionsByDateRange(quarter.user_id, quarter.period_start, quarter.period_end);
  const allEvidence = await store.listEvidence(quarter.user_id);

  const periodEvidence = allEvidence.filter(e => {
    const date = e.doc_date || e.captured_at.split("T")[0];
    return date >= quarter.period_start && date <= quarter.period_end;
  });

  let matchedEvidenceCount = 0;
  for (const e of periodEvidence) {
    const links = await store.getEvidenceLinksForEvidence(e.evidence_id);       
    if (links.some(l => l.user_confirmed)) {
      matchedEvidenceCount++;
    }
  }

  const totalIn = transactions.filter(t => t.direction === "in").reduce((sum, t) => sum + parseFloat(t.amount), 0);
  const totalOut = transactions.filter(t => t.direction === "out").reduce((sum, t) => sum + parseFloat(t.amount), 0);

  const evidenceCoverage = periodEvidence.length === 0 ? 100 : Math.round((matchedEvidenceCount / periodEvidence.length) * 100);

  let manualAuditCount = 0;
  for (const txn of transactions) {
    const classification = await store.getClassificationByTxnId(txn.txn_id);
    if (classification) {
      const audits = await store.getAuditTrailForClassification(classification.classification_id);
      if (audits && audits.some(a => a.changed_by !== "import")) {
        manualAuditCount++;
      }
    }
  }

  const categoryTotals = new Map();
  for (const txn of transactions) {
    const classification = await store.getClassificationByTxnId(txn.txn_id) || {};
    const code = classification.category_code || "UNCATEGORIZED";
    if (!categoryTotals.has(code)) {
      categoryTotals.set(code, { name: classification.category_name || "Uncategorized", total: 0 });
    }
    categoryTotals.get(code).total += parseFloat(txn.amount);
  }

  let categoriesHtml = "";
  for (const [code, data] of categoryTotals.entries()) {
    categoriesHtml += `<tr><td>${code}</td><td>${data.name}</td><td style="text-align: right;">${data.total.toFixed(2)}</td></tr>`;
  }

  return `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: sans-serif; color: #333; margin: 40px; }
    h1 { color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
    h2 { color: #2980b9; margin-top: 30px; }
    .summary-box { background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; display: flex; justify-content: space-between; margin-bottom: 20px; }
    .metric { text-align: center; flex: 1; }
    .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
    .metric-label { font-size: 14px; color: #7f8c8d; text-transform: uppercase; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
    th { background: #f2f2f2; }
    .status-badge { padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .status-ready { background: #d4edda; color: #155724; }
    .status-blocked { background: #f8d7da; color: #721c24; }
    .footer { margin-top: 50px; font-size: 12px; color: #95a5a6; text-align: center; border-top: 1px solid #eee; padding-top: 20px; }
  </style>
</head>
<body>
  <h1>Quarterly Pack Summary</h1>
  <p><strong>Period:</strong> ${quarter.period_start} to ${quarter.period_end}</p>
  <p><strong>Quarter Label:</strong> ${quarter.quarter_label}</p>

  <div class="summary-box">
    <div class="metric">
      <div class="metric-value">${totalIn.toFixed(2)}</div>
      <div class="metric-label">Income (GBP)</div>
    </div>
    <div class="metric">
      <div class="metric-value">${totalOut.toFixed(2)}</div>
      <div class="metric-label">Expenses (GBP)</div>
    </div>
    <div class="metric">
      <div class="metric-value">${(totalIn - totalOut).toFixed(2)}</div>
      <div class="metric-label">Net (GBP)</div>
    </div>
  </div>

  <div class="summary-box">
    <div class="metric">
      <div class="metric-value">${metrics ? metrics.readiness_pct : 0}%</div>
      <div class="metric-label">Export Readiness</div>
    </div>
    <div class="metric">
      <div class="metric-value">${metrics ? metrics.blocking_txns_count : "Unknown"}</div>
      <div class="metric-label">Blocking Transactions</div>
    </div>
    <div class="metric">
      <div class="metric-value">${manualAuditCount}</div>
      <div class="metric-label">Manual Audits</div>
    </div>
    <div class="metric" style="display: flex; align-items: center; justify-content: center;">
      <span class="status-badge ${metrics && metrics.blocking_txns_count === 0 ? "status-ready" : "status-blocked"}">
        ${metrics && metrics.blocking_txns_count === 0 ? "READY FOR HANDOFF" : "BLOCKED"}
      </span>
    </div>
  </div>

  <h2>Evidence Coverage</h2>
  <p><strong>Total Evidence Captured:</strong> ${periodEvidence.length}</p>
  <p><strong>Matched to Transactions:</strong> ${matchedEvidenceCount}</p>
  <p><strong>Evidence Coverage:</strong> ${evidenceCoverage}%</p>

  <h2>Category Highlights</h2>
  <table>
    <thead>
      <tr><th>Code</th><th>Category</th><th style="text-align: right;">Total (GBP)</th></tr>
    </thead>
    <tbody>
      ${categoriesHtml}
    </tbody>
  </table>

  <div class="footer">
    Generated At: ${new Date().toISOString()}<br>
    MVP Mobile Quarterly Export Service
  </div>
</body>
</html>
`;
}

async function generateQuarterlyPackPdf(store, quarterId, outputPath) {
  const html = await generateQuarterlyPackHtml(store, quarterId);
  const tempHtmlPath = path.join(path.dirname(outputPath), `temp_summary_${quarterId}.html`);
  fs.writeFileSync(tempHtmlPath, html);
  
  try {
    const cmd = `"${EDGE_PATH}" --headless --print-to-pdf="${outputPath}" "${tempHtmlPath}"`;
    execSync(cmd);
    if (!fs.existsSync(outputPath)) {
      throw new Error("Failed to generate PDF: output file not found after Edge execution.");
    }
  } catch (err) {
    console.error("PDF generation error:", err);
    throw err;
  } finally {
    if (fs.existsSync(tempHtmlPath)) {
      fs.unlinkSync(tempHtmlPath);
    }
  }
}

async function generateQuarterlyPackSummary(store, quarterId) {
  const quarter = await store.getQuarter(quarterId);
  const metrics = await store.getQuarterMetrics(quarterId);
  const transactions = await store.getTransactionsByDateRange(quarter.user_id, quarter.period_start, quarter.period_end);
  const allEvidence = await store.listEvidence(quarter.user_id);

  const periodEvidence = allEvidence.filter(e => {
    const date = e.doc_date || e.captured_at.split("T")[0];
    return date >= quarter.period_start && date <= quarter.period_end;
  });

  let matchedEvidenceCount = 0;
  for (const e of periodEvidence) {
    const links = await store.getEvidenceLinksForEvidence(e.evidence_id);       
    if (links.some(l => l.user_confirmed)) {
      matchedEvidenceCount++;
    }
  }

  const totalIn = transactions.filter(t => t.direction === "in").reduce((sum, t) => sum + parseFloat(t.amount), 0);
  const totalOut = transactions.filter(t => t.direction === "out").reduce((sum, t) => sum + parseFloat(t.amount), 0);

  const lines = [
    "# Quarterly Pack Summary",
    `Period: ${quarter.period_start} to ${quarter.period_end}`,
    `Quarter Label: ${quarter.quarter_label}`,
    "",
    "## Financial Totals",
    `Total Income: ${totalIn.toFixed(2)} GBP`,
    `Total Expenses: ${totalOut.toFixed(2)} GBP`,
    `Net: ${(totalIn - totalOut).toFixed(2)} GBP`,
    "",
    "## Readiness Status",
    `Export Readiness: ${metrics ? metrics.readiness_pct : 0}%`,
    `Blocking Transactions: ${metrics ? metrics.blocking_txns_count : "Unknown"}`,
    "",
    "## Evidence Coverage",
    `Total Evidence Captured: ${periodEvidence.length}`,
    `Matched to Transactions: ${matchedEvidenceCount}`,
    `Evidence Coverage: ${periodEvidence.length === 0 ? 100 : Math.round((matchedEvidenceCount / periodEvidence.length) * 100)}%`,
    "",
    "---",
    `Generated At: ${new Date().toISOString()}`
  ];

  return lines.join("\n");
}

module.exports = {
  generateTransactionsCsv,
  generateEvidenceIndexCsv,
  generateQuarterlySummaryCsv,
  generateQuarterlyPackSummary,
  generateQuarterlyPackPdf
};