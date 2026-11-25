# -*- coding: utf-8 -*-
"""Invite a user by e-mail (0.9.0) and the administrator alert for new access requests."""
import time
import unittest
from unittest import mock

from test_api import Base
from helpers import Client
from core import notify

MAIL = {"email_enabled": True, "smtp_host": "mail.acme.test", "smtp_from": "assets@acme.test", "smtp_port": 25,
        "smtp_security": "none", "public_url": "https://assets.acme.test"}


def token_of(link):
    return link.split("#/invite?t=")[1]


class TestInvites(Base):
    def anon(self):
        return Client(self.env)

    def invite(self, c, **over):
        d = {"email": "Mona@Acme.test", "full_name": "Mona Samir", "lang": "ar", "days": 7, "origin": "http://127.0.0.1:8080"}
        d.update(over)
        if "role_id" not in d:
            d["role_id"] = self.role_id(c, "viewer")
        return c.post("/api/invites", d)

    def test_invite_without_email_gives_link_and_accept_signs_in(self):
        c = self.admin()
        s, js, _ = self.invite(c)
        self.assertEqual(s, 201, js)
        self.assertEqual((js["emailed"], js["mail_error"]), (False, "email_off"))
        self.assertTrue(js["link"].startswith("http://127.0.0.1:8080/#/invite?t="))
        tok = token_of(js["link"])
        # only the hash is stored
        self.assertIsNone(self.env.app.db.one("SELECT 1 FROM invitations WHERE token_hash=?", (tok,)))
        lst = c.get("/api/invites")[1]["invites"]
        self.assertEqual((len(lst), lst[0]["status"], lst[0]["email"], lst[0]["invited_by"]), (1, "pending", "mona@acme.test", "root"))

        a = self.anon()
        s, info, _ = a.post("/api/invite/check", {"token": tok})
        self.assertEqual(s, 200, info)
        self.assertEqual((info["email"], info["suggested"], info["role_name_en"]), ("mona@acme.test", "mona", "Viewer"))
        self.assertEqual(a.post("/api/invite/accept", {"token": tok, "username": "mona", "password": "short"})[1]["field"], "password")
        s, res, _ = a.post("/api/invite/accept", {"token": tok, "username": "mona", "password": "Mona-Strong-Pass-1"})
        self.assertEqual((s, res["username"]), (200, "mona"), res)
        s, me, _ = a.login("mona", "Mona-Strong-Pass-1")
        self.assertEqual(s, 200, me)
        self.assertEqual((me["user"]["role_key"], me["user"]["must_change_password"], me["user"]["lang"], me["user"]["email"]),
                         ("viewer", False, "ar", "mona@acme.test"))
        # the link works once
        self.assertEqual(self.anon().post("/api/invite/check", {"token": tok})[1]["code"], "invite_used")
        self.assertEqual(c.get("/api/invites")[1]["invites"], [])
        hist = c.get("/api/invites?view=all")[1]["invites"][0]
        self.assertEqual((hist["status"], hist["account"]), ("accepted", "mona"))
        actions = sorted(e["action"] for e in c.get("/api/audit?action=invite")[1]["entries"])
        self.assertEqual(actions, ["invite.accept", "invite.create"])
        # the same e-mail cannot be invited again
        self.assertEqual(self.invite(c)[1]["code"], "invite_email_has_account")

    def test_email_sent_with_fixed_username(self):
        c = self.admin()
        c.put("/api/settings", MAIL)
        sent = []
        with mock.patch.object(notify, "_smtp_send", side_effect=lambda s, to, subj, txt, html: sent.append((to, subj, txt))):
            s, js, _ = self.invite(c, username="m.samir", lang="en", role_id=self.role_id(c, "company_admin"))
        self.assertEqual((s, js["emailed"]), (201, True), js)
        self.assertTrue(js["link"].startswith("https://assets.acme.test/#/invite?t="))   # the public address wins
        to, subj, txt = sent[0]
        self.assertIn("mona@acme.test", to)
        self.assertIn(js["link"], txt)
        self.assertIn("m.samir", txt)
        self.assertIn("Acme Corp", subj)
        tok = token_of(js["link"])
        # the username chosen by the administrator cannot be changed by the person
        s, res, _ = self.anon().post("/api/invite/accept", {"token": tok, "username": "hacker", "password": "Mona-Strong-Pass-1"})
        self.assertEqual(res["username"], "m.samir", res)
        u = [x for x in c.get("/api/users")[1]["users"] if x["username"] == "m.samir"][0]
        self.assertEqual(u["role_key"], "company_admin")

    def test_mail_failure_keeps_invitation(self):
        c = self.admin()
        c.put("/api/settings", MAIL)
        import smtplib
        with mock.patch.object(notify, "_smtp_send", side_effect=smtplib.SMTPAuthenticationError(535, b"bad")):
            s, js, _ = self.invite(c)
        self.assertEqual((s, js["emailed"], js["mail_error"]), (201, False, "smtp_auth"))
        self.assertEqual(self.anon().post("/api/invite/check", {"token": token_of(js["link"])})[0], 200)

    def test_resend_revoke_expiry_and_bad_links(self):
        c = self.admin()
        first = token_of(self.invite(c)[1]["link"])
        iid = c.get("/api/invites")[1]["invites"][0]["id"]
        second = token_of(c.post("/api/invites/%d/resend" % iid, {"origin": "http://127.0.0.1:8080"})[1]["link"])
        a = self.anon()
        self.assertEqual(a.post("/api/invite/check", {"token": first})[1]["code"], "invite_invalid")    # replaced
        self.assertEqual(a.post("/api/invite/check", {"token": second})[0], 200)
        # inviting the same e-mail again replaces the waiting invitation
        third = token_of(self.invite(c, full_name="Mona S.")[1]["link"])
        self.assertEqual(a.post("/api/invite/check", {"token": second})[1]["code"], "invite_invalid")
        self.assertEqual(len(c.get("/api/invites")[1]["invites"]), 1)
        iid = c.get("/api/invites")[1]["invites"][0]["id"]
        self.env.app.db.execute("UPDATE invitations SET expires_at=? WHERE id=?", (int(time.time()) - 5, iid))
        self.assertEqual(a.post("/api/invite/check", {"token": third})[1]["code"], "invite_expired")
        self.assertEqual(c.get("/api/invites")[1]["invites"][0]["status"], "expired")
        self.assertEqual(c.post("/api/invites/%d/revoke" % iid)[0], 200)
        self.assertEqual(a.post("/api/invite/check", {"token": third})[1]["code"], "invite_invalid")
        self.assertEqual(c.post("/api/invites/%d/revoke" % iid)[1]["code"], "invite_closed")
        self.assertEqual(a.post("/api/invite/check", {"token": "x" * 43})[1]["code"], "invite_invalid")
        self.assertEqual(a.post("/api/invite/check", {})[1]["code"], "invite_invalid")
        # wrong links are rate limited per IP
        for _ in range(25):
            st = a.post("/api/invite/check", {"token": "y" * 43})[0]
        self.assertEqual(st, 429)

    def test_permissions_and_role_limits(self):
        c = self.admin()
        self.make_user(c, "cadmin", "company_admin")
        self.make_user(c, "view1", "viewer")
        ca = self.login_as("cadmin")
        self.assertEqual(self.invite(ca, role_id=self.role_id(c, "super_admin"))[1]["code"], "role_not_allowed")
        s, js, _ = self.invite(ca, email="ali@acme.test")
        self.assertEqual(s, 201, js)
        v = self.login_as("view1")
        self.assertEqual(self.invite(v, email="x@acme.test", role_id=self.role_id(c, "viewer"))[0], 403)
        self.assertEqual(v.get("/api/invites")[0], 403)
        # an invitation from an account that was disabled afterwards no longer works
        cid = [u for u in c.get("/api/users")[1]["users"] if u["username"] == "cadmin"][0]["id"]
        c.post("/api/users/%d/active" % cid, {"active": False})
        self.assertEqual(self.anon().post("/api/invite/check", {"token": token_of(js["link"])})[1]["code"], "invite_invalid")
        self.assertEqual(self.invite(c, email="bad")[1]["field"], "email")
        self.assertEqual(self.invite(c, email="a@acme.test", days=99)[1]["field"], "days")
        self.assertEqual(self.invite(c, email="a@acme.test", username="root")[1]["code"], "username_taken")


class TestAccessAlert(Base):
    def test_admins_emailed_on_new_request(self):
        c = self.admin()
        c.put("/api/settings", MAIL)
        sent = []
        with mock.patch.object(notify, "_smtp_send", side_effect=lambda s, to, subj, txt, html: sent.append((to, subj, txt))):
            s, js, _ = Client(self.env).post("/api/access-requests", {"full_name": "Sara Adel", "email": "sara@acme.test",
                                                                       "department": "Finance", "reason": "Reports"})
            self.assertEqual(s, 201, js)
            for _ in range(50):
                if sent:
                    break
                time.sleep(0.05)
        self.assertEqual(len(sent), 1)
        to, subj, txt = sent[0]
        self.assertIn("root@acme.test", to)
        self.assertIn("Sara Adel", subj)
        self.assertIn("Finance", txt)
        self.assertIn("https://assets.acme.test/#/users", txt)


if __name__ == "__main__":
    unittest.main()
