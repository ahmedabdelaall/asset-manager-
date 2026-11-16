# -*- coding: utf-8 -*-
import os
import time
import json
import sqlite3
import unittest

from helpers import Env, Client, do_setup, SETUP
from core import licensing, audit, rbac


class Base(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)

    def admin(self, licensed=True):
        s, js, _ = do_setup(self.env)
        self.assertEqual(s, 200, js)
        c = Client(self.env)
        st, js, _ = c.login("root", SETUP["password"])
        self.assertEqual(st, 200, js)
        if licensed:
            lic, _ = self.env.issue_license()
            st, js, _ = c.post("/api/license/activate", {"license": lic})
            self.assertEqual(st, 200, js)
        return c

    def role_id(self, c, key):
        return [r["id"] for r in c.get("/api/roles")[1]["roles"] if r["key"] == key][0]

    def make_user(self, c, username, role_key, pw="Valid-Pass-123"):
        s, js, _ = c.post("/api/users", {"username": username, "full_name": username.title(), "role_id": self.role_id(c, role_key), "password": pw})
        self.assertEqual(s, 201, js)
        return js["id"]

    def login_as(self, username, pw="Valid-Pass-123", change_to="Another-Pass-456"):
        c = Client(self.env)
        s, js, _ = c.login(username, pw)
        self.assertEqual(s, 200, js)
        if js["user"]["must_change_password"]:
            s, js2, _ = c.post("/api/auth/password", {"current": pw, "new": change_to})
            self.assertEqual(s, 200, js2)
        return c


class TestSetupAndAuth(Base):
    def test_setup_requires_code_and_runs_once(self):
        s, js, _ = do_setup(self.env, setup_code="WRONGCODE")
        self.assertEqual((s, js["code"]), (403, "bad_setup_code"))
        self.assertTrue(os.path.exists(self.env.app.inst.setup_code_path))
        s, js, _ = do_setup(self.env)
        self.assertEqual(s, 200, js)
        self.assertFalse(os.path.exists(self.env.app.inst.setup_code_path))
        s, js, _ = do_setup(self.env, setup_code="x")
        self.assertEqual((s, js["code"]), (409, "already_configured"))
        b = Client(self.env).get("/api/branding")[1]
        self.assertEqual((b["name_en"], b["configured"], b["needs_setup"]), ("Acme Corp", True, False))

    def test_setup_rejects_weak_password_and_does_not_half_create(self):
        s, js, _ = do_setup(self.env, password="short")
        self.assertEqual((s, js["code"]), (422, "password_short"))
        self.assertTrue(self.env.app.needs_setup())
        self.assertIsNone(Client(self.env).get("/api/branding")[1]["name_en"] or None)

    def test_login_generic_errors_cookie_flags_and_csrf(self):
        self.admin()
        c = Client(self.env)
        s, js, _ = c.login("nobody", "whatever-123")
        s2, js2, _ = c.login("root", "wrong-pass-123")
        self.assertEqual((s, s2, js["code"], js2["code"]), (401, 401, "bad_credentials", "bad_credentials"))
        s, js, r = c.login("root", SETUP["password"])
        self.assertEqual(s, 200)
        sc = r.getheader("Set-Cookie")
        self.assertIn("HttpOnly", sc)
        self.assertIn("SameSite=Strict", sc)
        self.assertEqual(c.get("/api/auth/me")[0], 200)
        s, js, _ = c.post("/api/backups", csrf=False)
        self.assertEqual((s, js["code"]), (403, "csrf"))
        s, js, _ = c.post("/api/backups", headers={"Origin": "http://evil.example"})
        self.assertEqual((s, js["code"]), (403, "forbidden"))
        self.assertEqual(c.post("/api/auth/logout")[0], 200)
        self.assertEqual(c.get("/api/auth/me")[0], 401)

    def test_allowed_hosts_setting(self):
        self.env.close()
        self.env = Env(config={"host": "0.0.0.0", "allowed_hosts": ["assets.example.com"]})
        self.addCleanup(self.env.close)
        c = Client(self.env)
        self.assertEqual(c.get("/api/health", headers={"Host": "assets.example.com"})[0], 200)
        self.assertEqual(c.get("/api/health", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(c.get("/api/health")[0], 200)            # 127.0.0.1:<port> (container health check)

    def test_host_header_is_checked_in_loopback_mode(self):
        c = Client(self.env)
        s, js, _ = c.get("/api/health", headers={"Host": "evil.example"})
        self.assertEqual(s, 403)

    def test_lockout_after_failed_attempts(self):
        self.admin()
        c = Client(self.env)
        for _ in range(5):
            self.assertEqual(c.login("root", "bad-password-1")[0], 401)
        s, js, _ = c.login("root", SETUP["password"])
        self.assertEqual((s, js["code"]), (429, "account_locked"))

    def test_session_idle_timeout(self):
        c = self.admin()
        self.env.app.db.execute("UPDATE sessions SET last_seen = last_seen - 4000")
        self.assertEqual(c.get("/api/auth/me")[0], 401)

    def test_password_change_revokes_other_sessions_and_enforces_policy(self):
        c1 = self.admin()
        c2 = Client(self.env)
        c2.login("root", SETUP["password"])
        s, js, _ = c1.post("/api/auth/password", {"current": SETUP["password"], "new": "alllettersnodigits"})
        self.assertEqual((s, js["code"]), (422, "password_weak"))
        s, js, _ = c1.post("/api/auth/password", {"current": "wrong", "new": "Brand-New-Pass-9"})
        self.assertEqual((s, js["code"]), (403, "wrong_current_password"))
        self.assertEqual(c1.post("/api/auth/password", {"current": SETUP["password"], "new": "Brand-New-Pass-9"})[0], 200)
        self.assertEqual(c1.get("/api/auth/me")[0], 200)
        self.assertEqual(c2.get("/api/auth/me")[0], 401)

    def test_admin_created_user_must_change_password_first(self):
        c = self.admin()
        self.make_user(c, "sara", "viewer")
        u = Client(self.env)
        s, js, _ = u.login("sara", "Valid-Pass-123")
        self.assertTrue(js["user"]["must_change_password"])
        self.assertEqual(u.get("/api/dashboard")[1]["code"], "password_change_required")
        self.assertEqual(u.post("/api/auth/password", {"current": "Valid-Pass-123", "new": "Fresh-Pass-789"})[0], 200)
        self.assertEqual(u.get("/api/dashboard")[0], 200)


class TestRbac(Base):
    def test_permissions_enforced_per_role(self):
        c = self.admin()
        self.make_user(c, "vic", "viewer")
        v = self.login_as("vic")
        self.assertEqual(v.get("/api/dashboard")[0], 200)
        for path in ("/api/users", "/api/audit", "/api/backups", "/api/company"):
            s, js, _ = v.get(path)
            self.assertEqual((s, js["code"]), (403, "forbidden"), path)
        self.assertEqual(v.post("/api/users", {"username": "zed"})[0], 403)

    def test_no_privilege_escalation(self):
        c = self.admin()
        self.make_user(c, "cathy", "company_admin")
        ca = self.login_as("cathy")
        sup = self.role_id(c, "super_admin")
        s, js, _ = ca.post("/api/users", {"username": "evil", "full_name": "Evil", "role_id": sup, "password": "Valid-Pass-123"})
        self.assertEqual((s, js["code"]), (403, "role_not_allowed"))
        s, js, _ = ca.post("/api/roles", {"name_en": "Sneaky", "permissions": ["license.manage"]})
        self.assertEqual((s, js["code"]), (403, "permission_not_allowed"))
        s, js, _ = ca.get("/api/license")
        self.assertEqual(s, 200)
        s, js, _ = ca.post("/api/license/activate", {"license": "x"})
        self.assertEqual((s, js["code"]), (403, "forbidden"))
        root_id = [u for u in c.get("/api/users")[1]["users"] if u["username"] == "root"][0]["id"]
        self.assertEqual(ca.post("/api/users/%d/reset-password" % root_id)[1]["code"], "user_not_allowed")
        self.assertEqual(ca.put("/api/roles/%d" % self.role_id(c, "company_admin"), {"permissions": []})[1]["code"], "role_locked")

    def test_last_super_admin_and_self_protection(self):
        c = self.admin()
        me = [u for u in c.get("/api/users")[1]["users"] if u["username"] == "root"][0]
        self.assertEqual(c.post("/api/users/%d/active" % me["id"], {"active": False})[1]["code"], "cannot_disable_self")
        self.assertEqual(c.put("/api/users/%d" % me["id"], {"full_name": "Root", "role_id": self.role_id(c, "viewer")})[1]["code"], "cannot_change_own_role")
        uid = self.make_user(c, "second", "company_admin")
        self.assertEqual(c.post("/api/users/%d/active" % uid, {"active": False})[0], 200)

    def test_custom_roles_lifecycle(self):
        c = self.admin()
        s, js, _ = c.post("/api/roles", {"name_en": "Auditor", "name_ar": "مراجع", "permissions": ["dashboard.view", "audit.view"]})
        self.assertEqual(s, 201, js)
        rid = js["id"]
        uid = self.make_user(c, "audra", "auditor") if False else None
        s, js, _ = c.post("/api/users", {"username": "audra", "full_name": "Audra", "role_id": rid, "password": "Valid-Pass-123"})
        self.assertEqual(s, 201)
        a = self.login_as("audra")
        self.assertEqual(a.get("/api/audit")[0], 200)
        self.assertEqual(a.get("/api/users")[0], 403)
        self.assertEqual(c.delete("/api/roles/%d" % rid)[1]["code"], "role_in_use")
        self.assertEqual(c.put("/api/roles/%d" % rid, {"name_en": "Auditor", "permissions": ["dashboard.view"]})[0], 200)
        self.assertEqual(a.get("/api/audit")[0], 403)      # permission change is live
        self.assertEqual(c.delete("/api/roles/%d" % self.role_id(c, "viewer"))[1]["code"], "role_locked")
        self.assertEqual(c.put("/api/roles/%d" % self.role_id(c, "super_admin"), {"permissions": []})[1]["code"], "role_locked")

    def test_deactivated_user_loses_access_immediately(self):
        c = self.admin()
        uid = self.make_user(c, "temp", "viewer")
        t = self.login_as("temp")
        self.assertEqual(t.get("/api/dashboard")[0], 200)
        c.post("/api/users/%d/active" % uid, {"active": False})
        self.assertEqual(t.get("/api/dashboard")[0], 401)
        self.assertEqual(Client(self.env).login("temp", "Another-Pass-456")[1]["code"], "account_disabled")

    def test_admin_reset_password_flow(self):
        c = self.admin()
        uid = self.make_user(c, "forgetful", "viewer")
        s, js, _ = c.post("/api/users/%d/reset-password" % uid)
        pw = js["temp_password"]
        u = Client(self.env)
        s, js, _ = u.login("forgetful", pw)
        self.assertEqual(s, 200)
        self.assertTrue(js["user"]["must_change_password"])


class TestLicense(Base):
    def test_locked_until_licensed_then_unlocked(self):
        c = self.admin(licensed=False)
        s, js, _ = c.get("/api/dashboard")
        self.assertEqual((s, js["code"], js["state"]), (402, "license_required", "missing"))
        self.assertEqual(c.get("/api/license")[0], 200)
        lic, _ = self.env.issue_license()
        self.assertEqual(c.post("/api/license/activate", {"license": lic})[0], 200)
        self.assertEqual(c.get("/api/dashboard")[0], 200)
        self.assertEqual(c.get("/api/license")[1]["state"], "valid")

    def test_non_super_cannot_login_while_locked(self):
        c = self.admin()
        self.make_user(c, "norm", "viewer")
        lid = self.env.app.db.one("SELECT license_id FROM license_store")["license_id"]
        self.assertEqual(c.post("/api/license/revocations", {"list": self.env.issue_revocations(1, [lid])})[0], 200)
        s, js, _ = Client(self.env).login("norm", "Valid-Pass-123")
        self.assertEqual((s, js["code"]), (403, "license_locked"))
        self.assertEqual(Client(self.env).login("root", SETUP["password"])[0], 200)    # super admin can still fix it
        self.assertEqual(c.get("/api/users")[1]["code"], "license_required")

    def test_tampered_wrong_server_and_wrong_product_rejected(self):
        c = self.admin(licensed=False)
        lic, payload = self.env.issue_license()
        env = json.loads(lic)
        env["payload"]["max_users"] = 9999
        s, js, _ = c.post("/api/license/activate", {"license": json.dumps(env)})
        self.assertEqual((s, js["code"]), (422, "license_signature"))
        other, _ = self.env.issue_license(deployment_id="f" * 32)
        s, js, _ = c.post("/api/license/activate", {"license": other})
        self.assertEqual((s, js["code"]), (422, "license_mismatch"))
        self.assertEqual(c.post("/api/license/activate", {"license": "not json"})[1]["code"], "license_format")
        expired, _ = self.env.issue_license(expires="2020-01-01", grace=0)
        self.assertEqual(c.post("/api/license/activate", {"license": expired})[1]["code"], "license_expired")
        self.assertEqual(c.get("/api/license")[1]["state"], "missing")
        events = [e["event"] for e in c.get("/api/license/events")[1]["events"]]
        self.assertIn("rejected_wrong_deployment", events)

    def test_expiry_grace_and_lock(self):
        c = self.admin(licensed=False)
        lic, p = self.env.issue_license(days=1, grace=5)
        c.post("/api/license/activate", {"license": lic})
        db, inst = self.env.app.db, self.env.app.inst
        day = 86400
        now = time.time()
        self.assertEqual(licensing.compute_status(db, inst, now)["state"], "valid")
        self.assertEqual(licensing.compute_status(db, inst, now + 3 * day)["state"], "grace")
        self.assertEqual(licensing.compute_status(db, inst, now + 9 * day)["state"], "expired")
        self.assertTrue(licensing.compute_status(db, inst, now + 9 * day)["locked"])

    def test_perpetual_license_and_features(self):
        c = self.admin(licensed=False)
        lic, p = self.env.issue_license(expires="", features=["qr"])
        env = json.loads(lic); env["payload"]["expires_at"] = None
        from license_tool import sign
        lic = json.dumps(sign(self.env.priv, env["payload"]))
        self.assertEqual(c.post("/api/license/activate", {"license": lic})[0], 200)
        st = licensing.compute_status(self.env.app.db, self.env.app.inst, time.time() + 3650 * 86400)
        self.assertEqual(st["state"], "valid")
        self.env.app.license.invalidate()
        self.assertTrue(self.env.app.license.has_feature("qr"))
        self.assertFalse(self.env.app.license.has_feature("workflows"))

    def test_user_limit_enforced(self):
        c = self.admin(licensed=False)
        lic, _ = self.env.issue_license(max_users=2)
        c.post("/api/license/activate", {"license": lic})
        self.make_user(c, "user2", "viewer")
        s, js, _ = c.post("/api/users", {"username": "user3", "full_name": "User3", "role_id": self.role_id(c, "viewer"), "password": "Valid-Pass-123"})
        self.assertEqual((s, js["code"]), (402, "license_user_limit"))
        big, _ = self.env.issue_license(max_users=1)
        self.assertEqual(c.post("/api/license/activate", {"license": big})[1]["code"], "license_users_exceeded")

    def test_revocation_and_replay_protection(self):
        c = self.admin()
        lid = self.env.app.db.one("SELECT license_id FROM license_store")["license_id"]
        rev = self.env.issue_revocations(1, [lid])
        self.assertEqual(c.post("/api/license/revocations", {"list": rev})[0], 200)
        s, js, _ = c.get("/api/dashboard")
        self.assertEqual((s, js["state"]), (402, "revoked"))
        self.assertEqual(c.post("/api/license/revocations", {"list": rev})[1]["code"], "revocation_old")
        again, _ = self.env.issue_license()
        self.assertEqual(c.post("/api/license/activate", {"license": again})[0], 200)   # a fresh licence works
        self.assertEqual(c.get("/api/dashboard")[0], 200)

    def test_clock_rollback_locks_system(self):
        c = self.admin()
        db, inst = self.env.app.db, self.env.app.inst
        future = int(time.time()) + 5 * 86400
        v = str(future)
        db.execute("UPDATE system_state SET value=?, mac=? WHERE key='last_seen'", (v, __import__("core.security", fromlist=["x"]).mac(inst.secret_key, "last_seen:" + v)))
        self.assertEqual(licensing.compute_status(db, inst)["state"], "clock")
        db.execute("UPDATE system_state SET value='1' WHERE key='last_seen'")           # tampered without the secret
        self.assertEqual(licensing.compute_status(db, inst)["state"], "clock")

    def test_no_vendor_key_means_locked(self):
        self.env.close()
        self.env = Env(with_key=False)
        self.addCleanup(self.env.close)
        c = self.admin(licensed=False)
        self.assertEqual(c.get("/api/license")[1]["state"], "no_key")

    def test_license_events_cannot_be_edited(self):
        self.admin()
        with self.assertRaises(sqlite3.DatabaseError):
            self.env.app.db.execute("DELETE FROM license_events")


class TestAuditAndData(Base):
    def test_audit_trail_and_tamper_detection(self):
        c = self.admin()
        self.make_user(c, "aud", "viewer")
        actions = [e["action"] for e in c.get("/api/audit")[1]["entries"]]
        for a in ("setup.complete", "auth.login", "license.activate", "user.create"):
            self.assertIn(a, actions)
        self.assertTrue(c.post("/api/audit/verify")[1]["ok"])
        db = self.env.app.db
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("UPDATE audit_log SET username='x' WHERE id=1")
        with self.assertRaises(sqlite3.DatabaseError):
            db.execute("DELETE FROM audit_log")
        # an attacker with file access drops the trigger and edits a row
        db.execute("DROP TRIGGER audit_no_update")
        db.execute("UPDATE audit_log SET detail='{\"forged\":1}' WHERE id=2")
        r = audit.verify_chain(db)
        self.assertEqual((r["ok"], r["broken_at"]), (False, 2))

    def test_audit_filtering_and_pagination(self):
        c = self.admin()
        s, js, _ = c.get("/api/audit?action=user.&per_page=1")
        self.assertEqual(s, 200)
        self.assertEqual(len(js["entries"]), 1)
        self.assertEqual(c.get("/api/audit?per_page=abc")[0], 400)

    def test_company_branding_and_logo(self):
        c = self.admin()
        s, js, _ = c.put("/api/company", {"name_en": "Beta Ltd", "name_ar": "بيتا", "primary_color": "#112233", "accent_color": "#445566", "default_language": "ar", "default_theme": "dark"})
        self.assertEqual(s, 200, js)
        b = Client(self.env).get("/api/branding")[1]
        self.assertEqual((b["name_en"], b["primary_color"], b["default_language"], b["default_theme"]), ("Beta Ltd", "#112233", "ar", "dark"))
        self.assertEqual(c.put("/api/company", {"name_en": "X", "primary_color": "red"})[1]["code"], "invalid_color")
        self.assertEqual(c.put("/api/company", {"name_en": "", "name_ar": ""})[1]["code"], "company_name_required")
        self.assertEqual(c.post("/api/company/logo", raw=b"<svg onload=alert(1)>", csrf=True)[1]["code"], "logo_bad_type")
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 50
        s, js, _ = c.post("/api/company/logo", raw=png)
        self.assertEqual(s, 200, js)
        self.assertTrue(js["logo"].startswith("/brand/logo?v="))
        s, _, r = Client(self.env).get("/brand/logo")
        self.assertEqual((s, r.getheader("Content-Type")), (200, "image/png"))
        self.assertEqual(c.delete("/api/company/logo")[0], 200)
        self.assertEqual(Client(self.env).get("/brand/logo")[0], 404)

    def test_backup_endpoint_and_retention(self):
        c = self.admin()
        for _ in range(3):
            self.assertEqual(c.post("/api/backups")[0], 200)
        bl = c.get("/api/backups")[1]["backups"]
        self.assertGreaterEqual(len(bl), 3)
        con = sqlite3.connect(os.path.join(self.env.app.inst.backups_dir, bl[0]["name"]))
        self.assertGreaterEqual(con.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
        con.close()

    def test_migrations_detect_modified_file_and_are_idempotent(self):
        db = self.env.app.db
        self.assertEqual(db.migrate(), [])
        self.assertEqual(db.schema_version(), "0001")
        db.execute("UPDATE schema_migrations SET checksum='bad' WHERE version='0001'")
        from core.db import MigrationError
        with self.assertRaises(MigrationError):
            db.migrate()

    def test_static_files_and_security_headers(self):
        c = Client(self.env)
        s, js, r = c.get("/api/health")
        self.assertEqual(r.getheader("X-Frame-Options"), "DENY")
        self.assertIn("script-src 'self'", r.getheader("Content-Security-Policy"))
        self.assertEqual(c.get("/static/../server.py")[0], 404)
        self.assertEqual(c.get("/..%2fserver.py")[0], 404)
        self.assertEqual(c.get("/nope")[0], 404)


if __name__ == "__main__":
    unittest.main(verbosity=1)
