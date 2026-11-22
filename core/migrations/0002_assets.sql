-- Phase 2: asset categories with custom fields, departments, employees, assets and assignments.

CREATE TABLE categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,              -- prefix of generated asset tags, e.g. LAP -> LAP-00001
    name_en     TEXT NOT NULL,
    name_ar     TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    next_seq    INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- Extra fields an administrator defines per category (e.g. RAM for laptops, plate number for vehicles)
CREATE TABLE category_fields (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    label_en    TEXT NOT NULL,
    label_ar    TEXT NOT NULL,
    type        TEXT NOT NULL CHECK (type IN ('text','number','date','select','bool')),
    options     TEXT NOT NULL DEFAULT '[]',        -- JSON list, for type=select
    required    INTEGER NOT NULL DEFAULT 0,
    sort        INTEGER NOT NULL DEFAULT 0,
    UNIQUE (category_id, key)
);

CREATE TABLE departments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name_en    TEXT NOT NULL,
    name_ar    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE employees (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_no        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name_en  TEXT NOT NULL,
    full_name_ar  TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    job_title     TEXT NOT NULL DEFAULT '',
    email         TEXT NOT NULL DEFAULT '',
    phone         TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','left')),
    notes         TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX idx_employees_dept ON employees(department_id);

CREATE TABLE assets (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tag            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    category_id    INTEGER NOT NULL REFERENCES categories(id),
    name           TEXT NOT NULL,
    brand          TEXT NOT NULL DEFAULT '',
    model          TEXT NOT NULL DEFAULT '',
    serial_no      TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'in_stock' CHECK (status IN ('in_stock','assigned','maintenance','retired','lost')),
    condition      TEXT NOT NULL DEFAULT 'good' CHECK (condition IN ('new','good','fair','poor','damaged')),
    location       TEXT NOT NULL DEFAULT '',
    purchase_date  TEXT NOT NULL DEFAULT '',
    purchase_cost  REAL,
    supplier       TEXT NOT NULL DEFAULT '',
    warranty_until TEXT NOT NULL DEFAULT '',
    notes          TEXT NOT NULL DEFAULT '',
    custom         TEXT NOT NULL DEFAULT '{}',     -- JSON object: values of the category's custom fields
    created_at     TEXT NOT NULL,
    created_by     INTEGER,
    updated_at     TEXT NOT NULL
);
CREATE INDEX idx_assets_category ON assets(category_id);
CREATE INDEX idx_assets_status ON assets(status);
CREATE UNIQUE INDEX idx_assets_serial ON assets(serial_no COLLATE NOCASE) WHERE serial_no <> '';

-- Who holds what. An open assignment has returned_at NULL; at most one open assignment per asset.
CREATE TABLE assignments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id        INTEGER NOT NULL REFERENCES assets(id),
    employee_id     INTEGER NOT NULL REFERENCES employees(id),
    assigned_at     TEXT NOT NULL,
    assigned_by     INTEGER,
    expected_return TEXT NOT NULL DEFAULT '',
    condition_out   TEXT NOT NULL,
    notes_out       TEXT NOT NULL DEFAULT '',
    returned_at     TEXT,
    returned_by     INTEGER,
    condition_in    TEXT,
    notes_in        TEXT NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX idx_assignments_open ON assignments(asset_id) WHERE returned_at IS NULL;
CREATE INDEX idx_assignments_employee ON assignments(employee_id);
CREATE INDEX idx_audit_entity ON audit_log(entity, entity_id);
