const fs = require('fs');
const path = require('path');
const assert = require('assert');

const {
  STRUCTURED_EXPORT_COLUMNS,
  buildAccountantReadyPackage
} = require('./src/services/exportPackageBuilderService');

const fixturePath = path.join(__dirname, 'test_fixtures', 'export_package_snapshot_fixture.json');
const snapshotFixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));

const firstRun = buildAccountantReadyPackage(snapshotFixture);
const secondRun = buildAccountantReadyPackage(snapshotFixture);

const expectedFiles = [
  'compatibility_validation.json',
  'generic_export_mapping.json',
  'integrity_report.json',
  'package_manifest.json',
  'quickbooks_compatible_mapping.json',
  'snapshot_metadata.json',
  'structured_csv.csv',
  'vat_summary_document.pdf',
  'xero_compatible_mapping.json'
];

assert.deepStrictEqual(
  firstRun.files.map((file) => file.name),
  expectedFiles,
  'Package must include all accountant-ready files.'
);

const structuredCsv = firstRun.files.find((file) => file.name === 'structured_csv.csv').content.toString('utf8').trim().split('\n');
assert.strictEqual(
  structuredCsv[0],
  STRUCTURED_EXPORT_COLUMNS.join(','),
  'Structured CSV header must align to the canonical schema export order.'
);

const metadata = JSON.parse(firstRun.files.find((file) => file.name === 'snapshot_metadata.json').content.toString('utf8'));
assert.strictEqual(metadata.quarter_label, snapshotFixture.quarter_reference);
assert.strictEqual(metadata.version_number, snapshotFixture.version_number);

const integrityReport = JSON.parse(firstRun.files.find((file) => file.name === 'integrity_report.json').content.toString('utf8'));
assert.strictEqual(integrityReport.invalid_records.length, 0, 'Fixture records should satisfy canonical validation.');
assert.strictEqual(integrityReport.checks.totals_match.net_amount, true);
assert.strictEqual(integrityReport.checks.totals_match.vat_amount, true);
assert.strictEqual(integrityReport.checks.totals_match.gross_amount, true);
assert.strictEqual(integrityReport.checks.vat_totals_match, true);

const compatibilityValidation = JSON.parse(firstRun.files.find((file) => file.name === 'compatibility_validation.json').content.toString('utf8'));
assert.ok(Array.isArray(compatibilityValidation.canonical_field_set), 'Compatibility validation must expose a canonical field set.');
assert.strictEqual(compatibilityValidation.canonical_field_set.length, STRUCTURED_EXPORT_COLUMNS.length);
assert.strictEqual(compatibilityValidation.validation_errors.length, 0, 'Positive fixture must not emit compatibility validation errors.');
assert.strictEqual(compatibilityValidation.mapping_results.generic_export_mapping.valid, true);
assert.strictEqual(compatibilityValidation.mapping_results.xero_compatible_mapping.valid, true);
assert.strictEqual(compatibilityValidation.mapping_results.quickbooks_compatible_mapping.valid, true);

assert.deepStrictEqual(
  firstRun.files.map((file) => ({ name: file.name, sha256: file.sha256 })),
  secondRun.files.map((file) => ({ name: file.name, sha256: file.sha256 })),
  'Re-exporting the same snapshot must yield equivalent file contents.'
);

assert.strictEqual(
  firstRun.manifest.package_checksum,
  secondRun.manifest.package_checksum,
  'Package manifest checksum must remain stable for the same snapshot.'
);

console.log('verify_export_package_builder=PASS');
