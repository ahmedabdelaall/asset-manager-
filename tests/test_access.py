# -*- coding: utf-8 -*-
"""Request access (0.9.0): public form on the sign-in page, administrator approval, abuse limits."""
import unittest
from unittest import mock

from test_api import Base
from helpers import Client, SETUP, do_setup
from core import notify

REQ = {"full_name": "Sara Adel", "email": "Sara@Acme.test", "department": "Finance", "job_title": "Accountant",
       "phone": "+20 100 000 0000", "username": "sara", "reason": "Monthly asset value report", "lang": "ar"}


class TestAccessRequests(Base):
    def anon(self):
        return Client(self.env)

    def role_id(self, c, key):
        return next(r["id"] for r in c.get("/api/roles")[1]["roles"] if r["key"] == key)

    def test_submit_and_approve(self):
        c = self.admin()
        a = self.anon()
        self.assertTrue(a.get("/api/branding")[1]["access_requests"])
        s, js, _ = a.post("/api/access-requests", REQ)
        self.assertEqual((s, js["received"]), (201, True), js)
        # same e-mail again -> same answer, still one request; honeypot -> accepted silently, nothing stored
        self.assertEqual(a.post("/api/access-requests", dict(REQ, email="sara@acme.test"))[0], 201)
        self.assertEqual(a.post("/api/access-requests", dict(REQ, email="bot@spam.test", website="http://x"))[0], 201)
        self.assertEqual(a.post("/api/access-requests", dict(REQ, email="nope"))[1]["field"], "email")
        self.assertEqual(a.post("/api/access-requests", dict(REQ, email="x@y.test", full_name=""))[1]["code"], "field_required")
        self.assertEqual(a.post("/api/access-requests", dict(REQ, email="x@y.test", username="A B"))[1]["code"], "username_invalid")

        lst = c.get("/api/access-requests")[1]
        self.assertEqual(lst["pending"], 1)
        r = lst["requests"][0]
        self.assertEqual((r["email"], r["username"], r["username_taken"], r["status"]), ("sara@acme.test", "sara", False, "pending"))
        al = c.get("/api/alerts")[1]
        self.assertEqual(al["counts"].get("access"), 1)

        s, js, _ = c.post("/api/access-requests/%d/approve" % r["id"], {"role_id": self.role_id(c, "viewer")})
        self.assertEqual(s, 200, js)
        self.assertEqual(js["username"], "sara")
        self.assertTrue(js["temp_password"])
        self.assertFalse(js["emailed"])
        # the new account works, must change its password, has the chosen role and the requester's language
        u = self.anon()
        s, me, _ = u.login("sara", js["temp_password"])
        self.assertEqual(s, 200, me)
        self.assertEqual((me["user"]["must_change_password"], me["user"]["role_key"], me["user"]["lang"]), (True, "viewer", "ar"))
        done = c.get("/api/access-requests?status=all")[1]["requests"][0]
        self.assertEqual((done["status"], done["account"], done["decided_by_name"]), ("approved", "sara", "root"))
        self.assertEqual(c.post("/api/access-requests/%d/approve" % r["id"], {"role_id": self.role_id(c, "viewer")})[1]["code"], "access_request_decided")
        self.assertNotIn("access", c.get("/api/alerts")[1]["counts"])
        actions = [e["action"] for e in c.get("/api/audit?action=access")[1]["entries"]]
        self.assertEqual(sorted(actions), ["access.approve", "access.request"])

    def test_conflicts_roll_back(self):
        c = self.admin()
        self.anon().post("/api/access-requests", dict(REQ, username="root"))
        r = c.get("/api/access-requests")[1]["requests"][0]
        self.assertTrue(r["username_taken"])
        s, js, _ = c.post("/api/access-requests/%d/approve" % r["id"], {"role_id": self.role_id(c, "viewer")})
        self.assertEqual((s, js["code"]), (409, "username_taken"))
        self.assertEqual(c.get("/api/access-requests")[1]["requests"][0]["status"], "pending")      # nothing changed
        self.assertEqual(c.post("/api/access-requests/%d/approve" % r["id"], {"username": "sara.adel", "role_id": 999})[1]["code"], "role_not_found")
        self.assertEqual(len(c.get("/api/users")[1]["users"]), 1)

    def test_reject_and_permissions(self):
        c = self.admin()
        self.anon().post("/api/access-requests", REQ)
        rid = c.get("/api/access-requests")[1]["requests"][0]["id"]
        # a company administrator cannot hand out the Super Administrator role through an approval
        c.post("/api/users", {"username": "cadmin", "full_name": "Co Admin", "role_id": self.role_id(c, "company_admin"), "password": "Company-Admin-Pass-1"})
        c.post("/api/users", {"username": "view1", "full_name": "Viewer", "role_id": self.role_id(c, "viewer"), "password": "Viewer-Pass-Long-1"})
        ca = self.anon(); ca.login("cadmin", "Company-Admin-Pass-1"); ca.post("/api/auth/password", {"current": "Company-Admin-Pass-1", "new": "Company-Admin-Pass-2"})
        s, js, _ = ca.post("/api/access-requests/%d/approve" % rid, {"username": "sara", "role_id": self.role_id(c, "super_admin")})
        self.assertEqual((s, js["code"]), (403, "role_not_allowed"))
        v = self.anon(); v.login("view1", "Viewer-Pass-Long-1"); v.post("/api/auth/password", {"current": "Viewer-Pass-Long-1", "new": "Viewer-Pass-Long-2"})
        self.assertEqual(v.get("/api/access-requests")[0], 403)
        self.assertEqual(v.post("/api/access-requests/%d/reject" % rid, {})[0], 403)
        self.assertNotIn("access", v.get("/api/alerts")[1]["counts"])
        # anonymous visitors cannot read the queue
        self.assertEqual(self.anon().get("/api/access-requests")[0], 401)
        s, js, _ = c.post("/api/access-requests/%d/reject" % rid, {"note": "Please ask your manager first"})
        self.assertEqual((s, js["emailed"]), (200, False))
        r = c.get("/api/access-requests?status=rejected")[1]["requests"][0]
        self.assertEqual((r["status"], r["decision_note"]), ("rejected", "Please ask your manager first"))
        self.assertEqual(c.post("/api/access-requests/%d/reject" % rid, {})[1]["code"], "access_request_decided")
        # a new request from the same e-mail is possible once the old one is decided
        self.assertEqual(self.anon().post("/api/access-requests", REQ)[0], 201)
        self.assertEqual(c.get("/api/access-requests")[1]["pending"], 1)

    def test_switch_off_and_rate_limit(self):
        c = self.admin()
        a = self.anon()
        for i in range(5):
            self.assertEqual(a.post("/api/access-requests", dict(REQ, email="p%d@acme.test" % i))[0], 201)
        s, js, _ = a.post("/api/access-requests", dict(REQ, email="p9@acme.test"))
        self.assertEqual((s, js["code"]), (429, "too_many_attempts"))
        s, js, _ = c.put("/api/settings", dict(notify.get_settings(self.env.app.db, self.env.app.inst), access_requests_enabled=False))
        self.assertEqual(s, 200, js)
        self.assertFalse(a.get("/api/branding")[1]["access_requests"])
        self.env.app.access_limiter.clear("127.0.0.1")
        self.assertEqual(a.post("/api/access-requests", dict(REQ, email="z@acme.test"))[1]["code"], "access_requests_off")
        # saving other settings without the field keeps the switch as it is
        c.put("/api/settings", {"alert_warranty_days": 30})
        self.assertFalse(c.get("/api/settings")[1]["access_requests_enabled"])

    def test_allowed_domains_from_setup(self):
        # a bad domain stops setup and nothing is created
        s, js, _ = do_setup(self.env, access_allowed_domains="acme.test, not a domain")
        self.assertEqual((s, js["code"], js["field"]), (422, "invalid_domain", "access_allowed_domains"))
        self.assertTrue(self.env.app.needs_setup())
        s, js, _ = do_setup(self.env, access_allowed_domains=" @ACME.test,acme.com.eg ; acme.test ")
        self.assertEqual(s, 200, js)
        a = self.anon()
        self.assertEqual(a.get("/api/branding")[1]["access_domains"], ["acme.test", "acme.com.eg"])
        s, js, _ = a.post("/api/access-requests", dict(REQ, email="sara@gmail.com"))
        self.assertEqual((s, js["code"], js["field"], js["domains"]), (422, "email_domain_not_allowed", "email", "@acme.test, @acme.com.eg"))
        # exact match only: a sub-domain or a look-alike is refused, case does not matter
        for bad in ("sara@mail.acme.test", "sara@acme.test.evil.com", "sara@xacme.test"):
            self.assertEqual(a.post("/api/access-requests", dict(REQ, email=bad))[1]["code"], "email_domain_not_allowed", bad)
        self.assertEqual(a.post("/api/access-requests", REQ)[0], 201)                  # Sara@Acme.test
        self.assertEqual(a.post("/api/access-requests", dict(REQ, email="omar@acme.com.eg"))[0], 201)
        # refused domains do not use up the hourly limit: 5 good ones above/below still pass
        for i in range(3):
            self.assertEqual(a.post("/api/access-requests", dict(REQ, email="p%d@acme.test" % i))[0], 201)

    def test_allowed_domains_settings(self):
        c = self.admin()                                                               # no domains -> any e-mail
        self.assertEqual(c.get("/api/settings")[1]["access_allowed_domains"], [])
        self.assertEqual(self.anon().post("/api/access-requests", dict(REQ, email="x@gmail.com"))[0], 201)
        s, js, _ = c.put("/api/settings", {"alert_warranty_days": 30, "access_allowed_domains": "acme.test"})
        self.assertEqual(s, 200, js)
        self.assertEqual(self.anon().post("/api/access-requests", dict(REQ, email="y@gmail.com"))[1]["code"], "email_domain_not_allowed")
        c.put("/api/settings", {"alert_warranty_days": 30})                            # field absent -> kept
        self.assertEqual(c.get("/api/settings")[1]["access_allowed_domains"], ["acme.test"])
        self.assertEqual(c.put("/api/settings", {"access_allowed_domains": "acme..test"})[1]["code"], "invalid_domain")
        self.assertEqual(c.put("/api/settings", {"access_allowed_domains": ",".join("d%d.test" % i for i in range(21))})[1]["code"], "too_many_domains")
        self.assertEqual(c.put("/api/settings", {"access_allowed_domains": {"x": 1}})[0], 400)
        c.put("/api/settings", {"alert_warranty_days": 30, "access_allowed_domains": ""})   # emptied -> any e-mail again
        self.assertEqual(self.anon().post("/api/access-requests", dict(REQ, email="z@gmail.com"))[0], 201)
        # the change is audited
        e = c.get("/api/audit?action=settings")[1]["entries"][0]
        self.assertIn("access_allowed_domains", str(e))

    def test_not_before_setup(self):
        a = self.anon()
        self.assertFalse(a.get("/api/branding")[1]["access_requests"])
        self.assertEqual(a.post("/api/access-requests", REQ)[1]["code"], "setup_required")

    def test_emails(self):
        c = self.admin()
        c.put("/api/settings", {"email_enabled": True, "smtp_host": "mail.acme.test", "smtp_from": "assets@acme.test",
                                "public_url": "https://assets.acme.test", "alert_warranty_days": 30})
        self.anon().post("/api/access-requests", REQ)
        self.anon().post("/api/access-requests", dict(REQ, email="omar@acme.test", full_name="Omar", lang="en"))
        reqs = {r["full_name"]: r["id"] for r in c.get("/api/access-requests")[1]["requests"]}
        with mock.patch.object(notify, "_smtp_send") as send:
            js = c.post("/api/access-requests/%d/approve" % reqs["Sara Adel"], {"role_id": self.role_id(c, "viewer"), "notify": True})[1]
            self.assertTrue(js["emailed"], js)
            to, subject, body, _ = send.call_args[0][1:]
            self.assertIn("sara@acme.test", to)
            self.assertIn("sara", body)
            self.assertIn(js["temp_password"], body)
            self.assertIn("https://assets.acme.test", body)
            self.assertIn("اسم المستخدم", body)                                  # requester asked in Arabic
            js = c.post("/api/access-requests/%d/reject" % reqs["Omar"], {"note": "Not needed", "notify": True})[1]
            self.assertTrue(js["emailed"])
            self.assertIn("Not needed", send.call_args[0][3])
        with mock.patch.object(notify, "_smtp_send", side_effect=OSError("down")):
            self.anon().post("/api/access-requests", dict(REQ, email="lina@acme.test", username="lina"))
            rid = c.get("/api/access-requests")[1]["requests"][0]["id"]
            js = c.post("/api/access-requests/%d/approve" % rid, {"role_id": self.role_id(c, "viewer"), "notify": True})[1]
            self.assertEqual((js["emailed"], js["username"]), (False, "lina"))     # account still created; password shown instead


if __name__ == "__main__":
    unittest.main()
