const db = require('../config/db');

const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000000';

async function getTopSuggestions(userId, evidenceId, limit = 3) {
  const query = `
    WITH ev AS (
      SELECT id, doc_date, merchant, amount
      FROM evidence
      WHERE id = $1 AND user_id = $2
    )
    SELECT
      bt.id AS bank_txn_id,
      bt.txn_date,
      bt.merchant,
      bt.amount,
      bt.direction,
      GREATEST(0, 1 - LEAST(1, ABS(COALESCE(bt.amount, 0) - COALESCE(ev.amount, 0)) / NULLIF(GREATEST(ABS(COALESCE(ev.amount, 1)), 1), 0))) AS amount_score,
      GREATEST(0, 1 - LEAST(1, ABS(bt.txn_date - COALESCE(ev.doc_date, bt.txn_date)) / 14.0)) AS date_score,
      similarity(COALESCE(bt.merchant, ''), COALESCE(ev.merchant, '')) AS merchant_score
    FROM bank_transactions bt
    CROSS JOIN ev
    WHERE bt.user_id = $2
    ORDER BY (0.45 * GREATEST(0, 1 - LEAST(1, ABS(COALESCE(bt.amount, 0) - COALESCE(ev.amount, 0)) / NULLIF(GREATEST(ABS(COALESCE(ev.amount, 1)), 1), 0)))
             +0.35 * GREATEST(0, 1 - LEAST(1, ABS(bt.txn_date - COALESCE(ev.doc_date, bt.txn_date)) / 14.0))
             +0.20 * similarity(COALESCE(bt.merchant, ''), COALESCE(ev.merchant, ''))) DESC
    LIMIT $3
  `;
  const res = await db.query(query, [evidenceId, userId, limit]);
  return res.rows;
}

const uploadEvidence = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const {
    type = 'RECEIPT',
    doc_date = null,
    merchant = null,
    amount = null,
    extraction_confidence = null
  } = req.body || {};

  if (!req.file?.path) {
    return res.status(400).json({ error: 'Missing evidence file upload.' });
  }

  try {
    const created = await db.query(
      `
      INSERT INTO evidence (user_id, type, doc_date, merchant, amount, storage_link, extraction_confidence, extraction_payload)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
      RETURNING *
      `,
      [userId, String(type).toUpperCase(), doc_date, merchant, amount, req.file.path, extraction_confidence, req.body || {}]
    );
    const evidence = created.rows[0];
    const suggestions = await getTopSuggestions(userId, evidence.id, 3);
    return res.status(201).json({ evidence, suggestions });
  } catch (err) {
    console.error('[EvidenceController] uploadEvidence failed:', err);
    return res.status(500).json({ error: 'Failed to store evidence.' });
  }
};

const getEvidenceSuggestions = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const evidenceId = req.params.id;
  try {
    const suggestions = await getTopSuggestions(userId, evidenceId, 3);
    return res.status(200).json(suggestions);
  } catch (err) {
    console.error('[EvidenceController] getEvidenceSuggestions failed:', err);
    return res.status(500).json({ error: 'Failed to load suggestions.' });
  }
};

const confirmEvidenceMatch = async (req, res) => {
  const userId = req.user?.id || DEFAULT_USER_ID;
  const evidenceId = req.params.id;
  const { bank_txn_id = null, method = 'manual', no_match = false } = req.body || {};

  try {
    if (no_match || !bank_txn_id) {
      await db.query(
        `
        INSERT INTO evidence_links (user_id, evidence_id, bank_txn_id, link_confidence, user_confirmed, confirmed_at, method)
        VALUES ($1,$2,NULL,0,true,CURRENT_TIMESTAMP,$3)
        ON CONFLICT (evidence_id, bank_txn_id) DO NOTHING
        `,
        [userId, evidenceId, method]
      );
      return res.status(200).json({ status: 'confirmed_no_match' });
    }

    const score = await db.query(
      `
      SELECT
        GREATEST(0, 1 - LEAST(1, ABS(COALESCE(bt.amount, 0) - COALESCE(ev.amount, 0)) / NULLIF(GREATEST(ABS(COALESCE(ev.amount, 1)), 1), 0))) AS amount_score,
        GREATEST(0, 1 - LEAST(1, ABS(bt.txn_date - COALESCE(ev.doc_date, bt.txn_date)) / 14.0)) AS date_score,
        similarity(COALESCE(bt.merchant, ''), COALESCE(ev.merchant, '')) AS merchant_score
      FROM bank_transactions bt
      JOIN evidence ev ON ev.id = $2 AND ev.user_id = $1
      WHERE bt.id = $3 AND bt.user_id = $1
      `,
      [userId, evidenceId, bank_txn_id]
    );
    if (!score.rows.length) return res.status(404).json({ error: 'Evidence or bank transaction not found.' });
    const s = score.rows[0];
    const confidence = Math.max(0, Math.min(1, (0.45 * Number(s.amount_score)) + (0.35 * Number(s.date_score)) + (0.2 * Number(s.merchant_score))));

    await db.query(
      `
      INSERT INTO evidence_links (user_id, evidence_id, bank_txn_id, link_confidence, user_confirmed, confirmed_at, method)
      VALUES ($1,$2,$3,$4,true,CURRENT_TIMESTAMP,$5)
      ON CONFLICT (evidence_id, bank_txn_id)
      DO UPDATE SET
        user_confirmed = true,
        confirmed_at = CURRENT_TIMESTAMP,
        link_confidence = EXCLUDED.link_confidence,
        method = EXCLUDED.method
      `,
      [userId, evidenceId, bank_txn_id, confidence, method]
    );
    return res.status(200).json({ status: 'confirmed_match', bank_txn_id, link_confidence: confidence });
  } catch (err) {
    console.error('[EvidenceController] confirmEvidenceMatch failed:', err);
    return res.status(500).json({ error: 'Failed to confirm evidence match.' });
  }
};

module.exports = {
  uploadEvidence,
  getEvidenceSuggestions,
  confirmEvidenceMatch
};
