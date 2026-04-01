const assert = require('assert');
const {
  AutoCommitGovernanceError,
  disableAutoCommit,
  enableAutoCommit,
  evaluateAutoCommitEligibility,
  getAutoCommitState,
  updateAutoCommitPolicy
} = require('./src/services/autoCommitGovernanceService');
const { listBusinessEvents } = require('./src/services/businessEventLogService');

class MockExecutor {
  constructor() {
    this.events = [];
    this.governance = new Map();
  }

  async query(text, params) {
    const sql = text.replace(/\s+/g, ' ').trim();

    if (sql.includes('SELECT user_id, owner_policy_allows_auto_commit')) {
      const row = this.governance.get(params[0]);
      return { rows: row ? [{ ...row }] : [] };
    }

    if (sql.includes('INSERT INTO governance_settings')) {
      const row = {
        user_id: params[0],
        owner_policy_allows_auto_commit: params[1],
        auto_commit_enabled: params[2],
        enabled_by: params[3],
        duration: params[4],
        max_allowed_duration: params[5],
        risk_acknowledged: params[6],
        confirmation_reference: params[7],
        threshold_override: params[8],
        threshold_override_limit: params[9],
        max_auto_commit_amount: params[10],
        low_confidence_threshold: params[11],
        expires_at: params[12],
        policy_metadata: JSON.parse(params[13] || '{}'),
        updated_at: new Date().toISOString(),
        updated_by: params[14]
      };
      this.governance.set(params[0], row);
      return { rows: [{ ...row }] };
    }

    if (sql.includes('INSERT INTO business_event_log')) {
      const row = {
        event_id: params[0],
        user_id: params[1],
        event_type: params[2],
        entity_id: params[3],
        entity_type: params[4],
        created_at: params[5],
        actor_id: params[6],
        source_type: params[7],
        description: params[8],
        metadata: JSON.parse(params[9] || '{}'),
        quarter_reference: params[10],
        status_from: params[11],
        status_to: params[12]
      };
      this.events.push(row);
      return { rows: [row] };
    }

    if (sql.includes('SELECT event_id,')) {
      const [userId] = params;
      const filtered = this.events
        .filter((event) => event.user_id === userId)
        .sort((left, right) => {
          const timeCompare = String(right.created_at).localeCompare(String(left.created_at));
          if (timeCompare !== 0) {
            return timeCompare;
          }
          return String(right.event_id).localeCompare(String(left.event_id));
        })
        .map((event) => ({
          event_id: event.event_id,
          event_type: event.event_type,
          entity_id: event.entity_id,
          entity_type: event.entity_type,
          timestamp: event.created_at,
          actor_id: event.actor_id,
          description: event.description,
          metadata: event.metadata,
          quarter_reference: event.quarter_reference,
          status_from: event.status_from,
          status_to: event.status_to
        }));
      return { rows: filtered };
    }

    throw new Error(`Unsupported SQL in auto-commit governance mock: ${sql}`);
  }
}

const userId = '00000000-0000-0000-0000-000000000000';

const runPolicyScenario = async () => {
  const executor = new MockExecutor();

  await updateAutoCommitPolicy(executor, {
    user_id: userId,
    actor_id: userId,
    owner_policy_allows_auto_commit: false,
    max_allowed_duration: 'weekly',
    max_auto_commit_amount: 250,
    threshold_override_limit: 1000,
    low_confidence_threshold: 0.86,
    metadata: { source: 'policy_test' }
  });

  await assert.rejects(
    () => enableAutoCommit(executor, {
      user_id: userId,
      actor_id: userId,
      duration: 'daily',
      risk_acknowledged: true,
      confirmation_reference: 'owner-blocked-ref'
    }),
    (error) => {
      assert(error instanceof AutoCommitGovernanceError);
      assert(error.message.includes('owner policy disallows'));
      return true;
    }
  );

  await updateAutoCommitPolicy(executor, {
    user_id: userId,
    actor_id: userId,
    owner_policy_allows_auto_commit: true,
    max_allowed_duration: 'weekly',
    max_auto_commit_amount: 250,
    threshold_override_limit: 1000,
    low_confidence_threshold: 0.86
  });

  await assert.rejects(
    () => enableAutoCommit(executor, {
      user_id: userId,
      actor_id: userId,
      duration: 'monthly',
      risk_acknowledged: true,
      confirmation_reference: 'duration-cap-ref'
    }),
    (error) => {
      assert(error instanceof AutoCommitGovernanceError);
      assert(error.message.includes('duration exceeds'));
      return true;
    }
  );

  const enabled = await enableAutoCommit(executor, {
    user_id: userId,
    actor_id: userId,
    duration: 'weekly',
    risk_acknowledged: true,
    confirmation_reference: 'weekly-enable-ref',
    threshold_override: true,
    now: new Date('2026-03-11T12:00:00.000Z')
  });

  assert.strictEqual(enabled.auto_commit_enabled, true);
  assert.strictEqual(enabled.duration, 'weekly');
  assert.strictEqual(enabled.max_allowed_duration, 'weekly');

  const history = await listBusinessEvents(executor, { user_id: userId, limit: 20, offset: 0 });
  assert(history.some((event) => event.event_type === 'governance_policy_changed'));
  assert(history.some((event) => event.event_type === 'auto_commit_enabled'));

  return {
    policy_denied_when_disallowed: true,
    duration_cap_enforced: true,
    enabled_duration: enabled.duration,
    logged_events: history.map((event) => event.event_type)
  };
};

const runEnforcementScenario = async () => {
  const executor = new MockExecutor();

  await updateAutoCommitPolicy(executor, {
    user_id: userId,
    actor_id: userId,
    owner_policy_allows_auto_commit: true,
    max_allowed_duration: 'monthly',
    max_auto_commit_amount: 100,
    threshold_override_limit: 500,
    low_confidence_threshold: 0.85
  });

  await enableAutoCommit(executor, {
    user_id: userId,
    actor_id: userId,
    duration: 'monthly',
    risk_acknowledged: true,
    confirmation_reference: 'override-approved',
    threshold_override: true,
    now: new Date('2026-03-11T09:00:00.000Z')
  });

  const lowConfidence = await evaluateAutoCommitEligibility(executor, {
    user_id: userId,
    entity_type: 'invoice',
    amount: 50,
    confidence_score: 0.7
  });
  assert.strictEqual(lowConfidence.eligible, false);
  assert(lowConfidence.reasons.includes('low_confidence'));

  const overrideEligible = await evaluateAutoCommitEligibility(executor, {
    user_id: userId,
    entity_type: 'invoice',
    amount: 300,
    confidence_score: 0.93
  });
  assert.strictEqual(overrideEligible.eligible, true);

  const aboveOverrideLimit = await evaluateAutoCommitEligibility(executor, {
    user_id: userId,
    entity_type: 'invoice',
    amount: 650,
    confidence_score: 0.93
  });
  assert.strictEqual(aboveOverrideLimit.eligible, false);
  assert(aboveOverrideLimit.reasons.includes('threshold_override_exceeded'));

  await disableAutoCommit(executor, {
    user_id: userId,
    actor_id: userId,
    reason: 'manual_disable'
  });

  await enableAutoCommit(executor, {
    user_id: userId,
    actor_id: userId,
    duration: 'daily',
    risk_acknowledged: true,
    confirmation_reference: 'expiry-ref',
    threshold_override: false,
    now: new Date('2026-03-11T09:00:00.000Z')
  });

  const expiredState = await getAutoCommitState(executor, {
    userId,
    now: new Date('2026-03-13T09:00:00.000Z')
  });
  assert.strictEqual(expiredState.auto_commit_enabled, false);
  assert.strictEqual(expiredState.is_expired, true);

  const history = await listBusinessEvents(executor, { user_id: userId, limit: 30, offset: 0 });
  assert(history.some((event) => event.event_type === 'auto_commit_disabled'));
  assert(history.some((event) => event.event_type === 'auto_commit_expired'));

  return {
    low_confidence_requires_confirmation: lowConfidence.reasons,
    threshold_override_allows_mid_band_amount: overrideEligible.threshold_applied,
    above_override_limit_requires_confirmation: aboveOverrideLimit.reasons,
    expiry_logged: history.filter((event) => event.event_type === 'auto_commit_expired').length
  };
};

const run = async () => {
  const mode = (process.argv[2] || 'all').toLowerCase();
  const results = {};

  if (mode === 'policy' || mode === 'all') {
    results.policy = await runPolicyScenario();
  }

  if (mode === 'enforcement' || mode === 'all') {
    results.enforcement = await runEnforcementScenario();
  }

  console.log(`verify_auto_commit_governance=${mode.toUpperCase()}=PASS`);
  console.log(JSON.stringify(results));
};

run().catch((error) => {
  console.error('verify_auto_commit_governance=FAIL');
  console.error(error);
  process.exit(1);
});
