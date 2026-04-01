function normalizeDirection(value) {
  const v = String(value || '').toLowerCase();
  if (v === 'in' || v === 'credit' || v === 'incoming') return 'in';
  return 'out';
}

function normalizeTxn(raw) {
  return {
    bank_txn_ref: raw.bank_txn_ref || raw.transaction_id || raw.id,
    txn_date: raw.txn_date || raw.booking_date || raw.date,
    posted_at: raw.posted_at || raw.timestamp || null,
    merchant: raw.merchant || raw.counterparty || raw.description || 'Unknown merchant',
    amount: Number(raw.amount || 0),
    direction: normalizeDirection(raw.direction || raw.credit_debit_indicator),
    description: raw.description || null,
    balance: raw.balance !== undefined && raw.balance !== null ? Number(raw.balance) : null,
    raw_payload: raw
  };
}

function normalizeBatch(payload) {
  const txns = Array.isArray(payload?.transactions) ? payload.transactions : [];
  return txns.map(normalizeTxn).filter((t) => t.bank_txn_ref && t.txn_date && t.amount !== 0);
}

module.exports = {
  normalizeBatch,
  normalizeTxn
};
