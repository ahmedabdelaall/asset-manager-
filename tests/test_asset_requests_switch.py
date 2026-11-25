# -*- coding: utf-8 -*-
"""Switching asset requests off (0.9.0)."""
import unittest

from test_assets import InvBase


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
