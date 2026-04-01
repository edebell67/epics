/**
 * Test for Evidence Confirmation Workflow (Task D3).
 */

const { MemoryTransactionImportStore } = require("./memoryTransactionImportStore");
const { ingestEvidence } = require("../services/evidenceIngestionService");
const { 
  rankCandidates, 
  confirmMatch, 
  rejectMatch, 
  deferMatch,
  getPendingEvidence
} = require("../services/evidenceMatchingService");
const { generateEvidenceIndexCsv } = require("../services/exportService");

async function runTest() {
  console.log("Starting Task D3 Verification: Persist evidence links and unmatched states...");

  const store = new MemoryTransactionImportStore();
  const userId = "user-123";

  // 1. Ingest Evidence
  console.log("\n1. Ingesting evidence...");
  const e1 = await ingestEvidence({
    store, userId, fileName: "tesco_receipt.png", type: "RECEIPT", content: "..."
  });
  const e2 = await ingestEvidence({
    store, userId, fileName: "amazon_invoice.pdf", type: "INVOICE", content: "..."
  });
  const e3 = await ingestEvidence({
    store, userId, fileName: "unknown_doc.jpg", type: "OTHER", content: "..."
  });
  const e4 = await ingestEvidence({
    store, userId, fileName: "unprocessed_doc.jpg", type: "OTHER", content: "..."
  });

  // 2. Add Bank Transactions
  console.log("2. Adding bank transactions...");
  const t1 = (await store.upsertBankTransaction({
    user_id: userId,
    bank_account_id: "acc-1",
    bank_txn_ref: "TXN001",
    date: "2026-03-20",
    merchant: "Tesco Stores",
    amount: 12.50,
    direction: "out",
    source_hash: "hash1"
  })).record;

  const t2 = (await store.upsertBankTransaction({
    user_id: userId,
    bank_account_id: "acc-1",
    bank_txn_ref: "TXN002",
    date: "2026-03-15",
    merchant: "Amazon.co.uk",
    amount: 45.99,
    direction: "out",
    source_hash: "hash2"
  })).record;

  // 3. Confirm Match (e1 -> t1)
  console.log("3. Confirming match for Tesco receipt...");
  await confirmMatch(store, userId, e1.evidence_id, t1.txn_id);

  // 4. Manual No Match (e2)
  console.log("4. Marking Amazon invoice as No Match...");
  await rejectMatch(store, userId, e2.evidence_id);

  // 5. Defer Match (e3)
  console.log("5. Deferring match for unknown doc...");
  await deferMatch(store, userId, e3.evidence_id);

  // 6. Verify Pending Evidence (Active Queue)
  console.log("\n6. Verifying pending evidence (Active Queue)...");
  const pending = await getPendingEvidence(store, userId);
  console.log("   Pending evidence count:", pending.length);
  console.log("   Pending IDs:", pending.map(e => e.evidence_id).join(", "));

  const isE1Pending = pending.some(e => e.evidence_id === e1.evidence_id);
  const isE2Pending = pending.some(e => e.evidence_id === e2.evidence_id);
  const isE3Pending = pending.some(e => e.evidence_id === e3.evidence_id);
  const isE4Pending = pending.some(e => e.evidence_id === e4.evidence_id);

  console.log("   e1 (Confirmed) is pending:", isE1Pending);
  console.log("   e2 (No Match) is pending:", isE2Pending);
  console.log("   e3 (Deferred) is pending:", isE3Pending);
  console.log("   e4 (New) is pending:", isE4Pending);

  // 7. Verify Export
  console.log("\n7. Verifying EvidenceIndex.csv export...");
  const csv = await generateEvidenceIndexCsv(store, userId, "2026-03-01", "2026-03-31");
  
  // Checks
  const lines = csv.split("\n");
  const headers = lines[0].split(",");
  const e1Row = lines.find(l => l.includes(e1.evidence_id)).split(",");
  const e2Row = lines.find(l => l.includes(e2.evidence_id)).split(",");
  const e3Row = lines.find(l => l.includes(e3.evidence_id)).split(",");

  const confirmedIdx = headers.indexOf("user_confirmed");
  const txnIdIdx = headers.indexOf("matched_bank_txn_id");

  console.log(`\nVerification Results:`);
  console.log(`- e1 (Confirmed): user_confirmed=${e1Row[confirmedIdx]}, txn_id=${e1Row[txnIdIdx]}`);
  console.log(`- e2 (No Match):  user_confirmed=${e2Row[confirmedIdx]}, txn_id=${e2Row[txnIdIdx]}`);
  console.log(`- e3 (Deferred):  user_confirmed=${e3Row[confirmedIdx]}, txn_id=${e3Row[txnIdIdx]}`);

  if (e1Row[confirmedIdx] === "true" && e1Row[txnIdIdx] === t1.txn_id &&
      e2Row[confirmedIdx] === "true" && e2Row[txnIdIdx] === "" &&
      e3Row[confirmedIdx] === "false" &&
      !isE1Pending && !isE2Pending && isE3Pending && isE4Pending) {
    console.log("\nPASS: Task D3 requirements verified successfully.");
  } else {
    console.error("\nFAIL: One or more verification checks failed.");
    process.exit(1);
  }
}

runTest().catch(err => {
  console.error(err);
  process.exit(1);
});
