const assert = require('assert');

const {
  buildCorrectionAuditPayloads,
  validateArchiveRequest,
  validateCorrectionRequest,
  validateItemUpdate
} = require('./src/services/monetaryIntegrityService');
const {
  classifyVatType,
  deriveQuarterReference,
  validateAndClassifyMonetaryPayload
} = require('./src/services/vatQuarterClassificationService');

const committedInvoice = {
  id: '11111111-1111-1111-1111-111111111111',
  type: 'invoice',
  status: 'confirmed',
  payment_status: 'sent',
  amount: 120,
  currency: 'GBP',
  net_amount: 100,
  gross_amount: 120,
  vat_amount: 20,
  vat_rate: 20,
  quarter_ref: 'Q1-2026',
  device_id: 'device-1',
  created_at: '2026-03-01T09:00:00.000Z',
  updated_at: '2026-03-02T09:00:00.000Z'
};

const mutationValidation = validateItemUpdate(committedInvoice, { amount: 150 });
assert(!mutationValidation.valid, 'Committed monetary amount edits should be rejected');
assert(
  mutationValidation.errors.some((error) => error.includes('immutable fields')),
  'Mutation rejection should explain immutable-field protection'
);

const transitionValidation = validateItemUpdate(committedInvoice, { status: 'draft' });
assert(!transitionValidation.valid, 'Invalid lifecycle transition should be rejected');
assert(
  transitionValidation.errors.some((error) => error.includes('Invalid status transition')),
  'Status transition rejection should be explainable'
);

const archiveValidation = validateArchiveRequest(committedInvoice);
assert(!archiveValidation.valid, 'Committed monetary item archive/delete should be rejected');

const correctionValidation = validateCorrectionRequest(
  committedInvoice,
  'replace',
  'Sent invoice with wrong gross amount',
  {
    amount: 144,
    net_amount: 120,
    vat_amount: 24,
    transaction_date: '2026-03-15',
    raw_note: 'Corrected replacement invoice'
  }
);
assert(correctionValidation.valid, 'Replacement correction should validate');
assert(
  correctionValidation.immutableChanges.includes('amount'),
  'Replacement correction should track immutable field changes'
);

const replacementItem = {
  id: '22222222-2222-2222-2222-222222222222',
  status: 'confirmed',
  device_id: 'device-1',
  created_at: '2026-03-03T09:00:00.000Z',
  updated_at: '2026-03-03T09:00:00.000Z'
};

const auditPayloads = buildCorrectionAuditPayloads({
  action: 'replace',
  originalItem: committedInvoice,
  replacementItem,
  reason: 'Sent invoice with wrong gross amount',
  userId: '33333333-3333-3333-3333-333333333333',
  deviceId: 'device-1'
});

assert.strictEqual(auditPayloads.length, 2, 'Replacement correction should emit traceable audit payloads');
assert.strictEqual(auditPayloads[0].diff_log.correction_type, 'replace');
assert.strictEqual(auditPayloads[0].diff_log.superseded_by, replacementItem.id);
assert.strictEqual(auditPayloads[1].diff_log.supersedes, committedInvoice.id);

const invoiceClassification = validateAndClassifyMonetaryPayload({
  entityType: 'invoice',
  transactionDate: '2026-03-31',
  amount: 120,
  vat_rate: 20
});
assert.strictEqual(invoiceClassification.net_amount, 100, 'Invoice gross amount should resolve deterministic net');
assert.strictEqual(invoiceClassification.vat_amount, 20, 'Invoice gross amount should resolve deterministic VAT');
assert.strictEqual(invoiceClassification.vat_type, 'output', 'Invoice should classify as output VAT');
assert.strictEqual(invoiceClassification.quarter_reference, 'Q1-2026', 'Quarter should derive from March boundary');

const receiptClassification = validateAndClassifyMonetaryPayload({
  entityType: 'receipt_expense',
  transactionDate: '2026-04-01',
  net_amount: 50,
  vat_rate: 20
});
assert.strictEqual(receiptClassification.gross_amount, 60, 'Receipt net amount should resolve deterministic gross');
assert.strictEqual(receiptClassification.vat_type, 'input', 'Receipt should classify as input VAT');
assert.strictEqual(receiptClassification.quarter_reference, 'Q2-2026', 'Quarter should derive from April boundary');

assert.strictEqual(classifyVatType({ entityType: 'invoice', vatType: 'Output' }), 'output');
assert.strictEqual(deriveQuarterReference('2026-12-31'), 'Q4-2026');

assert.throws(
  () => validateAndClassifyMonetaryPayload({
    entityType: 'invoice',
    transactionDate: '2026-03-11',
    net_amount: 100,
    vat_amount: 10,
    gross_amount: 110,
    vat_rate: 20
  }),
  /Invalid VAT combination/,
  'Invalid VAT combinations should be rejected before commit'
);

assert.throws(
  () => validateAndClassifyMonetaryPayload({
    entityType: 'invoice',
    transactionDate: '2026-03-11',
    amount: 120,
    quarterReference: 'Q2-2026',
    vat_rate: 20
  }),
  /quarter_reference "Q2-2026" does not match/,
  'Quarter mismatches should be rejected'
);

console.log('monetary_integrity_ok');
console.log('mutation_blocked=true');
console.log('invalid_transition_rejected=true');
console.log('correction_metadata_traced=true');
console.log('vat_totals_deterministic=true');
console.log('quarter_boundaries_deterministic=true');
console.log('invalid_amount_combinations_rejected=true');
