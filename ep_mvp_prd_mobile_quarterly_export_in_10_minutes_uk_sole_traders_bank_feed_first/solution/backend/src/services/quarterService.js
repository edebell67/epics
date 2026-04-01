/**
 * Quarter and QuarterMetrics services.
 * Version: V20260322_1825
 * Datetime: 2026-03-22 18:25
 */

const crypto = require("crypto");
const { evaluateTransaction } = require("./resolutionRuleService");

/**
 * Calculates readiness metrics for a given quarter.
 */
async function calculateQuarterMetrics(store, quarterId) {
  const quarter = await store.getQuarter(quarterId);
  if (!quarter) {
    throw new Error(`Quarter not found: ${quarterId}`);
  }

  const transactions = await store.getTransactionsByDateRange(
    quarter.user_id,
    quarter.period_start,
    quarter.period_end
  );

  const blockingQueue = [];
  const totalCount = transactions.length;

  for (const txn of transactions) {
    const classification = await store.getClassificationByTxnId(txn.txn_id) || {};    

    // Use centralized blocker evaluation logic
    const evaluation = evaluateTransaction(txn, classification);

    if (evaluation.is_blocking_export) {
      blockingQueue.push({
        txn_id: txn.txn_id,
        blocker_type: evaluation.blockers[0],
        reason_codes: evaluation.reason_codes,
        queue_rank: getQueueRank(evaluation.blockers[0])
      });
    }
  }

  blockingQueue.sort((a, b) => a.queue_rank - b.queue_rank);

  const blockingCount = blockingQueue.length;
  const readinessPct = totalCount === 0 ? 100 : Math.round(((totalCount - blockingCount) / totalCount) * 100);

  const metrics = {
    quarter_id: quarterId,
    total_txns_in_period: totalCount,
    blocking_txns_count: blockingCount,
    readiness_pct: readinessPct,
    blocking_queue: blockingQueue
  };

  await store.upsertQuarterMetrics(metrics);

  if (blockingCount === 0 && (quarter.status === "open" || quarter.status === undefined)) {
    await store.upsertQuarter({
      ...quarter,
      status: "ready"
    });
  } else if (blockingCount > 0 && quarter.status === "ready") {
    await store.upsertQuarter({
      ...quarter,
      status: "open"
    });
  }

  return metrics;
}

function getQueueRank(blockerType) {
  const ranks = {
    "missing_category": 1,
    "missing_business_personal": 2,
    "missing_split_pct": 3,
    "duplicate_unresolved": 4
  };
  return ranks[blockerType] || 99;
}

async function createQuarter(store, { userId, periodStart, periodEnd, quarterLabel }) {
  const quarter = {
    user_id: userId,
    period_start: periodStart,
    period_end: periodEnd,
    quarter_label: quarterLabel,
    status: "open",
    last_exported_at: null
  };
  return await store.upsertQuarter(quarter);
}

module.exports = {
  calculateQuarterMetrics,
  createQuarter
};
