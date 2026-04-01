const assert = require('assert');
const { buildReadinessReport } = require('./src/services/readinessService');

const activeQuarterTransactions = [
  {
    id: 'txn-001',
    txn_date: '2026-03-03',
    merchant: 'Fuel Stop',
    amount: 42.5,
    direction: 'out',
    category_code: null,
    business_personal: null,
    is_split: false,
    split_business_pct: null,
    duplicate_flag: false,
    duplicate_resolution: null
  },
  {
    id: 'txn-002',
    txn_date: '2026-03-05',
    merchant: 'Office Depot',
    amount: 18,
    direction: 'out',
    category_code: 'OFFICE',
    business_personal: 'BUSINESS',
    is_split: false,
    split_business_pct: null,
    duplicate_flag: false,
    duplicate_resolution: null
  },
  {
    id: 'txn-003',
    txn_date: '2026-02-20',
    merchant: 'Duplicate Supplier',
    amount: 120,
    direction: 'out',
    category_code: 'SUPPLIES',
    business_personal: 'BUSINESS',
    is_split: false,
    split_business_pct: null,
    duplicate_flag: true,
    duplicate_resolution: null
  }
];

const historicalSnapshotCandidate = {
  id: 'txn-old',
  txn_date: '2025-12-15',
  merchant: 'Old Expense',
  amount: 75,
  direction: 'out',
  category_code: null,
  business_personal: null,
  is_split: false,
  split_business_pct: null,
  duplicate_flag: false,
  duplicate_resolution: null
};

const run = () => {
  const baseReport = buildReadinessReport({
    asOfDate: '2026-03-11',
    transactions: [...activeQuarterTransactions, historicalSnapshotCandidate]
  });

  assert.equal(baseReport.quarter_reference, 'Q1-2026');
  assert.equal(baseReport.period_start, '2026-01-01');
  assert.equal(baseReport.period_end, '2026-03-31');
  assert.equal(baseReport.total_txns_in_period, 3);
  assert.equal(baseReport.blocking_txns_count, 2);
  assert.equal(baseReport.issue_list.length, 3);
  assert.equal(baseReport.issue_count, 3);
  assert.equal(baseReport.score, baseReport.readiness_pct);
  assert(baseReport.issue_list.every((issue) => issue.tier));
  assert(baseReport.issue_list.every((issue) => issue.explanation && issue.resolution_target && issue.resolution_target.route));
  assert(baseReport.issue_list.every((issue) => !issue.affected_entity_id.includes('old')));
  assert(baseReport.issue_summary.some((issue) => issue.issue_type === 'missing_category'));
  assert(baseReport.issue_summary.some((issue) => issue.issue_type === 'missing_business_personal'));
  assert(baseReport.issue_summary.some((issue) => issue.issue_type === 'unresolved_duplicate'));
  assert(baseReport.issue_summary.some((issue) => issue.tier === 'tier_1'));
  assert(baseReport.issue_summary.some((issue) => issue.tier === 'tier_2'));

  const tier1Report = buildReadinessReport({
    asOfDate: '2026-03-11',
    transactions: [{
      id: 'tier1',
      txn_date: '2026-03-10',
      merchant: 'Invoice Alpha',
      amount: 120,
      net_amount: 100,
      vat_amount: 20,
      gross_amount: 120,
      vat_rate: 20,
      vat_type: 'output',
      entity_type: 'invoice',
      category_code: 'SALES',
      business_personal: 'BUSINESS',
      is_split: false,
      split_business_pct: null,
      duplicate_flag: true,
      duplicate_resolution: null
    }]
  });
  const tier2Report = buildReadinessReport({
    asOfDate: '2026-03-11',
    transactions: [{
      id: 'tier2',
      txn_date: '2026-03-10',
      merchant: 'Fuel Stop',
      amount: 50,
      category_code: null,
      business_personal: 'BUSINESS',
      is_split: false,
      split_business_pct: null,
      duplicate_flag: false,
      duplicate_resolution: null
    }]
  });
  const tier3Report = buildReadinessReport({
    asOfDate: '2026-03-11',
    transactions: [{
      id: 'tier3',
      txn_date: '2026-03-10',
      merchant: 'Client Note',
      amount: 50,
      category_code: 'GENERAL',
      business_personal: 'BUSINESS',
      is_split: false,
      split_business_pct: null,
      duplicate_flag: false,
      duplicate_resolution: null,
      attachment_expected: true,
      attachment_reference: null
    }]
  });
  assert(tier1Report.readiness_pct < tier2Report.readiness_pct);
  assert(tier2Report.readiness_pct < tier3Report.readiness_pct);

  const resolvedTransactions = [
    {
      ...activeQuarterTransactions[0],
      category_code: 'FUEL',
      business_personal: 'BUSINESS'
    },
    {
      ...activeQuarterTransactions[2],
      duplicate_resolution: 'dismiss'
    },
    activeQuarterTransactions[1]
  ];

  const resolvedReport = buildReadinessReport({
    asOfDate: '2026-03-11',
    transactions: resolvedTransactions
  });

  assert.equal(resolvedReport.blocking_txns_count, 0);
  assert.equal(resolvedReport.readiness_pct, 100);
  assert.equal(resolvedReport.issue_list.length, 0);

  console.log('verify_readiness_drilldown=PASS');
};

run();
