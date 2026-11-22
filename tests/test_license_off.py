# -*- coding: utf-8 -*-
"""Licensing switched off (config "license_enabled": false / AM_LICENSE=off): no lock, no user limit, no activation."""
import os
import unittest
from unittest import mock

from test_api import Base
from helpers import Env, Client, SETUP
from core.config import Instance


class TestLicenseOff(Base):
    def setUp(self):
        self.env = Env(config={"license_enabled": False})
        self.addCleanup(self.env.close)

    def test_everything_works_without_a_licence(self):
        c = self.admin(licensed=False)                          # never activated
        me = c.get("/api/auth/me")[1]["license"]
        self.assertEqual((me["state"], me["locked"], me["disabled"]), ("disabled", False, True))
        # pages that need a licence work
        self.assertEqual(c.get("/api/users")[0], 200)
        self.assertEqual(c.get("/api/employees")[0], 200)
        d = c.get("/api/dashboard")[1]["license"]
        self.assertTrue(d["disabled"])
        # no user limit (a licence would allow 10 in the tests; create more than that)
        viewer = self.role_id(c, "viewer")
        for i in range(12):
            s, js, _ = c.post("/api/users", {"username": "u%02d" % i, "full_name": "User %d" % i, "role_id": viewer,
                                             "password": "Long-Password-%02d" % i})
            self.assertEqual(s, 201, js)
        # ordinary users can sign in (a locked licence only lets the super admin in)
        self.assertEqual(Client(self.env).login("u00", "Long-Password-00")[0], 200)
        # activation is refused with a clear reason instead of silently storing a licence
        lic, _ = self.env.issue_license()
        s, js, _ = c.post("/api/license/activate", {"license": lic})
        self.assertEqual((s, js["code"]), (409, "license_disabled"))
        self.assertEqual(c.post("/api/license/revocations", {"list": "x"})[1]["code"], "license_disabled")
        # the health check does not report a failure
        h = {x["key"]: x for x in c.get("/api/system/health")[1]["checks"]}
        self.assertEqual((h["license"]["state"], h["license"]["value"]), ("ok", "disabled"))

    def test_env_switch(self):
        inst_dir = os.path.join(self.env.dir, "inst2")
        for val, expected in (("off", False), ("false", False), ("0", False), ("on", True), ("true", True)):
            with mock.patch.dict(os.environ, {"AM_LICENSE": val}):
                self.assertIs(Instance(inst_dir).config["license_enabled"], expected, val)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AM_LICENSE", None)
            self.assertIs(Instance(inst_dir).config["license_enabled"], True)       # default: licensing on


class TestLicenseStillOnByDefault(Base):
    def test_default_is_locked(self):
        c = self.admin(licensed=False)
        self.assertEqual(c.get("/api/users")[1]["code"], "license_required")
        self.assertFalse(c.get("/api/auth/me")[1]["license"]["disabled"])


if __name__ == "__main__":
    unittest.main()
