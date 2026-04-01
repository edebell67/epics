const crypto = require('crypto');

const DEFAULT_CURRENCY = 'GBP';

function formatDateOnly(value) {
  if (!value) {
    return null;
  }

  const text = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return text;
  }

  const date = new Date(text);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toISOString().slice(0, 10);
}

function formatTimestamp(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toISOString();
}

function normalizeDirection(rawDirection, signedAmount) {
  const candidate = String(rawDirection || '').trim().toLowerCase();
  if (['in', 'credit', 'incoming', 'received'].includes(candidate)) {
    return 'in';
  }
  if (['out', 'debit', 'outgoing', 'sent'].includes(candidate)) {
    return 'out';
  }
  return signedAmount < 0 ? 'out' : 'in';
}

function normalizeAmount(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric === 0) {
    return null;
  }
  return Number(Math.abs(numeric).toFixed(2));
}

function buildSourceHash(parts) {
  return crypto.createHash('sha256').update(parts.join('|')).digest('hex');     
}

function normalizeTransaction(rawTransaction, bankAccount) {
  const signedAmount = Number(
    rawTransaction.amount
      ?? rawTransaction.transaction_amount
      ?? rawTransaction.amount_minor_units
      ?? 0
  );
  const amount = normalizeAmount(signedAmount);
  const date = formatDateOnly(
    rawTransaction.date
      ?? rawTransaction.booking_date
      ?? rawTransaction.transaction_date
      ?? rawTransaction.booked_at
  );
  const postedAt = formatTimestamp(
    rawTransaction.posted_at
      ?? rawTransaction.booked_at
      ?? rawTransaction.timestamp
      ?? rawTransaction.created_at
  );
  const merchant = String(
    rawTransaction.merchant
      ?? rawTransaction.counterparty
      ?? rawTransaction.payee_name
      ?? rawTransaction.description
      ?? 'Unknown merchant'
  ).trim();
  const direction = normalizeDirection(
    rawTransaction.direction ?? rawTransaction.credit_debit_indicator,
    signedAmount
  );
  const currency = String(rawTransaction.currency ?? bankAccount.currency ?? DEFAULT_CURRENCY).trim().toUpperCase();
  const providerTxnId = rawTransaction.provider_txn_id ?? rawTransaction.transaction_id ?? rawTransaction.id ?? null;
  const description = rawTransaction.description ?? rawTransaction.reference ?? rawTransaction.remittance_information ?? null;
  const balance = rawTransaction.balance == null ? null : Number(rawTransaction.balance);
  const bookingStatus = rawTransaction.booking_status ?? rawTransaction.status ?? null;
  const sourceHash = buildSourceHash([
    bankAccount.bank_account_id,
    providerTxnId ?? '',
    date ?? '',
    String(amount ?? ''),
    direction,
    merchant,
    description ?? '',
    postedAt ?? ''
  ]);
  const bankTxnRef = String(
    rawTransaction.bank_txn_ref
      ?? rawTransaction.reference
      ?? providerTxnId
      ?? sourceHash.slice(0, 32)
  ).trim();

  if (!date || !amount || !bankTxnRef) {
    return {
      valid: false,
      reason: 'missing_required_fields',
      raw_transaction: rawTransaction
    };
  }

  return {
    valid: true,
    transaction: {
      txn_id: null,
      user_id: bankAccount.user_id,
      bank_account_id: bankAccount.bank_account_id,
      bank_txn_ref: bankTxnRef,
      provider_txn_id: providerTxnId,
      date,
      merchant: merchant || 'Unknown merchant',
      amount,
      direction,
      currency,
      booking_status: bookingStatus,
      imported_at: null,
      source_hash: sourceHash,
      duplicate_flag: false,
      duplicate_group_id: null,
      description,
      posted_at: postedAt,
      balance,
      raw_payload: rawTransaction
    }
  };
}

function normalizeBatch(rawTransactions, bankAccount) {
  const validTransactions = [];
  const skipped = [];

  for (const rawTransaction of Array.isArray(rawTransactions) ? rawTransactions : []) {
    const normalized = normalizeTransaction(rawTransaction, bankAccount);       
    if (normalized.valid) {
      validTransactions.push(normalized.transaction);
    } else {
      skipped.push(normalized);
    }
  }

  return {
    validTransactions,
    skipped
  };
}

/**
 * Connection Flow Integration [V20260321_1235]
 */

function buildConsentUrl(config, userContext) {
  const { providerBaseUrl, clientId, redirectUri, scopes } = config;
  const { state } = userContext;
  
  const url = new URL(`${providerBaseUrl}/authorize`);
  url.searchParams.set('client_id', clientId);
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('scope', (scopes || []).join(' '));
  url.searchParams.set('state', state);
  url.searchParams.set('response_type', 'code');
  
  return url.toString();
}

async function exchangeCodeForTokens(config, code) {
  // Mock token exchange for MVP
  return {
    accessToken: `mock_access_${crypto.randomBytes(8).toString('hex')}`,
    refreshToken: `mock_refresh_${crypto.randomBytes(8).toString('hex')}`,
    expiresAt: new Date(Date.now() + 3600 * 1000).toISOString(),
    scopes: config.scopes,
    providerConsentId: `consent_${crypto.randomBytes(4).toString('hex')}`
  };
}

async function fetchProviderAccounts(accessToken) {
  // Mock account fetch for MVP
  return [
    {
      provider_account_id: 'acc_12345',
      account_name: 'Main Business Account',
      currency: 'GBP',
      account_mask: '****6789'
    }
  ];
}

module.exports = {
  DEFAULT_CURRENCY,
  buildSourceHash,
  normalizeBatch,
  normalizeDirection,
  normalizeTransaction,
  buildConsentUrl,
  exchangeCodeForTokens,
  fetchProviderAccounts
};
