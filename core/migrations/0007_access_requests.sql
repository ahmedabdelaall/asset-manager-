-- Request access: people without an account ask for one from the sign-in page; an administrator approves
-- (choosing the username and role, which creates the account) or rejects. Nothing is granted automatically.

CREATE TABLE access_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL DEFAULT '',
    phone         TEXT NOT NULL DEFAULT '',
    department    TEXT NOT NULL DEFAULT '',
    job_title     TEXT NOT NULL DEFAULT '',
    username      TEXT NOT NULL DEFAULT '',      -- preferred username (a suggestion; the administrator decides)
    reason        TEXT NOT NULL DEFAULT '',
    lang          TEXT NOT NULL DEFAULT 'en',
    status        TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')),
    ip            TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL,
    decided_by    INTEGER,
    decided_at    TEXT,
    decision_note TEXT NOT NULL DEFAULT '',
    user_id       INTEGER REFERENCES users(id)   -- the account created on approval
);
CREATE INDEX idx_access_requests_status ON access_requests(status, id);
