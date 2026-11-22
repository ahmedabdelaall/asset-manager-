# Architecture (Phase 7)

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

- **Inventory (Phase 2):** business rules live in `core/inventory.py`, HTTP routes in `core/api_inventory.py`.
  Every change is audited inside the same transaction; the asset timeline is read from the audit log (`entity='asset'`).
  Asset status `assigned` is only set/cleared by assign/return; a partial unique index allows one open assignment per asset.

- **Documents & Excel (Phase 3):** `core/documents.py` (uploads under `uploads/docs/`, type sniffed from content),
  `core/xlsx.py` (dependency-free .xlsx reader/writer), `core/transfer.py` (import = one transaction with a savepoint
  per row; dry-run or any error rolls everything back). Receipts are rendered by the browser (`#/receipt`) and printed
  to PDF, which gives correct Arabic shaping without server-side PDF libraries.

- **Reports (Phase 4):** `core/reports.py` — every report returns `{columns, rows, totals, summary?}` so one renderer
  and one Excel exporter serve all of them. Charts are dependency-free HTML/SVG in `app.js`; palette tokens live in
  `.viz` in `app.css` (validated categorical slots 1–5, light and dark steps).

- **Operations (Phase 6):** `core/operations.py` (maintenance state machine and the request → approve → assign workflow),
  `core/notify.py` (settings with an AES-GCM-encrypted SMTP password, permission-filtered live alerts, daily digest thread),
  `core/web/qr.js` (dependency-free QR encoder: byte mode, level M, versions 1–10; checked against the ISO reference vectors).

- **Hardening (Phase 7):** `core/backup.py` (full zip backups with manifest + SHA-256, verify, restore with zip-slip
  protection, scheduler), `core/health.py` (read-only system checks), streamed file responses (`Raw(path=...)`),
  `tests/perf_check.py` (large-data benchmark), `tests/test_phase7.py` (restore drill).

- **Request access (0.9.0):** `core/access.py` — public form (`POST /api/access-requests`, rate-limited, honeypot,
  no account enumeration) and an approval queue for `users.manage`; approval calls `Auth.create_user` inside one
  transaction, so role, licence and username rules are the same as for "Add user".

## Roadmap
1. Foundation ✔ · 2. Assets, categories & custom fields, employees, assignments (lifecycle) ✔ (0.2.0) ·
3. Documents, handover/return receipts, PDF (Arabic), Excel import/export ✔ (0.3.0) · 4. Dashboard analytics, reports ✔ (0.4.0) ·
5. Visual polish & animations ✔ (0.8.0) · 6. QR, maintenance, warranty, workflows, notifications ✔ (0.6.0) · 7. Hardening, performance, recovery tests ✔ (0.7.0).
