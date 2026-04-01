const { validateAndClassifyMonetaryPayload } = require('./vatQuarterClassificationService');

const TIER_ORDER = ['tier_1', 'tier_2', 'tier_3'];
const TIER_LABELS = {
  tier_1: 'Tier 1 - Critical Monetary Integrity',
  tier_2: 'Tier 2 - Structural Completeness',
  tier_3: 'Tier 3 - Optional Quality Signals'
};
const TIER_SEVERITY = {
  tier_1: 'high',
  tier_2: 'medium',
  tier_3: 'low'
};
const TIER_DEFAULT_WEIGHT = {
  tier_1: 45,
  tier_2: 25,
  tier_3: 5
};

const ISSUE_DEFINITIONS = {
  missing_vat_rate: {
    label: 'VAT rate missing',
    tier: 'tier_1',
    severity: 'high',
    weight: 45,
    blocking: true,
    explanation: 'This monetary entry is missing a VAT rate, so the tax treatment cannot be trusted.',
    resolution_target: {
      kind: 'transaction_classification',
      route: '/api/v1/inbox/:id/classification',
      method: 'PATCH',
      label: 'Add VAT rate'
    }
  },
  invalid_vat_treatment: {
    label: 'VAT treatment invalid',
    tier: 'tier_1',
    severity: 'high',
    weight: 45,
    blocking: true,
    explanation: 'This monetary entry has an invalid VAT combination and needs correction before quarter totals can be trusted.',
    resolution_target: {
      kind: 'transaction_review',
      route: '/api/v1/inbox/:id/classification',
      method: 'PATCH',
      label: 'Correct VAT treatment'
    }
  },
  unconfirmed_monetary_entry: {
    label: 'Monetary entry unconfirmed',
    tier: 'tier_1',
    severity: 'high',
    weight: 40,
    blocking: true,
    explanation: 'This monetary entry is not confirmed yet, so it should not be treated as stable quarter evidence.',
    resolution_target: {
      kind: 'transaction_review',
      route: '/api/v1/inbox/:id/classification',
      method: 'PATCH',
      label: 'Confirm entry'
    }
  },
  unresolved_duplicate: {
    label: 'Duplicate unresolved',
    tier: 'tier_1',
    severity: 'high',
    weight: 35,
    blocking: true,
    explanation: 'This transaction is flagged as a duplicate but has not been dismissed or merged yet.',
    resolution_target: {
      kind: 'duplicate_resolution',
      route: '/api/v1/inbox/:id/duplicate-resolution',
      method: 'POST',
      label: 'Resolve duplicate'
    }
  },
  unresolved_correction_state: {
    label: 'Correction state unresolved',
    tier: 'tier_1',
    severity: 'high',
    weight: 35,
    blocking: true,
    explanation: 'This record is in a voided or superseded correction state that still impacts live quarter totals.',
    resolution_target: {
      kind: 'entity_review',
      route: '/api/v1/inbox/:id',
      method: 'PATCH',
      label: 'Review correction'
    }
  },
  post_snapshot_change_pending: {
    label: 'Post-snapshot change pending',
    tier: 'tier_1',
    severity: 'high',
    weight: 35,
    blocking: true,
    explanation: 'This quarter has changed since the latest snapshot and needs a new version to align exports with live data.',
    resolution_target: {
      kind: 'snapshot_versioning',
      route: '/api/v1/business-events/quarters/:quarter_reference/snapshot-status',
      method: 'GET',
      label: 'Review snapshot diff'
    }
  },
  missing_category: {
    label: 'Category missing',
    tier: 'tier_2',
    severity: 'medium',
    weight: 25,
    blocking: true,
    explanation: 'This transaction has no tax category yet, so it cannot be included safely in the quarter calculation.',
    resolution_target: {
      kind: 'transaction_classification',
      route: '/api/v1/inbox/:id/classification',
      method: 'PATCH',
      label: 'Classify transaction'
    }
  },
  missing_business_personal: {
    label: 'Business or personal flag missing',
    tier: 'tier_2',
    severity: 'medium',
    weight: 20,
    blocking: true,
    explanation: 'This transaction still needs a business or personal decision before readiness can be finalized.',
    resolution_target: {
      kind: 'transaction_classification',
      route: '/api/v1/inbox/:id/classification',
      method: 'PATCH',
      label: 'Set business or personal'
    }
  },
  missing_split_pct: {
    label: 'Split percentage missing',
    tier: 'tier_2',
    severity: 'medium',
    weight: 20,
    blocking: true,
    explanation: 'A split transaction is missing the business percentage, so the deductible amount is still ambiguous.',
    resolution_target: {
      kind: 'transaction_classification',
      route: '/api/v1/inbox/:id/classification',
      method: 'PATCH',
      label: 'Complete split percentage'
    }
  },
  missing_counterparty: {
    label: 'Counterparty missing',
    tier: 'tier_2',
    severity: 'medium',
    weight: 15,
    blocking: false,
    explanation: 'This record is missing a supplier or client reference, which weakens quarter completeness.',
    resolution_target: {
      kind: 'entity_review',
      route: '/api/v1/inbox/:id',
      method: 'PATCH',
      label: 'Add counterparty'
    }
  },
  missing_due_date: {
    label: 'Due date missing',
    tier: 'tier_2',
    severity: 'medium',
    weight: 10,
    blocking: false,
    explanation: 'This record is missing a due date, reducing structural completeness.',
    resolution_target: {
      kind: 'entity_review',
      route: '/api/v1/inbox/:id',
      method: 'PATCH',
      label: 'Add due date'
    }
  },
  missing_reference_number: {
    label: 'Reference number missing',
    tier: 'tier_2',
    severity: 'medium',
    weight: 10,
    blocking: false,
    explanation: 'This record is missing a reference number, making quarter audit trails weaker.',
    resolution_target: {
      kind: 'entity_review',
      route: '/api/v1/inbox/:id',
      method: 'PATCH',
      label: 'Add reference'
    }
  },
  missing_attachment: {
    label: 'Attachment missing',
    tier: 'tier_3',
    severity: 'low',
    weight: 5,
    blocking: false,
    explanation: 'An attachment is missing for this item, which reduces supporting quality but should barely affect readiness.',
    resolution_target: {
      kind: 'attachment_upload',
      route: '/api/v1/inbox/:id',
      method: 'PATCH',
      label: 'Attach evidence'
    }
  },
  weak_description: {
    label: 'Description weak',
    tier: 'tier_3',
    severity: 'low',
    weight: 5,
    blocking: false,
    explanation: 'This item description is weak, so the narrative context for the quarter is less clear.',
    resolution_target: {
      kind: 'entity_review',
      route: '/api/v1/inbox/:id',
      method: 'PATCH',
      label: 'Improve description'
    }
  },
  missing_notes: {
    label: 'Notes missing',
    tier: 'tier_3',
    severity: 'low',
    weight: 3,
    blocking: false,
    explanation: 'This item is missing supporting notes, which is a low-priority quality gap.',
    resolution_target: {
      kind: 'entity_review',
      route: '/api/v1/inbox/:id',
      method: 'PATCH',
      label: 'Add notes'
    }
  }
};

const ISSUE_ORDER = Object.keys(ISSUE_DEFINITIONS);

const hasValue = (value) => value !== undefined && value !== null && value !== '';

const normalizeText = (value) => String(value || '').trim();

const toIsoDate = (value) => {
  if (!value) return null;
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString().slice(0, 10);
};

const deriveQuarterBounds = (input) => {
  const isoDate = toIsoDate(input) || new Date().toISOString().slice(0, 10);
  const [year, month] = isoDate.split('-').map(Number);
  const quarter = Math.floor((month - 1) / 3) + 1;
  const monthStart = (quarter - 1) * 3;
  const periodStart = new Date(Date.UTC(year, monthStart, 1)).toISOString().slice(0, 10);
  const periodEnd = new Date(Date.UTC(year, monthStart + 3, 0)).toISOString().slice(0, 10);
  return {
    as_of_date: isoDate,
    quarter_reference: `Q${quarter}-${year}`,
    period_start: periodStart,
    period_end: periodEnd
  };
};

const inferEntityType = (transaction = {}) => (
  transaction.entity_type
  || transaction.type
  || transaction.item_type
  || transaction.record_type
  || null
);

const normalizeSeverityRank = (severity) => ({ high: 3, medium: 2, low: 1 }[severity] || 0);

const buildResolutionTarget = (detail, transaction, activeQuarter) => {
  const route = detail.resolution_target.route
    .replace(':id', String(transaction.id || transaction.txn_id || ''))
    .replace(':quarter_reference', String(activeQuarter.quarter_reference || ''));

  return {
    ...detail.resolution_target,
    entity_id: transaction.id || transaction.txn_id || null,
    route,
    workflow: '/inbox/finish-now'
  };
};

const buildIssueRecord = (transaction = {}, issueType, activeQuarter) => {
  const detail = ISSUE_DEFINITIONS[issueType];
  const explanation = `${detail.explanation}${transaction.merchant ? ` Merchant: ${transaction.merchant}.` : ''}`.trim();

  return {
    issue_type: issueType,
    label: detail.label,
    tier: detail.tier,
    tier_label: TIER_LABELS[detail.tier],
    affected_entity_id: transaction.id || transaction.txn_id || null,
    affected_entity_type: inferEntityType(transaction) || 'bank_transaction',
    severity: detail.severity,
    weight: detail.weight,
    blocking: detail.blocking,
    resolution_target: buildResolutionTarget(detail, transaction, activeQuarter),
    explanation,
    txn_date: transaction.txn_date || transaction.date || null,
    merchant: transaction.merchant || transaction.client_name || null,
    amount: transaction.amount ?? transaction.gross_amount ?? null,
    direction: transaction.direction || null
  };
};

const validateVatIssue = (transaction = {}) => {
  const entityType = inferEntityType(transaction);
  if (!entityType) {
    return null;
  }

  if (!hasValue(transaction.net_amount) && !hasValue(transaction.gross_amount) && !hasValue(transaction.amount)) {
    return null;
  }

  if (!hasValue(transaction.vat_rate)) {
    return 'missing_vat_rate';
  }

  try {
    validateAndClassifyMonetaryPayload({
      entityType,
      transactionDate: transaction.txn_date || transaction.date || transaction.transaction_date || transaction.created_at,
      quarterReference: transaction.quarter_reference || transaction.quarter_ref || null,
      amount: transaction.amount,
      net_amount: transaction.net_amount,
      vat_amount: transaction.vat_amount,
      gross_amount: transaction.gross_amount,
      vat_rate: transaction.vat_rate,
      vat_type: transaction.vat_type
    });
  } catch (error) {
    return 'invalid_vat_treatment';
  }

  return null;
};

const deriveIssueTypes = (transaction = {}) => {
  const issues = [];
  const vatIssue = validateVatIssue(transaction);
  if (vatIssue) issues.push(vatIssue);

  if (hasValue(transaction.status) && !['confirmed', 'reconciled', 'paid', 'sent'].includes(String(transaction.status).toLowerCase())) {
    issues.push('unconfirmed_monetary_entry');
  }
  if (transaction.duplicate_flag === true && !transaction.duplicate_resolution) {
    issues.push('unresolved_duplicate');
  }
  if (['voided', 'superseded'].includes(String(transaction.status || '').toLowerCase()) || transaction.correction_pending === true) {
    issues.push('unresolved_correction_state');
  }
  if (transaction.post_snapshot_change_pending === true || transaction.changed_since_snapshot === true) {
    issues.push('post_snapshot_change_pending');
  }

  if (!transaction.category_code) {
    issues.push('missing_category');
  }
  if (!transaction.business_personal) {
    issues.push('missing_business_personal');
  }
  if (transaction.is_split === true && !hasValue(transaction.split_business_pct)) {
    issues.push('missing_split_pct');
  }
  if (transaction.counterparty_required === true && !hasValue(transaction.counterparty_reference || transaction.client_id || transaction.supplier_id)) {
    issues.push('missing_counterparty');
  }
  if (transaction.due_date_required === true && !hasValue(transaction.due_date)) {
    issues.push('missing_due_date');
  }
  if (transaction.reference_required === true && !hasValue(transaction.reference_number || transaction.invoice_number || transaction.quote_number)) {
    issues.push('missing_reference_number');
  }

  if ((transaction.attachment_expected === true || transaction.attachment_required === true) && !hasValue(transaction.attachment_reference)) {
    issues.push('missing_attachment');
  }
  if (transaction.description_quality_check !== false) {
    const description = normalizeText(transaction.description || transaction.raw_note || transaction.extracted_text);
    if (description && description.length < 8) {
      issues.push('weak_description');
    }
  }
  if (transaction.notes_expected === true && !normalizeText(transaction.notes)) {
    issues.push('missing_notes');
  }

  return ISSUE_ORDER.filter((issueType) => issues.includes(issueType));
};

const calculateReadinessPct = (transactions, issueList) => {
  if (transactions.length === 0) {
    return 100;
  }

  const totalPossibleWeight = transactions.length * 100;
  const penaltyWeight = issueList.reduce((total, issue) => total + Number(issue.weight || TIER_DEFAULT_WEIGHT[issue.tier] || 0), 0);
  const weightedScore = Math.max(0, 100 - Math.round((penaltyWeight / totalPossibleWeight) * 100));
  return Math.max(0, Math.min(100, weightedScore));
};

const compareIssues = (left, right) => {
  const tierDelta = TIER_ORDER.indexOf(left.tier) - TIER_ORDER.indexOf(right.tier);
  if (tierDelta !== 0) return tierDelta;
  if (right.weight !== left.weight) return right.weight - left.weight;
  if (left.txn_date !== right.txn_date) return String(left.txn_date || '').localeCompare(String(right.txn_date || ''));
  if (left.affected_entity_id !== right.affected_entity_id) {
    return String(left.affected_entity_id || '').localeCompare(String(right.affected_entity_id || ''));
  }
  return String(left.issue_type || '').localeCompare(String(right.issue_type || ''));
};

const buildReadinessReport = ({ periodStart, periodEnd, asOfDate = null, transactions = [] }) => {
  const activeQuarter = deriveQuarterBounds(asOfDate || periodStart || periodEnd);
  const scopedTransactions = transactions.filter((transaction) => {
    const txnDate = toIsoDate(transaction.txn_date || transaction.date || transaction.transaction_date);
    return txnDate && txnDate >= activeQuarter.period_start && txnDate <= activeQuarter.period_end;
  });

  const issuesByTransaction = scopedTransactions.map((transaction) => {
    const issueTypes = deriveIssueTypes(transaction);
    const issueRecords = issueTypes.map((issueType) => buildIssueRecord(transaction, issueType, activeQuarter));
    return {
      transaction,
      issueTypes,
      issueRecords
    };
  });

  const issueList = issuesByTransaction
    .flatMap((entry) => entry.issueRecords)
    .sort(compareIssues);

  const blockingIssues = issueList.filter((issue) => issue.blocking);
  const blockingTransactions = issuesByTransaction
    .filter((entry) => entry.issueRecords.some((issue) => issue.blocking))
    .map((entry) => {
      const primaryIssue = entry.issueRecords
        .filter((issue) => issue.blocking)
        .sort(compareIssues)[0];
      return {
        id: entry.transaction.id || entry.transaction.txn_id || null,
        txn_date: entry.transaction.txn_date || entry.transaction.date || null,
        merchant: entry.transaction.merchant || entry.transaction.client_name || null,
        amount: entry.transaction.amount ?? entry.transaction.gross_amount ?? null,
        direction: entry.transaction.direction || null,
        blocker_reason: primaryIssue.issue_type,
        tier: primaryIssue.tier,
        severity: primaryIssue.severity,
        weight: primaryIssue.weight,
        explanation: primaryIssue.explanation,
        resolution_target: primaryIssue.resolution_target
      };
    })
    .sort((left, right) => compareIssues({
      issue_type: left.blocker_reason,
      tier: left.tier,
      weight: left.weight,
      txn_date: left.txn_date,
      affected_entity_id: left.id
    }, {
      issue_type: right.blocker_reason,
      tier: right.tier,
      weight: right.weight,
      txn_date: right.txn_date,
      affected_entity_id: right.id
    }));

  const blockersByReason = ISSUE_ORDER
    .map((issueType) => {
      const count = blockingIssues.filter((issue) => issue.issue_type === issueType).length;
      if (count === 0) {
        return null;
      }
      return {
        reason: issueType,
        label: ISSUE_DEFINITIONS[issueType].label,
        tier: ISSUE_DEFINITIONS[issueType].tier,
        severity: ISSUE_DEFINITIONS[issueType].severity,
        count
      };
    })
    .filter(Boolean);

  const issueSummary = ISSUE_ORDER
    .map((issueType) => {
      const matchingIssues = issueList.filter((issue) => issue.issue_type === issueType);
      if (matchingIssues.length === 0) {
        return null;
      }
      const detail = ISSUE_DEFINITIONS[issueType];
      return {
        issue_type: issueType,
        label: detail.label,
        tier: detail.tier,
        tier_label: TIER_LABELS[detail.tier],
        severity: detail.severity,
        weight: detail.weight,
        blocking: detail.blocking,
        count: matchingIssues.length,
        percentage_of_issues: issueList.length === 0 ? 0 : Math.round((matchingIssues.length / issueList.length) * 100),
        percentage_of_period_transactions: scopedTransactions.length === 0 ? 0 : Math.round((matchingIssues.length / scopedTransactions.length) * 100),
        total_weight: matchingIssues.reduce((total, issue) => total + Number(issue.weight || 0), 0),
        explanation: detail.explanation
      };
    })
    .filter(Boolean);

  const readinessPct = calculateReadinessPct(scopedTransactions, issueList);
  const totalIssues = issueList.length;
  const overallSeverity = issueList.length === 0
    ? 'none'
    : issueList
      .slice()
      .sort((left, right) => normalizeSeverityRank(right.severity) - normalizeSeverityRank(left.severity))[0]
      .severity;

  const explanationLines = totalIssues === 0
    ? [
        `Readiness is 100% for ${activeQuarter.period_start} to ${activeQuarter.period_end}.`,
        'No weighted readiness issues were found.',
        'Quarterly export can proceed without live-quarter penalties.'
      ]
    : [
        `Readiness is ${readinessPct}% for ${activeQuarter.period_start} to ${activeQuarter.period_end}.`,
        `${blockingTransactions.length} transactions have blocking issues and ${totalIssues} weighted issues are open.`,
        `Weighted reasons: ${issueSummary.map((issue) => `${issue.label} (${issue.count}, ${issue.tier_label})`).join('; ')}.`
      ];

  return {
    as_of_date: activeQuarter.as_of_date,
    quarter_reference: activeQuarter.quarter_reference,
    period_start: activeQuarter.period_start,
    period_end: activeQuarter.period_end,
    active_period_enforced: true,
    requested_period_start: periodStart || null,
    requested_period_end: periodEnd || null,
    total_txns_in_period: scopedTransactions.length,
    blocking_txns_count: blockingTransactions.length,
    issue_count: totalIssues,
    readiness_pct: readinessPct,
    score: readinessPct,
    severity: overallSeverity,
    can_export: blockingTransactions.length === 0,
    blockers_by_reason: blockersByReason,
    blocking_transactions: blockingTransactions,
    issue_summary: issueSummary,
    issue_list: issueList,
    explanation_lines: explanationLines,
    explanation_summary: explanationLines.join(' ')
  };
};

const reportsMatch = (left, right) => JSON.stringify(left) === JSON.stringify(right);

module.exports = {
  BLOCKER_REASON_DETAILS: ISSUE_DEFINITIONS,
  BLOCKER_REASON_LABELS: Object.fromEntries(Object.entries(ISSUE_DEFINITIONS).map(([key, value]) => [key, value.label])),
  BLOCKER_REASON_ORDER: ISSUE_ORDER,
  ISSUE_DEFINITIONS,
  TIER_LABELS,
  TIER_ORDER,
  buildIssueRecord,
  buildReadinessReport,
  deriveIssueTypes,
  deriveQuarterBounds,
  reportsMatch
};
