# -*- coding: utf-8 -*-
"""Excel import (employees, assets) and export (assets, employees, assignments).

Import is all-or-nothing: every row is validated with the same rules as the screens, inside one transaction.
With dry_run (the "check file" step) or if any row fails, everything is rolled back and the errors are returned.
Exported files use the same column names as the import templates, so an export can be edited and re-imported."""
import os
import re
import json
import datetime

from . import inventory as inv
from . import xlsx
from .errors import ApiError
from .util import today_iso

WEB_I18N = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "i18n")
EMP_COLS = ["emp_no", "full_name_en", "full_name_ar", "department", "job_title", "email", "phone", "national_id", "status", "notes"]
ASSET_COLS = ["category_code", "tag", "name", "brand", "model", "serial_no", "condition", "location", "purchase_date",
              "purchase_cost", "supplier", "warranty_until", "notes", "assigned_to", "assigned_on"]
REQUIRED = {"emp_no", "category_code", "name"}
MAX_ERRORS = 300

_DICTS = {}


def _dict(lang):
    if lang not in _DICTS:
        with open(os.path.join(WEB_I18N, lang + ".json"), encoding="utf-8") as f:
            _DICTS[lang] = json.load(f)
    return _DICTS[lang]


def _t(lang, key):
    return _dict(lang).get(key) or _dict("en").get(key) or key


def _reverse(prefix, codes):
    """Accept codes and their English/Arabic labels (e.g. 'good', 'Good', 'جيد')."""
    out = {}
    for c in codes:
        out[c.lower()] = c
        for lang in ("en", "ar"):
            lbl = _dict(lang).get(prefix + c)
            if lbl:
                out[lbl.strip().lower()] = c
    return out


# ------------------------------------------------------------------ cell helpers
def _s(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else ""
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    return str(v).strip()


def _date(v):
    s = _s(v)
    if not s:
        return ""
    if isinstance(v, float):                                 # date typed into a General-formatted cell
        try:
            return xlsx._serial_to_date(v)
        except (OverflowError, ValueError):
            return s
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T].*)?", s)
    if m:
        y, mo, d = m.groups()
    else:
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", s)        # day/month/year
        if not m:
            return s                                         # let the normal validation report it
        d, mo, y = m.groups()
    try:
        return datetime.date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return s


def _bool(v):
    if isinstance(v, bool):
        return v
    return _s(v).lower() in ("1", "yes", "y", "true", "x", "✓", "نعم")


def _parse(data, filename):
    if data[:4] == b"PK\x03\x04":
        rows = xlsx.read(data)
    elif (filename or "").lower().endswith(".csv") or b"," in data[:2000] or b";" in data[:2000]:
        rows = xlsx.read_csv(data)
    else:
        raise ApiError(400, "file_unreadable", "Use an Excel (.xlsx) or CSV file")
    while rows and not any(_s(v) for v in rows[0]):
        rows.pop(0)
    if not rows:
        raise ApiError(400, "file_empty", "The file has no rows")
    header = [re.sub(r"[\s*]+$", "", _s(h)).strip().lower() for h in rows[0]]
    return header, rows[1:]


def _map(header, known):
    idx, ignored = {}, []
    for i, h in enumerate(header):
        if not h:
            continue
        if h in known and h not in idx:
            idx[h] = i
        else:
            ignored.append(h)
    missing = [c for c in known if c in REQUIRED and c not in idx]
    if missing:
        raise ApiError(422, "missing_columns", "Required columns are missing: " + ", ".join(missing), columns=missing)
    return idx, ignored


FIELD_TO_COL = {"department_id": "department", "category_id": "category_code", "employee_id": "assigned_to"}


class _Rollback(Exception):
    pass


def _run(ctx, rows, dry_run, handle_row):
    db = ctx.db
    result = {"total": 0, "created": 0, "updated": 0, "errors": [], "error_count": 0, "committed": False}
    try:
        with db.tx():
            for n, row in enumerate(rows, start=2):                 # row 1 is the header
                if not any(_s(v) for v in row):
                    continue
                result["total"] += 1
                db.execute("SAVEPOINT imp_row")
                try:
                    result[handle_row(row)] += 1
                    db.execute("RELEASE imp_row")
                except ApiError as e:
                    db.execute("ROLLBACK TO imp_row")
                    db.execute("RELEASE imp_row")
                    result["error_count"] += 1
                    if len(result["errors"]) < MAX_ERRORS:
                        f = e.extra.get("field", "")
                        col = f[7:] if f.startswith("custom.") else FIELD_TO_COL.get(f, f)
                        result["errors"].append({"row": n, "column": col, "code": e.code, "error": e.message})
            if result["total"] == 0:
                raise ApiError(400, "file_empty", "The file has no rows")
            if dry_run or result["error_count"]:
                raise _Rollback()
            result["committed"] = True
            ctx.audit("import.%s" % handle_row.kind, "import", "", {k: result[k] for k in ("total", "created", "updated")})
    except _Rollback:
        pass
    return result


# ------------------------------------------------------------------ import: employees
def import_employees(ctx, data, filename, dry_run=True, update=False):
    header, rows = _parse(data, filename)
    idx, ignored = _map(header, EMP_COLS)
    db = ctx.db
    status_map = _reverse("emp.", ("active", "left"))
    created_depts = []

    def dept_id(name):
        if not name:
            return None
        r = db.one("SELECT id FROM departments WHERE lower(name_en)=lower(?) OR lower(name_ar)=lower(?)", (name, name))
        if r:
            return r["id"]
        created_depts.append(name)
        arabic = bool(re.search(r"[؀-ۿ]", name))
        return inv.save_department(ctx, None, {"name_en": "" if arabic else name, "name_ar": name if arabic else ""})

    def handle(row):
        cell = lambda c: _s(row[idx[c]]) if c in idx and idx[c] < len(row) else None   # None = column not in file
        emp_no = cell("emp_no")
        if not emp_no:
            raise ApiError(422, "field_required", "emp_no is required", field="emp_no")
        old = db.one("SELECT * FROM employees WHERE emp_no=?", (emp_no,))
        if old and not update:
            raise ApiError(409, "employee_no_taken", "Another employee has this number", field="emp_no")
        body = dict(old) if old else {"status": "active"}
        for c in ("full_name_en", "full_name_ar", "job_title", "email", "phone", "notes", "national_id"):
            if cell(c) is not None:
                body[c] = cell(c)
        body["emp_no"] = emp_no
        if cell("status"):
            st = status_map.get(cell("status").lower())
            if not st:
                raise ApiError(422, "invalid_field", "Invalid status", field="status")
            body["status"] = st
        if cell("department") is not None:
            body["department_id"] = dept_id(cell("department"))
        inv.save_employee(ctx, old["id"] if old else None, body)
        return "updated" if old else "created"
    handle.kind = "employees"
    res = _run(ctx, rows, dry_run, handle)
    res["ignored_columns"] = ignored
    res["departments_created"] = sorted(set(created_depts))
    return res


# ------------------------------------------------------------------ import: assets
def _custom_keys(db):
    keys = []
    for c in inv.list_categories(db):
        for f in c["fields"]:
            if f["key"] not in keys:
                keys.append(f["key"])
    return keys


def import_assets(ctx, data, filename, dry_run=True, update=False):
    db = ctx.db
    header, rows = _parse(data, filename)
    custom_keys = [k for k in _custom_keys(db) if k not in ASSET_COLS]
    idx, ignored = _map(header, ASSET_COLS + custom_keys)
    cats = {c["code"]: c for c in inv.list_categories(db)}
    cond_map = _reverse("cond.", inv.CONDITIONS)

    def handle(row):
        cell = lambda c: _s(row[idx[c]]) if c in idx and idx[c] < len(row) else None
        raw = lambda c: row[idx[c]] if c in idx and idx[c] < len(row) else None
        code = (cell("category_code") or "").upper()
        if not code:
            raise ApiError(422, "field_required", "category_code is required", field="category_code")
        cat = cats.get(code)
        if cat is None:
            raise ApiError(422, "category_not_found", "Unknown category code", field="category_code")
        tag = (cell("tag") or "").upper()
        old = db.one("SELECT * FROM assets WHERE tag=?", (tag,)) if tag else None
        if old and not update:
            raise ApiError(409, "asset_tag_taken", "Another asset already has this tag", field="tag")
        if old:
            body = dict(old)
            body["custom"] = json.loads(old["custom"] or "{}")
        else:
            body = {"custom": {}, "condition": "good"}
        body["category_id"], body["tag"] = cat["id"], tag
        for c in ("name", "brand", "model", "serial_no", "location", "supplier", "notes"):
            if cell(c) is not None:
                body[c] = cell(c)
        for c in ("purchase_date", "warranty_until"):
            if cell(c) is not None:
                body[c] = _date(raw(c))
        if cell("purchase_cost") is not None:
            body["purchase_cost"] = cell("purchase_cost").replace(",", "")
        if cell("condition"):
            cnd = cond_map.get(cell("condition").lower())
            if not cnd:
                raise ApiError(422, "invalid_field", "Invalid condition", field="condition")
            body["condition"] = cnd
        for f in cat["fields"]:
            if f["key"] not in idx:
                continue
            v = raw(f["key"])
            if f["type"] == "bool":
                body["custom"][f["key"]] = _bool(v)
            elif f["type"] == "date":
                body["custom"][f["key"]] = _date(v)
            else:
                body["custom"][f["key"]] = _s(v)
        if old:
            inv.update_asset(ctx, old["id"], body)
            return "updated"
        aid, _ = inv.create_asset(ctx, body)
        holder = cell("assigned_to")
        if holder:
            e = db.one("SELECT id FROM employees WHERE emp_no=?", (holder,))
            if e is None:
                raise ApiError(422, "employee_not_found", "No employee with this number", field="assigned_to")
            inv.assign(ctx, aid, {"employee_id": e["id"]}, at=_date(raw("assigned_on")) or None)
        elif cell("assigned_on"):
            raise ApiError(422, "field_required", "assigned_on needs assigned_to", field="assigned_to")
        return "created"
    handle.kind = "assets"
    res = _run(ctx, rows, dry_run, handle)
    res["ignored_columns"] = ignored
    return res


# ------------------------------------------------------------------ templates
HELP = {
    "emp_no": ("Unique employee number (required)", "الرقم الوظيفي - فريد (إلزامي)"),
    "full_name_en": ("Full name in English (English or Arabic name required)", "الاسم بالإنجليزية (مطلوب اسم بالعربية أو الإنجليزية)"),
    "full_name_ar": ("Full name in Arabic", "الاسم بالعربية"),
    "department": ("Department name - created automatically if it does not exist", "اسم الإدارة - تُنشأ تلقائياً إن لم تكن موجودة"),
    "job_title": ("Job title", "المسمى الوظيفي"), "email": ("Email address", "البريد الإلكتروني"), "phone": ("Phone", "الهاتف"),
    "national_id": ("National ID (14 digits in Egypt) or passport number - printed on receipts, must be unique",
                    "الرقم القومي (14 رقماً في مصر) أو رقم جواز السفر - يُطبع على الإيصالات، ويجب ألا يتكرر"),
    "status": ("active or left (empty = active)", "active أو left (فارغ = نشط)"), "notes": ("Notes", "ملاحظات"),
    "category_code": ("Category code, e.g. LAP (required)", "رمز التصنيف مثل LAP (إلزامي)"),
    "tag": ("Asset tag - leave empty to generate automatically", "رمز الأصل - اتركه فارغاً ليُنشأ تلقائياً"),
    "name": ("Asset name / description (required)", "اسم الأصل / الوصف (إلزامي)"),
    "brand": ("Brand", "الماركة"), "model": ("Model", "الموديل"), "serial_no": ("Serial number - must be unique", "الرقم التسلسلي - يجب أن يكون فريداً"),
    "condition": ("new, good, fair, poor or damaged (empty = good)", "new أو good أو fair أو poor أو damaged (فارغ = جيد)"),
    "location": ("Location", "الموقع"), "purchase_date": ("Date, e.g. 2026-03-31", "تاريخ مثل 2026-03-31"),
    "purchase_cost": ("Number", "رقم"), "supplier": ("Supplier", "المورّد"), "warranty_until": ("Date, e.g. 2028-03-31", "تاريخ مثل 2028-03-31"),
    "assigned_to": ("Employee number - the new asset is assigned to this employee", "الرقم الوظيفي - يُسلَّم الأصل الجديد لهذا الموظف"),
    "assigned_on": ("Handover date for assigned_to, e.g. 2025-03-31 or 31/3/2025 (empty = today; cannot be in the future)",
                    "تاريخ التسليم لـ assigned_to، مثل 2025-03-31 أو 31/3/2025 (فارغ = اليوم، ولا يكون في المستقبل)"),
}


def template(db, kind, lang):
    li = 1 if lang == "ar" else 0
    head = [_t(lang, "imp.col"), _t(lang, "imp.meaning")]
    if kind == "employees":
        help_rows = [head] + [[c + (" *" if c in REQUIRED else ""), HELP[c][li]] for c in EMP_COLS]
        return xlsx.write([{"name": _t(lang, "nav.employees"), "rows": [EMP_COLS], "rtl": lang == "ar"},
                           {"name": _t(lang, "imp.help"), "rows": help_rows, "rtl": lang == "ar", "widths": [22, 80]}])
    cats = inv.list_categories(db)
    custom = [k for k in _custom_keys(db) if k not in ASSET_COLS]
    help_rows = [head] + [[c + (" *" if c in REQUIRED else ""), HELP[c][li]] for c in ASSET_COLS]
    cat_rows = [[_t(lang, "cat.code"), _t(lang, "cat.name"), _t(lang, "imp.col"), _t(lang, "imp.field_label"),
                 _t(lang, "imp.field_type"), _t(lang, "imp.options"), _t(lang, "cat.required")]]
    for c in cats:
        nm = c["name_ar"] if lang == "ar" else c["name_en"]
        if not c["fields"]:
            cat_rows.append([c["code"], nm, "", "", "", "", ""])
        for f in c["fields"]:
            cat_rows.append([c["code"], nm, f["key"], f["label_ar"] if lang == "ar" else f["label_en"], _t(lang, "ft." + f["type"]),
                             ", ".join(f["options"]), _t(lang, "common.yes") if f["required"] else ""])
    return xlsx.write([{"name": _t(lang, "nav.assets"), "rows": [ASSET_COLS + custom], "rtl": lang == "ar"},
                       {"name": _t(lang, "imp.help"), "rows": help_rows, "rtl": lang == "ar", "widths": [22, 80]},
                       {"name": _t(lang, "nav.categories"), "rows": cat_rows, "rtl": lang == "ar"}])


# ------------------------------------------------------------------ exports
def _nm(r, base, lang):
    a, b = (r[base + "_ar"], r[base + "_en"]) if lang == "ar" else (r[base + "_en"], r[base + "_ar"])
    return a or b or ""


def export_assets(db, lang, q="", status="", category_id=None):
    custom = [k for k in _custom_keys(db) if k not in ASSET_COLS]
    head = ASSET_COLS[:-2] + ["status", "category", "holder_emp_no", "holder_name", "assigned_at", "expected_return"] + custom
    rows = [head]
    for a in inv.list_assets(db, q, status, category_id, 1, None)["assets"]:     # one query for every matching asset
        rows.append([a["cat_code"], a["tag"], a["name"], a["brand"], a["model"], a["serial_no"], _t(lang, "cond." + a["condition"]),
                     a["location"], a["purchase_date"], a["purchase_cost"], a["supplier"], a["warranty_until"], a["notes"],
                     _t(lang, "st." + a["status"]), _nm(a, "cat", lang), a["holder_no"] or "",
                     _nm(a, "holder", lang) if a["holder_id"] else "", (a["assigned_at"] or "")[:10], a["expected_return"] or ""]
                    + [_cell_out(a["custom"].get(k)) for k in custom])
    return xlsx.write([{"name": _t(lang, "nav.assets"), "rows": rows, "rtl": lang == "ar"}])


def _cell_out(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    return v


def export_employees(db, lang, q="", status="", department_id=None, with_nid=False):
    """The national ID column is only included for people allowed to see it (see inventory.can_see_national_id)."""
    cols = [c for c in EMP_COLS if with_nid or c != "national_id"]
    nid = {r["id"]: r["national_id"] for r in db.query("SELECT id, national_id FROM employees")} if with_nid else {}
    rows = [cols + ["holding"]]
    for e in inv.list_employees(db, q, status, department_id):
        val = {"department": _nm(e, "dept", lang) if e["dept_en"] else "", "national_id": nid.get(e["id"], "")}
        rows.append([val[c] if c in val else e[c] for c in cols] + [e["holding"]])
    return xlsx.write([{"name": _t(lang, "nav.employees"), "rows": rows, "rtl": lang == "ar"}])


def export_assignments(db, lang, open_only=False):
    rows = [["receipt_out_no", "tag", "asset", "emp_no", "employee", "department", "assigned_at", "expected_return",
             "condition_out", "notes_out", "returned_at", "receipt_in_no", "condition_in", "notes_in", "overdue"]]
    t = today_iso()
    for g in db.query("SELECT g.*, a.tag, a.name AS asset_name, e.emp_no, e.full_name_en, e.full_name_ar, d.name_en AS dept_en, d.name_ar AS dept_ar "
                      "FROM assignments g JOIN assets a ON a.id=g.asset_id JOIN employees e ON e.id=g.employee_id "
                      "LEFT JOIN departments d ON d.id=e.department_id " + ("WHERE g.returned_at IS NULL " if open_only else "") +
                      "ORDER BY g.id DESC"):
        overdue = not g["returned_at"] and g["expected_return"] and g["expected_return"] < t
        rows.append([g["receipt_out_no"], g["tag"], g["asset_name"], g["emp_no"], _nm(g, "full_name", lang),
                     _nm(g, "dept", lang) if g["dept_en"] else "", g["assigned_at"][:10], g["expected_return"],
                     _t(lang, "cond." + g["condition_out"]), g["notes_out"], (g["returned_at"] or "")[:10], g["receipt_in_no"] or "",
                     _t(lang, "cond." + g["condition_in"]) if g["condition_in"] else "", g["notes_in"], _t(lang, "common.yes") if overdue else ""])
    return xlsx.write([{"name": _t(lang, "nav.assignments"), "rows": rows, "rtl": lang == "ar"}])
