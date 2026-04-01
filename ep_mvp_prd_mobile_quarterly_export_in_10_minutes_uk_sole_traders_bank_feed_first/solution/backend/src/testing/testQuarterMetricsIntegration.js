/**
 * Integration test for QuarterMetrics and Resolution Rules.
 * Version: V20260322_1640
 */

const { MemoryTransactionImportStore } = require("./memoryTransactionImportStore");
const { calculateQuarterMetrics, createQuarter } = require("../services/quarterService");

async function runIntegrationTest() {
  console.log("Running Quarter Metrics Integration Test...");

  const store = new MemoryTransactionImportStore();
  const userId = "user-123";
  const bankAccountId = "bank-123";

  // 1. Create a quarter
  const quarter = await createQuarter(store, {
    userId,
    periodStart: "2026-01-01",
    periodEnd: "2026-03-31",
    quarterLabel: "2026-Q1"
  });

  // 2. Add some transactions
  // T1: Resolved
  const txn1 = await store.upsertBankTransaction({
    user_id: userId,
    bank_account_id: bankAccountId,
    bank_txn_ref: "TXN001",
    date: "2026-01-15",
    merchant: "Test Merchant 1",
    amount: -10.00,
    direction: "out",
    currency: "GBP",
    duplicate_flag: false,
    source_hash: "hash1"
  });

  await store.upsertTransactionClassification({
    txn_id: txn1.record.txn_id,
    category_code: "EXP_TRAVEL",
    business_personal: "BUSINESS",
    is_split: false,
    confidence: 1.0,
    applied_by: "user",
    review_required: false
  });

  // T2: Blocking (missing category)
  const txn2 = await store.upsertBankTransaction({
    user_id: userId,
    bank_account_id: bankAccountId,
    bank_txn_ref: "TXN002",
    date: "2026-02-10",
    merchant: "Test Merchant 2",
    amount: -20.00,
    direction: "out",
    currency: "GBP",
    duplicate_flag: false,
    source_hash: "hash2"
  });

  await store.upsertTransactionClassification({
    txn_id: txn2.record.txn_id,
    category_code: null,
    business_personal: "BUSINESS",
    is_split: false,
    confidence: 0.5,
    applied_by: "import",
    review_required: true
  });

  // T3: Blocking (duplicate unresolved)
  const txn3 = await store.upsertBankTransaction({
    user_id: userId,
    bank_account_id: bankAccountId,
    bank_txn_ref: "TXN003",
    date: "2026-03-05",
    merchant: "Test Merchant 3",
    amount: -30.00,
    direction: "out",
    currency: "GBP",
    duplicate_flag: true,
    source_hash: "hash3"
  });

  await store.upsertTransactionClassification({
    txn_id: txn3.record.txn_id,
    category_code: "EXP_MEALS",
    business_personal: "BUSINESS",
    is_split: false,
    confidence: 1.0,
    applied_by: "user",
    review_required: false,
    duplicate_resolution: "NONE"
  });

  // 3. Calculate metrics
  const metrics = await calculateQuarterMetrics(store, quarter.quarter_id);

  // 4. Verify results
  console.log("Verifying Metrics...");
  console.log(`Total Transactions: ${metrics.total_txns_in_period} (Expected: 3)`);
  console.log(`Blocking Transactions: ${metrics.blocking_txns_count} (Expected: 2)`);
  console.log(`Readiness: ${metrics.readiness_pct}% (Expected: 33%)`);

  const success = 
    metrics.total_txns_in_period === 3 &&
    metrics.blocking_txns_count === 2 &&
    metrics.readiness_pct === 33 &&
    metrics.blocking_queue.length === 2;

  if (success) {
    console.log("[PASS] Quarter metrics integration test passed.");
    
    // Check if reason codes are present
    const t2Blocker = metrics.blocking_queue.find(b => b.txn_id === txn2.record.txn_id);
    if (t2Blocker && t2Blocker.reason_codes && t2Blocker.reason_codes.includes("B001")) {
      console.log("[PASS] Reason codes correctly emitted.");
    } else {
      console.log("[FAIL] Reason codes missing or incorrect.");
      process.exit(1);
    }

  } else {
    console.log("[FAIL] Quarter metrics integration test failed.");
    console.log(JSON.stringify(metrics, null, 2));
    process.exit(1);
  }
}

runIntegrationTest().catch(err => {
  console.error(err);
  process.exit(1);
});
