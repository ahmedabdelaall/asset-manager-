# -*- coding: utf-8 -*-
"""Sorting the asset list, and the public page a QR label opens when nobody is signed in."""
import unittest

from test_assets import InvBase
from helpers import Client


class TestAssetSort(InvBase):
    def test_sort_options(self):
        c = self.setup_inventory()
        self.new_asset(c, name="Charlie", purchase_cost=500, location="Cairo", purchase_date="2024-05-01")
        self.new_asset(c, name="alpha", purchase_cost=1500, purchase_date="2022-01-10")
        a3, t3 = self.new_asset(c, name="Bravo")
        c.post("/api/assets/%d/assign" % a3, {"employee_id": self.emp})
        names = lambda sort: [a["name"] for a in c.get("/api/assets?sort=" + sort)[1]["assets"]]
        self.assertEqual(names("newest"), ["Bravo", "alpha", "Charlie"])
        self.assertEqual(names("oldest"), ["Charlie", "alpha", "Bravo"])
        self.assertEqual(names("name"), ["alpha", "Bravo", "Charlie"])               # case does not matter
        self.assertEqual(names("cost_high"), ["alpha", "Charlie", "Bravo"])          # blanks last
        self.assertEqual(names("cost_low"), ["Charlie", "alpha", "Bravo"])
        self.assertEqual(names("purchase_new"), ["Charlie", "alpha", "Bravo"])
        self.assertEqual(names("holder")[0], "Bravo")
        self.assertEqual(names("location")[0], "Charlie")
        self.assertEqual(names("x;DROP%20TABLE%20assets"), names("newest"))           # unknown -> default, never SQL
        self.assertEqual(c.get("/api/export/assets?sort=name")[0], 200)


class TestPublicScan(InvBase):
    def test_public_page_shows_only_safe_fields(self):
        c = self.setup_inventory()
        aid, tag = self.new_asset(c, serial_no="SN-77", purchase_cost=999, notes="secret note", location="HQ 3rd floor",
                                  warranty_until="2030-01-01")
        c.put("/api/employees/%d" % self.emp, {"emp_no": "E-001", "full_name_en": "Sara Ali", "department_id": self.dept,
                                                "email": "sara@acme.test", "phone": "0100", "national_id": "29901011234567"})
        c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})
        a = Client(self.env)
        s, js, _ = a.get("/api/public/asset?tag=" + tag.lower())                     # tags are case-insensitive
        self.assertEqual(s, 200, js)
        self.assertEqual((js["tag"], js["serial_no"], js["holder_en"], js["dept_en"], js["location"], js["warranty_until"]),
                         (tag, "SN-77", "Sara Ali", "IT", "HQ 3rd floor", "2030-01-01"))
        body = str(js)
        for secret in ("999", "secret note", "0100", "29901011234567", "sara@acme.test", "ram_gb"):
            self.assertNotIn(secret, body)
        self.assertEqual(a.get("/api/public/asset?tag=NOPE-1")[1]["code"], "asset_not_found")
        # the signed-in look-up still needs a session
        self.assertEqual(a.get("/api/assets/by-tag?tag=" + tag)[0], 401)
        # switched off -> sign-in required
        c.put("/api/settings", {"alert_warranty_days": 30, "public_scan_enabled": False})
        self.assertEqual(a.get("/api/public/asset?tag=" + tag)[1]["code"], "public_scan_off")
        self.assertFalse(c.get("/api/settings")[1]["public_scan_enabled"])
        c.put("/api/settings", {"alert_warranty_days": 30})                          # other saves keep the switch as it is
        self.assertFalse(c.get("/api/settings")[1]["public_scan_enabled"])

    def test_rate_limited(self):
        c = self.setup_inventory()
        a = Client(self.env)
        codes = [a.get("/api/public/asset?tag=LAP-%04d" % i)[0] for i in range(65)]
        self.assertEqual(codes[0], 404)
        self.assertEqual(codes[-1], 429)


if __name__ == "__main__":
    unittest.main()
