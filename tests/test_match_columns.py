# -*- coding: utf-8 -*-
"""Importing sheets that do not follow the template: header row below a title, any sheet, suggested and
remembered column matching, one category for the whole sheet, category names and holders by name."""
import json
import unittest
import urllib.parse

from test_assets import InvBase
from core import xlsx


def book(*sheets):
    return xlsx.write([{"name": n, "rows": rows} for n, rows in sheets])


class TestMatchColumns(InvBase):
    def columns(self, c, kind, data, sheet=0):
        return c.post("/api/import/%s/columns?sheet=%d" % (kind, sheet), raw=data, headers={"X-Filename": "f.xlsx"})

    def imp(self, c, kind, data, mapping, dry=True, sheet=0, category=""):
        q = urllib.parse.urlencode({"dry_run": 1 if dry else 0, "sheet": sheet, "category": category})
        return c.post("/api/import/%s?%s" % (kind, q), raw=data,
                      headers={"X-Filename": "f.xlsx", "X-Mapping": urllib.parse.quote(json.dumps(mapping))})

    def test_messy_asset_sheet(self):
        c = self.setup_inventory()
        data = book(("Notes", [["ignore me"]]),
                    ("Laptops", [["NDS - Laptop register 2025"], [],
                                 ["Device", "S/N", "Brand", "Employee Name", "Handover Date", "Price", "Colour"],
                                 ["ThinkPad T14", "SN-100", "Lenovo", "Sara Ali", "2025-03-01", "1,250", "black"],
                                 ["Latitude 5440", "SN-101", "Dell", "", "", "", "grey"]]))
        s, js, _ = self.columns(c, "assets", data, sheet=1)
        self.assertEqual(s, 200, js)
        self.assertEqual((js["sheets"], js["header_row"], js["rows"]), (["Notes", "Laptops"], 3, 2))
        sug = {col["header"]: col["suggested"] for col in js["columns"]}
        self.assertEqual(sug, {"Device": "name", "S/N": "serial_no", "Brand": "brand", "Employee Name": "assigned_to",
                               "Handover Date": "assigned_on", "Price": "purchase_cost", "Colour": ""})
        self.assertTrue(any(f["key"] == "ram_gb" and f["custom"] for f in js["fields"]))
        mapping = {str(col["index"]): col["suggested"] for col in js["columns"]}
        # no category column: required unless one category is chosen for the whole sheet
        self.assertEqual(self.imp(c, "assets", data, mapping, sheet=1)[1]["code"], "missing_columns")
        s, r, _ = self.imp(c, "assets", data, mapping, sheet=1, category="lap")
        self.assertEqual(s, 200, r)
        # RAM is a required custom field of Laptops: the errors carry the real Excel row numbers
        self.assertEqual(sorted({e["row"] for e in r["errors"]}), [4, 5])
        c.put("/api/categories/%d" % self.cat, {"code": "LAP", "name_en": "Laptops", "name_ar": "حواسيب محمولة", "fields": []})
        s, r, _ = self.imp(c, "assets", data, mapping, dry=False, sheet=1, category="LAP")
        self.assertTrue(r["committed"], r)
        assets = c.get("/api/assets?sort=name")[1]["assets"]
        lat, tp = assets
        self.assertEqual((tp["serial_no"], tp["holder_no"], tp["purchase_cost"], tp["assigned_at"][:10]), ("SN-100", "E-001", 1250, "2025-03-01"))
        self.assertIsNone(lat["holder_id"])
        self.assertEqual(r["ignored_columns"], ["Colour"])                         # the title row is not a column

    def test_choices_are_remembered_and_category_names(self):
        c = self.setup_inventory()
        c.put("/api/categories/%d" % self.cat, {"code": "LAP", "name_en": "Laptops", "name_ar": "حواسيب محمولة", "fields": []})
        data = book(("S", [["Gadget", "Kind", "Junk"], ["X1 Carbon", "حواسيب محمولة", "z"]]))
        js = self.columns(c, "assets", data)[1]
        self.assertEqual([col["suggested"] for col in js["columns"]], ["", "category_code", ""])
        s, r, _ = self.imp(c, "assets", data, {"0": "name", "1": "category_code", "2": ""}, dry=False)
        self.assertTrue(r["committed"], r)
        self.assertEqual(c.get("/api/assets")[1]["assets"][0]["cat_code"], "LAP")          # category given by its Arabic name
        js = self.columns(c, "assets", book(("S", [["GADGET", "Junk", "Kind"], ["a", "b", "Laptops"]])))[1]
        self.assertEqual([col["suggested"] for col in js["columns"]], ["name", "", "category_code"])
        # mistakes in the mapping
        self.assertEqual(self.imp(c, "assets", data, {"0": "name", "1": "name"})[1]["code"], "mapping_duplicate")
        self.assertEqual(self.imp(c, "assets", data, {"0": "nope", "1": "category_code"})[1]["code"], "mapping_unknown_field")
        self.assertEqual(self.imp(c, "assets", data, {"9": "name"})[0], 400)
        self.assertEqual(self.columns(c, "assets", data, sheet=4)[1]["code"], "sheet_not_found")

    def test_employee_sheet_in_arabic(self):
        c = self.setup_inventory()
        data = book(("موظفين", [["Code", "Name", "Mobile", "الادارة", "الرقم القومى"],
                                ["E-200", "منى سمير", "01000000000", "المالية", "29901011234567"]]))
        js = self.columns(c, "employees", data)[1]
        self.assertEqual([col["suggested"] for col in js["columns"]], ["emp_no", "full_name_ar", "phone", "department", "national_id"])
        mapping = {str(col["index"]): col["suggested"] for col in js["columns"]}
        s, r, _ = self.imp(c, "employees", data, mapping, dry=False)
        self.assertTrue(r["committed"], r)
        self.assertEqual(r["departments_created"], ["المالية"])
        e = [x for x in c.get("/api/employees")[1]["employees"] if x["emp_no"] == "E-200"][0]
        self.assertEqual((e["full_name_ar"], e["phone"], e["has_national_id"]), ("منى سمير", "01000000000", True))
        # the template layout still works without any mapping
        tpl = book(("S", [["emp_no", "full_name_en"], ["E-201", "Ali Hassan"]]))
        s, r, _ = c.post("/api/import/employees?dry_run=0", raw=tpl, headers={"X-Filename": "f.xlsx"})
        self.assertTrue(r["committed"], r)

    def test_holder_by_name_must_be_unique(self):
        c = self.setup_inventory()
        c.put("/api/categories/%d" % self.cat, {"code": "LAP", "name_en": "Laptops", "fields": []})
        c.post("/api/employees", {"emp_no": "E-002", "full_name_en": "Sara Ali"})
        data = book(("S", [["Device", "Holder"], ["T14", "sara ali"], ["T15", "Nobody"]]))
        s, r, _ = self.imp(c, "assets", data, {"0": "name", "1": "assigned_to"}, category="LAP")
        self.assertEqual([e["code"] for e in r["errors"]], ["employee_ambiguous", "employee_not_found"])
        self.assertEqual([e["column"] for e in r["errors"]], ["assigned_to", "assigned_to"])

    def test_phone_lines_with_national_ids(self):
        """A mobile-lines register: no name column, holders given by name + national ID, some not employees yet."""
        c = self.setup_inventory()
        s, js, _ = c.post("/api/categories", {"code": "SIM", "name_en": "Mobile lines", "name_ar": "خطوط المحمول",
                                              "fields": [{"label_en": "Phone number", "type": "text", "required": True, "unique": True}]})
        c.post("/api/employees", {"emp_no": "NDS-007", "full_name_en": "Old Person", "national_id": "29903030100882"})
        data = book(("Lines", [["Mobile lines register"], [],
                               ["Employee Name", "National ID", "Receipt Date", "Phone Number"],
                               ["Someone Renamed", "29903030100882", "11/10/2025", "01026261465"],
                               ["بسمه محمد السيد كمال", "30309202106906", "28/10/2025", "01095575776"],
                               ["بسمه محمد السيد كمال", "30309202106906", "28/10/2025", "01020096000"]]))
        cols = self.columns(c, "assets", data)[1]["columns"]
        self.assertEqual([x["suggested"] for x in cols], ["assigned_to", "holder_national_id", "assigned_on", "phone_number"])
        mapping = {str(x["index"]): x["suggested"] for x in cols}
        # without "add holders" the new person is refused
        r = self.imp(c, "assets", data, mapping, category="SIM")[1]
        self.assertEqual([e["code"] for e in r["errors"]], ["employee_not_found", "employee_not_found"])
        q = urllib.parse.urlencode({"dry_run": 0, "category": "SIM", "add_people": 1})
        s, r, _ = c.post("/api/import/assets?" + q, raw=data,
                         headers={"X-Filename": "f.xlsx", "X-Mapping": urllib.parse.quote(json.dumps(mapping))})
        self.assertTrue(r["committed"], r)
        self.assertEqual(r["employees_created"], ["بسمه محمد السيد كمال"])                 # added once, holds two lines
        lines = {a["custom"]["phone_number"]: a for a in c.get("/api/assets?category=%d" % js["id"])[1]["assets"]}
        self.assertEqual(lines["01026261465"]["name"], "Mobile lines 01026261465")
        self.assertEqual(lines["01026261465"]["holder_no"], "NDS-007")                     # found by national ID, not name
        self.assertEqual(lines["01095575776"]["holder_no"], "NDS-008")                     # numbering continues
        self.assertEqual(lines["01020096000"]["holder_no"], "NDS-008")
        self.assertEqual(lines["01095575776"]["assigned_at"][:10], "2025-10-28")
        emp = [e for e in c.get("/api/employees")[1]["employees"] if e["emp_no"] == "NDS-008"][0]
        self.assertEqual((emp["full_name_ar"], emp["has_national_id"]), ("بسمه محمد السيد كمال", True))
        # a bad national ID is reported on that column
        bad = book(("L", [["Employee Name", "National ID", "Phone Number"], ["X Y", "12", "0100"]]))
        r = self.imp(c, "assets", bad, {"0": "assigned_to", "1": "holder_national_id", "2": "phone_number"}, category="SIM")[1]
        self.assertEqual(r["errors"][0]["column"], "holder_national_id")

    def test_permissions(self):
        c = self.setup_inventory()
        self.make_user(c, "view1", "viewer")
        v = self.login_as("view1")
        self.assertEqual(self.columns(v, "assets", book(("S", [["a"], ["b"]])))[0], 403)


if __name__ == "__main__":
    unittest.main()
