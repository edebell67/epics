const assert = require("assert");
const { MemoryTransactionImportStore } = require("./src/testing/memoryTransactionImportStore");
const { 
  importNormalizedTransactions, 
  acceptCategorySuggestion, 
  overrideCategory, 
  setBusinessPersonal, 
  updateSplit, 
  resolveDuplicate 
} = require("./src/services/transactionImportService");

async function runTest() {
  console.log("Starting verification of inbox micro-decision actions...");

  const store = new MemoryTransactionImportStore();
  const bankAccount = { bank_account_id: "acc_123", user_id: "user_456", provider_name: "test_bank" };
  const rawTransactions = [
    { id: "tx_1", amount: -50.0, description: "Office Supplies", date: "2026-03-20" },
    { id: "tx_2", amount: -120.0, description: "Lunch with Client", date: "2026-03-20" },
    { id: "tx_3", amount: -10.0, description: "Netflix", date: "2026-03-20" }
  ];

  // 1. Import transactions
  console.log("Step 1: Importing transactions...");
  await importNormalizedTransactions({ store, bankAccount, rawTransactions });
  
  const transactions = store.getTransactionsForAccount("acc_123");
  const tx1Id = transactions.find(t => t.bank_txn_ref === "tx_1").txn_id;
  const tx2Id = transactions.find(t => t.bank_txn_ref === "tx_2").txn_id;
  const tx3Id = transactions.find(t => t.bank_txn_ref === "tx_3").txn_id;

  // 2. Accept suggestion
  console.log("Step 2: Accepting category suggestion...");
  await acceptCategorySuggestion({
    store,
    txnId: tx1Id,
    categoryCode: "OFFICE_SUPPLIES",
    categoryName: "Office Supplies",
    confidence: 0.95,
    acceptedBy: "user_agent"
  });

  const class1 = await store.getClassificationByTxnId(tx1Id);
  assert.strictEqual(class1.category_code, "OFFICE_SUPPLIES");
  assert.strictEqual(class1.confidence, 0.95);
  assert.strictEqual(class1.review_required, true); // Still true because business_personal is null
  assert.strictEqual(class1.applied_by, "user_agent");

  // 3. Set business/personal
  console.log("Step 3: Setting business/personal tagging...");
  await setBusinessPersonal({
    store,
    txnId: tx1Id,
    businessPersonal: "BUSINESS",
    setBy: "user_agent"
  });

  const class1Updated = await store.getClassificationByTxnId(tx1Id);
  assert.strictEqual(class1Updated.business_personal, "BUSINESS");
  assert.strictEqual(class1Updated.review_required, false); // Now resolved

  // 4. Manual override
  console.log("Step 4: Manually overriding category...");
  await overrideCategory({
    store,
    txnId: tx2Id,
    categoryCode: "MEALS_ENTERTAINMENT",
    categoryName: "Meals and Entertainment",
    overriddenBy: "user_agent"
  });

  const class2 = await store.getClassificationByTxnId(tx2Id);
  assert.strictEqual(class2.category_code, "MEALS_ENTERTAINMENT");
  assert.strictEqual(class2.confidence, 1.0);
  assert.strictEqual(class2.review_required, true);

  // 5. Update split
  console.log("Step 5: Updating split percentage...");
  await updateSplit({
    store,
    txnId: tx2Id,
    splitBusinessPct: 50,
    updatedBy: "user_agent"
  });

  const class2Split = await store.getClassificationByTxnId(tx2Id);
  assert.strictEqual(class2Split.is_split, true);
  assert.strictEqual(class2Split.split_business_pct, 50);

  // 6. Resolve duplicate
  console.log("Step 6: Resolving duplicate...");
  await resolveDuplicate({
    store,
    txnId: tx3Id,
    resolution: "DISMISSED",
    resolvedBy: "user_agent"
  });

  const class3 = await store.getClassificationByTxnId(tx3Id);
  assert.strictEqual(class3.duplicate_resolution, "DISMISSED");
  assert.strictEqual(class3.review_required, false);

  // 7. Verify audit trail
  console.log("Step 7: Verifying audit trail...");
  const auditTrail1 = await store.getAuditTrailForClassification(class1.classification_id);
  assert.ok(auditTrail1.length >= 2, "Should have at least 2 audit entries for tx1");
  assert.ok(auditTrail1.some(e => e.field_name === "category_code" && e.new_value === "OFFICE_SUPPLIES"));
  assert.ok(auditTrail1.some(e => e.field_name === "business_personal" && e.new_value === "BUSINESS"));

  const auditTrail2 = await store.getAuditTrailForClassification(class2.classification_id);
  assert.ok(auditTrail2.some(e => e.field_name === "split_business_pct" && e.new_value === 50));

  console.log("Verification successful! All actions performed correctly and audit trails recorded.");
}

runTest().catch(err => {
  console.error("Verification failed!");
  console.error(err);
  process.exit(1);
});
