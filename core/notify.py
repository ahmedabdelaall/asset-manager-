# -*- coding: utf-8 -*-
"""Settings, in-app alerts and the daily e-mail digest.

Alerts are computed live from the data (nothing to dismiss: fixing the cause clears the alert) and filtered by the
viewer's permissions. The SMTP password is encrypted with a key derived from the instance secret (never stored plain,
never returned to the browser)."""
import os
import re
import ssl
import time
import json
import base64
import hashlib
import logging
import socket
import smtplib
import datetime
import threading
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import rbac
from .errors import ApiError
from .transfer import _t
from .util import today_iso, text, choice, number

log = logging.getLogger("am")

DEFAULTS = {"alert_warranty_days": 30, "alert_maintenance_days": 7, "public_url": "",
            "email_enabled": False, "smtp_host": "", "smtp_port": 587, "smtp_security": "starttls",
            "smtp_user": "", "smtp_password": "", "smtp_from": "", "digest_hour": 7,
            "access_requests_enabled": True, "access_allowed_domains": []}
SECRET_KEYS = {"smtp_password"}


# ------------------------------------------------------------------ settings
def _key(inst):
    return hashlib.sha256(inst.secret_key + b"|settings-v1").digest()


def _enc(inst, s):
    nonce = os.urandom(12)
    return "enc:" + base64.b64encode(nonce + AESGCM(_key(inst)).encrypt(nonce, s.encode("utf-8"), b"settings")).decode()


def _dec(inst, s):
    if not s.startswith("enc:"):
        return s
    raw = base64.b64decode(s[4:])
    try:
        return AESGCM(_key(inst)).decrypt(raw[:12], raw[12:], b"settings").decode("utf-8")
    except Exception:
        return ""


def get_settings(db, inst, reveal=False):
    out = dict(DEFAULTS)
    for r in db.query("SELECT key, value FROM settings"):
        if r["key"] in DEFAULTS:
            v = json.loads(r["value"])
            out[r["key"]] = _dec(inst, v) if r["key"] in SECRET_KEYS and isinstance(v, str) else v
    if not reveal:
        out["smtp_password_set"] = bool(out["smtp_password"])
        out["smtp_password"] = ""
    return out


def set_value(db, key, val):
    """Store one non-secret setting (used by first-time setup)."""
    if key not in DEFAULTS or key in SECRET_KEYS:
        raise ValueError(key)
    db.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(val)))


def save_settings(ctx, d):
    from . import access                                # access imports this module
    db, inst = ctx.db, ctx.app.inst
    cur = get_settings(db, inst, reveal=True)
    url = text(d, "public_url", maxlen=200, required=False).rstrip("/")
    if url and not (url.startswith("http://") or url.startswith("https://")):
        raise ApiError(422, "invalid_url", "Start the address with http:// or https://", field="public_url")
    v = {"alert_warranty_days": int(number(d, "alert_warranty_days", minimum=1, maximum=365) or 30),
         "alert_maintenance_days": int(number(d, "alert_maintenance_days", minimum=0, maximum=90) or 0),
         "public_url": url, "email_enabled": bool(d.get("email_enabled")),
         "smtp_host": text(d, "smtp_host", maxlen=200, required=False),
         "smtp_port": int(number(d, "smtp_port", minimum=1, maximum=65535) or 587),
         "smtp_security": choice(d, "smtp_security", ("starttls", "ssl", "none"), "starttls"),
         "smtp_user": text(d, "smtp_user", maxlen=200, required=False),
         "smtp_from": text(d, "smtp_from", maxlen=200, required=False),
         "digest_hour": int(number(d, "digest_hour", minimum=0, maximum=23) or 0),
         "access_requests_enabled": bool(d["access_requests_enabled"]) if "access_requests_enabled" in d else bool(cur["access_requests_enabled"]),
         "access_allowed_domains": access.parse_domains(d["access_allowed_domains"]) if "access_allowed_domains" in d else list(cur["access_allowed_domains"] or [])}
    pw = d.get("smtp_password")
    v["smtp_password"] = text(d, "smtp_password", maxlen=300, required=False) if isinstance(pw, str) and pw != "" else cur["smtp_password"]
    if d.get("clear_password"):
        v["smtp_password"] = ""
    if v["email_enabled"] and (not v["smtp_host"] or "@" not in v["smtp_from"]):
        raise ApiError(422, "smtp_incomplete", "Enter the mail server and the sender address", field="smtp_host" if not v["smtp_host"] else "smtp_from")
    with db.tx():
        for k, val in v.items():
            stored = _enc(inst, val) if k in SECRET_KEYS and val else val
            db.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, json.dumps(stored)))
        ctx.audit("settings.update", "settings", "", {k: val for k, val in v.items() if k not in SECRET_KEYS})


def _state(db, key, value=None):
    if value is None:
        r = db.one("SELECT value FROM settings WHERE key=?", ("_" + key,))
        return json.loads(r["value"]) if r else None
    db.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("_" + key, json.dumps(value)))


# ------------------------------------------------------------------ alerts
def _days(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def alerts(db, inst, user, limit=60):
    """Counts are exact; only the first `limit` items of each kind are fetched (a large overdue backlog stays fast)."""
    perms = rbac.role_permissions(db, user["role_id"])
    s = get_settings(db, inst)
    t = today_iso()
    items, counts = [], {}

    def kind(name, where, params, select, make):
        n = db.one("SELECT COUNT(*) c " + where, params)["c"]
        if n:
            counts[name] = n
            items.extend(make(r) for r in db.query(select + " " + where + " LIMIT ?", list(params) + [limit]))

    if "assets.view" in perms:
        kind("overdue", "FROM assignments g JOIN assets a ON a.id=g.asset_id JOIN employees e ON e.id=g.employee_id WHERE g.returned_at IS NULL "
             "AND g.expected_return <> '' AND g.expected_return < ? ORDER BY g.expected_return", (t,),
             "SELECT g.asset_id, a.tag, a.name, e.full_name_en, e.full_name_ar, g.expected_return",
             lambda r: {"kind": "overdue", "severity": "critical", "asset_id": r["asset_id"], "tag": r["tag"], "name": r["name"],
                        "who_en": r["full_name_en"], "who_ar": r["full_name_ar"], "date": r["expected_return"], "days": _days(r["expected_return"], t)})
        until = (datetime.date.fromisoformat(t) + datetime.timedelta(days=s["alert_warranty_days"])).isoformat()
        kind("warranty", "FROM assets WHERE warranty_until <> '' AND warranty_until >= ? AND warranty_until <= ? "
             "AND status NOT IN ('retired','lost') ORDER BY warranty_until", (t, until), "SELECT id, tag, name, warranty_until",
             lambda r: {"kind": "warranty", "severity": "warning", "asset_id": r["id"], "tag": r["tag"], "name": r["name"],
                        "date": r["warranty_until"], "days": _days(t, r["warranty_until"])})
    if "maintenance.view" in perms:
        until = (datetime.date.fromisoformat(t) + datetime.timedelta(days=s["alert_maintenance_days"])).isoformat()
        kind("maintenance", "FROM maintenance m JOIN assets a ON a.id=m.asset_id WHERE m.status='scheduled' AND m.scheduled_for <> '' "
             "AND m.scheduled_for <= ? ORDER BY m.scheduled_for", (until,), "SELECT m.id, m.asset_id, m.title, m.scheduled_for, a.tag, a.name",
             lambda r: {"kind": "maintenance", "severity": "critical" if r["scheduled_for"] < t else "warning", "maintenance_id": r["id"],
                        "asset_id": r["asset_id"], "tag": r["tag"], "name": r["name"], "title": r["title"], "date": r["scheduled_for"],
                        "days": _days(t, r["scheduled_for"])})
    if "requests.approve" in perms:
        kind("request", "FROM asset_requests r JOIN employees e ON e.id=r.employee_id LEFT JOIN categories c ON c.id=r.category_id "
             "WHERE r.status='pending' ORDER BY r.id", (),
             "SELECT r.id, r.requested_at, r.needed_by, e.full_name_en, e.full_name_ar, c.name_en AS cat_en, c.name_ar AS cat_ar",
             lambda r: {"kind": "request", "severity": "info", "request_id": r["id"], "who_en": r["full_name_en"], "who_ar": r["full_name_ar"],
                        "cat_en": r["cat_en"], "cat_ar": r["cat_ar"], "date": r["needed_by"] or r["requested_at"][:10]})
    if "users.manage" in perms:
        kind("access", "FROM access_requests WHERE status='pending' ORDER BY id", (),
             "SELECT id, full_name, created_at",
             lambda r: {"kind": "access", "severity": "info", "access_id": r["id"], "who_en": r["full_name"], "who_ar": r["full_name"],
                        "date": r["created_at"][:10]})
    week_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    kind("decided", "FROM asset_requests r JOIN employees e ON e.id=r.employee_id WHERE r.requested_by=? AND r.status IN ('fulfilled','rejected') "
         "AND r.decided_at >= ? ORDER BY r.decided_at DESC", (user["id"], week_ago),
         "SELECT r.id, r.status, r.decided_at, e.full_name_en, e.full_name_ar",
         lambda r: {"kind": "decided", "severity": "info", "request_id": r["id"], "status": r["status"], "who_en": r["full_name_en"],
                    "who_ar": r["full_name_ar"], "date": r["decided_at"][:10]})
    order = {"critical": 0, "warning": 1, "info": 2}
    items.sort(key=lambda x: (order[x["severity"]], x.get("date") or ""))
    return {"total": sum(counts.values()), "counts": counts, "items": items[:limit]}


# ------------------------------------------------------------------ e-mail
def _smtp_send(s, to, subject, body_text, body_html):
    one_line = lambda x: " ".join(str(x).split())          # headers are always a single line (no header injection)
    subject, to = one_line(subject), one_line(to)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = s["smtp_from"]
    msg["To"] = to
    msg["Message-ID"] = make_msgid()
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")
    ctxs = ssl.create_default_context()
    if s["smtp_security"] == "ssl":
        srv = smtplib.SMTP_SSL(s["smtp_host"], s["smtp_port"], timeout=20, context=ctxs)
    else:
        srv = smtplib.SMTP(s["smtp_host"], s["smtp_port"], timeout=20)
    try:
        if s["smtp_security"] == "starttls":
            srv.starttls(context=ctxs)
        if s["smtp_user"]:
            srv.login(s["smtp_user"], s["smtp_password"])
        srv.send_message(msg)
    finally:
        try:
            srv.quit()
        except Exception:
            pass


def smtp_error(e):
    """Turn a mail-sending exception into an ApiError with a specific, translatable reason."""
    detail = " ".join(str(e).split())[:200]
    if isinstance(e, smtplib.SMTPAuthenticationError):
        code = "smtp_auth"
    elif isinstance(e, smtplib.SMTPSenderRefused) or (
            isinstance(e, smtplib.SMTPResponseException) and e.smtp_code in (550, 553, 554)
            and re.search(r"send(ing)? (e-?mail )?from|sender|not owned|from this domain|relay", detail, re.I)):
        code = "smtp_sender"                            # some servers (e.g. cPanel/Exim) reject the From domain only after DATA
    elif isinstance(e, smtplib.SMTPRecipientsRefused):
        code = "smtp_recipient"
    elif isinstance(e, socket.gaierror):
        code = "smtp_host_unknown"
    elif isinstance(e, (socket.timeout, TimeoutError)):
        code = "smtp_timeout"
    elif isinstance(e, (ssl.SSLError, smtplib.SMTPNotSupportedError)) or "wrong version number" in detail.lower():
        code = "smtp_tls"
    elif isinstance(e, (ConnectionError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected)):
        code = "smtp_connect"
    else:
        code = "smtp_failed"
    return ApiError(502, code, "The mail server refused the message: %s" % detail, detail=detail)


def send_test(ctx, to):
    s = get_settings(ctx.db, ctx.app.inst, reveal=True)
    if not s["smtp_host"] or "@" not in s["smtp_from"]:
        raise ApiError(422, "smtp_incomplete", "Enter the mail server and the sender address")
    to = text({"to": to}, "to", maxlen=200)
    if "@" not in to:
        raise ApiError(422, "invalid_email", "Enter a valid email address", field="to")
    lang = ctx.user["lang"] or "en"
    try:
        _smtp_send(s, to, _t(lang, "mail.test_subject"), _t(lang, "mail.test_body"), None)
    except Exception as e:
        raise smtp_error(e)
    ctx.audit("settings.test_email", "settings", "", {"to": to})


def _line(lang, it):
    who = (it.get("who_ar") or it.get("who_en")) if lang == "ar" else (it.get("who_en") or it.get("who_ar"))
    k = it["kind"]
    if k == "overdue":
        return _t(lang, "alert.overdue").format(tag=it["tag"], name=it["name"], who=who, days=it["days"])
    if k == "warranty":
        return _t(lang, "alert.warranty").format(tag=it["tag"], name=it["name"], days=it["days"])
    if k == "maintenance":
        return _t(lang, "alert.maintenance_late" if it["days"] < 0 else "alert.maintenance").format(tag=it["tag"], title=it["title"], days=abs(it["days"]))
    if k == "request":
        return _t(lang, "alert.request").format(who=who)
    if k == "access":
        return _t(lang, "alert.access").format(who=who)
    return _t(lang, "alert.decided_" + it.get("status", "fulfilled")).format(who=who)


def digest_for(db, inst, user, company_name, base_url):
    lang = user["lang"] or "en"
    a = alerts(db, inst, user, limit=200)
    if not a["total"]:
        return None
    lines = [_line(lang, i) for i in a["items"]]
    subject = _t(lang, "mail.digest_subject").format(n=a["total"], company=company_name)
    link = (base_url + "/#/dashboard") if base_url else ""
    text_body = _t(lang, "mail.digest_intro").format(company=company_name) + "\n\n" + "\n".join("- " + l for l in lines) + ("\n\n" + link if link else "")
    esc = lambda x: x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = ('<div dir="%s" style="font-family:Segoe UI,Tahoma,Arial,sans-serif;font-size:14px;color:#1c1938">'
            '<p>%s</p><ul>%s</ul>%s<p style="color:#7c7a9a;font-size:12px">%s</p></div>') % (
        "rtl" if lang == "ar" else "ltr", esc(_t(lang, "mail.digest_intro").format(company=company_name)),
        "".join("<li style='margin:4px 0'>%s</li>" % esc(l) for l in lines),
        ('<p><a href="%s">%s</a></p>' % (esc(link), esc(_t(lang, "mail.open_app")))) if link else "",
        esc(_t(lang, "mail.footer")))
    return subject, text_body, html


def run_digest(db, inst, force=False):
    """Send each subscribed user their alerts. Returns the number of e-mails sent."""
    from . import company
    s = get_settings(db, inst, reveal=True)
    if not s["email_enabled"] or not s["smtp_host"]:
        return 0
    if not force and _state(db, "digest_last") == today_iso():
        return 0
    c = company.get(db) or {}
    sent = 0
    for u in db.query("SELECT * FROM users WHERE is_active=1 AND email_alerts=1 AND email <> ''"):
        name = (c.get("name_ar") or c.get("name_en")) if (u["lang"] or "en") == "ar" else (c.get("name_en") or c.get("name_ar"))
        d = digest_for(db, inst, u, name or "", s["public_url"])
        if not d:
            continue
        try:
            _smtp_send(s, formataddr((u["full_name"], u["email"])), *d)
            sent += 1
        except Exception as e:
            log.error("Alert e-mail to %s failed: %s", u["username"], e)
    _state(db, "digest_last", today_iso())
    return sent


class DigestScheduler(threading.Thread):
    def __init__(self, db, inst):
        super().__init__(daemon=True)
        self.db, self.inst = db, inst

    def run(self):
        while True:
            try:
                s = get_settings(self.db, self.inst)
                if s["email_enabled"] and time.localtime().tm_hour == s["digest_hour"]:
                    n = run_digest(self.db, self.inst)
                    if n:
                        log.info("Daily alert e-mails sent: %d", n)
            except Exception as e:
                log.error("Alert e-mail scheduler: %s", e)
            finally:
                self.db.close_thread()
            time.sleep(300)
