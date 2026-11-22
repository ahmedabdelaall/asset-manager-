# -*- coding: utf-8 -*-
"""Performance check with a large, realistic data set (not part of the unit tests - run it by hand):

    cd tests && python perf_check.py            # default: 20k assets, 5k employees, 25k assignments
    python perf_check.py --assets 50000

It seeds a throw-away instance directly through SQL, then times every main screen/report through the real HTTP server
(median of several runs) and prints the slowest. Target: every page under 500 ms on modest hardware."""
import sys
import time
import random
import argparse
import statistics
import http.client

from helpers import Env, Client, do_setup, SETUP


def seed(env, n_assets, n_emp):
    from core import audit
    db, rnd = env.app.db, random.Random(7)
    now = "2026-01-01T08:00:00Z"
    t0 = time.time()
    with db.tx():
        cats = []
        for i in range(30):
            cur = db.execute("INSERT INTO categories(code,name_en,name_ar,created_at,updated_at,useful_life_years) VALUES (?,?,?,?,?,?)",
                             ("C%02d" % i, "Category %d" % i, "تصنيف %d" % i, now, now, rnd.choice([0, 3, 4, 5])))
            cats.append(cur.lastrowid)
            db.execute("INSERT INTO category_fields(category_id,key,label_en,label_ar,type,options,required,sort) VALUES (?,?,?,?,?,?,?,?)",
                       (cur.lastrowid, "ram_gb", "RAM", "الذاكرة", "number", "[]", 0, 0))
        depts = [db.execute("INSERT INTO departments(name_en,name_ar,created_at) VALUES (?,?,?)", ("Dept %d" % i, "إدارة %d" % i, now)).lastrowid for i in range(50)]
        emps = [db.execute("INSERT INTO employees(emp_no,full_name_en,full_name_ar,department_id,job_title,email,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                           ("E%05d" % i, "Employee %d" % i, "موظف %d" % i, rnd.choice(depts), "Engineer", "e%d@x.test" % i,
                            "active" if rnd.random() > .05 else "left", now, now)).lastrowid for i in range(n_emp)]
        assets = []
        for i in range(n_assets):
            y = rnd.randint(2019, 2026)
            cur = db.execute("INSERT INTO assets(tag,category_id,name,brand,model,serial_no,status,condition,location,purchase_date,purchase_cost,"
                             "warranty_until,custom,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             ("A-%06d" % i, rnd.choice(cats), rnd.choice(["Dell Latitude", "ThinkPad", "iPhone", "Monitor", "Desk"]) + " %d" % i,
                              rnd.choice(["Dell", "Lenovo", "Apple", "HP"]), "M%d" % rnd.randint(1, 99), "SN%07d" % i,
                              "in_stock", rnd.choice(["new", "good", "fair"]), "HQ floor %d" % rnd.randint(1, 9), "%d-%02d-15" % (y, rnd.randint(1, 12)),
                              rnd.randint(100, 5000), "%d-%02d-01" % (y + rnd.randint(1, 4), rnd.randint(1, 12)), '{"ram_gb": 16}', now, now))
            assets.append(cur.lastrowid)
        rnd.shuffle(assets)
        open_n, k = int(n_assets * 0.4), 0
        for aid in assets[:int(n_assets * 0.85)]:
            for j in range(rnd.randint(1, 2)):
                k += 1
                is_open = j == 0 and aid in assets[:open_n]
                db.execute("INSERT INTO assignments(asset_id,employee_id,assigned_at,expected_return,condition_out,returned_at,condition_in,receipt_out_no,receipt_in_no) "
                           "VALUES (?,?,?,?,?,?,?,?,?)", (aid, rnd.choice(emps), "2025-%02d-%02dT09:00:00Z" % (rnd.randint(1, 12), rnd.randint(1, 28)),
                                                          rnd.choice(["", "2026-0%d-01" % rnd.randint(1, 9)]), "good",
                                                          None if is_open else "2025-12-%02dT09:00:00Z" % rnd.randint(1, 28), None if is_open else "good",
                                                          "HO-X-%06d" % k, None if is_open else "RT-X-%06d" % k))
                if is_open:
                    break
        db.execute("UPDATE assets SET status='assigned' WHERE id IN (SELECT asset_id FROM assignments WHERE returned_at IS NULL)")
        for i in range(n_assets // 4):
            db.execute("INSERT INTO maintenance(asset_id,kind,status,title,vendor,cost,scheduled_for,created_at,updated_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (rnd.choice(assets), rnd.choice(["repair", "service"]), rnd.choice(["done", "done", "open", "scheduled"]), "Job %d" % i, "FixIt",
                        rnd.randint(20, 900), "2026-0%d-10" % rnd.randint(1, 9), now, now, now))
        user = {"id": 1, "username": "root"}
        for i in range(int(n_assets * 1.5)):
            audit.write(db, user, rnd.choice(["asset.update", "asset.assign", "auth.login"]), "asset", rnd.choice(assets), {"i": i}, "10.0.0.1")
    db.execute("ANALYZE")
    return time.time() - t0


def timed(c, path, runs):
    times, size = [], 0
    for _ in range(runs):
        h = http.client.HTTPConnection("127.0.0.1", c.env.port, timeout=300)
        t0 = time.perf_counter()
        h.request("GET", path, headers={"Host": "127.0.0.1:%d" % c.env.port, "Cookie": "am_session=" + c.cookie})
        r = h.getresponse()
        body = r.read()
        times.append((time.perf_counter() - t0) * 1000)
        size = len(body)
        h.close()
        if r.status != 200:
            raise SystemExit("%s -> HTTP %d %s" % (path, r.status, body[:200]))
    return statistics.median(times), size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", type=int, default=20000)
    ap.add_argument("--employees", type=int, default=5000)
    ap.add_argument("--runs", type=int, default=5)
    a = ap.parse_args()
    env = Env()
    try:
        do_setup(env)
        c = Client(env)
        c.login("root", SETUP["password"])
        lic, _ = env.issue_license(max_users=50)
        c.post("/api/license/activate", {"license": lic})
        print("Seeding %d assets, %d employees ..." % (a.assets, a.employees), flush=True)
        print("  seeded in %.1f s" % seed(env, a.assets, a.employees))
        paths = ["/api/dashboard", "/api/analytics", "/api/alerts", "/api/assets", "/api/assets?q=dell", "/api/assets?status=assigned&page=40",
                 "/api/assets?category=3", "/api/assets/123", "/api/employees", "/api/employees?q=employee%2012", "/api/employees/50", "/api/assignments",
                 "/api/maintenance", "/api/audit", "/api/audit?q=asset", "/api/categories", "/api/requests",
                 "/api/reports/holdings", "/api/reports/overdue", "/api/reports/warranty?days=365&expired=1", "/api/reports/activity?from=2025-01-01&to=2026-12-31",
                 "/api/reports/value", "/api/reports/maintenance?from=2025-01-01&to=2026-12-31", "/api/system/health"]
        rows = []
        for p in paths:
            ms, size = timed(c, p, a.runs)
            rows.append((ms, p, size))
            print("  %8.1f ms  %7.0f KB  %s" % (ms, size / 1024, p), flush=True)
        for p in ("/api/export/assets", "/api/reports/value?format=xlsx", "/api/system/health?deep=1"):
            ms, size = timed(c, p, 1)
            rows.append((ms, p, size))
            print("  %8.1f ms  %7.0f KB  %s  (single run)" % (ms, size / 1024, p), flush=True)
        t0 = time.perf_counter()
        s, js, _ = c.post("/api/backups")
        print("  %8.1f ms  full backup (%s)" % ((time.perf_counter() - t0) * 1000, js.get("file")))
        slow = [r for r in rows if r[0] > 500 and "export" not in r[1] and "xlsx" not in r[1] and "deep" not in r[1]]
        print("\nSlowest: %s" % ", ".join("%s %.0f ms" % (r[1], r[0]) for r in sorted(rows, reverse=True)[:3]))
        print("Pages over 500 ms: %s" % (", ".join(r[1] for r in slow) if slow else "none"))
    finally:
        env.close()


if __name__ == "__main__":
    main()
