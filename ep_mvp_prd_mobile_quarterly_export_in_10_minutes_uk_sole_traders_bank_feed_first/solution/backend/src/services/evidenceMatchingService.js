/**
 * Evidence Matching Service.
 * Rank top bank transaction candidates for a piece of evidence.
 * Version: V20260327_0115
 * Datetime: 2026-03-27 01:15
 * Reference: C:\Users\edebe\eds\plans\20260327_0113_V20260327_0115_build_confirm_first_evidence_matching_candidate_service.md
 */

/**
 * Calculates Levenshtein distance between two strings.
 */
function levenshteinDistance(a, b) {
  const matrix = [];

  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }

  for (j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // substitution
          matrix[i][j - 1] + 1,     // insertion
          matrix[i - 1][j] + 1      // deletion
        );
      }
    }
  }

  return matrix[b.length][a.length];
}

/**
 * Calculates merchant similarity score (0-1).
 */
function calculateMerchantSimilarity(merchantA, merchantB) {
  if (!merchantA || !merchantB) return 0;

  const a = merchantA.toLowerCase().trim();
  const b = merchantB.toLowerCase().trim();

  if (a === b) return 1.0;
  if (a.includes(b) || b.includes(a)) return 0.9;

  const distance = levenshteinDistance(a, b);
  const maxLength = Math.max(a.length, b.length);
  const similarity = 1 - distance / maxLength;

  return Math.max(0, similarity);
}

/**
 * Ranks bank transaction candidates for a piece of evidence.
 *
 * @param {Object} evidence - Extracted evidence metadata
 * @param {Array<Object>} transactions - List of bank transactions to search    
 * @returns {Array<Object>} Top 3 ranked candidates
 */
function rankCandidates(evidence, transactions) {
  if (!evidence || !transactions || transactions.length === 0) {
    return [];
  }

  const candidates = transactions
    .filter(txn => txn.direction === 'out') // receipts are usually expenses    
    .map(txn => {
      const reasons = [];
      let amountScore = 0;
      let dateScore = 0;
      let merchantScore = 0;

      // 1. Amount Match
      if (evidence.amount !== null && evidence.amount !== undefined) {
        const diff = Math.abs(evidence.amount - txn.amount);
        if (diff === 0) {
          amountScore = 1.0;
          reasons.push('Exact amount match');
        } else if (diff <= 1.0 || diff / txn.amount <= 0.01) {
          amountScore = 0.8;
          reasons.push('Close amount match');
        }
      }

      // 2. Date Proximity
      if (evidence.doc_date && txn.date) {
        const docDate = new Date(evidence.doc_date);
        const txnDate = new Date(txn.date);
        const diffDays = Math.abs((txnDate - docDate) / (1000 * 60 * 60 * 24)); 

        if (diffDays === 0) {
          dateScore = 1.0;
          reasons.push('Exact date match');
        } else if (diffDays <= 1) {
          dateScore = 0.9;
          reasons.push('Within 1 day');
        } else if (diffDays <= 3) {
          dateScore = 0.7;
          reasons.push('Within 3 days');
        } else if (diffDays <= 7) {
          dateScore = 0.5;
          reasons.push('Within 7 days');
        }
      }

      // 3. Merchant Similarity
      if (evidence.merchant && txn.merchant) {
        merchantScore = calculateMerchantSimilarity(evidence.merchant, txn.merchant);
        if (merchantScore >= 0.9) {
          reasons.push('Strong merchant match');
        } else if (merchantScore >= 0.7) {
          reasons.push('Partial merchant match');
        }
      }

      // Calculate total confidence (weighted average)
      const totalScore = (amountScore * 0.5) + (merchantScore * 0.3) + (dateScore * 0.2);

      return {
        bank_txn_id: txn.txn_id,
        merchant: txn.merchant,
        date: txn.date,
        amount: txn.amount,
        link_confidence: Math.round(totalScore * 100) / 100,
        amount_match: amountScore,
        date_proximity: dateScore,
        merchant_similarity: merchantScore,
        reasons: reasons
      };
    })
    .filter(c => c.link_confidence >= 0.3) // Filter out weak matches (e.g. date only)
    .sort((a, b) => b.link_confidence - a.link_confidence)
    .slice(0, 3)
    .map((c, index) => ({
      candidate_rank: index + 1,
      ...c
    }));

  return candidates;
}

/**
 * Confirms a match between evidence and a bank transaction.
 */
async function confirmMatch(store, userId, evidenceId, bankTxnId, method = 'user_confirmed') {
  const linkRecord = {
    evidence_id: evidenceId,
    bank_txn_id: bankTxnId,
    user_confirmed: true,
    confirmed_at: new Date().toISOString(),
    method: method,
    link_confidence: 1.0 // confirmed by user
  };

  return await store.upsertEvidenceLink(linkRecord);
}

/**
 * Marks evidence as having no match in the bank feed.
 */
async function rejectMatch(store, userId, evidenceId) {
  const linkRecord = {
    evidence_id: evidenceId,
    bank_txn_id: null,
    user_confirmed: true,
    confirmed_at: new Date().toISOString(),
    method: 'manual_no_match',
    link_confidence: 0.0
  };

  return await store.upsertEvidenceLink(linkRecord);
}

/**
 * Defers matching for evidence.
 */
async function deferMatch(store, userId, evidenceId) {
  const linkRecord = {
    evidence_id: evidenceId,
    bank_txn_id: null,
    user_confirmed: false,
    method: 'deferred',
    link_confidence: 0.0
  };

  return await store.upsertEvidenceLink(linkRecord);
}

/**
 * Retrieves all evidence for a user that hasn't been confirmed or explicitly rejected as no match.
 */
async function getPendingEvidence(store, userId) {
  const allEvidence = await store.listEvidence(userId);
  const pending = [];

  for (const evidence of allEvidence) {
    const links = await store.getEvidenceLinksForEvidence(evidence.evidence_id);
    const isResolved = links.some(l => l.user_confirmed === true);

    if (!isResolved) {
      pending.push(evidence);
    }
  }

  return pending;
}

module.exports = {
  rankCandidates,
  calculateMerchantSimilarity,
  confirmMatch,
  rejectMatch,
  deferMatch,
  getPendingEvidence
};
