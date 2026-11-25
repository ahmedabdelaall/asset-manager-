# -*- coding: utf-8 -*-
"""JSON API for assets, categories, departments, employees and assignments (Phase 2),
documents, receipts, Excel import/export (Phase 3)."""
import json
import time
import urllib.parse

from . import inventory as inv, documents as docs, transfer, rbac, reports, operations as ops, notify
from .errors import ApiError
from .server import route, Raw

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _int(q, key, default):
    v = q.get(key, "")
    if v == "":
        return default
    try:
        return int(v)
    except ValueError:
        raise ApiError(400, "bad_request", "Bad request")


def _id(ctx):
    return int(ctx.params["id"])


# ---------------------------------------------------------------- categories
@route("GET", "/api/categories", perm=("assets.view", "categories.manage", "requests.create"))
def categories_list(ctx):
    return {"categories": inv.list_categories(ctx.db)}


@route("POST", "/api/categories", perm="categories.manage")
def categories_create(ctx):
    return 201, {"id": inv.create_category(ctx, ctx.json())}


@route("PUT", "/api/categories/<int:id>", perm="categories.manage")
def categories_update(ctx):
    inv.update_category(ctx, _id(ctx), ctx.json())
    return {}


@route("DELETE", "/api/categories/<int:id>", perm="categories.manage")
def categories_delete(ctx):
    inv.delete_category(ctx, _id(ctx))
    return {}


# ---------------------------------------------------------------- departments
@route("GET", "/api/departments", perm=("employees.view", "employees.manage"))
def departments_list(ctx):
    return {"departments": inv.list_departments(ctx.db)}


@route("POST", "/api/departments", perm="employees.manage")
def departments_create(ctx):
    return 201, {"id": inv.save_department(ctx, None, ctx.json())}


@route("PUT", "/api/departments/<int:id>", perm="employees.manage")
def departments_update(ctx):
    inv.save_department(ctx, _id(ctx), ctx.json())
    return {}


@route("DELETE", "/api/departments/<int:id>", perm="employees.manage")
def departments_delete(ctx):
    inv.delete_department(ctx, _id(ctx))
    return {}


# ---------------------------------------------------------------- employees
@route("GET", "/api/employees", perm="employees.view")
def employees_list(ctx):
    q = ctx.query
    return {"employees": inv.list_employees(ctx.db, q.get("q", "").strip(), q.get("status", ""), _int(q, "department", None))}


@route("GET", "/api/employees/lookup", perm=("employees.view", "assignments.manage", "requests.create"))
def employees_lookup(ctx):
    return {"employees": inv.lookup_employees(ctx.db, ctx.query.get("q", "").strip())}


@route("GET", "/api/employees/<int:id>", perm="employees.view")
def employees_get(ctx):
    return inv.get_employee(ctx.db, _id(ctx), inv.can_see_national_id(ctx.db, ctx.user))


@route("POST", "/api/employees", perm="employees.manage")
def employees_create(ctx):
    return 201, {"id": inv.save_employee(ctx, None, ctx.json())}


@route("PUT", "/api/employees/<int:id>", perm="employees.manage")
def employees_update(ctx):
    inv.save_employee(ctx, _id(ctx), ctx.json())
    return {}


@route("DELETE", "/api/employees/<int:id>", perm="employees.manage")
def employees_delete(ctx):
    inv.delete_employee(ctx, _id(ctx))
    return {}


# ---------------------------------------------------------------- assets
@route("GET", "/api/assets", perm="assets.view")
def assets_list(ctx):
    q = ctx.query
    return inv.list_assets(ctx.db, q.get("q", "").strip(), q.get("status", ""), _int(q, "category", None),
                           _int(q, "page", 1), _int(q, "per_page", 50), q.get("sort", "newest"))


@route("GET", "/api/public/asset", public=True, lic=False)
def public_asset(ctx):
    """The page a phone opens from a QR label when nobody is signed in (can be switched off in Company settings)."""
    if not notify.get_settings(ctx.db, ctx.app.inst)["public_scan_enabled"]:
        raise ApiError(403, "public_scan_off", "Sign in to see this asset")
    lim = ctx.app.scan_limiter
    if not lim.check(ctx.ip):
        raise ApiError(429, "too_many_attempts", "Too many attempts. Try again later.")
    lim.fail(ctx.ip)                                  # every look-up counts: slows down guessing tags one by one
    tag = ctx.query.get("tag", "").strip()[:40]
    if not tag:
        raise ApiError(404, "asset_not_found", "Asset not found")
    return inv.public_asset(ctx.db, tag)


@route("GET", "/api/assets/summary", perm="assets.view")
def assets_summary(ctx):
    return inv.summary(ctx.db)


@route("GET", "/api/assets/<int:id>", perm="assets.view")
def assets_get(ctx):
    return inv.get_asset(ctx.db, _id(ctx))


@route("POST", "/api/assets", perm="assets.manage")
def assets_create(ctx):
    aid, tag = inv.create_asset(ctx, ctx.json())
    return 201, {"id": aid, "tag": tag}


@route("PUT", "/api/assets/<int:id>", perm="assets.manage")
def assets_update(ctx):
    inv.update_asset(ctx, _id(ctx), ctx.json())
    return {}


@route("DELETE", "/api/assets/<int:id>", perm="assets.manage")
def assets_delete(ctx):
    inv.delete_asset(ctx, _id(ctx))
    return {}


@route("POST", "/api/assets/<int:id>/status", perm="assets.manage")
def assets_status(ctx):
    inv.set_status(ctx, _id(ctx), ctx.json())
    return {}


# ---------------------------------------------------------------- assignments
@route("POST", "/api/assets/<int:id>/assign", perm="assignments.manage")
def assets_assign(ctx):
    return 201, {"id": inv.assign(ctx, _id(ctx), ctx.json())}


@route("POST", "/api/assets/<int:id>/return", perm="assignments.manage")
def assets_return(ctx):
    inv.return_asset(ctx, _id(ctx), ctx.json())
    return {}


@route("GET", "/api/assignments", perm="assets.view")
def assignments_open(ctx):
    return {"assignments": inv.list_open_assignments(ctx.db, ctx.query.get("q", "").strip())}


@route("GET", "/api/assignments/<int:id>/receipt", perm="assets.view")
def assignments_receipt(ctx):
    kind = ctx.query.get("kind", "handover")
    if kind not in ("handover", "return"):
        raise ApiError(400, "bad_request", "Bad request")
    return inv.receipt(ctx.db, _id(ctx), kind, inv.can_see_national_id(ctx.db, ctx.user))


# ---------------------------------------------------------------- documents (permission depends on what they are attached to)
def _entity(ctx):
    return ctx.query.get("entity", ""), _int(ctx.query, "id", 0)


@route("GET", "/api/documents")
def documents_list(ctx):
    entity, eid = _entity(ctx)
    return {"documents": docs.list_for(ctx, entity, eid)}


@route("POST", "/api/documents")
def documents_add(ctx):
    entity, eid = _entity(ctx)
    did = docs.add(ctx, entity, eid, ctx.body, ctx.h.headers.get("X-Filename", ""),
                   urllib.parse.unquote(ctx.h.headers.get("X-Note", "")))
    return 201, {"id": did}


@route("GET", "/api/documents/<int:id>/file")
def documents_file(ctx):
    d, data = docs.file_for(ctx, _id(ctx))
    inline = ctx.query.get("inline") == "1" and d["mime"] in docs.INLINE
    return Raw(data, d["mime"], headers={"Content-Disposition": docs.disposition(d["filename"], inline), "Cache-Control": "private, no-store"})


@route("DELETE", "/api/documents/<int:id>")
def documents_delete(ctx):
    docs.remove(ctx, _id(ctx))
    return {}


# ---------------------------------------------------------------- Excel import / export
IMPORT_PERM = {"employees": "employees.manage", "assets": "assets.manage"}


def _need(ctx, perm):
    if not rbac.user_has(ctx.db, ctx.user, perm):
        raise ApiError(403, "forbidden", "You do not have permission")


def _lang(ctx):
    lang = ctx.query.get("lang") or ctx.user["lang"] or "en"
    return lang if lang in ("en", "ar") else "en"


def _xlsx(data, name):
    fn = "%s_%s.xlsx" % (name, time.strftime("%Y-%m-%d"))
    return Raw(data, XLSX, headers={"Content-Disposition": docs.disposition(fn, False), "Cache-Control": "no-store"})


@route("GET", "/api/import/template")
def import_template(ctx):
    kind = ctx.query.get("type", "")
    if kind not in IMPORT_PERM:
        raise ApiError(400, "bad_request", "Bad request")
    _need(ctx, IMPORT_PERM[kind])
    return _xlsx(transfer.template(ctx.db, kind, _lang(ctx)), kind + "_template")


def _mapping(ctx):
    """The Match columns choice, sent as JSON in the X-Mapping header ({column index: field}); absent = template names."""
    raw = ctx.h.headers.get("X-Mapping")
    if not raw:
        return None
    try:
        m = json.loads(urllib.parse.unquote(raw))
    except ValueError:
        raise ApiError(400, "bad_request", "Bad request")
    if not isinstance(m, dict):
        raise ApiError(400, "bad_request", "Bad request")
    return m


def _fname(ctx):
    return urllib.parse.unquote(ctx.h.headers.get("X-Filename", ""))


@route("POST", "/api/import/employees/columns", perm="employees.manage")
def import_employee_columns(ctx):
    return transfer.columns(ctx, "employees", ctx.body, _fname(ctx), _int(ctx.query, "sheet", 0))


@route("POST", "/api/import/assets/columns", perm="assets.manage")
def import_asset_columns(ctx):
    return transfer.columns(ctx, "assets", ctx.body, _fname(ctx), _int(ctx.query, "sheet", 0))


@route("POST", "/api/import/employees", perm="employees.manage")
def import_employees(ctx):
    q = ctx.query
    return transfer.import_employees(ctx, ctx.body, _fname(ctx), q.get("dry_run", "1") == "1", q.get("update") == "1",
                                     _mapping(ctx), _int(q, "sheet", 0))


@route("POST", "/api/import/assets", perm="assets.manage")
def import_assets(ctx):
    q = ctx.query
    return transfer.import_assets(ctx, ctx.body, _fname(ctx), q.get("dry_run", "1") == "1", q.get("update") == "1",
                                  _mapping(ctx), _int(q, "sheet", 0), q.get("category", ""), q.get("add_people") == "1")


@route("GET", "/api/export/assets", perm="assets.view")
def export_assets(ctx):
    q = ctx.query
    return _xlsx(transfer.export_assets(ctx.db, _lang(ctx), q.get("q", "").strip(), q.get("status", ""), _int(q, "category", None),
                                         q.get("sort", "newest")), "assets")


@route("GET", "/api/export/employees", perm="employees.view")
def export_employees(ctx):
    q = ctx.query
    return _xlsx(transfer.export_employees(ctx.db, _lang(ctx), q.get("q", "").strip(), q.get("status", ""), _int(q, "department", None),
                                           with_nid=inv.can_see_national_id(ctx.db, ctx.user)), "employees")


@route("GET", "/api/export/assignments", perm="assets.view")
def export_assignments(ctx):
    return _xlsx(transfer.export_assignments(ctx.db, _lang(ctx), ctx.query.get("open") == "1"), "assignments")


# ---------------------------------------------------------------- reports & analytics (Phase 4)
@route("GET", "/api/analytics", perm="assets.view")
def analytics(ctx):
    return reports.analytics(ctx.db)


@route("GET", r"/api/reports/(?P<name>[a-z]+)", perm="reports.view")
def report(ctx):
    name = ctx.params["name"]
    if name not in reports.REPORTS:
        raise ApiError(404, "not_found", "Not found")
    if name in reports.REPORT_PERM:
        _need(ctx, reports.REPORT_PERM[name])
    if ctx.query.get("format") == "xlsx":
        return _xlsx(reports.to_xlsx(name, reports.run(ctx.db, name, ctx.query), _lang(ctx)), "report_" + name)
    rep = reports.run(ctx.db, name, ctx.query, limit=reports.SCREEN_ROWS)
    total = rep.pop("total_rows", len(rep["rows"]))
    if total > reports.SCREEN_ROWS:                       # totals already cover every row; the Excel export has them all
        rep["truncated"] = total
        rep["rows"] = rep["rows"][:reports.SCREEN_ROWS]
    return rep


# ---------------------------------------------------------------- QR lookup (Phase 6)
@route("GET", "/api/assets/by-tag", perm="assets.view")
def assets_by_tag(ctx):
    tag = ctx.query.get("tag", "").strip()
    r = ctx.db.one("SELECT id FROM assets WHERE tag=?", (tag,)) if tag else None
    if r is None:
        raise ApiError(404, "asset_not_found", "Asset not found")
    return {"id": r["id"]}


@route("GET", "/api/assets/by-code", perm="assets.view")
def assets_by_code(ctx):
    """A code read from any QR/barcode on the device (manufacturer label, old sticker, IMEI barcode...):
    matches the asset tag, the serial number, or any custom field value (e.g. IMEI, phone number)."""
    code = " ".join((ctx.query.get("code") or "").split())[:300]
    if not code:
        raise ApiError(404, "asset_not_found", "Asset not found")
    db = ctx.db
    for how, sql in (("tag", "SELECT id, tag FROM assets WHERE tag=? COLLATE NOCASE"),
                     ("serial", "SELECT id, tag FROM assets WHERE serial_no=? COLLATE NOCASE"),
                     ("field", "SELECT a.id, a.tag FROM assets a, json_each(a.custom) j WHERE CAST(j.value AS TEXT)=?1 "
                               "OR (j.type IN ('integer','real') AND ?1 GLOB '[0-9]*' AND ?1 NOT GLOB '*[^0-9.]*' AND j.value = CAST(?1 AS REAL))")):
        rows = db.query(sql + " LIMIT 2", (code,))
        if rows:
            return {"id": rows[0]["id"], "tag": rows[0]["tag"], "matched": how, "more": len(rows) > 1}
    raise ApiError(404, "asset_not_found", "Asset not found")


@route("GET", "/api/labels", perm="assets.view")
def labels(ctx):
    ids = [int(x) for x in ctx.query.get("ids", "").split(",") if x.strip().isdigit()][:500]
    if not ids:
        raise ApiError(400, "bad_request", "Bad request")
    rows = ctx.db.query("SELECT a.id, a.tag, a.name, a.serial_no, c.name_en AS cat_en, c.name_ar AS cat_ar FROM assets a "
                        "JOIN categories c ON c.id=a.category_id WHERE a.id IN (%s) ORDER BY a.tag" % ",".join("?" * len(ids)), ids)
    return {"assets": [dict(r) for r in rows], "public_url": notify.get_settings(ctx.db, ctx.app.inst)["public_url"]}


# ---------------------------------------------------------------- maintenance
@route("GET", "/api/maintenance", perm="maintenance.view")
def maintenance_list(ctx):
    q = ctx.query
    return {"maintenance": ops.list_maintenance(ctx.db, q.get("status", ""), _int(q, "asset", None), q.get("q", "").strip())}


@route("POST", "/api/maintenance", perm="maintenance.manage")
def maintenance_create(ctx):
    return 201, {"id": ops.create_maintenance(ctx, ctx.json())}


@route("PUT", "/api/maintenance/<int:id>", perm="maintenance.manage")
def maintenance_update(ctx):
    ops.update_maintenance(ctx, _id(ctx), ctx.json())
    return {}


@route("POST", r"/api/maintenance/(?P<id>[0-9]+)/(?P<action>start|complete|cancel)", perm="maintenance.manage")
def maintenance_action(ctx):
    {"start": ops.start_maintenance, "complete": ops.complete_maintenance, "cancel": ops.cancel_maintenance}[ctx.params["action"]](ctx, _id(ctx), ctx.json())
    return {}


# ---------------------------------------------------------------- asset requests (approval workflow)
@route("GET", "/api/requests", perm=("requests.create", "requests.approve"))
def requests_list(ctx):
    mine = None if rbac.user_has(ctx.db, ctx.user, "requests.approve") else ctx.user["id"]
    return {"requests": ops.list_requests(ctx.db, ctx.query.get("status", ""), mine)}


@route("POST", "/api/requests", perm="requests.create")
def requests_create(ctx):
    if not notify.get_settings(ctx.db, ctx.app.inst)["asset_requests_enabled"]:
        raise ApiError(409, "requests_off", "Asset requests are switched off")
    return 201, {"id": ops.create_request(ctx, ctx.json())}


@route("GET", "/api/requests/<int:id>/candidates", perm="requests.approve")
def requests_candidates(ctx):
    r = ctx.db.one("SELECT category_id FROM asset_requests WHERE id=?", (_id(ctx),))
    if r is None:
        raise ApiError(404, "request_not_found", "Request not found")
    sql = ("SELECT a.id, a.tag, a.name, a.brand, a.model, a.condition, a.location, c.name_en AS cat_en, c.name_ar AS cat_ar FROM assets a "
           "JOIN categories c ON c.id=a.category_id WHERE a.status='in_stock'" + (" AND a.category_id=?" if r["category_id"] else "") +
           " ORDER BY a.tag LIMIT 300")
    return {"assets": [dict(x) for x in ctx.db.query(sql, (r["category_id"],) if r["category_id"] else ())]}


@route("POST", "/api/requests/<int:id>/approve", perm="requests.approve")
def requests_approve(ctx):
    return {"assignment_id": ops.approve_request(ctx, _id(ctx), ctx.json())}


@route("POST", "/api/requests/<int:id>/reject", perm="requests.approve")
def requests_reject(ctx):
    ops.reject_request(ctx, _id(ctx), ctx.json())
    return {}


@route("POST", "/api/requests/<int:id>/cancel", perm=("requests.create", "requests.approve"))
def requests_cancel(ctx):
    ops.cancel_request(ctx, _id(ctx), rbac.user_has(ctx.db, ctx.user, "requests.approve"))
    return {}


# ---------------------------------------------------------------- alerts & settings
@route("GET", "/api/alerts")
def alerts_get(ctx):
    return notify.alerts(ctx.db, ctx.app.inst, ctx.user)


@route("POST", "/api/alerts/dismiss")
def alerts_dismiss(ctx):
    notify.dismiss_alerts(ctx.db, ctx.user, ctx.json().get("keys"))
    return notify.alerts(ctx.db, ctx.app.inst, ctx.user)


@route("POST", "/api/alerts/restore")
def alerts_restore(ctx):
    notify.restore_alerts(ctx.db, ctx.user)
    return notify.alerts(ctx.db, ctx.app.inst, ctx.user)


@route("GET", "/api/settings", perm="company.view")
def settings_get(ctx):
    return notify.get_settings(ctx.db, ctx.app.inst)


@route("PUT", "/api/settings", perm="company.manage")
def settings_put(ctx):
    notify.save_settings(ctx, ctx.json())
    return {}


@route("POST", "/api/settings/test-email", perm="company.manage")
def settings_test(ctx):
    notify.send_test(ctx, ctx.json().get("to") or ctx.user["email"] or "")
    return {}


@route("POST", "/api/settings/send-digest", perm="company.manage")
def settings_digest(ctx):
    return notify.digest_report(ctx.db, ctx.app.inst, force=True)
