# -*- coding: utf-8 -*-
"""Maintenance log and asset requests (approval workflow).

Maintenance: scheduled -> open -> done (or cancelled). Starting work on an in-stock asset can take it out of service
(status 'maintenance'); completing that record puts it back in stock - but only if this record took it out.
Requests: pending -> fulfilled (an approver picks an in-stock asset; it is assigned in the same transaction)
or rejected / cancelled. Every change is audited; maintenance entries appear on the asset's timeline."""
from . import inventory as inv
from .errors import ApiError
from .util import now_iso, today_iso, text, choice, date_field, number, ref_id

KINDS = ("repair", "service", "inspection", "upgrade", "other")

# ================================================================ maintenance
M_SELECT = ("SELECT m.*, a.tag, a.name AS asset_name, a.status AS asset_status, c.name_en AS cat_en, c.name_ar AS cat_ar, "
            "u.username AS created_by_name FROM maintenance m JOIN assets a ON a.id=m.asset_id "
            "JOIN categories c ON c.id=a.category_id LEFT JOIN users u ON u.id=m.created_by")


def _m_row(r):
    d = dict(r)
    d["overdue"] = d["status"] == "scheduled" and bool(d["scheduled_for"]) and d["scheduled_for"] < today_iso()
    return d


def list_maintenance(db, status="", asset_id=None, q=""):
    where, params = [], []
    if status == "active":
        where.append("m.status IN ('scheduled','open')")
    elif status in ("scheduled", "open", "done", "cancelled"):
        where.append("m.status=?")
        params.append(status)
    if asset_id:
        where.append("m.asset_id=?")
        params.append(asset_id)
    if q:
        where.append("(a.tag LIKE ? ESCAPE '\\' OR a.name LIKE ? ESCAPE '\\' OR m.title LIKE ? ESCAPE '\\' OR m.vendor LIKE ? ESCAPE '\\')")
        params += [inv._like(q)] * 4
    w = (" WHERE " + " AND ".join(where)) if where else ""
    order = (" ORDER BY CASE m.status WHEN 'open' THEN 0 WHEN 'scheduled' THEN 1 ELSE 2 END, "
             "CASE WHEN m.status='scheduled' THEN m.scheduled_for END, m.id DESC LIMIT 2000")
    return [_m_row(r) for r in db.query(M_SELECT + w + order, params)]


def _get_m(db, mid):
    r = db.one(M_SELECT + " WHERE m.id=?", (mid,))
    if r is None:
        raise ApiError(404, "maintenance_not_found", "Maintenance record not found")
    return r


def _audit(ctx, action, m, extra=None):
    d = {"tag": m["tag"], "maintenance": m["id"], "title": m["title"]}
    d.update(extra or {})
    ctx.audit(action, "asset", m["asset_id"], d)


def _take_out(db, asset):
    """Move an in-stock asset to maintenance. Returns True when this record did it."""
    if asset["status"] == "in_stock":
        db.execute("UPDATE assets SET status='maintenance', updated_at=? WHERE id=?", (now_iso(), asset["id"]))
        return True
    return False


def _release(db, m, ts, condition=None):
    """Called when record `m` closes. If it took the asset out of service: hand that over to another open record on
    the same asset (work is still going on), or put the asset back in stock when it was the last one. Returns True if back in stock."""
    if not m["took_out_of_service"] or m["asset_status"] != "maintenance":
        return False
    other = db.one("SELECT id FROM maintenance WHERE asset_id=? AND id<>? AND status='open' ORDER BY id DESC LIMIT 1", (m["asset_id"], m["id"]))
    if other:
        db.execute("UPDATE maintenance SET took_out_of_service=1 WHERE id=?", (other["id"],))
        return False
    db.execute("UPDATE assets SET status='in_stock', condition=COALESCE(?, condition), updated_at=? WHERE id=?", (condition, ts, m["asset_id"]))
    return True


def create_maintenance(ctx, d):
    db = ctx.db
    aid = ref_id(d, "asset_id")
    kind = choice(d, "kind", KINDS, "repair")
    title = text(d, "title", maxlen=150)
    scheduled_for = date_field(d, "scheduled_for")
    status = "scheduled" if scheduled_for and scheduled_for > today_iso() else "open"
    if d.get("schedule_only") and scheduled_for:
        status = "scheduled"
    with db.tx():
        a = db.one("SELECT * FROM assets WHERE id=?", (aid,))
        if a is None:
            raise ApiError(422, "asset_not_found", "Asset not found", field="asset_id")
        if a["status"] in ("retired", "lost"):
            raise ApiError(409, "asset_disposed", "This asset is retired or lost")
        took = status == "open" and bool(d.get("out_of_service")) and _take_out(db, a)
        ts = now_iso()
        cur = db.execute("INSERT INTO maintenance(asset_id,kind,status,title,description,vendor,cost,scheduled_for,started_at,took_out_of_service,"
                         "created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (aid, kind, status, title, text(d, "description", maxlen=2000, required=False),
                          text(d, "vendor", maxlen=120, required=False), number(d, "cost"), scheduled_for,
                          ts if status == "open" else None, 1 if took else 0, ctx.user["id"], ts, ts))
        m = _get_m(db, cur.lastrowid)
        _audit(ctx, "maintenance.create", m, {"status": status, "kind": kind, "out_of_service": took})
    return cur.lastrowid


def update_maintenance(ctx, mid, d):
    db = ctx.db
    with db.tx():
        m = _get_m(db, mid)
        sched = date_field(d, "scheduled_for") if m["status"] == "scheduled" else m["scheduled_for"]
        if m["status"] == "scheduled" and not sched:
            raise ApiError(422, "field_required", "scheduled_for is required", field="scheduled_for")
        db.execute("UPDATE maintenance SET kind=?, title=?, description=?, vendor=?, cost=?, scheduled_for=?, resolution=?, updated_at=? WHERE id=?",
                   (choice(d, "kind", KINDS, m["kind"]), text(d, "title", maxlen=150), text(d, "description", maxlen=2000, required=False),
                    text(d, "vendor", maxlen=120, required=False), number(d, "cost"), sched,
                    text(d, "resolution", maxlen=2000, required=False) if "resolution" in d else m["resolution"], now_iso(), mid))
        _audit(ctx, "maintenance.update", _get_m(db, mid))


def start_maintenance(ctx, mid, d):
    db = ctx.db
    with db.tx():
        m = _get_m(db, mid)
        if m["status"] != "scheduled":
            raise ApiError(409, "maintenance_wrong_state", "This record cannot be started")
        a = db.one("SELECT * FROM assets WHERE id=?", (m["asset_id"],))
        if a["status"] in ("retired", "lost"):
            raise ApiError(409, "asset_disposed", "This asset is retired or lost")
        took = bool(d.get("out_of_service")) and _take_out(db, a)
        db.execute("UPDATE maintenance SET status='open', started_at=?, took_out_of_service=?, updated_at=? WHERE id=?",
                   (now_iso(), 1 if took else 0, now_iso(), mid))
        _audit(ctx, "maintenance.start", m, {"out_of_service": took})


def complete_maintenance(ctx, mid, d):
    db = ctx.db
    with db.tx():
        m = _get_m(db, mid)
        if m["status"] not in ("open", "scheduled"):
            raise ApiError(409, "maintenance_wrong_state", "This record is already closed")
        cost = number(d, "cost") if d.get("cost") not in (None, "") else m["cost"]
        ts = now_iso()
        db.execute("UPDATE maintenance SET status='done', completed_at=?, started_at=COALESCE(started_at, ?), cost=?, resolution=?, updated_at=? WHERE id=?",
                   (ts, ts, cost, text(d, "resolution", maxlen=2000, required=False), ts, mid))
        condition = choice(d, "condition", inv.CONDITIONS, None) if d.get("condition") else None
        back = _release(db, m, ts, condition)
        _audit(ctx, "maintenance.complete", m, {"cost": cost, "back_in_stock": back})


def cancel_maintenance(ctx, mid, d):
    db = ctx.db
    with db.tx():
        m = _get_m(db, mid)
        if m["status"] not in ("open", "scheduled"):
            raise ApiError(409, "maintenance_wrong_state", "This record is already closed")
        db.execute("UPDATE maintenance SET status='cancelled', resolution=?, updated_at=? WHERE id=?",
                   (text(d, "resolution", maxlen=2000, required=False), now_iso(), mid))
        back = _release(db, m, now_iso())
        _audit(ctx, "maintenance.cancel", m, {"back_in_stock": back})


# ================================================================ requests
R_SELECT = ("SELECT r.*, e.emp_no, e.full_name_en, e.full_name_ar, e.status AS employee_status, d.name_en AS dept_en, d.name_ar AS dept_ar, "
            "c.code AS cat_code, c.name_en AS cat_en, c.name_ar AS cat_ar, ur.username AS requested_by_name, ur.full_name AS requested_by_full, "
            "ud.username AS decided_by_name, a.tag AS asset_tag, a.name AS asset_name "
            "FROM asset_requests r JOIN employees e ON e.id=r.employee_id LEFT JOIN departments d ON d.id=e.department_id "
            "LEFT JOIN categories c ON c.id=r.category_id LEFT JOIN users ur ON ur.id=r.requested_by LEFT JOIN users ud ON ud.id=r.decided_by "
            "LEFT JOIN assignments g ON g.id=r.assignment_id LEFT JOIN assets a ON a.id=g.asset_id")


def list_requests(db, status="", mine_user_id=None):
    where, params = [], []
    if status in ("pending", "fulfilled", "rejected", "cancelled"):
        where.append("r.status=?")
        params.append(status)
    if mine_user_id:
        where.append("r.requested_by=?")
        params.append(mine_user_id)
    w = (" WHERE " + " AND ".join(where)) if where else ""
    rows = [dict(r) for r in db.query(R_SELECT + w + " ORDER BY r.status='pending' DESC, r.id DESC LIMIT 1000", params)]
    for r in rows:
        r["available"] = db.one("SELECT COUNT(*) c FROM assets WHERE status='in_stock'" + (" AND category_id=?" if r["category_id"] else ""),
                                (r["category_id"],) if r["category_id"] else ())["c"] if r["status"] == "pending" else None
    return rows


def _get_r(db, rid):
    r = db.one(R_SELECT + " WHERE r.id=?", (rid,))
    if r is None:
        raise ApiError(404, "request_not_found", "Request not found")
    return r


def create_request(ctx, d):
    db = ctx.db
    eid = ref_id(d, "employee_id")
    cid = ref_id(d, "category_id", required=False)
    needed = date_field(d, "needed_by")
    with db.tx():
        e = db.one("SELECT * FROM employees WHERE id=?", (eid,))
        if e is None:
            raise ApiError(422, "employee_not_found", "Employee not found", field="employee_id")
        if e["status"] != "active":
            raise ApiError(409, "employee_inactive", "This employee is marked as left", field="employee_id")
        if cid and db.one("SELECT 1 FROM categories WHERE id=?", (cid,)) is None:
            raise ApiError(422, "category_not_found", "Category not found", field="category_id")
        cur = db.execute("INSERT INTO asset_requests(employee_id,category_id,reason,needed_by,status,requested_by,requested_at) VALUES (?,?,?,?,?,?,?)",
                         (eid, cid, text(d, "reason", maxlen=1000), needed, "pending", ctx.user["id"], now_iso()))
        ctx.audit("request.create", "request", cur.lastrowid, {"employee": e["full_name_en"], "emp_no": e["emp_no"], "category_id": cid})
    return cur.lastrowid


def approve_request(ctx, rid, d):
    db = ctx.db
    aid = ref_id(d, "asset_id")
    note = text(d, "note", maxlen=1000, required=False)
    with db.tx():
        r = _get_r(db, rid)
        if r["status"] != "pending":
            raise ApiError(409, "request_closed", "This request is already closed")
        a = db.one("SELECT * FROM assets WHERE id=?", (aid,))
        if a is None:
            raise ApiError(422, "asset_not_found", "Asset not found", field="asset_id")
        if r["category_id"] and a["category_id"] != r["category_id"]:
            raise ApiError(422, "asset_wrong_category", "Choose an asset from the requested category", field="asset_id")
        gid = inv.assign(ctx, aid, {"employee_id": r["employee_id"], "expected_return": d.get("expected_return") or "",
                                    "notes": note or r["reason"], "condition": a["condition"]})
        db.execute("UPDATE asset_requests SET status='fulfilled', decided_by=?, decided_at=?, decision_note=?, assignment_id=? WHERE id=?",
                   (ctx.user["id"], now_iso(), note, gid, rid))
        ctx.audit("request.approve", "request", rid, {"asset": a["tag"], "assignment": gid, "employee": r["full_name_en"]})
    return gid


def reject_request(ctx, rid, d):
    db = ctx.db
    note = text(d, "note", maxlen=1000)
    with db.tx():
        r = _get_r(db, rid)
        if r["status"] != "pending":
            raise ApiError(409, "request_closed", "This request is already closed")
        db.execute("UPDATE asset_requests SET status='rejected', decided_by=?, decided_at=?, decision_note=? WHERE id=?",
                   (ctx.user["id"], now_iso(), note, rid))
        ctx.audit("request.reject", "request", rid, {"note": note, "employee": r["full_name_en"]})


def cancel_request(ctx, rid, can_approve):
    db = ctx.db
    with db.tx():
        r = _get_r(db, rid)
        if r["status"] != "pending":
            raise ApiError(409, "request_closed", "This request is already closed")
        if r["requested_by"] != ctx.user["id"] and not can_approve:
            raise ApiError(403, "forbidden", "You do not have permission")
        db.execute("UPDATE asset_requests SET status='cancelled', decided_by=?, decided_at=? WHERE id=?", (ctx.user["id"], now_iso(), rid))
        ctx.audit("request.cancel", "request", rid, {"employee": r["full_name_en"]})
