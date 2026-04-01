const axios = require('axios');

const BASE = 'http://127.0.0.1:5056/api/v1';
const headers = { 'X-User-ID': '00000000-0000-0000-0000-000000000000' };

async function run() {
  const health = await axios.get('http://127.0.0.1:5056/api/health', { headers });
  if (!health.data?.mvp_quarterly_export_mode) {
    throw new Error('MVP quarterly mode is not enabled.');
  }

  const readiness = await axios.get(`${BASE}/inbox/readiness?as_of_date=2026-03-11&period_start=2025-10-01&period_end=2025-12-31`, { headers });
  if (typeof readiness.data?.blocking_txns_count !== 'number') {
    throw new Error('Readiness payload missing blocking_txns_count.');
  }
  if (readiness.data?.quarter_reference !== 'Q1-2026') {
    throw new Error(`Readiness quarter enforcement failed: expected Q1-2026, received ${readiness.data?.quarter_reference || 'unknown'}.`);
  }
  if (!Array.isArray(readiness.data?.issue_list) || !Array.isArray(readiness.data?.issue_summary)) {
    throw new Error('Readiness payload missing issue drill-down arrays.');
  }
  const invalidIssue = (readiness.data.issue_list || []).find((issue) => !issue.explanation || !issue.resolution_target?.route);
  if (invalidIssue) {
    throw new Error(`Readiness issue ${invalidIssue.affected_entity_id || 'unknown'} is missing explanation or navigation target.`);
  }

  const queue = await axios.get(`${BASE}/inbox/finish-now?limit=5`, { headers });
  if (!Array.isArray(queue.data)) {
    throw new Error('Finish-now queue is not an array.');
  }

  console.log('verify_mvp_quarterly_flow=PASS');
}

run().catch((err) => {
  console.error(`verify_mvp_quarterly_flow=FAIL: ${err.message}`);
  process.exit(1);
});
