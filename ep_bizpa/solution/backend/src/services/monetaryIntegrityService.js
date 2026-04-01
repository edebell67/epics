const { monetaryEntityTypes } = require('./canonicalSchemaService');
const { validateAndClassifyMonetaryPayload } = require('./vatQuarterClassificationService');

const IMMUTABLE_COMMITTED_FIELDS = [
  'amount',
  'currency',
  'net_amount',
  'gross_amount',
  'vat_amount',
  'vat_rate',
  'type',
  'quarter_ref'
];

const CORRECTION_ACTIONS = new Set(['void', 'replace', 'supersede']);
const LEGACY_COMMITTED_STATUSES = new Set(['confirmed', 'reconciled']);
const ENTITY_TYPE_ALIASES = {
  receipt: 'receipt_expense'
};

const LEGACY_STATUS_TRANSITIONS = {
  draft: new Set(['confirmed', 'archived']),
  confirmed: new Set(['reconciled']),
  reconciled: new Set([]),
  archived: new Set([])
};

const INVOICE_PAYMENT_TRANSITIONS = {
  draft: new Set(['sent', 'overdue', 'paid', 'partial', 'void']),
  sent: new Set(['overdue', 'paid', 'partial', 'void']),
  overdue: new Set(['paid', 'partial', 'void']),
  partial: new Set(['paid', 'void']),
  paid: new Set([]),
  void: new Set([])
};

const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);

const normalizeEntityType = (type) => ENTITY_TYPE_ALIASES[type] || type;

const isMonetaryItemType = (type) => monetaryEntityTypes.includes(normalizeEntityType(type));

const isCommittedStatus = (status) => LEGACY_COMMITTED_STATUSES.has(status);

const isCommittedMonetaryItem = (item) => isMonetaryItemType(item?.type) && isCommittedStatus(item?.status);

const valuesDiffer = (existingValue, nextValue) => {
  if (existingValue === null || existingValue === undefined) {
    return !(nextValue === null || nextValue === undefined);
  }

  if (nextValue === null || nextValue === undefined) {
    return true;
  }

  const existingNumber = Number(existingValue);
  const nextNumber = Number(nextValue);
  if (!Number.isNaN(existingNumber) && !Number.isNaN(nextNumber)) {
    return existingNumber !== nextNumber;
  }

  return String(existingValue) !== String(nextValue);
};

const collectImmutableFieldChanges = (existingItem, updates) =>
  IMMUTABLE_COMMITTED_FIELDS.filter((field) => hasOwn(updates, field) && valuesDiffer(existingItem[field], updates[field]));

const validateStatusTransition = (currentStatus, nextStatus) => {
  if (!nextStatus || currentStatus === nextStatus) {
    return null;
  }

  const allowedTransitions = LEGACY_STATUS_TRANSITIONS[currentStatus];
  if (!allowedTransitions) {
    return `Unsupported current status "${currentStatus}"`;
  }

  if (!allowedTransitions.has(nextStatus)) {
    return `Invalid status transition from "${currentStatus}" to "${nextStatus}"`;
  }

  return null;
};

const validateInvoicePaymentTransition = (currentStatus, nextStatus) => {
  if (!nextStatus || currentStatus === nextStatus) {
    return null;
  }

  const allowedTransitions = INVOICE_PAYMENT_TRANSITIONS[currentStatus];
  if (!allowedTransitions) {
    return `Unsupported invoice payment status "${currentStatus}"`;
  }

  if (!allowedTransitions.has(nextStatus)) {
    return `Invalid payment_status transition from "${currentStatus}" to "${nextStatus}"`;
  }

  return null;
};

const validateItemUpdate = (existingItem, updates) => {
  const errors = [];
  const immutableChanges = collectImmutableFieldChanges(existingItem, updates);

  if (hasOwn(updates, 'status')) {
    const transitionError = validateStatusTransition(existingItem.status, updates.status);
    if (transitionError) {
      errors.push(transitionError);
    }
  }

  if (existingItem.type === 'invoice' && hasOwn(updates, 'payment_status')) {
    const paymentTransitionError = validateInvoicePaymentTransition(existingItem.payment_status || 'draft', updates.payment_status);
    if (paymentTransitionError) {
      errors.push(paymentTransitionError);
    }
  }

  if (isCommittedMonetaryItem(existingItem) && immutableChanges.length > 0) {
    errors.push(
      `Committed monetary item cannot change immutable fields in place: ${immutableChanges.join(', ')}. Use a void/replace/supersede correction flow instead.`
    );
  }

  if (isCommittedMonetaryItem(existingItem) && updates.status === 'archived') {
    errors.push('Committed monetary items cannot be archived through the delete path. Use an explicit correction flow instead.');
  }

  return {
    valid: errors.length === 0,
    errors,
    immutableChanges
  };
};

const validateArchiveRequest = (existingItem) => {
  if (isCommittedMonetaryItem(existingItem)) {
    return {
      valid: false,
      errors: ['Committed monetary items cannot be deleted or archived. Use a void, replace, or supersede correction flow instead.']
    };
  }

  return { valid: true, errors: [] };
};

const buildReplacementItemData = (existingItem, replacementData = {}) => {
  const replacementAmountProvided = hasOwn(replacementData, 'amount');
  const replacementNetProvided = hasOwn(replacementData, 'net_amount');
  const replacementVatProvided = hasOwn(replacementData, 'vat_amount');
  const replacementGrossProvided = hasOwn(replacementData, 'gross_amount');

  return {
    type: replacementData.type || existingItem.type,
    status: replacementData.status || 'confirmed',
    amount: replacementAmountProvided ? replacementData.amount : existingItem.amount,
    currency: hasOwn(replacementData, 'currency') ? replacementData.currency : existingItem.currency,
    tax_flag: hasOwn(replacementData, 'tax_flag') ? replacementData.tax_flag : existingItem.tax_flag,
    vat_amount: replacementVatProvided ? replacementData.vat_amount : existingItem.vat_amount,
    due_date: hasOwn(replacementData, 'due_date') ? replacementData.due_date : existingItem.due_date,
    client_id: hasOwn(replacementData, 'client_id') ? replacementData.client_id : existingItem.client_id,
    job_id: hasOwn(replacementData, 'job_id') ? replacementData.job_id : existingItem.job_id,
    extracted_text: hasOwn(replacementData, 'extracted_text') ? replacementData.extracted_text : existingItem.extracted_text,
    raw_note: hasOwn(replacementData, 'raw_note') ? replacementData.raw_note : existingItem.raw_note,
    device_id: replacementData.device_id || existingItem.device_id,
    voice_command_source_text: hasOwn(replacementData, 'voice_command_source_text')
      ? replacementData.voice_command_source_text
      : existingItem.voice_command_source_text,
    voice_action_confidence: hasOwn(replacementData, 'voice_action_confidence')
      ? replacementData.voice_action_confidence
      : existingItem.voice_action_confidence,
    net_amount: replacementNetProvided ? replacementData.net_amount : existingItem.net_amount,
    gross_amount: replacementGrossProvided
      ? replacementData.gross_amount
      : (replacementAmountProvided || replacementNetProvided || replacementVatProvided ? undefined : existingItem.gross_amount),
    vat_type: hasOwn(replacementData, 'vat_type') ? replacementData.vat_type : existingItem.vat_type,
    quarter_ref: hasOwn(replacementData, 'quarter_ref') ? replacementData.quarter_ref : existingItem.quarter_ref,
    transaction_date: hasOwn(replacementData, 'transaction_date')
      ? replacementData.transaction_date
      : (existingItem.transaction_date || existingItem.txn_date || existingItem.created_at),
    vat_rate: hasOwn(replacementData, 'vat_rate') ? replacementData.vat_rate : existingItem.vat_rate,
    payment_status: hasOwn(replacementData, 'payment_status') ? replacementData.payment_status : existingItem.payment_status
  };
};

const validateCorrectionRequest = (existingItem, action, reason, replacementData = {}) => {
  const errors = [];

  if (!CORRECTION_ACTIONS.has(action)) {
    errors.push(`Unsupported correction action "${action}"`);
  }

  if (!isCommittedMonetaryItem(existingItem)) {
    errors.push('Correction flows are only available for committed monetary items.');
  }

  if (!reason || !String(reason).trim()) {
    errors.push('Correction reason is required.');
  }

  let replacementItemData = null;
  let immutableChanges = [];

  if ((action === 'replace' || action === 'supersede') && errors.length === 0) {
    replacementItemData = buildReplacementItemData(existingItem, replacementData);
    immutableChanges = collectImmutableFieldChanges(existingItem, replacementItemData);

    if (immutableChanges.length === 0) {
      errors.push('Replacement or supersede flow must change at least one immutable monetary field.');
    }

    if (errors.length === 0) {
      try {
        const resolvedMonetaryFields = validateAndClassifyMonetaryPayload({
          entityType: replacementItemData.type,
          transactionDate: replacementItemData.transaction_date,
          quarterReference: replacementItemData.quarter_ref,
          amount: replacementItemData.amount,
          net_amount: replacementItemData.net_amount,
          vat_amount: replacementItemData.vat_amount,
          gross_amount: replacementItemData.gross_amount,
          vat_rate: replacementItemData.vat_rate,
          vat_type: replacementItemData.vat_type
        });
        replacementItemData = {
          ...replacementItemData,
          amount: resolvedMonetaryFields.amount,
          net_amount: resolvedMonetaryFields.net_amount,
          vat_amount: resolvedMonetaryFields.vat_amount,
          gross_amount: resolvedMonetaryFields.gross_amount,
          vat_rate: resolvedMonetaryFields.vat_rate,
          vat_type: resolvedMonetaryFields.vat_type,
          quarter_ref: resolvedMonetaryFields.quarter_ref
        };
      } catch (err) {
        errors.push(err.message);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    replacementItemData,
    immutableChanges
  };
};

const getCommitTimestamp = (item) => item.updated_at || item.created_at || null;

const buildCorrectionAuditPayloads = ({ action, originalItem, replacementItem, reason, userId, deviceId }) => {
  const originalPayload = {
    action_type: `monetary_${action}`,
    entity_name: 'capture_items',
    entity_id: originalItem.id,
    user_id: userId,
    device_id: deviceId || originalItem.device_id || 'system',
    diff_log: {
      correction_type: action,
      status_transition: {
        from: originalItem.status,
        to: action === 'void' ? 'void_requested' : 'replacement_created'
      },
      void_reason: action === 'void' ? reason : null,
      superseded_by: replacementItem ? replacementItem.id : null,
      commit_timestamp: getCommitTimestamp(originalItem),
      immutable_fields: IMMUTABLE_COMMITTED_FIELDS
    }
  };

  if (!replacementItem) {
    return [originalPayload];
  }

  return [
    originalPayload,
    {
      action_type: `monetary_${action}_replacement`,
      entity_name: 'capture_items',
      entity_id: replacementItem.id,
      user_id: userId,
      device_id: deviceId || replacementItem.device_id || originalItem.device_id || 'system',
      diff_log: {
        correction_type: action,
        status_transition: {
          from: null,
          to: replacementItem.status
        },
        void_reason: null,
        superseded_by: null,
        supersedes: originalItem.id,
        commit_timestamp: getCommitTimestamp(replacementItem),
        immutable_fields: IMMUTABLE_COMMITTED_FIELDS
      }
    }
  ];
};

module.exports = {
  IMMUTABLE_COMMITTED_FIELDS,
  buildCorrectionAuditPayloads,
  buildReplacementItemData,
  isCommittedMonetaryItem,
  isMonetaryItemType,
  validateArchiveRequest,
  validateCorrectionRequest,
  validateItemUpdate
};
