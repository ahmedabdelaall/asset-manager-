-- Phase 3: attached documents, handover/return receipt numbers, receipt terms text.

CREATE TABLE documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity      TEXT NOT NULL CHECK (entity IN ('asset','employee','assignment')),
    entity_id   INTEGER NOT NULL,
    filename    TEXT NOT NULL,                 -- original name, shown to users
    stored      TEXT NOT NULL UNIQUE,          -- path under uploads/, random name
    mime        TEXT NOT NULL,
    size        INTEGER NOT NULL,
    sha256      TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    uploaded_by INTEGER,
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_documents_entity ON documents(entity, entity_id);

-- Simple named counters (receipt numbers per year, e.g. HO-2026 -> 17)
CREATE TABLE counters (
    key   TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);

ALTER TABLE assignments ADD COLUMN receipt_out_no TEXT;
ALTER TABLE assignments ADD COLUMN receipt_in_no TEXT;

-- number the assignments that already exist
UPDATE assignments SET receipt_out_no = (
    SELECT 'HO-' || s.y || '-' || printf('%04d', s.rn) FROM (
        SELECT id, substr(assigned_at, 1, 4) AS y, row_number() OVER (PARTITION BY substr(assigned_at, 1, 4) ORDER BY id) AS rn
        FROM assignments) s WHERE s.id = assignments.id);
UPDATE assignments SET receipt_in_no = (
    SELECT 'RT-' || s.y || '-' || printf('%04d', s.rn) FROM (
        SELECT id, substr(returned_at, 1, 4) AS y, row_number() OVER (PARTITION BY substr(returned_at, 1, 4) ORDER BY id) AS rn
        FROM assignments WHERE returned_at IS NOT NULL) s WHERE s.id = assignments.id)
WHERE returned_at IS NOT NULL;
INSERT INTO counters(key, value) SELECT 'HO-' || substr(assigned_at, 1, 4), COUNT(*) FROM assignments GROUP BY 1;
INSERT INTO counters(key, value) SELECT 'RT-' || substr(returned_at, 1, 4), COUNT(*) FROM assignments WHERE returned_at IS NOT NULL GROUP BY 1;
CREATE UNIQUE INDEX idx_receipt_out ON assignments(receipt_out_no) WHERE receipt_out_no IS NOT NULL;
CREATE UNIQUE INDEX idx_receipt_in ON assignments(receipt_in_no) WHERE receipt_in_no IS NOT NULL;

ALTER TABLE company ADD COLUMN receipt_terms_en TEXT NOT NULL DEFAULT '';
ALTER TABLE company ADD COLUMN receipt_terms_ar TEXT NOT NULL DEFAULT '';
