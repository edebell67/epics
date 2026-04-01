const db = require('../config/db');
const actionController = require('./actionController');
const searchController = require('./searchController');
const itemController = require('./itemController');
const { isMonetaryItemType } = require('../services/monetaryIntegrityService');
const {
  evaluateAutoCommitEligibility
} = require('../services/autoCommitGovernanceService');
const {
  buildCaptureParseResult,
  toLegacyIntentShape
} = require('../services/voiceCaptureParserService');

/**
 * Simple Intent Parser and Slot Extractor (NLU Mock)
 * Matches transcripts to core intents and extracts slots using regex.
 */
function parseIntent(transcript, clientDateStr = null) {
  const parseResult = buildCaptureParseResult(transcript, clientDateStr);
  console.log(
    `[VoiceController] Intent matched: ${parseResult.detected_intent} ` +
    `confidence=${parseResult.confidence_score} review=${parseResult.requires_review}`
  );
  return toLegacyIntentShape(parseResult);
}

/**
 * Process incoming voice transcript
 */
const processVoice = async (req, res) => {
  const { transcript, device_id, current_date } = req.body;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  if (!transcript) {
    return res.status(400).json({ error: 'Missing transcript in request body' });
  }

  console.log(`[VoiceController] Incoming transcript: "${transcript}" from device: ${device_id} (Client Date: ${current_date})`);

  const captureIntents = {
    'capture_receipt': 'receipt',
    'capture_invoice': 'invoice',
    'capture_payment': 'payment',
    'capture_booking': 'booking',
    'capture_quote': 'quote',
    'create_reminder': 'reminder',
    'create_note': 'note',
    'capture_photo': 'image'
  };

  try {
    const parseState = parseIntent(transcript, current_date);
    const { intent, slots, confidence, parse_result: parseResult } = parseState;

    let confirmationText = `I've understood that as ${intent.replace(/_/g, ' ')}.`;
    let actionStatus = 'execute';

    // Handle Intent Logic
    if (captureIntents[intent]) {
      const type = captureIntents[intent];
      const shouldReview = Boolean(parseResult?.requires_review);
      const baseCompositionPayload = parseResult?.composition_payload || {
        type,
        status: itemController.AUTO_COMMIT_NON_MONETARY_TYPES.has(type) ? 'confirmed' : 'draft',
        amount: slots.amount || 0,
        extracted_text: transcript,
        raw_note: (type === 'note' || type === 'reminder') ? (slots.description || transcript) : transcript,
        client_name: slots.client_name || null,
        transaction_date: slots.date || new Date().toISOString().split('T')[0],
        due_date: type === 'reminder' ? (slots.date || new Date().toISOString().split('T')[0]) : null,
        voice_command_source_text: transcript,
        voice_action_confidence: confidence,
        labels: Array.isArray(slots.labels) ? slots.labels : []
      };
      
      // Attempt to find client by name if provided
      let clientId = null;
      if (slots.client_name) {
        const { rows } = await db.query('SELECT id, name FROM clients WHERE LOWER(name) LIKE $1 AND user_id = $2 LIMIT 1', [`%${slots.client_name}%`, userId]);
        if (rows.length > 0) {
          clientId = rows[0].id;
          slots.client_name = rows[0].name; // Use proper name
        }
      }

      if (shouldReview) {
        const reviewPayload = {
          ...baseCompositionPayload,
          client_id: clientId,
          client_name: slots.client_name || baseCompositionPayload.client_name || null,
          device_id
        };
        confirmationText = `I need you to review this ${type} before commit.`;
        actionStatus = 'review_required';
        return res.status(200).json({
          intent,
          slots,
          confidence,
          transcript,
          confirmation_text: confirmationText,
          action_status: actionStatus,
          parser_result: parseResult,
          review_reason: parseResult?.review_reason || 'low_confidence',
          missing_fields: parseResult?.missing_fields || [],
          composition_payload: reviewPayload
        });
      }

      if (isMonetaryItemType(type)) {
        const composition = await itemController.createItemInternal(
          {
            ...baseCompositionPayload,
            type,
            status: 'draft',
            device_id,
            client_id: clientId,
            client_name: slots.client_name || baseCompositionPayload.client_name || null,
            transaction_date: slots.date || baseCompositionPayload.transaction_date || new Date().toISOString()
          },
          { emitBusinessEvents: false }
        );

        const preview = itemController.buildMonetaryPreviewPayload(composition, {
          counterparty_name: slots.client_name || composition.client_name || null
        });

        const eligibility = await evaluateAutoCommitEligibility(db, {
          user_id: userId,
          entity_type: type,
          amount: preview.gross_amount ?? slots.amount ?? 0,
          confidence_score: confidence
        });

        if (eligibility.eligible) {
          const committed = await itemController.confirmCompositionInternal(composition.id, {
            user_id: userId,
            actor_id: userId,
            source_type: 'voice',
            commit_mode: 'auto',
            confirmation_reference: eligibility.state.confirmation_reference,
            updates: {
              client_id: clientId,
              client_name: slots.client_name || composition.client_name || null,
              transaction_date: slots.date || composition.captured_at || composition.created_at
            }
          });

          confirmationText = `Auto-committed ${type}${slots.amount ? ` £${slots.amount}` : ''}.`;
          actionStatus = 'committed';
          return res.status(200).json({
            intent,
            slots,
            confidence,
            transcript,
            confirmation_text: confirmationText,
            action_status: actionStatus,
            composition_id: composition.id,
            committed_entity_id: committed.id,
            item: committed,
            parser_result: parseResult,
            auto_commit: {
              enabled: true,
              expires_at: eligibility.state.expires_at,
              threshold_applied: eligibility.threshold_applied
            }
          });
        }

        confirmationText = `Preview ready for ${type}${slots.amount ? ` £${slots.amount}` : ''}. Confirm to commit.`;
        actionStatus = 'preview_required';
        return res.status(200).json({
          intent,
          slots,
          confidence,
          transcript,
          confirmation_text: confirmationText,
          action_status: actionStatus,
          composition_id: composition.id,
          preview,
          parser_result: parseResult,
          auto_commit: {
            enabled: eligibility.state.auto_commit_enabled,
            reasons_blocked: eligibility.reasons,
            threshold_applied: eligibility.threshold_applied,
            confidence_threshold: eligibility.confidence_threshold
          }
        });
      } else {
        const client = await db.pool.connect();
        try {
          await client.query('BEGIN');

          const created = await itemController.createItemInternal({
            ...baseCompositionPayload,
            type,
            status: 'confirmed',
            device_id,
            user_id: userId,
            client_id: clientId,
            client_name: slots.client_name || baseCompositionPayload.client_name || null,
            due_date: type === 'reminder' ? (slots.date || baseCompositionPayload.due_date || null) : baseCompositionPayload.due_date,
            transaction_date: slots.date || baseCompositionPayload.transaction_date || new Date().toISOString()
          }, { dbClient: client });

          if (type === 'booking') {
            const bookingDate = slots.date || new Date().toISOString();
            await client.query(
              'INSERT INTO calendar_events (user_id, title, start_at, end_at, client_id, event_type, device_id) VALUES ($1, $2, $3, $4, $5, $6, $7)',
              [userId, transcript, bookingDate, bookingDate, clientId, 'appointment', device_id]
            );
            confirmationText = `Booked ${slots.client_name ? 'with ' + slots.client_name : 'your meeting'} for ${slots.date || 'today'}.`;
          } else if (type === 'note') {
            await client.query(
              'INSERT INTO diary_entries (user_id, content, entry_date, client_id) VALUES ($1, $2, $3, $4)',
              [userId, baseCompositionPayload.raw_note || transcript, slots.date || new Date().toISOString(), clientId]
            );
            confirmationText = `Saved to your diary for ${slots.date || 'today'}.`;
          } else if (type === 'reminder') {
            confirmationText = `Reminder set for ${slots.date || 'today'}.`;
          } else {
            confirmationText = `Logged ${created.type}.`;
          }

          await client.query('COMMIT');
        } catch (err) {
          await client.query('ROLLBACK');
          throw err;
        } finally {
          client.release();
        }
      }
    } else if (intent === 'undo_last_action') {
      await db.query(
        `
        DELETE FROM capture_items
        WHERE id IN (
          SELECT id
          FROM capture_items
          WHERE user_id = $1 AND status = 'draft'
          ORDER BY created_at DESC
          LIMIT 1
        )
        `,
        [userId]
      );
      confirmationText = 'Undone. Last draft composition removed.';
    }

    res.status(200).json({
      intent,
      slots,
      confidence,
      transcript,
      confirmation_text: confirmationText,
      action_status: actionStatus,
      parser_result: parseResult || null
    });
  } catch (err) {
    console.error('[VoiceController] Error:', err);
    res.status(500).json({ error: 'Internal Voice Error' });
  }
};

const processMicroDecision = async (req, res) => {
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const { transcript = '', bank_txn_id = null, evidence_id = null } = req.body || {};
  const text = String(transcript).toLowerCase().trim();

  if (!text) return res.status(400).json({ error: 'Missing transcript.' });

  try {
    if (text.startsWith('category:')) {
      if (!bank_txn_id) return res.status(400).json({ error: 'bank_txn_id is required for category commands.' });
      const categoryName = text.replace('category:', '').trim();
      const categoryCode = categoryName.toUpperCase().replace(/[^A-Z0-9]+/g, '_');
      await db.query(
        `
        INSERT INTO transaction_classifications
        (user_id, bank_txn_id, category_code, category_name, source)
        VALUES ($1,$2,$3,$4,'manual')
        ON CONFLICT (bank_txn_id) DO UPDATE
        SET category_code=EXCLUDED.category_code, category_name=EXCLUDED.category_name, source='manual', updated_at=CURRENT_TIMESTAMP
        `,
        [userId, bank_txn_id, categoryCode, categoryName]
      );
      return res.status(200).json({ action_status: 'execute', confirmation_chip: `Applied: ${categoryName}` });
    }

    if (text === 'business' || text === 'personal') {
      if (!bank_txn_id) return res.status(400).json({ error: 'bank_txn_id is required for business/personal commands.' });
      const bp = text === 'business' ? 'BUSINESS' : 'PERSONAL';
      await db.query(
        `
        INSERT INTO transaction_classifications
        (user_id, bank_txn_id, business_personal, source)
        VALUES ($1,$2,$3,'manual')
        ON CONFLICT (bank_txn_id) DO UPDATE
        SET business_personal=EXCLUDED.business_personal, source='manual', updated_at=CURRENT_TIMESTAMP
        `,
        [userId, bank_txn_id, bp]
      );
      return res.status(200).json({ action_status: 'execute', confirmation_chip: `Applied: ${bp}` });
    }

    const splitMatch = text.match(/split\s+(\d{1,3})%?/);
    if (splitMatch) {
      if (!bank_txn_id) return res.status(400).json({ error: 'bank_txn_id is required for split commands.' });
      const pct = Number(splitMatch[1]);
      if (Number.isNaN(pct) || pct < 0 || pct > 100) {
        return res.status(400).json({ error: 'Split percentage must be 0-100.' });
      }
      await db.query(
        `
        INSERT INTO transaction_classifications
        (user_id, bank_txn_id, is_split, split_business_pct, source)
        VALUES ($1,$2,true,$3,'manual')
        ON CONFLICT (bank_txn_id) DO UPDATE
        SET is_split=true, split_business_pct=EXCLUDED.split_business_pct, source='manual', updated_at=CURRENT_TIMESTAMP
        `,
        [userId, bank_txn_id, pct]
      );
      return res.status(200).json({ action_status: 'execute', confirmation_chip: `Applied: Split ${pct}%` });
    }

    if (text.includes('attach receipt')) {
      return res.status(200).json({
        action_status: 'clarification_needed',
        confirmation_chip: 'Attach receipt requested',
        instruction: 'Use /api/v1/evidence/upload with file + metadata to attach receipt.'
      });
    }

    if (['match first', 'match second', 'match third'].includes(text)) {
      if (!evidence_id) return res.status(400).json({ error: 'evidence_id is required for match commands.' });
      const index = text === 'match first' ? 1 : text === 'match second' ? 2 : 3;
      const suggestions = await db.query(
        `
        WITH ev AS (
          SELECT id, doc_date, merchant, amount FROM evidence WHERE id = $1 AND user_id = $2
        )
        SELECT bt.id AS bank_txn_id
        FROM bank_transactions bt
        CROSS JOIN ev
        WHERE bt.user_id = $2
        ORDER BY (0.45 * GREATEST(0, 1 - LEAST(1, ABS(COALESCE(bt.amount, 0) - COALESCE(ev.amount, 0)) / NULLIF(GREATEST(ABS(COALESCE(ev.amount, 1)), 1), 0)))
               + 0.35 * GREATEST(0, 1 - LEAST(1, ABS(bt.txn_date - COALESCE(ev.doc_date, bt.txn_date)) / 14.0))
               + 0.20 * similarity(COALESCE(bt.merchant, ''), COALESCE(ev.merchant, ''))) DESC
        LIMIT 3
        `,
        [evidence_id, userId]
      );
      if (suggestions.rows.length < index) return res.status(404).json({ error: 'Requested match suggestion not available.' });
      const chosen = suggestions.rows[index - 1].bank_txn_id;
      await db.query(
        `
        INSERT INTO evidence_links (user_id, evidence_id, bank_txn_id, link_confidence, user_confirmed, confirmed_at, method)
        VALUES ($1,$2,$3,1,true,CURRENT_TIMESTAMP,'voice')
        ON CONFLICT (evidence_id, bank_txn_id)
        DO UPDATE SET user_confirmed=true, confirmed_at=CURRENT_TIMESTAMP, method='voice'
        `,
        [userId, evidence_id, chosen]
      );
      return res.status(200).json({ action_status: 'execute', confirmation_chip: `Applied: Match ${index}` });
    }

    if (text === 'no match') {
      if (!evidence_id) return res.status(400).json({ error: 'evidence_id is required for no match.' });
      await db.query(
        `
        INSERT INTO evidence_links (user_id, evidence_id, bank_txn_id, link_confidence, user_confirmed, confirmed_at, method)
        VALUES ($1,$2,NULL,0,true,CURRENT_TIMESTAMP,'voice')
        `,
        [userId, evidence_id]
      );
      return res.status(200).json({ action_status: 'execute', confirmation_chip: 'Applied: No match' });
    }

    return res.status(400).json({ error: 'Unsupported MVP voice micro-decision command.' });
  } catch (err) {
    console.error('[VoiceController] processMicroDecision error:', err);
    return res.status(500).json({ error: 'Failed to process micro-decision.' });
  }
};

module.exports = { parseIntent, processVoice, processMicroDecision };
