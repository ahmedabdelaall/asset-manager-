-- Foundation schema: company identity, users, roles/permissions, sessions, audit trail, licensing.

CREATE TABLE company (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    name_en          TEXT NOT NULL,
    name_ar          TEXT NOT NULL DEFAULT '',
    app_name_en      TEXT NOT NULL DEFAULT 'Asset Manager',
    app_name_ar      TEXT NOT NULL DEFAULT 'إدارة الأصول',
    logo_file        TEXT,
    logo_hash        TEXT,
    primary_color    TEXT NOT NULL DEFAULT '#6D4AF2',
    accent_color     TEXT NOT NULL DEFAULT '#2F6BF0',
    default_language TEXT NOT NULL DEFAULT 'en' CHECK (default_language IN ('en','ar')),
    default_theme    TEXT NOT NULL DEFAULT 'light' CHECK (default_theme IN ('light','dark','system')),
    updated_at       TEXT NOT NULL
);

CREATE TABLE roles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    key             TEXT NOT NULL UNIQUE,
    name_en         TEXT NOT NULL,
    name_ar         TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    is_system       INTEGER NOT NULL DEFAULT 0,
    all_permissions INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE permissions (
    code   TEXT PRIMARY KEY,
    module TEXT NOT NULL
);

CREATE TABLE role_permissions (
    role_id   INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    perm_code TEXT NOT NULL REFERENCES permissions(code) ON DELETE CASCADE,
    PRIMARY KEY (role_id, perm_code)
);

CREATE TABLE users (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    username             TEXT NOT NULL UNIQUE,
    full_name            TEXT NOT NULL,
    email                TEXT NOT NULL DEFAULT '',
    role_id              INTEGER NOT NULL REFERENCES roles(id),
    password_hash        TEXT NOT NULL,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    is_active            INTEGER NOT NULL DEFAULT 1,
    lang                 TEXT CHECK (lang IN ('en','ar')),
    theme                TEXT CHECK (theme IN ('light','dark','system')),
    failed_count         INTEGER NOT NULL DEFAULT 0,
    locked_until         INTEGER NOT NULL DEFAULT 0,
    last_login_at        TEXT,
    password_changed_at  TEXT,
    created_at           TEXT NOT NULL,
    created_by           INTEGER
);

CREATE TABLE sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    csrf       TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    last_seen  INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    ip         TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    revoked    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_sessions_user ON sessions(user_id);

-- Append-only, hash-chained audit trail
CREATE TABLE audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    user_id   INTEGER,
    username  TEXT NOT NULL DEFAULT '',
    action    TEXT NOT NULL,
    entity    TEXT NOT NULL DEFAULT '',
    entity_id TEXT NOT NULL DEFAULT '',
    detail    TEXT NOT NULL DEFAULT '{}',
    ip        TEXT NOT NULL DEFAULT '',
    prev_hash TEXT NOT NULL,
    hash      TEXT NOT NULL
);
CREATE INDEX idx_audit_ts ON audit_log(ts);
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;

-- Licensing
CREATE TABLE license_store (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    envelope     TEXT NOT NULL,
    license_id   TEXT NOT NULL,
    activated_at TEXT NOT NULL,
    activated_by TEXT NOT NULL DEFAULT ''
);
CREATE TABLE license_events (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    event  TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '{}'
);
CREATE TRIGGER license_events_no_update BEFORE UPDATE ON license_events BEGIN SELECT RAISE(ABORT, 'license events are append-only'); END;
CREATE TRIGGER license_events_no_delete BEFORE DELETE ON license_events BEGIN SELECT RAISE(ABORT, 'license events are append-only'); END;
CREATE TABLE license_revocations (
    id       INTEGER PRIMARY KEY CHECK (id = 1),
    envelope TEXT NOT NULL,
    serial   INTEGER NOT NULL
);

-- Small signed key/value store (e.g. last time the server clock was seen)
CREATE TABLE system_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    mac   TEXT NOT NULL
);
