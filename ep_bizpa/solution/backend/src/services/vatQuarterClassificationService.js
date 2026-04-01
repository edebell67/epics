const DEFAULT_VAT_RATE = 20;

const OUTPUT_VAT_ENTITY_TYPES = new Set(['invoice', 'quote', 'payment']);
const INPUT_VAT_ENTITY_TYPES = new Set(['receipt', 'receipt_expense', 'monetary_booking']);
const VALID_VAT_TYPES = new Set(['input', 'output', 'outside_scope', 'exempt']);
const LEGACY_VAT_TYPE_ALIASES = {
  Input: 'input',
  Output: 'output',
  input: 'input',
  output: 'output',
  outside_scope: 'outside_scope',
  outsideScope: 'outside_scope',
  exempt: 'exempt',
  Exempt: 'exempt'
};

const isPresent = (value) => value !== undefined && value !== null && value !== '';

const toBasisPoints = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    throw new Error(`Invalid vat_rate "${value}"`);
  }
  return Math.round(numeric * 100);
};

const fromBasisPoints = (basisPoints) => basisPoints / 100;

const toCents = (value, fieldName) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    throw new Error(`Invalid ${fieldName} "${value}"`);
  }
  return Math.round(numeric * 100);
};

const fromCents = (cents) => cents / 100;

const roundCurrency = (value) => fromCents(toCents(value, 'currency value'));

const calculateVatFromNetCents = (netCents, vatRateBasisPoints) =>
  Math.round((netCents * vatRateBasisPoints) / 10000);

const calculateNetFromGrossCents = (grossCents, vatRateBasisPoints) => {
  if (vatRateBasisPoints === 0) {
    return grossCents;
  }
  return Math.round((grossCents * 10000) / (10000 + vatRateBasisPoints));
};

const normalizeVatType = (vatType) => {
  if (!isPresent(vatType)) {
    return null;
  }
  const normalized = LEGACY_VAT_TYPE_ALIASES[vatType] || String(vatType).trim().toLowerCase();
  if (!VALID_VAT_TYPES.has(normalized)) {
    throw new Error(`Unsupported vat_type "${vatType}"`);
  }
  return normalized;
};

const inferVatTypeFromEntityType = (entityType) => {
  if (OUTPUT_VAT_ENTITY_TYPES.has(entityType)) {
    return 'output';
  }
  if (INPUT_VAT_ENTITY_TYPES.has(entityType)) {
    return 'input';
  }
  throw new Error(`Unable to infer vat_type for unsupported entity type "${entityType}"`);
};

const classifyVatType = ({ entityType, vatType, vatRate, vatAmount }) => {
  const normalizedVatType = normalizeVatType(vatType);
  if (normalizedVatType) {
    return normalizedVatType;
  }

  const normalizedAmount = isPresent(vatAmount) ? roundCurrency(vatAmount) : null;
  const normalizedRate = isPresent(vatRate) ? Number(vatRate) : DEFAULT_VAT_RATE;
  if ((normalizedAmount === 0 || normalizedAmount === null) && Number(normalizedRate) === 0) {
    return inferVatTypeFromEntityType(entityType);
  }

  return inferVatTypeFromEntityType(entityType);
};

const parseTransactionDate = (value) => {
  if (!isPresent(value)) {
    throw new Error('transaction_date is required for quarter derivation');
  }

  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return {
      year: value.getUTCFullYear(),
      month: value.getUTCMonth() + 1,
      day: value.getUTCDate()
    };
  }

  const text = String(value).trim();
  const datePrefixMatch = /^(\d{4})-(\d{2})-(\d{2})/.exec(text);
  if (datePrefixMatch) {
    const year = Number(datePrefixMatch[1]);
    const month = Number(datePrefixMatch[2]);
    const day = Number(datePrefixMatch[3]);
    if (month < 1 || month > 12 || day < 1 || day > 31) {
      throw new Error(`Invalid transaction date: ${value}`);
    }
    return { year, month, day };
  }

  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`Invalid transaction date: ${value}`);
  }

  return {
    year: parsed.getUTCFullYear(),
    month: parsed.getUTCMonth() + 1,
    day: parsed.getUTCDate()
  };
};

const deriveQuarterReference = (transactionDate) => {
  const { year, month } = parseTransactionDate(transactionDate);
  const quarter = Math.ceil(month / 3);
  return `Q${quarter}-${year}`;
};

const resolveMonetaryAmounts = ({
  amount,
  net_amount,
  vat_amount,
  gross_amount,
  vat_rate,
  vat_type
}) => {
  const providedNet = isPresent(net_amount) ? toCents(net_amount, 'net_amount') : null;
  const providedVat = isPresent(vat_amount) ? toCents(vat_amount, 'vat_amount') : null;
  const providedGross = isPresent(gross_amount)
    ? toCents(gross_amount, 'gross_amount')
    : (isPresent(amount) ? toCents(amount, 'amount') : null);

  const normalizedVatType = normalizeVatType(vat_type);
  const vatRateBasisPoints = normalizedVatType === 'exempt' || normalizedVatType === 'outside_scope'
    ? 0
    : toBasisPoints(isPresent(vat_rate) ? vat_rate : DEFAULT_VAT_RATE);

  const derivedZeroVat = normalizedVatType === 'exempt' || normalizedVatType === 'outside_scope';

  if (providedNet === null && providedVat === null && providedGross === null) {
    throw new Error('At least one of amount, gross_amount, net_amount, or vat_amount must be provided.');
  }

  let resolvedNet = providedNet;
  let resolvedVat = providedVat;
  let resolvedGross = providedGross;

  if (derivedZeroVat) {
    if (providedVat !== null && providedVat !== 0) {
      throw new Error(`vat_amount must be 0 when vat_type is "${normalizedVatType}"`);
    }
    if (isPresent(vat_rate) && vatRateBasisPoints !== 0) {
      throw new Error(`vat_rate must be 0 when vat_type is "${normalizedVatType}"`);
    }
  }

  if (resolvedNet !== null && resolvedVat !== null && resolvedGross === null) {
    resolvedGross = resolvedNet + resolvedVat;
  } else if (resolvedNet !== null && resolvedGross !== null && resolvedVat === null) {
    resolvedVat = resolvedGross - resolvedNet;
  } else if (resolvedVat !== null && resolvedGross !== null && resolvedNet === null) {
    resolvedNet = resolvedGross - resolvedVat;
  } else if (resolvedGross !== null && resolvedNet === null && resolvedVat === null) {
    resolvedNet = calculateNetFromGrossCents(resolvedGross, vatRateBasisPoints);
    resolvedVat = resolvedGross - resolvedNet;
  } else if (resolvedNet !== null && resolvedVat === null && resolvedGross === null) {
    resolvedVat = derivedZeroVat ? 0 : calculateVatFromNetCents(resolvedNet, vatRateBasisPoints);
    resolvedGross = resolvedNet + resolvedVat;
  }

  if (resolvedNet === null || resolvedVat === null || resolvedGross === null) {
    throw new Error('Unable to resolve a complete net/vat/gross set from the provided amounts.');
  }

  if (resolvedGross !== resolvedNet + resolvedVat) {
    throw new Error('gross_amount must equal net_amount plus vat_amount.');
  }

  if (derivedZeroVat) {
    if (resolvedVat !== 0) {
      throw new Error(`vat_amount must be 0 when vat_type is "${normalizedVatType}"`);
    }
    if (resolvedGross !== resolvedNet) {
      throw new Error(`gross_amount must equal net_amount when vat_type is "${normalizedVatType}"`);
    }
  } else if (resolvedNet !== null) {
    const expectedVat = calculateVatFromNetCents(resolvedNet, vatRateBasisPoints);
    if (resolvedVat !== expectedVat) {
      throw new Error(
        `Invalid VAT combination: expected vat_amount ${fromCents(expectedVat).toFixed(2)} for net_amount ${fromCents(resolvedNet).toFixed(2)} at vat_rate ${fromBasisPoints(vatRateBasisPoints).toFixed(2)}`
      );
    }
  }

  return {
    net_amount: fromCents(resolvedNet),
    vat_amount: fromCents(resolvedVat),
    gross_amount: fromCents(resolvedGross),
    amount: fromCents(resolvedGross),
    vat_rate: fromBasisPoints(vatRateBasisPoints)
  };
};

const validateAndClassifyMonetaryPayload = ({
  entityType,
  transactionDate,
  quarterReference,
  amount,
  net_amount,
  vat_amount,
  gross_amount,
  vat_rate,
  vat_type
}) => {
  const resolvedVatType = classifyVatType({
    entityType,
    vatType: vat_type,
    vatRate: vat_rate,
    vatAmount: vat_amount
  });

  const resolvedAmounts = resolveMonetaryAmounts({
    amount,
    net_amount,
    vat_amount,
    gross_amount,
    vat_rate,
    vat_type: resolvedVatType
  });

  const derivedQuarterReference = deriveQuarterReference(transactionDate);
  if (isPresent(quarterReference) && quarterReference !== derivedQuarterReference) {
    throw new Error(
      `quarter_reference "${quarterReference}" does not match transaction_date-derived value "${derivedQuarterReference}"`
    );
  }

  return {
    ...resolvedAmounts,
    quarter_reference: derivedQuarterReference,
    quarter_ref: derivedQuarterReference,
    vat_type: resolvedVatType
  };
};

module.exports = {
  DEFAULT_VAT_RATE,
  VALID_VAT_TYPES,
  classifyVatType,
  deriveQuarterReference,
  normalizeVatType,
  resolveMonetaryAmounts,
  roundCurrency,
  validateAndClassifyMonetaryPayload
};
