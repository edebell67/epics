const db = require('../config/db');
const { normalizeBatch } = require('../services/openBankingAdapter');
const { buildReadinessReport } = require('../services/readinessService');
const {
  deriveQuarterFromDate,
  quarterBoundsFromReference,
  recordReadinessRecalculated,
  recordStatusChange
} = require('../services/businessEventLogService');

const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000000';

const recordReadinessForTransaction = async (executor, userId, bankTxnId, txnDate, summary, description) => {
  await recordReadinessRecalculated(executor, {
    user_id: userId,
    actor_id: userId,
    source_type: 'manual',
    quarter_reference: deriveQuarterFromDate(txnDate),
    entity_id: bankTxnId,
    entity_type: 'bank_transaction',
    description,
    metadata: summary
  });
};

const ingestBankFeed = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const {
    provider_name = 'manual_import',
    provider_account_id = 'default_account',
    account_name = null,
    transactions = []
  } = req.body || {};

  const normalized = normalizeBatch({ transactions });
  if (normalized.length === 0) {
    return res.status(400).json({ error: 'No valid transactions to ingest.' });
  }

  const client = await db.pool.connect();
  try {
    await client.query('BEGIN');

    const accountUpsert = await client.query(
      `
      INSERT INTO bank_accounts (user_id, provider_name, provider_account_id, account_name)
      VALUES ($1, $2, $3, $4)
      ON CONFLICT (user_id, provider_name, provider_account_id)
      DO UPDATE SET account_name = COALESCE(EXCLUDED.account_name, bank_accounts.account_name), updated_at = CURRENT_TIMESTAMP
      RETURNING id
      `,
      [userId, provider_name, provider_account_id, account_name]
    );
    const bankAccountId = accountUpsert.rows[0].id;

    let inserted = 0;
    let deduped = 0;
    for (const txn of normalized) {
      const result = await client.query(
        `
        INSERT INTO bank_transactions (
          user_id, bank_account_id, bank_txn_ref, txn_date, posted_at, merchant, amount, direction, description, balance, raw_payload
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ON CONFLICT (bank_account_id, bank_txn_ref) DO NOTHING
        RETURNING id
        `,
        [
          userId,
          bankAccountId,
          txn.bank_txn_ref,
          txn.txn_date,
          txn.posted_at,
          txn.merchant,
          txn.amount,
          txn.direction,
          txn.description,
          txn.balance,
          txn.raw_payload
        ]
      );
      if (result.rows.length > 0) inserted += 1;
      else deduped += 1;
    }

    await client.query(
      'UPDATE bank_accounts SET last_synced_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = $1',
      [bankAccountId]
    );
    await client.query('COMMIT');

    return res.status(200).json({
      status: 'ok',
      bank_account_id: bankAccountId,
      received: normalized.length,
      inserted,
      deduped
    });
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[InboxController] ingestBankFeed failed:', err);
    return res.status(500).json({ error: 'Failed to ingest transactions.' });
  } finally {
    client.release();
  }
};

const getInbox = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const limit = Math.max(1, Math.min(500, Number(req.query.limit || 200)));
  const offset = Math.max(0, Number(req.query.offset || 0));

  try {
    const query = `
      SELECT
        bt.id,
        bt.txn_date,
        bt.merchant,
        bt.amount,
        bt.direction,
        bt.bank_txn_ref,
        tc.category_code,
        tc.business_personal,
        tc.is_split,
        tc.split_business_pct,
        bt.duplicate_flag,
        bt.duplicate_resolution,
        CASE
          WHEN tc.category_code IS NULL THEN 'missing_category'
          WHEN tc.business_personal IS NULL THEN 'missing_business_personal'
          WHEN tc.is_split = TRUE AND tc.split_business_pct IS NULL THEN 'missing_split_pct'
          WHEN bt.duplicate_flag = TRUE AND bt.duplicate_resolution IS NULL THEN 'unresolved_duplicate'
          ELSE NULL
        END AS blocker_reason
      FROM bank_transactions bt
      LEFT JOIN transaction_classifications tc ON tc.bank_txn_id = bt.id
      WHERE bt.user_id = $1
        AND (
          tc.category_code IS NULL
          OR tc.business_personal IS NULL
          OR (tc.is_split = TRUE AND tc.split_business_pct IS NULL)
          OR (bt.duplicate_flag = TRUE AND bt.duplicate_resolution IS NULL)
        )
      ORDER BY
        CASE
          WHEN tc.category_code IS NULL THEN 1
          WHEN tc.business_personal IS NULL THEN 2
          WHEN tc.is_split = TRUE AND tc.split_business_pct IS NULL THEN 3
          WHEN bt.duplicate_flag = TRUE AND bt.duplicate_resolution IS NULL THEN 4
          ELSE 5
        END,
        bt.txn_date DESC
      LIMIT $2 OFFSET $3
    `;
    const result = await db.query(query, [userId, limit, offset]);
    return res.status(200).json(result.rows);
  } catch (err) {
    console.error('[InboxController] getInbox failed:', err);
    return res.status(500).json({ error: 'Failed to load inbox queue.' });
  }
};

const classifyTransaction = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const bankTxnId = req.params.id;
  const {
    category_code = null,
    category_name = null,
    business_personal = null,
    is_split = false,
    split_business_pct = null,
    confidence = null,
    source = 'manual'
  } = req.body || {};

  if (is_split && (split_business_pct === null || split_business_pct === undefined)) {
    return res.status(400).json({ error: 'split_business_pct is required when is_split=true.' });
  }

  const client = await db.pool.connect();
  try {
    await client.query('BEGIN');
    const existing = await client.query(
      'SELECT * FROM transaction_classifications WHERE bank_txn_id = $1 AND user_id = $2',
      [bankTxnId, userId]
    );
    const previous = existing.rows[0] || null;

    const upsert = await client.query(
      `
      INSERT INTO transaction_classifications
      (user_id, bank_txn_id, category_code, category_name, business_personal, is_split, split_business_pct, confidence, source)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
      ON CONFLICT (bank_txn_id)
      DO UPDATE SET
        category_code = EXCLUDED.category_code,
        category_name = EXCLUDED.category_name,
        business_personal = EXCLUDED.business_personal,
        is_split = EXCLUDED.is_split,
        split_business_pct = EXCLUDED.split_business_pct,
        confidence = EXCLUDED.confidence,
        source = EXCLUDED.source,
        updated_at = CURRENT_TIMESTAMP
      RETURNING *
      `,
      [userId, bankTxnId, category_code, category_name, business_personal, is_split, split_business_pct, confidence, source]
    );

    await client.query(
      `
      INSERT INTO transaction_audit_log (user_id, bank_txn_id, changed_by, field_name, previous_value, new_value, change_source)
      VALUES ($1,$2,$3,$4,$5,$6,$7)
      `,
      [userId, bankTxnId, userId, 'classification', previous, upsert.rows[0], source === 'manual' ? 'ui' : source]
    );

    const bankTxn = await client.query(
      'SELECT txn_date FROM bank_transactions WHERE id = $1 AND user_id = $2',
      [bankTxnId, userId]
    );

    await recordReadinessForTransaction(
      client,
      userId,
      bankTxnId,
      bankTxn.rows[0]?.txn_date,
      {
        category_code,
        business_personal,
        is_split,
        split_business_pct,
        source
      },
      `Inbox classification updated for transaction ${bankTxnId}`
    );

    await client.query('COMMIT');
    return res.status(200).json(upsert.rows[0]);
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[InboxController] classifyTransaction failed:', err);
    return res.status(500).json({ error: 'Failed to classify transaction.' });
  } finally {
    client.release();
  }
};

const resolveDuplicate = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const bankTxnId = req.params.id;
  const { action, duplicate_of_txn_id = null } = req.body || {};
  if (!['dismiss', 'merge'].includes(action)) {
    return res.status(400).json({ error: 'action must be dismiss or merge.' });
  }
  try {
    const existing = await db.query(
      'SELECT duplicate_resolution, txn_date FROM bank_transactions WHERE id = $1 AND user_id = $2',
      [bankTxnId, userId]
    );
    const result = await db.query(
      `
      UPDATE bank_transactions
      SET duplicate_flag = TRUE,
          duplicate_resolution = $1,
          duplicate_of_txn_id = $2,
          updated_at = CURRENT_TIMESTAMP
      WHERE id = $3 AND user_id = $4
      RETURNING *
      `,
      [action, duplicate_of_txn_id, bankTxnId, userId]
    );
    if (!result.rows.length) return res.status(404).json({ error: 'Transaction not found.' });

    await recordStatusChange(db, {
      user_id: userId,
      actor_id: userId,
      source_type: 'manual',
      entity_id: bankTxnId,
      entity_type: 'bank_transaction',
      quarter_reference: deriveQuarterFromDate(result.rows[0].txn_date || existing.rows[0]?.txn_date),
      status_from: existing.rows[0]?.duplicate_resolution || 'unresolved_duplicate',
      status_to: action,
      description: `Duplicate resolution set to ${action} for transaction ${bankTxnId}`,
      metadata: {
        duplicate_of_txn_id,
        duplicate_flag: true
      }
    });

    await recordReadinessForTransaction(
      db,
      userId,
      bankTxnId,
      result.rows[0].txn_date || existing.rows[0]?.txn_date,
      {
        duplicate_resolution: action,
        duplicate_of_txn_id
      },
      `Readiness recalculated after duplicate resolution for transaction ${bankTxnId}`
    );

    return res.status(200).json(result.rows[0]);
  } catch (err) {
    console.error('[InboxController] resolveDuplicate failed:', err);
    return res.status(500).json({ error: 'Failed to resolve duplicate.' });
  }
};

const undoLastTriageAction = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  try {
    const audit = await db.query(
      `
      SELECT id, bank_txn_id, previous_value, field_name
      FROM transaction_audit_log
      WHERE user_id = $1
      ORDER BY changed_at DESC
      LIMIT 1
      `,
      [userId]
    );
    if (!audit.rows.length) return res.status(404).json({ error: 'No triage action to undo.' });
    const row = audit.rows[0];
    if (row.field_name !== 'classification') {
      return res.status(400).json({ error: 'Latest action is not undoable via classification undo.' });
    }
    const prev = row.previous_value || null;
    if (!prev) {
      await db.query('DELETE FROM transaction_classifications WHERE bank_txn_id = $1 AND user_id = $2', [row.bank_txn_id, userId]);
    } else {
      await db.query(
        `
        UPDATE transaction_classifications
        SET category_code = $1,
            category_name = $2,
            business_personal = $3,
            is_split = $4,
            split_business_pct = $5,
            confidence = $6,
            source = $7,
            updated_at = CURRENT_TIMESTAMP
        WHERE bank_txn_id = $8 AND user_id = $9
        `,
        [
          prev.category_code,
          prev.category_name,
          prev.business_personal,
          prev.is_split,
          prev.split_business_pct,
          prev.confidence,
          prev.source || 'manual',
          row.bank_txn_id,
          userId
        ]
      );
    }
    return res.status(200).json({ status: 'undone', bank_txn_id: row.bank_txn_id });
  } catch (err) {
    console.error('[InboxController] undoLastTriageAction failed:', err);
    return res.status(500).json({ error: 'Failed to undo last triage action.' });
  }
};

const getReadiness = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const asOfDate = req.query.as_of_date || new Date().toISOString().slice(0, 10);
  const activeQuarterReference = deriveQuarterFromDate(asOfDate);
  if (!activeQuarterReference) {
    return res.status(400).json({ error: 'as_of_date must be a valid date (YYYY-MM-DD).' });
  }

  const activeQuarterBounds = quarterBoundsFromReference(activeQuarterReference);
  const requestedPeriodStart = req.query.period_start || null;
  const requestedPeriodEnd = req.query.period_end || null;

  try {
    const result = await db.query(
      `
      SELECT
        bt.id,
        bt.txn_date,
        bt.merchant,
        bt.amount,
        bt.direction,
        bt.duplicate_flag,
        bt.duplicate_resolution,
        tc.category_code,
        tc.business_personal,
        COALESCE(tc.is_split, FALSE) AS is_split,
        tc.split_business_pct
      FROM bank_transactions bt
      LEFT JOIN transaction_classifications tc ON tc.bank_txn_id = bt.id
      WHERE bt.user_id = $1
        AND bt.txn_date BETWEEN $2::date AND $3::date
      `,
      [userId, activeQuarterBounds.periodStart, activeQuarterBounds.periodEnd]
    );
    const report = buildReadinessReport({
      periodStart: requestedPeriodStart,
      periodEnd: requestedPeriodEnd,
      asOfDate,
      transactions: result.rows
    });
    await recordReadinessRecalculated(db, {
      user_id: userId,
      actor_id: userId,
      source_type: 'system',
      quarter_reference: report.quarter_reference,
      description: `Readiness recalculated for ${report.period_start} to ${report.period_end}`,
      metadata: {
        ...report
      }
    });
    return res.status(200).json(report);
  } catch (err) {
    console.error('[InboxController] getReadiness failed:', err);
    return res.status(500).json({ error: 'Failed to compute readiness.' });
  }
};

module.exports = {
  ingestBankFeed,
  getInbox,
  classifyTransaction,
  resolveDuplicate,
  undoLastTriageAction,
  getReadiness
};
