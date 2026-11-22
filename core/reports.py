# -*- coding: utf-8 -*-
"""Reports and dashboard analytics.

Every report returns the same shape so the interface and the Excel export can render any of them:
    {"columns": [{"key", "label", "type"}], "rows": [dict], "totals": {key: value}, "summary": {...} optional}
`label` is an interface translation key; `type` tells the renderer how to show the value
(text, mono, name, date, datetime, money, int, num, status, condition, event)."""
import datetime

from . import xlsx
from .errors import ApiError
from .transfer import _t
from .util import today_iso, date_field

DISPOSED = ("retired", "lost")
SCREEN_ROWS = 2000          # rows sent to the browser; the Excel export always contains every row


def C(key, label, typ="text"):
    return {"key": key, "label": label, "type": typ}


def _today():
    return datetime.date.fromisoformat(today_iso())


def _days(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


# ------------------------------------------------------------------ reports
def holdings(db, department_id=None):
    where, params = "WHERE g.returned_at IS NULL", []
    if department_id:
        where += " AND e.department_id=?"
        params.append(department_id)
    rows = [dict(r) for r in db.query(
        "SELECT e.id, e.emp_no, e.full_name_en AS employee_en, e.full_name_ar AS employee_ar, d.name_en AS dept_en, d.name_ar AS dept_ar, "
        "COUNT(g.id) AS count, SUM(a.purchase_cost) AS value, GROUP_CONCAT(a.tag, ', ') AS tags "
        "FROM assignments g JOIN employees e ON e.id=g.employee_id JOIN assets a ON a.id=g.asset_id "
        "LEFT JOIN departments d ON d.id=e.department_id " + where +
        " GROUP BY e.id ORDER BY count DESC, e.full_name_en COLLATE NOCASE", params)]
    return {"columns": [C("emp_no", "emp.no", "mono"), C("employee", "emp.name", "name"), C("dept", "emp.department", "name"),
                        C("count", "rep.assets_held", "int"), C("value", "rep.cost", "money"), C("tags", "assets.tag", "mono")],
            "rows": rows, "totals": {"count": sum(r["count"] for r in rows), "value": sum(r["value"] or 0 for r in rows)}}


def overdue(db):
    t = today_iso()
    rows = []
    for r in db.query(
            "SELECT g.id AS assignment_id, g.receipt_out_no AS receipt, a.id AS asset_id, a.tag, a.name AS asset, e.emp_no, "
            "e.full_name_en AS employee_en, e.full_name_ar AS employee_ar, d.name_en AS dept_en, d.name_ar AS dept_ar, "
            "g.assigned_at, g.expected_return FROM assignments g JOIN assets a ON a.id=g.asset_id JOIN employees e ON e.id=g.employee_id "
            "LEFT JOIN departments d ON d.id=e.department_id "
            "WHERE g.returned_at IS NULL AND g.expected_return <> '' AND g.expected_return < ? ORDER BY g.expected_return", (t,)):
        d = dict(r)
        d["days"] = _days(d["expected_return"], t)
        rows.append(d)
    return {"columns": [C("tag", "assets.tag", "mono"), C("asset", "assets.asset"), C("emp_no", "emp.no", "mono"),
                        C("employee", "emp.name", "name"), C("dept", "emp.department", "name"), C("assigned_at", "asg.assigned_on", "date"),
                        C("expected_return", "asg.expected_return", "date"), C("days", "rep.days_overdue", "int"),
                        C("receipt", "rcpt.handover", "mono")],
            "rows": rows, "totals": {"tag": len(rows)}}


def warranty(db, days=60, include_expired=False):
    t = _today()
    limit = (t + datetime.timedelta(days=days)).isoformat()
    where = "a.warranty_until <> '' AND a.warranty_until <= ? AND a.status NOT IN ('retired','lost')"
    params = [limit]
    if not include_expired:
        where += " AND a.warranty_until >= ?"
        params.append(t.isoformat())
    rows = []
    for r in db.query(
            "SELECT a.id AS asset_id, a.tag, a.name AS asset, a.serial_no, a.status, a.supplier, c.name_en AS cat_en, c.name_ar AS cat_ar, "
            "e.full_name_en AS holder_en, e.full_name_ar AS holder_ar, a.warranty_until FROM assets a JOIN categories c ON c.id=a.category_id "
            "LEFT JOIN assignments g ON g.asset_id=a.id AND g.returned_at IS NULL LEFT JOIN employees e ON e.id=g.employee_id "
            "WHERE " + where + " ORDER BY a.warranty_until", params):
        d = dict(r)
        d["days_left"] = _days(t.isoformat(), d["warranty_until"])
        rows.append(d)
    return {"columns": [C("tag", "assets.tag", "mono"), C("asset", "assets.asset"), C("cat", "assets.category", "name"),
                        C("serial_no", "assets.serial", "mono"), C("status", "assets.status", "status"), C("holder", "assets.holder", "name"),
                        C("supplier", "assets.supplier"), C("warranty_until", "assets.warranty", "date"), C("days_left", "rep.days_left", "int")],
            "rows": rows, "totals": {"tag": len(rows)}}


def activity(db, date_from, date_to, limit=None):
    """Handovers and returns in a date range, newest first. With `limit`, each half reads only its newest rows
    through the date indexes (fast even for years of history); the totals are always exact."""
    if date_from > date_to:
        raise ApiError(422, "date_range_invalid", "The start date is after the end date", field="from")
    lo, hi = date_from, date_to + "T23:59:59Z"
    n = -1 if limit is None else int(limit)
    base = ("SELECT g.id AS assignment_id, a.id AS asset_id, a.tag, a.name AS asset, e.emp_no, e.full_name_en AS employee_en, "
            "e.full_name_ar AS employee_ar, d.name_en AS dept_en, d.name_ar AS dept_ar, ")
    joins = ("FROM assignments g JOIN assets a ON a.id=g.asset_id JOIN employees e ON e.id=g.employee_id "
             "LEFT JOIN departments d ON d.id=e.department_id ")
    rows = [dict(r) for r in db.query(
        "SELECT * FROM (" + base + "'handover' AS event, g.assigned_at AS at, g.receipt_out_no AS receipt, g.condition_out AS condition, "
        "u.username AS by_user " + joins + "LEFT JOIN users u ON u.id=g.assigned_by WHERE g.assigned_at BETWEEN ? AND ? ORDER BY g.assigned_at DESC LIMIT ?) "
        "UNION ALL SELECT * FROM (" + base + "'return' AS event, g.returned_at AS at, g.receipt_in_no AS receipt, g.condition_in AS condition, "
        "u.username AS by_user " + joins + "LEFT JOIN users u ON u.id=g.returned_by WHERE g.returned_at BETWEEN ? AND ? ORDER BY g.returned_at DESC LIMIT ?) "
        "ORDER BY at DESC, event DESC, assignment_id DESC LIMIT ?", (lo, hi, n, lo, hi, n, n))]
    ho = db.one("SELECT COUNT(*) c FROM assignments WHERE assigned_at BETWEEN ? AND ?", (lo, hi))["c"]
    rt = db.one("SELECT COUNT(*) c FROM assignments WHERE returned_at BETWEEN ? AND ?", (lo, hi))["c"]
    return {"columns": [C("at", "rep.date", "datetime"), C("event", "rep.event", "event"), C("receipt", "rep.receipt", "mono"),
                        C("tag", "assets.tag", "mono"), C("asset", "assets.asset"), C("emp_no", "emp.no", "mono"),
                        C("employee", "emp.name", "name"), C("dept", "emp.department", "name"), C("condition", "assets.condition", "condition"),
                        C("by_user", "rep.by_user", "mono")],
            "rows": rows, "total_rows": ho + rt, "totals": {"handover": ho, "return": rt}}


def depreciation(cost, purchase_date, life, as_of):
    """Straight-line to zero over `life` years. Returns (age_years, accumulated, book_value); None parts when unknown."""
    if cost is None:
        return None, None, None
    if not purchase_date:
        return None, None, cost
    age = max(0.0, (as_of - datetime.date.fromisoformat(purchase_date)).days / 365.25)
    if not life:
        return round(age, 1), 0.0, cost
    acc = min(cost, cost * age / life)
    return round(age, 1), round(acc, 2), round(cost - acc, 2)


def value(db, category_id=None, include_disposed=False):
    as_of = _today()
    where, params = [], []
    if category_id:
        where.append("a.category_id=?")
        params.append(category_id)
    if not include_disposed:
        where.append("a.status NOT IN ('retired','lost')")
    w = (" WHERE " + " AND ".join(where)) if where else ""
    rows, groups = [], {}
    for r in db.query("SELECT a.id AS asset_id, a.tag, a.name AS asset, a.status, a.purchase_date, a.purchase_cost AS cost, "
                      "c.id AS cat_id, c.name_en AS cat_en, c.name_ar AS cat_ar, c.useful_life_years AS life "
                      "FROM assets a JOIN categories c ON c.id=a.category_id" + w + " ORDER BY c.name_en COLLATE NOCASE, a.tag", params):
        d = dict(r)
        d["age"], d["accumulated"], d["book"] = depreciation(d["cost"], d["purchase_date"], d["life"], as_of)
        d["life"] = d["life"] or None
        rows.append(d)
        g = groups.setdefault(d["cat_id"], {"cat_en": d["cat_en"], "cat_ar": d["cat_ar"], "count": 0, "cost": 0.0, "accumulated": 0.0, "book": 0.0,
                                            "life": d["life"]})
        g["count"] += 1
        g["cost"] += d["cost"] or 0
        g["accumulated"] += d["accumulated"] or 0
        g["book"] += d["book"] or 0
    tot = {k: round(sum(g[k] for g in groups.values()), 2) for k in ("cost", "accumulated", "book")}
    return {"columns": [C("tag", "assets.tag", "mono"), C("asset", "assets.asset"), C("cat", "assets.category", "name"),
                        C("status", "assets.status", "status"), C("purchase_date", "assets.purchase_date", "date"), C("cost", "rep.cost", "money"),
                        C("life", "rep.life", "int"), C("age", "rep.age", "num"), C("accumulated", "rep.accumulated", "money"),
                        C("book", "rep.book", "money")],
            "rows": rows, "totals": dict(tot, tag=len(rows)), "as_of": as_of.isoformat(),
            "summary": {"columns": [C("cat", "assets.category", "name"), C("life", "rep.life", "int"), C("count", "rep.count", "int"),
                                    C("cost", "rep.cost", "money"), C("accumulated", "rep.accumulated", "money"), C("book", "rep.book", "money")],
                        "rows": sorted(groups.values(), key=lambda g: -g["cost"]), "totals": dict(tot, count=len(rows))}}


def maintenance(db, date_from, date_to, status=""):
    if date_from > date_to:
        raise ApiError(422, "date_range_invalid", "The start date is after the end date", field="from")
    where = "COALESCE(m.completed_at, m.started_at, m.created_at) BETWEEN ? AND ?"
    params = [date_from, date_to + "T23:59:59Z"]
    if status in ("scheduled", "open", "done", "cancelled"):
        where += " AND m.status=?"
        params.append(status)
    rows = [dict(r) for r in db.query(
        "SELECT m.id, a.id AS asset_id, a.tag, a.name AS asset, c.name_en AS cat_en, c.name_ar AS cat_ar, m.kind, m.status, m.title, m.vendor, m.cost, "
        "COALESCE(m.completed_at, m.started_at, m.created_at) AS at FROM maintenance m JOIN assets a ON a.id=m.asset_id "
        "JOIN categories c ON c.id=a.category_id WHERE " + where + " ORDER BY at DESC, m.id DESC", params)]
    return {"columns": [C("at", "rep.date", "date"), C("tag", "assets.tag", "mono"), C("asset", "assets.asset"), C("cat", "assets.category", "name"),
                        C("kind", "mnt.kind", "mkind"), C("status", "assets.status", "mstatus"), C("title", "mnt.title"),
                        C("vendor", "mnt.vendor"), C("cost", "mnt.cost", "money")],
            "rows": rows, "totals": {"tag": len(rows), "cost": round(sum(r["cost"] or 0 for r in rows), 2)}}


# ------------------------------------------------------------------ dispatch
def _int_or_none(v):
    try:
        return int(v) if v not in (None, "") else None
    except ValueError:
        raise ApiError(400, "bad_request", "Bad request")


def run(db, name, q, limit=None):
    if name == "holdings":
        return holdings(db, _int_or_none(q.get("department")))
    if name == "overdue":
        return overdue(db)
    if name == "warranty":
        days = _int_or_none(q.get("days")) or 60
        return warranty(db, max(1, min(days, 3650)), q.get("expired") == "1")
    if name == "activity":
        t = _today()
        f = date_field(q, "from") or (t - datetime.timedelta(days=30)).isoformat()
        to = date_field(q, "to") or t.isoformat()
        return activity(db, f, to, limit)
    if name == "value":
        return value(db, _int_or_none(q.get("category")), q.get("disposed") == "1")
    if name == "maintenance":
        t = _today()
        f = date_field(q, "from") or (t - datetime.timedelta(days=90)).isoformat()
        to = date_field(q, "to") or t.isoformat()
        return maintenance(db, f, to, q.get("status", ""))
    raise ApiError(404, "not_found", "Not found")


REPORTS = ("holdings", "overdue", "warranty", "activity", "value", "maintenance")
REPORT_PERM = {"maintenance": "maintenance.view"}


def _out(col, row, lang):
    v = row.get(col["key"]) if col["type"] != "name" else (
        (row.get(col["key"] + "_ar") or row.get(col["key"] + "_en")) if lang == "ar" else (row.get(col["key"] + "_en") or row.get(col["key"] + "_ar")))
    if v is None:
        return ""
    if col["type"] == "status":
        return _t(lang, "st." + v)
    if col["type"] == "condition":
        return _t(lang, "cond." + v)
    if col["type"] == "event":
        return _t(lang, "rcpt." + v)
    if col["type"] == "mkind":
        return _t(lang, "mnt.k_" + v)
    if col["type"] == "mstatus":
        return _t(lang, "mnt.s_" + v)
    if col["type"] in ("date", "datetime"):
        return v[:10] if col["type"] == "date" else v.replace("T", " ").rstrip("Z")
    return v


def _sheet(name, rep, lang):
    cols = rep["columns"]
    rows = [[_t(lang, c["label"]) for c in cols]]
    rows += [[_out(c, r, lang) for c in cols] for r in rep["rows"]]
    tot = rep.get("totals") or {}
    if any(c["key"] in tot for c in cols):
        first = _t(lang, "rep.total") + (": %s" % tot[cols[0]["key"]] if cols[0]["key"] in tot else "")
        rows.append([first] + [tot.get(c["key"], "") for c in cols[1:]])
    return {"name": name, "rows": rows, "rtl": lang == "ar"}


def to_xlsx(name, rep, lang):
    sheets = [_sheet(_t(lang, "rep." + name), rep, lang)]
    if rep.get("summary"):
        sheets.append(_sheet(_t(lang, "rep.summary"), rep["summary"], lang))
    return xlsx.write(sheets)


# ------------------------------------------------------------------ dashboard analytics
def analytics(db, months=12):
    t = _today()
    keys, y, m = [], t.year, t.month
    for _ in range(months):
        keys.append("%04d-%02d" % (y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys.reverse()
    start = keys[0] + "-01"
    ho = {r["m"]: r["c"] for r in db.query("SELECT substr(assigned_at,1,7) m, COUNT(*) c FROM assignments WHERE assigned_at >= ? GROUP BY m", (start,))}
    rt = {r["m"]: r["c"] for r in db.query("SELECT substr(returned_at,1,7) m, COUNT(*) c FROM assignments WHERE returned_at >= ? GROUP BY m", (start,))}
    return {
        "monthly": [{"month": k, "handovers": ho.get(k, 0), "returns": rt.get(k, 0)} for k in keys],
        "by_category": [dict(r) for r in db.query(
            "SELECT c.id, c.name_en, c.name_ar, COUNT(a.id) AS count, COALESCE(SUM(a.purchase_cost),0) AS value FROM categories c "
            "JOIN assets a ON a.category_id=c.id WHERE a.status NOT IN ('retired','lost') GROUP BY c.id ORDER BY count DESC")],
        "by_department": [dict(r) for r in db.query(
            "SELECT d.id, d.name_en, d.name_ar, COUNT(g.id) AS count FROM assignments g JOIN employees e ON e.id=g.employee_id "
            "LEFT JOIN departments d ON d.id=e.department_id WHERE g.returned_at IS NULL GROUP BY d.id ORDER BY count DESC")],
    }
