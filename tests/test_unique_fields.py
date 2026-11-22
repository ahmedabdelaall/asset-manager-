# -*- coding: utf-8 -*-
"""Unique custom fields (0.9.0): e.g. a mobile line's phone number may not be used twice in its category."""
import unittest

from test_assets import InvBase

LINES = {"code": "SIM", "name_en": "Mobile lines", "fields": [
    {"key": "phone_number", "label_en": "Phone number", "type": "text", "required": True, "unique": True},
    {"key": "account", "label_en": "Account", "type": "text"},
    {"key": "flag", "label_en": "Flag", "type": "bool", "unique": True}]}            # unique is ignored for yes/no fields


class TestUniqueFields(InvBase):
    def test_unique_value_per_category(self):
        c = self.setup_inventory()
        s, js, _ = c.post("/api/categories", LINES)
        self.assertEqual(s, 201, js)
        cat = next(x for x in c.get("/api/categories")[1]["categories"] if x["code"] == "SIM")
        self.assertEqual([(f["key"], f["unique"]) for f in cat["fields"]], [("phone_number", True), ("account", False), ("flag", False)])
        line = lambda num, **o: c.post("/api/assets", dict({"category_id": cat["id"], "name": "Line", "custom": {"phone_number": num}}, **o))
        s, js, _ = line("01000000001")
        self.assertEqual(s, 201, js)
        first = js["id"]
        s, js, _ = line("01000000001")
        self.assertEqual((s, js["code"], js["field"], js["tag"]), (409, "custom_value_taken", "custom.phone_number", "SIM-00001"))
        s, js, _ = line("01000000002")
        self.assertEqual(s, 201, js)
        # editing an asset keeps its own value; changing it onto another asset's value is refused
        a = c.get("/api/assets/%d" % first)[1]
        body = {k: a[k] for k in ("category_id", "name", "brand", "model", "serial_no", "condition", "notes")}
        body["custom"] = {"phone_number": "01000000001", "account": "X"}
        self.assertEqual(c.put("/api/assets/%d" % first, body)[0], 200)
        body["custom"] = {"phone_number": "01000000002"}
        self.assertEqual(c.put("/api/assets/%d" % first, body)[1]["code"], "custom_value_taken")
        # the same value is fine in another category (uniqueness is per category)
        lap = next(x for x in c.get("/api/categories")[1]["categories"] if x["code"] == "LAP")
        self.assertEqual(c.post("/api/assets", {"category_id": lap["id"], "name": "L", "custom": {"ram_gb": 8}})[0], 201)

    def test_cannot_switch_on_with_existing_duplicates(self):
        c = self.setup_inventory()
        body = dict(LINES, fields=[dict(LINES["fields"][0], unique=False)])
        cid = c.post("/api/categories", body)[1]["id"]
        for _ in range(2):
            self.assertEqual(c.post("/api/assets", {"category_id": cid, "name": "Line", "custom": {"phone_number": "0100"}})[0], 201)
        s, js, _ = c.put("/api/categories/%d" % cid, dict(body, fields=[LINES["fields"][0]]))
        self.assertEqual((s, js["code"], js["value"], js["count"]), (409, "field_values_not_unique", "0100", 2))
        cat = next(x for x in c.get("/api/categories")[1]["categories"] if x["id"] == cid)
        self.assertFalse(cat["fields"][0]["unique"])                                     # rolled back


if __name__ == "__main__":
    unittest.main()
