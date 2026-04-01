/**
 * Pack Orchestration Service for coordinating the quarterly export flow.
 * Version: V20260322_1900
 * Datetime: 2026-03-22 19:00
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const { calculateQuarterMetrics } = require("./quarterService");
const { 
  generateTransactionsCsv, 
  generateEvidenceIndexCsv, 
  generateQuarterlySummaryCsv, 
  generateQuarterlyPackPdf
} = require("./exportService");

/**
 * Orchestrates the end-to-end export process for a quarter.
 * Validates readiness, generates all artifacts, and records the export event.
 * 
 * @param {Object} store - The data store instance
 * @param {string} userId - ID of the user
 * @param {string} quarterId - ID of the quarter to export
 * @returns {Object} Export result including metadata and artifact contents
 */
async function orchestrateQuarterlyExport(store, userId, quarterId) {
  // 1. Validate Readiness
  const metrics = await calculateQuarterMetrics(store, quarterId);
  const quarter = await store.getQuarter(quarterId);

  if (metrics.blocking_txns_count > 0) {
    throw new Error(`Export blocked: ${metrics.blocking_txns_count} unresolved transactions remain.`);
  }

  // 2. Define consistent naming and metadata
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const prefix = `${quarter.quarter_label}_Export_${timestamp}`;

  const artifactPaths = {
    transactions: `${prefix}_Transactions.csv`,
    evidenceIndex: `${prefix}_EvidenceIndex.csv`,
    quarterlySummary: `${prefix}_QuarterlySummary.csv`,
    quarterlyPackPdf: `${prefix}_QuarterlyPack.pdf`
  };

  // 3. Generate Artifacts
  const transactionsCsv = await generateTransactionsCsv(store, userId, quarter.period_start, quarter.period_end);
  const evidenceIndexCsv = await generateEvidenceIndexCsv(store, userId, quarter.period_start, quarter.period_end);
  const quarterlySummaryCsv = await generateQuarterlySummaryCsv(store, quarterId);
  
  // Generate PDF to a temp file then read it
  const tempPdfPath = path.join(os.tmpdir(), artifactPaths.quarterlyPackPdf);
  await generateQuarterlyPackPdf(store, quarterId, tempPdfPath);
  const quarterlyPackPdfBuffer = fs.readFileSync(tempPdfPath);
  // Clean up temp file
  if (fs.existsSync(tempPdfPath)) {
    fs.unlinkSync(tempPdfPath);
  }

  // 4. Record Export Metadata
  const exportRecord = await store.upsertExportRecord({
    quarter_id: quarterId,
    user_id: userId,
    generated_at: new Date().toISOString(),
    artifact_paths: Object.values(artifactPaths),
    readiness_pct_at_export: metrics.readiness_pct,
    total_txns_exported: metrics.total_txns_in_period
  });

  // 5. Update Quarter status
  await store.upsertQuarter({
    ...quarter,
    status: "exported",
    last_exported_at: exportRecord.generated_at
  });

  return {
    export_id: exportRecord.export_id,
    metadata: exportRecord,
    artifacts: {
      [artifactPaths.transactions]: transactionsCsv,
      [artifactPaths.evidenceIndex]: evidenceIndexCsv,
      [artifactPaths.quarterlySummary]: quarterlySummaryCsv,
      [artifactPaths.quarterlyPackPdf]: quarterlyPackPdfBuffer
    }
  };
}

module.exports = {
  orchestrateQuarterlyExport
};