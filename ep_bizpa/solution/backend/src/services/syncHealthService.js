const SYNC_TELEMETRY_RELATION_MISSING = '42P01';
const MAX_ISSUE_SAMPLES = 5;

const roundRate = (value) => Number(value.toFixed(4));

const summarizeResultIssues = (results = []) => {
  const conflicts = [];
  const errors = [];

  results.forEach((result) => {
    if (result.status === 'conflict') {
      conflicts.push({
        sync_item_id: result.sync_item_id,
        entity_id: result.entity_id,
        table_name: result.table_name,
        conflict_code: result.conflict_code || null,
        conflict_type: result.conflict_type || null,
        resolution_strategy: result.resolution_strategy || null
      });
    }

    if (result.status === 'error') {
      errors.push({
        sync_item_id: result.sync_item_id,
        entity_id: result.entity_id,
        table_name: result.table_name,
        error: result.error || 'Unknown sync error'
      });
    }
  });

  return {
    conflicts: conflicts.slice(0, MAX_ISSUE_SAMPLES),
    errors: errors.slice(0, MAX_ISSUE_SAMPLES)
  };
};

const buildSyncRunTelemetry = ({
  tenantId,
  deviceId,
  direction,
  startedAt,
  completedAt = new Date().toISOString(),
  status,
  results = [],
  changes = [],
  backlogSize = 0,
  lastSuccessfulSync = null
}) => {
  const totalChanges = results.length > 0 ? results.length : changes.length;
  const successCount = results.filter((entry) => entry.status === 'success').length;
  const conflictCount = results.filter((entry) => entry.status === 'conflict').length;
  const errorCount = results.filter((entry) => entry.status === 'error').length;
  const telemetryStatus = status || (errorCount > 0 ? 'error' : (conflictCount > 0 ? 'partial' : 'success'));
  const errorRate = totalChanges === 0 ? 0 : roundRate(errorCount / totalChanges);
  const samples = summarizeResultIssues(results);

  return {
    tenant_scope: tenantId,
    device_id: deviceId,
    direction,
    started_at: startedAt,
    completed_at: completedAt,
    status: telemetryStatus,
    total_changes: totalChanges,
    success_count: successCount,
    conflict_count: conflictCount,
    error_count: errorCount,
    backlog_size: backlogSize,
    error_rate: errorRate,
    last_successful_sync: telemetryStatus === 'success' ? completedAt : lastSuccessfulSync,
    conflict_samples: samples.conflicts,
    error_samples: samples.errors
  };
};

const buildSyncHealthSnapshot = ({
  tenantId,
  deviceId = null,
  recentRuns = [],
  latestBacklogSize = 0,
  lastSuccessfulSync = null
}) => {
  const relevantRuns = recentRuns.filter((run) => !deviceId || run.device_id === deviceId);
  const totalChanges = relevantRuns.reduce((sum, run) => sum + Number(run.total_changes || 0), 0);
  const totalErrors = relevantRuns.reduce((sum, run) => sum + Number(run.error_count || 0), 0);
  const totalConflicts = relevantRuns.reduce((sum, run) => sum + Number(run.conflict_count || 0), 0);
  const aggregateErrorRate = totalChanges === 0 ? 0 : roundRate(totalErrors / totalChanges);
  const latestRun = relevantRuns[0] || null;
  const latestSuccessfulRun = relevantRuns.find((run) => run.status === 'success' && run.last_successful_sync) || null;

  return {
    tenant_scope: tenantId,
    device_id: deviceId,
    backlog_size: Number(latestBacklogSize || 0),
    error_rate: aggregateErrorRate,
    conflict_rate: totalChanges === 0 ? 0 : roundRate(totalConflicts / totalChanges),
    last_successful_sync: lastSuccessfulSync || latestSuccessfulRun?.last_successful_sync || null,
    last_run_at: latestRun?.completed_at || null,
    recent_run_count: relevantRuns.length,
    recent_conflicts: relevantRuns.flatMap((run) => run.conflict_samples || []).slice(0, MAX_ISSUE_SAMPLES),
    recent_errors: relevantRuns.flatMap((run) => run.error_samples || []).slice(0, MAX_ISSUE_SAMPLES)
  };
};

const recordSyncTelemetry = async (client, telemetry) => {
  try {
    await client.query(
      `
      INSERT INTO sync_run_telemetry (
        user_id,
        device_id,
        direction,
        status,
        total_changes,
        success_count,
        conflict_count,
        error_count,
        backlog_size,
        error_rate,
        last_successful_sync,
        conflict_samples,
        error_samples,
        started_at,
        completed_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13::jsonb, $14, $15)
      `,
      [
        telemetry.tenant_scope,
        telemetry.device_id,
        telemetry.direction,
        telemetry.status,
        telemetry.total_changes,
        telemetry.success_count,
        telemetry.conflict_count,
        telemetry.error_count,
        telemetry.backlog_size,
        telemetry.error_rate,
        telemetry.last_successful_sync,
        JSON.stringify(telemetry.conflict_samples || []),
        JSON.stringify(telemetry.error_samples || []),
        telemetry.started_at,
        telemetry.completed_at
      ]
    );
  } catch (err) {
    if (err.code !== SYNC_TELEMETRY_RELATION_MISSING) {
      throw err;
    }
  }
};

const loadSyncHealthSnapshot = async (queryable, { tenantId, deviceId = null, limit = 10 }) => {
  let recentRuns = [];
  let latestBacklogSize = 0;
  let lastSuccessfulSync = null;

  try {
    const params = [tenantId];
    let deviceClause = '';
    if (deviceId) {
      params.push(deviceId);
      deviceClause = ` AND device_id = $${params.length}`;
    }

    params.push(limit);
    const recentRunsResult = await queryable.query(
      `
      SELECT
        user_id AS tenant_scope,
        device_id,
        direction,
        status,
        total_changes,
        success_count,
        conflict_count,
        error_count,
        backlog_size,
        error_rate,
        last_successful_sync,
        conflict_samples,
        error_samples,
        completed_at
      FROM sync_run_telemetry
      WHERE user_id = $1${deviceClause}
      ORDER BY completed_at DESC
      LIMIT $${params.length}
      `,
      params
    );

    recentRuns = recentRunsResult.rows.map((row) => ({
      ...row,
      conflict_samples: Array.isArray(row.conflict_samples) ? row.conflict_samples : [],
      error_samples: Array.isArray(row.error_samples) ? row.error_samples : []
    }));
  } catch (err) {
    if (err.code !== SYNC_TELEMETRY_RELATION_MISSING) {
      throw err;
    }
  }

  if (recentRuns.length > 0) {
    latestBacklogSize = Number(recentRuns[0].backlog_size || 0);
    lastSuccessfulSync =
      recentRuns.find((run) => run.status === 'success' && run.last_successful_sync)?.last_successful_sync ||
      null;
  }

  if (!lastSuccessfulSync) {
    try {
      const params = [tenantId];
      let deviceClause = '';
      if (deviceId) {
        params.push(deviceId);
        deviceClause = ` AND device_id = $2`;
      }

      const deviceResult = await queryable.query(
        `
        SELECT last_sync_at
        FROM sync_devices
        WHERE user_id = $1${deviceClause}
        ORDER BY last_sync_at DESC NULLS LAST
        LIMIT 1
        `,
        params
      );
      lastSuccessfulSync = deviceResult.rows[0]?.last_sync_at || null;
    } catch (err) {
      if (err.code !== SYNC_TELEMETRY_RELATION_MISSING) {
        throw err;
      }
    }
  }

  return buildSyncHealthSnapshot({
    tenantId,
    deviceId,
    recentRuns,
    latestBacklogSize,
    lastSuccessfulSync
  });
};

module.exports = {
  buildSyncHealthSnapshot,
  buildSyncRunTelemetry,
  loadSyncHealthSnapshot,
  recordSyncTelemetry
};
