# -*- coding: utf-8 -*-
"""Excel import (employees, assets) and export (assets, employees, assignments).

Sheets do not have to follow the template: the header row is found even below title rows, any sheet (tab) can be
chosen, and each column of the file is matched to a field - suggested from common English/Arabic column names and
from earlier imports, then confirmed by the person (the "Match columns" step).

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
ASSET_IMPORT_EXTRA = ["holder_national_id"]                 # import only (not exported)
REQUIRED = {"emp_no", "category_code"}                       # an asset without a name gets one from its category
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


HEADER_SCAN = 15                                             # the header row is looked for in the first rows only
_NUMERIC = re.compile(r"[\d\s.,:/\-+]+")


def _header_index(rows):
    """The header is the first row that is about as wide as the table and mostly text - so a title, a logo row or
    a blank line above the real headers is skipped."""
    cand = rows[:HEADER_SCAN]
    counts = [sum(1 for v in r if _s(v)) for r in cand]
    widest = max(counts) if counts else 0
    if not widest:
        raise ApiError(400, "file_empty", "The file has no rows")
    need = max(2, int(widest * 0.6 + 0.5)) if widest > 1 else 1
    for i, r in enumerate(cand):
        filled = [v for v in r if _s(v)]
        texts = [v for v in filled if isinstance(v, str) and not _NUMERIC.fullmatch(v)]
        if len(filled) >= need and len(texts) * 10 >= len(filled) * 6:
            return i
    return next(i for i, c in enumerate(counts) if c)


def _parse(data, filename, sheet=0):
    """-> (raw header texts, data rows, number of the first data row as Excel shows it, sheet names)."""
    if data[:4] == b"PK\x03\x04":
        rows, sheets = xlsx.read(data, sheet), xlsx.sheet_names(data)
    elif (filename or "").lower().endswith(".csv") or b"," in data[:2000] or b";" in data[:2000]:
        rows, sheets = xlsx.read_csv(data), []
    else:
        raise ApiError(400, "file_unreadable", "Use an Excel (.xlsx) or CSV file")
    if not any(any(_s(v) for v in r) for r in rows):
        raise ApiError(400, "file_empty", "The file has no rows")
    hi = _header_index(rows)
    return [_s(h) for h in rows[hi]], rows[hi + 1:], hi + 2, sheets


def _key(h):
    return re.sub(r"[\s*]+$", "", h).strip().lower()


def _map(header, known, mapping=None, required=REQUIRED):
    """Column index for each field. Without `mapping` the file must use the template's column names; with it,
    `mapping` is {column index: field} as chosen in the Match columns step (columns left out are skipped)."""
    idx, ignored = {}, []
    if mapping is None:
        for i, h in enumerate(header):
            k = _key(h)
            if not k:
                continue
            if k in known and k not in idx:
                idx[k] = i
            else:
                ignored.append(h)
    else:
        if not isinstance(mapping, dict) or len(mapping) > 500:
            raise ApiError(400, "bad_request", "Bad request")
        for col, field in mapping.items():
            if not str(col).isdigit() or not isinstance(field, str) or int(col) >= len(header):
                raise ApiError(400, "bad_request", "Bad request")
            if not field:
                continue
            if field not in known:
                raise ApiError(422, "mapping_unknown_field", "Unknown field: " + field[:40], field=field[:40])
            if field in idx:
                raise ApiError(422, "mapping_duplicate", "Two columns go to the same field: " + field, columns=[field])
            idx[field] = int(col)
        ignored = [h for i, h in enumerate(header) if _s(h) and i not in idx.values()]
    missing = [c for c in known if c in required and c not in idx]
    if missing:
        raise ApiError(422, "missing_columns", "Required columns are missing: " + ", ".join(missing), columns=missing)
    return idx, ignored


# ------------------------------------------------------------------ column matching (suggestions)
_AR_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي", "ـ": None})


def _norm(s):
    """'Serial No.' / 'serial_no' / 'SERIAL NO' -> 'serialno'; Arabic letter forms and diacritics folded."""
    s = re.sub(r"[\u064B-\u0652\u0670]", "", str(s or "")).translate(_AR_FOLD).lower()
    return re.sub(r"[^0-9a-z\u0621-\u064a]+", "", s)


# Common column names people use, English and Arabic. The field's own label in the app is added automatically.
SYNONYMS = {
    "emp_no": ["emp no", "employee no", "employee number", "employee id", "emp id", "emp code", "employee code", "staff id",
               "staff no", "staff number", "hr code", "hr id", "personnel no", "code", "الرقم الوظيفي", "رقم وظيفي",
               "رقم الموظف", "كود الموظف", "الكود", "كود", "الرقم الوظيفى"],
    "full_name_en": ["name", "full name", "employee name", "english name", "name en", "name english", "staff name",
                     "الاسم بالانجليزية", "الاسم بالانجليزي", "الاسم انجليزي"],
    "full_name_ar": ["arabic name", "name ar", "name arabic", "الاسم", "اسم الموظف", "الاسم بالعربية", "الاسم بالعربي",
                     "الاسم عربي", "الاسم الكامل", "اسم الموظف بالعربي"],
    "department": ["department", "dept", "section", "division", "administration", "unit", "الادارة", "القسم", "ادارة",
                   "الاداره", "قسم"],
    "job_title": ["job", "job title", "title", "position", "designation", "role", "occupation", "الوظيفة", "المسمى الوظيفي",
                  "المسمى", "الوظيفه", "المنصب"],
    "email": ["email", "e mail", "mail", "email address", "work email", "البريد", "البريد الالكتروني", "الايميل", "ايميل"],
    "phone": ["phone", "mobile", "mobile no", "mobile number", "phone number", "phone no", "tel", "telephone", "cell",
              "contact", "الهاتف", "الموبايل", "رقم الهاتف", "رقم الموبايل", "تليفون", "التليفون", "المحمول", "الجوال", "موبايل"],
    "national_id": ["national id", "nid", "id number", "national number", "national no", "civil id", "ssn",
                    "الرقم القومي", "رقم قومي", "الرقم القومى", "رقم البطاقة", "البطاقة", "رقم الهوية"],
    "status": ["status", "employment status", "الحالة", "الحاله"],
    "notes": ["notes", "note", "remarks", "remark", "comments", "comment", "ملاحظات", "ملاحظة", "ملاحظه"],
    "category_code": ["category", "category code", "type", "asset type", "device type", "item type", "class", "kind",
                      "التصنيف", "الفئة", "النوع", "نوع الجهاز", "نوع الاصل", "الفئه"],
    "tag": ["tag", "asset tag", "asset no", "asset number", "asset code", "asset id", "inventory no", "inventory number",
            "رمز الاصل", "رقم الاصل", "كود الاصل", "رقم الجرد"],
    "name": ["name", "asset", "asset name", "description", "item", "item name", "device", "device name", "product",
             "اسم الاصل", "الوصف", "البيان", "الصنف", "الجهاز", "اسم الجهاز", "اسم الصنف"],
    "brand": ["brand", "make", "manufacturer", "الماركة", "ماركة", "الشركة المصنعة", "الماركه"],
    "model": ["model", "model no", "model number", "الموديل", "موديل"],
    "serial_no": ["serial", "serial no", "serial number", "s n", "sn", "service tag", "الرقم التسلسلي", "السيريال",
                  "سيريال", "رقم السيريال", "الرقم المسلسل"],
    "condition": ["condition", "device condition", "state", "الحالة الفنية", "حالة الجهاز", "الحالة", "الحاله"],
    "location": ["location", "site", "place", "office", "branch", "building", "floor", "الموقع", "المكان", "الفرع", "المبنى"],
    "purchase_date": ["purchase date", "date of purchase", "bought on", "purchased", "purchase", "invoice date",
                      "تاريخ الشراء", "تاريخ الفاتورة"],
    "purchase_cost": ["cost", "price", "purchase cost", "purchase price", "value", "amount", "التكلفة", "السعر", "القيمة",
                      "سعر الشراء", "التكلفه", "القيمه"],
    "supplier": ["supplier", "vendor", "seller", "المورد", "المورّد", "البائع"],
    "warranty_until": ["warranty", "warranty until", "warranty end", "warranty expiry", "warranty date", "الضمان",
                       "نهاية الضمان", "تاريخ انتهاء الضمان", "انتهاء الضمان"],
    "assigned_to": ["assigned to", "holder", "user", "employee", "custodian", "received by", "receiver", "owner",
                    "employee name", "employee no", "staff", "used by", "المستلم", "الموظف", "المستخدم", "اسم المستلم",
                    "العهدة", "مستلم العهدة", "اسم الموظف", "صاحب العهدة"],
    "holder_national_id": ["national id", "nid", "id number", "national number", "national no", "civil id",
                           "holder national id", "employee national id", "الرقم القومي", "رقم قومي", "رقم البطاقة",
                           "البطاقة", "رقم الهوية", "الرقم القومي للمستلم"],
    "assigned_on": ["assigned on", "handover date", "assignment date", "date assigned", "issue date", "delivery date",
                    "received on", "date", "تاريخ التسليم", "تاريخ الاستلام", "تاريخ العهدة"],
}
FIELD_LABEL = {"emp_no": "emp.no", "full_name_en": "emp.name_en", "full_name_ar": "emp.name_ar", "department": "emp.department",
               "job_title": "emp.job", "email": "users.email", "phone": "emp.phone", "national_id": "emp.national_id",
               "status": "users.status", "notes": "assets.notes", "category_code": "assets.category", "tag": "assets.tag",
               "name": "assets.name", "brand": "assets.brand", "model": "assets.model", "serial_no": "assets.serial",
               "condition": "assets.condition", "location": "assets.location", "purchase_date": "assets.purchase_date",
               "purchase_cost": "assets.cost", "supplier": "assets.supplier", "warranty_until": "assets.warranty",
               "assigned_to": "imp.f_assigned_to", "assigned_on": "imp.f_assigned_on", "holder_national_id": "imp.f_holder_nid"}
_ARABIC = re.compile(r"[\u0600-\u06ff]")


def _fields(db, kind):
    """The fields a column can go to: [{key, label_en, label_ar, required}]."""
    if kind == "employees":
        cols = [(c, None) for c in EMP_COLS]
    else:
        cols = [(c, None) for c in ASSET_COLS + ASSET_IMPORT_EXTRA]
        seen = set(ASSET_COLS + ASSET_IMPORT_EXTRA)
        for cat in inv.list_categories(db):
            for f in cat["fields"]:
                if f["key"] not in seen:
                    seen.add(f["key"])
                    cols.append((f["key"], (f, cat)))
    out = []
    for key, extra in cols:
        if extra:
            f, cat = extra
            en = "%s (%s)" % (f["label_en"] or f["label_ar"] or key, cat["name_en"] or cat["name_ar"])
            ar = "%s (%s)" % (f["label_ar"] or f["label_en"] or key, cat["name_ar"] or cat["name_en"])
            out.append({"key": key, "label_en": en, "label_ar": ar, "required": False, "custom": True,
                        "names": [key, f["label_en"], f["label_ar"]]})
        else:
            lk = FIELD_LABEL.get(key, key)
            out.append({"key": key, "label_en": _t("en", lk), "label_ar": _t("ar", lk), "required": key in REQUIRED,
                        "custom": False, "names": [key, _t("en", lk), _t("ar", lk)] + SYNONYMS.get(key, [])})
    return out


def _layout(db, kind, value=None):
    from . import notify
    return notify._state(db, "import_layout_" + kind, value) if value is not None else (notify._state(db, "import_layout_" + kind) or {})


def remember_layout(db, kind, header, mapping):
    """After a successful import: remember which field each column name went to (or that it was skipped)."""
    lay = _layout(db, kind)
    for col, field in mapping.items():
        n = _norm(header[int(col)]) if str(col).isdigit() and int(col) < len(header) else ""
        if n:
            lay[n] = field or ""
    if len(lay) > 1000:
        lay = dict(list(lay.items())[-1000:])
    _layout(db, kind, lay)


def suggest(db, kind, header, rows):
    """Best guess for each column: what was chosen for this column name before, then an exact name match,
    then a partial one ('Laptop Serial No' -> serial number). Each field is used once."""
    fields = _fields(db, kind)
    keys = {f["key"] for f in fields}
    names = [(f["key"], _norm(n)) for f in fields for n in f["names"] if _norm(n)]
    lay = _layout(db, kind)
    out, used = [""] * len(header), set()

    def take(i, key):
        if key and key in keys and key not in used:
            out[i] = key
            used.add(key)
            return True
        return False

    norms = [_norm(h) for h in header]
    for i, n in enumerate(norms):                                   # 1. remembered from earlier imports
        if n and n in lay:
            out[i] = lay[n] if lay[n] in keys and lay[n] not in used else ""
            if out[i]:
                used.add(out[i])
    done = {i for i, n in enumerate(norms) if n in lay}
    for i, n in enumerate(norms):                                   # 2. exact name
        if n and i not in done and not out[i]:
            for key, nm in names:
                if nm == n and take(i, key):
                    break
    for i, n in enumerate(norms):                                   # 3. partial name, longest match wins
        if n and i not in done and not out[i] and len(n) >= 3:
            best = sorted(((len(nm), key) for key, nm in names if len(nm) >= 4 and (nm in n or (len(n) >= 4 and n in nm))),
                          reverse=True)
            for _, key in best:
                if take(i, key):
                    break
    if kind == "employees":                                         # a "Name" column written in Arabic is the Arabic name
        for i, key in enumerate(out):
            if key == "full_name_en" and "full_name_ar" not in used:
                vals = [_s(r[i]) for r in rows[:20] if i < len(r) and _s(r[i])]
                if vals and sum(1 for v in vals if _ARABIC.search(v)) * 2 > len(vals):
                    out[i] = "full_name_ar"
                    used.discard("full_name_en"); used.add("full_name_ar")
    return out


def columns(ctx, kind, data, filename, sheet=0):
    """The Match columns step: the file's columns with sample values and a suggested field for each."""
    header, rows, first, sheets = _parse(data, filename, sheet)
    sug = suggest(ctx.db, kind, header, rows)
    cols = []
    for i, h in enumerate(header):
        samples = []
        for r in rows:
            v = _s(r[i]) if i < len(r) else ""
            if v and v not in samples:
                samples.append(v[:60])
            if len(samples) == 3:
                break
        if h or samples:
            cols.append({"index": i, "header": h[:80], "samples": samples, "suggested": sug[i]})
    fields = [{k: f[k] for k in ("key", "label_en", "label_ar", "required", "custom")} for f in _fields(ctx.db, kind)]
    return {"sheets": sheets, "sheet": sheet, "header_row": first - 1, "rows": sum(1 for r in rows if any(_s(v) for v in r)),
            "columns": cols, "fields": fields}


FIELD_TO_COL = {"department_id": "department", "category_id": "category_code", "employee_id": "assigned_to"}


class _Rollback(Exception):
    pass


def _run(ctx, rows, dry_run, handle_row, first_row=2):
    db = ctx.db
    result = {"total": 0, "created": 0, "updated": 0, "errors": [], "error_count": 0, "committed": False}
    try:
        with db.tx():
            for n, row in enumerate(rows, start=first_row):         # row numbers as Excel shows them
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
def import_employees(ctx, data, filename, dry_run=True, update=False, mapping=None, sheet=0):
    header, rows, first, _ = _parse(data, filename, sheet)
    idx, ignored = _map(header, EMP_COLS, mapping)
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
    res = _run(ctx, rows, dry_run, handle, first)
    if res["committed"] and mapping is not None:
        remember_layout(db, "employees", header, mapping)
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


def _next_emp_no(db):
    """Continue the company's own numbering (NDS-040 -> NDS-041); EMP-0001 when there is none yet."""
    best = {}
    for r in db.query("SELECT id, emp_no FROM employees ORDER BY id"):
        m = re.fullmatch(r"(.*?)(\d+)", r["emp_no"])
        if m:
            p, n = m.group(1), m.group(2)
            cnt, top, width, _ = best.get(p, (0, 0, len(n), 0))
            best[p] = (cnt + 1, max(top, int(n)), max(width, len(n)), r["id"])
    if not best:
        prefix, top, width = "EMP-", 0, 4
    else:                                                    # the most used numbering; on a tie, the latest one
        prefix, (_, top, width, _) = max(best.items(), key=lambda kv: (kv[1][0], kv[1][3]))
    n = top + 1
    while db.one("SELECT 1 FROM employees WHERE emp_no=?", ("%s%0*d" % (prefix, width, n),)):
        n += 1
    return "%s%0*d" % (prefix, width, n)


def import_assets(ctx, data, filename, dry_run=True, update=False, mapping=None, sheet=0, default_category="", add_people=False):
    db = ctx.db
    header, rows, first, _ = _parse(data, filename, sheet)
    custom_keys = [k for k in _custom_keys(db) if k not in ASSET_COLS]
    cats = {c["code"]: c for c in inv.list_categories(db)}
    default_category = (default_category or "").strip().upper()
    if default_category and default_category not in cats:
        raise ApiError(422, "category_not_found", "Unknown category code", field="category_code")
    idx, ignored = _map(header, ASSET_COLS + ASSET_IMPORT_EXTRA + custom_keys, mapping,
                        REQUIRED - {"category_code"} if default_category else REQUIRED)
    cat_names = {}                                        # the category column may hold a code or a name (English/Arabic)
    for c in cats.values():
        for n in (c["code"], c["name_en"], c["name_ar"]):
            if _norm(n):
                cat_names.setdefault(_norm(n), c)
    cond_map = _reverse("cond.", inv.CONDITIONS)
    people, added = {}, []

    def holder_id(v, nid=""):
        """Find the holder by national ID, employee number or full name (English or Arabic). With add_people, someone
        who is not in the system yet is added from the name and national ID in the sheet."""
        if nid:
            e = db.one("SELECT id FROM employees WHERE national_id=?", (nid,))
            if e:
                return e["id"]
        if not v:
            if nid and not add_people:
                raise ApiError(422, "employee_nid_not_found", "No employee has this national ID", field="holder_national_id")
            raise ApiError(422, "field_required", "Give the holder's name for a new employee", field="assigned_to")
        e = db.one("SELECT id FROM employees WHERE emp_no=?", (v,))
        if e:
            return e["id"]
        if not people:
            for r in db.query("SELECT id, full_name_en, full_name_ar FROM employees"):
                for n in {_norm(r["full_name_en"]), _norm(r["full_name_ar"])}:
                    if n:
                        people.setdefault(n, set()).add(r["id"])
            people.setdefault("", set())
        ids = people.get(_norm(v), set())
        if len(ids) > 1:
            raise ApiError(422, "employee_ambiguous", "More than one employee has this name - use the employee number", field="assigned_to")
        if not ids:
            if not add_people:
                raise ApiError(422, "employee_not_found", "No employee with this number or name", field="assigned_to")
            arabic = bool(_ARABIC.search(v))
            eid = inv.save_employee(ctx, None, {"emp_no": _next_emp_no(db), "full_name_en": "" if arabic else v,
                                                "full_name_ar": v if arabic else "", "national_id": nid, "status": "active"})
            people.setdefault(_norm(v), set()).add(eid)
            added.append(v)
            return eid
        return next(iter(ids))

    def auto_name(cat, body):
        """'Mobile lines 01026261465': the category name and what identifies the item (serial, or a unique field)."""
        ident = body.get("serial_no") or ""
        for f in sorted(cat["fields"], key=lambda f: not f.get("unique")):
            if not ident and _s(body["custom"].get(f["key"])):
                ident = _s(body["custom"].get(f["key"]))
        base = cat["name_en"] or cat["name_ar"] or cat["code"]
        return (base + " " + ident).strip()[:200]

    def handle(row):
        cell = lambda c: _s(row[idx[c]]) if c in idx and idx[c] < len(row) else None
        raw = lambda c: row[idx[c]] if c in idx and idx[c] < len(row) else None
        code = (cell("category_code") or "").strip()
        if not code and not default_category:
            raise ApiError(422, "field_required", "category_code is required", field="category_code")
        cat = (cats.get(code.upper()) or cat_names.get(_norm(code))) if code else cats[default_category]
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
        if not _s(body.get("name")):
            body["name"] = auto_name(cat, body)
        if old:
            inv.update_asset(ctx, old["id"], body)
            return "updated"
        holder, nid = cell("assigned_to") or "", ""
        if cell("holder_national_id"):
            try:
                nid = inv.national_id({"national_id": cell("holder_national_id")})
            except ApiError as e:
                raise ApiError(e.status, e.code, e.message, field="holder_national_id")
        aid, _ = inv.create_asset(ctx, body)
        if holder or nid:
            inv.assign(ctx, aid, {"employee_id": holder_id(holder, nid)}, at=_date(raw("assigned_on")) or None)
        elif cell("assigned_on"):
            raise ApiError(422, "field_required", "assigned_on needs assigned_to", field="assigned_to")
        return "created"
    handle.kind = "assets"
    res = _run(ctx, rows, dry_run, handle, first)
    if res["committed"] and mapping is not None:
        remember_layout(db, "assets", header, mapping)
    res["ignored_columns"] = ignored
    res["employees_created"] = sorted(set(added))
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
    "name": ("Asset name / description - empty: category name + serial number", "اسم الأصل / الوصف - فارغ: اسم التصنيف + الرقم التسلسلي"),
    "brand": ("Brand", "الماركة"), "model": ("Model", "الموديل"), "serial_no": ("Serial number - must be unique", "الرقم التسلسلي - يجب أن يكون فريداً"),
    "condition": ("new, good, fair, poor or damaged (empty = good)", "new أو good أو fair أو poor أو damaged (فارغ = جيد)"),
    "location": ("Location", "الموقع"), "purchase_date": ("Date, e.g. 2026-03-31", "تاريخ مثل 2026-03-31"),
    "purchase_cost": ("Number", "رقم"), "supplier": ("Supplier", "المورّد"), "warranty_until": ("Date, e.g. 2028-03-31", "تاريخ مثل 2028-03-31"),
    "assigned_to": ("Employee number - the new asset is assigned to this employee", "الرقم الوظيفي - يُسلَّم الأصل الجديد لهذا الموظف"),
    "holder_national_id": ("National ID of the holder - finds the employee (or, with 'add employees', creates them)",
                           "الرقم القومي للمستلم - للعثور على الموظف (أو إضافته عند اختيار «إضافة الموظفين»)"),
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
    help_rows = [head] + [[c + (" *" if c in REQUIRED else ""), HELP[c][li]] for c in ASSET_COLS + ASSET_IMPORT_EXTRA]
    cat_rows = [[_t(lang, "cat.code"), _t(lang, "cat.name"), _t(lang, "imp.col"), _t(lang, "imp.field_label"),
                 _t(lang, "imp.field_type"), _t(lang, "imp.options"), _t(lang, "cat.required")]]
    for c in cats:
        nm = c["name_ar"] if lang == "ar" else c["name_en"]
        if not c["fields"]:
            cat_rows.append([c["code"], nm, "", "", "", "", ""])
        for f in c["fields"]:
            cat_rows.append([c["code"], nm, f["key"], f["label_ar"] if lang == "ar" else f["label_en"], _t(lang, "ft." + f["type"]),
                             ", ".join(f["options"]), _t(lang, "common.yes") if f["required"] else ""])
    return xlsx.write([{"name": _t(lang, "nav.assets"), "rows": [ASSET_COLS + ASSET_IMPORT_EXTRA + custom], "rtl": lang == "ar"},
                       {"name": _t(lang, "imp.help"), "rows": help_rows, "rtl": lang == "ar", "widths": [22, 80]},
                       {"name": _t(lang, "nav.categories"), "rows": cat_rows, "rtl": lang == "ar"}])


# ------------------------------------------------------------------ exports
def _nm(r, base, lang):
    a, b = (r[base + "_ar"], r[base + "_en"]) if lang == "ar" else (r[base + "_en"], r[base + "_ar"])
    return a or b or ""


def export_assets(db, lang, q="", status="", category_id=None, sort="newest"):
    custom = [k for k in _custom_keys(db) if k not in ASSET_COLS]
    head = ASSET_COLS[:-2] + ["status", "category", "holder_emp_no", "holder_name", "assigned_at", "expected_return"] + custom
    rows = [head]
    for a in inv.list_assets(db, q, status, category_id, 1, None, sort)["assets"]:     # one query for every matching asset
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
