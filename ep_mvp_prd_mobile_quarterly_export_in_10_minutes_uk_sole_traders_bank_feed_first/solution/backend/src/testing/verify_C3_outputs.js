/**
 * Verification script for Task C3: Generate QuarterlySummary.csv and QuarterlyPack.pdf
 */

const fs = require("fs");
const path = require("path");
const { MemoryTransactionImportStore } = require("./memoryTransactionImportStore");
const { orchestrateQuarterlyExport } = require("../services/packOrchestrationService");

async function runVerification() {
  console.log("Starting C3 Verification...");
  const store = new MemoryTransactionImportStore();
  const userId = "usr_test_123";
  const quarterId = "qtr_2026_q1";

  // 1. Setup Mock Data
  console.log("Setting up mock data...");
  await store.upsertQuarter({
    quarter_id: quarterId,
    user_id: userId,
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    quarter_label: "2026-Q1",
    status: "open"
  });

  // Add some transactions
  const txns = [
    { txn_id: "t1", user_id: userId, date: "2026-01-10", merchant: "Tesco", amount: "45.50", direction: "out", bank_account_id: "ba1", bank_txn_ref: "REF1", source_hash: "H1" },
    { txn_id: "t2", user_id: userId, date: "2026-02-15", merchant: "Client A", amount: "1200.00", direction: "in", bank_account_id: "ba1", bank_txn_ref: "REF2", source_hash: "H2" },
    { txn_id: "t3", user_id: userId, date: "2026-03-05", merchant: "Shell", amount: "60.00", direction: "out", bank_account_id: "ba1", bank_txn_ref: "REF3", source_hash: "H3" }
  ];

  for (const txn of txns) {
    await store.upsertBankTransaction(txn);
    // Classify them so they aren't blocking
    const classification = await store.upsertTransactionClassification({
      txn_id: txn.txn_id,
      category_code: txn.direction === "in" ? "INCOME" : "EXPENSE",
      category_name: txn.direction === "in" ? "Income" : "Expense",
      business_personal: "business",
      confidence: 1.0
    });

    // Add a manual audit for t1
    if (txn.txn_id === "t1") {
      await store.addClassificationAuditEntry({
        classification_id: classification.classification_id,
        field_name: "category_code",
        previous_value: "UNCATEGORIZED",
        new_value: "EXPENSE",
        changed_by: "user",
        changed_at: new Date().toISOString()
      });
    }
  }

  // Add some evidence
  await store.upsertEvidence({
    evidence_id: "e1",
    user_id: userId,
    doc_date: "2026-01-10",
    merchant: "Tesco",
    amount: "45.50",
    type: "receipt",
    storage_link: "https://storage.example.com/receipt1.jpg"
  });
  await store.upsertEvidenceLink({
    evidence_id: "e1",
    bank_txn_id: "t1",
    user_confirmed: true
  });

  // 2. Orchestrate Export
  console.log("Running orchestrateQuarterlyExport...");
  const result = await orchestrateQuarterlyExport(store, userId, quarterId);

  // 3. Verify Artifacts
  console.log("Verifying artifacts...");
  const artifacts = result.artifacts;
  const artifactNames = Object.keys(artifacts);

  const expectedFiles = ["Transactions.csv", "EvidenceIndex.csv", "QuarterlySummary.csv", "QuarterlyPack.pdf"];
  
  for (const expected of expectedFiles) {
    const found = artifactNames.find(n => n.endsWith(expected));
    if (!found) {
      throw new Error(`Missing artifact: ${expected}`);
    }
    console.log(`✓ Found artifact: ${found}`);
    
    // Write to disk for manual inspection
    const outPath = path.join(__dirname, "../../../..", "workstreams", "C", expected);
    fs.writeFileSync(outPath, artifacts[found]);
    console.log(`  - Saved to: ${outPath}`);
  }

  // Verify QuarterlySummary.csv totals
  const summaryCsv = artifacts[artifactNames.find(n => n.endsWith("QuarterlySummary.csv"))];
  console.log("Reconciling QuarterlySummary.csv totals...");
  const lines = summaryCsv.split("\n");

  let totalIn = 0;
  let totalOut = 0;
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i]) continue;
    const parts = lines[i].split(",");
    totalIn += parseFloat(parts[4]);
    totalOut += parseFloat(parts[5]);
  }

  if (Math.abs(totalIn - 1200.00) > 0.01 || Math.abs(totalOut - 105.50) > 0.01) {
    throw new Error(`Totals mismatch in QuarterlySummary.csv: In=${totalIn}, Out=${totalOut}`);
  }
  console.log("✓ QuarterlySummary.csv totals reconcile.");

  // Verify PDF
  const pdfBuffer = artifacts[artifactNames.find(n => n.endsWith("QuarterlyPack.pdf"))];
  if (!pdfBuffer || pdfBuffer.length < 1000) {
    throw new Error("QuarterlyPack.pdf seems too small or empty.");
  }
  if (pdfBuffer.toString("binary", 0, 4) !== "%PDF") {
    throw new Error("QuarterlyPack.pdf does not have a valid PDF header.");
  }
  console.log(`✓ QuarterlyPack.pdf verified (Size: ${pdfBuffer.length} bytes).`);

  console.log("\nC3 Verification SUCCESSFUL!");
}

runVerification().catch(err => {
  console.error("\nC3 Verification FAILED:");
  console.error(err);
  process.exit(1);
});