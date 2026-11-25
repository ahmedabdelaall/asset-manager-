-- Invitations: an administrator invites a person by e-mail and chooses their role (and optionally the username).
-- The person opens the one-time link, chooses a password and the account is created with exactly that role.
-- Only a SHA-256 hash of the link's secret is stored, so a copy of the database cannot be used to accept an invitation.

CREATE TABLE invitations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    email        TEXT NOT NULL,
    full_name    TEXT NOT NULL,
    username     TEXT NOT NULL DEFAULT '',      -- empty: the person chooses it when accepting
    role_id      INTEGER NOT NULL REFERENCES roles(id),
    lang         TEXT NOT NULL DEFAULT 'en',
    token_hash   TEXT NOT NULL UNIQUE,
    status       TEXT NOT NULL CHECK (status IN ('pending','accepted','revoked')),
    created_by   INTEGER NOT NULL REFERENCES users(id),
    created_at   TEXT NOT NULL,
    expires_at   INTEGER NOT NULL,              -- unix time
    sent_at      TEXT,                          -- last time the e-mail went out (NULL: not e-mailed)
    accepted_at  TEXT,
    user_id      INTEGER REFERENCES users(id)   -- the account created on acceptance
);
CREATE INDEX idx_invitations_status ON invitations(status, id);
CREATE INDEX idx_invitations_email ON invitations(email);
