const fs = require("fs");
const path = require("path");

const { MemoryTransactionImportStore } = require("./src/testing/memoryTransactionImportStore");
const { ingestEvidence } = require("./src/services/evidenceIngestionService");
const { rankCandidates } = require("./src/services/evidenceMatchingService");

async function buildDemoPayload() {
  const store = new MemoryTransactionImportStore();
  const userId = "user-123";

  await store.upsertBankTransaction({
    txn_id: "txn-tesco-001",
    user_id: userId,
    bank_account_id: "acc-1",
    bank_txn_ref: "TESCO001",
    date: "2026-03-20",
    merchant: "Tesco Stores",
    amount: 12.5,
    direction: "out",
    source_hash: "hash-tesco"
  });

  await store.upsertBankTransaction({
    txn_id: "txn-pret-002",
    user_id: userId,
    bank_account_id: "acc-1",
    bank_txn_ref: "PRET002",
    date: "2026-03-19",
    merchant: "Pret A Manger",
    amount: 12.95,
    direction: "out",
    source_hash: "hash-pret"
  });

  await store.upsertBankTransaction({
    txn_id: "txn-coop-003",
    user_id: userId,
    bank_account_id: "acc-1",
    bank_txn_ref: "COOP003",
    date: "2026-03-18",
    merchant: "Co-op Food",
    amount: 12.3,
    direction: "out",
    source_hash: "hash-coop"
  });

  await store.upsertBankTransaction({
    txn_id: "txn-gwr-004",
    user_id: userId,
    bank_account_id: "acc-1",
    bank_txn_ref: "GWR004",
    date: "2026-03-21",
    merchant: "Great Western Railway",
    amount: 48.2,
    direction: "out",
    source_hash: "hash-gwr"
  });

  await store.upsertTransactionClassification({
    txn_id: "txn-gwr-004",
    category_code: null,
    category_name: null,
    business_personal: null,
    is_split: false,
    split_business_pct: null,
    confidence: 0.0,
    applied_by: "import",
    review_required: true,
    duplicate_resolution: "NONE",
    duplicate_of_txn_id: null
  });

  const evidence = await ingestEvidence({
    store,
    userId,
    fileName: "tesco_receipt_20260320.png",
    type: "RECEIPT",
    content: "demo"
  });

  const transactions = store.getTransactionsForAccount("acc-1");
  const candidates = rankCandidates(evidence, transactions);

  return {
    defaultContext: "quarter-close",
    heroCopy: "Use the same micro-decision handlers for voice and tap actions, keep the latest change visible in a single confirmation chip, and allow one-tap undo before quarter export moves on.",
    attachHint: "The first candidate is visually promoted so a sole trader can clear the receipt match in seconds.",
    pendingCopy: "Open the bottom sheet to review the top three matches and decide whether to confirm, defer, or skip the link.",
    sheetCopy: "Each candidate keeps the merchant, date, amount, and match reasons visible. The leading option is promoted, but the user can still override it.",
    outcomes: [
      "Voice and tap actions share the same intent dispatcher so they produce the same state changes.",
      "Every applied voice action raises a single confirmation chip with one-tap undo.",
      "Receipt attach, match confirm, and No match still resolve without creating export blockers."
    ],
    voiceCommandExamples: [
      "Category: Travel",
      "Business",
      "Personal",
      "Split 40%",
      "Attach receipt",
      "Match first",
      "No match"
    ],
    blockerStatus: {
      createsExportBlocker: false,
      safeCopy: "No export blockers created"
    },
    contexts: [
      {
        id: "quarter-close",
        label: "Quarter close",
        summary: "Clear pending receipts before the final pack is generated.",
        description: "This quarter-close pass keeps the export queue moving while the evidence link is confirmed, deferred, or marked as no match."
      },
      {
        id: "inbox",
        label: "Inbox",
        summary: "Resolve receipts as they land in the mobile queue.",
        description: "Inbox mode uses the same bottom-sheet decision flow so the receipt can be resolved the moment it appears."
      }
    ],
    evidence: {
      fileName: evidence.storage_link.split("/").pop(),
      merchant: evidence.merchant,
      amount: evidence.amount,
      doc_date: evidence.doc_date,
      storage_link: evidence.storage_link
    },
    transaction: {
      txn_id: "txn-gwr-004",
      merchant: "Great Western Railway",
      date: "2026-03-21",
      amount: 48.2,
      classification: await store.getClassificationByTxnId("txn-gwr-004")
    },
    categoryCatalog: [
      { code: "travel", name: "Travel" },
      { code: "meals", name: "Meals" },
      { code: "software", name: "Software" }
    ],
    candidates
  };
}

async function main() {
  const payload = await buildDemoPayload();
  const outputPath = path.join(__dirname, "..", "frontend", "data", "evidence-match-demo.json");
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.log(`evidence_ui_demo_written=${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
