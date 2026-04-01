const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { validateArchiveRequest, validateItemUpdate } = require('./src/services/monetaryIntegrityService');
const { reconstructAuditTrace } = require('./src/services/auditTraceService');
const { sortNotifications } = require('./src/services/notificationService');
const { buildQuarterlyPackArtifacts, buildSnapshotDiff } = require('./src/services/quarterlyExportService');
const { buildReadinessReport, reportsMatch } = require('./src/services/readinessService');
const { validateSyncChanges } = require('./src/services/syncValidationService');

const loadFixture = (name) => JSON.parse(
  fs.readFileSync(path.join(__dirname, 'regression_fixtures', name), 'utf8')
);

const verifyReadinessAndExport = () => {
  const fixture = loadFixture('readiness_export_fixture.json');

  const readinessReport = buildReadinessReport({
    periodStart: fixture.readiness.period_start,
    periodEnd: fixture.readiness.period_end,
    transactions: fixture.readiness.transactions
  });
  assert(
    reportsMatch(readinessReport, fixture.readiness.expected_readiness_report),
    `Readiness report drift detected.\nExpected: ${JSON.stringify(fixture.readiness.expected_readiness_report, null, 2)}\nActual: ${JSON.stringify(readinessReport, null, 2)}`
  );

  const snapshotDiff = buildSnapshotDiff(
    fixture.snapshot_diff.previous_snapshot_transactions,
    fixture.snapshot_diff.next_snapshot_transactions
  );
  assert.deepStrictEqual(snapshotDiff, fixture.snapshot_diff.expected_diff);

  const exportArtifacts = buildQuarterlyPackArtifacts({
    periodStart: fixture.export.period_start,
    periodEnd: fixture.export.period_end,
    transactions: fixture.export.transactions,
    evidenceRows: fixture.export.evidence_rows,
    summaryRows: fixture.export.summary_rows,
    previousSnapshotRows: fixture.snapshot_diff.previous_snapshot_transactions,
    nextSnapshotRows: fixture.snapshot_diff.next_snapshot_transactions
  });

  const expectedChecksum = fixture.export.expected_export_checksum;
  if (expectedChecksum === 'PENDING') {
    throw new Error(`Export fixture checksum is still PENDING. Computed checksum: ${exportArtifacts.manifest.pack_checksum}`);
  }
  assert.strictEqual(exportArtifacts.manifest.pack_checksum, expectedChecksum);

  return {
    readiness_pct: readinessReport.readiness_pct,
    export_checksum: exportArtifacts.manifest.pack_checksum
  };
};

const verifyFailureModes = () => {
  const fixture = loadFixture('failure_modes_fixture.json');

  const mutationCheck = validateItemUpdate(
    fixture.monetary_integrity.committed_item,
    fixture.monetary_integrity.mutation_attempt
  );
  assert.strictEqual(mutationCheck.valid, false);
  assert(mutationCheck.errors.some((entry) => entry.includes('Committed monetary item cannot change immutable fields in place')));

  const archiveCheck = validateArchiveRequest(fixture.monetary_integrity.committed_item);
  assert.strictEqual(archiveCheck.valid, false);
  assert(archiveCheck.errors.some((entry) => entry.includes('cannot be deleted or archived')));

  const syncValidation = validateSyncChanges(fixture.sync_corruption.changes);
  assert.strictEqual(syncValidation.valid, false);
  assert(syncValidation.errors.some((entry) => entry.includes('server-managed fields')));
  assert(syncValidation.errors.some((entry) => entry.includes('unsupported table')));
  assert(syncValidation.errors.some((entry) => entry.includes('duplicates entity')));

  const sortedNotificationIds = sortNotifications(fixture.notifications.items).map((entry) => entry.id);
  assert.deepStrictEqual(sortedNotificationIds, fixture.notifications.expected_order);

  const auditTrace = reconstructAuditTrace({
    events: fixture.audit_trace.events,
    snapshots: fixture.audit_trace.snapshots
  });
  assert.deepStrictEqual(
    {
      immutable_history: auditTrace.immutable_history,
      total_events: auditTrace.total_events,
      snapshot_count: auditTrace.snapshot_count,
      event_types: auditTrace.event_types,
      quarter_references: auditTrace.quarter_references,
      unique_entities: auditTrace.unique_entities
    },
    fixture.audit_trace.expected_audit_trace
  );

  return {
    sync_errors: syncValidation.errors.length,
    audit_timeline_entries: auditTrace.timeline.length
  };
};

const main = () => {
  const mode = process.argv[2] || 'all';
  const outcomes = [];

  if (!['all', 'failure-modes', 'readiness-export'].includes(mode)) {
    throw new Error(`Unknown mode "${mode}". Use readiness-export, failure-modes, or all.`);
  }

  if (mode === 'readiness-export' || mode === 'all') {
    outcomes.push({ suite: 'readiness-export', ...verifyReadinessAndExport() });
  }

  if (mode === 'failure-modes' || mode === 'all') {
    outcomes.push({ suite: 'failure-modes', ...verifyFailureModes() });
  }

  console.log('verify_regression_harness=PASS');
  outcomes.forEach((outcome) => console.log(JSON.stringify(outcome)));
};

try {
  main();
} catch (error) {
  console.error('verify_regression_harness=FAIL');
  console.error(error.message);
  process.exit(1);
}
