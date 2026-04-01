const crypto = require("crypto");
const { normalizeBatch } = require("./openBankingAdapter");
const { findMatchingRule, applyRuleToClassification } = require("./merchantRuleService");

const DEFAULT_BACKFILL_DAYS = 90;

function toIsoTimestamp(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  return date.toISOString();
}

function computeBackfillStartDate(now = new Date(), windowDays = DEFAULT_BACKFILL_DAYS) {
  const date = now instanceof Date ? new Date(now.getTime()) : new Date(now);
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCDate(date.getUTCDate() - windowDays);
  return date.toISOString().slice(0, 10);
}

function summarizeSkipped(skipped) {
  return skipped.reduce((accumulator, item) => {
    const key = item.reason || "unknown";
    accumulator[key] = (accumulator[key] || 0) + 1;
    return accumulator;
  }, {});
}

function createImportRunRecord({
  bankAccount,
  importTriggeredBy,
  requestedWindowDays,
  fetchStartedAt,
  fromDate,
  cursorUsed
}) {
  return {
    import_run_id: crypto.randomUUID(),
    bank_account_id: bankAccount.bank_account_id,
    user_id: bankAccount.user_id,
    provider_name: bankAccount.provider_name,
    import_triggered_by: importTriggeredBy,
    requested_window_days: requestedWindowDays,
    fetch_started_at: fetchStartedAt,
    from_date: fromDate,
    cursor_used: cursorUsed,
    status: "started"
  };
}

async function importNormalizedTransactions({
  store,
  bankAccount,
  rawTransactions,
  now = new Date(),
  importTriggeredBy = "manual_refresh",
  requestedWindowDays = DEFAULT_BACKFILL_DAYS,
  fromDate = null,
  nextCursor = null,
  failAfterTransactionCount = null
}) {
  const importedAt = toIsoTimestamp(now);
  const { validTransactions, skipped } = normalizeBatch(rawTransactions, bankAccount);
  const importRun = createImportRunRecord({
    bankAccount,
    importTriggeredBy,
    requestedWindowDays,
    fetchStartedAt: importedAt,
    fromDate,
    cursorUsed: nextCursor
  });
  await store.startImportRun(importRun);

  try {
    const transactionSummary = await store.runInTransaction(async (transactionalStore) => {
      let inserted = 0;
      let deduped = 0;
      let processed = 0;
      let latestTransactionDate = null;

      for (const transaction of validTransactions) {
        processed += 1;
        if (failAfterTransactionCount !== null && processed > failAfterTransactionCount) {
          throw new Error(`Simulated import failure after ${failAfterTransactionCount} transaction(s)`);
        }

        const result = await transactionalStore.upsertBankTransaction({
          ...transaction,
          imported_at: importedAt
        });

        if (result.status === "inserted") {
          inserted += 1;

          // Initialise classification for new transactions
          // Version: V20260322_1730
          // Datetime: 2026-03-22 17:30
          const classification = {
            txn_id: result.record.txn_id,
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
          };

          // Apply merchant rules if matching
          const rule = await findMatchingRule({
            store: transactionalStore,
            userId: bankAccount.user_id,
            merchantName: result.record.merchant
          });

          if (rule) {
            const updates = applyRuleToClassification(rule, classification);
            Object.assign(classification, updates);
          }

          await transactionalStore.upsertTransactionClassification(classification);
        } else {
          deduped += 1;
        }

        if (!latestTransactionDate || result.record.date > latestTransactionDate) {
          latestTransactionDate = result.record.date;
        }
      }

      return {
        inserted,
        deduped,
        processed,
        latestTransactionDate
      };
    });

    const summary = {
      status: "completed",
      import_run_id: importRun.import_run_id,
      bank_account_id: bankAccount.bank_account_id,
      requested_window_days: requestedWindowDays,
      from_date: fromDate,
      next_cursor: nextCursor,
      received: Array.isArray(rawTransactions) ? rawTransactions.length : 0,    
      normalized: validTransactions.length,
      skipped_invalid: skipped.length,
      skipped_reasons: summarizeSkipped(skipped),
      inserted: transactionSummary.inserted,
      duplicate_suppressed: transactionSummary.deduped,
      imported_at: importedAt,
      latest_transaction_date: transactionSummary.latestTransactionDate
    };

    await store.completeImportRun(importRun.import_run_id, summary);
    await store.updateImportCheckpoint(bankAccount.bank_account_id, {
      bank_account_id: bankAccount.bank_account_id,
      last_attempt_at: importedAt,
      last_successful_import_at: importedAt,
      last_status: "completed",
      last_error: null,
      last_requested_window_days: requestedWindowDays,
      last_backfill_start_date: fromDate,
      last_successful_cursor: nextCursor,
      last_received_count: summary.received,
      last_inserted_count: summary.inserted,
      last_duplicate_suppressed_count: summary.duplicate_suppressed,
      last_skipped_invalid_count: summary.skipped_invalid,
      latest_transaction_date: summary.latest_transaction_date
    });

    return summary;
  } catch (error) {
    const failureSummary = {
      status: "failed",
      import_run_id: importRun.import_run_id,
      bank_account_id: bankAccount.bank_account_id,
      requested_window_days: requestedWindowDays,
      from_date: fromDate,
      next_cursor: nextCursor,
      received: Array.isArray(rawTransactions) ? rawTransactions.length : 0,    
      normalized: validTransactions.length,
      skipped_invalid: skipped.length,
      skipped_reasons: summarizeSkipped(skipped),
      error_message: error.message,
      failed_at: importedAt
    };

    await store.failImportRun(importRun.import_run_id, failureSummary);
    await store.updateImportCheckpoint(bankAccount.bank_account_id, {
      bank_account_id: bankAccount.bank_account_id,
      last_attempt_at: importedAt,
      last_status: "failed",
      last_error: error.message,
      last_requested_window_days: requestedWindowDays,
      last_backfill_start_date: fromDate,
      last_successful_cursor: null
    });

    error.importSummary = failureSummary;
    throw error;
  }
}

async function refreshBankAccount({
  store,
  providerClient,
  bankAccount,
  now = new Date(),
  requestedWindowDays = DEFAULT_BACKFILL_DAYS,
  importTriggeredBy = "refresh"
}) {
  const checkpoint = await store.getImportCheckpoint(bankAccount.bank_account_id);
  const fromDate = checkpoint?.last_successful_import_at
    ? null
    : computeBackfillStartDate(now, requestedWindowDays);
  const cursor = checkpoint?.last_successful_cursor || null;
  const payload = await providerClient.fetchTransactions({
    bankAccount,
    fromDate,
    cursor,
    requestedWindowDays
  });

  return importNormalizedTransactions({
    store,
    bankAccount,
    rawTransactions: payload.transactions || [],
    now,
    importTriggeredBy,
    requestedWindowDays,
    fromDate,
    nextCursor: payload.nextCursor ?? cursor
  });
}

/**
 * Updates a transaction classification with full audit trail.
 * Version: V20260322_1730
 * Datetime: 2026-03-22 17:30
 */
async function updateTransactionClassification({
  store,
  txnId,
  updates,
  changedBy = "user",
  now = new Date()
}) {
  return await store.runInTransaction(async (transactionalStore) => {
    const current = await transactionalStore.getClassificationByTxnId(txnId);   
    if (!current) {
      throw new Error(`Classification not found for transaction ${txnId}`);     
    }

    const changedAt = toIsoTimestamp(now);
    const updatedRecord = { ...current };

    // Identify changes and record audit entries
    for (const [field, newValue] of Object.entries(updates)) {
      const previousValue = current[field];
      if (previousValue !== newValue) {
        updatedRecord[field] = newValue;

        await transactionalStore.addClassificationAuditEntry({
          classification_id: current.classification_id,
          field_name: field,
          previous_value: previousValue,
          new_value: newValue,
          changed_by: changedBy,
          changed_at: changedAt
        });
      }
    }

    updatedRecord.updated_at = changedAt;
    updatedRecord.applied_by = changedBy;

    // Resolve logic: Resolved if (Category AND Biz/Pers set) OR Duplicate Resolved
    const isClassified = !!(updatedRecord.category_code && updatedRecord.business_personal);
    const isDuplicateResolved = updatedRecord.duplicate_resolution !== "NONE";  

    updatedRecord.review_required = !(isClassified || isDuplicateResolved);     

    return await transactionalStore.upsertTransactionClassification(updatedRecord);
  });
}

/**
 * Accepts a suggested category for a transaction.
 * Version: V20260321_1000
 */
async function acceptCategorySuggestion({ store, txnId, categoryCode, categoryName, confidence, acceptedBy = "user", now = new Date() }) {
  return await updateTransactionClassification({
    store,
    txnId,
    updates: {
      category_code: categoryCode,
      category_name: categoryName,
      confidence: confidence
    },
    changedBy: acceptedBy,
    now
  });
}

/**
 * Manually overrides the category for a transaction.
 * Version: V20260321_1000
 */
async function overrideCategory({ store, txnId, categoryCode, categoryName, overriddenBy = "user", now = new Date() }) {
  return await updateTransactionClassification({
    store,
    txnId,
    updates: {
      category_code: categoryCode,
      category_name: categoryName,
      confidence: 1.0 // Manual override is high confidence
    },
    changedBy: overriddenBy,
    now
  });
}

/**
 * Sets the business/personal tagging.
 * Version: V20260321_1000
 */
async function setBusinessPersonal({ store, txnId, businessPersonal, setBy = "user", now = new Date() }) {
  return await updateTransactionClassification({
    store,
    txnId,
    updates: {
      business_personal: businessPersonal
    },
    changedBy: setBy,
    now
  });
}

/**
 * Updates the split percentage for mixed transactions.
 * Version: V20260321_1000
 */
async function updateSplit({ store, txnId, splitBusinessPct, updatedBy = "user", now = new Date() }) {
  return await updateTransactionClassification({
    store,
    txnId,
    updates: {
      is_split: true,
      split_business_pct: splitBusinessPct
    },
    changedBy: updatedBy,
    now
  });
}

/**
 * Resolves a duplicate transaction.
 * Version: V20260321_1000
 */
async function resolveDuplicate({ store, txnId, resolution, duplicateOfTxnId = null, resolvedBy = "user", now = new Date() }) {
  return await updateTransactionClassification({
    store,
    txnId,
    updates: {
      duplicate_resolution: resolution,
      duplicate_of_txn_id: duplicateOfTxnId
    },
    changedBy: resolvedBy,
    now
  });
}

module.exports = {
  DEFAULT_BACKFILL_DAYS,
  computeBackfillStartDate,
  importNormalizedTransactions,
  refreshBankAccount,
  updateTransactionClassification,
  acceptCategorySuggestion,
  overrideCategory,
  setBusinessPersonal,
  updateSplit,
  resolveDuplicate
};
