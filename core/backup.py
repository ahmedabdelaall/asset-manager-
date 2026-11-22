# -*- coding: utf-8 -*-
"""Backups: complete archives (database + uploaded files), verification, restore, and the daily scheduler.

A full backup is one zip file  backup_<date>_<time>_<reason>.zip  containing
    data.db        - a consistent snapshot taken with SQLite's online backup API (safe while the app is running)
    uploads/...    - every uploaded file (documents, signed receipts, logo)
    manifest.json  - format, app version, schema, and the SHA-256 of every file
Verification re-hashes every file and runs SQLite's integrity check, so a damaged archive is never restored.
Database-only snapshots (data_*.db) are still taken automatically right before each upgrade."""
import os
import re
import json
import time
import shutil
import pathlib
import sqlite3
import hashlib
import logging
import zipfile
import threading

log = logging.getLogger("am.backup")

FULL_RX = re.compile(r"^backup_\d{8}_\d{6}_[a-z0-9\-]+(_\d+)?\.zip$")
DB_RX = re.compile(r"^data_\d{8}_\d{6}_[a-z0-9\-]+(_\d+)?\.db$")
FORMAT = 1


class BackupError(Exception):
    pass


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_name(name):
    return bool(FULL_RX.match(name) or DB_RX.match(name))


def path_of(inst, name):
    if not valid_name(name):
        raise BackupError("Unknown backup")
    p = os.path.join(inst.backups_dir, name)
    if not os.path.isfile(p):
        raise BackupError("Unknown backup")
    return p


# ------------------------------------------------------------------ create
def full_backup(db, inst, reason="manual"):
    from . import VERSION
    os.makedirs(inst.backups_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    reason = re.sub(r"[^a-z0-9\-]", "", reason.lower()) or "manual"
    dest = os.path.join(inst.backups_dir, "backup_%s_%s.zip" % (stamp, reason))
    n = 1
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(inst.backups_dir, "backup_%s_%s_%d.zip" % (stamp, reason, n))
    snap = dest + ".db.tmp"
    tmp = dest + ".tmp"
    try:
        dst = sqlite3.connect(snap)
        try:
            db.conn().backup(dst)
            schema = dst.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or "0000"
        finally:
            dst.close()
        files = {"data.db": {"sha256": _sha256_file(snap), "size": os.path.getsize(snap)}}
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
            z.write(snap, "data.db")
            up = inst.uploads_dir
            for base, _, names in os.walk(up):
                for fn in sorted(names):
                    full = os.path.join(base, fn)
                    rel = "uploads/" + os.path.relpath(full, up).replace(os.sep, "/")
                    files[rel] = {"sha256": _sha256_file(full), "size": os.path.getsize(full)}
                    z.write(full, rel, compress_type=zipfile.ZIP_STORED if fn.lower().endswith((".jpg", ".png", ".webp", ".pdf", ".docx", ".xlsx", ".gif")) else zipfile.ZIP_DEFLATED)
            manifest = {"format": FORMAT, "product": "asset-master", "app_version": VERSION, "schema": schema,
                        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "reason": reason, "files": files}
            z.writestr("manifest.json", json.dumps(manifest, indent=1))
        os.replace(tmp, dest)
    finally:
        for p in (snap, tmp):
            if os.path.exists(p):
                os.remove(p)
    return dest


def prune(inst, keep):
    """Keep the newest `keep` full backups and the newest `keep` database-only snapshots."""
    if keep <= 0 or not os.path.isdir(inst.backups_dir):
        return
    for rx in (FULL_RX, DB_RX):
        names = sorted(f for f in os.listdir(inst.backups_dir) if rx.match(f))
        for old in names[:-keep]:
            try:
                os.remove(os.path.join(inst.backups_dir, old))
            except OSError:
                pass


def list_all(inst):
    d = inst.backups_dir
    if not os.path.isdir(d):
        return []
    out = []
    for f in os.listdir(d):
        if FULL_RX.match(f) or DB_RX.match(f):
            st = os.stat(os.path.join(d, f))
            out.append({"name": f, "size": st.st_size, "ts": int(st.st_mtime), "kind": "full" if f.endswith(".zip") else "db"})
    out.sort(key=lambda x: (x["ts"], x["name"]), reverse=True)
    return out


# ------------------------------------------------------------------ verify
def _check_sqlite(path):
    con = sqlite3.connect(pathlib.Path(os.path.abspath(path)).as_uri() + "?mode=ro", uri=True)
    try:
        ok = con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        schema = con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        assets = con.execute("SELECT COUNT(*) FROM assets").fetchone()[0] if con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='assets'").fetchone() else 0
    finally:
        con.close()
    return ok, {"users": users, "assets": assets, "schema": schema}


def _safe_member(name):
    return not (name.startswith("/") or name.startswith("\\") or ".." in name.replace("\\", "/").split("/") or ":" in name)


def verify(path):
    """Returns {"ok", "problems": [...], "kind", "schema", "files", "counts", "app_version", "created"}."""
    res = {"ok": False, "problems": [], "kind": "full" if path.endswith(".zip") else "db", "files": 0}
    if res["kind"] == "db":
        try:
            ok, info = _check_sqlite(path)
        except Exception:
            res["problems"].append("database_unreadable")
            return res
        res.update(counts={"users": info["users"], "assets": info["assets"]}, schema=info["schema"], files=1)
        if not ok:
            res["problems"].append("database_damaged")
        res["ok"] = not res["problems"]
        return res
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        res["problems"].append("archive_unreadable")
        return res
    with z:
        names = set(z.namelist())
        if "manifest.json" not in names or "data.db" not in names:
            res["problems"].append("archive_incomplete")
            return res
        try:
            man = json.loads(z.read("manifest.json"))
        except ValueError:
            res["problems"].append("archive_incomplete")
            return res
        res.update(schema=man.get("schema"), app_version=man.get("app_version"), created=man.get("created"), files=len(man.get("files", {})))
        for name in names:
            if not _safe_member(name):
                res["problems"].append("archive_unsafe")
                return res
        for name, meta in man.get("files", {}).items():
            if name not in names:
                res["problems"].append("file_missing:" + name)
                continue
            h = hashlib.sha256()
            with z.open(name) as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != meta.get("sha256"):
                res["problems"].append("file_changed:" + name)
        tmp = path + ".verify.db"
        try:
            with z.open("data.db") as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst)
            ok, info = _check_sqlite(tmp)
            res["counts"] = {"users": info["users"], "assets": info["assets"]}
            if not ok:
                res["problems"].append("database_damaged")
        except Exception:
            res["problems"].append("database_unreadable")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    res["ok"] = not res["problems"]
    return res


# ------------------------------------------------------------------ restore (server must be stopped)
def restore(db, inst, path):
    """Replace the database and uploaded files with the backup's. The current state is first saved as a
    'before-restore' full backup. Returns (safety_backup_path, verify_result)."""
    v = verify(path)
    if not v["ok"]:
        raise BackupError("The backup failed verification: " + ", ".join(v["problems"]))
    safety = full_backup(db, inst, "before-restore") if os.path.exists(inst.db_path) else None
    db.close_thread()
    stage = os.path.join(inst.path, ".restore_%d" % int(time.time()))
    os.makedirs(stage)
    try:
        if v["kind"] == "full":
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    if name == "manifest.json":
                        continue
                    target = os.path.join(stage, *name.split("/"))
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with z.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        else:
            shutil.copy2(path, os.path.join(stage, "data.db"))
        for ext in ("-wal", "-shm"):
            if os.path.exists(inst.db_path + ext):
                os.remove(inst.db_path + ext)
        os.replace(os.path.join(stage, "data.db"), inst.db_path)
        if v["kind"] == "full":
            new_up = os.path.join(stage, "uploads")
            os.makedirs(new_up, exist_ok=True)
            old_up = inst.uploads_dir + ".old_%d" % int(time.time())
            if os.path.exists(inst.uploads_dir):
                os.replace(inst.uploads_dir, old_up)
            os.replace(new_up, inst.uploads_dir)
            shutil.rmtree(old_up, ignore_errors=True)
    except PermissionError:
        raise BackupError("The database is in use. Stop the server first, then run restore again.")
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return safety, v


# ------------------------------------------------------------------ scheduler
class BackupScheduler(threading.Thread):
    def __init__(self, db, inst):
        super().__init__(daemon=True)
        self.db, self.inst = db, inst
        self._halt = threading.Event()
        self._last_day = None

    def stop(self):
        self._halt.set()

    def run(self):
        while not self._halt.wait(60):
            hour = int(self.inst.config["auto_backup_hour"])
            if hour < 0:
                continue
            lt = time.localtime()
            if lt.tm_hour >= hour and self._last_day != lt.tm_yday:
                try:
                    full_backup(self.db, self.inst, "auto")
                    prune(self.inst, int(self.inst.config["backup_keep"]))
                    self._last_day = lt.tm_yday
                    log.info("Automatic backup done")
                except Exception as e:
                    log.error("Automatic backup failed: %s", e)
                finally:
                    self.db.close_thread()
