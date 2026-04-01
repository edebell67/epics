const db = require('../config/db');
const { validateSyncChanges } = require('../services/syncValidationService');
const {
  DEFAULT_TENANT_ID,
  buildPullChangeEnvelope,
  buildResultEnvelope,
  buildSyncEnvelope,
  evaluateSyncConflict
} = require('../services/syncEnvelopeService');
const {
  buildSyncRunTelemetry,
  loadSyncHealthSnapshot,
  recordSyncTelemetry
} = require('../services/syncHealthService');

const SYNC_DEVICE_RELATION_MISSING = '42P01';

const ensureSyncDeviceRegistration = async (client, tenantId, deviceId) => {
  try {
    await client.query(
      `
      INSERT INTO sync_devices (user_id, device_id, last_sync_at)
      VALUES ($1, $2, CURRENT_TIMESTAMP)
      ON CONFLICT (user_id, device_id)
      DO UPDATE SET last_sync_at = CURRENT_TIMESTAMP
      `,
      [tenantId, deviceId]
    );
  } catch (err) {
    if (err.code !== SYNC_DEVICE_RELATION_MISSING) {
      throw err;
    }
  }
};

const fetchExistingRecord = async (client, tableName, entityId, tenantId) => {
  const result = await client.query(
    `SELECT * FROM ${tableName} WHERE id = $1 AND user_id = $2`,
    [entityId, tenantId]
  );
  return result.rows[0] || null;
};

const countUnresolvedResults = (results = []) =>
  results.filter((result) => result.status === 'conflict' || result.status === 'error').length;

/**
 * Pull Delta: Download changes from server
 * GET /api/v1/sync/pull?since=TIMESTAMP
 */
const pullDelta = async (req, res) => {
  const { since } = req.query;
  const userId = req.user?.id || DEFAULT_TENANT_ID;
  const deviceId = req.headers['x-device-id'] || 'unknown';
  const startedAt = new Date().toISOString();

  try {
    const query = `SELECT * FROM get_delta_changes($1, $2)`;
    const result = await db.query(query, [userId, since || '1970-01-01']);
    const serverTimestamp = new Date().toISOString();
    const changes = result.rows.map((row) => buildPullChangeEnvelope(row, userId, serverTimestamp));
    const telemetry = buildSyncRunTelemetry({
      tenantId: userId,
      deviceId,
      direction: 'pull',
      startedAt,
      completedAt: serverTimestamp,
      status: 'success',
      changes,
      backlogSize: 0,
      lastSuccessfulSync: serverTimestamp
    });

    try {
      await recordSyncTelemetry(db, telemetry);
    } catch (telemetryErr) {
      console.error('[SyncController] pullDelta telemetry warning:', telemetryErr.message);
    }

    res.json({
      ...buildSyncEnvelope({
        tenantId: userId,
        deviceId,
        since: since || '1970-01-01',
        serverTimestamp,
        changes
      }),
      telemetry
    });
  } catch (err) {
    console.error('[SyncController] pullDelta Error:', err);
    res.status(500).json({ error: 'Failed to pull delta changes' });
  }
};

/**
 * Push Delta: Upload local changes to server
 * POST /api/v1/sync/push
 * Payload: { changes: [{ table_name, entity_id, action, data }] }
 */
const pushDelta = async (req, res) => {
  const { changes } = req.body;
  const userId = req.user?.id || DEFAULT_TENANT_ID;
  const deviceId = req.headers['x-device-id'] || 'unknown';
  const startedAt = new Date().toISOString();

  const validation = validateSyncChanges(changes);
  if (!validation.valid) {
    return res.status(400).json({
      error: 'Invalid changes format',
      tenant_id: userId,
      device_id: deviceId,
      validation_errors: validation.errors
    });
  }

  const results = [];
  const client = await db.pool.connect();

  try {
    await client.query('BEGIN');
    await ensureSyncDeviceRegistration(client, userId, deviceId);

    for (const change of validation.sanitizedChanges) {
      const { table_name, entity_id, action, data, sync_item_id } = change;
      await client.query(`SAVEPOINT sync_item_${results.length}`);

      const existingRecord = await fetchExistingRecord(client, table_name, entity_id, userId);
      const conflict = evaluateSyncConflict({
        tenantId: userId,
        change,
        existingRecord
      });

      if (conflict) {
        results.push(conflict);
        await client.query(`ROLLBACK TO SAVEPOINT sync_item_${results.length - 1}`);
        continue;
      }

      try {
        if (action === 'upsert') {
          const columns = Object.keys(data);
          if (columns.length === 0) {
            const upsertQuery = `
              INSERT INTO ${table_name} (user_id, id, last_synced_at)
              VALUES ($1, $2, CURRENT_TIMESTAMP)
              ON CONFLICT (id) DO UPDATE SET user_id = EXCLUDED.user_id, updated_at = CURRENT_TIMESTAMP, last_synced_at = CURRENT_TIMESTAMP
              RETURNING id, last_synced_at, updated_at, created_at
            `;
            const upsertResult = await client.query(upsertQuery, [userId, entity_id]);
            const row = upsertResult.rows[0] || {};
            results.push(buildResultEnvelope(change, {
              status: 'success',
              sync_status: 'synced',
              entity_version: row.last_synced_at || row.updated_at || row.created_at || new Date().toISOString()
            }));
          } else {
            const values = columns.map((col) => data[col]);
            values.push(userId);
            values.push(entity_id);

            const setClause = columns.map((col, idx) => `${col} = $${idx + 1}`).join(', ');
            const placeholders = columns.map((_, idx) => `$${idx + 1}`).join(', ');

            const upsertQuery = `
              INSERT INTO ${table_name} (${columns.join(', ')}, user_id, id, last_synced_at)
              VALUES (${placeholders}, $${columns.length + 1}, $${columns.length + 2}, CURRENT_TIMESTAMP)
              ON CONFLICT (id) DO UPDATE SET ${setClause}, user_id = EXCLUDED.user_id, updated_at = CURRENT_TIMESTAMP, last_synced_at = CURRENT_TIMESTAMP
              RETURNING id, last_synced_at, updated_at, created_at
            `;

            const upsertResult = await client.query(upsertQuery, values);
            const row = upsertResult.rows[0] || {};
            results.push(buildResultEnvelope(change, {
              status: 'success',
              sync_status: 'synced',
              entity_version: row.last_synced_at || row.updated_at || row.created_at || new Date().toISOString()
            }));
          }
        } else if (action === 'delete') {
          const deleteQuery = `
            UPDATE ${table_name} SET deleted_at = CURRENT_TIMESTAMP, last_synced_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND user_id = $2
            RETURNING id, deleted_at, last_synced_at
          `;
          const deleteResult = await client.query(deleteQuery, [entity_id, userId]);
          const row = deleteResult.rows[0] || {};
          results.push(buildResultEnvelope(change, {
            status: 'success',
            sync_status: 'synced',
            entity_version: row.last_synced_at || row.deleted_at || new Date().toISOString()
          }));
        } else {
          throw new Error(`Unsupported sync action "${action}"`);
        }
      } catch (itemError) {
        await client.query(`ROLLBACK TO SAVEPOINT sync_item_${results.length}`);
        results.push(buildResultEnvelope(change, {
          status: 'error',
          sync_status: 'retry_scheduled',
          retry_count: (change.retry_count || 0) + 1,
          error: itemError.message
        }));
      }
    }

    await ensureSyncDeviceRegistration(client, userId, deviceId);
    const completedAt = new Date().toISOString();
    const telemetry = buildSyncRunTelemetry({
      tenantId: userId,
      deviceId,
      direction: 'push',
      startedAt,
      completedAt,
      results,
      backlogSize: countUnresolvedResults(results),
      lastSuccessfulSync: results.every((result) => result.status === 'success') ? completedAt : null
    });
    try {
      await recordSyncTelemetry(client, telemetry);
    } catch (telemetryErr) {
      console.error('[SyncController] pushDelta telemetry warning:', telemetryErr.message);
    }
    await client.query('COMMIT');

    res.json({
      ...buildSyncEnvelope({
        tenantId: userId,
        deviceId,
        serverTimestamp: completedAt,
        results
      }),
      telemetry
    });

  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[SyncController] pushDelta Error:', err);
    res.status(500).json({ error: 'Failed to push delta changes' });
  } finally {
    client.release();
  }
};

const getHealth = async (req, res) => {
  const userId = req.user?.id || DEFAULT_TENANT_ID;
  const deviceId = req.query.device_id || null;

  try {
    const health = await loadSyncHealthSnapshot(db, {
      tenantId: userId,
      deviceId
    });
    res.json(health);
  } catch (err) {
    console.error('[SyncController] getHealth Error:', err);
    res.status(500).json({ error: 'Failed to load sync health' });
  }
};

module.exports = {
  getHealth,
  pullDelta,
  pushDelta
};
