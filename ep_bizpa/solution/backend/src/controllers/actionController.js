const db = require('../config/db');

/**
 * Undo the last action for a specific device
 * POST /api/v1/action/undo
 */
const undoLastAction = async (req, res) => {
  const { device_id } = req.body;

  if (!device_id) {
    return res.status(400).json({ error: 'Missing device_id' });
  }

  const client = await db.pool.connect();
  try {
    await client.query('BEGIN');

    // 1. Find the latest audit event for this device in the last 60 seconds
    const findAuditQuery = `
      SELECT * FROM audit_events 
      WHERE device_id = $1 
      AND created_at > NOW() - INTERVAL '60 seconds'
      AND action_type IN ('create', 'update', 'delete')
      ORDER BY created_at DESC 
      LIMIT 1
    `;
    const auditRes = await client.query(findAuditQuery, [device_id]);

    if (auditRes.rows.length === 0) {
      await client.query('ROLLBACK');
      return res.status(404).json({ error: 'No recent action found to undo' });
    }

    const lastAction = auditRes.rows[0];
    const { action_type, entity_name, entity_id, diff_log } = lastAction;

    console.log(`[Undo] Reverting ${action_type} on ${entity_name} (${entity_id})`);

    // 2. Perform Reversion Logic
    if (action_type === 'create') {
      await client.query(`DELETE FROM ${entity_name} WHERE id = $1`, [entity_id]);
    } 
    else if (action_type === 'update') {
      const oldData = diff_log.old;
      if (!oldData) {
        throw new Error('Old data missing from audit log for update reversion');
      }
      const fields = Object.keys(oldData).filter(key => key !== 'id' && key !== 'updated_at' && key !== 'created_at');
      const setClause = fields.map((key, i) => `${key} = $${i + 2}`).join(', ');
      const values = [entity_id, ...fields.map(f => oldData[f])];
      await client.query(`UPDATE ${entity_name} SET ${setClause}, updated_at = CURRENT_TIMESTAMP WHERE id = $1`, values);
    } 
    else if (action_type === 'delete') {
      const oldData = diff_log.old;
      const statusToRestore = (oldData && oldData.status) ? oldData.status : 'confirmed';
      await client.query(`UPDATE ${entity_name} SET status = $2, updated_at = CURRENT_TIMESTAMP WHERE id = $1`, [entity_id, statusToRestore]);
    }

    await client.query('DELETE FROM audit_events WHERE id = $1', [lastAction.id]);

    await client.query('COMMIT');
    res.status(200).json({ 
      message: 'Action undone successfully', 
      reverted_action: action_type,
      entity: entity_name,
      intent: 'undo_last_action',
      slots: {},
      confidence: 1.0,
      confirmation_text: `Undone last ${action_type}.`,
      action_status: 'execute'
    });
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[ActionController] Undo Error:', err);
    res.status(500).json({ error: 'Failed to undo last action' });
  } finally {
    client.release();
  }
};

module.exports = {
  undoLastAction
};