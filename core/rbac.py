# -*- coding: utf-8 -*-
"""Roles & permissions. The permission catalogue lives in code; each release can add new permissions
and they are granted to the built-in roles by default without overwriting an administrator's customisation."""
from .errors import ApiError

# (code, module)
CATALOG = [
    ("dashboard.view", "dashboard"),
    ("users.view", "users"), ("users.manage", "users"),
    ("roles.view", "roles"), ("roles.manage", "roles"),
    ("company.view", "company"), ("company.manage", "company"),
    ("license.view", "license"), ("license.manage", "license"),
    ("audit.view", "audit"), ("audit.verify", "audit"),
    ("backup.view", "backup"), ("backup.manage", "backup"),
    ("assets.view", "assets"), ("assets.manage", "assets"), ("categories.manage", "assets"),
    ("assignments.manage", "assignments"),
    ("employees.view", "employees"), ("employees.manage", "employees"),
    ("reports.view", "reports"),
    ("maintenance.view", "maintenance"), ("maintenance.manage", "maintenance"),
    ("requests.create", "requests"), ("requests.approve", "requests"),
]
ASSET_PERMS = ["assets.view", "assets.manage", "categories.manage", "assignments.manage", "employees.view"]

# key -> (name_en, name_ar, description, all_permissions, default permission list)
SYSTEM_ROLES = {
    "super_admin": ("Super Administrator", "المدير الأعلى", "Full control, including licensing and system settings.", 1, []),
    "company_admin": ("Company Administrator", "مدير الشركة", "Manages users, roles and company settings.", 0,
                      ["dashboard.view", "users.view", "users.manage", "roles.view", "roles.manage", "company.view",
                       "company.manage", "license.view", "audit.view", "backup.view"] + ASSET_PERMS +
                      ["employees.manage", "reports.view", "maintenance.view", "maintenance.manage", "requests.create", "requests.approve"]),
    "asset_manager": ("Asset Manager", "مدير الأصول", "Manages assets and assignments.", 0,
                      ["dashboard.view", "company.view"] + ASSET_PERMS +
                      ["reports.view", "maintenance.view", "maintenance.manage", "requests.create", "requests.approve"]),
    "hr": ("HR", "الموارد البشرية", "Manages employees and their documents.", 0,
           ["dashboard.view", "company.view", "employees.view", "employees.manage", "assets.view", "reports.view", "requests.create"]),
    "viewer": ("Viewer", "مشاهد", "Read-only access.", 0, ["dashboard.view", "assets.view", "employees.view", "reports.view", "maintenance.view"]),
}
# Permissions that only the Super Administrator can grant or hold implicitly
SUPER_ONLY = {"license.manage", "backup.manage", "audit.verify"}


def sync(db):
    """Make the database match the code catalogue. Safe to run on every start."""
    with db.tx():
        known = {r["code"] for r in db.query("SELECT code FROM permissions")}
        new = [(c, m) for c, m in CATALOG if c not in known]
        for c, m in new:
            db.execute("INSERT INTO permissions(code,module) VALUES (?,?)", (c, m))
        for key, (en, ar, desc, allp, perms) in SYSTEM_ROLES.items():
            row = db.one("SELECT id FROM roles WHERE key=?", (key,))
            if row is None:
                db.execute("INSERT INTO roles(key,name_en,name_ar,description,is_system,all_permissions) VALUES (?,?,?,?,1,?)",
                           (key, en, ar, desc, allp))
                row = db.one("SELECT id FROM roles WHERE key=?", (key,))
                grant = perms
            else:
                grant = [p for p in perms if p in {c for c, _ in new}]
            for p in grant:
                db.execute("INSERT OR IGNORE INTO role_permissions(role_id,perm_code) VALUES (?,?)", (row["id"], p))


def role_permissions(db, role_id):
    r = db.one("SELECT all_permissions FROM roles WHERE id=?", (role_id,))
    if r is None:
        return set()
    if r["all_permissions"]:
        return {c for c, _ in CATALOG}
    return {x["perm_code"] for x in db.query("SELECT perm_code FROM role_permissions WHERE role_id=?", (role_id,))}


def user_has(db, user, perm):
    return perm in role_permissions(db, user["role_id"])


def is_super(db, user):
    r = db.one("SELECT all_permissions FROM roles WHERE id=?", (user["role_id"],))
    return bool(r and r["all_permissions"])


def can_assign_role(db, actor, role_id):
    """An administrator may only hand out roles that are no more powerful than their own."""
    r = db.one("SELECT all_permissions FROM roles WHERE id=?", (role_id,))
    if r is None:
        raise ApiError(422, "role_not_found", "Role not found", field="role_id")
    if is_super(db, actor):
        return True
    if r["all_permissions"]:
        return False
    return role_permissions(db, role_id) <= role_permissions(db, actor["role_id"])


def list_roles(db):
    out = []
    for r in db.query("SELECT r.*, (SELECT COUNT(*) FROM users u WHERE u.role_id=r.id) AS users FROM roles r ORDER BY r.is_system DESC, r.id"):
        d = dict(r)
        d["permissions"] = sorted(role_permissions(db, r["id"]))
        out.append(d)
    return out
