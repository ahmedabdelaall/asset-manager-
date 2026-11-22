# Release notes

Format: newest first. Every release lists what changed, why, and any upgrade notes.
Database changes are only ever made through numbered files in `core/migrations/` (never edited after release);
a backup is taken automatically before any migration runs.

## 0.9.0 — Request access with administrator approval

**Added**
- **Request access** link on the sign-in page. People without an account fill in their name, work e-mail, department,
  job title, phone, a preferred username and the reason they need access. Nothing is granted automatically.
- **Access requests** panel at the top of the **Users** page (for users who can manage users), plus an alert in the bell.
  **Approve** opens a form with the username, role, name and e-mail filled in from the request; approving creates the
  account with a temporary password that must be changed at first sign-in. **Reject** takes an optional reason.
  **All requests** shows the history: who decided, when, and which account was created.
- Optional e-mails: on approval the sign-in details (username, temporary password, link) are sent in the language the
  person used; on rejection they are told, with the reason. The password is always shown to the administrator too, in
  case the e-mail is not set up or fails.
- Switch under **Company & branding → Alerts & e-mail**: *Allow people to request access from the sign-in page*
  (on by default). Turning it off hides the link and refuses new requests.
- **Allowed e-mail domains**: each company can limit requests to its own domains (e.g. `mycompany.com, mycompany.com.eg`).
  Set it in the first-time setup form or later under **Company & branding → Alerts & e-mail**. The request form shows
  the accepted domains; any other address is refused. The match is exact (a sub-domain must be listed on its own).
  Empty = any e-mail, which is how existing companies start after the upgrade.
- **Licensing can be switched off** per server: `AM_LICENSE=off` (in `.env` next to `docker-compose.yml`, or
  `"license_enabled": false` in the instance `config.json`). The app then runs fully unlocked: no licence, no user
  limit, the License page, banners and dashboard tile are hidden, and activation is refused with a clear message.
  Default stays **on**; the licence code is untouched so it can be switched back on with one setting.
- Asset Excel import: new column **`assigned_on`** (handover date for `assigned_to`, e.g. `31/3/2025`), so existing
  handovers keep their real date and receipt year (HO-2025-…). Future dates are refused; return dates cannot be before
  the handover, and a new handover cannot be before the last return.
- **Unique custom fields**: tick *Unique* on a text or number field of a category (e.g. a mobile line's phone number,
  a phone's IMEI) and no two assets in that category can share a value. Switching it on is refused while duplicates
  exist. Migration `0009_unique_custom_fields`.
- Database migration `0008_employee_national_id` (adds the column and a unique index); runs automatically.

- **Employee national ID (الرقم القومي)**: new field on the employee form, printed on handover and return receipts
  (in the employee table and next to the employee's signature). If it is not on file, the receipt shows a dotted line
  to write it by hand. Arabic or Western digits, spaces and dashes are accepted; Egyptian 14-digit numbers are checked
  (century, month, day); passport numbers (5-20 letters/digits) also work. Must be unique. Included in the employee
  Excel import (column `national_id`) and export.

**Security**
- National ID is personal data: only users who can manage employees or assignments see it in full (employee page,
  receipts, Excel export). Everyone else sees the last 4 digits; lists never carry it; the audit log stores only the
  masked value.
- The usual account rules apply on approval: an administrator cannot hand out a role stronger than their own, the
  licence user limit counts, usernames must be unique. If anything fails, the request stays waiting and no account is made.
- The public form never reveals whether an e-mail or username already exists; a repeated request from the same e-mail
  is merged. Limits: 5 requests per address per hour, at most 200 waiting requests, a hidden field that catches bots.
- Every request, approval and rejection is in the audit log.

**Fixed**
- The setup and request forms could be wider than a phone screen.
- "Send a test e-mail" now says *why* the mail server failed (wrong password, sender address not allowed, server not
  found, no answer / wrong port, SSL vs STARTTLS mismatch) and shows the server's own reply, instead of a generic
  "the mail server refused the message".

**Upgrade notes:** migration `0007_access_requests.sql` runs automatically (backup first). The feature is on after
upgrading; switch it off under Company & branding if you do not want it.

## 0.8.0 — Phase 5: visual polish & motion

(Released after Phase 7 — the version number follows release order.)

**Fixed (visible bugs found by screenshot review)**
- Dashboard summary cards showed their labels ("Assets", "Assigned"…) as empty white boxes — a style name used by the
  QR label sheets (0.6.0) also matched the cards. Label-sheet styles are now scoped to the label sheet.
- Blue status badges ("Assigned", "Current", …) stretched across the whole table column — the asset-detail grid shared
  the badge's style name (0.2.0). The grid now has its own name.
- The user menu (My account / Sign out) opened under the alert bell instead of under the user's name (0.6.0).
- Arabic headings were letter-spaced and upper-cased like English, which breaks the joining of Arabic letters.

**Polish**
- Menu grouped into Inventory · Operations · Insights · Administration, with an active-page marker.
- Phones: the menu slides in from a ☰ button instead of a narrow icon strip; compact top bar; dialogs open as sheets.
- New sign-in page: brand panel (logo, company name, what the system does) beside the form.
- Motion: pages rise in gently, summary numbers count up, buttons respond to presses, notifications slide in with a
  countdown bar and can be clicked away, the alert bell pulses while something is critical. Loading shows placeholders
  instead of "Loading…". All motion is switched off when the operating system asks for reduced motion.
- Sticky translucent top bar, keyboard focus rings, friendlier empty states, thinner scrollbars, card hover lift.

## 0.7.0 — Phase 7: hardening, performance, recovery

**Backups & recovery**
- **Full backups**: every backup is now one `.zip` with the database **and all uploaded files** (documents, signed
  receipts, logo) plus a SHA-256 checksum for each file. Daily automatic backups are full backups.
- **Verify** any backup (page button or `manage.py verify`): re-hashes every file and integrity-checks the database.
  Tampered, truncated or unsafe archives (path tricks) are refused and never restored.
- **Restore** brings back the database and the files together; the current state is saved first as a `before-restore` backup.
- **Download** backups from the Backups page (super administrator only, audited) to keep a copy off the server; large
  files are streamed, never loaded into memory.
- **System health** panel (Backups page) and `manage.py check`: database integrity, broken links, database version,
  audit-log tamper check, missing/unused document files, age of the last full backup, free disk space, licence.
- **Restore drill** in the automated tests: backup → delete files and change data → restore → every table row and file compared.

**Performance** (measured with `tests/perf_check.py`: 20,000 assets, 5,000 employees, 25,000 assignments)
- Every screen answers in under 0.5 s. Activity report over two years: 1.4 s → 0.15 s; alerts 140 → 90 ms;
  asset export 3.9 s → 1.7 s. New indexes (migration `0006`), report screens show at most 2,000 rows (totals and Excel
  exports always include everything), alerts fetch only what is shown.

**Security**
- Single-line fields (names, titles, tags) can no longer contain line breaks; e-mail headers are always one line.
- Idle/slow connections are dropped after 60 s (protects against connection-exhaustion attacks).
- Extra browser security headers (`Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, `Permissions-Policy`).
- Docker: read-only filesystem except `/data`, all Linux capabilities dropped, `no-new-privileges`.
- Reviewed: SQL parameterisation, output escaping in the interface, upload type checks, archive/backup paths, Excel XML parsing.

**Upgrade notes:** migration `0006_performance.sql` runs automatically. Existing `data_*.db` backups can still be
verified and restored. After upgrading, create a first full backup from the Backups page.

## 0.6.0 — Phase 6: QR labels, maintenance, approvals, alerts & e-mail

(0.5.0 is reserved for the visual-polish phase.)

**Added**
- **QR labels**: print label sheets (50×25, 70×37 or 100×50 mm) from the Assets list (selected assets or the current page)
  or from an asset. Scanning a label with a phone opens the asset in the app (after sign-in). The QR generator is
  built in (no external service); the link address is set once under Company & branding.
- **Maintenance log**: repairs, services, inspections and upgrades with vendor, cost and result. Work can start now or be
  scheduled. Starting work can take an in-stock asset out of service; it returns to stock when the last open work on it
  is completed or cancelled. Shown on the asset, on its timeline, and on a new **Maintenance** page.
  New report: **Maintenance & costs**.
- **Asset requests (approval workflow)**: users with `requests.create` (e.g. HR) request an asset for an employee;
  approvers pick an in-stock asset from the requested category and approve — the asset is assigned immediately — or
  reject with a reason. Requesters see only their own requests and are notified of the decision.
- **Alerts** (bell in the top bar): overdue returns, warranties ending soon, maintenance due or overdue, requests waiting
  for approval, decisions on your requests. Each user only sees what their permissions allow.
- **Daily e-mail summary** (optional): configure your mail server under Company & branding → Alerts & e-mail;
  each user can opt out under My account. The SMTP password is stored encrypted and never shown again.
- New permissions: `maintenance.view`, `maintenance.manage`, `requests.create`, `requests.approve`
  (granted on upgrade: Company Administrator all; Asset Manager all; HR `requests.create`; Viewer `maintenance.view`).

**Upgrade notes:** migration `0005_operations.sql` runs automatically (backup first). To use QR labels from phones and
links in e-mails, set *Address your team uses* in Company & branding.

## 0.4.0 — Phase 4: reports & dashboard analytics

**Added**
- **Dashboard charts** (for users who can view assets): assets by status (segmented bar), assets by category and
  assets held per department (ranked bars), handovers vs returns over the last 12 months (line chart).
  Every chart has hover/keyboard tooltips and a **Table** view; colours come from a colour-blind-checked palette
  with separate light and dark steps, and a status always keeps the same colour.
- **Reports** page with five reports — each with filters, totals, **Excel export** and **Print**:
  assets per employee · overdue returns · warranty expiry (next 30–365 days, optionally expired) ·
  assignment activity (last 7/30/90 days, this month/year or a custom range) ·
  asset value & depreciation (summary per category + per asset).
- **Depreciation**: categories get a *useful life (years)*; book value uses straight-line depreciation to zero from the purchase date.
- New permission `reports.view` (granted on upgrade to Company Administrator, Asset Manager, HR and Viewer).

**Fixed**
- "Today" (overdue returns, warranty days, date checks) now follows the server's local time zone instead of UTC.
  Set `TZ` (e.g. `TZ=Asia/Riyadh`) in `.env` for Docker — see DEPLOY_DOCKER.md.

**Upgrade notes:** migration `0004_reports.sql` runs automatically (backup first). Optionally set `TZ` in `.env`.

## 0.3.0 — Phase 3: documents, receipts, Excel

**Added**
- **Documents** on assets and employees (invoices, photos, contracts, IDs): PDF, images, Word, Excel up to 25 MB.
  The file type is verified from the content; files are stored with random names; uploads and deletions are audited.
  Viewing follows the record's permission (e.g. `assets.view`), adding/deleting follows the manage permission.
- **Handover and return receipts**: numbered automatically per year (`HO-2026-0001`, `RT-2026-0001`), printable on A4
  in Arabic or English with company logo, employee and asset details (including custom fields), condition, notes,
  terms and signature lines. *Print → Save as PDF* produces the PDF. The signed scan can be attached to the receipt.
  Existing assignments are numbered by the upgrade.
- **Receipt terms** editable per company in two languages (Company & branding); a standard text is used when empty.
- **Excel import** of employees and assets with a downloadable template (Help sheet + list of categories and their custom fields).
  The file is checked first and shows every problem by row and column; nothing is saved unless all rows are valid.
  Options: update existing records (by employee number / asset tag, only the columns in the file change);
  departments are created automatically; assets can be assigned on import (`assigned_to` = employee number).
  Accepts .xlsx and .csv; dates as 2026-03-31, 31/03/2026 or Excel dates; conditions/statuses in English or Arabic.
- **Excel export** of assets (with current filters and custom fields), employees and the full assignment history.
  Exports use the template's column names, so an export can be edited and imported back with "update existing".

**Important:** the daily backups contain the database only. Also copy the `uploads/` folder (documents, logo) — see DEPLOY_DOCKER.md.

**Upgrade notes:** migration `0003_documents.sql` runs automatically (backup first). No manual steps.

## 0.2.0 — Phase 2: assets, employees and assignments

**Added**
- **Categories** with custom fields per category (text, number, date, list, yes/no; optional "required").
  Each category has a short code used to generate asset tags automatically (e.g. `LAP-00001`).
- **Assets**: tag, name, brand, model, serial number (unique), condition, location, purchase date & cost, supplier,
  warranty date, notes and the category's custom fields. Search, filter by status/category, pagination.
  Each asset has a full activity timeline (from the audit log) and its assignment history.
- **Lifecycle**: In stock → Assigned → Returned (back to stock, maintenance, retired or lost). Status changes record a reason.
  An asset can never be assigned to two people at once (enforced by the database).
- **Employees & departments**: employee number (unique), names in two languages, department, job title, contact details.
  Employees do not need a user account. Employee page shows assets held now and previously.
- **Assignments** page: everything currently handed out, with expected return dates and overdue highlighting.
- **Dashboard**: asset totals by status, overdue returns, warranties ending within 30 days, total asset value.
- New permissions: `assets.view`, `assets.manage`, `categories.manage`, `assignments.manage`, `employees.view`,
  `employees.manage` — granted automatically to the built-in roles on upgrade (Asset Manager, HR, Viewer, Company Administrator).

**Data protection rules**
- Assets with assignment history cannot be deleted — retire them instead. Employees with history cannot be deleted — mark them as "left".
- An employee who still holds assets cannot be marked as left. A category or department in use cannot be deleted.

**Fixed**
- `manage.py restore` now prints a clear message instead of a crash when the database is still in use (server not stopped).

**Upgrade notes:** migration `0002_assets.sql` runs automatically on start (a backup is taken first). No manual steps.

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
