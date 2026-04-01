/**
 * Merchant Categorisation Rule Service.
 * Version: V20260322_1730
 * Datetime: 2026-03-22 17:30
 */

const crypto = require("crypto");

/**
 * Creates a merchant rule from an existing transaction classification.
 * 
 * @param {Object} params
 * @param {Object} params.store - The storage provider
 * @param {string} params.txnId - The source transaction ID
 * @param {string} params.userId - The user ID
 * @param {string} params.merchantPattern - The pattern to match (e.g. "Tesco")
 * @param {Date} [params.now] - Optional override for current time
 * @returns {Promise<Object>} The created rule
 */
async function createRuleFromClassification({ store, txnId, userId, merchantPattern, now = new Date() }) {
  const classification = await store.getClassificationByTxnId(txnId);
  if (!classification) {
    throw new Error(`Classification not found for transaction ${txnId}`);
  }

  if (!classification.category_code) {
    throw new Error(`Cannot create rule from un-categorised classification`);
  }

  const rule = {
    rule_id: crypto.randomUUID(),
    user_id: userId,
    scope: "merchant_pattern",
    merchant_pattern: merchantPattern,
    category_code: classification.category_code,
    default_business_personal: classification.business_personal,
    default_split_business_pct: classification.split_business_pct,
    status: "active",
    created_at: now.toISOString(),
    updated_at: now.toISOString()
  };

  return await store.upsertRule(rule);
}

/**
 * Finds the best matching rule for a merchant name.
 * Matches are case-insensitive substrings.
 * Most specific (longest) pattern wins if multiple match.
 * 
 * @param {Object} params
 * @param {Object} params.store - The storage provider
 * @param {string} params.userId - The user ID
 * @param {string} params.merchantName - The merchant name from bank feed
 * @returns {Promise<Object|null>} The matching rule or null
 */
async function findMatchingRule({ store, userId, merchantName }) {
  if (!merchantName) return null;

  const rules = await store.listRules(userId);
  const activeRules = rules.filter(r => r.status === "active" && r.scope === "merchant_pattern");

  if (activeRules.length === 0) return null;

  // Sort by pattern length descending to match most specific pattern first
  activeRules.sort((a, b) => b.merchant_pattern.length - a.merchant_pattern.length);

  const normalizedMerchant = merchantName.toLowerCase();

  for (const rule of activeRules) {
    const normalizedPattern = rule.merchant_pattern.toLowerCase();
    if (normalizedMerchant.includes(normalizedPattern)) {
      return rule;
    }
  }

  return null;
}

/**
 * Applies a rule to a classification object (suggests defaults).
 * Note: This does NOT save to store, it returns the merged updates.
 * 
 * @param {Object} rule - The rule to apply
 * @param {Object} classification - The target classification object
 * @returns {Object} The suggested updates
 */
function applyRuleToClassification(rule, classification) {
  const updates = {};

  if (rule.category_code) {
    updates.category_code = rule.category_code;
    // Suggest high confidence if applied by rule
    updates.confidence = 0.8; 
    updates.applied_by = "rule";
  }

  if (rule.default_business_personal) {
    updates.business_personal = rule.default_business_personal;
  }

  if (rule.default_split_business_pct !== null && rule.default_split_business_pct !== undefined) {
    updates.is_split = true;
    updates.split_business_pct = rule.default_split_business_pct;
  }

  // If rule completes basic classification, mark review NOT required by default
  // but allow user override later.
  if (updates.category_code && updates.business_personal) {
    updates.review_required = false;
  }

  return updates;
}

module.exports = {
  createRuleFromClassification,
  findMatchingRule,
  applyRuleToClassification
};
