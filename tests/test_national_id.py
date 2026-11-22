# -*- coding: utf-8 -*-
"""Employee national ID (0.9.0): validation, uniqueness, receipts, who may see it, Excel, audit."""
import unittest

from test_assets import InvBase
import test_phase3                          # module import (not the class), so its tests are not collected twice
from core import xlsx

NID = "29901011234567"                      # Egyptian format: century 2, 1999-01-01


class TestNationalId(InvBase):
    def put_emp(self, c, **over):
        e = c.get("/api/employees/%d" % self.emp)[1]
        body = {k: e[k] for k in ("emp_no", "full_name_en", "full_name_ar", "department_id", "job_title", "email", "phone", "status", "notes")}
        body.update(over)
        return c.put("/api/employees/%d" % self.emp, body)

    def test_validation_and_uniqueness(self):
        c = self.setup_inventory()
        # Arabic-Indic digits, spaces and dashes are accepted and stored as plain digits
        s, js, _ = self.put_emp(c, national_id="٢٩٩ ٠١٠١-١٢٣٤٥٦٧")
        self.assertEqual(s, 200, js)
        self.assertEqual(c.get("/api/employees/%d" % self.emp)[1]["national_id"], NID)
        for bad, code in (("29913011234567", "national_id_invalid_eg"),      # month 13
                          ("19901011234567", "national_id_invalid_eg"),      # century digit 1
                          ("12-34", "national_id_invalid"), ("ABC$1234", "national_id_invalid")):
            s, js, _ = self.put_emp(c, national_id=bad)
            self.assertEqual((s, js["code"], js["field"]), (422, code, "national_id"), bad)
        self.assertEqual(self.put_emp(c, national_id="a1234567")[0], 200)                          # passport: upper-cased
        self.assertEqual(c.get("/api/employees/%d" % self.emp)[1]["national_id"], "A1234567")
        self.put_emp(c, national_id=NID)
        s, js, _ = c.post("/api/employees", {"emp_no": "E-002", "full_name_en": "Omar", "national_id": NID})
        self.assertEqual((s, js["code"]), (409, "national_id_taken"))
        # empty is allowed for many employees; not sending the field keeps the stored value
        self.assertEqual(c.post("/api/employees", {"emp_no": "E-003", "full_name_en": "Mona"})[0], 201)
        self.assertEqual(c.post("/api/employees", {"emp_no": "E-004", "full_name_en": "Hany", "national_id": ""})[0], 201)
        self.assertEqual(self.put_emp(c, job_title="Engineer")[0], 200)
        self.assertEqual(c.get("/api/employees/%d" % self.emp)[1]["national_id"], NID)

    def test_receipt_visibility_and_audit(self):
        c = self.setup_inventory()
        self.put_emp(c, national_id=NID)
        aid, _ = self.new_asset(c)
        g = c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[1]["id"]
        r = c.get("/api/assignments/%d/receipt?kind=handover" % g)[1]
        self.assertEqual((r["employee"]["national_id"], r["employee"]["national_id_masked"]), (NID, False))
        # lists never carry the number
        e = c.get("/api/employees")[1]["employees"][0]
        self.assertNotIn("national_id", e)
        self.assertTrue(e["has_national_id"])
        # a viewer (assets.view + employees.view, no manage rights) only sees the last 4 digits
        self.make_user(c, "view1", "viewer")
        v = self.login_as("view1")
        r = v.get("/api/assignments/%d/receipt?kind=handover" % g)[1]
        self.assertEqual((r["employee"]["national_id"], r["employee"]["national_id_masked"]), ("••••••••••4567", True))
        self.assertEqual(v.get("/api/employees/%d" % self.emp)[1]["national_id"], "••••••••••4567")
        self.assertNotIn(NID, str(v.get("/api/employees")[1]))
        # the permanent audit log never contains the full number
        self.put_emp(c, national_id="")
        log = str(c.get("/api/audit?entity=employee")[1])
        self.assertNotIn(NID, log)
        self.assertIn("4567", log)
        self.assertIn("(removed)", log)


class TestNationalIdExcel(InvBase):
    imp, raw_get = test_phase3.TestImportExport.imp, test_phase3.TestImportExport.raw_get

    def test_import_and_export(self):
        c = self.setup_inventory()
        rows = [["emp_no", "full_name_en", "national_id"], ["1001", "Omar Hassan", 29901011234567.0], ["1002", "Laila", "bad!"]]
        js = self.imp(c, "employees", rows)[1]
        self.assertEqual((js["errors"][0]["code"], js["errors"][0]["row"]), ("national_id_invalid", 3), js)
        rows.pop()
        s, js, _ = self.imp(c, "employees", rows, dry=False)
        self.assertEqual((s, js["committed"]), (200, True), js)
        flat = str(xlsx.read(self.raw_get(c, "/api/export/employees")))
        self.assertIn("national_id", flat)
        self.assertIn(NID, flat)                                                  # Excel number came back as the full 14 digits
        self.make_user(c, "view1", "viewer")
        v = self.login_as("view1")
        flat = str(xlsx.read(self.raw_get(v, "/api/export/employees")))
        self.assertNotIn("national_id", flat)
        self.assertNotIn(NID, flat)


class TestPastHandoverDates(InvBase):
    imp = test_phase3.TestImportExport.imp

    def test_import_assigned_on_and_backdated_history(self):
        c = self.setup_inventory()
        rows = [["category_code", "name", "ram_gb", "assigned_to", "assigned_on"],
                ["LAP", "Old laptop", 8, "E-001", "8/10/2024"]]
        s, js, _ = self.imp(c, "assets", rows, dry=False)
        self.assertEqual((s, js["committed"]), (200, True), js)
        a = c.get("/api/assets")[1]["assets"][0]
        g = c.get("/api/assets/%d" % a["id"])[1]["assignments"][0]
        self.assertEqual((g["assigned_at"], g["receipt_out_no"]), ("2024-10-08T10:00:00Z", "HO-2024-0001"))
        # a future date is refused; assigned_on without assigned_to is refused
        js = self.imp(c, "assets", [rows[0], ["LAP", "X", 8, "E-001", "1/1/2999"]])[1]
        self.assertEqual(js["errors"][0]["code"], "date_in_future")
        js = self.imp(c, "assets", [rows[0], ["LAP", "X", 8, "", "1/1/2024"]])[1]
        self.assertEqual(js["errors"][0]["code"], "field_required")
        # trusted code can record a past return and a later handover; dates must stay in order
        from core import inventory as inv
        app = self.env.app
        ctx = type("Ctx", (), {"db": app.db, "user": {"id": 1, "username": "root"}, "audit": lambda self, *a, **k: None})()
        e2 = c.post("/api/employees", {"emp_no": "E-002", "full_name_ar": "عمر"})[1]["id"]
        with self.assertRaises(Exception) as cm:
            inv.return_asset(ctx, a["id"], {}, at="2024-01-01")
        self.assertEqual(cm.exception.code, "date_before_handover")
        inv.return_asset(ctx, a["id"], {}, at="2026-11-01")
        with self.assertRaises(Exception) as cm:
            inv.assign(ctx, a["id"], {"employee_id": e2}, at="2026-10-01")
        self.assertEqual(cm.exception.code, "date_before_return")
        inv.assign(ctx, a["id"], {"employee_id": e2}, at="2026-11-01")
        hist = c.get("/api/assets/%d" % a["id"])[1]["assignments"]
        self.assertEqual(sorted((h["receipt_out_no"], h["receipt_in_no"]) for h in hist),
                         [("HO-2024-0001", "RT-2026-0001"), ("HO-2026-0001", None)])
        # the export still lines its columns up with the header
        rows = __import__("core.xlsx", fromlist=["x"]).read(test_phase3.TestImportExport.raw_get(self, c, "/api/export/assets"))
        head = rows[0]
        self.assertEqual(rows[1][head.index("holder_emp_no")], "E-002")
        self.assertEqual(rows[1][head.index("assigned_at")], "2026-11-01")
        self.assertNotIn("assigned_on", head)


if __name__ == "__main__":
    unittest.main()
