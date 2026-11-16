import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import Env
from playwright.sync_api import sync_playwright

env = Env()
base = "http://127.0.0.1:%d/" % env.port
errs = []
OUT = "/tmp/ui_am"; os.makedirs(OUT, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}); pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append("PAGEERR " + str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "status of 4" not in m.text and "status of 5" not in m.text else None)
    pg.goto(base); pg.wait_for_selector("#sf")
    pg.screenshot(path=OUT + "/01_setup.png")
    pg.fill("#f-setup_code", env.app.setup_code); pg.fill("#f-name_en", "Acme Corp"); pg.fill("#f-name_ar", "شركة أكمي")
    pg.fill("#f-full_name", "Root Admin"); pg.fill("#f-username", "root"); pg.fill("#f-email", "root@acme.test")
    pg.fill("#f-password", "Sup3r-Secret-Pass"); pg.fill("#f-password2", "Sup3r-Secret-Pass")
    pg.click("#sbtn"); pg.wait_for_selector("#rq", timeout=8000)
    print("after setup url:", pg.url.split("#")[1], "| sidebar items:", pg.locator(".nav a").count())
    pg.screenshot(path=OUT + "/02_license_locked.png")
    lic, _ = env.issue_license(max_users=20)
    pg.fill("#lt", lic); pg.click("#lact"); pg.wait_for_selector(".nav a:nth-child(4)", timeout=8000)
    pg.goto(base + "#/dashboard"); pg.wait_for_selector(".kpi"); pg.wait_for_timeout(500)
    pg.screenshot(path=OUT + "/03_dashboard.png")
    # users: create one
    pg.goto(base + "#/users"); pg.wait_for_selector("#addu"); pg.click("#addu"); pg.wait_for_selector("#uf")
    pg.fill("#f-username", "sara"); pg.fill("#f-full_name", "Sara Ali"); pg.fill("#f-email", "sara@acme.test")
    pg.select_option("#f-role_id", label="Viewer"); pg.click("#uf button[type=submit]")
    pg.wait_for_selector("#sec"); temp = pg.inner_text("#sec"); pg.screenshot(path=OUT + "/04_tempbox.png"); pg.click("#ok")
    pg.wait_for_selector("#utbl tbody tr"); pg.wait_for_timeout(300); pg.screenshot(path=OUT + "/05_users.png")
    print("users rows:", pg.locator("#utbl tbody tr").count(), "temp pw len:", len(temp))
    # validation error shown inline
    pg.click("#addu"); pg.wait_for_selector("#uf"); pg.fill("#f-username", "x"); pg.fill("#f-full_name", "X"); pg.click("#uf button[type=submit]"); pg.wait_for_selector(".fld.err")
    print("inline error:", pg.inner_text(".fld.err .em")); pg.keyboard.press("Escape")
    # roles
    pg.goto(base + "#/roles"); pg.wait_for_selector(".role"); pg.locator(".role").nth(1).click(); pg.wait_for_selector("[data-p]"); pg.screenshot(path=OUT + "/06_roles.png")
    # company: colours + logo
    pg.goto(base + "#/company"); pg.wait_for_selector("#cf")
    pg.fill("#f-primary_color", "#0E8A6B"); pg.fill("#f-accent_color", "#1F5FBF")
    from PIL import Image; Image.new("RGB", (200, 200), "#0E8A6B").save("/tmp/logo.png")
    pg.set_input_files("#logo", "/tmp/logo.png"); pg.wait_for_selector(".side .logo img", timeout=8000)
    pg.click("#cf button[type=submit]"); pg.wait_for_timeout(900); pg.screenshot(path=OUT + "/07_company.png")
    print("brand primary applied:", pg.locator("html").get_attribute("style"))
    pg.goto(base + "#/license"); pg.wait_for_selector("#rq"); pg.screenshot(path=OUT + "/08_license.png", full_page=True)
    pg.goto(base + "#/audit"); pg.wait_for_selector("#atbl tbody tr"); pg.click("#verify"); pg.wait_for_selector(".toast"); pg.screenshot(path=OUT + "/09_audit.png")
    pg.goto(base + "#/backups"); pg.wait_for_selector("#bk"); pg.click("#bk"); pg.wait_for_selector("#page .tbl"); pg.screenshot(path=OUT + "/10_backups.png")
    # Arabic / RTL
    pg.goto(base + "#/account"); pg.wait_for_selector("#sl"); pg.click("#sl button[data-l=ar]"); pg.wait_for_timeout(500)
    print("dir:", pg.locator("html").get_attribute("dir"), "lang:", pg.locator("html").get_attribute("lang"))
    for name, h in (("11_ar_dashboard", "dashboard"), ("12_ar_users", "users"), ("13_ar_roles", "roles"), ("14_ar_license", "license")):
        pg.goto(base + "#/" + h); pg.wait_for_timeout(900); pg.screenshot(path=OUT + "/%s.png" % name)
    # dark mode
    pg.goto(base + "#/account"); pg.wait_for_selector("#st"); pg.click("#st button[data-t=dark]"); pg.wait_for_timeout(300)
    pg.goto(base + "#/dashboard"); pg.wait_for_selector(".kpi"); pg.wait_for_timeout(500); pg.screenshot(path=OUT + "/15_ar_dark_dashboard.png")
    # persists across reload (stored in user profile)
    pg.reload(); pg.wait_for_selector(".kpi"); print("after reload dir:", pg.locator("html").get_attribute("dir"), "theme:", pg.locator("html").get_attribute("data-theme"))
    # logout and sign in as the new user: forced password change
    pg.click("#t-user"); pg.click("#m-out"); pg.wait_for_selector("#lf")
    pg.fill("#f-username", "sara"); pg.fill("#f-password", temp); pg.click("#lbtn"); pg.wait_for_selector("#pf")
    print("forced change screen:", pg.inner_text("h1"))
    pg.fill("#f-current", temp); pg.fill("#f-new", "Brand-New-Pass-77"); pg.fill("#f-new2", "Brand-New-Pass-77"); pg.click("#pbtn")
    pg.wait_for_selector(".kpi"); print("viewer nav items:", pg.locator(".nav a").all_inner_texts())
    pg.goto(base + "#/users"); pg.wait_for_timeout(700); print("viewer on users page:", pg.inner_text("#page")[:60].replace("\n", " "))
    print("JS errors:", errs)
    b.close()
env.close()
