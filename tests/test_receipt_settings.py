# -*- coding: utf-8 -*-
"""Receipt layout, correcting a saved handover, and switching asset requests off (0.9.0)."""
import unittest

from test_assets import InvBase
from core import inventory as inv


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


class TestEditHandover(InvBase):
    def test_correct_dates_condition_and_notes(self):
        c = self.setup_inventory()
        app = self.env.app
        ctx = type("Ctx", (), {"db": app.db, "user": {"id": 1, "username": "root"}, "audit": lambda self, *a, **k: None})()
        aid, _ = self.new_asset(c)
        g1 = inv.assign(ctx, aid, {"employee_id": self.emp}, at="2025-01-10")
        inv.return_asset(ctx, aid, {}, at="2025-06-01")
        g2 = inv.assign(ctx, aid, {"employee_id": self.emp}, at="2025-06-05")
        # fix the first handover: date, condition and notes; the receipt number is unchanged
        s, js, _ = c.put("/api/assignments/%d" % g1, {"assigned_on": "2025-01-08", "condition_out": "fair", "notes_out": "Charger missing",
                                                     "returned_on": "2025-06-02", "condition_in": "poor", "notes_in": "Scratched"})
        self.assertEqual(s, 200, js)
        r = c.get("/api/assignments/%d/receipt" % g1)[1]["assignment"]
        self.assertEqual((r["assigned_at"][:10], r["condition_out"], r["notes_out"], r["returned_at"][:10], r["condition_in"], r["receipt_out_no"]),
                         ("2025-01-08", "fair", "Charger missing", "2025-06-02", "poor", "HO-2025-0001"))
        # dates must stay in order
        self.assertEqual(c.put("/api/assignments/%d" % g1, {"returned_on": "2025-01-01"})[1]["code"], "date_before_handover")
        self.assertEqual(c.put("/api/assignments/%d" % g1, {"returned_on": "2025-07-01"})[1]["code"], "date_after_next")
        self.assertEqual(c.put("/api/assignments/%d" % g2, {"assigned_on": "2025-05-01"})[1]["code"], "date_before_return")
        self.assertEqual(c.put("/api/assignments/%d" % g2, {"assigned_on": "2999-01-01"})[1]["code"], "date_in_future")
        self.assertEqual(c.put("/api/assignments/%d" % g2, {"returned_on": "2025-07-01"})[1]["code"], "asset_not_returned")
        self.assertEqual(c.put("/api/assignments/%d" % g2, {"expected_return": "2025-12-31"})[0], 200)   # past dates allowed when correcting
        # audited, with the notes text kept out of the permanent log
        e = [x for x in c.get("/api/audit?action=assignment")[1]["entries"] if x["action"] == "assignment.update"]
        self.assertEqual(len(e), 2)
        self.assertNotIn("Charger missing", str(e))
        self.assertIn("notes_out", str(e))
        # only people who manage assignments
        self.make_user(c, "view1", "viewer")
        self.assertEqual(self.login_as("view1").put("/api/assignments/%d" % g1, {"notes_out": "x"})[0], 403)


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
