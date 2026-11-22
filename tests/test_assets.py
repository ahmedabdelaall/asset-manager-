# -*- coding: utf-8 -*-
"""Phase 2: categories & custom fields, departments, employees, assets, assignments."""
import sqlite3
import unittest

from test_api import Base

LAPTOP = {"code": "lap", "name_en": "Laptops", "name_ar": "حواسيب محمولة",
          "fields": [{"label_en": "RAM (GB)", "label_ar": "الذاكرة", "type": "number", "required": True},
                     {"label_en": "OS", "type": "select", "options": ["Windows", "macOS", "Linux"]},
                     {"label_en": "Has charger", "type": "bool"}]}


class InvBase(Base):
    def setup_inventory(self):
        c = self.admin()
        s, js, _ = c.post("/api/categories", LAPTOP)
        self.assertEqual(s, 201, js)
        self.cat = js["id"]
        s, js, _ = c.post("/api/departments", {"name_en": "IT", "name_ar": "تقنية المعلومات"})
        self.assertEqual(s, 201, js)
        self.dept = js["id"]
        s, js, _ = c.post("/api/employees", {"emp_no": "E-001", "full_name_en": "Sara Ali", "full_name_ar": "سارة علي",
                                             "department_id": self.dept, "email": "sara@acme.test"})
        self.assertEqual(s, 201, js)
        self.emp = js["id"]
        return c

    def new_asset(self, c, **over):
        body = {"category_id": self.cat, "name": "ThinkPad T14", "brand": "Lenovo", "custom": {"ram_gb": 16, "os": "Windows"}}
        body.update(over)
        s, js, _ = c.post("/api/assets", body)
        self.assertEqual(s, 201, js)
        return js["id"], js["tag"]


class TestCategories(InvBase):
    def test_category_fields_codes_and_validation(self):
        c = self.setup_inventory()
        cat = c.get("/api/categories")[1]["categories"][0]
        self.assertEqual(cat["code"], "LAP")
        self.assertEqual([f["key"] for f in cat["fields"]], ["ram_gb", "os", "has_charger"])
        self.assertEqual(c.post("/api/categories", dict(LAPTOP, name_en="Other"))[1]["code"], "category_code_taken")
        self.assertEqual(c.post("/api/categories", {"code": "X", "name_en": "Bad"})[1]["code"], "category_code_invalid")
        self.assertEqual(c.post("/api/categories", {"code": "AB", "name_en": "", "name_ar": ""})[1]["code"], "category_name_required")
        bad = {"code": "SEL", "name_en": "S", "fields": [{"label_en": "Colour", "type": "select", "options": []}]}
        self.assertEqual(c.post("/api/categories", bad)[1]["code"], "select_needs_options")
        # a category with assets cannot be deleted
        self.new_asset(c)
        self.assertEqual(c.delete("/api/categories/%d" % self.cat)[1]["code"], "category_in_use")
        s, js, _ = c.post("/api/categories", {"code": "TMP", "name_ar": "مؤقت"})
        self.assertEqual(c.get("/api/categories")[1]["categories"][-1]["name_en"], "مؤقت")   # falls back to the other language
        self.assertEqual(c.delete("/api/categories/%d" % js["id"])[0], 200)


class TestAssets(InvBase):
    def test_tags_serials_and_custom_fields(self):
        c = self.setup_inventory()
        _, t1 = self.new_asset(c)
        _, t2 = self.new_asset(c, serial_no="SN-1")
        self.assertEqual((t1, t2), ("LAP-00001", "LAP-00002"))
        _, t3 = self.new_asset(c, tag="custom-7")
        self.assertEqual(t3, "CUSTOM-7")
        s, js, _ = c.post("/api/assets", {"category_id": self.cat, "name": "X", "tag": "custom-7", "custom": {"ram_gb": 8}})
        self.assertEqual((s, js["code"]), (409, "asset_tag_taken"))
        s, js, _ = c.post("/api/assets", {"category_id": self.cat, "name": "X", "serial_no": "sn-1", "custom": {"ram_gb": 8}})
        self.assertEqual((s, js["code"]), (409, "serial_taken"))
        s, js, _ = c.post("/api/assets", {"category_id": self.cat, "name": "X"})
        self.assertEqual((js["code"], js["field"]), ("field_required", "custom.ram_gb"))
        s, js, _ = c.post("/api/assets", {"category_id": self.cat, "name": "X", "custom": {"ram_gb": 8, "os": "BeOS"}})
        self.assertEqual((js["code"], js["field"]), ("invalid_field", "custom.os"))
        s, js, _ = c.post("/api/assets", {"category_id": self.cat, "name": "X", "custom": {"ram_gb": "lots"}})
        self.assertEqual(js["code"], "invalid_number")
        self.assertEqual(c.post("/api/assets", {"category_id": self.cat, "name": "X", "custom": {"ram_gb": 8}, "purchase_date": "2026-02-30"})[1]["code"], "invalid_date")
        self.assertEqual(c.post("/api/assets", {"category_id": 999, "name": "X"})[1]["code"], "category_not_found")
        # generated tags skip a number that was taken manually
        self.new_asset(c, tag="LAP-00003")
        self.assertEqual(self.new_asset(c)[1], "LAP-00004")

    def test_search_filter_and_pagination(self):
        c = self.setup_inventory()
        for i in range(5):
            self.new_asset(c, name="Dell %d" % i, serial_no="DL%d" % i)
        self.new_asset(c, name="MacBook", brand="Apple")
        r = c.get("/api/assets?q=dell&per_page=2&page=2")[1]
        self.assertEqual((r["total"], len(r["assets"])), (5, 2))
        self.assertEqual(c.get("/api/assets?q=apple")[1]["total"], 1)
        self.assertEqual(c.get("/api/assets?q=%25")[1]["total"], 0)          # wildcards are literal
        self.assertEqual(c.get("/api/assets?status=assigned")[1]["total"], 0)
        self.assertEqual(c.get("/api/assets?page=x")[0], 400)

    def test_edit_status_and_delete_rules(self):
        c = self.setup_inventory()
        aid, tag = self.new_asset(c)
        s, js, _ = c.put("/api/assets/%d" % aid, {"category_id": self.cat, "name": "Renamed", "location": "HQ", "custom": {"ram_gb": 32}})
        self.assertEqual(s, 200, js)
        a = c.get("/api/assets/%d" % aid)[1]
        self.assertEqual((a["name"], a["tag"], a["custom"]["ram_gb"]), ("Renamed", tag, 32))
        self.assertEqual(c.post("/api/assets/%d/status" % aid, {"status": "assigned"})[1]["code"], "invalid_field")
        self.assertEqual(c.post("/api/assets/%d/status" % aid, {"status": "maintenance"})[0], 200)
        self.assertEqual(c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[1]["code"], "asset_not_available")
        c.post("/api/assets/%d/status" % aid, {"status": "in_stock"})
        actions = [h["action"] for h in c.get("/api/assets/%d" % aid)[1]["history"]]
        self.assertEqual(actions, ["asset.status", "asset.status", "asset.update", "asset.create"])
        self.assertEqual(c.delete("/api/assets/%d" % aid)[0], 200)
        self.assertEqual(c.get("/api/assets/%d" % aid)[0], 404)


class TestAssignments(InvBase):
    def test_full_lifecycle(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        s, js, _ = c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp, "condition": "new", "notes": "With bag"})
        self.assertEqual(s, 201, js)
        a = c.get("/api/assets/%d" % aid)[1]
        self.assertEqual((a["status"], a["holder_id"], a["condition"]), ("assigned", self.emp, "new"))
        self.assertEqual(c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[1]["code"], "asset_already_assigned")
        self.assertEqual(c.post("/api/assets/%d/status" % aid, {"status": "retired"})[1]["code"], "asset_is_assigned")
        self.assertEqual(c.get("/api/assignments")[1]["assignments"][0]["asset_id"], aid)
        e = c.get("/api/employees/%d" % self.emp)[1]
        self.assertEqual((e["holding"], len(e["assignments"])), (1, 1))
        # an employee who still holds assets cannot leave, nor be deleted once they have history
        body = {"emp_no": "E-001", "full_name_en": "Sara Ali", "status": "left"}
        self.assertEqual(c.put("/api/employees/%d" % self.emp, body)[1]["code"], "employee_has_assets")
        s, js, _ = c.post("/api/assets/%d/return" % aid, {"condition": "fair", "status_after": "maintenance"})
        self.assertEqual(s, 200, js)
        a = c.get("/api/assets/%d" % aid)[1]
        self.assertEqual((a["status"], a["holder_id"], a["condition"]), ("maintenance", None, "fair"))
        self.assertEqual(a["assignments"][0]["condition_in"], "fair")
        self.assertEqual(c.post("/api/assets/%d/return" % aid, {})[1]["code"], "asset_not_assigned")
        self.assertEqual(c.delete("/api/assets/%d" % aid)[1]["code"], "asset_has_history")
        self.assertEqual(c.delete("/api/employees/%d" % self.emp)[1]["code"], "employee_has_history")
        self.assertEqual(c.put("/api/employees/%d" % self.emp, body)[0], 200)
        c.post("/api/assets/%d/status" % aid, {"status": "in_stock"})
        self.assertEqual(c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[1]["code"], "employee_inactive")
        actions = [x["action"] for x in c.get("/api/audit?action=asset.")[1]["entries"]]
        self.assertIn("asset.assign", actions)
        self.assertIn("asset.return", actions)
        self.assertTrue(c.post("/api/audit/verify")[1]["ok"])

    def test_overdue_and_dashboard_summary(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c, purchase_cost=1500)
        self.assertEqual(c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp, "expected_return": "2000-01-01"})[1]["code"], "date_in_past")
        c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp, "expected_return": "2999-01-01"})
        self.env.app.db.execute("UPDATE assignments SET expected_return='2000-01-01'")
        self.assertTrue(c.get("/api/assignments")[1]["assignments"][0]["overdue"])
        d = c.get("/api/dashboard")[1]["assets"]
        self.assertEqual((d["total"], d["by_status"]["assigned"], d["overdue"], d["value"]), (1, 1, 1, 1500))

    def test_database_blocks_two_open_assignments(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        c.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})
        with self.assertRaises(sqlite3.IntegrityError):
            self.env.app.db.execute("INSERT INTO assignments(asset_id,employee_id,assigned_at,condition_out) VALUES (?,?,'x','good')", (aid, self.emp))


class TestEmployeesAndPermissions(InvBase):
    def test_employee_rules(self):
        c = self.setup_inventory()
        self.assertEqual(c.post("/api/employees", {"emp_no": "e-001", "full_name_en": "Dup"})[1]["code"], "employee_no_taken")
        self.assertEqual(c.post("/api/employees", {"emp_no": "E-2", "full_name_en": "X", "email": "nope"})[1]["code"], "invalid_email")
        self.assertEqual(c.post("/api/employees", {"emp_no": "E-2", "full_name_en": "X", "department_id": 99})[1]["code"], "department_not_found")
        self.assertEqual(c.delete("/api/departments/%d" % self.dept)[1]["code"], "department_in_use")
        self.assertEqual(len(c.get("/api/employees?q=sara")[1]["employees"]), 1)
        self.assertEqual(len(c.get("/api/employees?department=%d" % self.dept)[1]["employees"]), 1)
        self.assertEqual(len(c.get("/api/employees/lookup?q=E-0")[1]["employees"]), 1)
        s, js, _ = c.post("/api/employees", {"emp_no": "E-3", "full_name_en": "Temp"})
        self.assertEqual(c.delete("/api/employees/%d" % js["id"])[0], 200)

    def test_role_permissions(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        self.make_user(c, "view1", "viewer")
        self.make_user(c, "hr1", "hr")
        self.make_user(c, "amgr", "asset_manager")
        v = self.login_as("view1")
        self.assertEqual(v.get("/api/assets")[0], 200)
        self.assertEqual(v.get("/api/employees")[0], 200)
        self.assertEqual(v.post("/api/assets", {"category_id": self.cat, "name": "X"})[0], 403)
        self.assertEqual(v.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[0], 403)
        self.assertEqual(v.post("/api/categories", {"code": "ZZ", "name_en": "Z"})[0], 403)
        h = self.login_as("hr1")
        self.assertEqual(h.post("/api/employees", {"emp_no": "H-1", "full_name_en": "Hired"})[0], 201)
        self.assertEqual(h.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[0], 403)
        m = self.login_as("amgr")
        self.assertEqual(m.post("/api/employees", {"emp_no": "M-1", "full_name_en": "No"})[0], 403)
        self.assertEqual(m.get("/api/employees/lookup")[0], 200)
        self.assertEqual(m.post("/api/assets/%d/assign" % aid, {"employee_id": self.emp})[0], 201)
        self.assertIn("assets", m.get("/api/dashboard")[1])

    def test_licence_lock_blocks_inventory(self):
        c = self.admin(licensed=False)
        self.assertEqual(c.get("/api/assets")[0], 402)


if __name__ == "__main__":
    unittest.main(verbosity=1)
