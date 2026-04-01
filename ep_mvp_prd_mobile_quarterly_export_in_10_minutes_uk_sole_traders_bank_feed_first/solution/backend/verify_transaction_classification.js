const assert = require('assert');
const {
  importNormalizedTransactions,
  updateTransactionClassification
} = require('./src/services/transactionImportService');
const { MemoryTransactionImportStore } = require('./src/testing/memoryTransactionImportStore');

async function main() {
  const store = new MemoryTransactionImportStore();
  const now = new Date('2026-03-21T09:30:00.000Z');
  const bankAccount = {
    bank_account_id: 'bank-account-001',
    user_id: 'user-001',
    provider_name: 'mock_open_banking',
    currency: 'GBP'
  };

  const providerPayload = [
    {
      id: 'txn-abc-123',
      booking_date: '2026-03-20',
      amount: -45.50,
      description: 'Starbucks London',
      merchant: 'Starbucks',
      booking_status: 'booked'
    }
  ];

  console.log('Testing: Classification Initialization on Import...');
  const importSummary = await importNormalizedTransactions({
    store,
    bankAccount,
    rawTransactions: providerPayload,
    now
  });

  assert.strictEqual(importSummary.inserted, 1);
  const txns = store.getTransactionsForAccount(bankAccount.bank_account_id);
  const txnId = txns[0].txn_id;

  const classification = await store.getClassificationByTxnId(txnId);
  assert(classification, 'Classification should be created for new transaction');
  assert.strictEqual(classification.txn_id, txnId);
  assert.strictEqual(classification.category_code, null);
  assert.strictEqual(classification.review_required, true);
  console.log('PASS: Classification initialized with defaults.');

  console.log('Testing: Classification Update with Audit Trail...');
  const updated = await updateTransactionClassification({
    store,
    txnId,
    updates: {
      category_code: 'EXP_MEALS',
      business_personal: 'BUSINESS'
    },
    changedBy: 'test-user',
    now: new Date('2026-03-21T10:00:00.000Z')
  });

  assert.strictEqual(updated.category_code, 'EXP_MEALS');
  assert.strictEqual(updated.business_personal, 'BUSINESS');
  assert.strictEqual(updated.review_required, false, 'Should be resolved now');

  const auditTrail = await store.getAuditTrailForClassification(updated.classification_id);
  assert.strictEqual(auditTrail.length, 2, 'Should have 2 audit entries (category and biz/pers)');
  
  const categoryAudit = auditTrail.find(e => e.field_name === 'category_code');
  assert.strictEqual(categoryAudit.previous_value, null);
  assert.strictEqual(categoryAudit.new_value, 'EXP_MEALS');
  assert.strictEqual(categoryAudit.changed_by, 'test-user');
  
  const bizPersAudit = auditTrail.find(e => e.field_name === 'business_personal');
  assert.strictEqual(bizPersAudit.previous_value, null);
  assert.strictEqual(bizPersAudit.new_value, 'BUSINESS');
  
  console.log('PASS: Update success and audit trail verified.');

  console.log('Testing: Data Integrity (Original Transaction payload)...');
  const txnAfter = txns[0];
  assert.strictEqual(txnAfter.merchant, 'Starbucks');
  assert.strictEqual(txnAfter.amount, 45.50);
  assert.strictEqual(txnAfter.category_code, undefined, 'Original transaction should NOT have classification fields injected');
  console.log('PASS: Original transaction remained immutable.');

  console.log('Testing: Rollback on failed classification update...');
  // Since MemoryStore implements simple snapshotting, let's verify it works for classifications too
  try {
    await store.runInTransaction(async (transactionalStore) => {
      await transactionalStore.upsertTransactionClassification({
        txn_id: txnId,
        category_code: 'SHOULD_NOT_EXIST'
      });
      throw new Error('Simulated failure during classification write');
    });
  } catch (e) {
    // Expected
  }
  
  const finalClassification = await store.getClassificationByTxnId(txnId);
  assert.strictEqual(finalClassification.category_code, 'EXP_MEALS', 'Rollback should restore previous classification state');
  console.log('PASS: Transactional integrity for classifications verified.');

  console.log('\nALL VERIFICATION SCENARIOS PASSED.');
}

main().catch((error) => {
  console.error('\nFAIL:', error);
  process.exitCode = 1;
});
