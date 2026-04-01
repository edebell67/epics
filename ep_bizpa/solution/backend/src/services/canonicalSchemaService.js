const fs = require('fs');
const path = require('path');
const {
  deriveQuarterReference,
  validateAndClassifyMonetaryPayload
} = require('./vatQuarterClassificationService');

const schemaPath = path.join(__dirname, '..', 'models', 'canonical_entity_event_schemas.json');
const canonicalSchemas = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));

const monetaryEntityTypes = Object.entries(canonicalSchemas.entity_types)
  .filter(([, definition]) => definition.class === 'monetary')
  .map(([entityType]) => entityType);

const nonMonetaryEntityTypes = Object.entries(canonicalSchemas.entity_types)
  .filter(([, definition]) => definition.class === 'non_monetary')
  .map(([entityType]) => entityType);

const requiredFieldSet = (entityType) => {
  const definition = canonicalSchemas.entity_types[entityType];
  return new Set(definition ? definition.required_fields : []);
};

const isPresent = (value) => value !== undefined && value !== null && value !== '';

const validateEntityPayload = (entityType, payload) => {
  const definition = canonicalSchemas.entity_types[entityType];
  if (!definition) {
    return {
      valid: false,
      errors: [`Unsupported entity_type: ${entityType}`]
    };
  }

  const errors = [];
  for (const field of requiredFieldSet(entityType)) {
    if (!isPresent(payload[field])) {
      errors.push(`Missing required field: ${field}`);
    }
  }

  if (isPresent(payload.status) && !definition.allowed_statuses.includes(payload.status)) {
    errors.push(`Unsupported status "${payload.status}" for ${entityType}`);
  }

  if (isPresent(payload.commit_mode) && !canonicalSchemas.shared_fields.commit_mode.allowed_values.includes(payload.commit_mode)) {
    errors.push(`Unsupported commit_mode "${payload.commit_mode}"`);
  }

  if (isPresent(payload.source_type) && !canonicalSchemas.shared_fields.source_type.allowed_values.includes(payload.source_type)) {
    errors.push(`Unsupported source_type "${payload.source_type}"`);
  }

  if (definition.class === 'monetary') {
    const quarterPattern = new RegExp(canonicalSchemas.quarter_reference.pattern);
    if (isPresent(payload.quarter_reference) && !quarterPattern.test(payload.quarter_reference)) {
      errors.push(`Invalid quarter_reference "${payload.quarter_reference}"`);
    }
    if (isPresent(payload.vat_type) && !canonicalSchemas.shared_fields.vat_type.allowed_values.includes(payload.vat_type)) {
      errors.push(`Unsupported vat_type "${payload.vat_type}"`);
    }

    if (errors.length === 0) {
      try {
        validateAndClassifyMonetaryPayload({
          entityType: entityType,
          transactionDate: payload.transaction_date,
          quarterReference: payload.quarter_reference,
          amount: payload.amount,
          net_amount: payload.net_amount,
          vat_amount: payload.vat_amount,
          gross_amount: payload.gross_amount,
          vat_rate: payload.vat_rate,
          vat_type: payload.vat_type
        });
      } catch (err) {
        errors.push(err.message);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
};

const validateEventPayload = (payload) => {
  const errors = [];
  for (const field of canonicalSchemas.event_schema.required_fields) {
    if (!isPresent(payload[field])) {
      errors.push(`Missing required event field: ${field}`);
    }
  }

  if (isPresent(payload.event_type) && !canonicalSchemas.event_schema.allowed_event_types.includes(payload.event_type)) {
    errors.push(`Unsupported event_type "${payload.event_type}"`);
  }

  if (isPresent(payload.source_type) && !canonicalSchemas.shared_fields.source_type.allowed_values.includes(payload.source_type)) {
    errors.push(`Unsupported source_type "${payload.source_type}"`);
  }

  if (isPresent(payload.quarter_reference)) {
    const quarterPattern = new RegExp(canonicalSchemas.quarter_reference.pattern);
    if (!quarterPattern.test(payload.quarter_reference)) {
      errors.push(`Invalid quarter_reference "${payload.quarter_reference}"`);
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
};

module.exports = {
  canonicalSchemas,
  monetaryEntityTypes,
  nonMonetaryEntityTypes,
  validateEntityPayload,
  validateEventPayload,
  deriveQuarterReference
};
