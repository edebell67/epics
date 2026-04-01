-- Evidence and Evidence Matching Migration [V20260322_1930]
-- Persists evidence records, extracted metadata, and links to transactions.

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('RECEIPT', 'INVOICE', 'OTHER')),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    doc_date DATE,
    merchant TEXT,
    amount NUMERIC(18,2),
    storage_link TEXT NOT NULL,
    extraction_confidence NUMERIC(3,2) NOT NULL DEFAULT 0.0 CHECK (extraction_confidence >= 0.0 AND extraction_confidence <= 1.0),
    ocr_status TEXT NOT NULL DEFAULT 'PENDING' -- PENDING, COMPLETED, FAILED
);

CREATE INDEX IF NOT EXISTS idx_evidence_user_id ON evidence(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_doc_date ON evidence(doc_date);

CREATE TABLE IF NOT EXISTS evidence_link (
    evidence_link_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evidence_id UUID NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    bank_txn_id UUID REFERENCES bank_transactions(txn_id) ON DELETE SET NULL,
    link_confidence NUMERIC(3,2) NOT NULL DEFAULT 0.0 CHECK (link_confidence >= 0.0 AND link_confidence <= 1.0),
    user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_at TIMESTAMPTZ,
    method TEXT NOT NULL CHECK (method IN ('candidate_match', 'user_confirmed', 'voice_confirmed', 'manual_no_match', 'deferred'))
);

CREATE INDEX IF NOT EXISTS idx_evidence_link_evidence_id ON evidence_link(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_link_bank_txn_id ON evidence_link(bank_txn_id);
