# -*- coding: utf-8 -*-
"""HTTP server, routing and the JSON API."""
import os
import re
import json
import time
import shutil
import logging
import threading
import traceback
import urllib.parse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import VERSION, audit, rbac, company, licensing, security, backup, access, notify, invites
from . import health as health_checks          # not "health": that name is the /api/health route below
from .auth import Auth
from .backup import BackupScheduler
from .config import Instance
from .db import Database
from .errors import ApiError
from .util import text, choice

log = logging.getLogger("am")
CORE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(CORE, "web")
MIGRATIONS = os.path.join(CORE, "migrations")
COOKIE = "am_session"
MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8", ".ico": "image/x-icon", ".png": "image/png", ".svg": "image/svg+xml"}


class Raw:
    """A non-JSON response. Pass `path` instead of `body` to stream a (possibly large) file from disk."""
    def __init__(self, body, ctype, status=200, headers=None, path=None):
        self.body, self.ctype, self.status, self.headers, self.path = body, ctype, status, headers or {}, path


# ------------------------------------------------------------------ routing
ROUTES = []


def route(method, pattern, perm=None, public=False, csrf=True, lic=True, pw_exempt=False):
    rx = re.compile("^" + re.sub(r"<int:(\w+)>", r"(?P<\1>[0-9]+)", pattern) + "$")

    def deco(fn):
        ROUTES.append({"m": method, "rx": rx, "fn": fn, "perm": perm, "public": public, "csrf": csrf, "lic": lic, "pw": pw_exempt})
        return fn
    return deco


class Ctx:
    def __init__(self, app, h, method, path, query, params, body, user, session, token, ip, ua):
        self.app, self.h, self.method, self.path, self.query, self.params = app, h, method, path, query, params
        self.body, self.user, self.session, self.token, self.ip, self.ua = body, user, session, token, ip, ua
        self.set_cookie, self.clear_cookie = None, False

    @property
    def db(self):
        return self.app.db

    def json(self):
        if not self.body:
            return {}
        try:
            d = json.loads(self.body.decode("utf-8"))
        except Exception:
            raise ApiError(400, "bad_request", "Malformed request")
        if not isinstance(d, dict):
            raise ApiError(400, "bad_request", "Malformed request")
        return d

    def audit(self, action, entity="", entity_id="", detail=None):
        audit.write(self.db, self.user, action, entity, entity_id, detail, self.ip)


def lic_error(e):
    return ApiError(422, e.code, e.message)


# ------------------------------------------------------------------ application
class App:
    def __init__(self, instance_path):
        self.inst = Instance(instance_path)
        self.db = Database(self.inst.db_path, MIGRATIONS, self.inst.backups_dir)
        self.db.migrate()
        self.db.execute("PRAGMA optimize")          # refresh the query planner's statistics where they are stale (cheap)
        rbac.sync(self.db)
        self.auth = Auth(self.db, self.inst)
        self.license = licensing.Manager(self.db, self.inst)
        self.setup_code = None
        self.ensure_setup_code()
        from .auth import IpLimiter
        self.setup_limiter = IpLimiter()
        self.access_limiter = IpLimiter(window=3600, maximum=5)     # public "request access" form: 5 per IP per hour
        self.invite_limiter = IpLimiter(window=600, maximum=20)     # invitation links: 20 wrong links per IP per 10 minutes

    def needs_setup(self):
        return self.db.one("SELECT COUNT(*) c FROM users")["c"] == 0

    def ensure_setup_code(self):
        p = self.inst.setup_code_path
        if self.needs_setup():
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    self.setup_code = f.read().strip()
            else:
                self.setup_code = security.new_token()[:12].upper()
                with open(p, "w", encoding="utf-8") as f:
                    f.write(self.setup_code)
                try:
                    os.chmod(p, 0o600)
                except OSError:
                    pass
        elif os.path.exists(p):
            os.remove(p)

    def loopback_only(self):
        return self.inst.config["host"] in ("127.0.0.1", "localhost", "::1")

    def host_allowed(self, host):
        h = (host or "").lower()
        name = h.rsplit(":", 1)[0].strip("[]") if (h.count(":") == 1 or h.startswith("[")) else h.strip("[]")
        loop = name in ("127.0.0.1", "localhost", "::1")
        allowed = [x.lower() for x in self.inst.config.get("allowed_hosts", [])]
        if allowed:
            return loop or h in allowed or name in allowed     # loopback always works (container health check)
        if self.loopback_only():
            return loop
        return True

    def secure_cookie(self, h):
        if self.inst.config["https"]:
            return True
        return bool(self.inst.config["trust_proxy"] and h.headers.get("X-Forwarded-Proto", "") == "https")


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        import sys
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, TimeoutError)):
            return                      # browser closed the connection - not an error
        log.error("Server error handling %s: %s", client_address, exc)


def make_handler(app):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "AssetMaster"
        timeout = 60          # seconds of silence before an idle/slow connection is dropped (slow-client protection)

        def log_message(self, fmt, *a):
            pass

        # ---- low level
        def _ip(self):
            if app.inst.config["trust_proxy"]:
                xf = self.headers.get("X-Forwarded-For", "")
                if xf:
                    return xf.split(",")[0].strip()
            return self.client_address[0]

        def _send(self, status, body, ctype, headers=None, cookie=None, clear_cookie=False):
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Permissions-Policy", "camera=(self), microphone=(), geolocation=(), payment=(), usb=()")   # camera: QR scanner
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                             "script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
            if app.inst.config["https"]:
                self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            sec = "; Secure" if app.secure_cookie(self) else ""
            if cookie:
                age = int(float(app.inst.config["session_absolute_hours"]) * 3600)
                self.send_header("Set-Cookie", "%s=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=%d%s" % (COOKIE, cookie, age, sec))
            if clear_cookie:
                self.send_header("Set-Cookie", "%s=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0%s" % (COOKIE, sec))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _send_file(self, path, ctype, headers):
            size = os.path.getsize(path)
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            for k, v in headers.items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                with open(path, "rb") as f:
                    shutil.copyfileobj(f, self.wfile, 1 << 20)

        def _json(self, status, data, **kw):
            self._send(status, json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8",
                       headers={"Cache-Control": "no-store"}, **kw)

        def _read_body(self):
            n = int(self.headers.get("Content-Length") or 0)
            limit = int(app.inst.config["max_upload_mb"]) * 1024 * 1024
            if n > limit:
                self.close_connection = True
                raise ApiError(413, "too_large", "The request is too large")
            buf = bytearray()
            while len(buf) < n:
                chunk = self.rfile.read(min(1 << 20, n - len(buf)))
                if not chunk:
                    break
                buf.extend(chunk)
            return bytes(buf)

        # ---- dispatch
        def _handle(self, method):
            try:
                body = self._read_body() if method in ("POST", "PUT", "DELETE") else b""
                if not app.host_allowed(self.headers.get("Host", "")):
                    return self._json(403, {"ok": False, "code": "forbidden", "error": "Forbidden"})
                u = urllib.parse.urlparse(self.path)
                path = u.path
                query = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
                if method == "GET" and not path.startswith("/api/") and not path.startswith("/brand/") \
                        and path != "/manifest.webmanifest" and not path.startswith("/app-icon-"):
                    return self._static(path)
                if method != "GET":
                    origin = self.headers.get("Origin")
                    if origin is not None and urllib.parse.urlparse(origin).netloc.lower() != (self.headers.get("Host") or "").lower():
                        return self._json(403, {"ok": False, "code": "forbidden", "error": "Forbidden"})
                matched, params = None, {}
                allowed_methods = set()
                for r in ROUTES:
                    m = r["rx"].match(path)
                    if m:
                        allowed_methods.add(r["m"])
                        if r["m"] == method:
                            matched, params = r, m.groupdict()
                            break
                if matched is None:
                    raise ApiError(405 if allowed_methods else 404, "not_found", "Not found")
                token = None
                ck = self.headers.get("Cookie")
                if ck:
                    try:
                        c = SimpleCookie()
                        c.load(ck)
                        token = c[COOKIE].value if COOKIE in c else None
                    except Exception:
                        token = None
                user = session = None
                found = app.auth.session(token) if token else None
                if found:
                    user, session = found
                if not matched["public"]:
                    if user is None:
                        raise ApiError(401, "not_authenticated", "Please sign in")
                    if matched["csrf"] and method != "GET":
                        if not security.safe_eq(self.headers.get("X-CSRF-Token", ""), session["csrf"]):
                            raise ApiError(403, "csrf", "Security check failed. Reload the page.")
                    if user["must_change_password"] and not matched["pw"]:
                        raise ApiError(403, "password_change_required", "You must change your password first")
                    perm = matched["perm"]
                    if perm:
                        perms = perm if isinstance(perm, (tuple, list)) else (perm,)
                        if not any(rbac.user_has(app.db, user, p) for p in perms):
                            raise ApiError(403, "forbidden", "You do not have permission")
                if matched["lic"] and app.license.is_locked():
                    st = app.license.status()
                    raise ApiError(402, "license_required", "A valid licence is required", state=st["state"])
                ctx = Ctx(app, self, method, path, query, params, body, user, session, token, self._ip(), self.headers.get("User-Agent", ""))
                result = matched["fn"](ctx)
                if isinstance(result, Raw):
                    if result.path:
                        return self._send_file(result.path, result.ctype, result.headers)
                    return self._send(result.status, result.body, result.ctype, headers=result.headers)
                status = 200
                if isinstance(result, tuple):
                    status, result = result
                if isinstance(result, dict) and "ok" not in result:
                    result = dict(result, ok=True)
                return self._json(status, result, cookie=ctx.set_cookie, clear_cookie=ctx.clear_cookie)
            except ApiError as e:
                return self._json(e.status, e.payload())
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as e:
                log.error("Unhandled error on %s %s: %s\n%s", method, self.path, e, traceback.format_exc())
                try:
                    self._json(500, {"ok": False, "code": "server_error", "error": "Unexpected server error"})
                except Exception:
                    pass
            finally:
                app.db.close_thread()

        def _static(self, path):
            if path in ("", "/"):
                path = "/index.html"
            rel = os.path.normpath(path.lstrip("/"))
            if rel.startswith("static" + os.sep):
                rel = rel[len("static" + os.sep):]
            full = os.path.join(WEB, rel)
            ext = os.path.splitext(full)[1].lower()
            if not os.path.realpath(full).startswith(os.path.realpath(WEB) + os.sep) or ext not in MIME or not os.path.isfile(full):
                return self._send(404, "Not found", "text/plain; charset=utf-8")
            with open(full, "rb") as f:
                return self._send(200, f.read(), MIME[ext], headers={"Cache-Control": "no-cache"})

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_PUT(self):
            self._handle("PUT")

        def do_DELETE(self):
            self._handle("DELETE")

    return H


# ================================================================== API routes
@route("GET", "/api/health", public=True, lic=False)
def health(ctx):
    return {"version": VERSION, "schema": ctx.db.schema_version()}


@route("GET", "/api/branding", public=True, lic=False)
def branding(ctx):
    b = company.branding(ctx.db)
    b["needs_setup"] = ctx.app.needs_setup()
    b["version"] = VERSION
    b["access_requests"] = not b["needs_setup"] and access.enabled(ctx.db, ctx.app.inst)
    if b["access_requests"]:
        b["access_domains"] = access.allowed_domains(ctx.db, ctx.app.inst)
    b["asset_requests"] = bool(notify.get_settings(ctx.db, ctx.app.inst)["asset_requests_enabled"])
    return b


@route("GET", "/manifest.webmanifest", public=True, lic=False)
def web_manifest(ctx):
    """Makes the app installable on phones ("Install app" / "Add to Home screen"), named and coloured per company."""
    b = company.branding(ctx.db)
    lang = b.get("default_language") or "en"
    comp = (b.get("name_ar") if lang == "ar" else b.get("name_en")) or b.get("name_en") or ""
    app_name = (b.get("app_name_ar") if lang == "ar" else b.get("app_name_en")) or "Asset Manager"
    icons = [{"src": "/app-icon-%d.png" % s, "sizes": "%dx%d" % (s, s), "type": "image/png", "purpose": "any"} for s in (192, 512)]
    icons.append({"src": "/app-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"})
    m = {"name": ("%s %s" % (comp, app_name)).strip(), "short_name": (comp or app_name)[:24], "id": "/",
         "start_url": "/#/dashboard", "scope": "/", "display": "standalone", "orientation": "any",
         "lang": lang, "dir": "rtl" if lang == "ar" else "ltr",
         "background_color": "#ffffff", "theme_color": b.get("primary_color") or "#6D4AF2", "icons": icons,
         "shortcuts": [{"name": "Scan" if lang != "ar" else "مسح", "url": "/#/scanner",
                        "icons": [{"src": "/app-icon-192.png", "sizes": "192x192", "type": "image/png"}]}]}
    return Raw(json.dumps(m, ensure_ascii=False).encode("utf-8"), "application/manifest+json; charset=utf-8",
               headers={"Cache-Control": "no-cache"})


@route("GET", "/app-icon-<int:size>.png", public=True, lic=False)
def app_icon(ctx):
    from . import appicon
    size = int(ctx.params["size"])
    if size not in appicon.SIZES:
        raise ApiError(404, "not_found", "No such icon")
    b = company.branding(ctx.db)
    return Raw(appicon.png(size, b.get("primary_color"), b.get("accent_color")), "image/png",
               headers={"Cache-Control": "public, max-age=86400"})


@route("GET", "/brand/logo", public=True, lic=False)
def brand_logo(ctx):
    f = company.logo_file(ctx.db, ctx.app.inst)
    if not f:
        raise ApiError(404, "not_found", "No logo")
    with open(f[0], "rb") as fh:
        return Raw(fh.read(), f[1], headers={"Cache-Control": "public, max-age=3600"})


# ---------------------------------------------------------------- setup
@route("GET", "/api/setup/status", public=True, lic=False)
def setup_status(ctx):
    return {"needs_setup": ctx.app.needs_setup()}


@route("POST", "/api/setup", public=True, csrf=False, lic=False)
def setup(ctx):
    app = ctx.app
    if not app.needs_setup():
        raise ApiError(409, "already_configured", "The system is already set up")
    if not app.setup_limiter.check(ctx.ip):
        raise ApiError(429, "too_many_attempts", "Too many attempts. Try again later.")
    d = ctx.json()
    if not security.safe_eq((d.get("setup_code") or "").strip().upper(), app.setup_code or "-"):
        app.setup_limiter.fail(ctx.ip)
        raise ApiError(403, "bad_setup_code", "The setup code is not correct")
    super_role = ctx.db.one("SELECT id FROM roles WHERE key='super_admin'")
    domains = access.parse_domains(d.get("access_allowed_domains"))
    with ctx.db.tx():
        company.create(ctx.db, d)
        notify.set_value(ctx.db, "access_allowed_domains", domains)
        uid, _ = app.auth.create_user(None, {"username": d.get("username"), "full_name": d.get("full_name"), "email": d.get("email"),
                                             "role_id": super_role["id"], "password": d.get("password") or ""}, None, ctx.ip)
        ctx.db.execute("UPDATE users SET must_change_password=0 WHERE id=?", (uid,))
        audit.write(ctx.db, {"id": uid, "username": (d.get("username") or "").lower()}, "setup.complete", "company", 1, {}, ctx.ip)
    app.ensure_setup_code()
    return {"done": True}


# ---------------------------------------------------------------- auth
def _session_payload(ctx, user, csrf):
    st = ctx.app.license.status()
    return {"user": ctx.app.auth.public_user(user), "csrf": csrf,
            "license": {"state": st["state"], "locked": st["locked"], "days_left": st["days_left"],
                        "expires_at": (st["license"] or {}).get("expires_at"), "disabled": st["state"] == "disabled"}}


@route("POST", "/api/auth/login", public=True, csrf=False, lic=False)
def login(ctx):
    d = ctx.json()
    u, token, csrf = ctx.app.auth.login(d.get("username"), d.get("password"), ctx.ip, ctx.ua)
    if ctx.app.license.is_locked() and not rbac.is_super(ctx.db, u):
        ctx.app.auth.logout(token)
        raise ApiError(403, "license_locked", "The system licence is not active. Contact your administrator.")
    ctx.set_cookie = token
    return _session_payload(ctx, u, csrf)


@route("POST", "/api/auth/logout", lic=False, pw_exempt=True)
def logout(ctx):
    ctx.app.auth.logout(ctx.token, ctx.user, ctx.ip)
    ctx.clear_cookie = True
    return {}


@route("GET", "/api/auth/me", lic=False, pw_exempt=True)
def me(ctx):
    return _session_payload(ctx, ctx.user, ctx.session["csrf"])


@route("POST", "/api/auth/password", lic=False, pw_exempt=True)
def change_password(ctx):
    d = ctx.json()
    ctx.app.auth.change_own_password(ctx.user, ctx.session, d.get("current"), d.get("new"), ctx.ip)
    return {}


@route("PUT", "/api/auth/prefs", lic=False, pw_exempt=True)
def prefs(ctx):
    d = ctx.json()
    lang = choice(d, "lang", ("en", "ar"), ctx.user["lang"] or "en")
    theme = choice(d, "theme", ("light", "dark", "system"), ctx.user["theme"] or "light")
    alerts = (1 if d["email_alerts"] else 0) if isinstance(d.get("email_alerts"), bool) else ctx.user["email_alerts"]
    ctx.db.execute("UPDATE users SET lang=?, theme=?, email_alerts=? WHERE id=?", (lang, theme, alerts, ctx.user["id"]))
    return {}


# ---------------------------------------------------------------- dashboard
@route("GET", "/api/dashboard", perm="dashboard.view")
def dashboard(ctx):
    db = ctx.db
    st = ctx.app.license.status()
    users = db.one("SELECT COUNT(*) total, SUM(is_active) active FROM users")
    last_backup = ([b for b in backup.list_all(ctx.app.inst) if b["kind"] == "full"] or [None])[0]
    out = {"version": VERSION, "schema": db.schema_version(),
           "users": {"total": users["total"], "active": users["active"] or 0},
           "roles": db.one("SELECT COUNT(*) c FROM roles")["c"],
           "license": {"state": st["state"], "days_left": st["days_left"],
                       "expires_at": (st["license"] or {}).get("expires_at"),
                       "max_users": (st["license"] or {}).get("max_users"), "disabled": st["state"] == "disabled"},
           "last_backup": last_backup}
    if rbac.user_has(db, ctx.user, "audit.view"):
        out["recent"] = audit.list_entries(db, 1, 8)["entries"]
    if rbac.user_has(db, ctx.user, "assets.view"):
        from . import inventory
        out["assets"] = inventory.summary(db)
    if rbac.user_has(db, ctx.user, "maintenance.view"):
        out["maintenance"] = {"open": db.one("SELECT COUNT(*) c FROM maintenance WHERE status='open'")["c"],
                              "scheduled": db.one("SELECT COUNT(*) c FROM maintenance WHERE status='scheduled'")["c"]}
    return out


# ---------------------------------------------------------------- users
@route("GET", "/api/users", perm="users.view")
def users_list(ctx):
    return {"users": ctx.app.auth.list_users()}


@route("POST", "/api/users", perm="users.manage")
def users_create(ctx):
    uid, pw = ctx.app.auth.create_user(ctx.user, ctx.json(), ctx.app.license, ctx.ip)
    return 201, {"id": uid, "temp_password": pw}


@route("PUT", "/api/users/<int:id>", perm="users.manage")
def users_update(ctx):
    ctx.app.auth.update_user(ctx.user, int(ctx.params["id"]), ctx.json(), ctx.ip)
    return {}


@route("POST", "/api/users/<int:id>/active", perm="users.manage")
def users_active(ctx):
    d = ctx.json()
    ctx.app.auth.set_active(ctx.user, int(ctx.params["id"]), bool(d.get("active")), ctx.app.license, ctx.ip)
    return {}


@route("POST", "/api/users/<int:id>/reset-password", perm="users.manage")
def users_reset(ctx):
    return {"temp_password": ctx.app.auth.admin_reset_password(ctx.user, int(ctx.params["id"]), ctx.ip)}


# ---------------------------------------------------------------- request access
@route("POST", "/api/access-requests", public=True, csrf=False, lic=False)
def access_submit(ctx):
    if ctx.app.needs_setup():
        raise ApiError(409, "setup_required", "The system is not set up yet")
    access.submit(ctx)
    return 201, {"received": True}         # same answer whether or not the e-mail already has a request or account


@route("GET", "/api/access-requests", perm="users.manage")
def access_list(ctx):
    return access.list_requests(ctx.db, ctx.query.get("status", "pending"))


@route("POST", "/api/access-requests/<int:id>/approve", perm="users.manage")
def access_approve(ctx):
    return access.approve(ctx, int(ctx.params["id"]))


@route("POST", "/api/access-requests/<int:id>/reject", perm="users.manage")
def access_reject(ctx):
    return access.reject(ctx, int(ctx.params["id"]))


# ---------------------------------------------------------------- invitations
@route("GET", "/api/invites", perm="users.manage")
def invites_list(ctx):
    return invites.list_invites(ctx.db, ctx.query.get("view", "open"))


@route("POST", "/api/invites", perm="users.manage")
def invites_create(ctx):
    return 201, invites.create(ctx)


@route("POST", "/api/invites/<int:id>/resend", perm="users.manage")
def invites_resend(ctx):
    return invites.resend(ctx, int(ctx.params["id"]))


@route("POST", "/api/invites/<int:id>/revoke", perm="users.manage")
def invites_revoke(ctx):
    return invites.revoke(ctx, int(ctx.params["id"]))


@route("POST", "/api/invite/check", public=True, csrf=False, lic=False)
def invite_check(ctx):
    return invites.check(ctx)


@route("POST", "/api/invite/accept", public=True, csrf=False, lic=False)
def invite_accept(ctx):
    return invites.accept(ctx)


# ---------------------------------------------------------------- roles
@route("GET", "/api/roles", perm=("roles.view", "users.manage"))
def roles_list(ctx):
    return {"roles": rbac.list_roles(ctx.db)}


@route("GET", "/api/permissions", perm="roles.view")
def permissions(ctx):
    mods = {}
    for code, module in rbac.CATALOG:
        mods.setdefault(module, []).append(code)
    return {"modules": mods, "super_only": sorted(rbac.SUPER_ONLY)}


def _role_perms_from(ctx, d):
    perms = d.get("permissions", [])
    if not isinstance(perms, list):
        raise ApiError(422, "invalid_field", "Invalid permissions", field="permissions")
    valid = {c for c, _ in rbac.CATALOG}
    out = set()
    mine = rbac.role_permissions(ctx.db, ctx.user["role_id"])
    sup = rbac.is_super(ctx.db, ctx.user)
    for p in perms:
        if p not in valid:
            raise ApiError(422, "invalid_field", "Unknown permission", field="permissions")
        if not sup and (p in rbac.SUPER_ONLY or p not in mine):
            raise ApiError(403, "permission_not_allowed", "You cannot grant a permission you do not have", field="permissions")
        out.add(p)
    return out


@route("POST", "/api/roles", perm="roles.manage")
def roles_create(ctx):
    d = ctx.json()
    name_en = text(d, "name_en", maxlen=60)
    name_ar = text(d, "name_ar", maxlen=60, required=False) or name_en
    desc = text(d, "description", maxlen=200, required=False)
    perms = _role_perms_from(ctx, d)
    base = re.sub(r"[^a-z0-9]+", "_", name_en.lower()).strip("_") or "role"
    key, n = "custom_" + base, 1
    while ctx.db.one("SELECT 1 FROM roles WHERE key=?", (key,)):
        n += 1
        key = "custom_%s_%d" % (base, n)
    with ctx.db.tx():
        cur = ctx.db.execute("INSERT INTO roles(key,name_en,name_ar,description,is_system,all_permissions) VALUES (?,?,?,?,0,0)",
                             (key, name_en, name_ar, desc))
        for p in perms:
            ctx.db.execute("INSERT INTO role_permissions(role_id,perm_code) VALUES (?,?)", (cur.lastrowid, p))
    ctx.audit("role.create", "role", cur.lastrowid, {"name": name_en, "permissions": sorted(perms)})
    return 201, {"id": cur.lastrowid}


@route("PUT", "/api/roles/<int:id>", perm="roles.manage")
def roles_update(ctx):
    rid = int(ctx.params["id"])
    r = ctx.db.one("SELECT * FROM roles WHERE id=?", (rid,))
    if r is None:
        raise ApiError(404, "role_not_found", "Role not found")
    d = ctx.json()
    sup = rbac.is_super(ctx.db, ctx.user)
    if r["all_permissions"]:
        raise ApiError(403, "role_locked", "The Super Administrator role cannot be changed")
    if r["key"] == "company_admin" and not sup:
        raise ApiError(403, "role_locked", "Only a Super Administrator can change this role")
    if rid == ctx.user["role_id"] and not sup:
        raise ApiError(403, "cannot_edit_own_role", "You cannot change the permissions of your own role")
    perms = _role_perms_from(ctx, d)
    if not sup:       # keep super-only permissions untouched
        perms |= {p for p in rbac.role_permissions(ctx.db, rid) if p in rbac.SUPER_ONLY}
    with ctx.db.tx():
        if not r["is_system"]:
            ctx.db.execute("UPDATE roles SET name_en=?, name_ar=?, description=? WHERE id=?",
                           (text(d, "name_en", maxlen=60), text(d, "name_ar", maxlen=60, required=False) or text(d, "name_en", maxlen=60),
                            text(d, "description", maxlen=200, required=False), rid))
        ctx.db.execute("DELETE FROM role_permissions WHERE role_id=?", (rid,))
        for p in perms:
            ctx.db.execute("INSERT INTO role_permissions(role_id,perm_code) VALUES (?,?)", (rid, p))
    ctx.audit("role.update", "role", rid, {"permissions": sorted(perms)})
    return {}


@route("DELETE", "/api/roles/<int:id>", perm="roles.manage")
def roles_delete(ctx):
    rid = int(ctx.params["id"])
    r = ctx.db.one("SELECT * FROM roles WHERE id=?", (rid,))
    if r is None:
        raise ApiError(404, "role_not_found", "Role not found")
    if r["is_system"]:
        raise ApiError(403, "role_locked", "Built-in roles cannot be deleted")
    if ctx.db.one("SELECT 1 FROM users WHERE role_id=?", (rid,)):
        raise ApiError(409, "role_in_use", "Move the users of this role to another role first")
    ctx.db.execute("DELETE FROM roles WHERE id=?", (rid,))
    ctx.audit("role.delete", "role", rid, {"name": r["name_en"]})
    return {}


# ---------------------------------------------------------------- company & branding
@route("GET", "/api/company", perm="company.view")
def company_get(ctx):
    c = company.get(ctx.db)
    c["logo"] = company.branding(ctx.db)["logo"]
    return c


@route("PUT", "/api/company", perm="company.manage")
def company_put(ctx):
    v = company.update(ctx.db, ctx.json())
    ctx.audit("company.update", "company", 1, v)
    return {}


@route("POST", "/api/company/logo", perm="company.manage")
def company_logo(ctx):
    company.set_logo(ctx.db, ctx.app.inst, ctx.body)
    ctx.audit("company.logo_set", "company", 1)
    return {"logo": company.branding(ctx.db)["logo"]}


@route("DELETE", "/api/company/logo", perm="company.manage")
def company_logo_del(ctx):
    company.remove_logo(ctx.db, ctx.app.inst)
    ctx.audit("company.logo_removed", "company", 1)
    return {}


# ---------------------------------------------------------------- licence
@route("GET", "/api/license", perm="license.view", lic=False)
def license_get(ctx):
    st = ctx.app.license.status()
    c = company.get(ctx.db)
    out = dict(st)
    out["request_code"] = licensing.activation_request(ctx.db, ctx.app.inst, (c or {}).get("name_en", ""))
    out["active_users"] = ctx.db.one("SELECT COUNT(*) c FROM users WHERE is_active=1")["c"]
    return out


def _license_on(ctx):
    if not licensing.enabled(ctx.app.inst):
        raise ApiError(409, "license_disabled", "Licensing is switched off on this server")


@route("POST", "/api/license/activate", perm="license.manage", lic=False)
def license_activate(ctx):
    _license_on(ctx)
    d = ctx.json()
    try:
        payload = licensing.activate(ctx.db, ctx.app.inst, ctx.app.license, d.get("license") or "", ctx.user["username"])
    except licensing.LicenseError as e:
        ctx.audit("license.activate_rejected", "license", "", {"code": e.code})
        raise lic_error(e)
    ctx.audit("license.activate", "license", payload["license_id"], {"company": payload["company"], "expires_at": payload.get("expires_at")})
    return {"state": ctx.app.license.status()["state"]}


@route("POST", "/api/license/revocations", perm="license.manage", lic=False)
def license_revocations(ctx):
    _license_on(ctx)
    try:
        p = licensing.apply_revocations(ctx.db, ctx.app.inst, ctx.app.license, ctx.json().get("list") or "", ctx.user["username"])
    except licensing.LicenseError as e:
        raise lic_error(e)
    ctx.audit("license.revocations", "license", "", {"serial": p["serial"]})
    return {"state": ctx.app.license.status()["state"]}


@route("GET", "/api/license/events", perm="license.view", lic=False)
def license_events(ctx):
    return {"events": licensing.events(ctx.db)}


# ---------------------------------------------------------------- audit & backups
@route("GET", "/api/audit", perm="audit.view")
def audit_list(ctx):
    q = ctx.query
    try:
        page, per = int(q.get("page", 1)), int(q.get("per_page", 50))
    except ValueError:
        raise ApiError(400, "bad_request", "Bad request")
    return audit.list_entries(ctx.db, page, per, q.get("user", ""), q.get("action", ""), q.get("q", ""))


@route("POST", "/api/audit/verify", perm="audit.verify")
def audit_verify(ctx):
    r = audit.verify_chain(ctx.db)
    ctx.audit("audit.verify", "audit", "", r)
    return r


@route("GET", "/api/backups", perm="backup.view")
def backups_list(ctx):
    return {"backups": backup.list_all(ctx.app.inst), "dir": ctx.app.inst.backups_dir, "keep": ctx.app.inst.config["backup_keep"]}


@route("POST", "/api/backups", perm="backup.manage")
def backups_create(ctx):
    p = backup.full_backup(ctx.db, ctx.app.inst, "manual")
    backup.prune(ctx.app.inst, int(ctx.app.inst.config["backup_keep"]))
    ctx.audit("backup.create", "backup", os.path.basename(p), {"size": os.path.getsize(p)})
    return {"file": os.path.basename(p)}


def _backup_path(ctx):
    try:
        return backup.path_of(ctx.app.inst, ctx.params["name"])
    except backup.BackupError:
        raise ApiError(404, "backup_not_found", "Backup not found")


@route("POST", r"/api/backups/(?P<name>[A-Za-z0-9_.\-]+)/verify", perm="backup.manage")
def backups_verify(ctx):
    r = backup.verify(_backup_path(ctx))
    ctx.audit("backup.verify", "backup", ctx.params["name"], {"ok": r["ok"], "problems": r["problems"][:5]})
    return {"result": r}


@route("GET", r"/api/backups/(?P<name>[A-Za-z0-9_.\-]+)/download", perm="backup.manage")
def backups_download(ctx):
    p = _backup_path(ctx)
    ctx.audit("backup.download", "backup", ctx.params["name"], {"size": os.path.getsize(p)})
    ctype = "application/zip" if p.endswith(".zip") else "application/octet-stream"
    return Raw(None, ctype, path=p, headers={"Content-Disposition": 'attachment; filename="%s"' % ctx.params["name"], "Cache-Control": "no-store"})


@route("GET", "/api/system/health", perm="backup.view")
def system_health(ctx):
    return health_checks.run(ctx.db, ctx.app.inst, MIGRATIONS, deep=ctx.query.get("deep") == "1")


from . import api_inventory  # noqa: E402,F401  (registers the Phase 2 routes)


# ================================================================== run
def serve(instance_path):
    import sys
    import signal
    app = App(instance_path)
    fmt = "%(asctime)s %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=[
        logging.FileHandler(os.path.join(app.inst.path, "logs", "server.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)])
    cfg = app.inst.config
    httpd = Server((cfg["host"], int(cfg["port"])), make_handler(app))
    BackupScheduler(app.db, app.inst).start()
    from .notify import DigestScheduler
    DigestScheduler(app.db, app.inst).start()
    if not licensing.enabled(app.inst):
        print("Licensing is switched off (AM_LICENSE=off): no licence needed, no user limit.", flush=True)
    elif cfg.get("license_server_url"):
        def loop():
            while True:
                licensing.refresh_online(app.db, app.inst, app.license)
                time.sleep(12 * 3600)
        threading.Thread(target=loop, daemon=True).start()
    print("Asset Master %s listening on http://%s:%s" % (VERSION, cfg["host"], cfg["port"]), flush=True)
    if app.needs_setup():
        print("FIRST-TIME SETUP: open the address above and enter this setup code: %s" % app.setup_code, flush=True)
        print("(also saved in %s)" % app.inst.setup_code_path, flush=True)
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, lambda *a: threading.Thread(target=httpd.shutdown, daemon=True).start())
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
