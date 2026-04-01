const assert = require('assert');
const {
  DEFAULT_BACKFILL_DAYS,
  computeBackfillStartDate,
  importNormalizedTransactions,
  refreshBankAccount
} = require('./src/services/transactionImportService');
const { MemoryTransactionImportStore } = require('./src/testing/memoryTransactionImportStore');

async function main() {
  const store = new MemoryTransactionImportStore();
  const now = new Date('2026-03-18T18:35:00.000Z');
  const bankAccount = {
    bank_account_id: 'bank-account-001',
    user_id: 'user-001',
    provider_name: 'mock_open_banking',
    currency: 'GBP'
  };

  const expectedBackfillStart = computeBackfillStartDate(now, DEFAULT_BACKFILL_DAYS);
  assert.strictEqual(expectedBackfillStart, '2025-12-18');

  const providerPayload = [
    {
      id: 'txn-100',
      booking_date: '2026-03-10',
      amount: -125.75,
      description: 'Office Depot',
      merchant: 'Office Depot',
      balance: 1200.11,
      booking_status: 'booked'
    },
    {
      id: 'txn-101',
      booking_date: '2026-03-11',
      amount: 890.4,
      description: 'Client invoice paid',
      counterparty: 'Client Payment',
      balance: 2090.51
    },
    {
      transaction_id: 'txn-no-ref',
      booking_date: '2026-03-12',
      amount: -9.99,
      description: 'Monthly fee'
    },
    {
      id: 'invalid-zero-amount',
      booking_date: '2026-03-12',
      amount: 0,
      description: 'Should be skipped'
    }
  ];

  const providerClient = {
    async fetchTransactions({ fromDate, cursor, requestedWindowDays }) {
      assert.strictEqual(fromDate, expectedBackfillStart);
      assert.strictEqual(cursor, null);
      assert.strictEqual(requestedWindowDays, DEFAULT_BACKFILL_DAYS);
      return {
        transactions: providerPayload,
        nextCursor: 'cursor-001'
      };
    }
  };

  const firstImport = await refreshBankAccount({
    store,
    providerClient,
    bankAccount,
    now,
    requestedWindowDays: DEFAULT_BACKFILL_DAYS,
    importTriggeredBy: 'initial_backfill'
  });

  assert.strictEqual(firstImport.from_date, '2025-12-18');
  assert.strictEqual(firstImport.received, 4);
  assert.strictEqual(firstImport.normalized, 3);
  assert.strictEqual(firstImport.inserted, 3);
  assert.strictEqual(firstImport.duplicate_suppressed, 0);
  assert.strictEqual(firstImport.skipped_invalid, 1);
  assert.strictEqual(firstImport.skipped_reasons.missing_required_fields, 1);

  const importedTransactions = store.getTransactionsForAccount(bankAccount.bank_account_id);
  assert.strictEqual(importedTransactions.length, 3);
  assert.deepStrictEqual(
    importedTransactions.map((transaction) => ({
      bank_txn_ref: transaction.bank_txn_ref,
      date: transaction.date,
      merchant: transaction.merchant,
      amount: transaction.amount,
      direction: transaction.direction,
      bank_account_id: transaction.bank_account_id,
      currency: transaction.currency,
      source_hash_present: Boolean(transaction.source_hash)
    })),
    [
      {
        bank_txn_ref: 'txn-100',
        date: '2026-03-10',
        merchant: 'Office Depot',
        amount: 125.75,
        direction: 'out',
        bank_account_id: 'bank-account-001',
        currency: 'GBP',
        source_hash_present: true
      },
      {
        bank_txn_ref: 'txn-101',
        date: '2026-03-11',
        merchant: 'Client Payment',
        amount: 890.4,
        direction: 'in',
        bank_account_id: 'bank-account-001',
        currency: 'GBP',
        source_hash_present: true
      },
      {
        bank_txn_ref: 'txn-no-ref',
        date: '2026-03-12',
        merchant: 'Monthly fee',
        amount: 9.99,
        direction: 'out',
        bank_account_id: 'bank-account-001',
        currency: 'GBP',
        source_hash_present: true
      }
    ]
  );

  const secondImport = await importNormalizedTransactions({
    store,
    bankAccount,
    rawTransactions: providerPayload,
    now: new Date('2026-03-18T18:36:00.000Z'),
    importTriggeredBy: 'manual_refresh',
    requestedWindowDays: DEFAULT_BACKFILL_DAYS,
    fromDate: null,
    nextCursor: 'cursor-002'
  });

  assert.strictEqual(secondImport.inserted, 0);
  assert.strictEqual(secondImport.duplicate_suppressed, 3);
  assert.strictEqual(store.countTransactions(), 3);

  const checkpointAfterRefresh = await store.getImportCheckpoint(bankAccount.bank_account_id);
  assert.strictEqual(checkpointAfterRefresh.last_status, 'completed');
  assert.strictEqual(checkpointAfterRefresh.last_successful_cursor, 'cursor-002');
  assert.strictEqual(checkpointAfterRefresh.last_inserted_count, 0);
  assert.strictEqual(checkpointAfterRefresh.last_duplicate_suppressed_count, 3);

  let failure;
  try {
    await importNormalizedTransactions({
      store,
      bankAccount,
      rawTransactions: [
        {
          id: 'txn-102',
          booking_date: '2026-03-13',
          amount: -55.11,
          description: 'Travel expense'
        },
        {
          id: 'txn-103',
          booking_date: '2026-03-14',
          amount: -12.0,
          description: 'Parking'
        }
      ],
      now: new Date('2026-03-18T18:37:00.000Z'),
      importTriggeredBy: 'manual_refresh',
      requestedWindowDays: DEFAULT_BACKFILL_DAYS,
      failAfterTransactionCount: 1,
      nextCursor: 'cursor-003'
    });
  } catch (error) {
    failure = error;
  }

  assert(failure, 'Expected simulated failure to throw');
  assert.strictEqual(store.countTransactions(), 3, 'rollback should prevent partial inserts');

  const checkpointAfterFailure = await store.getImportCheckpoint(bankAccount.bank_account_id);
  assert.strictEqual(checkpointAfterFailure.last_status, 'failed');
  assert.strictEqual(checkpointAfterFailure.last_error, 'Simulated import failure after 1 transaction(s)');
  assert.strictEqual(checkpointAfterFailure.last_successful_cursor, 'cursor-002');

  const failedRun = store.getImportRun(failure.importSummary.import_run_id);
  assert.strictEqual(failedRun.status, 'failed');
  assert.strictEqual(failedRun.error_message, 'Simulated import failure after 1 transaction(s)');

  console.log('PASS: initial import defaults to a 90-day backfill window');
  console.log('PASS: re-import suppresses duplicates and preserves transaction count');
  console.log('PASS: normalized transactions expose canonical export fields');
  console.log('PASS: failed imports roll back writes and preserve retry-safe checkpoints');
}

main().catch((error) => {
  console.error('FAIL:', error.message);
  process.exitCode = 1;
});
