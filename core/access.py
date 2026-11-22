# -*- coding: utf-8 -*-
"""Request access: a public form on the sign-in page and an administrator approval queue.

Security notes
- Submitting a request never grants anything: an administrator chooses the username and role on approval, and the
  usual rules apply (no role stronger than the administrator's own, licence user limit, password policy).
- The public form does not reveal whether a username or e-mail already exists (no account enumeration): it always
  answers the same way, and the preferred username is only a suggestion checked at approval time.
- Abuse limits: a few submissions per IP per hour, a cap on the number of pending requests, a hidden "honeypot"
  field that bots fill in, and one pending request per e-mail address.
- Allowed domains: each company can limit requests to its own e-mail domains (set during first-time setup and in
  Settings). The list is shown on the public form, so it is not treated as secret.
"""
import re
import logging
from email.utils import formataddr

from . import audit, notify, company
from .errors import ApiError
from .transfer import _t
from .util import now_iso, text, username_ok

log = logging.getLogger("am")

MAX_PENDING = 200
MAX_DOMAINS = 20
EMAIL_RX = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
DOMAIN_RX = re.compile(r"(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})")


def enabled(db, inst):
    return bool(notify.get_settings(db, inst)["access_requests_enabled"])


def parse_domains(value, field="access_allowed_domains"):
    """'acme.com, @ACME.com.eg' or ['acme.com'] -> ['acme.com', 'acme.com.eg'] (lower case, no '@', no duplicates).
    An empty result means any e-mail domain may request access."""
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[\s,;]+", value)
    elif isinstance(value, list) and all(isinstance(x, str) for x in value):
        parts = value
    else:
        raise ApiError(400, "invalid_field", "Invalid value for %s" % field, field=field)
    out = []
    for p in parts:
        p = p.strip().lower().lstrip("@").rstrip(".")
        if not p:
            continue
        if not DOMAIN_RX.fullmatch(p):
            raise ApiError(422, "invalid_domain", "Not a valid domain: %s" % p[:80], field=field, domain=p[:80])
        if p not in out:
            out.append(p)
    if len(out) > MAX_DOMAINS:
        raise ApiError(422, "too_many_domains", "Enter at most %d domains" % MAX_DOMAINS, field=field, max=MAX_DOMAINS)
    return out


def allowed_domains(db, inst):
    return list(notify.get_settings(db, inst).get("access_allowed_domains") or [])


def domain_allowed(email, domains):
    """Exact match on the part after '@' (sub-domains must be listed on their own)."""
    return not domains or email.rsplit("@", 1)[-1] in domains


def submit(ctx):
    db, app = ctx.db, ctx.app
    if not enabled(db, app.inst):
        raise ApiError(403, "access_requests_off", "Access requests are switched off")
    if not app.access_limiter.check(ctx.ip):
        raise ApiError(429, "too_many_attempts", "Too many attempts. Try again later.")
    d = ctx.json()
    if d.get("website"):                              # honeypot: invisible to people, filled in by bots
        app.access_limiter.fail(ctx.ip)
        return
    full_name = text(d, "full_name", minlen=2, maxlen=120)
    email = text(d, "email", maxlen=160).lower()
    if not EMAIL_RX.fullmatch(email):
        raise ApiError(422, "invalid_email", "Enter a valid email address", field="email")
    domains = allowed_domains(db, app.inst)
    if not domain_allowed(email, domains):
        raise ApiError(422, "email_domain_not_allowed", "Use your work e-mail address", field="email",
                       domains=", ".join("@" + x for x in domains))
    username = text(d, "username", maxlen=40, required=False).lower()
    if username and not username_ok(username):
        raise ApiError(422, "username_invalid", "Use 3-40 letters, digits, dot, dash or underscore", field="username")
    row = {"full_name": full_name, "email": email, "username": username,
           "phone": text(d, "phone", maxlen=40, required=False),
           "department": text(d, "department", maxlen=120, required=False),
           "job_title": text(d, "job_title", maxlen=120, required=False),
           "reason": text(d, "reason", maxlen=500, required=False, multiline=True),
           "lang": "ar" if d.get("lang") == "ar" else "en"}
    app.access_limiter.fail(ctx.ip)                   # every valid submission counts towards the hourly limit (typos do not)
    with db.tx():
        if db.one("SELECT 1 FROM access_requests WHERE status='pending' AND email=?", (email,)):
            return                                    # already waiting - same answer, no duplicate
        if db.one("SELECT COUNT(*) c FROM access_requests WHERE status='pending'")["c"] >= MAX_PENDING:
            raise ApiError(429, "access_requests_full", "Too many requests are waiting. Try again later.")
        cur = db.execute("INSERT INTO access_requests(full_name,email,phone,department,job_title,username,reason,lang,status,ip,created_at) "
                         "VALUES (?,?,?,?,?,?,?,?,'pending',?,?)",
                         (row["full_name"], email, row["phone"], row["department"], row["job_title"], username, row["reason"],
                          row["lang"], ctx.ip, now_iso()))
        audit.write(db, None, "access.request", "access_request", cur.lastrowid, {"full_name": full_name, "email": email}, ctx.ip)


def list_requests(db, status="pending"):
    if status not in ("pending", "approved", "rejected", "all"):
        raise ApiError(400, "bad_request", "Bad request")
    where, params = ("", ()) if status == "all" else (" WHERE r.status=?", (status,))
    rows = db.query("SELECT r.id, r.full_name, r.email, r.phone, r.department, r.job_title, r.username, r.reason, r.lang, r.status, "
                    "r.created_at, r.decided_at, r.decision_note, r.user_id, u.username AS decided_by_name, nu.username AS account "
                    "FROM access_requests r LEFT JOIN users u ON u.id=r.decided_by LEFT JOIN users nu ON nu.id=r.user_id"
                    + where + " ORDER BY r.id DESC LIMIT 300", params)
    out = []
    for r in rows:
        x = dict(r)
        x["username_taken"] = bool(x["username"]) and bool(db.one("SELECT 1 FROM users WHERE username=?", (x["username"],)))
        out.append(x)
    pending = db.one("SELECT COUNT(*) c FROM access_requests WHERE status='pending'")["c"]
    return {"requests": out, "pending": pending}


def _pending(db, rid):
    r = db.one("SELECT * FROM access_requests WHERE id=?", (rid,))
    if r is None:
        raise ApiError(404, "access_request_not_found", "Request not found")
    if r["status"] != "pending":
        raise ApiError(409, "access_request_decided", "This request was already decided")
    return r


def approve(ctx, rid):
    db = ctx.db
    d = ctx.json()
    with db.tx():
        r = _pending(db, rid)
        data = {"username": d.get("username") if d.get("username") is not None else r["username"],
                "full_name": d.get("full_name") if d.get("full_name") is not None else r["full_name"],
                "email": d.get("email") if d.get("email") is not None else r["email"],
                "role_id": d.get("role_id")}
        uid, pw = ctx.app.auth.create_user(ctx.user, data, ctx.app.license, ctx.ip)
        db.execute("UPDATE users SET lang=? WHERE id=?", (r["lang"], uid))
        db.execute("UPDATE access_requests SET status='approved', decided_by=?, decided_at=?, user_id=? WHERE id=?",
                   (ctx.user["id"], now_iso(), uid, rid))
        ctx.audit("access.approve", "access_request", rid, {"user_id": uid, "role_id": data["role_id"]})
    u = db.one("SELECT username, full_name, email FROM users WHERE id=?", (uid,))
    emailed = bool(d.get("notify")) and bool(u["email"]) and _mail(ctx, u["email"], u["full_name"], r["lang"], "approved",
                                                                  username=u["username"], password=pw or "")
    return {"user_id": uid, "username": u["username"], "temp_password": pw, "emailed": emailed}


def reject(ctx, rid):
    db = ctx.db
    d = ctx.json()
    note = text(d, "note", maxlen=300, required=False)
    with db.tx():
        r = _pending(db, rid)
        db.execute("UPDATE access_requests SET status='rejected', decided_by=?, decided_at=?, decision_note=? WHERE id=?",
                   (ctx.user["id"], now_iso(), note, rid))
        ctx.audit("access.reject", "access_request", rid, {"note": note})
    emailed = bool(d.get("notify")) and _mail(ctx, r["email"], r["full_name"], r["lang"], "rejected", note=note)
    return {"emailed": emailed}


def _mail(ctx, to, name, lang, kind, **kw):
    """Best effort: the decision is already saved; a mail failure is reported back, never raised."""
    s = notify.get_settings(ctx.db, ctx.app.inst, reveal=True)
    if not s["email_enabled"] or not s["smtp_host"] or not to:
        return False
    c = company.get(ctx.db) or {}
    cname = ((c.get("name_ar") or c.get("name_en")) if lang == "ar" else (c.get("name_en") or c.get("name_ar"))) or ""
    link = s["public_url"] or ""
    fmt = dict(kw, name=name, company=cname, link=link)
    subject = _t(lang, "mail.access_%s_subject" % kind).format(**fmt)
    body = _t(lang, "mail.access_%s_body" % kind).format(**fmt)
    if kind == "rejected" and kw.get("note"):
        body += "\n\n" + _t(lang, "mail.access_note").format(**fmt)
    if link and kind == "approved":
        body += "\n\n" + link
    body += "\n\n" + _t(lang, "mail.footer")
    try:
        notify._smtp_send(s, formataddr((name, to)), subject, body, None)
        return True
    except Exception as e:
        log.error("Access-request e-mail to %s failed: %s", to, e)
        return False
