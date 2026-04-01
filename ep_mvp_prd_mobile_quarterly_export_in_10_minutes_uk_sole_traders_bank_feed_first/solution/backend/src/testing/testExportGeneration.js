/**
 * Integration test for Export Generation.
 * Version: V20260322_1745
 * Datetime: 2026-03-22 17:45
 */

const { MemoryTransactionImportStore } = require("./memoryTransactionImportStore");
const { generateTransactionsCsv, generateEvidenceIndexCsv } = require("../services/exportService");
const crypto = require("crypto");

async function runTest() {
  console.log("Starting Export Generation test...");

  const store = new MemoryTransactionImportStore();
  const userId = crypto.randomUUID();
  const bankAccountId = crypto.randomUUID();

  // 1. Setup Data
  const txnId1 = crypto.randomUUID();
  const txnId2 = crypto.randomUUID();
  const evidenceId1 = crypto.randomUUID();
  const evidenceId2 = crypto.randomUUID();

  // Transactions
  await store.upsertBankTransaction({
    txn_id: txnId1,
    user_id: userId,
    bank_account_id: bankAccountId,
    bank_txn_ref: "TXN_001",
    date: "2026-01-15",
    merchant: "Amazon",
    amount: 45.99,
    direction: "out",
    currency: "GBP",
    duplicate_flag: false,
    source_hash: "HASH_1"
  });

  await store.upsertBankTransaction({
    txn_id: txnId2,
    user_id: userId,
    bank_account_id: bankAccountId,
    bank_txn_ref: "TXN_002",
    date: "2026-02-20",
    merchant: "Tesco, Inc.", // Has comma
    amount: 12.50,
    direction: "out",
    currency: "GBP",
    duplicate_flag: false,
    source_hash: "HASH_2"
  });

  // Classifications
  await store.upsertTransactionClassification({
    txn_id: txnId1,
    category_code: "EXP_OFFICE",
    category_name: "Office Supplies",
    business_personal: "BUSINESS",
    is_split: false,
    confidence: 0.95,
    review_required: false
  });

  await store.upsertTransactionClassification({
    txn_id: txnId2,
    category_code: "EXP_MEALS",
    category_name: "Meals",
    business_personal: "PERSONAL",
    is_split: false,
    confidence: 1.0,
    review_required: false
  });

  // Evidence
  await store.upsertEvidence({
    evidence_id: evidenceId1,
    user_id: userId,
    type: "RECEIPT",
    captured_at: "2026-01-16T10:00:00Z",
    doc_date: "2026-01-15",
    merchant: "Amazon",
    amount: 45.99,
    storage_link: "https://storage.com/e1.png",
    extraction_confidence: 0.99,
    ocr_status: "completed"
  });

  await store.upsertEvidence({
    evidence_id: evidenceId2,
    user_id: userId,
    type: "RECEIPT",
    captured_at: "2026-02-21T11:00:00Z",
    doc_date: "2026-02-20",
    merchant: "Tesco",
    amount: 12.50,
    storage_link: "https://storage.com/e2.png",
    extraction_confidence: 0.98,
    ocr_status: "completed"
  });

  // Links
  await store.upsertEvidenceLink({
    evidence_id: evidenceId1,
    bank_txn_id: txnId1,
    user_confirmed: true,
    method: "candidate_match"
  });

  // 2. Generate Exports
  const periodStart = "2026-01-01";
  const periodEnd = "2026-03-31";

  const txnsCsv = await generateTransactionsCsv(store, userId, periodStart, periodEnd);
  const evidenceCsv = await generateEvidenceIndexCsv(store, userId, periodStart, periodEnd);

  console.log("Generated Transactions.csv:");
  console.log(txnsCsv);
  console.log("\nGenerated EvidenceIndex.csv:");
  console.log(evidenceCsv);

  // 3. Validation
  const txnLines = txnsCsv.split("\n");
  if (txnLines.length !== 3) throw new Error(`Expected 3 lines in Transactions.csv, got ${txnLines.length}`);
  
  // Check headers
  const txnHeaders = txnLines[0].split(",");
  if (txnHeaders[0] !== "txn_id") throw new Error("Missing txn_id header");
  if (txnHeaders[2] !== "merchant") throw new Error("Missing merchant header");

  // Check data
  if (!txnsCsv.includes("Amazon")) throw new Error("Transactions.csv missing Amazon record");
  if (!txnsCsv.includes("\"Tesco, Inc.\"")) throw new Error("Transactions.csv missing quoted Tesco record");
  if (!txnsCsv.includes(evidenceId1)) throw new Error("Transactions.csv missing linked evidence ID");

  const evidenceLines = evidenceCsv.split("\n");
  if (evidenceLines.length !== 3) throw new Error(`Expected 3 lines in EvidenceIndex.csv, got ${evidenceLines.length}`);

  if (!evidenceCsv.includes(evidenceId1)) throw new Error("EvidenceIndex.csv missing evidenceId1");
  if (!evidenceCsv.includes(txnId1)) throw new Error("EvidenceIndex.csv missing linked txnId1");
  
  // Check user_confirmed logic
  if (!evidenceCsv.includes("true")) throw new Error("EvidenceIndex.csv should have a true for confirmed link");

  console.log("Export Generation test PASSED!");
}

runTest().catch(err => {
  console.error("Export Generation test FAILED!");
  console.error(err);
  process.exit(1);
});
