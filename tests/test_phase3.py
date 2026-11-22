# -*- coding: utf-8 -*-
"""Phase 3: documents, receipts, Excel import/export."""
import os
import shutil
import sqlite3
import tempfile
import datetime
import unittest
import urllib.parse

from test_api import Base
from test_assets import InvBase, LAPTOP
from core import xlsx
from core.db import Database
from core.server import MIGRATIONS

PDF = b"%PDF-1.4\n% test\n" + b"0" * 200
YEAR = datetime.date.today().year


def up(c, path, data, name="file.pdf"):
    return c.post(path, raw=data, headers={"X-Filename": urllib.parse.quote(name)})


class TestDocuments(InvBase):
    def test_upload_list_download_delete_and_permissions(self):
        c = self.setup_inventory()
        aid, _ = self.new_asset(c)
        s, js, _ = up(c, "/api/documents?entity=asset&id=%d" % aid, PDF, "فاتورة شراء.pdf")
        self.assertEqual(s, 201, js)
        did = js["id"]
        docs = c.get("/api/documents?entity=asset&id=%d" % aid)[1]["documents"]
        self.assertEqual((docs[0]["filename"], docs[0]["mime"], docs[0]["size"]), ("فاتورة شراء.pdf", "application/pdf", len(PDF)))
        s, _, r = c.get("/api/documents/%d/file" % did)
        self.assertEqual((s, r.getheader("Content-Type")), (200, "application/pdf"))
        self.assertTrue(r.getheader("Content-Disposition").startswith("attachment;"))
        self.assertIn("filename*=UTF-8''", r.getheader("Content-Disposition"))
        self.assertTrue(c.get("/api/documents/%d/file?inline=1" % did)[2].getheader("Content-Disposition").startswith("inline;"))
        # the content decides the type, not the name
        self.assertEqual(up(c, "/api/documents?entity=asset&id=%d" % aid, b"<html><script>x</script>", "a.pdf")[1]["code"], "file_bad_type")
        self.assertEqual(up(c, "/api/documents?entity=asset&id=999", PDF)[0], 404)
        self.assertEqual(up(c, "/api/documents?entity=users&id=1", PDF)[0], 400)
        # path tricks in the name are neutralised
        s, js, _ = up(c, "/api/documents?entity=asset&id=%d" % aid, PDF, "../../etc/passwd")
        self.assertEqual(c.get("/api/documents?entity=asset&id=%d" % aid)[1]["documents"][0]["filename"], "passwd.pdf")
        # viewers can read but not add or delete
        self.make_user(c, "view1", "viewer")
        v = self.login_as("view1")
        self.assertEqual(v.get("/api/documents/%d/file" % did)[0], 200)
        self.assertEqual(up(v, "/api/documents?entity=asset&id=%d" % aid, PDF)[0], 403)
        self.assertEqual(v.delete("/api/documents/%d" % did)[0], 403)
        self.assertEqual(c.delete("/api/documents/%d" % did)[0], 200)
        self.assertEqual(c.get("/api/documents/%d/file" % did)[0], 404)
        actions = [h["action"] for h in c.get("/api/assets/%d" % aid)[1]["history"]]
        self.assertIn("document.add", actions)
        self.assertIn("document.delete", actions)

    def test_employee_documents_follow_employee_permissions(self):
        c = self.setup_inventory()
        png = b"\x89PNG\r\n\x1a\n" + b"1" * 100
        self.assertEqual(up(c, "/api/documents?entity=employee&id=%d" % self.emp, png, "id.png")[0], 201)
        self.make_user(c, "amgr", "asset_manager")
        m = self.login_as("amgr")
        self.assertEqual(up(m, "/api/documents?entity=employee&id=%d" % self.emp, png)[0], 403)   # asset managers cannot edit employees
        self.assertEqual(len(m.get("/api/documents?entity=employee&id=%d" % self.emp)[1]["documents"]), 1)


class TestReceipts(InvBase):
    def test_numbers_and_receipt_data(self):
        c = self.setup_inventory()
        a1, _ = self.new_asset(c, serial_no="S1")
        a2, _ = self.new_asset(c)
        g1 = c.post("/api/assets/%d/assign" % a1, {"employee_id": self.emp, "notes": "With bag"})[1]["id"]
        g2 = c.post("/api/assets/%d/assign" % a2, {"employee_id": self.emp})[1]["id"]
        r = c.get("/api/assignments/%d/receipt?kind=handover" % g1)[1]
        self.assertEqual(r["number"], "HO-%d-0001" % YEAR)
        self.assertEqual(c.get("/api/assignments/%d/receipt" % g2)[1]["number"], "HO-%d-0002" % YEAR)
        self.assertEqual((r["asset"]["serial_no"], r["employee"]["emp_no"], r["assignment"]["notes_out"], r["company"]["name_en"]),
                         ("S1", "E-001", "With bag", "Acme Corp"))
        self.assertEqual(r["assignment"]["assigned_by_name"], "Root Admin")
        self.assertEqual(c.get("/api/assignments/%d/receipt?kind=return" % g1)[1]["code"], "receipt_not_ready")
        c.post("/api/assets/%d/return" % a1, {"condition": "fair"})
        r = c.get("/api/assignments/%d/receipt?kind=return" % g1)[1]
        self.assertEqual((r["number"], r["assignment"]["condition_in"]), ("RT-%d-0001" % YEAR, "fair"))
        # a signed copy can be attached to the assignment and is listed on the receipt
        self.assertEqual(up(c, "/api/documents?entity=assignment&id=%d" % g1, PDF, "signed.pdf")[0], 201)
        self.assertEqual(c.get("/api/assignments/%d/receipt?kind=return" % g1)[1]["signed_copies"][0]["filename"], "signed.pdf")
        self.assertEqual(c.get("/api/assignments/999/receipt")[0], 404)

    def test_receipt_terms_are_kept_when_not_sent(self):
        c = self.setup_inventory()
        base = {"name_en": "Acme Corp", "primary_color": "#112233", "accent_color": "#445566"}
        c.put("/api/company", dict(base, receipt_terms_en="Return in good condition.", receipt_terms_ar="يُعاد بحالة جيدة."))
        c.put("/api/company", base)
        co = c.get("/api/company")[1]
        self.assertEqual((co["receipt_terms_en"], co["receipt_terms_ar"]), ("Return in good condition.", "يُعاد بحالة جيدة."))

    def test_migration_numbers_existing_assignments(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        old = os.path.join(tmp, "m")
        os.makedirs(old)
        for f in ("0001_initial.sql", "0002_assets.sql"):
            shutil.copy(os.path.join(MIGRATIONS, f), old)
        db = Database(os.path.join(tmp, "x.db"), old, os.path.join(tmp, "b"))
        db.migrate()
        db.execute("INSERT INTO categories(code,name_en,name_ar,created_at,updated_at) VALUES ('C','C','C','x','x')")
        db.execute("INSERT INTO employees(emp_no,full_name_en,full_name_ar,created_at,updated_at) VALUES ('1','A','A','x','x')")
        for i in range(3):
            db.execute("INSERT INTO assets(tag,category_id,name,created_at,updated_at) VALUES (?,1,'n','x','x')", ("T%d" % i,))
        db.execute("INSERT INTO assignments(asset_id,employee_id,assigned_at,condition_out,returned_at) VALUES (1,1,'2025-05-01T00:00:00Z','good','2026-01-02T00:00:00Z')")
        db.execute("INSERT INTO assignments(asset_id,employee_id,assigned_at,condition_out) VALUES (2,1,'2025-06-01T00:00:00Z','good')")
        db.execute("INSERT INTO assignments(asset_id,employee_id,assigned_at,condition_out) VALUES (3,1,'2026-02-01T00:00:00Z','good')")
        db.close_thread()
        db2 = Database(os.path.join(tmp, "x.db"), MIGRATIONS, os.path.join(tmp, "b"))
        db2.migrate()
        got = [tuple(r) for r in db2.query("SELECT receipt_out_no, receipt_in_no FROM assignments ORDER BY id")]
        self.assertEqual(got, [("HO-2025-0001", "RT-2026-0001"), ("HO-2025-0002", None), ("HO-2026-0001", None)])
        self.assertEqual(db2.one("SELECT value FROM counters WHERE key='HO-2025'")["value"], 2)
        db2.close_thread()


class TestXlsx(unittest.TestCase):
    def test_roundtrip(self):
        data = xlsx.write([{"name": "S/1", "rows": [["a", "b", "c", "d"], ["نص عربي", 12.5, True, None], ["=1+1", 3, "", "x"]], "rtl": True},
                           {"name": "Second", "rows": [["only"]]}])
        rows = xlsx.read(data)
        self.assertEqual(rows[0], ["a", "b", "c", "d"])
        self.assertEqual(rows[1][:3], ["نص عربي", 12.5, True])
        self.assertEqual(rows[2][:2], ["=1+1", 3.0])                 # stored as text, never a formula

    def test_rejects_entity_tricks_and_garbage(self):
        from core.errors import ApiError
        with self.assertRaises(ApiError):
            xlsx.read(b"not a zip")
        import io, zipfile
        b = io.BytesIO()
        z = zipfile.ZipFile(b, "w")
        z.writestr("xl/workbook.xml", '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><workbook/>')
        z.close()
        with self.assertRaises(ApiError):
            xlsx.read(b.getvalue())


def sheet(rows):
    return xlsx.write([{"name": "Data", "rows": rows}])


class TestImportExport(InvBase):
    def imp(self, c, kind, rows, dry=True, update=False, raw=None, name="f.xlsx"):
        return c.post("/api/import/%s?dry_run=%d&update=%d" % (kind, 1 if dry else 0, 1 if update else 0),
                      raw=raw if raw is not None else sheet(rows), headers={"X-Filename": name})

    def test_templates(self):
        c = self.setup_inventory()
        s, _, r = c.get("/api/import/template?type=assets&lang=ar")
        self.assertEqual(s, 200)
        self.assertTrue(r.getheader("Content-Type").startswith("application/vnd.openxmlformats"))
        s, _, r = c.get("/api/import/template?type=assets")
        self.assertEqual(s, 200)
        self.make_user(c, "view1", "viewer")
        self.assertEqual(self.login_as("view1").get("/api/import/template?type=employees")[0], 403)

    def test_employee_import_check_then_commit_then_update(self):
        c = self.setup_inventory()
        rows = [["Emp_No *", "full_name_en", "full_name_ar", "department", "status", "email"],
                [1001, "Omar Hassan", "عمر حسن", "Finance", "", "omar@acme.test"],
                ["1002", "", "ليلى أحمد", "المالية", "نشط", ""],
                ["E-001", "Dup", "", "", "", ""],
                ["1003", "Bad Mail", "", "", "", "nope"],
                ["", "", "", "", "", ""]]
        r = self.imp(c, "employees", rows)[1]
        self.assertEqual((r["total"], r["error_count"], r["committed"]), (4, 2, False))
        self.assertEqual({(e["row"], e["column"], e["code"]) for e in r["errors"]},
                         {(4, "emp_no", "employee_no_taken"), (5, "email", "invalid_email")})
        self.assertEqual(len(c.get("/api/employees?status=")[1]["employees"]), 1)            # nothing written
        r = self.imp(c, "employees", rows[:3], dry=False)[1]
        self.assertEqual((r["created"], r["committed"], r["departments_created"]), (2, True, ["Finance", "المالية"]))
        emps = {e["emp_no"]: e for e in c.get("/api/employees")[1]["employees"]}
        self.assertEqual((emps["1001"]["dept_en"], emps["1002"]["full_name_en"]), ("Finance", "ليلى أحمد"))
        # update mode changes only the columns present in the file
        r = self.imp(c, "employees", [["emp_no", "job_title"], ["1001", "Accountant"]], dry=False, update=True)[1]
        self.assertEqual((r["updated"], r["committed"]), (1, True))
        e = [x for x in c.get("/api/employees")[1]["employees"] if x["emp_no"] == "1001"][0]
        self.assertEqual((e["job_title"], e["email"], e["dept_en"]), ("Accountant", "omar@acme.test", "Finance"))
        self.assertEqual(self.imp(c, "employees", [["full_name_en"], ["x"]])[1]["code"], "missing_columns")
        self.assertIn("import.employees", [x["action"] for x in c.get("/api/audit?action=import.")[1]["entries"]])

    def test_asset_import_custom_fields_assignment_and_all_or_nothing(self):
        c = self.setup_inventory()
        head = ["category_code", "tag", "name", "serial_no", "condition", "purchase_date", "purchase_cost", "ram_gb", "os", "has_charger", "assigned_to"]
        rows = [head,
                ["lap", "", "Dell 5440", "D1", "جيد", "15/03/2026", "1,200.50", 16, "Windows", "yes", "E-001"],
                ["LAP", "LAP-9", "Mac", "", "new", "2026-04-01", "", 8, "macOS", "", ""]]
        r = self.imp(c, "assets", rows)[1]
        self.assertEqual((r["total"], r["error_count"], r["committed"]), (2, 0, False))
        self.assertEqual(c.get("/api/assets")[1]["total"], 0)
        r = self.imp(c, "assets", rows, dry=False)[1]
        self.assertEqual((r["created"], r["committed"]), (2, True))
        a = {x["tag"]: x for x in c.get("/api/assets")[1]["assets"]}
        dell = a["LAP-00001"]
        self.assertEqual((dell["status"], dell["holder_no"], dell["purchase_date"], dell["purchase_cost"], dell["condition"]),
                         ("assigned", "E-001", "2026-03-15", 1200.5, "good"))
        self.assertEqual(dell["custom"], {"ram_gb": 16.0, "os": "Windows", "has_charger": True})
        # one bad row -> nothing is imported
        bad = [head, ["LAP", "", "OK row", "", "", "", "", 4, "", "", ""], ["LAP", "", "Bad", "D1", "", "", "", "", "BeOS", "", "X-404"]]
        r = self.imp(c, "assets", bad, dry=False)[1]
        self.assertFalse(r["committed"])
        self.assertEqual({(e["column"], e["code"]) for e in r["errors"]}, {("serial_no", "serial_taken")})
        self.assertEqual(c.get("/api/assets")[1]["total"], 2)
        self.assertEqual(self.imp(c, "assets", [head, ["ZZZ", "", "x"] + [""] * 8])[1]["errors"][0]["code"], "category_not_found")

    def test_csv_and_export_reimport_roundtrip(self):
        c = self.setup_inventory()
        csv = "category_code;name;ram_gb\nLAP;Lenovo;32\n".encode("utf-8-sig")
        r = self.imp(c, "assets", None, dry=False, raw=csv, name="a.csv")[1]
        self.assertEqual((r["created"], r["committed"]), (1, True), r)
        s, _, resp = c.get("/api/export/assets?lang=ar")
        self.assertEqual(s, 200)
        self.assertIn("attachment;", resp.getheader("Content-Disposition"))
        rows = xlsx.read(self.raw_get(c, "/api/export/assets"))
        self.assertEqual(rows[0][:3], ["category_code", "tag", "name"])
        rows[1][2] = "Lenovo X1"
        r = self.imp(c, "assets", rows, dry=False, update=True)[1]
        self.assertEqual((r["updated"], r["committed"]), (1, True), r)
        self.assertEqual(c.get("/api/assets")[1]["assets"][0]["name"], "Lenovo X1")
        for p in ("/api/export/employees", "/api/export/assignments?open=1"):
            self.assertEqual(c.get(p)[0], 200)

    def raw_get(self, c, path):
        import http.client
        h = http.client.HTTPConnection("127.0.0.1", self.env.port, timeout=15)
        h.request("GET", path, headers={"Host": "127.0.0.1:%d" % self.env.port, "Cookie": "am_session=" + c.cookie})
        data = h.getresponse().read()
        h.close()
        return data


if __name__ == "__main__":
    unittest.main(verbosity=1)
