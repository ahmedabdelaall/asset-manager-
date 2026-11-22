# -*- coding: utf-8 -*-
"""Phase 4: reports, depreciation, dashboard analytics."""
import datetime
import unittest

from test_assets import InvBase, LAPTOP
from core import reports, xlsx

TODAY = datetime.date.today()
D = lambda days: (TODAY + datetime.timedelta(days=days)).isoformat()


class TestDepreciation(unittest.TestCase):
    def test_straight_line(self):
        as_of = datetime.date(2026, 1, 1)
        age, acc, book = reports.depreciation(1200.0, "2024-01-01", 4, as_of)
        self.assertEqual(age, 2.0)
        self.assertAlmostEqual(book, 600.0, delta=1)
        self.assertEqual(reports.depreciation(1200.0, "2015-01-01", 4, as_of)[2], 0.0)       # fully depreciated, never negative
        self.assertEqual(reports.depreciation(1200.0, "2024-01-01", 0, as_of)[2], 1200.0)    # category not depreciated
        self.assertEqual(reports.depreciation(1200.0, "", 4, as_of), (None, None, 1200.0))  # unknown purchase date
        self.assertEqual(reports.depreciation(None, "2024-01-01", 4, as_of), (None, None, None))


class TestReports(InvBase):
    def setup_data(self):
        c = self.setup_inventory()
        cat = c.get("/api/categories")[1]["categories"][0]
        s, js, _ = c.put("/api/categories/%d" % self.cat, dict(LAPTOP, useful_life_years=4, fields=cat["fields"]))
        self.assertEqual(s, 200, js)
        self.a1, _ = self.new_asset(c, purchase_cost=1200, purchase_date=D(-730), warranty_until=D(10))
        self.a2, _ = self.new_asset(c, purchase_cost=800, warranty_until=D(-5))
        self.g1 = c.post("/api/assets/%d/assign" % self.a1, {"employee_id": self.emp, "expected_return": D(5)})[1]["id"]
        self.env.app.db.execute("UPDATE assignments SET expected_return=? WHERE id=?", (D(-3), self.g1))
        return c

    def test_holdings_overdue_warranty(self):
        c = self.setup_data()
        r = c.get("/api/reports/holdings")[1]
        self.assertEqual((r["rows"][0]["emp_no"], r["rows"][0]["count"], r["totals"]["value"]), ("E-001", 1, 1200))
        self.assertEqual(c.get("/api/reports/holdings?department=999")[1]["rows"], [])
        r = c.get("/api/reports/overdue")[1]
        self.assertEqual((len(r["rows"]), r["rows"][0]["days"]), (1, 3))
        r = c.get("/api/reports/warranty")[1]
        self.assertEqual([(x["asset_id"], x["days_left"]) for x in r["rows"]], [(self.a1, 10)])
        r = c.get("/api/reports/warranty?expired=1&days=30")[1]
        self.assertEqual({x["asset_id"] for x in r["rows"]}, {self.a1, self.a2})

    def test_value_and_activity(self):
        c = self.setup_data()
        r = c.get("/api/reports/value")[1]
        row = [x for x in r["rows"] if x["asset_id"] == self.a1][0]
        self.assertEqual(row["life"], 4)
        self.assertAlmostEqual(row["book"], 600, delta=5)
        self.assertEqual(r["totals"]["cost"], 2000)
        self.assertEqual(r["summary"]["rows"][0]["count"], 2)
        c.post("/api/assets/%d/status" % self.a2, {"status": "retired"})
        self.assertEqual(c.get("/api/reports/value")[1]["totals"]["tag"], 1)
        self.assertEqual(c.get("/api/reports/value?disposed=1")[1]["totals"]["tag"], 2)
        c.post("/api/assets/%d/return" % self.a1, {})
        r = c.get("/api/reports/activity")[1]
        self.assertEqual((r["totals"]["handover"], r["totals"]["return"]), (1, 1))
        self.assertEqual(r["rows"][0]["event"], "return")
        self.assertEqual(c.get("/api/reports/activity?from=%s&to=%s" % (D(-60), D(-30)))[1]["rows"], [])
        self.assertEqual(c.get("/api/reports/activity?from=%s&to=%s" % (D(1), D(-1)))[1]["code"], "date_range_invalid")
        self.assertEqual(c.get("/api/reports/activity?from=bad")[1]["code"], "invalid_date")
        self.assertEqual(c.get("/api/reports/nope")[0], 404)

    def test_excel_export_and_analytics(self):
        c = self.setup_data()
        import http.client
        h = http.client.HTTPConnection("127.0.0.1", self.env.port, timeout=15)
        h.request("GET", "/api/reports/value?format=xlsx&lang=ar", headers={"Host": "127.0.0.1:%d" % self.env.port, "Cookie": "am_session=" + c.cookie})
        resp = h.getresponse()
        data = resp.read()
        self.assertEqual(resp.status, 200)
        rows = xlsx.read(data)
        self.assertEqual(rows[0][0], "رمز الأصل")
        self.assertTrue(str(rows[-1][0]).startswith("الإجمالي"))
        a = c.get("/api/analytics")[1]
        self.assertEqual(len(a["monthly"]), 12)
        self.assertEqual(a["monthly"][-1]["month"], TODAY.strftime("%Y-%m"))
        self.assertEqual(a["monthly"][-1]["handovers"], 1)
        self.assertEqual((a["by_category"][0]["count"], a["by_department"][0]["count"]), (2, 1))

    def test_permissions_and_category_life(self):
        c = self.setup_data()
        self.make_user(c, "view1", "viewer")
        self.assertEqual(self.login_as("view1").get("/api/reports/value")[0], 200)
        s, js, _ = c.post("/api/roles", {"name_en": "Desk", "permissions": ["dashboard.view", "assets.view"]})
        rid = js["id"]
        c.post("/api/users", {"username": "desk1", "full_name": "Desk", "role_id": rid, "password": "Valid-Pass-123"})
        self.assertEqual(self.login_as("desk1").get("/api/reports/holdings")[0], 403)
        bad = dict(LAPTOP, code="L2", name_en="L2", useful_life_years=2.5, fields=[])
        self.assertEqual(c.post("/api/categories", bad)[1]["code"], "invalid_number")


if __name__ == "__main__":
    unittest.main(verbosity=1)
