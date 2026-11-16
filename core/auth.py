# -*- coding: utf-8 -*-
"""Login, sessions, lockout and user management rules."""
import time
import threading
from collections import defaultdict, deque

from . import security, rbac, audit
from .errors import ApiError
from .util import now_iso, text, choice, username_ok

MAX_FAILS, LOCK_SECONDS = 5, 15 * 60
IP_WINDOW, IP_MAX = 10 * 60, 30


class IpLimiter:
    def __init__(self):
        self._hits, self._lock = defaultdict(deque), threading.Lock()

    def check(self, ip):
        now = time.time()
        with self._lock:
            q = self._hits[ip]
            while q and now - q[0] > IP_WINDOW:
                q.popleft()
            return len(q) < IP_MAX

    def fail(self, ip):
        with self._lock:
            self._hits[ip].append(time.time())

    def clear(self, ip):
        with self._lock:
            self._hits.pop(ip, None)


class Auth:
    def __init__(self, db, inst):
        self.db, self.inst = db, inst
        self.limiter = IpLimiter()

    # ---------------------------------------------------------------- sessions
    def login(self, username, password, ip="", ua=""):
        username = (username or "").strip().lower()
        if not isinstance(password, str):
            password = ""
        if not self.limiter.check(ip):
            raise ApiError(429, "too_many_attempts", "Too many attempts. Try again later.")
        u = self.db.one("SELECT * FROM users WHERE username=?", (username,))
        now = int(time.time())
        if u is None:
            security.dummy_verify(password)
            self.limiter.fail(ip)
            audit.write(self.db, None, "auth.login_failed", "user", username, {"reason": "unknown_user"}, ip)
            raise ApiError(401, "bad_credentials", "Wrong username or password")
        if u["locked_until"] > now:
            audit.write(self.db, u, "auth.login_blocked", "user", u["id"], {"reason": "locked"}, ip)
            raise ApiError(429, "account_locked", "The account is temporarily locked", retry_after=u["locked_until"] - now)
        if not security.verify_password(password, u["password_hash"]):
            fails = u["failed_count"] + 1
            locked = now + LOCK_SECONDS if fails >= MAX_FAILS else 0
            self.db.execute("UPDATE users SET failed_count=?, locked_until=? WHERE id=?",
                            (0 if locked else fails, locked, u["id"]))
            self.limiter.fail(ip)
            audit.write(self.db, u, "auth.login_failed", "user", u["id"], {"reason": "bad_password", "locked": bool(locked)}, ip)
            raise ApiError(401, "bad_credentials", "Wrong username or password")
        if not u["is_active"]:
            audit.write(self.db, u, "auth.login_blocked", "user", u["id"], {"reason": "inactive"}, ip)
            raise ApiError(403, "account_disabled", "This account is disabled")
        self.limiter.clear(ip)
        token, csrf = security.new_token(), security.new_token()
        abs_h = float(self.inst.config["session_absolute_hours"])
        with self.db.tx():
            self.db.execute("UPDATE users SET failed_count=0, locked_until=0, last_login_at=? WHERE id=?", (now_iso(), u["id"]))
            self.db.execute("INSERT INTO sessions(user_id,token_hash,csrf,created_at,last_seen,expires_at,ip,user_agent) VALUES (?,?,?,?,?,?,?,?)",
                            (u["id"], security.token_hash(token), csrf, now, now, now + int(abs_h * 3600), ip, (ua or "")[:200]))
        audit.write(self.db, u, "auth.login", "user", u["id"], {}, ip)
        return u, token, csrf

    def session(self, token):
        """Return (user_row, session_row) for a valid token, else None. Slides the idle timer."""
        if not token:
            return None
        s = self.db.one("SELECT * FROM sessions WHERE token_hash=? AND revoked=0", (security.token_hash(token),))
        if s is None:
            return None
        now = int(time.time())
        idle = int(self.inst.config["session_idle_minutes"]) * 60
        if now > s["expires_at"] or now - s["last_seen"] > idle:
            self.db.execute("UPDATE sessions SET revoked=1 WHERE id=?", (s["id"],))
            return None
        u = self.db.one("SELECT * FROM users WHERE id=?", (s["user_id"],))
        if u is None or not u["is_active"]:
            return None
        if now - s["last_seen"] >= 30:
            self.db.execute("UPDATE sessions SET last_seen=? WHERE id=?", (now, s["id"]))
        return u, s

    def logout(self, token, user=None, ip=""):
        self.db.execute("UPDATE sessions SET revoked=1 WHERE token_hash=?", (security.token_hash(token or ""),))
        if user:
            audit.write(self.db, user, "auth.logout", "user", user["id"], {}, ip)

    def revoke_user_sessions(self, user_id, except_session_id=None):
        self.db.execute("UPDATE sessions SET revoked=1 WHERE user_id=? AND id IS NOT ?", (user_id, except_session_id))

    # ---------------------------------------------------------------- passwords
    def change_own_password(self, user, session, current, new, ip=""):
        u = self.db.one("SELECT * FROM users WHERE id=?", (user["id"],))
        if not security.verify_password(current or "", u["password_hash"]):
            raise ApiError(403, "wrong_current_password", "The current password is wrong")
        self._set_password(u, new)
        self.db.execute("UPDATE users SET must_change_password=0 WHERE id=?", (u["id"],))
        self.revoke_user_sessions(u["id"], except_session_id=session["id"])
        audit.write(self.db, u, "auth.password_changed", "user", u["id"], {}, ip)

    def _set_password(self, u, new):
        prob = security.password_problem(new or "", u["username"])
        if prob:
            raise ApiError(422, prob, "Password does not meet the policy", field="password")
        if security.verify_password(new, u["password_hash"]):
            raise ApiError(422, "password_same", "Choose a different password", field="password")
        self.db.execute("UPDATE users SET password_hash=?, password_changed_at=? WHERE id=?",
                        (security.hash_password(new), now_iso(), u["id"]))

    # ---------------------------------------------------------------- user management
    def create_user(self, actor, data, license_manager, ip=""):
        username = text(data, "username", maxlen=40).lower()
        if not username_ok(username):
            raise ApiError(422, "username_invalid", "Use 3-40 letters, digits, dot, dash or underscore", field="username")
        full_name = text(data, "full_name", maxlen=120)
        email = text(data, "email", maxlen=160, required=False)
        role_id = data.get("role_id")
        if not isinstance(role_id, int):
            raise ApiError(422, "role_not_found", "Choose a role", field="role_id")
        if actor is not None and not rbac.can_assign_role(self.db, actor, role_id):
            raise ApiError(403, "role_not_allowed", "You cannot assign a role more powerful than your own", field="role_id")
        pw = data.get("password") or security.temp_password()
        generated = not data.get("password")
        prob = security.password_problem(pw, username)
        if prob:
            raise ApiError(422, prob, "Password does not meet the policy", field="password")
        if self.db.one("SELECT 1 FROM users WHERE username=?", (username,)):
            raise ApiError(409, "username_taken", "That username is already used", field="username")
        self._check_user_limit(license_manager, adding=1)
        with self.db.tx():
            cur = self.db.execute(
                "INSERT INTO users(username,full_name,email,role_id,password_hash,must_change_password,is_active,created_at,created_by,password_changed_at) "
                "VALUES (?,?,?,?,?,?,1,?,?,?)",
                (username, full_name, email, role_id, security.hash_password(pw), 1, now_iso(), actor["id"] if actor else None, now_iso()))
        audit.write(self.db, actor, "user.create", "user", cur.lastrowid, {"username": username, "role_id": role_id}, ip)
        return cur.lastrowid, (pw if generated else None)

    def _check_user_limit(self, lm, adding=1):
        if lm is None:
            return
        st = lm.status()
        if st["license"] is None:
            return
        active = self.db.one("SELECT COUNT(*) c FROM users WHERE is_active=1")["c"]
        if active + adding > st["license"]["max_users"]:
            raise ApiError(402, "license_user_limit", "Your licence allows %d active users" % st["license"]["max_users"],
                           limit=st["license"]["max_users"])

    def update_user(self, actor, user_id, data, ip=""):
        u = self.db.one("SELECT * FROM users WHERE id=?", (user_id,))
        if u is None:
            raise ApiError(404, "user_not_found", "User not found")
        self._guard_target(actor, u)
        full_name = text(data, "full_name", maxlen=120)
        email = text(data, "email", maxlen=160, required=False)
        role_id = data.get("role_id", u["role_id"])
        if not isinstance(role_id, int):
            raise ApiError(422, "role_not_found", "Choose a role", field="role_id")
        if role_id != u["role_id"]:
            if u["id"] == actor["id"]:
                raise ApiError(403, "cannot_change_own_role", "You cannot change your own role")
            if not rbac.can_assign_role(self.db, actor, role_id):
                raise ApiError(403, "role_not_allowed", "You cannot assign a role more powerful than your own", field="role_id")
            self._ensure_not_last_super(u, new_role_id=role_id)
        with self.db.tx():
            self.db.execute("UPDATE users SET full_name=?, email=?, role_id=? WHERE id=?", (full_name, email, role_id, user_id))
            if role_id != u["role_id"]:
                self.revoke_user_sessions(user_id)
        audit.write(self.db, actor, "user.update", "user", user_id, {"role_id": role_id}, ip)

    def set_active(self, actor, user_id, active, license_manager, ip=""):
        u = self.db.one("SELECT * FROM users WHERE id=?", (user_id,))
        if u is None:
            raise ApiError(404, "user_not_found", "User not found")
        self._guard_target(actor, u)
        if u["id"] == actor["id"] and not active:
            raise ApiError(403, "cannot_disable_self", "You cannot disable your own account")
        if active and not u["is_active"]:
            self._check_user_limit(license_manager, adding=1)
        if not active:
            self._ensure_not_last_super(u, deactivating=True)
        with self.db.tx():
            self.db.execute("UPDATE users SET is_active=?, failed_count=0, locked_until=0 WHERE id=?", (1 if active else 0, user_id))
            if not active:
                self.revoke_user_sessions(user_id)
        audit.write(self.db, actor, "user.activate" if active else "user.deactivate", "user", user_id, {}, ip)

    def admin_reset_password(self, actor, user_id, ip=""):
        u = self.db.one("SELECT * FROM users WHERE id=?", (user_id,))
        if u is None:
            raise ApiError(404, "user_not_found", "User not found")
        self._guard_target(actor, u)
        pw = security.temp_password()
        with self.db.tx():
            self.db.execute("UPDATE users SET password_hash=?, must_change_password=1, failed_count=0, locked_until=0, password_changed_at=? WHERE id=?",
                            (security.hash_password(pw), now_iso(), user_id))
            self.revoke_user_sessions(user_id)
        audit.write(self.db, actor, "user.reset_password", "user", user_id, {}, ip)
        return pw

    def _guard_target(self, actor, target):
        """Only a Super Administrator may modify another Super Administrator or an equal/stronger account."""
        if rbac.is_super(self.db, actor):
            return
        if not rbac.can_assign_role(self.db, actor, target["role_id"]):
            raise ApiError(403, "user_not_allowed", "You cannot manage this account")

    def _ensure_not_last_super(self, u, new_role_id=None, deactivating=False):
        if not rbac.is_super(self.db, u):
            return
        if new_role_id is not None:
            r = self.db.one("SELECT all_permissions FROM roles WHERE id=?", (new_role_id,))
            if r and r["all_permissions"]:
                return                      # stays a Super Administrator
        elif not deactivating:
            return
        others = self.db.one("SELECT COUNT(*) c FROM users x JOIN roles r ON r.id=x.role_id "
                             "WHERE r.all_permissions=1 AND x.is_active=1 AND x.id<>?", (u["id"],))["c"]
        if others == 0:
            raise ApiError(409, "last_super_admin", "There must always be at least one active Super Administrator")

    def public_user(self, u):
        perms = sorted(rbac.role_permissions(self.db, u["role_id"]))
        r = self.db.one("SELECT key,name_en,name_ar,all_permissions FROM roles WHERE id=?", (u["role_id"],))
        return {"id": u["id"], "username": u["username"], "full_name": u["full_name"], "email": u["email"],
                "role_id": u["role_id"], "role_key": r["key"], "role_name_en": r["name_en"], "role_name_ar": r["name_ar"],
                "is_super": bool(r["all_permissions"]), "must_change_password": bool(u["must_change_password"]),
                "lang": u["lang"], "theme": u["theme"], "permissions": perms}

    def list_users(self):
        out = []
        for u in self.db.query("SELECT u.*, r.name_en role_name_en, r.name_ar role_name_ar, r.key role_key FROM users u JOIN roles r ON r.id=u.role_id ORDER BY u.id"):
            out.append({"id": u["id"], "username": u["username"], "full_name": u["full_name"], "email": u["email"],
                        "role_id": u["role_id"], "role_name_en": u["role_name_en"], "role_name_ar": u["role_name_ar"],
                        "role_key": u["role_key"], "is_active": bool(u["is_active"]), "last_login_at": u["last_login_at"],
                        "locked": u["locked_until"] > time.time(), "created_at": u["created_at"]})
        return out
