# -*- coding: utf-8 -*-
"""Invite a user by e-mail: the administrator chooses the role, the person chooses the password.

Security notes
- The administrator's normal limits apply when inviting and again when the invitation is accepted: no role stronger
  than the inviter's own, the licence user limit, the password policy. An invitation from an account that has since
  been disabled (or lost users.manage) no longer works.
- The link carries a random 256-bit secret in the URL fragment (#/invite?t=...), which browsers never send to the
  server or put in Referer headers. Only its SHA-256 hash is stored. The link works once and expires (1-30 days).
- Public endpoints receive the secret in a POST body (never a query string, so it is not written to access logs) and
  failed lookups are rate limited per IP.
- Sending again creates a new secret, so an older e-mail stops working.
"""
import re
import time
import logging
from email.utils import formataddr

from . import audit, notify, company, rbac, security
from .errors import ApiError
from .transfer import _t
from .util import now_iso, text

log = logging.getLogger("am")

EMAIL_RX = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
ORIGIN_RX = re.compile(r"https?://[A-Za-z0-9.\-\[\]:]{1,200}")
DAYS = (1, 3, 7, 14, 30)
MAX_PENDING = 200


def _email(d):
    email = text(d, "email", maxlen=160).lower()
    if not EMAIL_RX.fullmatch(email):
        raise ApiError(422, "invalid_email", "Enter a valid email address", field="email")
    return email


def _role(db, role_id):
    if not isinstance(role_id, int) or isinstance(role_id, bool):
        raise ApiError(422, "role_not_found", "Choose a role", field="role_id")
    r = db.one("SELECT id, name_en, name_ar FROM roles WHERE id=?", (role_id,))
    if r is None:
        raise ApiError(422, "role_not_found", "Role not found", field="role_id")
    return r


def _base_url(ctx, d):
    """The address people use to open the system: Company settings -> public address, else the address the
    administrator is using right now (sent by their browser, checked to be a plain http(s) origin)."""
    url = notify.get_settings(ctx.db, ctx.app.inst)["public_url"]
    if url:
        return url.rstrip("/")
    origin = (d.get("origin") or "").strip().rstrip("/") if isinstance(d.get("origin"), str) else ""
    return origin if ORIGIN_RX.fullmatch(origin) else ""


def _view(r):
    now = int(time.time())
    status = r["status"]
    if status == "pending" and r["expires_at"] <= now:
        status = "expired"
    return {"id": r["id"], "email": r["email"], "full_name": r["full_name"], "username": r["username"],
            "role_id": r["role_id"], "role_name_en": r["role_name_en"], "role_name_ar": r["role_name_ar"],
            "lang": r["lang"], "status": status, "created_at": r["created_at"],
            "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r["expires_at"])),
            "sent_at": r["sent_at"], "accepted_at": r["accepted_at"], "invited_by": r["invited_by"], "account": r["account"]}


_SELECT = ("SELECT i.*, r.name_en role_name_en, r.name_ar role_name_ar, u.username invited_by, nu.username account "
           "FROM invitations i JOIN roles r ON r.id=i.role_id LEFT JOIN users u ON u.id=i.created_by "
           "LEFT JOIN users nu ON nu.id=i.user_id")


def list_invites(db, view="open"):
    """open = waiting or expired (what still needs attention); all = everything except cancelled, newest first."""
    if view not in ("open", "all"):
        raise ApiError(400, "bad_request", "Bad request")
    where = " WHERE i.status='pending'" if view == "open" else " WHERE i.status<>'revoked'"
    return {"invites": [_view(r) for r in db.query(_SELECT + where + " ORDER BY i.id DESC LIMIT 300")]}


def create(ctx):
    db, d = ctx.db, ctx.json()
    email = _email(d)
    full_name = text(d, "full_name", minlen=2, maxlen=120)
    username = ""                                     # the invited person always chooses their own username
    role = _role(db, d.get("role_id"))
    if not rbac.can_assign_role(db, ctx.user, role["id"]):
        raise ApiError(403, "role_not_allowed", "You cannot assign a role more powerful than your own", field="role_id")
    days = d.get("days", 7)
    if days not in DAYS:
        raise ApiError(422, "invalid_field", "Choose how long the link works", field="days")
    lang = "ar" if d.get("lang") == "ar" else "en"
    base = _base_url(ctx, d)
    with db.tx():
        if db.one("SELECT 1 FROM users WHERE lower(email)=?", (email,)):
            raise ApiError(409, "invite_email_has_account", "Someone already has an account with this email", field="email")
        if db.one("SELECT COUNT(*) c FROM invitations WHERE status='pending'")["c"] >= MAX_PENDING:
            raise ApiError(429, "invites_full", "Too many invitations are waiting")
        db.execute("UPDATE invitations SET status='revoked' WHERE status='pending' AND email=?", (email,))   # one live link per person
        token = security.new_token()
        cur = db.execute("INSERT INTO invitations(email,full_name,username,role_id,lang,token_hash,status,created_by,created_at,expires_at) "
                         "VALUES (?,?,?,?,?,?,'pending',?,?,?)",
                         (email, full_name, username, role["id"], lang, security.token_hash(token), ctx.user["id"], now_iso(),
                          int(time.time()) + days * 86400))
        iid = cur.lastrowid
        ctx.audit("invite.create", "invitation", iid, {"email": email, "role_id": role["id"], "days": days})
    return _deliver(ctx, iid, token, base)


def resend(ctx, iid):
    db, d = ctx.db, ctx.json()
    with db.tx():
        r = db.one("SELECT * FROM invitations WHERE id=?", (iid,))
        if r is None:
            raise ApiError(404, "invite_not_found", "Invitation not found")
        if r["status"] != "pending":
            raise ApiError(409, "invite_closed", "This invitation was already used or cancelled")
        if not rbac.can_assign_role(db, ctx.user, r["role_id"]):
            raise ApiError(403, "role_not_allowed", "You cannot assign a role more powerful than your own")
        days = d.get("days", 7)
        if days not in DAYS:
            days = 7
        token = security.new_token()                  # a new secret: any older link stops working
        db.execute("UPDATE invitations SET token_hash=?, expires_at=? WHERE id=?",
                   (security.token_hash(token), int(time.time()) + days * 86400, iid))
        ctx.audit("invite.resend", "invitation", iid, {"email": r["email"], "days": days})
    return _deliver(ctx, iid, token, _base_url(ctx, d))


def revoke(ctx, iid):
    db = ctx.db
    with db.tx():
        r = db.one("SELECT * FROM invitations WHERE id=?", (iid,))
        if r is None:
            raise ApiError(404, "invite_not_found", "Invitation not found")
        if r["status"] != "pending":
            raise ApiError(409, "invite_closed", "This invitation was already used or cancelled")
        db.execute("UPDATE invitations SET status='revoked' WHERE id=?", (iid,))
        ctx.audit("invite.revoke", "invitation", iid, {"email": r["email"]})
    return {}


def _deliver(ctx, iid, token, base):
    """Return the link to the administrator and, when e-mail is set up, send it. A mail failure never undoes
    the invitation: the administrator can copy the link and send it another way."""
    link = (base or "") + "/#/invite?t=" + token
    out = {"id": iid, "link": link, "has_base": bool(base), "emailed": False, "mail_error": None}
    s = notify.get_settings(ctx.db, ctx.app.inst, reveal=True)
    if not s["email_enabled"] or not s["smtp_host"]:
        out["mail_error"] = "email_off"
        return out
    if not base:
        out["mail_error"] = "no_public_url"
        return out
    r = ctx.db.one(_SELECT + " WHERE i.id=?", (iid,))
    lang = r["lang"]
    c = company.get(ctx.db) or {}
    cname = ((c.get("name_ar") or c.get("name_en")) if lang == "ar" else (c.get("name_en") or c.get("name_ar"))) or ""
    role = (r["role_name_ar"] or r["role_name_en"]) if lang == "ar" else (r["role_name_en"] or r["role_name_ar"])
    fmt = {"name": r["full_name"], "company": cname, "role": role, "inviter": ctx.user["full_name"] or ctx.user["username"],
           "link": link, "expires": time.strftime("%Y-%m-%d", time.localtime(r["expires_at"]))}
    subject = _t(lang, "mail.invite_subject").format(**fmt)
    body = _t(lang, "mail.invite_body").format(**fmt)
    body +="\n\n" + _t(lang, "mail.invite_footer").format(**fmt)
    try:
        notify._smtp_send(s, formataddr((r["full_name"], r["email"])), subject, body, None)
    except Exception as e:
        log.error("Invitation e-mail to %s failed: %s", r["email"], e)
        out["mail_error"] = notify.smtp_error(e).code
        return out
    ctx.db.execute("UPDATE invitations SET sent_at=? WHERE id=?", (now_iso(), iid))
    out["emailed"] = True
    return out


# ------------------------------------------------------------------ public side (the invited person)
def _by_token(ctx, d):
    app = ctx.app
    if not app.invite_limiter.check(ctx.ip):
        raise ApiError(429, "too_many_attempts", "Too many attempts. Try again later.")
    token = d.get("token")
    r = None
    if isinstance(token, str) and 20 <= len(token) <= 100:
        r = ctx.db.one(_SELECT + " WHERE i.token_hash=?", (security.token_hash(token),))
    if r is None or r["status"] == "revoked":
        app.invite_limiter.fail(ctx.ip)
        raise ApiError(404, "invite_invalid", "This invitation link is not valid")
    if r["status"] == "accepted":
        raise ApiError(410, "invite_used", "This invitation was already used")
    if r["expires_at"] <= int(time.time()):
        raise ApiError(410, "invite_expired", "This invitation has expired")
    inviter = ctx.db.one("SELECT * FROM users WHERE id=?", (r["created_by"],))
    if inviter is None or not inviter["is_active"] or not rbac.user_has(ctx.db, inviter, "users.manage") \
            or not rbac.can_assign_role(ctx.db, inviter, r["role_id"]):
        raise ApiError(410, "invite_invalid", "This invitation link is not valid")
    return r, inviter


def check(ctx):
    r, _ = _by_token(ctx, ctx.json())
    c = company.get(ctx.db) or {}
    return {"email": r["email"], "full_name": r["full_name"], "username": r["username"], "lang": r["lang"],
            "role_name_en": r["role_name_en"], "role_name_ar": r["role_name_ar"],
            "company_en": c.get("name_en") or "", "company_ar": c.get("name_ar") or "",
            "suggested": r["username"] or _suggest(ctx.db, r["email"])}


def _suggest(db, email):
    base = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower())[:36] or "user"
    if len(base) < 3:
        base = (base + "user")[:6]
    name, n = base, 2
    while db.one("SELECT 1 FROM users WHERE username=?", (name,)):
        name, n = "%s%d" % (base, n), n + 1
    return name


def accept(ctx):
    db, d = ctx.db, ctx.json()
    with db.tx():
        r, inviter = _by_token(ctx, d)
        username = r["username"] or text(d, "username", maxlen=40).lower()
        full_name = text(d, "full_name", minlen=2, maxlen=120, required=False) or r["full_name"]
        password = d.get("password") if isinstance(d.get("password"), str) else ""
        if not password:
            raise ApiError(422, "field_required", "Choose a password", field="password")
        if db.one("SELECT 1 FROM users WHERE lower(email)=?", (r["email"],)):
            raise ApiError(409, "invite_email_has_account", "Someone already has an account with this email")
        uid, _ = ctx.app.auth.create_user(inviter, {"username": username, "full_name": full_name, "email": r["email"],
                                                    "role_id": r["role_id"], "password": password}, ctx.app.license, ctx.ip)
        db.execute("UPDATE users SET must_change_password=0, lang=? WHERE id=?", (r["lang"], uid))
        db.execute("UPDATE invitations SET status='accepted', accepted_at=?, user_id=? WHERE id=?", (now_iso(), uid, r["id"]))
        audit.write(db, {"id": uid, "username": username}, "invite.accept", "invitation", r["id"],
                    {"user_id": uid, "role_id": r["role_id"], "invited_by": inviter["username"]}, ctx.ip)
    return {"username": username}
