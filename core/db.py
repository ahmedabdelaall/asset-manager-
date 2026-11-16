# -*- coding: utf-8 -*-
"""SQLite access layer with versioned migrations and safe backups."""
import os
import re
import time
import sqlite3
import hashlib
import threading
from contextlib import contextmanager


class MigrationError(Exception):
    pass


class Database:
    def __init__(self, path, migrations_dir, backups_dir=None):
        self.path = path
        self.migrations_dir = migrations_dir
        self.backups_dir = backups_dir
        self._local = threading.local()

    # ------------------------------------------------------------ connections
    def conn(self):
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=10, isolation_level=None, check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=8000")
            self._local.c = c
        return c

    def close_thread(self):
        c = getattr(self._local, "c", None)
        if c is not None:
            c.close()
            self._local.c = None

    def query(self, sql, params=()):
        return self.conn().execute(sql, params).fetchall()

    def one(self, sql, params=()):
        return self.conn().execute(sql, params).fetchone()

    def execute(self, sql, params=()):
        return self.conn().execute(sql, params)

    @contextmanager
    def tx(self):
        c = self.conn()
        if c.in_transaction:           # nested: join the outer transaction
            yield c
            return
        c.execute("BEGIN IMMEDIATE")
        try:
            yield c
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise

    # ------------------------------------------------------------ migrations
    def _migration_files(self):
        out = []
        for f in sorted(os.listdir(self.migrations_dir)):
            m = re.match(r"^(\d{4})_([a-z0-9_]+)\.sql$", f)
            if m:
                out.append((m.group(1), f))
        return out

    def migrate(self):
        """Apply pending migrations in order. A backup is taken first if the database already has data."""
        c = self.conn()
        c.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                  "version TEXT PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)")
        applied = {r["version"]: r["checksum"] for r in self.query("SELECT version, checksum FROM schema_migrations")}
        files = self._migration_files()
        pending, backed_up = [], False
        for ver, fname in files:
            with open(os.path.join(self.migrations_dir, fname), "rb") as f:
                body = f.read()
            checksum = hashlib.sha256(body).hexdigest()
            if ver in applied:
                if applied[ver] != checksum:
                    raise MigrationError("Migration %s was modified after being applied. Never edit applied "
                                         "migrations - add a new one instead." % fname)
                continue
            pending.append((ver, fname, body.decode("utf-8"), checksum))
        if not pending:
            return []
        if applied and self.backups_dir:
            self.backup("before-migration-" + pending[0][0])
        done = []
        for ver, fname, sql, checksum in pending:
            script = ("BEGIN;\n" + sql + "\nINSERT INTO schema_migrations(version,name,checksum,applied_at) VALUES ('%s','%s','%s','%s');\nCOMMIT;"
                      % (ver, fname, checksum, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
            try:
                c.executescript(script)
            except Exception as e:
                try:
                    c.execute("ROLLBACK")
                except Exception:
                    pass
                raise MigrationError("Migration %s failed and was rolled back: %s" % (fname, e))
            done.append(fname)
        return done

    def schema_version(self):
        r = self.one("SELECT MAX(version) v FROM schema_migrations")
        return r["v"] if r and r["v"] else "0000"

    # ------------------------------------------------------------ backups
    def backup(self, reason="manual"):
        if not self.backups_dir:
            raise MigrationError("No backup folder configured.")
        os.makedirs(self.backups_dir, exist_ok=True)
        dest = os.path.join(self.backups_dir, "data_%s_%s.db" % (time.strftime("%Y%m%d_%H%M%S"), re.sub(r"[^a-z0-9\-]", "", reason.lower())))
        n = 1
        while os.path.exists(dest):
            n += 1
            dest = dest[:-3] + "_%d.db" % n
        dst = sqlite3.connect(dest)
        try:
            self.conn().backup(dst)
        finally:
            dst.close()
        return dest

    def prune_backups(self, keep):
        files = sorted(f for f in os.listdir(self.backups_dir) if f.startswith("data_") and f.endswith(".db"))
        for old in files[:-keep] if keep > 0 else []:
            try:
                os.remove(os.path.join(self.backups_dir, old))
            except OSError:
                pass

    def list_backups(self):
        if not self.backups_dir or not os.path.isdir(self.backups_dir):
            return []
        out = []
        for f in os.listdir(self.backups_dir):
            if f.startswith("data_") and f.endswith(".db"):
                st = os.stat(os.path.join(self.backups_dir, f))
                out.append({"name": f, "size": st.st_size, "ts": int(st.st_mtime)})
        out.sort(key=lambda x: x["ts"], reverse=True)
        return out
