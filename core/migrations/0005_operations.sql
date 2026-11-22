-- Phase 6: maintenance log, asset requests (approval workflow), settings, e-mail alert preference.

CREATE TABLE maintenance (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id            INTEGER NOT NULL REFERENCES assets(id),
    kind                TEXT NOT NULL CHECK (kind IN ('repair','service','inspection','upgrade','other')),
    status              TEXT NOT NULL CHECK (status IN ('scheduled','open','done','cancelled')),
    title               TEXT NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    vendor              TEXT NOT NULL DEFAULT '',
    cost                REAL,
    scheduled_for       TEXT NOT NULL DEFAULT '',      -- planned date (YYYY-MM-DD) for scheduled work
    started_at          TEXT,
    completed_at        TEXT,
    resolution          TEXT NOT NULL DEFAULT '',
    took_out_of_service INTEGER NOT NULL DEFAULT 0,    -- this record moved the asset to 'maintenance'
    created_by          INTEGER,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX idx_maintenance_asset ON maintenance(asset_id);
CREATE INDEX idx_maintenance_status ON maintenance(status, scheduled_for);

CREATE TABLE asset_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL REFERENCES employees(id),
    category_id   INTEGER REFERENCES categories(id),
    reason        TEXT NOT NULL DEFAULT '',
    needed_by     TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL CHECK (status IN ('pending','fulfilled','rejected','cancelled')),
    requested_by  INTEGER NOT NULL,
    requested_at  TEXT NOT NULL,
    decided_by    INTEGER,
    decided_at    TEXT,
    decision_note TEXT NOT NULL DEFAULT '',
    assignment_id INTEGER REFERENCES assignments(id)
);
CREATE INDEX idx_requests_status ON asset_requests(status);

-- Small key/value settings (alert thresholds, e-mail server). Secrets are stored encrypted by the application.
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

ALTER TABLE users ADD COLUMN email_alerts INTEGER NOT NULL DEFAULT 1;
