/**
 * Evidence Ingestion Service.
 * Handles evidence capture, storage simulation, and best-effort metadata extraction.
 * Version: V20260322_1915
 * Datetime: 2026-03-22 19:15
 */

const crypto = require("crypto");

/**
 * Simulates OCR/Extraction of metadata from evidence.
 * In a real app, this would call an AI/OCR service.
 * For MVP, we use best-effort heuristics or random mock data if no patterns match.
 *
 * @param {string} fileName - Name of the uploaded file
 * @param {Buffer|string} content - File content (simulated)
 * @returns {Object} Extracted metadata
 */
function extractMetadata(fileName, content) {
  // Simple heuristic based on filename for demo/test predictability
  const lowerName = fileName.toLowerCase();
  
  if (lowerName.includes("tesco")) {
    return {
      merchant: "Tesco",
      amount: 12.50,
      doc_date: "2026-03-20",
      confidence: 0.95
    };
  }
  
  if (lowerName.includes("amazon")) {
    return {
      merchant: "Amazon",
      amount: 45.99,
      doc_date: "2026-03-15",
      confidence: 0.90
    };
  }

  // Default fallback for unknown files
  return {
    merchant: null,
    amount: null,
    doc_date: null,
    confidence: 0.1
  };
}

/**
 * Ingests a new piece of evidence.
 * 
 * @param {Object} params - Ingestion parameters
 * @param {Object} params.store - Data store
 * @param {string} params.userId - Owner user ID
 * @param {string} params.fileName - Original file name
 * @param {string} params.type - RECEIPT, INVOICE, or OTHER
 * @param {Buffer|string} params.content - File content
 * @returns {Promise<Object>} The persisted evidence record
 */
async function ingestEvidence({ store, userId, fileName, type, content }) {
  // 1. Simulate storage
  // In real app, upload to S3/Blob and get durable link
  const storageLink = `https://storage.example.com/evidence/${userId}/${crypto.randomUUID()}-${fileName}`;
  
  // 2. Extract best-effort metadata
  const extracted = extractMetadata(fileName, content);
  
  // 3. Persist record
  const evidenceRecord = {
    user_id: userId,
    type: type,
    captured_at: new Date().toISOString(),
    doc_date: extracted.doc_date,
    merchant: extracted.merchant,
    amount: extracted.amount,
    storage_link: storageLink,
    extraction_confidence: extracted.confidence,
    ocr_status: extracted.confidence > 0.5 ? "COMPLETED" : "FAILED"
  };
  
  try {
    const savedRecord = await store.upsertEvidence(evidenceRecord);
    return savedRecord;
  } catch (error) {
    // Requirements: Evidence ingestion failures should not block transaction flows.
    // In a real app, we might log this and queue for retry or alert.
    console.error("Evidence ingestion failed to persist:", error);
    throw error;
  }
}

module.exports = {
  ingestEvidence,
  extractMetadata
};
