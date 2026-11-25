# -*- coding: utf-8 -*-
"""Receipt layout and switching asset requests off (0.9.0)."""
import unittest

from test_assets import InvBase


class TestReceiptLayout(InvBase):
    def test_layout_saved_and_sent_with_receipt(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        g = c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[1]["id"]
        self.assertEqual(c.get("/api/assignments/%d/receipt" % g)[1]["layout"], {})
        s, js, _ = c.put("/api/settings/receipt", {"title_handover_ar": "إقرار استلام عهدة", "footer_en": "Call IT on 123\nThanks",
                                                   "hide": ["department", "sig_national_id"]})
        self.assertEqual(s, 200, js)
        lay = c.get("/api/assignments/%d/receipt" % g)[1]["layout"]
        self.assertEqual((lay["title_handover_ar"], lay["footer_en"], lay["hide"]), ("إقرار استلام عهدة", "Call IT on 123\nThanks", ["department", "sig_national_id"]))
        self.assertEqual(c.put("/api/settings/receipt", {"hide": ["password"]})[1]["code"], "invalid_field")
        # saving the receipt layout does not touch other settings, and the other settings do not touch the layout
        c.put("/api/settings", {"alert_warranty_days": 45})
        self.assertEqual(c.get("/api/settings")[1]["receipt"]["title_handover_ar"], "إقرار استلام عهدة")
        c.put("/api/settings/receipt", {"hide": []})
        self.assertEqual(c.get("/api/settings")[1]["alert_warranty_days"], 45)
        self.make_user(c, "view1", "viewer")
        self.assertEqual(self.login_as("view1").put("/api/settings/receipt", {"hide": []})[0], 403)


class TestAssetRequestsSwitch(InvBase):
    def test_switch_off_hides_and_refuses(self):
        c = self.setup_inventory()
        self.assertTrue(c.get("/api/branding")[1]["asset_requests"])
        self.assertEqual(c.post("/api/requests", {"employee_id": self.emp, "category_id": self.cat, "reason": "New hire"})[0], 201)
        self.assertEqual(c.get("/api/alerts")[1]["counts"].get("request"), 1)
        c.put("/api/settings", {"alert_warranty_days": 30, "asset_requests_enabled": False})
        self.assertFalse(c.get("/api/branding")[1]["asset_requests"])
        self.assertNotIn("request", c.get("/api/alerts")[1]["counts"])                    # waiting request no longer alerts
        s, js, _ = c.post("/api/requests", {"employee_id": self.emp, "category_id": self.cat, "reason": "x"})
        self.assertEqual((s, js["code"]), (409, "requests_off"))
        self.assertEqual(len(c.get("/api/requests")[1]["requests"]), 1)                   # nothing deleted
        c.put("/api/settings", {"alert_warranty_days": 30})                                # field absent -> kept off
        self.assertFalse(c.get("/api/settings")[1]["asset_requests_enabled"])


if __name__ == "__main__":
    unittest.main()
