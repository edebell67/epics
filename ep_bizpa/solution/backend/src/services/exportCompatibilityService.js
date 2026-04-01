const { canonicalSchemas, validateEntityPayload } = require('./canonicalSchemaService');

const CANONICAL_EXPORT_FIELDS = [
  'unique_id',
  'entity_type',
  'transaction_date',
  'created_at',
  'created_by',
  'quarter_reference',
  'counterparty_reference',
  'description',
  'category',
  'net_amount',
  'vat_amount',
  'gross_amount',
  'vat_rate',
  'vat_type',
  'status',
  'commit_mode',
  'source_type'
];

const isPresent = (value) => value !== undefined && value !== null && value !== '';

const stableSortObject = (value) => {
  if (Array.isArray(value)) {
    return value.map(stableSortObject);
  }
  if (!value || typeof value !== 'object') {
    return value;
  }

  return Object.keys(value)
    .sort()
    .reduce((acc, key) => {
      acc[key] = stableSortObject(value[key]);
      return acc;
    }, {});
};

const stableStringify = (value, spacing = 2) => JSON.stringify(stableSortObject(value), null, spacing);

const COMPATIBILITY_MAPPINGS = {
  generic_export_mapping: {
    format_key: 'generic_export_mapping',
    target_name: 'generic_accountant_ready',
    description: 'Canonical accountant-ready mapping aligned to the shared export field dictionary.',
    required_source_fields: CANONICAL_EXPORT_FIELDS,
    target_columns: CANONICAL_EXPORT_FIELDS.map((field) => ({
      target_column: canonicalSchemas.field_dictionary[field].export_column,
      source_field: field,
      required: true,
      data_type: canonicalSchemas.field_dictionary[field].data_type
    })),
    connector_constraints: {}
  },
  xero_compatible_mapping: {
    format_key: 'xero_compatible_mapping',
    target_name: 'xero_compatible',
    description: 'Connector-oriented mapping that keeps canonical records exportable into a Xero-friendly import structure without direct API coupling.',
    required_source_fields: [
      'transaction_date',
      'gross_amount',
      'counterparty_reference',
      'description',
      'unique_id',
      'vat_type',
      'category'
    ],
    target_columns: [
      { target_column: 'Date', source_field: 'transaction_date', required: true, data_type: 'date' },
      { target_column: 'Amount', source_field: 'gross_amount', required: true, data_type: 'decimal(18,2)' },
      { target_column: 'ContactName', source_field: 'counterparty_reference', required: true, data_type: 'string' },
      { target_column: 'Description', source_field: 'description', required: true, data_type: 'string' },
      { target_column: 'Reference', source_field: 'unique_id', required: true, data_type: 'uuid' },
      { target_column: 'TaxType', source_field: 'vat_type', required: true, data_type: 'enum' },
      { target_column: 'AccountCode', source_field: 'category', required: true, data_type: 'string' }
    ],
    connector_constraints: {
      counterparty_reference: { max_length: 120 },
      description: { max_length: 4000 },
      unique_id: { max_length: 255 },
      vat_type: {
        allowed_values: ['input', 'output', 'outside_scope', 'exempt'],
        export_value_map: {
          input: 'INPUT2',
          output: 'OUTPUT2',
          outside_scope: 'NONE',
          exempt: 'EXEMPT'
        }
      }
    }
  },
  quickbooks_compatible_mapping: {
    format_key: 'quickbooks_compatible_mapping',
    target_name: 'quickbooks_compatible',
    description: 'Connector-oriented mapping that keeps canonical records exportable into a QuickBooks-friendly import structure without direct API coupling.',
    required_source_fields: [
      'transaction_date',
      'gross_amount',
      'counterparty_reference',
      'description',
      'unique_id',
      'vat_type',
      'category'
    ],
    target_columns: [
      { target_column: 'TxnDate', source_field: 'transaction_date', required: true, data_type: 'date' },
      { target_column: 'Amount', source_field: 'gross_amount', required: true, data_type: 'decimal(18,2)' },
      { target_column: 'EntityName', source_field: 'counterparty_reference', required: true, data_type: 'string' },
      { target_column: 'Memo', source_field: 'description', required: true, data_type: 'string' },
      { target_column: 'RefNumber', source_field: 'unique_id', required: true, data_type: 'uuid' },
      { target_column: 'TaxCode', source_field: 'vat_type', required: true, data_type: 'enum' },
      { target_column: 'AccountRef', source_field: 'category', required: true, data_type: 'string' }
    ],
    connector_constraints: {
      counterparty_reference: { max_length: 100 },
      description: { max_length: 4000 },
      vat_type: {
        allowed_values: ['input', 'output', 'outside_scope', 'exempt'],
        export_value_map: {
          input: 'INPUT',
          output: 'OUTPUT',
          outside_scope: 'NON',
          exempt: 'EXEMPT'
        }
      }
    }
  }
};

const getFieldType = (field) => canonicalSchemas.shared_fields[field]?.type
  || canonicalSchemas.field_dictionary[field]?.data_type
  || 'string';

const validateValueType = (field, value) => {
  const type = getFieldType(field);
  if (!isPresent(value)) {
    return null;
  }

  if (type === 'uuid') {
    return null;
  }

  if (type === 'date') {
    return Number.isNaN(new Date(value).getTime()) ? `Expected ISO date for ${field}` : null;
  }

  if (type === 'datetime') {
    return Number.isNaN(new Date(value).getTime()) ? `Expected ISO datetime for ${field}` : null;
  }

  if (type.startsWith('decimal')) {
    return Number.isFinite(Number(value)) ? null : `Expected numeric value for ${field}`;
  }

  if (type === 'quarter_label') {
    return new RegExp(canonicalSchemas.quarter_reference.pattern).test(String(value))
      ? null
      : `Expected quarter label for ${field}`;
  }

  if (type === 'enum' || field === 'vat_type' || field === 'commit_mode' || field === 'source_type') {
    const allowedValues = canonicalSchemas.shared_fields[field]?.allowed_values;
    if (allowedValues && !allowedValues.includes(value)) {
      return `Unsupported ${field} value "${value}"`;
    }
  }

  return null;
};

const buildMappingDefinitionErrors = (mapping) => mapping.target_columns
  .filter((column) => !CANONICAL_EXPORT_FIELDS.includes(column.source_field))
  .map((column) => ({
    level: 'mapping',
    target_column: column.target_column,
    source_field: column.source_field,
    issue: `Unknown canonical source field "${column.source_field}".`
  }));

const validateConnectorConstraint = (mapping, transaction, field) => {
  const constraints = mapping.connector_constraints[field];
  if (!constraints || !isPresent(transaction[field])) {
    return null;
  }

  const value = String(transaction[field]);
  if (constraints.max_length && value.length > constraints.max_length) {
    return `${field} exceeds ${constraints.max_length} characters`;
  }

  if (constraints.allowed_values && !constraints.allowed_values.includes(transaction[field])) {
    return `${field} value "${transaction[field]}" is not supported by ${mapping.target_name}`;
  }

  return null;
};

const validateMappingAgainstTransactions = (mapping, transactions) => {
  const mappingErrors = buildMappingDefinitionErrors(mapping);
  const missingFields = [];
  const incompatibleFields = [];

  transactions.forEach((transaction) => {
    const payloadValidation = validateEntityPayload(transaction.entity_type, transaction);
    if (!payloadValidation.valid) {
      incompatibleFields.push({
        level: 'record',
        record_id: transaction.unique_id,
        target_column: 'canonical_record',
        source_field: 'entity_payload',
        issue: payloadValidation.errors.join('; ')
      });
    }

    mapping.target_columns.forEach((column) => {
      const value = transaction[column.source_field];
      if (column.required && !isPresent(value)) {
        missingFields.push({
          level: 'record',
          record_id: transaction.unique_id,
          target_column: column.target_column,
          source_field: column.source_field,
          issue: `Missing required field "${column.source_field}" for ${mapping.target_name}`
        });
        return;
      }

      const typeError = validateValueType(column.source_field, value);
      if (typeError) {
        incompatibleFields.push({
          level: 'record',
          record_id: transaction.unique_id,
          target_column: column.target_column,
          source_field: column.source_field,
          issue: typeError
        });
      }

      const connectorError = validateConnectorConstraint(mapping, transaction, column.source_field);
      if (connectorError) {
        incompatibleFields.push({
          level: 'record',
          record_id: transaction.unique_id,
          target_column: column.target_column,
          source_field: column.source_field,
          issue: connectorError
        });
      }
    });
  });

  return {
    valid: mappingErrors.length === 0 && missingFields.length === 0 && incompatibleFields.length === 0,
    records_checked: transactions.length,
    missing_fields: missingFields,
    incompatible_fields: incompatibleFields,
    mapping_errors: mappingErrors
  };
};

const buildCompatibilityValidationReport = (snapshotRecord) => {
  const mappingResults = Object.values(COMPATIBILITY_MAPPINGS).reduce((acc, mapping) => {
    acc[mapping.format_key] = validateMappingAgainstTransactions(mapping, snapshotRecord.transactions);
    return acc;
  }, {});

  const validationErrors = Object.entries(mappingResults).flatMap(([mappingKey, result]) => (
    result.mapping_errors
      .concat(result.missing_fields)
      .concat(result.incompatible_fields)
      .map((entry) => ({
        mapping: mappingKey,
        ...entry
      }))
  ));

  return {
    schema_version: canonicalSchemas.schema_version,
    snapshot_id: snapshotRecord.unique_id,
    quarter_label: snapshotRecord.quarter_reference,
    canonical_field_set: CANONICAL_EXPORT_FIELDS,
    mapping_results: stableSortObject(mappingResults),
    validation_errors: validationErrors.sort((left, right) => (
      `${left.mapping}:${left.record_id || ''}:${left.target_column}`.localeCompare(
        `${right.mapping}:${right.record_id || ''}:${right.target_column}`
      )
    ))
  };
};

const buildCompatibilityArtifacts = (snapshotRecord) => {
  const validationReport = buildCompatibilityValidationReport(snapshotRecord);
  const files = Object.entries(COMPATIBILITY_MAPPINGS).map(([name, mapping]) => ({
    name: `${name}.json`,
    content: Buffer.from(`${stableStringify(mapping)}\n`, 'utf8'),
    content_type: 'application/json'
  }));

  files.push({
    name: 'compatibility_validation.json',
    content: Buffer.from(`${stableStringify(validationReport)}\n`, 'utf8'),
    content_type: 'application/json'
  });

  return {
    mappings: COMPATIBILITY_MAPPINGS,
    validationReport,
    files
  };
};

module.exports = {
  CANONICAL_EXPORT_FIELDS,
  COMPATIBILITY_MAPPINGS,
  buildCompatibilityArtifacts,
  buildCompatibilityValidationReport,
  stableStringify
};
