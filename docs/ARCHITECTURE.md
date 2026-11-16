# Architecture (Phase 1)

- **Style:** web application. A Python server (standard library + `cryptography`) serves a JSON API and a single-page
  interface to Chrome/Edge. Multi-user, centrally hosted, runs on-premises or in the cloud (Docker).
- **Database:** SQLite (WAL mode) in the instance folder for this phase — safe for dozens of concurrent users on one server.
  All SQL is isolated in `core/` modules and schema changes live in `core/migrations/`, so moving to PostgreSQL later is a contained step.
- **Multi-company:** one *instance* per company (own database, files, secrets, licence, branding). Code is shared and never edited per company.
- **Security:** scrypt passwords, server-side sessions (token stored hashed), HttpOnly+SameSite=Strict cookies, CSRF token,
  Origin/Host checks, CSP and security headers, rate limiting + lockout, role-based permissions enforced per request,
  append-only hash-chained audit log, signed licences.
- **i18n:** `core/web/i18n/en.json` and `ar.json` must contain the same keys (checked by tests); RTL via CSS logical properties.
- **Upgrades:** numbered migrations with checksums; automatic backup before migrating; `CHANGELOG.md` per release.

## Roadmap
1. Foundation (this release) · 2. Assets, categories & custom fields, employees, assignments (lifecycle) ·
3. Documents, handover/return receipts, PDF (Arabic), Excel import/export · 4. Dashboard analytics, reports ·
5. Visual polish & animations · 6. QR, maintenance, warranty, workflows, notifications · 7. Hardening, performance, recovery tests.
