# -*- coding: utf-8 -*-
"""Assets, categories (with custom fields), departments, employees and assignments.

Rules that keep the data trustworthy:
- an asset has at most one open assignment (also enforced by a unique index);
- an asset's status 'assigned' is only ever set by assign() and cleared by return_asset();
- anything with history is never deleted - assets are retired, employees are marked as left;
- every change is written to the audit log inside the same transaction."""
import re
import json

from .errors import ApiError
from .util import now_iso, today_iso, text, choice, date_field, number, ref_id

STATUSES = ("in_stock", "assigned", "maintenance", "retired", "lost")
MANUAL_STATUSES = ("in_stock", "maintenance", "retired", "lost")      # 'assigned' only via assign()
CONDITIONS = ("new", "good", "fair", "poor", "damaged")
FIELD_TYPES = ("text", "number", "date", "select", "bool")
MAX_FIELDS = 30


def _bi(d, key_en, key_ar, maxlen, err_code, field=None):
    """Bilingual name: at least one language required, the other falls back to it."""
    en = text(d, key_en, maxlen=maxlen, required=False)
    ar = text(d, key_ar, maxlen=maxlen, required=False)
    if not en and not ar:
        raise ApiError(422, err_code, "Enter the name in English or Arabic", field=field or key_en)
    return en or ar, ar or en


# ================================================================ categories
def _fields_of(db, cid):
    out = []
    for r in db.query("SELECT * FROM category_fields WHERE category_id=? ORDER BY sort, id", (cid,)):
        d = dict(r)
        d["options"] = json.loads(d["options"] or "[]")
        d["required"] = bool(d["required"])
        d["unique"] = bool(d.pop("unique_value", 0))
        out.append(d)
    return out


def list_categories(db):
    rows = db.query("SELECT c.*, (SELECT COUNT(*) FROM assets a WHERE a.category_id=c.id) AS assets "
                    "FROM categories c ORDER BY c.name_en COLLATE NOCASE")
    return [dict(r, fields=_fields_of(db, r["id"])) for r in rows]


def _validate_fields(raw):
    if not isinstance(raw, list):
        raise ApiError(422, "invalid_field", "Invalid custom fields", field="fields")
    if len(raw) > MAX_FIELDS:
        raise ApiError(422, "too_many_fields", "Too many custom fields", field="fields")
    out, keys = [], set()
    for i, f in enumerate(raw):
        if not isinstance(f, dict):
            raise ApiError(422, "invalid_field", "Invalid custom fields", field="fields")
        label_en, label_ar = _bi(f, "label_en", "label_ar", 60, "field_label_required", field="fields")
        ftype = choice(f, "type", FIELD_TYPES, "text")
        opts = []
        if ftype == "select":
            raw_opts = f.get("options") or []
            if not isinstance(raw_opts, list):
                raise ApiError(422, "invalid_field", "Invalid options", field="fields")
            for o in raw_opts:
                if not isinstance(o, str):
                    raise ApiError(422, "invalid_field", "Invalid options", field="fields")
                o = o.strip()[:80]
                if o and o not in opts:
                    opts.append(o)
            if not opts:
                raise ApiError(422, "select_needs_options", "A list field needs at least one option", field="fields")
        key = f.get("key") if isinstance(f.get("key"), str) and re.fullmatch(r"[a-z][a-z0-9_]{0,39}", f.get("key") or "") else None
        if not key:
            base = re.sub(r"[^a-z0-9]+", "_", label_en.lower()).strip("_")[:30]
            key = ("f_" + base) if not base or not base[0].isalpha() else base
            key = key or "field"
        k, n = key, 1
        while k in keys:
            n += 1
            k = "%s_%d" % (key, n)
        keys.add(k)
        out.append({"key": k, "label_en": label_en, "label_ar": label_ar, "type": ftype, "options": opts,
                    "required": bool(f.get("required")), "unique": bool(f.get("unique")) and ftype in ("text", "number"), "sort": i})
    return out


def _category_values(db, d, cid=None):
    name_en, name_ar = _bi(d, "name_en", "name_ar", 80, "category_name_required")
    code = text(d, "code", maxlen=8).upper()
    if not re.fullmatch(r"[A-Z0-9]{2,8}", code):
        raise ApiError(422, "category_code_invalid", "Use 2-8 letters or digits", field="code")
    clash = db.one("SELECT id FROM categories WHERE code=?", (code,))
    if clash and clash["id"] != cid:
        raise ApiError(409, "category_code_taken", "Another category already uses this code", field="code")
    life = number(d, "useful_life_years", minimum=0, maximum=100)
    if life is not None and not float(life).is_integer():
        raise ApiError(422, "invalid_number", "Enter whole years", field="useful_life_years")
    return {"name_en": name_en, "name_ar": name_ar, "code": code,
            "description": text(d, "description", maxlen=300, required=False),
            "useful_life_years": int(life or 0),
            "fields": _validate_fields(d.get("fields", []))}


def _write_fields(db, cid, fields):
    db.execute("DELETE FROM category_fields WHERE category_id=?", (cid,))
    for f in fields:
        db.execute("INSERT INTO category_fields(category_id,key,label_en,label_ar,type,options,required,sort,unique_value) VALUES (?,?,?,?,?,?,?,?,?)",
                   (cid, f["key"], f["label_en"], f["label_ar"], f["type"], json.dumps(f["options"], ensure_ascii=False),
                    1 if f["required"] else 0, f["sort"], 1 if f["unique"] else 0))
        if f["unique"]:                                       # switching "unique" on must not leave existing duplicates
            dup = db.one("SELECT json_extract(custom, '$.' || ?) v, COUNT(*) n FROM assets WHERE category_id=? "
                         "AND COALESCE(json_extract(custom, '$.' || ?), '') <> '' GROUP BY v HAVING n > 1 LIMIT 1",
                         (f["key"], cid, f["key"]))
            if dup:
                raise ApiError(409, "field_values_not_unique", "Some assets already share a value in this field",
                               field="fields", label=f["label_en"], value=str(dup["v"])[:80], count=dup["n"])


def _unique_clash(db, cid, fields, custom, aid):
    for f in fields:
        v = custom.get(f["key"])
        if f.get("unique") and v not in (None, ""):
            r = db.one("SELECT id, tag FROM assets WHERE category_id=? AND json_extract(custom, '$.' || ?)=? AND id<>?",
                       (cid, f["key"], v, aid or 0))
            if r:
                raise ApiError(409, "custom_value_taken", "Another asset already has this value", field="custom." + f["key"], tag=r["tag"])


def create_category(ctx, d):
    db = ctx.db
    with db.tx():
        v = _category_values(db, d)
        ts = now_iso()
        cur = db.execute("INSERT INTO categories(code,name_en,name_ar,description,useful_life_years,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                         (v["code"], v["name_en"], v["name_ar"], v["description"], v["useful_life_years"], ts, ts))
        _write_fields(db, cur.lastrowid, v["fields"])
        ctx.audit("category.create", "category", cur.lastrowid, {"code": v["code"], "name": v["name_en"], "fields": [f["key"] for f in v["fields"]]})
    return cur.lastrowid


def update_category(ctx, cid, d):
    db = ctx.db
    with db.tx():
        old = db.one("SELECT * FROM categories WHERE id=?", (cid,))
        if old is None:
            raise ApiError(404, "category_not_found", "Category not found")
        v = _category_values(db, d, cid)      # a new code only affects tags generated from now on
        db.execute("UPDATE categories SET code=?,name_en=?,name_ar=?,description=?,useful_life_years=?,updated_at=? WHERE id=?",
                   (v["code"], v["name_en"], v["name_ar"], v["description"], v["useful_life_years"], now_iso(), cid))
        _write_fields(db, cid, v["fields"])
        ctx.audit("category.update", "category", cid, {"code": v["code"], "name": v["name_en"], "fields": [f["key"] for f in v["fields"]]})


def delete_category(ctx, cid):
    db = ctx.db
    with db.tx():
        old = db.one("SELECT * FROM categories WHERE id=?", (cid,))
        if old is None:
            raise ApiError(404, "category_not_found", "Category not found")
        if db.one("SELECT 1 FROM assets WHERE category_id=?", (cid,)):
            raise ApiError(409, "category_in_use", "Move or delete the assets of this category first")
        db.execute("DELETE FROM categories WHERE id=?", (cid,))
        ctx.audit("category.delete", "category", cid, {"code": old["code"], "name": old["name_en"]})


# ================================================================ departments
def list_departments(db):
    return [dict(r) for r in db.query(
        "SELECT d.*, (SELECT COUNT(*) FROM employees e WHERE e.department_id=d.id) AS employees "
        "FROM departments d ORDER BY d.name_en COLLATE NOCASE")]


def save_department(ctx, did, d):
    db = ctx.db
    name_en, name_ar = _bi(d, "name_en", "name_ar", 80, "department_name_required")
    with db.tx():
        if did is None:
            cur = db.execute("INSERT INTO departments(name_en,name_ar,created_at) VALUES (?,?,?)", (name_en, name_ar, now_iso()))
            did = cur.lastrowid
            ctx.audit("department.create", "department", did, {"name": name_en})
        else:
            if db.one("SELECT 1 FROM departments WHERE id=?", (did,)) is None:
                raise ApiError(404, "department_not_found", "Department not found")
            db.execute("UPDATE departments SET name_en=?, name_ar=? WHERE id=?", (name_en, name_ar, did))
            ctx.audit("department.update", "department", did, {"name": name_en})
    return did


def delete_department(ctx, did):
    db = ctx.db
    with db.tx():
        old = db.one("SELECT * FROM departments WHERE id=?", (did,))
        if old is None:
            raise ApiError(404, "department_not_found", "Department not found")
        if db.one("SELECT 1 FROM employees WHERE department_id=?", (did,)):
            raise ApiError(409, "department_in_use", "Move the employees of this department first")
        db.execute("DELETE FROM departments WHERE id=?", (did,))
        ctx.audit("department.delete", "department", did, {"name": old["name_en"]})


# ================================================================ employees
EMP_SELECT = ("SELECT e.*, d.name_en AS dept_en, d.name_ar AS dept_ar, "
              "(SELECT COUNT(*) FROM assignments x WHERE x.employee_id=e.id AND x.returned_at IS NULL) AS holding "
              "FROM employees e LEFT JOIN departments d ON d.id=e.department_id")


def _like(q):
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


# ---- national ID (personal data): full value only for people who manage employees or hand over assets
NID_PERMS = ("employees.manage", "assignments.manage")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def can_see_national_id(db, user):
    from . import rbac
    return bool(user) and any(rbac.user_has(db, user, p) for p in NID_PERMS)


def mask_national_id(v):
    v = v or ""
    return ("•" * (len(v) - 4) + v[-4:]) if len(v) > 4 else ("•" * len(v))


def _nid_view(row, full):
    """Replace the national ID in an employee dict according to the reader's rights."""
    v = row.get("national_id") or ""
    row["national_id"] = v if full else mask_national_id(v)
    row["national_id_masked"] = bool(v) and not full
    return row


def national_id(d, key="national_id"):
    """Arabic or Western digits, spaces and dashes allowed. Egyptian 14-digit numbers are checked (century, month, day);
    other countries / passport numbers: 5-20 letters or digits."""
    v = text(d, key, maxlen=40, required=False).translate(_DIGITS)
    v = re.sub(r"[\s\-_/.]", "", v).upper()
    if not v:
        return ""
    if not re.fullmatch(r"[A-Z0-9]{5,20}", v):
        raise ApiError(422, "national_id_invalid", "Use 5-20 letters or digits", field=key)
    if len(v) == 14 and v.isdigit():
        century, mm, dd = v[0], int(v[3:5]), int(v[5:7])
        if century not in "23" or not 1 <= mm <= 12 or not 1 <= dd <= 31:
            raise ApiError(422, "national_id_invalid_eg", "This is not a valid Egyptian national ID", field=key)
    return v


def list_employees(db, q="", status="", department_id=None):
    where, params = [], []
    if q:
        where.append("(e.emp_no LIKE ? ESCAPE '\\' OR e.full_name_en LIKE ? ESCAPE '\\' OR e.full_name_ar LIKE ? ESCAPE '\\' "
                     "OR e.email LIKE ? ESCAPE '\\' OR e.job_title LIKE ? ESCAPE '\\')")
        params += [_like(q)] * 5
    if status in ("active", "left"):
        where.append("e.status=?")
        params.append(status)
    if department_id:
        where.append("e.department_id=?")
        params.append(department_id)
    w = (" WHERE " + " AND ".join(where)) if where else ""
    out = []
    for r in db.query(EMP_SELECT + w + " ORDER BY e.full_name_en COLLATE NOCASE LIMIT 2000", params):
        x = dict(r)
        x["has_national_id"] = bool(x.pop("national_id", ""))        # lists never carry the number itself
        out.append(x)
    return out


def lookup_employees(db, q=""):
    """Small list of active employees for pickers (assign dialog)."""
    where, params = "WHERE e.status='active'", []
    if q:
        where += " AND (e.emp_no LIKE ? ESCAPE '\\' OR e.full_name_en LIKE ? ESCAPE '\\' OR e.full_name_ar LIKE ? ESCAPE '\\')"
        params = [_like(q)] * 3
    return [{"id": r["id"], "emp_no": r["emp_no"], "full_name_en": r["full_name_en"], "full_name_ar": r["full_name_ar"],
             "dept_en": r["dept_en"], "dept_ar": r["dept_ar"]}
            for r in db.query(EMP_SELECT + " " + where + " ORDER BY e.full_name_en COLLATE NOCASE LIMIT 50", params)]


def get_employee(db, eid, full_nid=False):
    r = db.one(EMP_SELECT + " WHERE e.id=?", (eid,))
    if r is None:
        raise ApiError(404, "employee_not_found", "Employee not found")
    out = _nid_view(dict(r), full_nid)
    out["assignments"] = [dict(x) for x in db.query(
        "SELECT g.*, a.tag, a.name AS asset_name, a.status AS asset_status, c.name_en AS cat_en, c.name_ar AS cat_ar "
        "FROM assignments g JOIN assets a ON a.id=g.asset_id JOIN categories c ON c.id=a.category_id "
        "WHERE g.employee_id=? ORDER BY g.returned_at IS NOT NULL, g.id DESC", (eid,))]
    return out


def _employee_values(db, d, eid=None):
    emp_no = text(d, "emp_no", maxlen=30)
    clash = db.one("SELECT id FROM employees WHERE emp_no=?", (emp_no,))
    if clash and clash["id"] != eid:
        raise ApiError(409, "employee_no_taken", "Another employee has this number", field="emp_no")
    en, ar = _bi(d, "full_name_en", "full_name_ar", 120, "employee_name_required")
    dept = ref_id(d, "department_id", required=False)
    if dept and db.one("SELECT 1 FROM departments WHERE id=?", (dept,)) is None:
        raise ApiError(422, "department_not_found", "Department not found", field="department_id")
    email = text(d, "email", maxlen=120, required=False)
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ApiError(422, "invalid_email", "Enter a valid email address", field="email")
    if "national_id" in d:
        nid = national_id(d)
    else:                                                    # not sent -> keep what is stored
        old = db.one("SELECT national_id FROM employees WHERE id=?", (eid,)) if eid else None
        nid = old["national_id"] if old else ""
    if nid:
        clash = db.one("SELECT id FROM employees WHERE national_id=?", (nid,))
        if clash and clash["id"] != eid:
            raise ApiError(409, "national_id_taken", "Another employee has this national ID", field="national_id")
    return {"national_id": nid, "emp_no": emp_no, "full_name_en": en, "full_name_ar": ar, "department_id": dept,
            "job_title": text(d, "job_title", maxlen=80, required=False), "email": email,
            "phone": text(d, "phone", maxlen=40, required=False),
            "status": choice(d, "status", ("active", "left"), "active"),
            "notes": text(d, "notes", maxlen=1000, required=False)}


def save_employee(ctx, eid, d):
    db = ctx.db
    cols = ("emp_no", "full_name_en", "full_name_ar", "department_id", "job_title", "email", "phone", "status", "notes", "national_id")
    with db.tx():
        v = _employee_values(db, d, eid)
        ts = now_iso()
        if eid is None:
            cur = db.execute("INSERT INTO employees(%s,created_at,updated_at) VALUES (%s,?,?)" % (",".join(cols), ",".join("?" * len(cols))),
                             tuple(v[c] for c in cols) + (ts, ts))
            eid = cur.lastrowid
            ctx.audit("employee.create", "employee", eid, {"emp_no": v["emp_no"], "name": v["full_name_en"],
                                                            **({"national_id": mask_national_id(v["national_id"])} if v["national_id"] else {})})
        else:
            old = db.one("SELECT * FROM employees WHERE id=?", (eid,))
            if old is None:
                raise ApiError(404, "employee_not_found", "Employee not found")
            if v["status"] == "left" and old["status"] != "left" and \
                    db.one("SELECT 1 FROM assignments WHERE employee_id=? AND returned_at IS NULL", (eid,)):
                raise ApiError(409, "employee_has_assets", "This employee still holds assets. Return them first.", field="status")
            db.execute("UPDATE employees SET %s, updated_at=? WHERE id=?" % ", ".join(c + "=?" for c in cols),
                       tuple(v[c] for c in cols) + (ts, eid))
            changed = {c: v[c] for c in cols if c != "notes" and old[c] != v[c]}
            if "national_id" in changed:                     # the permanent audit log never holds the full number
                changed["national_id"] = mask_national_id(v["national_id"]) if v["national_id"] else "(removed)"
            ctx.audit("employee.update", "employee", eid, changed)
    return eid


def delete_employee(ctx, eid):
    db = ctx.db
    with db.tx():
        old = db.one("SELECT * FROM employees WHERE id=?", (eid,))
        if old is None:
            raise ApiError(404, "employee_not_found", "Employee not found")
        if db.one("SELECT 1 FROM assignments WHERE employee_id=?", (eid,)):
            raise ApiError(409, "employee_has_history", "This employee has assignment history. Mark them as left instead.")
        db.execute("DELETE FROM employees WHERE id=?", (eid,))
        ctx.audit("employee.delete", "employee", eid, {"emp_no": old["emp_no"], "name": old["full_name_en"]})


# ================================================================ assets
ASSET_SELECT = ("SELECT a.*, c.code AS cat_code, c.name_en AS cat_en, c.name_ar AS cat_ar, "
                "g.id AS assignment_id, g.assigned_at, g.expected_return, "
                "e.id AS holder_id, e.emp_no AS holder_no, e.full_name_en AS holder_en, e.full_name_ar AS holder_ar "
                "FROM assets a JOIN categories c ON c.id=a.category_id "
                "LEFT JOIN assignments g ON g.asset_id=a.id AND g.returned_at IS NULL "
                "LEFT JOIN employees e ON e.id=g.employee_id")


def _asset_row(r):
    d = dict(r)
    d["custom"] = json.loads(d["custom"] or "{}")
    return d


def list_assets(db, q="", status="", category_id=None, page=1, per_page=50):
    where, params = [], []
    if q:
        where.append("(a.tag LIKE ? ESCAPE '\\' OR a.name LIKE ? ESCAPE '\\' OR a.serial_no LIKE ? ESCAPE '\\' OR a.brand LIKE ? ESCAPE '\\' "
                     "OR a.model LIKE ? ESCAPE '\\' OR a.location LIKE ? ESCAPE '\\' OR e.full_name_en LIKE ? ESCAPE '\\' "
                     "OR e.full_name_ar LIKE ? ESCAPE '\\' OR e.emp_no LIKE ? ESCAPE '\\')")
        params += [_like(q)] * 9
    if status in STATUSES:
        where.append("a.status=?")
        params.append(status)
    if category_id:
        where.append("a.category_id=?")
        params.append(category_id)
    w = (" WHERE " + " AND ".join(where)) if where else ""
    if per_page is None:                                  # everything (exports) - one query, no paging
        rows = db.query(ASSET_SELECT + w + " ORDER BY a.id DESC", params)
        return {"total": len(rows), "page": 1, "per_page": len(rows), "assets": [_asset_row(r) for r in rows]}
    per_page = max(1, min(int(per_page), 200))
    page = max(1, int(page))
    total = db.one("SELECT COUNT(*) c FROM assets a LEFT JOIN assignments g ON g.asset_id=a.id AND g.returned_at IS NULL "
                   "LEFT JOIN employees e ON e.id=g.employee_id" + w, params)["c"]
    rows = db.query(ASSET_SELECT + w + " ORDER BY a.id DESC LIMIT ? OFFSET ?", params + [per_page, (page - 1) * per_page])
    return {"total": total, "page": page, "per_page": per_page, "assets": [_asset_row(r) for r in rows]}


def get_asset(db, aid):
    r = db.one(ASSET_SELECT + " WHERE a.id=?", (aid,))
    if r is None:
        raise ApiError(404, "asset_not_found", "Asset not found")
    out = _asset_row(r)
    out["fields"] = _fields_of(db, r["category_id"])
    out["assignments"] = [dict(x) for x in db.query(
        "SELECT g.*, e.emp_no, e.full_name_en, e.full_name_ar, ub.username AS assigned_by_name, ur.username AS returned_by_name "
        "FROM assignments g JOIN employees e ON e.id=g.employee_id "
        "LEFT JOIN users ub ON ub.id=g.assigned_by LEFT JOIN users ur ON ur.id=g.returned_by "
        "WHERE g.asset_id=? ORDER BY g.id DESC", (aid,))]
    out["history"] = [dict(x, detail=json.loads(x["detail"] or "{}")) for x in db.query(
        "SELECT id, ts, username, action, detail FROM audit_log WHERE entity='asset' AND entity_id=? ORDER BY id DESC LIMIT 200", (str(aid),))]
    return out


def _custom_values(fields, raw):
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ApiError(422, "invalid_field", "Invalid custom values", field="custom")
    out = {}
    for f in fields:
        k, v = f["key"], raw.get(f["key"])
        fid = "custom." + k
        if v in (None, "") or (f["type"] == "bool" and v is False and not f["required"]):
            if f["required"] and f["type"] != "bool":
                raise ApiError(422, "field_required", "This field is required", field=fid)
            continue
        if f["type"] == "text":
            if not isinstance(v, str):
                _bad(fid)
            try:
                out[k] = text({k: v}, k, maxlen=300, required=False)
            except ApiError as e:
                raise ApiError(e.status, e.code, "This value is not valid", field=fid)
        elif f["type"] == "number":
            try:
                out[k] = number({k: v}, k, minimum=-1e12)
            except ApiError:
                raise ApiError(422, "invalid_number", "Enter a number", field=fid)
        elif f["type"] == "date":
            try:
                out[k] = date_field({k: v}, k)
            except ApiError:
                raise ApiError(422, "invalid_date", "Use a valid date", field=fid)
        elif f["type"] == "select":
            if v not in f["options"]:
                _bad(fid)
            out[k] = v
        elif f["type"] == "bool":
            if not isinstance(v, bool):
                _bad(fid)
            out[k] = v
    return out


def _bad(fid):
    raise ApiError(422, "invalid_field", "This value is not valid", field=fid)


def _asset_values(db, d, aid=None):
    cat = ref_id(d, "category_id")
    c = db.one("SELECT * FROM categories WHERE id=?", (cat,))
    if c is None:
        raise ApiError(422, "category_not_found", "Category not found", field="category_id")
    tag = text(d, "tag", maxlen=40, required=False).upper()
    if tag:
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-_/.]{0,39}", tag):
            raise ApiError(422, "asset_tag_invalid", "Use letters, digits, dash, slash, dot or underscore", field="tag")
        clash = db.one("SELECT id FROM assets WHERE tag=?", (tag,))
        if clash and clash["id"] != aid:
            raise ApiError(409, "asset_tag_taken", "Another asset already has this tag", field="tag")
    serial = text(d, "serial_no", maxlen=80, required=False)
    if serial:
        clash = db.one("SELECT id FROM assets WHERE serial_no=? COLLATE NOCASE", (serial,))
        if clash and clash["id"] != aid:
            raise ApiError(409, "serial_taken", "Another asset already has this serial number", field="serial_no")
    fields = _fields_of(db, cat)
    custom = _custom_values(fields, d.get("custom"))
    _unique_clash(db, cat, fields, custom, aid)
    return c, {
        "tag": tag, "category_id": cat, "name": text(d, "name", maxlen=120),
        "brand": text(d, "brand", maxlen=80, required=False), "model": text(d, "model", maxlen=80, required=False),
        "serial_no": serial, "condition": choice(d, "condition", CONDITIONS, "good"),
        "location": text(d, "location", maxlen=120, required=False),
        "purchase_date": date_field(d, "purchase_date"), "purchase_cost": number(d, "purchase_cost"),
        "supplier": text(d, "supplier", maxlen=120, required=False), "warranty_until": date_field(d, "warranty_until"),
        "notes": text(d, "notes", maxlen=2000, required=False),
        "custom": custom,
    }


ASSET_COLS = ("tag", "category_id", "name", "brand", "model", "serial_no", "condition", "location", "purchase_date",
              "purchase_cost", "supplier", "warranty_until", "notes", "custom")


def _next_tag(db, c):
    seq = c["next_seq"]
    while True:
        tag = "%s-%05d" % (c["code"], seq)
        seq += 1
        if db.one("SELECT 1 FROM assets WHERE tag=?", (tag,)) is None:
            break
    db.execute("UPDATE categories SET next_seq=? WHERE id=?", (seq, c["id"]))
    return tag


def create_asset(ctx, d):
    db = ctx.db
    with db.tx():
        c, v = _asset_values(db, d)
        if not v["tag"]:
            v["tag"] = _next_tag(db, c)
        ts = now_iso()
        vals = tuple(json.dumps(v[k], ensure_ascii=False, sort_keys=True) if k == "custom" else v[k] for k in ASSET_COLS)
        cur = db.execute("INSERT INTO assets(%s,status,created_at,created_by,updated_at) VALUES (%s,'in_stock',?,?,?)"
                         % (",".join(ASSET_COLS), ",".join("?" * len(ASSET_COLS))), vals + (ts, ctx.user["id"], ts))
        ctx.audit("asset.create", "asset", cur.lastrowid, {"tag": v["tag"], "name": v["name"], "category": c["code"]})
    return cur.lastrowid, v["tag"]


def update_asset(ctx, aid, d):
    db = ctx.db
    with db.tx():
        old = db.one("SELECT * FROM assets WHERE id=?", (aid,))
        if old is None:
            raise ApiError(404, "asset_not_found", "Asset not found")
        c, v = _asset_values(db, d, aid)
        if not v["tag"]:
            v["tag"] = old["tag"]
        v["custom"] = json.dumps(v["custom"], ensure_ascii=False, sort_keys=True)
        changed = {k: v[k] for k in ASSET_COLS if k != "notes" and old[k] != v[k]}
        db.execute("UPDATE assets SET %s, updated_at=? WHERE id=?" % ", ".join(k + "=?" for k in ASSET_COLS),
                   tuple(v[k] for k in ASSET_COLS) + (now_iso(), aid))
        if "custom" in changed:
            changed["custom"] = json.loads(changed["custom"])
        ctx.audit("asset.update", "asset", aid, changed)


def delete_asset(ctx, aid):
    db = ctx.db
    with db.tx():
        old = db.one("SELECT * FROM assets WHERE id=?", (aid,))
        if old is None:
            raise ApiError(404, "asset_not_found", "Asset not found")
        if db.one("SELECT 1 FROM assignments WHERE asset_id=?", (aid,)):
            raise ApiError(409, "asset_has_history", "This asset has assignment history. Retire it instead.")
        db.execute("DELETE FROM assets WHERE id=?", (aid,))
        ctx.audit("asset.delete", "asset", aid, {"tag": old["tag"], "name": old["name"]})


def set_status(ctx, aid, d):
    db = ctx.db
    status = choice(d, "status", MANUAL_STATUSES)
    note = text(d, "note", maxlen=500, required=False)
    with db.tx():
        old = db.one("SELECT * FROM assets WHERE id=?", (aid,))
        if old is None:
            raise ApiError(404, "asset_not_found", "Asset not found")
        if old["status"] == "assigned":
            raise ApiError(409, "asset_is_assigned", "Return this asset before changing its status")
        if old["status"] == status:
            return
        db.execute("UPDATE assets SET status=?, updated_at=? WHERE id=?", (status, now_iso(), aid))
        ctx.audit("asset.status", "asset", aid, {"tag": old["tag"], "from": old["status"], "to": status, "note": note})


# ================================================================ assignments
def _receipt_no(db, prefix, ts):
    """Next receipt number for the year of `ts`, e.g. HO-2026-0001. Must run inside a transaction."""
    key = "%s-%s" % (prefix, ts[:4])
    db.execute("INSERT INTO counters(key, value) VALUES (?, 1) ON CONFLICT(key) DO UPDATE SET value = value + 1", (key,))
    return "%s-%04d" % (key, db.one("SELECT value FROM counters WHERE key=?", (key,))["value"])


def _event_time(at):
    """Timestamp for a handover/return. `at` (ISO date or UTC timestamp) is only passed by trusted code - the Excel
    import and data migration - to record handovers that happened before the system existed; never from a form."""
    if not at:
        return now_iso()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", at):
        at += "T10:00:00Z"                                   # midday UTC: the same calendar day in Egypt and the Gulf
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", at):
        raise ApiError(422, "invalid_date", "Use a date like 2026-03-31", field="assigned_on")
    if at > now_iso():
        raise ApiError(422, "date_in_future", "The date cannot be in the future", field="assigned_on")
    return at


def assign(ctx, aid, d, at=None):
    db = ctx.db
    eid = ref_id(d, "employee_id")
    expected = date_field(d, "expected_return")
    notes = text(d, "notes", maxlen=1000, required=False)
    with db.tx():
        a = db.one("SELECT * FROM assets WHERE id=?", (aid,))
        if a is None:
            raise ApiError(404, "asset_not_found", "Asset not found")
        if a["status"] == "assigned":
            raise ApiError(409, "asset_already_assigned", "This asset is already assigned. Return it first.")
        if a["status"] != "in_stock":
            raise ApiError(409, "asset_not_available", "Only assets that are in stock can be assigned")
        e = db.one("SELECT * FROM employees WHERE id=?", (eid,))
        if e is None:
            raise ApiError(422, "employee_not_found", "Employee not found", field="employee_id")
        if e["status"] != "active":
            raise ApiError(409, "employee_inactive", "This employee is marked as left", field="employee_id")
        if expected and expected < today_iso():
            raise ApiError(422, "date_in_past", "The date cannot be in the past", field="expected_return")
        condition = choice(d, "condition", CONDITIONS, a["condition"])
        ts = _event_time(at)
        last = db.one("SELECT MAX(returned_at) t FROM assignments WHERE asset_id=?", (aid,))["t"]
        if last and ts < last:
            raise ApiError(422, "date_before_return", "The handover date is before this asset was last returned", field="assigned_on")
        rno = _receipt_no(db, "HO", ts)
        cur = db.execute("INSERT INTO assignments(asset_id,employee_id,assigned_at,assigned_by,expected_return,condition_out,notes_out,receipt_out_no) "
                         "VALUES (?,?,?,?,?,?,?,?)", (aid, eid, ts, ctx.user["id"], expected, condition, notes, rno))
        db.execute("UPDATE assets SET status='assigned', condition=?, updated_at=? WHERE id=?", (condition, ts, aid))
        ctx.audit("asset.assign", "asset", aid, {"tag": a["tag"], "employee_id": eid, "emp_no": e["emp_no"],
                                                  "employee": e["full_name_en"], "assignment": cur.lastrowid, "receipt": rno})
    return cur.lastrowid


def return_asset(ctx, aid, d, at=None):
    db = ctx.db
    notes = text(d, "notes", maxlen=1000, required=False)
    after = choice(d, "status_after", ("in_stock", "maintenance", "retired", "lost"), "in_stock")
    with db.tx():
        a = db.one("SELECT * FROM assets WHERE id=?", (aid,))
        if a is None:
            raise ApiError(404, "asset_not_found", "Asset not found")
        g = db.one("SELECT g.*, e.emp_no, e.full_name_en FROM assignments g JOIN employees e ON e.id=g.employee_id "
                   "WHERE g.asset_id=? AND g.returned_at IS NULL", (aid,))
        if g is None:
            raise ApiError(409, "asset_not_assigned", "This asset is not assigned to anyone")
        condition = choice(d, "condition", CONDITIONS, a["condition"])
        ts = _event_time(at)
        if ts < g["assigned_at"]:
            raise ApiError(422, "date_before_handover", "The return date is before the handover date", field="returned_on")
        rno = _receipt_no(db, "RT", ts)
        db.execute("UPDATE assignments SET returned_at=?, returned_by=?, condition_in=?, notes_in=?, receipt_in_no=? WHERE id=?",
                   (ts, ctx.user["id"], condition, notes, rno, g["id"]))
        db.execute("UPDATE assets SET status=?, condition=?, updated_at=? WHERE id=?", (after, condition, ts, aid))
        ctx.audit("asset.return", "asset", aid, {"tag": a["tag"], "employee_id": g["employee_id"], "emp_no": g["emp_no"],
                                                  "employee": g["full_name_en"], "assignment": g["id"], "status": after,
                                                  "condition": condition, "receipt": rno})


def receipt(db, gid, kind, full_nid=False):
    """Everything needed to print a handover or return receipt for one assignment."""
    from . import company
    g = db.one("SELECT g.*, ub.full_name AS assigned_by_name, ur.full_name AS returned_by_name FROM assignments g "
               "LEFT JOIN users ub ON ub.id=g.assigned_by LEFT JOIN users ur ON ur.id=g.returned_by WHERE g.id=?", (gid,))
    if g is None:
        raise ApiError(404, "assignment_not_found", "Assignment not found")
    if kind == "return" and not g["returned_at"]:
        raise ApiError(409, "receipt_not_ready", "This asset has not been returned yet")
    a = db.one("SELECT a.*, c.code AS cat_code, c.name_en AS cat_en, c.name_ar AS cat_ar FROM assets a "
               "JOIN categories c ON c.id=a.category_id WHERE a.id=?", (g["asset_id"],))
    e = db.one("SELECT e.*, d.name_en AS dept_en, d.name_ar AS dept_ar FROM employees e "
               "LEFT JOIN departments d ON d.id=e.department_id WHERE e.id=?", (g["employee_id"],))
    c = company.get(db) or {}
    asset = _asset_row(a)
    asset["fields"] = _fields_of(db, a["category_id"])
    return {"kind": kind, "number": g["receipt_out_no"] if kind == "handover" else g["receipt_in_no"],
            "assignment": dict(g), "asset": asset, "employee": _nid_view(dict(e), full_nid),
            "company": {"name_en": c.get("name_en", ""), "name_ar": c.get("name_ar", ""),
                        "logo": company.branding(db)["logo"],
                        "terms_en": c.get("receipt_terms_en", ""), "terms_ar": c.get("receipt_terms_ar", "")},
            "signed_copies": [dict(r) for r in db.query(
                "SELECT id, filename, created_at FROM documents WHERE entity='assignment' AND entity_id=? ORDER BY id", (gid,))]}


def list_open_assignments(db, q=""):
    where, params = "WHERE g.returned_at IS NULL", []
    if q:
        where += (" AND (a.tag LIKE ? ESCAPE '\\' OR a.name LIKE ? ESCAPE '\\' OR e.emp_no LIKE ? ESCAPE '\\' "
                  "OR e.full_name_en LIKE ? ESCAPE '\\' OR e.full_name_ar LIKE ? ESCAPE '\\')")
        params = [_like(q)] * 5
    rows = db.query("SELECT g.*, a.tag, a.name AS asset_name, c.name_en AS cat_en, c.name_ar AS cat_ar, "
                    "e.emp_no, e.full_name_en, e.full_name_ar, d.name_en AS dept_en, d.name_ar AS dept_ar "
                    "FROM assignments g JOIN assets a ON a.id=g.asset_id JOIN categories c ON c.id=a.category_id "
                    "JOIN employees e ON e.id=g.employee_id LEFT JOIN departments d ON d.id=e.department_id "
                    + where + " ORDER BY (g.expected_return <> '' AND g.expected_return < ?) DESC, g.assigned_at DESC LIMIT 2000",
                    params + [today_iso()])
    t = today_iso()
    return [dict(r, overdue=bool(r["expected_return"] and r["expected_return"] < t)) for r in rows]


def summary(db):
    by = {s: 0 for s in STATUSES}
    for r in db.query("SELECT status, COUNT(*) c FROM assets GROUP BY status"):
        by[r["status"]] = r["c"]
    val = db.one("SELECT COALESCE(SUM(purchase_cost),0) v FROM assets WHERE status NOT IN ('retired','lost')")["v"]
    overdue = db.one("SELECT COUNT(*) c FROM assignments WHERE returned_at IS NULL AND expected_return <> '' AND expected_return < ?",
                     (today_iso(),))["c"]
    warranty = db.one("SELECT COUNT(*) c FROM assets WHERE warranty_until <> '' AND warranty_until >= ? AND warranty_until <= date(?, '+30 day') "
                      "AND status NOT IN ('retired','lost')", (today_iso(), today_iso()))["c"]
    return {"total": sum(by.values()), "by_status": by, "value": val, "overdue": overdue, "warranty_soon": warranty,
            "categories": db.one("SELECT COUNT(*) c FROM categories")["c"],
            "employees": db.one("SELECT COUNT(*) c FROM employees WHERE status='active'")["c"]}
