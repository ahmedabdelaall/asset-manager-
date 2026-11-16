# -*- coding: utf-8 -*-
"""Append-only, hash-chained audit trail. Rows cannot be edited or deleted (database triggers),
and every row carries a hash of the previous one so tampering is detectable."""
import json
import hashlib

from .util import now_iso

GENESIS = "0" * 64


def _digest(prev, ts, user_id, username, action, entity, entity_id, detail, ip):
    raw = json.dumps([prev, ts, user_id, username, action, entity, entity_id, detail, ip],
                     ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def write(db, user, action, entity="", entity_id="", detail=None, ip=""):
    detail_s = json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)
    uid = user["id"] if user else None
    uname = user["username"] if user else ""
    with db.tx():
        last = db.one("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
        prev = last["hash"] if last else GENESIS
        ts = now_iso()
        h = _digest(prev, ts, uid, uname, action, entity, str(entity_id), detail_s, ip)
        db.execute("INSERT INTO audit_log(ts,user_id,username,action,entity,entity_id,detail,ip,prev_hash,hash) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?)", (ts, uid, uname, action, entity, str(entity_id), detail_s, ip, prev, h))


def list_entries(db, page=1, per_page=50, user="", action="", q=""):
    where, params = [], []
    if user:
        where.append("username = ?")
        params.append(user)
    if action:
        where.append("action LIKE ?")
        params.append(action.replace("%", "") + "%")
    if q:
        where.append("(detail LIKE ? OR entity_id LIKE ? OR username LIKE ?)")
        params += ["%" + q.replace("%", "") + "%"] * 3
    w = (" WHERE " + " AND ".join(where)) if where else ""
    total = db.one("SELECT COUNT(*) c FROM audit_log" + w, params)["c"]
    per_page = max(1, min(per_page, 200))
    rows = db.query("SELECT id,ts,username,action,entity,entity_id,detail,ip FROM audit_log" + w +
                    " ORDER BY id DESC LIMIT ? OFFSET ?", params + [per_page, (max(page, 1) - 1) * per_page])
    return {"total": total, "page": page, "per_page": per_page,
            "entries": [dict(r, detail=json.loads(r["detail"] or "{}")) for r in rows]}


def verify_chain(db):
    prev, n = GENESIS, 0
    for r in db.query("SELECT * FROM audit_log ORDER BY id"):
        expect = _digest(prev, r["ts"], r["user_id"], r["username"], r["action"], r["entity"], r["entity_id"], r["detail"], r["ip"])
        if r["prev_hash"] != prev or r["hash"] != expect:
            return {"ok": False, "checked": n, "broken_at": r["id"]}
        prev, n = r["hash"], n + 1
    return {"ok": True, "checked": n}
