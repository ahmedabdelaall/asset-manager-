# -*- coding: utf-8 -*-
"""Phase 6: maintenance, asset requests (approval workflow), alerts, settings & e-mail digest, labels."""
import json
import datetime
import unittest
from unittest import mock

from test_assets import InvBase
from core import notify

TODAY = datetime.date.today()
D = lambda days: (TODAY + datetime.timedelta(days=days)).isoformat()


class TestMaintenance(InvBase):
    def test_out_of_service_and_back(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        s, js, _ = c.post("/api/maintenance", {"asset_id": aid, "kind": "repair", "title": "Broken screen", "out_of_service": True, "vendor": "FixIt"})
        self.assertEqual(s, 201, js)
        m1 = js["id"]
        self.assertEqual(c.get("/api/assets/%d" % aid)[1]["status"], "maintenance")
        self.assertEqual(c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[1]["code"], "asset_not_available")
        m2 = c.post("/api/maintenance", {"asset_id": aid, "kind": "upgrade", "title": "RAM", "out_of_service": True})[1]["id"]
        c.post("/api/maintenance/%d/complete" % m1, {"cost": 350, "resolution": "Replaced panel"})
        self.assertEqual(c.get("/api/assets/%d" % aid)[1]["status"], "maintenance")      # m2 is still being worked on
        rec = {m["id"]: m for m in c.get("/api/maintenance?asset=%d" % aid)[1]["maintenance"]}
        self.assertEqual((rec[m1]["status"], rec[m1]["cost"], rec[m2]["took_out_of_service"]), ("done", 350, 1))   # m2 inherited it
        c.post("/api/maintenance/%d/cancel" % m2, {})
        self.assertEqual(c.get("/api/assets/%d" % aid)[1]["status"], "in_stock")         # last open record closed
        self.assertEqual(c.post("/api/maintenance/%d/complete" % m1, {})[1]["code"], "maintenance_wrong_state")
        actions = [h["action"] for h in c.get("/api/assets/%d" % aid)[1]["history"]]
        for a in ("maintenance.create", "maintenance.complete", "maintenance.cancel"):
            self.assertIn(a, actions)

    def test_single_record_returns_asset_to_stock(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        mid = c.post("/api/maintenance", {"asset_id": aid, "title": "Service", "kind": "service", "out_of_service": True})[1]["id"]
        c.post("/api/maintenance/%d/complete" % mid, {"condition": "good"})
        self.assertEqual(c.get("/api/assets/%d" % aid)[1]["status"], "in_stock")

    def test_scheduled_assigned_and_disposed(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        mid = c.post("/api/maintenance", {"asset_id": aid, "title": "Yearly check", "kind": "inspection", "scheduled_for": D(10)})[1]["id"]
        m = c.get("/api/maintenance?status=scheduled")[1]["maintenance"][0]
        self.assertEqual((m["id"], m["status"], m["started_at"]), (mid, "scheduled", None))
        c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})
        self.assertEqual(c.post("/api/maintenance/%d/start" % mid, {"out_of_service": True})[0], 200)
        self.assertEqual(c.get("/api/assets/%d" % aid)[1]["status"], "assigned")          # an assigned asset is never taken out
        self.assertEqual(c.post("/api/maintenance/%d/start" % mid, {})[1]["code"], "maintenance_wrong_state")
        b, _ = self.new_asset(c)
        c.post("/api/assets/%d/status" % b, {"status": "retired"})
        self.assertEqual(c.post("/api/maintenance", {"asset_id": b, "title": "x"})[1]["code"], "asset_disposed")
        self.assertEqual(c.post("/api/maintenance", {"asset_id": aid, "title": ""})[1]["code"], "field_required")

    def test_report_and_permissions(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        mid = c.post("/api/maintenance", {"asset_id": aid, "title": "Battery", "cost": 120})[1]["id"]
        c.post("/api/maintenance/%d/complete" % mid, {"cost": 150})
        r = c.get("/api/reports/maintenance")[1]
        self.assertEqual((len(r["rows"]), r["totals"]["cost"]), (1, 150))
        self.make_user(c, "view1", "viewer")
        v = self.login_as("view1")
        self.assertEqual(v.get("/api/maintenance")[0], 200)
        self.assertEqual(v.post("/api/maintenance", {"asset_id": aid, "title": "x"})[0], 403)
        self.make_user(c, "hr1", "hr")
        self.assertEqual(self.login_as("hr1").get("/api/reports/maintenance")[0], 403)


class TestRequests(InvBase):
    def test_request_approve_reject_cancel(self):
        c = self.setup_inventory()
        a1, _ = self.new_asset(c)
        other = c.post("/api/categories", {"code": "PHN", "name_en": "Phones"})[1]["id"]
        p1 = c.post("/api/assets", {"category_id": other, "name": "iPhone"})[1]["id"]
        self.make_user(c, "hr1", "hr")
        h = self.login_as("hr1")
        s, js, _ = h.post("/api/requests", {"employee_id": self.emp, "category_id": self.cat, "reason": "New joiner", "needed_by": D(3)})
        self.assertEqual(s, 201, js)
        rid = js["id"]
        self.assertEqual(h.post("/api/requests/%d/approve" % rid, {"asset_id": a1})[0], 403)          # HR can request, not approve
        reqs = c.get("/api/requests?status=pending")[1]["requests"]
        self.assertEqual((reqs[0]["id"], reqs[0]["available"]), (rid, 1))
        self.assertEqual([x["id"] for x in c.get("/api/requests/%d/candidates" % rid)[1]["assets"]], [a1])
        self.assertEqual(c.post("/api/requests/%d/approve" % rid, {"asset_id": p1})[1]["code"], "asset_wrong_category")
        s, js, _ = c.post("/api/requests/%d/approve" % rid, {"asset_id": a1, "note": "Enjoy"})
        self.assertEqual(s, 200, js)
        a = c.get("/api/assets/%d" % a1)[1]
        self.assertEqual((a["status"], a["holder_id"]), ("assigned", self.emp))
        r = h.get("/api/requests")[1]["requests"][0]
        self.assertEqual((r["status"], r["asset_tag"], r["decision_note"]), ("fulfilled", a["tag"], "Enjoy"))
        self.assertEqual(c.post("/api/requests/%d/approve" % rid, {"asset_id": a1})[1]["code"], "request_closed")
        # the requester sees the decision in their alerts
        self.assertIn("decided", h.get("/api/alerts")[1]["counts"])
        # reject needs a reason; cancel is for the requester or an approver
        r2 = h.post("/api/requests", {"employee_id": self.emp, "reason": "Spare"})[1]["id"]
        self.assertEqual(c.post("/api/requests/%d/reject" % r2, {})[1]["code"], "field_required")
        self.assertEqual(c.post("/api/requests/%d/reject" % r2, {"note": "No budget"})[0], 200)
        r3 = c.post("/api/requests", {"employee_id": self.emp, "reason": "Mine"})[1]["id"]
        self.assertEqual(h.post("/api/requests/%d/cancel" % r3, {})[0], 403)
        self.assertEqual(c.post("/api/requests/%d/cancel" % r3, {})[0], 200)
        self.assertEqual(len(h.get("/api/requests")[1]["requests"]), 2)                            # requesters only see their own
        self.make_user(c, "view1", "viewer")
        self.assertEqual(self.login_as("view1").get("/api/requests")[0], 403)
        self.assertEqual(h.post("/api/requests", {"employee_id": self.emp, "reason": ""})[1]["code"], "field_required")


class TestAlertsSettingsEmail(InvBase):
    def test_alerts_follow_permissions(self):
        c = self.setup_inventory()
        a1, _ = self.new_asset(c, warranty_until=D(5))
        g = c.post("/api/assets/%d/assign" % a1, {"employee_id": self.emp, "expected_return": D(1)})[1]["id"]
        self.env.app.db.execute("UPDATE assignments SET expected_return=? WHERE id=?", (D(-2), g))
        a2, _ = self.new_asset(c)
        c.post("/api/maintenance", {"asset_id": a2, "title": "Check", "scheduled_for": D(3)})
        c.post("/api/requests", {"employee_id": self.emp, "reason": "x"})
        al = c.get("/api/alerts")[1]
        self.assertEqual(al["counts"], {"overdue": 1, "warranty": 1, "maintenance": 1, "request": 1})
        self.assertEqual(al["items"][0]["kind"], "overdue")                       # critical first
        self.make_user(c, "view1", "viewer")
        self.assertEqual(self.login_as("view1").get("/api/alerts")[1]["counts"], {"overdue": 1, "warranty": 1, "maintenance": 1})

    def test_settings_secret_is_encrypted_and_never_returned(self):
        c = self.setup_inventory()
        base = {"alert_warranty_days": 45, "public_url": "https://assets.acme.test/", "smtp_host": "mail.acme.test", "smtp_port": 587,
                "smtp_security": "starttls", "smtp_user": "bot", "smtp_from": "assets@acme.test", "digest_hour": 8}
        s, js, _ = c.put("/api/settings", dict(base, smtp_password="P@ss-123", email_enabled=True))
        self.assertEqual(s, 200, js)
        g = c.get("/api/settings")[1]
        self.assertEqual((g["smtp_password"], g["smtp_password_set"], g["public_url"], g["alert_warranty_days"]),
                         ("", True, "https://assets.acme.test", 45))
        raw = self.env.app.db.one("SELECT value FROM settings WHERE key='smtp_password'")["value"]
        self.assertTrue(json.loads(raw).startswith("enc:"))
        self.assertNotIn("P@ss-123", raw)
        c.put("/api/settings", dict(base, email_enabled=True))                     # blank password keeps the stored one
        self.assertEqual(notify.get_settings(self.env.app.db, self.env.app.inst, reveal=True)["smtp_password"], "P@ss-123")
        self.assertEqual(c.put("/api/settings", dict(base, public_url="ftp://x"))[1]["code"], "invalid_url")
        self.assertEqual(c.put("/api/settings", dict(base, smtp_host="", email_enabled=True))[1]["code"], "smtp_incomplete")
        self.make_user(c, "view1", "viewer")
        self.assertEqual(self.login_as("view1").put("/api/settings", base)[0], 403)

    def test_digest_and_test_email(self):
        c = self.setup_inventory()
        a1, _ = self.new_asset(c, warranty_until=D(2))
        c.put("/api/settings", {"email_enabled": True, "smtp_host": "mail.acme.test", "smtp_from": "assets@acme.test", "smtp_port": 25, "smtp_security": "none"})
        sent = []
        with mock.patch.object(notify, "_smtp_send", side_effect=lambda s, to, subj, txt, html: sent.append((to, subj, txt))):
            self.assertEqual(c.post("/api/settings/send-digest")[1]["sent"], 1)
            self.assertIn("root@acme.test", sent[0][0])
            self.assertIn("LAP-00001", sent[0][2])
            self.assertEqual(notify.run_digest(self.env.app.db, self.env.app.inst), 0)       # already sent today
            c.put("/api/auth/prefs", {"lang": "ar", "theme": "light", "email_alerts": False})
            self.assertEqual(c.post("/api/settings/send-digest")[1]["sent"], 0)              # opted out
            self.assertTrue(c.post("/api/settings/test-email", {"to": "x@acme.test"})[1]["ok"])
        with mock.patch.object(notify, "_smtp_send", side_effect=OSError("connection refused")):
            self.assertEqual(c.post("/api/settings/test-email", {"to": "x@acme.test"})[1]["code"], "smtp_failed")
        # each common failure gets its own, explainable reason; the server's own words are passed on
        import smtplib, socket, ssl
        cases = [(smtplib.SMTPAuthenticationError(535, b"Incorrect authentication data"), "smtp_auth"),
                 (smtplib.SMTPSenderRefused(553, b"Sender not owned by user", "x@gmail.com"), "smtp_sender"),
                 (smtplib.SMTPDataError(550, b"Sorry! This server is unable to send email from this domain:\ngmail.com."), "smtp_sender"),
                 (smtplib.SMTPRecipientsRefused({"x@acme.test": (550, b"no")}), "smtp_recipient"),
                 (socket.gaierror(-2, "Name or service not known"), "smtp_host_unknown"),
                 (TimeoutError("timed out"), "smtp_timeout"),
                 (ssl.SSLError(1, "[SSL: WRONG_VERSION_NUMBER] wrong version number"), "smtp_tls"),
                 (ConnectionRefusedError(111, "Connection refused"), "smtp_connect"),
                 (smtplib.SMTPConnectError(421, b"please try again later"), "smtp_connect")]
        for exc, code in cases:
            with mock.patch.object(notify, "_smtp_send", side_effect=exc):
                s, js, _ = c.post("/api/settings/test-email", {"to": "x@acme.test"})
                self.assertEqual((s, js["code"]), (502, code), exc)
                self.assertTrue(js["detail"])
        with mock.patch.object(notify, "_smtp_send", side_effect=cases[1][0]):
            self.assertIn("Sender not owned", c.post("/api/settings/test-email", {"to": "x@acme.test"})[1]["detail"])
        self.assertFalse(c.get("/api/auth/me")[1]["user"]["email_alerts"])

    def test_send_summary_now_explains_why_nothing_was_sent(self):
        c = self.setup_inventory()
        r = c.post("/api/settings/send-digest")[1]
        self.assertEqual((r["status"], r["sent"]), ("email_off", 0))                     # alerts switched off
        c.put("/api/settings", {"email_enabled": True, "smtp_host": "mail.acme.test", "smtp_from": "assets@acme.test", "smtp_port": 25, "smtp_security": "none"})
        with mock.patch.object(notify, "_smtp_send") as send:
            r = c.post("/api/settings/send-digest")[1]
            self.assertEqual((r["status"], r["sent"], r["checked"], r["nothing"]), ("ok", 0, 1, 1))   # nothing to report
            send.assert_not_called()
            self.new_asset(c, warranty_until=D(2))
            r = c.post("/api/settings/send-digest")[1]
            self.assertEqual((r["sent"], r["nothing"]), (1, 0))
            c.put("/api/auth/prefs", {"lang": "en", "theme": "light", "email_alerts": False})
            r = c.post("/api/settings/send-digest")[1]
            self.assertEqual((r["checked"], r["opted_out"]), (0, 1))                         # nobody can receive it
        c.put("/api/auth/prefs", {"lang": "en", "theme": "light", "email_alerts": True})
        import smtplib
        with mock.patch.object(notify, "_smtp_send", side_effect=smtplib.SMTPAuthenticationError(535, b"bad")):
            r = c.post("/api/settings/send-digest")[1]
            self.assertEqual((r["failed"], r["error"]), (1, "smtp_auth"))


class TestLabels(InvBase):
    def test_lookup_and_labels(self):
        c = self.setup_inventory()
        aid, tag = self.new_asset(c, serial_no="SN9")
        self.assertEqual(c.get("/api/assets/by-tag?tag=" + tag.lower())[1]["id"], aid)
        self.assertEqual(c.get("/api/assets/by-tag?tag=NOPE")[0], 404)
        r = c.get("/api/labels?ids=%d,999" % aid)[1]
        self.assertEqual([(a["tag"], a["serial_no"]) for a in r["assets"]], [(tag, "SN9")])
        self.assertEqual(c.get("/api/labels?ids=")[0], 400)


if __name__ == "__main__":
    unittest.main(verbosity=1)
