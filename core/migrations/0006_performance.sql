-- Phase 7: indexes found with the large-data performance check (tests/perf_check.py).
CREATE INDEX idx_assets_warranty ON assets(warranty_until) WHERE warranty_until <> '';
CREATE INDEX idx_assignments_open_due ON assignments(expected_return) WHERE returned_at IS NULL;
CREATE INDEX idx_assignments_returned ON assignments(returned_at) WHERE returned_at IS NOT NULL;
CREATE INDEX idx_audit_user ON audit_log(username);
