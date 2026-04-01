/**
 * Test for Evidence Ingestion and Extraction.
 * Version: V20260322_1945
 * Datetime: 2026-03-22 19:45
 */

const { MemoryTransactionImportStore } = require("./memoryTransactionImportStore");
const { ingestEvidence, extractMetadata } = require("../services/evidenceIngestionService");
const assert = require("assert");

async function runTests() {
  console.log("Running Evidence Ingestion Tests...");
  
  const store = new MemoryTransactionImportStore();
  const userId = "user-123";

  // Test 1: Successful metadata extraction (Tesco)
  console.log("- Test 1: extraction logic (Tesco)");
  const metadataTesco = extractMetadata("receipt_tesco_20260320.png", "dummy content");
  assert.strictEqual(metadataTesco.merchant, "Tesco");
  assert.strictEqual(metadataTesco.amount, 12.50);
  assert.strictEqual(metadataTesco.doc_date, "2026-03-20");
  assert.ok(metadataTesco.confidence > 0.9);

  // Test 2: Successful metadata extraction (Amazon)
  console.log("- Test 2: extraction logic (Amazon)");
  const metadataAmazon = extractMetadata("Amazon_Invoice_123.pdf", "dummy content");
  assert.strictEqual(metadataAmazon.merchant, "Amazon");
  assert.strictEqual(metadataAmazon.amount, 45.99);
  assert.strictEqual(metadataAmazon.doc_date, "2026-03-15");
  assert.ok(metadataAmazon.confidence > 0.8);

  // Test 3: Fallback metadata extraction
  console.log("- Test 3: extraction fallback");
  const metadataUnknown = extractMetadata("scanned_doc.jpg", "dummy content");
  assert.strictEqual(metadataUnknown.merchant, null);
  assert.strictEqual(metadataUnknown.amount, null);
  assert.strictEqual(metadataUnknown.confidence, 0.1);

  // Test 4: Ingestion and persistence
  console.log("- Test 4: ingestion and persistence");
  const savedTesco = await ingestEvidence({
    store,
    userId,
    fileName: "Tesco_Weekly.png",
    type: "RECEIPT",
    content: "binary-data"
  });

  assert.ok(savedTesco.evidence_id, "Should have generated an ID");
  assert.strictEqual(savedTesco.user_id, userId);
  assert.strictEqual(savedTesco.merchant, "Tesco");
  assert.strictEqual(savedTesco.ocr_status, "COMPLETED");
  assert.ok(savedTesco.storage_link.includes("Tesco_Weekly.png"));

  const retrieved = await store.getEvidence(savedTesco.evidence_id);
  assert.deepStrictEqual(retrieved, savedTesco);

  // Test 5: List evidence
  console.log("- Test 5: list evidence");
  await ingestEvidence({
    store,
    userId,
    fileName: "Amazon_Office.pdf",
    type: "INVOICE",
    content: "binary-data"
  });

  const list = await store.listEvidence(userId);
  assert.strictEqual(list.length, 2);
  assert.ok(list.some(e => e.merchant === "Tesco"));
  assert.ok(list.some(e => e.merchant === "Amazon"));

  // Test 6: Ingestion resilience (caller handles error)
  console.log("- Test 6: ingestion resilience");
  const failingStore = {
    upsertEvidence: async () => { throw new Error("Database offline"); }
  };

  try {
    await ingestEvidence({
      store: failingStore,
      userId,
      fileName: "fail.png",
      type: "RECEIPT",
      content: "data"
    });
    assert.fail("Should have thrown error");
  } catch (err) {
    assert.strictEqual(err.message, "Database offline");
    console.log("  Successfully caught simulated persistence failure.");
  }

  console.log("All Evidence Ingestion Tests Passed!");
}

runTests().catch(err => {
  console.error("Test Suite Failed:");
  console.error(err);
  process.exit(1);
});
