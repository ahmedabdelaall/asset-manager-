# Release notes

Format: newest first. Every release lists what changed, why, and any upgrade notes.
Database changes are only ever made through numbered files in `core/migrations/` (never edited after release);
a backup is taken automatically before any migration runs.

## 0.1.0 — Phase 1 foundation (first release)

**Added**
- Web application served on port 5222 (Docker) — works in Chrome/Edge, multi-user.
- First-run setup wizard protected by a one-time setup code (printed in the server logs).
- Secure sign-in: scrypt password hashing, sessions with idle/absolute timeout, CSRF protection,
  account lockout and IP rate limiting, forced password change for admin-created accounts.
- Roles and permissions (Super Administrator, Company Administrator, Asset Manager, HR, Viewer + custom roles),
  with protection against privilege escalation and removal of the last Super Administrator.
- Company configuration & branding (names in two languages, logo, colours, default language/theme). No company is hard-coded.
- Licensing: Ed25519-signed licences bound to the deployment, expiry + grace period, user limit, features,
  signed revocation lists, offline activation (request code → licence file), clock-rollback protection, licence history.
- Tamper-evident audit log (append-only, hash-chained) with an integrity check.
- Database migrations with checksum protection, automatic daily backups, pre-migration backups, restore command.
- Arabic and English interface (RTL/LTR), light and dark themes, branding colours.
- Admin CLI (`tools/manage.py`), vendor licence tool (`tools/license_tool.py`), deployment generator (`tools/make_deployment.py`).

**Not included yet (planned phases):** assets & categories, employees, assignments, documents, receipts/PDF,
Excel import/export, reports, QR codes, maintenance, workflows.

**Upgrade notes:** none (first release).
