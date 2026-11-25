# -*- coding: utf-8 -*-
"""Dismissing alerts from the bell: personal, and an alert comes back when its date changes."""
import datetime
import unittest

from test_assets import InvBase


def D(n):
    return (datetime.date.today() + datetime.timedelta(days=n)).isoformat()


class TestAlertDismiss(InvBase):
    def test_dismiss_clear_restore(self):
        c = self.setup_inventory()
        a1, _ = self.new_asset(c, warranty_until=D(5))
        a2, _ = self.new_asset(c, warranty_until=D(9))
        g = c.post("/api/assets/%d/assign" % a1, {"employee_id": self.emp, "expected_return": D(1)})[1]["id"]
        self.env.app.db.execute("UPDATE assignments SET expected_return=? WHERE id=?", (D(-2), g))
        al = c.get("/api/alerts")[1]
        self.assertEqual((al["total"], al["hidden"]), (3, 0))
        over = [i for i in al["items"] if i["kind"] == "overdue"][0]
        self.assertEqual(over["key"], "overdue:%d:%s" % (a1, D(-2)))

        s, js, _ = c.post("/api/alerts/dismiss", {"keys": [over["key"]]})
        self.assertEqual(s, 200, js)
        self.assertEqual((js["total"], js["hidden"], js["counts"]), (2, 1, {"warranty": 2}))
        # personal: another user still sees it
        self.make_user(c, "view1", "viewer")
        self.assertEqual(self.login_as("view1").get("/api/alerts")[1]["counts"].get("overdue"), 1)
        # a new due date brings the alert back
        self.env.app.db.execute("UPDATE assignments SET expected_return=? WHERE id=?", (D(-1), g))
        self.assertEqual(c.get("/api/alerts")[1]["counts"].get("overdue"), 1)

        # clear all, then show again
        keys = [i["key"] for i in c.get("/api/alerts")[1]["items"]]
        js = c.post("/api/alerts/dismiss", {"keys": keys})[1]
        self.assertEqual((js["total"], js["items"]), (0, []))
        self.assertEqual(c.post("/api/alerts/restore")[1]["total"], 3)
        # bad keys are refused
        for bad in ([], ["x"], ["overdue:1:2024-01-01'; DROP TABLE users"], "overdue:1", [1]):
            self.assertEqual(c.post("/api/alerts/dismiss", {"keys": bad})[0], 400, bad)


if __name__ == "__main__":
    unittest.main()
