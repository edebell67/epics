const fs = require('fs');
const path = require('path');
const assert = require('assert');

const { buildAccountantReadyPackage } = require('./src/services/exportPackageBuilderService');

const positiveFixturePath = path.join(__dirname, 'test_fixtures', 'export_package_snapshot_fixture.json');
const negativeFixturePath = path.join(__dirname, 'test_fixtures', 'export_package_snapshot_connector_edge_fixture.json');

const positiveFixture = JSON.parse(fs.readFileSync(positiveFixturePath, 'utf8'));
const negativeFixture = JSON.parse(fs.readFileSync(negativeFixturePath, 'utf8'));

const readCompatibilityValidation = (exportPackage) => JSON.parse(
  exportPackage.files.find((file) => file.name === 'compatibility_validation.json').content.toString('utf8')
);

const positivePackage = buildAccountantReadyPackage(positiveFixture);
const positiveValidation = readCompatibilityValidation(positivePackage);

assert.strictEqual(positiveValidation.mapping_results.generic_export_mapping.valid, true);
assert.strictEqual(positiveValidation.mapping_results.xero_compatible_mapping.valid, true);
assert.strictEqual(positiveValidation.mapping_results.quickbooks_compatible_mapping.valid, true);
assert.strictEqual(positiveValidation.validation_errors.length, 0);

const negativePackage = buildAccountantReadyPackage(negativeFixture);
const negativeValidation = readCompatibilityValidation(negativePackage);

assert.strictEqual(negativeValidation.mapping_results.generic_export_mapping.valid, true);
assert.strictEqual(negativeValidation.mapping_results.xero_compatible_mapping.valid, false);
assert.strictEqual(negativeValidation.mapping_results.quickbooks_compatible_mapping.valid, false);
assert.ok(
  negativeValidation.validation_errors.some((entry) => entry.mapping === 'xero_compatible_mapping' && entry.source_field === 'counterparty_reference'),
  'Expected Xero-compatible validation error for connector field-length guardrail.'
);
assert.ok(
  negativeValidation.validation_errors.some((entry) => entry.mapping === 'quickbooks_compatible_mapping' && entry.source_field === 'counterparty_reference'),
  'Expected QuickBooks-compatible validation error for connector field-length guardrail.'
);

console.log('verify_export_compatibility=PASS');
console.log(JSON.stringify({
  positive_errors: positiveValidation.validation_errors.length,
  negative_errors: negativeValidation.validation_errors.length,
  quickbooks_valid: negativeValidation.mapping_results.quickbooks_compatible_mapping.valid,
  xero_valid: negativeValidation.mapping_results.xero_compatible_mapping.valid
}));
