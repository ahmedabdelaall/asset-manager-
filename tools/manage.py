#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Administrator command line (run on the server / inside the container).

  python tools/manage.py --instance ./instances/default info
  python tools/manage.py --instance ./instances/default migrate
  python tools/manage.py --instance ./instances/default backup
  python tools/manage.py --instance ./instances/default restore data_20260101_020000_auto.db
  python tools/manage.py --instance ./instances/default reset-password <username>
  python tools/manage.py --instance ./instances/default request-code
In Docker:  docker compose exec assetmaster python tools/manage.py info
"""
import os
import sys
import shutil
import sqlite3
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def open_instance(path):
    from core.config import Instance
    from core.db import Database
    from core.server import MIGRATIONS
    inst = Instance(path)
    return inst, Database(inst.db_path, MIGRATIONS, inst.backups_dir)


def cmd_info(a):
    from core import VERSION, licensing
    inst, db = open_instance(a.instance)
    db.migrate()
    print("Product version :", VERSION)
    print("Instance folder :", inst.path)
    print("Database schema :", db.schema_version())
    n = db.one("SELECT COUNT(*) c FROM users")["c"]
    print("Users           :", n)
    st = licensing.compute_status(db, inst)
    print("Licence state   :", st["state"], "| expires:", (st["license"] or {}).get("expires_at"))
    print("Deployment ID   :", st["deployment_id"])


def cmd_migrate(a):
    inst, db = open_instance(a.instance)
    done = db.migrate()
    print("Applied:", ", ".join(done) if done else "nothing to do (already up to date)")


def cmd_backup(a):
    inst, db = open_instance(a.instance)
    db.migrate()
    p = db.backup("manual")
    db.prune_backups(int(inst.config["backup_keep"]))
    print("Backup written:", p)


def cmd_restore(a):
    """Stop the server first. The current database is kept as a safety copy before it is replaced."""
    inst, db = open_instance(a.instance)
    src = a.file if os.path.isabs(a.file) else os.path.join(inst.backups_dir, a.file)
    if not os.path.isfile(src):
        sys.exit("Backup file not found: " + src)
    chk = sqlite3.connect(src)
    try:
        ok = chk.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        chk.execute("SELECT COUNT(*) FROM users")
    except Exception as e:
        sys.exit("This does not look like a valid backup: %s" % e)
    finally:
        chk.close()
    if not ok:
        sys.exit("The backup failed the integrity check. Not restoring.")
    if os.path.exists(inst.db_path):
        safety = db.backup("before-restore")
        print("Current database saved as:", safety)
    db.close_thread()                      # release our own connection before replacing the file
    for ext in ("-wal", "-shm"):
        if os.path.exists(inst.db_path + ext):
            os.remove(inst.db_path + ext)
    tmp = inst.db_path + ".restore_tmp"
    shutil.copy2(src, tmp)
    os.replace(tmp, inst.db_path)
    inst2, db2 = open_instance(a.instance)
    print("Restored. Schema:", db2.schema_version(), "(pending migrations apply on next start)")
    db2.close_thread()


def cmd_reset_password(a):
    from core import security, audit
    inst, db = open_instance(a.instance)
    db.migrate()
    u = db.one("SELECT * FROM users WHERE username=?", (a.username.lower(),))
    if not u:
        sys.exit("No such user.")
    pw = a.password or security.temp_password()
    prob = security.password_problem(pw, u["username"])
    if prob:
        sys.exit("Password rejected: " + prob)
    with db.tx():
        db.execute("UPDATE users SET password_hash=?, must_change_password=1, failed_count=0, locked_until=0, is_active=1 WHERE id=?",
                   (security.hash_password(pw), u["id"]))
        db.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (u["id"],))
    audit.write(db, {"id": None, "username": "cli"}, "user.reset_password", "user", u["id"], {"via": "cli"}, "local")
    print("Temporary password for %s: %s   (must be changed at next sign-in)" % (u["username"], pw))


def cmd_request_code(a):
    from core import licensing, company
    inst, db = open_instance(a.instance)
    db.migrate()
    c = company.get(db)
    print(licensing.activation_request(db, inst, (c or {}).get("name_en", a.company or "")))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--instance", default=os.environ.get("AM_INSTANCE", os.path.join(ROOT, "instances", "default")))
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("info").set_defaults(f=cmd_info)
    sp.add_parser("migrate").set_defaults(f=cmd_migrate)
    sp.add_parser("backup").set_defaults(f=cmd_backup)
    r = sp.add_parser("restore"); r.add_argument("file"); r.set_defaults(f=cmd_restore)
    x = sp.add_parser("reset-password"); x.add_argument("username"); x.add_argument("--password"); x.set_defaults(f=cmd_reset_password)
    q = sp.add_parser("request-code"); q.add_argument("--company", default=""); q.set_defaults(f=cmd_request_code)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
