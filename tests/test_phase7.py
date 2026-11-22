# -*- coding: utf-8 -*-
"""Phase 7: full backups (database + files), verification, restore drill, health checks, hardening."""
import io
import os
import json
import shutil
import hashlib
import zipfile
import unittest
import urllib.parse
import http.client

from test_assets import InvBase
from helpers import Client, SETUP
from core import backup, health
from core.server import App, MIGRATIONS

PDF = b"%PDF-1.4\n% receipt\n" + os.urandom(3000)
PNG = b"\x89PNG\r\n\x1a\n" + os.urandom(500)
TABLES = ("users", "company", "categories", "category_fields", "employees", "departments", "assets", "assignments", "documents", "audit_log")


def snapshot(db, inst):
    tables = {t: [tuple(r) for r in db.query("SELECT * FROM %s ORDER BY 1" % t)] for t in TABLES}
    files = {}
    for base, _, names in os.walk(inst.uploads_dir):
        for fn in names:
            p = os.path.join(base, fn)
            files[os.path.relpath(p, inst.uploads_dir)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return tables, files


class TestBackupRestore(InvBase):
    def populate(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c, serial_no="SN-1")
        g = c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[1]["id"]
        for ent, eid, data, name in (("asset", aid, PDF, "invoice.pdf"), ("assignment", g, PDF, "signed.pdf"), ("employee", self.emp, PNG, "id.png")):
            s, js, _ = c.post("/api/documents?entity=%s&id=%d" % (ent, eid), raw=data, headers={"X-Filename": urllib.parse.quote(name)})
            self.assertEqual(s, 201, js)
        self.assertEqual(c.post("/api/company/logo", raw=PNG)[0], 200)
        return c, aid

    def test_restore_drill_brings_back_database_and_files(self):
        c, aid = self.populate()
        inst = self.env.app.inst
        before = snapshot(self.env.app.db, inst)          # the state the backup captures (its own audit entry comes after)
        s, js, _ = c.post("/api/backups")
        self.assertEqual(s, 200, js)
        name = js["file"]
        self.assertTrue(name.startswith("backup_") and name.endswith(".zip"))
        v = c.post("/api/backups/%s/verify" % name)[1]["result"]
        self.assertTrue(v["ok"], v)
        self.assertEqual(v["counts"]["assets"], 1)
        self.assertGreaterEqual(v["files"], 5)                                   # data.db + 3 documents + logo
        # disaster: files deleted, data changed
        shutil.rmtree(os.path.join(inst.uploads_dir, "docs"))
        self.new_asset(c, name="Created after the backup")
        c.put("/api/company", {"name_en": "Changed", "primary_color": "#111111", "accent_color": "#222222"})
        self.assertEqual(health.run(self.env.app.db, inst, MIGRATIONS)["state"], "fail")   # missing documents detected
        # restore (server stopped, as the CLI requires)
        self.env.httpd.shutdown()
        safety, res = backup.restore(self.env.app.db, inst, os.path.join(inst.backups_dir, name))
        self.assertTrue(os.path.basename(safety).startswith("backup_") and "before-restore" in safety)
        app2 = App(inst.path)
        after = snapshot(app2.db, inst)
        self.assertEqual(after[1], before[1])                                    # every uploaded file, byte for byte
        for t in TABLES:
            self.assertEqual(after[0][t], before[0][t], t)                      # every table row
        h = health.run(app2.db, inst, MIGRATIONS)
        states = {c["key"]: c["state"] for c in h["checks"]}
        self.assertEqual((states["database"], states["audit_chain"], states["documents_missing"], states["schema"]), ("ok", "ok", "ok", "ok"))
        # the safety backup itself is restorable
        self.assertTrue(backup.verify(safety)["ok"])
        app2.db.close_thread()

    def test_tampered_and_unsafe_archives_are_refused(self):
        c, _ = self.populate()
        name = c.post("/api/backups")[1]["file"]
        src = os.path.join(self.env.app.inst.backups_dir, name)
        # change one uploaded file inside the archive (manifest unchanged)
        bad = src.replace(".zip", "_9.zip")
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(bad, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("uploads/docs/"):
                    data = data[:-1] + bytes([data[-1] ^ 1])
                zout.writestr(item, data)
        r = backup.verify(bad)
        self.assertFalse(r["ok"])
        self.assertTrue(any(p.startswith("file_changed:") for p in r["problems"]), r)
        with self.assertRaises(backup.BackupError):
            backup.restore(self.env.app.db, self.env.app.inst, bad)
        # path-traversal member names are rejected
        evil = os.path.join(self.env.app.inst.backups_dir, "backup_20260101_000000_evil.zip")
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(evil, "w") as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("../../escape.txt", b"x")
        self.assertIn("archive_unsafe", backup.verify(evil)["problems"])
        # garbage and truncated files
        junk = os.path.join(self.env.app.inst.backups_dir, "backup_20260101_000001_junk.zip")
        open(junk, "wb").write(open(src, "rb").read()[:200])
        self.assertFalse(backup.verify(junk)["ok"])

    def test_download_listing_retention_and_permissions(self):
        c, _ = self.populate()
        names = [c.post("/api/backups")[1]["file"] for _ in range(3)]
        listed = c.get("/api/backups")[1]["backups"]
        self.assertTrue(all(b["kind"] in ("full", "db") for b in listed))
        self.assertEqual({b["name"] for b in listed if b["kind"] == "full"} >= set(names), True)
        h = http.client.HTTPConnection("127.0.0.1", self.env.port, timeout=15)
        h.request("GET", "/api/backups/%s/download" % names[0], headers={"Host": "127.0.0.1:%d" % self.env.port, "Cookie": "am_session=" + c.cookie})
        resp = h.getresponse()
        data = resp.read()
        self.assertEqual((resp.status, resp.getheader("Content-Type")), (200, "application/zip"))
        self.assertEqual(data, open(os.path.join(self.env.app.inst.backups_dir, names[0]), "rb").read())
        self.assertEqual(c.get("/api/backups/..%2fdata.db/download")[0], 404)
        self.assertEqual(c.get("/api/backups/data.db/download")[0], 404)
        self.make_user(c, "cadmin", "company_admin")
        a = self.login_as("cadmin")
        self.assertEqual(a.get("/api/backups")[0], 200)                                    # can see the list ...
        self.assertEqual(a.get("/api/backups/%s/download" % names[0])[0], 403)          # ... but not download data
        # retention keeps the newest N full backups
        self.env.app.inst.config["backup_keep"] = 2
        c.post("/api/backups")
        fulls = [b for b in c.get("/api/backups")[1]["backups"] if b["kind"] == "full"]
        self.assertEqual(len(fulls), 2)
        actions = [e["action"] for e in c.get("/api/audit?action=backup.")[1]["entries"]]
        self.assertIn("backup.download", actions)

    def test_health_endpoint(self):
        c, _ = self.populate()
        r = c.get("/api/system/health?deep=1")[1]
        states = {x["key"]: x["state"] for x in r["checks"]}
        self.assertEqual(states["last_backup"], "warn")                                  # no full backup yet
        c.post("/api/backups")
        states = {x["key"]: x["state"] for x in c.get("/api/system/health")[1]["checks"]}
        self.assertEqual((states["last_backup"], states["database"], states["license"]), ("ok", "ok", "ok"))
        stray = os.path.join(self.env.app.inst.uploads_dir, "docs", "2026-01", "stray.pdf")
        os.makedirs(os.path.dirname(stray), exist_ok=True)
        open(stray, "wb").write(b"x")
        states = {x["key"]: x["state"] for x in c.get("/api/system/health")[1]["checks"]}
        self.assertEqual(states["documents_orphans"], "warn")


class TestHardening(InvBase):
    def test_security_headers_and_slow_clients(self):
        c = Client(self.env)
        s, _, r = c.get("/api/health")
        self.assertEqual(r.getheader("Cross-Origin-Opener-Policy"), "same-origin")
        self.assertIn("camera=()", r.getheader("Permissions-Policy"))
        from core.server import make_handler
        self.assertTrue(0 < make_handler(self.env.app).timeout <= 120)                    # idle connections are dropped

    def test_single_line_fields_drop_line_breaks(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c, name="Line1\r\nBcc: x@evil.test", notes="first line\nsecond line")
        a = c.get("/api/assets/%d" % aid)[1]
        self.assertEqual(a["name"], "Line1 Bcc: x@evil.test")
        self.assertEqual(a["notes"], "first line\nsecond line")                         # multi-line fields keep them


if __name__ == "__main__":
    unittest.main(verbosity=1)
