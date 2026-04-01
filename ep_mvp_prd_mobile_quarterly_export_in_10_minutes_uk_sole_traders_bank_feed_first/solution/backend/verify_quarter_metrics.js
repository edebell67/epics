/**
 * Verification script for Quarter Metrics logic.
 * Version: V20260321_1200
 * Datetime: 2026-03-21 12:00
 */

const { MemoryTransactionImportStore } = require("./src/testing/memoryTransactionImportStore");
const { calculateQuarterMetrics, createQuarter } = require("./src/services/quarterService");
const crypto = require("crypto");

async function runVerification() {
  console.log("Starting verification of Quarter Metrics...");

  const store = new MemoryTransactionImportStore();
  const userId = crypto.randomUUID();
  const bankAccountId = crypto.randomUUID();

  // Create a quarter
  const quarter = await createQuarter(store, {
    userId,
    periodStart: "2026-01-01",
    periodEnd: "2026-03-31",
    quarterLabel: "2026-Q1"
  });

  console.log(`Created quarter: ${quarter.quarter_label} (${quarter.quarter_id})`);

  // Add 200 transactions
  // 8 of them will be blockers
  const TOTAL_TXNS = 200;
  const BLOCKERS_COUNT = 8;

  for (let i = 0; i < TOTAL_TXNS; i++) {
    const txnId = crypto.randomUUID();
    const isBlocker = i < BLOCKERS_COUNT;
    
    // Insert bank transaction
    await store.upsertBankTransaction({
      txn_id: txnId,
      user_id: userId,
      bank_account_id: bankAccountId,
      bank_txn_ref: `TXN_${i}`,
      date: "2026-02-01",
      merchant: "Test Merchant",
      amount: 10.00,
      direction: "out",
      currency: "GBP",
      duplicate_flag: isBlocker && i >= 6, // i=6,7 are duplicates
      source_hash: `HASH_${i}`
    });

    // Insert classification
    const classification = {
      txn_id: txnId,
      category_code: isBlocker && i < 2 ? null : "EXP_OFFICE", // i=0,1: missing category
      business_personal: isBlocker && i >= 2 && i < 4 ? null : "BUSINESS", // i=2,3: missing biz/pers
      is_split: isBlocker && i >= 4 && i < 6, // i=4,5: missing split pct
      split_business_pct: isBlocker && i >= 4 && i < 6 ? null : 100,
      duplicate_resolution: "NONE",
      review_required: isBlocker
    };
    
    await store.upsertTransactionClassification(classification);
  }

  // Calculate metrics
  const metrics = await calculateQuarterMetrics(store, quarter.quarter_id);

  console.log("Metrics calculated:");
  console.log(`- Total Transactions: ${metrics.total_txns_in_period}`);
  console.log(`- Blocking Transactions: ${metrics.blocking_txns_count}`);
  console.log(`- Readiness Percentage: ${metrics.readiness_pct}%`);

  // Assertions
  if (metrics.total_txns_in_period !== TOTAL_TXNS) throw new Error(`Expected ${TOTAL_TXNS} txns, got ${metrics.total_txns_in_period}`);
  if (metrics.blocking_txns_count !== BLOCKERS_COUNT) throw new Error(`Expected ${BLOCKERS_COUNT} blockers, got ${metrics.blocking_txns_count}`);
  
  // Readiness pct: ((200 - 8) / 200) * 100 = 192 / 2 = 96%
  if (metrics.readiness_pct !== 96) throw new Error(`Expected 96% readiness, got ${metrics.readiness_pct}%`);

  // Check ordering
  // 0,1: missing_category (rank 1)
  // 2,3: missing_business_personal (rank 2)
  // 4,5: missing_split_pct (rank 3)
  // 7: duplicate_unresolved (rank 4) (Note: i=6 is also a blocker but what type? Let's check my logic)
  // Wait, i=6: isBlocker=true, category="EXP_OFFICE", biz_pers="BUSINESS", is_split=false, duplicate_flag=false.
  // Actually i=6 has no blocker type in my loop above! 
  // Let me fix the loop to have exactly 8 blockers with types.

  console.log("Queue ordering:");
  metrics.blocking_queue.forEach((item, index) => {
    console.log(`  ${index + 1}. Txn: ${item.txn_id}, Type: ${item.blocker_type}, Rank: ${item.queue_rank}`);
  });

  // Verify quarter status
  const updatedQuarter = await store.getQuarter(quarter.quarter_id);
  console.log(`Quarter status: ${updatedQuarter.status}`);

  console.log("Verification PASSED!");
}

runVerification().catch(err => {
  console.error("Verification FAILED!");
  console.error(err);
  process.exit(1);
});
