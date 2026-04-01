const crypto = require("crypto");

function cloneValue(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

class MemoryTransactionImportStore {
  constructor() {
    this.bankTransactions = new Map();
    this.transactionsByRef = new Map();
    this.transactionsBySourceHash = new Map();
    this.importRuns = new Map();
    this.importCheckpoints = new Map();
    this.classifications = new Map(); // classification_id -> record
    this.classificationsByTxnId = new Map(); // txn_id -> classification_id
    this.auditEntries = []; // list of audit records
    // V20260321_1200: Added support for quarters and metrics
    this.quarters = new Map();
    this.quarterMetrics = new Map();
    // V20260322_1730: Added support for merchant rules
    this.rules = new Map();
    // V20260322_1740: Added support for evidence and links
    this.evidence = new Map();
    this.evidenceLinks = new Map();
    // V20260322_1810: Added support for export metadata
    this.exports = new Map();
  }

  async startImportRun(importRun) {
    this.importRuns.set(importRun.import_run_id, cloneValue(importRun));        
  }

  async completeImportRun(importRunId, summary) {
    const record = this.importRuns.get(importRunId);
    this.importRuns.set(importRunId, {
      ...record,
      ...cloneValue(summary)
    });
  }

  async failImportRun(importRunId, summary) {
    const record = this.importRuns.get(importRunId);
    this.importRuns.set(importRunId, {
      ...record,
      ...cloneValue(summary)
    });
  }

  async getImportCheckpoint(bankAccountId) {
    return cloneValue(this.importCheckpoints.get(bankAccountId) || null);       
  }

  async updateImportCheckpoint(bankAccountId, checkpoint) {
    const previous = this.importCheckpoints.get(bankAccountId) || {};
    const lastSuccessfulCursor = checkpoint.last_status === "completed"
      ? checkpoint.last_successful_cursor
      : previous.last_successful_cursor ?? null;
    const lastSuccessfulImportAt = checkpoint.last_status === "completed"       
      ? checkpoint.last_successful_import_at
      : previous.last_successful_import_at ?? null;
    const merged = {
      ...previous,
      ...cloneValue(checkpoint),
      last_successful_cursor: lastSuccessfulCursor,
      last_successful_import_at: lastSuccessfulImportAt
    };
    this.importCheckpoints.set(bankAccountId, merged);
  }

  async runInTransaction(callback) {
    const snapshot = {
      bankTransactions: cloneValue([...this.bankTransactions.entries()]),       
      transactionsByRef: cloneValue([...this.transactionsByRef.entries()]),     
      transactionsBySourceHash: cloneValue([...this.transactionsBySourceHash.entries()]),
      importCheckpoints: cloneValue([...this.importCheckpoints.entries()]),     
      classifications: cloneValue([...this.classifications.entries()]),
      classificationsByTxnId: cloneValue([...this.classificationsByTxnId.entries()]),
      auditEntries: cloneValue(this.auditEntries),
      quarters: cloneValue([...this.quarters.entries()]),
      quarterMetrics: cloneValue([...this.quarterMetrics.entries()]),
      rules: cloneValue([...this.rules.entries()]),
      evidence: cloneValue([...this.evidence.entries()]),
      evidenceLinks: cloneValue([...this.evidenceLinks.entries()]),
      exports: cloneValue([...this.exports.entries()])
    };

    try {
      return await callback(this);
    } catch (error) {
      this.bankTransactions = new Map(snapshot.bankTransactions);
      this.transactionsByRef = new Map(snapshot.transactionsByRef);
      this.transactionsBySourceHash = new Map(snapshot.transactionsBySourceHash);
      this.importCheckpoints = new Map(snapshot.importCheckpoints);
      this.classifications = new Map(snapshot.classifications);
      this.classificationsByTxnId = new Map(snapshot.classificationsByTxnId);   
      this.auditEntries = snapshot.auditEntries;
      this.quarters = new Map(snapshot.quarters);
      this.quarterMetrics = new Map(snapshot.quarterMetrics);
      this.rules = new Map(snapshot.rules);
      this.evidence = new Map(snapshot.evidence);
      this.evidenceLinks = new Map(snapshot.evidenceLinks);
      this.exports = new Map(snapshot.exports);
      throw error;
    }
  }

  async upsertBankTransaction(transaction) {
    const refKey = `${transaction.bank_account_id}::${transaction.bank_txn_ref}`;
    const hashKey = `${transaction.bank_account_id}::${transaction.source_hash}`;
    const existingTxnId = this.transactionsByRef.get(refKey) || this.transactionsBySourceHash.get(hashKey);

    if (existingTxnId) {
      return {
        status: "duplicate",
        record: cloneValue(this.bankTransactions.get(existingTxnId))
      };
    }

    const record = {
      ...cloneValue(transaction),
      txn_id: transaction.txn_id || crypto.randomUUID()
    };
    this.bankTransactions.set(record.txn_id, record);
    this.transactionsByRef.set(refKey, record.txn_id);
    this.transactionsBySourceHash.set(hashKey, record.txn_id);

    return {
      status: "inserted",
      record: cloneValue(record)
    };
  }

  async upsertTransactionClassification(classification) {
    const record = cloneValue(classification);
    if (!record.classification_id) {
      record.classification_id = crypto.randomUUID();
    }
    if (!record.created_at) {
      record.created_at = new Date().toISOString();
    }
    record.updated_at = new Date().toISOString();

    if (record.duplicate_resolution === undefined) record.duplicate_resolution = "NONE";
    if (record.duplicate_of_txn_id === undefined) record.duplicate_of_txn_id = null;

    this.classifications.set(record.classification_id, record);
    this.classificationsByTxnId.set(record.txn_id, record.classification_id);   

    return cloneValue(record);
  }

  async addClassificationAuditEntry(auditEntry) {
    const record = {
      ...cloneValue(auditEntry),
      audit_id: crypto.randomUUID(),
      changed_at: auditEntry.changed_at || new Date().toISOString()
    };
    this.auditEntries.push(record);
    return cloneValue(record);
  }

  async getClassificationByTxnId(txnId) {
    const classificationId = this.classificationsByTxnId.get(txnId);
    if (!classificationId) return null;
    return cloneValue(this.classifications.get(classificationId));
  }

  async getAuditTrailForClassification(classificationId) {
    return this.auditEntries
      .filter(entry => entry.classification_id === classificationId)
      .sort((a, b) => new Date(b.changed_at) - new Date(a.changed_at))
      .map(entry => cloneValue(entry));
  }

  getTransactionsForAccount(bankAccountId) {
    return [...this.bankTransactions.values()]
      .filter((transaction) => transaction.bank_account_id === bankAccountId)   
      .map((transaction) => cloneValue(transaction));
  }

  async upsertQuarter(quarter) {
    const record = {
      ...cloneValue(quarter),
      quarter_id: quarter.quarter_id || crypto.randomUUID()
    };
    this.quarters.set(record.quarter_id, record);
    return cloneValue(record);
  }

  async getQuarter(quarterId) {
    return cloneValue(this.quarters.get(quarterId) || null);
  }

  async listQuarters(userId) {
    return [...this.quarters.values()]
      .filter(q => q.user_id === userId)
      .map(q => cloneValue(q));
  }

  async upsertQuarterMetrics(metrics) {
    const record = {
      ...cloneValue(metrics),
      quarter_metrics_id: metrics.quarter_metrics_id || crypto.randomUUID(),    
      computed_at: new Date().toISOString()
    };
    this.quarterMetrics.set(record.quarter_id, record);
    return cloneValue(record);
  }

  async getQuarterMetrics(quarterId) {
    return cloneValue(this.quarterMetrics.get(quarterId) || null);
  }

  async getTransactionsByDateRange(userId, startDate, endDate) {
    return [...this.bankTransactions.values()]
      .filter(t => t.user_id === userId && t.date >= startDate && t.date <= endDate)
      .map(t => cloneValue(t));
  }

  getImportRun(importRunId) {
    return cloneValue(this.importRuns.get(importRunId));
  }

  countTransactions() {
    return this.bankTransactions.size;
  }

  async upsertRule(rule) {
    const record = {
      ...cloneValue(rule),
      rule_id: rule.rule_id || crypto.randomUUID(),
      created_at: rule.created_at || new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    this.rules.set(record.rule_id, record);
    return cloneValue(record);
  }

  async getRule(ruleId) {
    return cloneValue(this.rules.get(ruleId) || null);
  }

  async listRules(userId) {
    return [...this.rules.values()]
      .filter(r => r.user_id === userId)
      .map(r => cloneValue(r));
  }

  async deleteRule(ruleId) {
    this.rules.delete(ruleId);
  }

  async upsertEvidence(evidence) {
    const record = {
      ...cloneValue(evidence),
      evidence_id: evidence.evidence_id || crypto.randomUUID(),
      captured_at: evidence.captured_at || new Date().toISOString()
    };
    this.evidence.set(record.evidence_id, record);
    return cloneValue(record);
  }

  async getEvidence(evidenceId) {
    return cloneValue(this.evidence.get(evidenceId) || null);
  }

  async listEvidence(userId) {
    return [...this.evidence.values()]
      .filter(e => e.user_id === userId)
      .map(e => cloneValue(e));
  }

  async getEvidenceByDateRange(userId, startDate, endDate) {
    return [...this.evidence.values()]
      .filter(e => e.user_id === userId && e.doc_date >= startDate && e.doc_date <= endDate)
      .map(e => cloneValue(e));
  }

  async upsertEvidenceLink(link) {
    const record = {
      ...cloneValue(link),
      evidence_link_id: link.evidence_link_id || crypto.randomUUID()
    };
    this.evidenceLinks.set(record.evidence_link_id, record);
    return cloneValue(record);
  }

  async getEvidenceLinksForTransaction(txnId) {
    return [...this.evidenceLinks.values()]
      .filter(l => l.bank_txn_id === txnId)
      .map(l => cloneValue(l));
  }

  async getEvidenceLinksForEvidence(evidenceId) {
    return [...this.evidenceLinks.values()]
      .filter(l => l.evidence_id === evidenceId)
      .map(l => cloneValue(l));
  }

  async upsertExportRecord(exportRecord) {
    const record = {
      ...cloneValue(exportRecord),
      export_id: exportRecord.export_id || crypto.randomUUID(),
      generated_at: exportRecord.generated_at || new Date().toISOString()
    };
    this.exports.set(record.export_id, record);
    return cloneValue(record);
  }

  async getExportRecord(exportId) {
    return cloneValue(this.exports.get(exportId) || null);
  }

  async listExportsForQuarter(quarterId) {
    return [...this.exports.values()]
      .filter(e => e.quarter_id === quarterId)
      .map(e => cloneValue(e));
  }
}

module.exports = {
  MemoryTransactionImportStore
};
