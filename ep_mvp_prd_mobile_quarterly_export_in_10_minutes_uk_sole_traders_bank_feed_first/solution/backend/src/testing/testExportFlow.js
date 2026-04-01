/**
 * Integration test for the Quarter Export Flow.
 * Version: V20260322_1820
 * Datetime: 2026-03-22 18:20
 */

const { MemoryTransactionImportStore } = require("./memoryTransactionImportStore");
const { createQuarter, calculateQuarterMetrics } = require("../services/quarterService");
const { orchestrateQuarterlyExport } = require("../services/packOrchestrationService");

async function runTest() {
  console.log("Starting Export Flow Integration Test...");
  const store = new MemoryTransactionImportStore();
  const userId = "user_123";

  // 1. Setup Quarter
  const quarter = await createQuarter(store, {
    userId,
    periodStart: "2026-01-01",
    periodEnd: "2026-03-31",
    quarterLabel: "2026-Q1"
  });
  console.log("Created Quarter:", quarter.quarter_id);

  // 2. Add some transactions
  const txn1 = await store.upsertBankTransaction({
    user_id: userId,
    bank_account_id: "acc_1",
    bank_txn_ref: "REF001",
    date: "2026-01-15",
    merchant: "Tesco",
    amount: "45.00",
    direction: "out",
    currency: "GBP",
    duplicate_flag: false,
    source_hash: "H1"
  });

  const txn2 = await store.upsertBankTransaction({
    user_id: userId,
    bank_account_id: "acc_1",
    bank_txn_ref: "REF002",
    date: "2026-02-10",
    merchant: "Client Payment",
    amount: "1500.00",
    direction: "in",
    currency: "GBP",
    duplicate_flag: false,
    source_hash: "H2"
  });

  console.log("Added 2 transactions.");

  // 3. Try export (should be blocked)
  console.log("Attempting export while transactions are unresolved...");
  try {
    await orchestrateQuarterlyExport(store, userId, quarter.quarter_id);
    console.error("FAIL: Export should have been blocked!");
    process.exit(1);
  } catch (error) {
    console.log("SUCCESS: Export correctly blocked:", error.message);
  }

  // 4. Resolve transactions
  console.log("Resolving transactions...");
  await store.upsertTransactionClassification({
    txn_id: txn1.record.txn_id,
    category_code: "EXP_MEALS",
    category_name: "Meals",
    business_personal: "BUSINESS",
    is_split: false,
    confidence: 1.0,
    applied_by: "user",
    review_required: false
  });

  await store.upsertTransactionClassification({
    txn_id: txn2.record.txn_id,
    category_code: "INCOME_SALES",
    category_name: "Sales / Fees",
    business_personal: "BUSINESS",
    is_split: false,
    confidence: 1.0,
    applied_by: "user",
    review_required: false
  });

  const metrics = await calculateQuarterMetrics(store, quarter.quarter_id);
  console.log("Readiness Pct:", metrics.readiness_pct + "%");

  // 5. Trigger successful export
  console.log("Triggering export flow...");
  const exportResult = await orchestrateQuarterlyExport(store, userId, quarter.quarter_id);
  
  console.log("Export Successful!");
  console.log("Export ID:", exportResult.export_id);
  console.log("Artifacts Generated:", Object.keys(exportResult.artifacts).length);
  
  // 6. Verify Artifacts
  const artifactNames = Object.keys(exportResult.artifacts);
  const expectedTypes = ["Transactions.csv", "EvidenceIndex.csv", "QuarterlySummary.csv", "QuarterlyPack.txt"];
  
  for (const type of expectedTypes) {
    const found = artifactNames.find(n => n.includes(type));
    if (found) {
      console.log(`Found artifact: ${found}`);
    } else {
      console.error(`FAIL: Missing artifact of type ${type}`);
      process.exit(1);
    }
  }

  // 7. Verify Metadata and Status
  const updatedQuarter = await store.getQuarter(quarter.quarter_id);
  console.log("Updated Quarter Status:", updatedQuarter.status);
  if (updatedQuarter.status !== "exported") {
    console.error("FAIL: Quarter status not updated to 'exported'");
    process.exit(1);
  }

  const exportRecord = await store.getExportRecord(exportResult.export_id);
  console.log("Export Record Metadata:", JSON.stringify(exportRecord, null, 2));

  if (exportRecord.readiness_pct_at_export !== 100) {
    console.error("FAIL: Export metadata readiness pct mismatch");
    process.exit(1);
  }

  console.log("Export Flow Test PASSED successfully!");
}

runTest().catch(err => {
  console.error("Test failed with error:", err);
  process.exit(1);
});
