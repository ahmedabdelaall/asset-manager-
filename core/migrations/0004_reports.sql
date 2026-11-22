-- Phase 4: straight-line depreciation needs a useful life per category (0 = not depreciated).
ALTER TABLE categories ADD COLUMN useful_life_years INTEGER NOT NULL DEFAULT 0;
CREATE INDEX idx_assignments_dates ON assignments(assigned_at, returned_at);
