const db = require('../config/db');
const supabase = require('../config/supabase');
const fs = require('fs');
const path = require('path');
const {
  buildCorrectionAuditPayloads,
  isCommittedMonetaryItem,
  isMonetaryItemType,
  validateArchiveRequest,
  validateCorrectionRequest,
  validateItemUpdate
} = require('../services/monetaryIntegrityService');
const { validateAndClassifyMonetaryPayload } = require('../services/vatQuarterClassificationService');
const {
  buildClientCreatedEvent,
  recordEntityCommitted,
  buildItemCreatedEvent,
  recordCorrectionEvent,
  recordEntityCreated,
  recordReadinessRecalculated,
  recordQuoteConverted,
  recordStatusChange
} = require('../services/businessEventLogService');
const {
  AutoCommitGovernanceError,
  evaluateAutoCommitEligibility
} = require('../services/autoCommitGovernanceService');
const {
  QuarterGovernanceError,
  assertQuarterAllowsMonetaryActivity
} = require('../services/quarterLifecycleService');

const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000000';
const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj || {}, key);
const AUTO_COMMIT_NON_MONETARY_TYPES = new Set(['note', 'image', 'booking', 'reminder']);

const getDefaultUserId = (reqOrValue) => reqOrValue?.user?.id || reqOrValue || DEFAULT_USER_ID;

const resolveRelevantDate = (item) =>
  item.captured_at ||
  item.due_date ||
  item.transaction_date ||
  item.created_at ||
  new Date().toISOString();

const buildMonetaryPreviewPayload = (item, options = {}) => {
  const counterpartyName = options.counterparty_name || item.client_name || item.counterparty_name || null;
  const category = options.category || item.category || (Array.isArray(item.labels) && item.labels.length ? item.labels[0] : null);
  const confidenceScore = item.voice_action_confidence ?? item.extraction_confidence ?? null;

  return {
    composition_id: item.id,
    lifecycle_state: 'composition',
    entity_type: item.type,
    counterparty: counterpartyName,
    net_amount: item.net_amount ?? null,
    vat_amount: item.vat_amount ?? null,
    gross_amount: item.gross_amount ?? item.amount ?? null,
    vat_rate: item.vat_rate ?? null,
    category,
    relevant_date: resolveRelevantDate(item),
    confidence_score: confidenceScore,
    confidence_indicator: confidenceScore === null
      ? 'unknown'
      : confidenceScore >= 0.85
        ? 'high'
        : confidenceScore >= 0.6
          ? 'medium'
          : 'low',
    review_fields: {
      entity_type: item.type,
      counterparty: counterpartyName,
      net_amount: item.net_amount ?? null,
      vat_amount: item.vat_amount ?? null,
      gross_amount: item.gross_amount ?? item.amount ?? null,
      vat_rate: item.vat_rate ?? null,
      category,
      relevant_date: resolveRelevantDate(item)
    }
  };
};

const enqueueSyncPush = async (client, itemId) => {
  await client.query(
    `
    INSERT INTO job_queue (task_type, item_id, status, run_at)
    VALUES ('sync_push', $1, 'pending', CURRENT_TIMESTAMP)
    `,
    [itemId]
  );
};

const resolveClientId = async (client, providedClientId, clientName, userId) => {
  const cleanUUID = (uuid) => (uuid && uuid.trim() !== '' ? uuid : null);
  let resolvedClientId = cleanUUID(providedClientId);

  if (!resolvedClientId && clientName) {
    const findClient = await client.query(
      'SELECT id, name FROM clients WHERE name ILIKE $1 AND user_id = $2',
      [clientName, userId]
    );
    if (findClient.rows.length > 0) {
      return {
        clientId: findClient.rows[0].id,
        clientName: findClient.rows[0].name,
        created: false
      };
    }

    const createClient = await client.query(
      'INSERT INTO clients (name, user_id) VALUES ($1, $2) RETURNING id',
      [clientName, userId]
    );
    const newClientId = createClient.rows[0].id;
    await recordEntityCreated(client, buildClientCreatedEvent({
      id: newClientId,
      user_id: userId,
      name: clientName
    }, userId));
    console.log(`[ItemController] Created new client: ${clientName} (${newClientId})`);
    return {
      clientId: newClientId,
      clientName,
      created: true
    };
  }

  return {
    clientId: resolvedClientId,
    clientName: clientName || null,
    created: false
  };
};

/**
 * List items with basic filtering
 * GET /api/v1/items?type=receipt&status=draft
 */
const getItems = async (req, res) => {
  const { type, status, client_id, limit = 50, offset = 0 } = req.query;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  
  let queryText = `
    SELECT ci.*, ca.file_path as attachment_path 
    FROM capture_items ci
    LEFT JOIN capture_item_attachments ca ON ci.id = ca.item_id
    WHERE ci.status != $1 AND ci.user_id = $2 AND ci.deleted_at IS NULL
  `;
  let params = ['archived', userId];
  let count = 3;

  if (type) {
    queryText += ` AND type = $${count++}`;
    params.push(type);
  }

  if (status) {
    queryText += ` AND status = $${count++}`;
    params.push(status);
  }

  if (client_id) {
    queryText += ` AND client_id = $${count++}`;
    params.push(client_id);
  }

  queryText += ` ORDER BY created_at DESC LIMIT $${count++} OFFSET $${count++}`;
  params.push(limit, offset);

  try {
    const result = await db.query(queryText, params);
    res.status(200).json(result.rows);
  } catch (err) {
    console.error('[ItemController] Error in getItems:', err);
    res.status(500).json({ error: 'Failed to fetch items' });
  }
};

/**
 * Get single item by ID
 * GET /api/v1/items/:id
 */
const getItemById = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  try {
    const result = await db.query(
      'SELECT * FROM capture_items WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL', 
      [id, userId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Item not found or access denied' });
    }
    res.status(200).json(result.rows[0]);
  } catch (err) {
    console.error('[ItemController] Error in getItemById:', err);
    res.status(500).json({ error: 'Failed to fetch item' });
  }
};

/**
 * Calculate VAT classification, totals, and quarter assignment for a monetary item
 */
const calculateVATDetails = (item) => {
  if (!isMonetaryItemType(item.type)) {
    return {
      amount: item.amount ?? null,
      net_amount: item.net_amount ?? null,
      vat_amount: item.vat_amount ?? null,
      gross_amount: item.gross_amount ?? item.amount ?? null,
      vat_rate: item.vat_rate ?? null,
      vat_type: item.vat_type ?? null,
      quarter_reference: item.quarter_ref || item.quarter_reference || null,
      quarter_ref: item.quarter_ref || item.quarter_reference || null
    };
  }

  const transactionDate = item.transaction_date || item.txn_date || item.created_at || new Date().toISOString();
  return {
    ...item,
    ...validateAndClassifyMonetaryPayload({
      entityType: item.type,
      transactionDate,
      quarterReference: item.quarter_ref || item.quarter_reference,
      amount: item.amount,
      net_amount: item.net_amount,
      vat_amount: item.vat_amount,
      gross_amount: item.gross_amount,
      vat_rate: item.vat_rate,
      vat_type: item.vat_type
    })
  };
};

/**
 * Internal logic for creating an item (re-usable by other controllers like Voice)
 */
const writeAuditEvent = async (client, payload) => {
  await client.query(
    `INSERT INTO audit_events (action_type, entity_name, entity_id, user_id, device_id, diff_log)
     VALUES ($1, $2, $3, $4, $5, $6)`,
    [
      payload.action_type,
      payload.entity_name,
      payload.entity_id,
      payload.user_id,
      payload.device_id,
      JSON.stringify(payload.diff_log)
    ]
  );
};

const assertMonetaryQuarterOpen = async (client, {
  userId,
  quarterReference,
  operation,
  entityId = null,
  entityType = null
}) => {
  if (!quarterReference) {
    return null;
  }
  return assertQuarterAllowsMonetaryActivity(client, {
    userId,
    quarterReference,
    operation,
    entityId,
    entityType
  });
};

const createItemInternal = async (itemData, options = {}) => {
  let { 
    type, status, amount, currency, tax_flag, vat_amount, 
    due_date, client_id, job_id, extracted_text, raw_note, 
    device_id, labels, voice_command_source_text, voice_action_confidence,
    client_name, net_amount, gross_amount, vat_rate, vat_type, quarter_ref, transaction_date, user_id
  } = itemData;

  const userId = user_id || DEFAULT_USER_ID;
  const emitBusinessEvents = options.emitBusinessEvents !== false;
  const isMonetary = isMonetaryItemType(type);

  const details = calculateVATDetails({
    type, amount, net_amount, vat_amount, gross_amount, vat_rate, vat_type, quarter_ref, transaction_date
  });

  const cleanUUID = (uuid) => (uuid && uuid.trim() !== '' ? uuid : null);

  const externalClient = options.dbClient || null;
  const client = externalClient || await db.pool.connect();
  const managesTransaction = !externalClient;
  try {
    if (managesTransaction) {
      await client.query('BEGIN');
    }

    if (isMonetary && details.quarter_ref) {
      await assertMonetaryQuarterOpen(client, {
        userId,
        quarterReference: details.quarter_ref,
        operation: 'New monetary entry',
        entityType: type
      });
    }

    const resolvedClient = await resolveClientId(client, client_id, client_name, userId);
    const resolvedClientId = resolvedClient.clientId;

    const insertQuery = `
      INSERT INTO capture_items (
        type, status, amount, currency, tax_flag, vat_amount, 
        due_date, client_id, job_id, extracted_text, raw_note, device_id,
        voice_command_source_text, voice_action_confidence,
        net_amount, gross_amount, vat_rate, vat_type, quarter_ref, user_id,
        captured_at,
        payment_status
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
      RETURNING *
    `;
    const insertValues = [
      type,
      status || (AUTO_COMMIT_NON_MONETARY_TYPES.has(type) ? 'confirmed' : 'draft'),
      isMonetary ? (details.gross_amount ?? amount) : (amount ?? null),
      currency || 'GBP',
      isMonetary ? Boolean(tax_flag) : false,
      isMonetary ? (details.vat_amount ?? vat_amount) : null,
      due_date || null,
      resolvedClientId,
      cleanUUID(job_id),
      extracted_text || raw_note || null,
      raw_note || extracted_text || null,
      device_id,
      voice_command_source_text, voice_action_confidence,
      isMonetary ? details.net_amount : null,
      isMonetary ? details.gross_amount : (gross_amount ?? amount ?? null),
      isMonetary ? (details.vat_rate ?? 20) : null,
      isMonetary ? details.vat_type : null,
      isMonetary ? details.quarter_ref : null,
      userId,
      transaction_date || due_date || null,
      type === 'invoice' ? (itemData.payment_status || 'draft') : null
    ];
    const itemResult = await client.query(insertQuery, insertValues);
    const newItem = {
      ...itemResult.rows[0],
      client_name: resolvedClient.clientName,
      labels: Array.isArray(labels) ? labels : []
    };

    // Create Audit Event
    await writeAuditEvent(client, {
      action_type: 'create',
      entity_name: 'capture_items',
      entity_id: newItem.id,
      user_id: userId,
      device_id,
      diff_log: { new: newItem }
    });

    if (emitBusinessEvents) {
      await recordEntityCreated(
        client,
        buildItemCreatedEvent(newItem, userId, newItem.voice_command_source_text ? 'voice' : 'manual')
      );
    }

    // Handle labels if provided
    if (labels && Array.isArray(labels)) {
      for (const label of labels) {
        await client.query(
          'INSERT INTO capture_item_labels (item_id, label_name) VALUES ($1, $2)',
          [newItem.id, label]
        );
      }
      newItem.labels = labels;
    }

    if (managesTransaction) {
      await client.query('COMMIT');
    }
    return newItem;
  } catch (err) {
    if (managesTransaction) {
      await client.query('ROLLBACK');
    }
    throw err;
  } finally {
    if (managesTransaction) {
      client.release();
    }
  }
};

/**
 * Create a new capture item
 * POST /api/v1/items
 */
const createItem = async (req, res) => {
  const { type, device_id } = req.body;
  const userId = getDefaultUserId(req);

  if (!type || !device_id) {
    return res.status(400).json({ error: 'Missing required fields: type, device_id' });
  }

  try {
    if (isMonetaryItemType(type)) {
      const composition = await createItemInternal(
        { ...req.body, status: 'draft', user_id: userId },
        { emitBusinessEvents: false }
      );
      return res.status(201).json({
        action_status: 'preview_required',
        composition_id: composition.id,
        preview: buildMonetaryPreviewPayload(composition, { counterparty_name: composition.client_name })
      });
    }

    const defaultStatus = AUTO_COMMIT_NON_MONETARY_TYPES.has(type) ? 'confirmed' : req.body.status;
    const newItem = await createItemInternal({ ...req.body, status: defaultStatus, user_id: userId });
    res.status(201).json(newItem);
  } catch (err) {
    console.error('[ItemController] Error in createItem:', err);
    if (err instanceof QuarterGovernanceError) {
      return res.status(err.statusCode).json({ error: err.message, details: err.details });
    }
    res.status(500).json({ error: 'Failed to create item' });
  }
};

const confirmCompositionInternal = async (compositionId, options = {}) => {
  const userId = options.user_id || DEFAULT_USER_ID;
  const actorId = options.actor_id || userId;
  const sourceType = options.source_type || 'manual';
  const directFields = { ...(options.updates || {}) };
  const labels = Array.isArray(options.updates?.labels) ? options.updates.labels : null;
  const requestedCommitMode = options.commit_mode || 'manual';
  delete directFields.labels;

  const externalClient = options.dbClient || null;
  const client = externalClient || await db.pool.connect();
  const managesTransaction = !externalClient;

  try {
    if (managesTransaction) {
      await client.query('BEGIN');
    }

    const existingResult = await client.query(
      `
      SELECT ci.*, c.name AS client_name
      FROM capture_items ci
      LEFT JOIN clients c ON c.id = ci.client_id
      WHERE ci.id = $1 AND ci.user_id = $2 AND ci.deleted_at IS NULL
      `,
      [compositionId, userId]
    );

    if (existingResult.rows.length === 0) {
      throw new Error('Composition not found or access denied');
    }

    const existingItem = existingResult.rows[0];
    if (!isMonetaryItemType(existingItem.type)) {
      throw new Error('Only monetary compositions support confirm.');
    }
    if (existingItem.status !== 'draft') {
      throw new Error(`Composition ${compositionId} is already committed.`);
    }

    const resolvedClient = await resolveClientId(
      client,
      directFields.client_id ?? existingItem.client_id,
      directFields.client_name ?? existingItem.client_name,
      userId
    );

    const nextState = {
      ...existingItem,
      ...directFields,
      client_id: resolvedClient.clientId,
      client_name: resolvedClient.clientName,
      transaction_date: directFields.transaction_date || directFields.captured_at || existingItem.captured_at || existingItem.created_at
    };

    const amountPayload = {
      type: existingItem.type,
      amount: hasOwn(directFields, 'amount') ? directFields.amount : existingItem.amount,
      net_amount: hasOwn(directFields, 'net_amount') ? directFields.net_amount : existingItem.net_amount,
      vat_amount: hasOwn(directFields, 'vat_amount') ? directFields.vat_amount : existingItem.vat_amount,
      gross_amount: hasOwn(directFields, 'gross_amount')
        ? directFields.gross_amount
        : (hasOwn(directFields, 'amount') ? directFields.amount : existingItem.gross_amount),
      vat_rate: hasOwn(directFields, 'vat_rate') ? directFields.vat_rate : existingItem.vat_rate,
      vat_type: hasOwn(directFields, 'vat_type') ? directFields.vat_type : existingItem.vat_type,
      quarter_ref: hasOwn(directFields, 'quarter_ref') ? directFields.quarter_ref : existingItem.quarter_ref,
      transaction_date: nextState.transaction_date
    };

    const monetaryDetails = calculateVATDetails(amountPayload);

    if (requestedCommitMode === 'auto') {
      const eligibility = await evaluateAutoCommitEligibility(client, {
        user_id: userId,
        entity_type: existingItem.type,
        amount: monetaryDetails.gross_amount ?? nextState.amount,
        confidence_score: nextState.voice_action_confidence ?? existingItem.voice_action_confidence ?? null
      });
      if (!eligibility.eligible) {
        throw new AutoCommitGovernanceError('Capture is not eligible for auto-commit.', 409, {
          reasons: eligibility.reasons,
          threshold_applied: eligibility.threshold_applied,
          confidence_threshold: eligibility.confidence_threshold
        });
      }
    }

    await assertMonetaryQuarterOpen(client, {
      userId,
      quarterReference: monetaryDetails.quarter_ref,
      operation: 'Confirm monetary entry',
      entityId: compositionId,
      entityType: existingItem.type
    });

    const updateResult = await client.query(
      `
      UPDATE capture_items
      SET
        amount = $3,
        vat_amount = $4,
        due_date = $5,
        client_id = $6,
        job_id = $7,
        extracted_text = $8,
        raw_note = $9,
        voice_command_source_text = $10,
        voice_action_confidence = $11,
        net_amount = $12,
        gross_amount = $13,
        vat_rate = $14,
        vat_type = $15,
        quarter_ref = $16,
        captured_at = $17,
        status = 'confirmed',
        updated_at = CURRENT_TIMESTAMP
      WHERE id = $1 AND user_id = $2
      RETURNING *
      `,
      [
        compositionId,
        userId,
        monetaryDetails.gross_amount ?? nextState.amount,
        monetaryDetails.vat_amount,
        nextState.due_date || null,
        resolvedClient.clientId,
        nextState.job_id || null,
        nextState.extracted_text || existingItem.extracted_text,
        nextState.raw_note || existingItem.raw_note,
        nextState.voice_command_source_text || existingItem.voice_command_source_text,
        nextState.voice_action_confidence ?? existingItem.voice_action_confidence,
        monetaryDetails.net_amount,
        monetaryDetails.gross_amount,
        monetaryDetails.vat_rate,
        monetaryDetails.vat_type,
        monetaryDetails.quarter_ref,
        nextState.transaction_date || null
      ]
    );

    if (labels) {
      await client.query('DELETE FROM capture_item_labels WHERE item_id = $1', [compositionId]);
      for (const label of labels) {
        await client.query(
          'INSERT INTO capture_item_labels (item_id, label_name) VALUES ($1, $2)',
          [compositionId, label]
        );
      }
    }

    const confirmedItem = {
      ...updateResult.rows[0],
      client_name: resolvedClient.clientName,
      labels: labels || []
    };

    await recordEntityCommitted(client, {
      user_id: userId,
      actor_id: actorId,
      source_type: sourceType,
      entity_id: confirmedItem.id,
      entity_type: confirmedItem.type,
      quarter_reference: confirmedItem.quarter_ref || null,
      status_from: existingItem.status,
      status_to: 'confirmed',
      description: `${confirmedItem.type} committed`,
      metadata: {
        commit_mode: requestedCommitMode,
        confirmation_reference: options.confirmation_reference || null,
        gross_amount: confirmedItem.gross_amount,
        confidence_score: confirmedItem.voice_action_confidence ?? null
      }
    });

    await recordReadinessRecalculated(client, {
      user_id: userId,
      actor_id: actorId,
      source_type: sourceType,
      quarter_reference: confirmedItem.quarter_ref || null,
      entity_id: confirmedItem.id,
      entity_type: confirmedItem.type,
      description: `Readiness recalculated after confirming ${confirmedItem.type} ${confirmedItem.id}`,
      metadata: {
        trigger: 'composition_confirmed',
        composition_id: compositionId,
        gross_amount: confirmedItem.gross_amount,
        vat_amount: confirmedItem.vat_amount
      }
    });

    await enqueueSyncPush(client, confirmedItem.id);

    if (managesTransaction) {
      await client.query('COMMIT');
    }

    return confirmedItem;
  } catch (err) {
    if (managesTransaction) {
      await client.query('ROLLBACK');
    }
    throw err;
  } finally {
    if (managesTransaction) {
      client.release();
    }
  }
};

const confirmComposition = async (req, res) => {
  const { id } = req.params;
  const userId = getDefaultUserId(req);

  try {
    const confirmedItem = await confirmCompositionInternal(id, {
      user_id: userId,
      actor_id: userId,
      source_type: req.body?.source_type || 'manual',
      commit_mode: req.body?.commit_mode || 'manual',
      confirmation_reference: req.body?.confirmation_reference || null,
      updates: req.body || {}
    });

    return res.status(200).json({
      action_status: 'committed',
      composition_id: id,
      committed_entity_id: confirmedItem.id,
      item: confirmedItem
    });
  } catch (err) {
    console.error('[ItemController] Error in confirmComposition:', err);
    const status = err instanceof QuarterGovernanceError
      ? err.statusCode
      : (err.message.includes('not found') ? 404 : 409);
    return res.status(status).json({ error: err.message });
  }
};

/**
 * Update capture item (labels, status, link)
 * PATCH /api/v1/items/:id
 */
const updateItem = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const updates = req.body;
  const { labels, ...directFields } = updates;

  const client = await db.pool.connect();
  try {
    await client.query('BEGIN');

    const existingResult = await client.query(
      'SELECT * FROM capture_items WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL',
      [id, userId]
    );

    if (existingResult.rows.length === 0) {
      await client.query('ROLLBACK');
      return res.status(404).json({ error: 'Item not found or access denied' });
    }

    const existingItem = existingResult.rows[0];
    const targetQuarterReference = hasOwn(directFields, 'quarter_ref')
      ? directFields.quarter_ref
      : existingItem.quarter_ref;
    const touchesQuarter = isMonetaryItemType(existingItem.type) && (
      Object.keys(directFields).length > 0
      || (labels && Array.isArray(labels))
    );

    if (touchesQuarter && targetQuarterReference) {
      await assertMonetaryQuarterOpen(client, {
        userId,
        quarterReference: targetQuarterReference,
        operation: 'Monetary entry update',
        entityId: existingItem.id,
        entityType: existingItem.type
      });
    }

    const validation = validateItemUpdate(existingItem, directFields);
    if (!validation.valid) {
      await client.query('ROLLBACK');
      return res.status(409).json({
        error: validation.errors[0],
        details: validation.errors,
        immutable_fields: validation.immutableChanges
      });
    }

    // Update direct fields on capture_items
    if (Object.keys(directFields).length > 0) {
      const setClause = Object.keys(directFields).map((key, i) => `${key} = $${i + 3}`).join(', ');
      const updateValues = [id, userId, ...Object.values(directFields)];
      await client.query(
        `UPDATE capture_items SET ${setClause}, updated_at = CURRENT_TIMESTAMP WHERE id = $1 AND user_id = $2`, 
        updateValues
      );
    }

    // Update labels if provided (REPLACE strategy)
    if (labels && Array.isArray(labels)) {
      // First verify ownership
      const checkRes = await client.query('SELECT id FROM capture_items WHERE id = $1 AND user_id = $2', [id, userId]);
      if (checkRes.rows.length === 0) throw new Error('Item not found or access denied');

      await client.query('DELETE FROM capture_item_labels WHERE item_id = $1', [id]);
      for (const label of labels) {
        await client.query(
          'INSERT INTO capture_item_labels (item_id, label_name) VALUES ($1, $2)',
          [id, label]
        );
      }
    }

    const finalResult = await client.query('SELECT * FROM capture_items WHERE id = $1 AND user_id = $2', [id, userId]);
    const updatedItem = finalResult.rows[0];

    if (directFields.status && directFields.status !== existingItem.status) {
      await recordStatusChange(client, {
        user_id: userId,
        actor_id: userId,
        source_type: 'manual',
        entity_id: updatedItem.id,
        entity_type: updatedItem.type,
        quarter_reference: updatedItem.quarter_ref || null,
        status_from: existingItem.status,
        status_to: directFields.status,
        description: `${updatedItem.type} ${updatedItem.id} status changed from ${existingItem.status} to ${directFields.status}`,
        metadata: {
          labels_updated: Array.isArray(labels),
          payment_status: updatedItem.payment_status || null
        }
      });
    }

    await client.query('COMMIT');
    res.status(200).json(updatedItem);
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[ItemController] Error in updateItem:', err);
    if (err instanceof QuarterGovernanceError) {
      return res.status(err.statusCode).json({ error: err.message, details: err.details });
    }
    res.status(500).json({ error: 'Failed to update item' });
  } finally {
    client.release();
  }
};

/**
 * Archive item (Soft Delete)
 * DELETE /api/v1/items/:id
 */
const archiveItem = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  try {
    const existingResult = await db.query(
      'SELECT * FROM capture_items WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL',
      [id, userId]
    );

    if (existingResult.rows.length === 0) {
      return res.status(404).json({ error: 'Item not found or access denied' });
    }

    const archiveValidation = validateArchiveRequest(existingResult.rows[0]);
    if (!archiveValidation.valid) {
      return res.status(409).json({
        error: archiveValidation.errors[0],
        details: archiveValidation.errors
      });
    }

    if (isMonetaryItemType(existingResult.rows[0].type) && existingResult.rows[0].quarter_ref) {
      await assertQuarterAllowsMonetaryActivity(db, {
        userId,
        quarterReference: existingResult.rows[0].quarter_ref,
        operation: 'Monetary entry archive',
        entityId: existingResult.rows[0].id,
        entityType: existingResult.rows[0].type
      });
    }

    const result = await db.query(
      "UPDATE capture_items SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = $1 AND user_id = $2 RETURNING id",
      [id, userId]
    );
    res.status(200).json({ message: 'Item deleted successfully', id: result.rows[0].id });
  } catch (err) {
    console.error('[ItemController] Error in archiveItem:', err);
    if (err instanceof QuarterGovernanceError) {
      return res.status(err.statusCode).json({ error: err.message, details: err.details });
    }
    res.status(500).json({ error: 'Failed to archive item' });
  }
};

/**
 * Get a summary of items captured today
 * (Used for voice summary)
 */
const getDailySummary = async (device_id) => {
  const query = `
    SELECT 
      type, 
      COUNT(*) as count, 
      SUM(COALESCE(amount, 0)) as total
    FROM capture_items 
    WHERE device_id = $1 
    AND created_at >= CURRENT_DATE
    AND status != 'archived'
    AND deleted_at IS NULL
    GROUP BY type
  `;
  const result = await db.query(query, [device_id]);
  return result.rows;
};

/**
 * Handle image upload and create capture_item + attachment
 * POST /api/v1/items/upload
 */
const uploadImage = async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No image file uploaded' });
  }

  const { device_id = 'unknown' } = req.body;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';
  const bucketName = process.env.SUPABASE_STORAGE_BUCKET || 'bizpa-uploads';

  try {
    const itemData = {
      type: 'image',
      status: 'confirmed',
      raw_note: `Uploaded image: ${req.file.originalname}`,
      device_id: device_id,
      user_id: userId
    };

    const newItem = await createItemInternal(itemData);

    let finalPath = req.file.path;
    let isCloud = false;

    // Upload to Supabase Storage if available
    if (supabase) {
      const fileContent = fs.readFileSync(req.file.path);
      const fileName = `${userId}/${newItem.id}-${req.file.originalname}`;
      
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from(bucketName)
        .upload(fileName, fileContent, {
          contentType: req.file.mimetype,
          upsert: true
        });

      if (uploadError) {
        console.error('[Supabase Storage] Upload Error:', uploadError);
      } else if (uploadData) {
        finalPath = uploadData.path;
        isCloud = true;
      }
    } else {
      console.warn('[Storage] Supabase client not initialized. Saving locally only.');
    }

    // Add attachment
    const attachmentQuery = `
      INSERT INTO capture_item_attachments (item_id, kind, file_path, metadata)
      VALUES ($1, $2, $3, $4)
      RETURNING *
    `;
    const attachmentValues = [
      newItem.id, 
      'image', 
      finalPath, 
      JSON.stringify({ 
        originalName: req.file.originalname, 
        size: req.file.size,
        storage: isCloud ? 'supabase' : 'local',
        bucket: bucketName
      })
    ];
    await db.query(attachmentQuery, attachmentValues);

    // Cleanup local file if successfully uploaded to cloud
    if (isCloud) {
      try {
        fs.unlinkSync(req.file.path);
      } catch (err) {
        console.warn('[Storage] Failed to cleanup local file:', req.file.path);
      }
    }

    res.status(201).json({ ...newItem, attachment_path: finalPath, storage: isCloud ? 'supabase' : 'local' });
  } catch (err) {
    console.error('[ItemController] Error in uploadImage:', err);
    res.status(500).json({ error: 'Failed to upload image' });
  }
};

/**
 * Convert Quote to Invoice
 * POST /api/v1/items/:id/convert
 */
const convertQuoteToInvoiceInternal = async (quoteId, options = {}) => {
  const userId = options.user_id || DEFAULT_USER_ID;
  const actorId = options.actor_id || userId;
  const sourceType = options.source_type || 'manual';
  const externalClient = options.dbClient || null;
  const client = externalClient || await db.pool.connect();
  const managesTransaction = !externalClient;

  try {
    if (managesTransaction) {
      await client.query('BEGIN');
    }

    const quoteRes = await client.query(
      'SELECT * FROM capture_items WHERE id = $1 AND user_id = $2 AND type = $3 AND deleted_at IS NULL',
      [quoteId, userId, 'quote']
    );

    if (quoteRes.rows.length === 0) {
      throw new Error('Quote not found or already converted');
    }

    const quote = quoteRes.rows[0];

    if (quote.quarter_ref) {
      await assertMonetaryQuarterOpen(client, {
        userId,
        quarterReference: quote.quarter_ref,
        operation: 'Quote conversion to invoice',
        entityId: quote.id,
        entityType: quote.type
      });
    }

    const invoiceQuery = `
      INSERT INTO capture_items (
        type, status, amount, currency, tax_flag, vat_amount, 
        due_date, client_id, job_id, extracted_text, raw_note, device_id,
        user_id, net_amount, gross_amount, vat_rate, vat_type, quarter_ref,
        converted_from_id, payment_status
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
      RETURNING *
    `;

    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + 30);

    const invoiceValues = [
      'invoice', 'confirmed', quote.amount, quote.currency, quote.tax_flag, quote.vat_amount,
      dueDate.toISOString().split('T')[0], quote.client_id, quote.job_id, 
      `Converted from Quote ${quote.reference_number}: ${quote.extracted_text}`, 
      quote.raw_note, quote.device_id, userId, quote.net_amount, quote.gross_amount, 
      quote.vat_rate, quote.vat_type || 'output', quote.quarter_ref, quote.id, 'sent'
    ];

    const invoiceRes = await client.query(invoiceQuery, invoiceValues);
    const invoice = invoiceRes.rows[0];

    await recordEntityCreated(client, buildItemCreatedEvent(invoice, actorId, sourceType));

    await client.query(
      "UPDATE capture_items SET status = 'confirmed', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
      [quote.id]
    );

    await recordQuoteConverted(client, {
      user_id: userId,
      actor_id: actorId,
      source_type: sourceType,
      quote_id: quote.id,
      invoice_id: invoice.id,
      quarter_reference: invoice.quarter_ref || quote.quarter_ref || null,
      metadata: {
        client_id: invoice.client_id,
        job_id: invoice.job_id
      }
    });

    if (managesTransaction) {
      await client.query('COMMIT');
    }
    return invoice;
  } catch (err) {
    if (managesTransaction) {
      await client.query('ROLLBACK');
    }
    throw err;
  } finally {
    if (managesTransaction) {
      client.release();
    }
  }
};

const convertQuoteToInvoice = async (req, res) => {
  const { id } = req.params;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  try {
    const invoice = await convertQuoteToInvoiceInternal(id, {
      user_id: userId,
      actor_id: userId,
      source_type: 'manual'
    });
    res.status(201).json(invoice);
  } catch (err) {
    console.error('[ItemController] Error in convertQuoteToInvoice:', err);
    if (err instanceof QuarterGovernanceError) {
      return res.status(err.statusCode).json({ error: err.message, details: err.details });
    }
    if (err.message.includes('not found')) {
      return res.status(404).json({ error: err.message });
    }
    res.status(500).json({ error: 'Failed to convert quote' });
  }
};

/**
 * Apply explicit correction flow for a committed monetary item
 * POST /api/v1/items/:id/corrections
 */
const applyCorrection = async (req, res) => {
  const { id } = req.params;
  const { action, reason, replacement = {} } = req.body;
  const userId = req.user?.id || '00000000-0000-0000-0000-000000000000';

  const client = await db.pool.connect();
  try {
    await client.query('BEGIN');

    const existingResult = await client.query(
      'SELECT * FROM capture_items WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL',
      [id, userId]
    );

    if (existingResult.rows.length === 0) {
      await client.query('ROLLBACK');
      return res.status(404).json({ error: 'Item not found or access denied' });
    }

    const existingItem = existingResult.rows[0];
    const correctionValidation = validateCorrectionRequest(existingItem, action, reason, replacement);
    if (!correctionValidation.valid) {
      await client.query('ROLLBACK');
      return res.status(409).json({
        error: correctionValidation.errors[0],
        details: correctionValidation.errors
      });
    }

    await assertMonetaryQuarterOpen(client, {
      userId,
      quarterReference: existingItem.quarter_ref,
      operation: 'Monetary correction',
      entityId: existingItem.id,
      entityType: existingItem.type
    });

    let replacementItem = null;
    if (action === 'replace' || action === 'supersede') {
      replacementItem = await createItemInternal(
        { ...correctionValidation.replacementItemData, user_id: userId },
        { dbClient: client }
      );
    }

    const auditPayloads = buildCorrectionAuditPayloads({
      action,
      originalItem: existingItem,
      replacementItem,
      reason,
      userId,
      deviceId: replacement.device_id || existingItem.device_id
    });

    for (const payload of auditPayloads) {
      await writeAuditEvent(client, payload);
    }

    await recordCorrectionEvent(client, {
      user_id: userId,
      actor_id: userId,
      source_type: 'manual',
      entity_id: existingItem.id,
      entity_type: existingItem.type,
      quarter_reference: existingItem.quarter_ref || null,
      action,
      status_from: existingItem.status,
      status_to: action === 'void' ? 'void_requested' : 'replacement_created',
      description: `${existingItem.type} ${existingItem.id} correction recorded: ${action}`,
      metadata: {
        reason,
        replacement_item_id: replacementItem?.id || null
      }
    });

    await client.query('COMMIT');
    res.status(action === 'void' ? 200 : 201).json({
      message: action === 'void' ? 'Correction event recorded' : 'Correction and replacement recorded',
      action,
      original_item_id: existingItem.id,
      replacement_item_id: replacementItem?.id || null,
      correction_metadata: auditPayloads.map((payload) => payload.diff_log),
      committed_item_protected: isCommittedMonetaryItem(existingItem)
    });
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[ItemController] Error in applyCorrection:', err);
    if (err instanceof QuarterGovernanceError) {
      return res.status(err.statusCode).json({ error: err.message, details: err.details });
    }
    res.status(500).json({ error: 'Failed to apply correction' });
  } finally {
    client.release();
  }
};

/**
 * Trigger overdue status update
 * GET /api/v1/items/maintenance/check-overdue
 */
const checkOverdueItems = async (req, res) => {
  try {
    const count = await db.query('SELECT update_overdue_statuses() as count');
    res.status(200).json({ updated_count: count.rows[0].count });
  } catch (err) {
    console.error('[ItemController] Error in checkOverdueItems:', err);
    res.status(500).json({ error: 'Failed to update overdue statuses' });
  }
};

module.exports = {
  AUTO_COMMIT_NON_MONETARY_TYPES,
  buildMonetaryPreviewPayload,
  confirmComposition,
  confirmCompositionInternal,
  getItems,
  getItemById,
  createItem,
  createItemInternal,
  getDailySummary,
  updateItem,
  archiveItem,
  uploadImage,
  convertQuoteToInvoiceInternal,
  convertQuoteToInvoice,
  applyCorrection,
  checkOverdueItems
};
