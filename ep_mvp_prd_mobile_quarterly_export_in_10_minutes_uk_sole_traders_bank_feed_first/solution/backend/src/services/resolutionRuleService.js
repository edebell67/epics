/**
 * Resolution and Blocker Rule Service.
 * Version: V20260322_1615
 * Datetime: 2026-03-22 16:15
 */

/**
 * Evaluates a transaction and its classification against MVP blocking rules.
 * 
 * Rules from PRD:
 * - RESOLVED requires:
 *   1. category_code is not null
 *   2. business_personal is not null
 *   3. if is_split = true then split_business_pct is not null
 *   4. if BankTransaction.duplicate_flag = true then duplicate_resolution is NOT "NONE"
 * 
 * - Evidence or receipt absence NEVER creates a blocking state.
 * 
 * @param {Object} txn - The BankTransaction object
 * @param {Object} classification - The TransactionClassification object
 * @returns {Object} Evaluation result
 */
function evaluateTransaction(txn, classification) {
  const blockers = [];
  const reasonCodes = [];

  // 1. Check Missing Category
  if (!classification.category_code) {
    blockers.push("missing_category");
    reasonCodes.push("B001");
  }

  // 2. Check Missing Business/Personal
  if (!classification.business_personal) {
    blockers.push("missing_business_personal");
    reasonCodes.push("B002");
  }

  // 3. Check Split flagged but percentage missing
  if (classification.is_split && (classification.split_business_pct === null || classification.split_business_pct === undefined)) {
    blockers.push("missing_split_pct");
    reasonCodes.push("B003");
  }

  // 4. Check Duplicate flagged but unresolved
  if (txn.duplicate_flag && (!classification.duplicate_resolution || classification.duplicate_resolution === "NONE")) {
    blockers.push("duplicate_unresolved");
    reasonCodes.push("B004");
  }

  const isBlockingExport = blockers.length > 0;
  const isResolved = !isBlockingExport;

  return {
    is_resolved: isResolved,
    is_blocking_export: isBlockingExport,
    blockers: blockers,
    reason_codes: reasonCodes
  };
}

module.exports = {
  evaluateTransaction
};
