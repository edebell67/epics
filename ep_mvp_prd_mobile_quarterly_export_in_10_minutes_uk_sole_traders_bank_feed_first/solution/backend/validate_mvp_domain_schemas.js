const fs = require('fs');
const path = require('path');

const schemaPath = path.join(__dirname, 'src', 'models', 'mvp_domain_schemas.json');
const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));

const expectedEntities = [
  'User',
  'BusinessProfile',
  'BankAccount',
  'BankTransaction',
  'TransactionClassification',
  'Evidence',
  'EvidenceLink',
  'Quarter',
  'QuarterMetrics',
  'Rule'
];

const expectedCategoryCodes = [
  'INCOME_SALES',
  'INCOME_OTHER',
  'EXP_COGS',
  'EXP_SUBCONTRACTORS',
  'EXP_TRAVEL',
  'EXP_VEHICLE',
  'EXP_MEALS',
  'EXP_ACCOM',
  'EXP_RENT_UTIL',
  'EXP_COMMS',
  'EXP_SOFTWARE',
  'EXP_MARKETING',
  'EXP_INSURANCE',
  'EXP_BANK_FEES',
  'EXP_PROFESSIONAL',
  'EXP_OFFICE',
  'EXP_TRAINING',
  'EXP_MISC'
];

const expectedTransactionsFields = [
  'txn_id',
  'date',
  'merchant',
  'amount',
  'direction',
  'category_code',
  'category_name',
  'confidence',
  'business_personal',
  'is_split',
  'split_business_pct',
  'matched_evidence_ids',
  'bank_account_id',
  'bank_txn_ref'
];

const expectedEvidenceFields = [
  'evidence_id',
  'type',
  'captured_at',
  'doc_date',
  'merchant',
  'amount',
  'storage_link',
  'extraction_confidence',
  'matched_bank_txn_id',
  'user_confirmed'
];

const expectedSummaryFields = [
  'period_start',
  'period_end',
  'category_code',
  'category_name',
  'total_in',
  'total_out',
  'count',
  'unresolved_count'
];

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function extractFieldNames(contractName) {
  return schema.quarterly_pack_contracts[contractName].fields.map((field) => field.name);
}

assert(schema.schema_version, 'schema_version is required');
assert(schema.entities, 'entities block is required');

for (const entityName of expectedEntities) {
  assert(schema.entities[entityName], `missing entity: ${entityName}`);
  assert(schema.entities[entityName].fields, `missing fields for entity: ${entityName}`);
}

const categoryCodes = schema.category_taxonomy.categories.map((item) => item.code);
assert(
  JSON.stringify(categoryCodes) === JSON.stringify(expectedCategoryCodes),
  `category codes do not match epic list exactly: ${categoryCodes.join(', ')}`
);

const tagCodes = schema.category_taxonomy.tags.map((item) => item.code);
for (const tagCode of tagCodes) {
  assert(!categoryCodes.includes(tagCode), `tag overlaps category code: ${tagCode}`);
}

const classificationFields = schema.entities.TransactionClassification.fields;
for (const field of ['category_code', 'business_personal', 'is_split', 'split_business_pct', 'confidence', 'duplicate_resolution', 'audit_trail']) {
  assert(classificationFields[field], `classification field missing: ${field}`);
}

const auditEntryFields = schema.audit_change_entry.fields;
for (const field of ['changed_at', 'changed_by', 'previous_value', 'new_value']) {
  assert(auditEntryFields[field], `audit field missing: ${field}`);
}

const nullableRules = new Set(schema.nullable_rules.map((rule) => rule.field));
for (const field of [
  'TransactionClassification.category_code',
  'TransactionClassification.business_personal',
  'TransactionClassification.split_business_pct',
  'TransactionClassification.duplicate_resolution'
]) {
  assert(nullableRules.has(field), `nullable rule missing: ${field}`);
}

assert(
  JSON.stringify(extractFieldNames('Transactions.csv')) === JSON.stringify(expectedTransactionsFields),
  'Transactions.csv field contract does not match the epic order'
);
assert(
  JSON.stringify(extractFieldNames('EvidenceIndex.csv')) === JSON.stringify(expectedEvidenceFields),
  'EvidenceIndex.csv field contract does not match the epic order'
);
assert(
  JSON.stringify(extractFieldNames('QuarterlySummary.csv')) === JSON.stringify(expectedSummaryFields),
  'QuarterlySummary.csv field contract does not match the epic order'
);

assert(schema.quarterly_pack_contracts['QuarterlyPack.pdf'], 'QuarterlyPack.pdf contract missing');
assert(schema.relationship_notes.length >= 6, 'relationship notes are incomplete');

console.log('mvp_domain_schema_ok');
console.log(`entities=${expectedEntities.length}`);
console.log(`category_codes=${categoryCodes.length}`);
console.log(`transaction_fields=${expectedTransactionsFields.length}`);
console.log(`evidence_fields=${expectedEvidenceFields.length}`);
console.log(`summary_fields=${expectedSummaryFields.length}`);
