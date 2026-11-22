# -*- coding: utf-8 -*-
"""System health: one place that answers "is this installation safe?" - used by the admin page and `manage.py check`.

Each check returns {"key", "state": "ok"|"warn"|"fail", "value", ...}. Nothing here changes data."""
import os
import time
import shutil

from . import audit, backup, licensing

BACKUP_WARN_HOURS = 36
DISK_WARN_BYTES = 1024 ** 3          # 1 GB


def run(db, inst, migrations_dir, deep=True):
    checks = []
    add = lambda key, state, value="", **extra: checks.append(dict(extra, key=key, state=state, value=value))

    r = db.one("PRAGMA integrity_check" if deep else "PRAGMA quick_check")[0]
    add("database", "ok" if r == "ok" else "fail", r if r != "ok" else "")
    fk = db.query("PRAGMA foreign_key_check")
    add("foreign_keys", "ok" if not fk else "fail", len(fk))

    latest = sorted(f[:4] for f in os.listdir(migrations_dir) if f.endswith(".sql"))[-1]
    cur = db.schema_version()
    add("schema", "ok" if cur == latest else "fail", cur, expected=latest)

    if deep:                                   # re-hashes the whole audit trail - only in the full check
        v = audit.verify_chain(db)
        add("audit_chain", "ok" if v["ok"] else "fail", v["checked"], broken_at=v.get("broken_at"))

    missing = 0
    referenced = set()
    for d in db.query("SELECT stored FROM documents"):
        referenced.add(d["stored"])
        if not os.path.isfile(os.path.join(inst.uploads_dir, *d["stored"].split("/"))):
            missing += 1
    add("documents_missing", "ok" if not missing else "fail", missing)
    orphans = 0
    docs_dir = os.path.join(inst.uploads_dir, "docs")
    if os.path.isdir(docs_dir):
        for base, _, names in os.walk(docs_dir):
            for fn in names:
                rel = os.path.relpath(os.path.join(base, fn), inst.uploads_dir).replace(os.sep, "/")
                if rel not in referenced:
                    orphans += 1
    add("documents_orphans", "ok" if not orphans else "warn", orphans)

    fulls = [b for b in backup.list_all(inst) if b["kind"] == "full"]
    if not fulls:
        add("last_backup", "warn", None)
    else:
        age_h = (time.time() - fulls[0]["ts"]) / 3600
        add("last_backup", "ok" if age_h <= BACKUP_WARN_HOURS else "warn", round(age_h, 1), name=fulls[0]["name"])

    du = shutil.disk_usage(inst.path)
    add("disk_free", "ok" if du.free >= DISK_WARN_BYTES else "warn", du.free)

    st = licensing.compute_status(db, inst)
    add("license", "ok" if st["state"] in ("valid", "disabled") else ("warn" if st["state"] == "grace" else "fail"), st["state"])

    size = sum(os.path.getsize(inst.db_path + ext) for ext in ("", "-wal") if os.path.exists(inst.db_path + ext))
    add("database_size", "ok", size)

    worst = "fail" if any(c["state"] == "fail" for c in checks) else "warn" if any(c["state"] == "warn" for c in checks) else "ok"
    return {"state": worst, "checks": checks, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
