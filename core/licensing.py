# -*- coding: utf-8 -*-
"""Licensing: signed licence files bound to one deployment (server).

How it works (plain language)
  * The vendor holds a PRIVATE key that never leaves the vendor. Licences are signed with it.
  * This product contains only the matching PUBLIC key, which can check a signature but cannot create one.
  * A licence names the company, the deployment id (derived from the server and this installation),
    an expiry date, a user limit and optional features.
  * The server checks all of this on the server side on every request. Copying the program files to another
    computer is not enough: there is no licence, no database and no secrets there; copying the whole
    instance folder to another computer fails the deployment-id check.

Limits (honest): somebody with full control of the server AND the source code can always try to patch the checks
out. This design raises the cost, keeps honest customers honest, and gives you revocation, expiry and an audit trail.
"""
import os
import json
import time
import uuid
import base64
import hashlib
import datetime
import threading
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from . import VERSION, PRODUCT
from .errors import ApiError
from .util import now_iso, parse_iso
from . import security

KEY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys")
CLOCK_TOLERANCE = 3600  # seconds the clock may jump backwards (NTP corrections, etc.)
OK_STATES = ("valid", "grace")


class LicenseError(Exception):
    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code, self.message = code, message or code


# ------------------------------------------------------------------ helpers
def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def machine_id(inst=None):
    """The server's identity. Containers have no stable OS machine id and get a random network address each time
    they are recreated, so in that case the fallback value is stored once in the instance folder and reused -
    otherwise every image rebuild would change the deployment ID and lock the licence."""
    env = os.environ.get("AM_MACHINE_ID", "").strip()
    if env:
        return env
    v = _os_machine_id()
    if v:
        return v
    if inst is None:
        return "node-%012x" % uuid.getnode()
    p = os.path.join(inst.path, "machine_id")
    try:
        with open(p, "r", encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    except OSError:
        pass
    v = "node-%012x" % uuid.getnode()      # same value as before this file existed, so current licences stay valid
    with open(p, "w", encoding="utf-8") as f:
        f.write(v)
    return v


def _os_machine_id():
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                v = f.read().strip()
                if v:
                    return v
        except OSError:
            pass
    try:
        import winreg  # Windows
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            return str(winreg.QueryValueEx(k, "MachineGuid")[0])
    except Exception:
        pass
    return None


def deployment_id(inst):
    return hashlib.sha256(("%s|%s" % (machine_id(inst), inst.install_id)).encode("utf-8")).hexdigest()[:32]


def load_public_key(inst):
    path = inst.config.get("public_key_path") or os.path.join(KEY_DIR, "vendor_public.pem")
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def verify_envelope(envelope, pub):
    if not isinstance(envelope, dict) or "payload" not in envelope or "signature" not in envelope:
        raise LicenseError("license_format", "Not a licence file")
    try:
        sig = base64.b64decode(envelope["signature"], validate=True)
        pub.verify(sig, canonical(envelope["payload"]))
    except (InvalidSignature, ValueError, TypeError):
        raise LicenseError("license_signature", "The licence signature is not valid")
    return envelope["payload"]


def parse_text(text):
    try:
        env = json.loads(text)
    except Exception:
        raise LicenseError("license_format", "Not a licence file")
    if not isinstance(env, dict):
        raise LicenseError("license_format", "Not a licence file")
    return env


def _expiry_dt(payload):
    e = payload.get("expires_at")
    if not e:
        return None
    try:
        d = datetime.datetime.strptime(e, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    except Exception:
        raise LicenseError("license_format", "Invalid expiry date")
    return d + datetime.timedelta(days=1)   # valid through the whole expiry day


def _check_payload(payload):
    if payload.get("product") != PRODUCT:
        raise LicenseError("license_product", "This licence is for a different product")
    for k in ("license_id", "company", "deployment_id", "issued_at", "max_users"):
        if k not in payload:
            raise LicenseError("license_format", "Missing field: " + k)
    if not isinstance(payload["max_users"], int) or payload["max_users"] < 1:
        raise LicenseError("license_format", "Invalid user limit")
    _expiry_dt(payload)


def log_event(db, event, detail=None):
    db.execute("INSERT INTO license_events(ts,event,detail) VALUES (?,?,?)",
               (now_iso(), event, json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)))


# ------------------------------------------------------------------ clock protection
def _clock_value(db, inst):
    r = db.one("SELECT value, mac FROM system_state WHERE key='last_seen'")
    if r is None:
        return None, True
    ok = security.safe_eq(security.mac(inst.secret_key, "last_seen:" + r["value"]), r["mac"])
    try:
        return int(r["value"]), ok
    except ValueError:
        return None, False


def clock_check(db, inst, now=None, record=True):
    """Returns True when the server clock looks sane. Also records the latest time seen."""
    now = int(now if now is not None else time.time())
    last, mac_ok = _clock_value(db, inst)
    if last is not None and not mac_ok:
        return False
    if last is not None and now < last - CLOCK_TOLERANCE:
        return False
    if record and (last is None or now - last >= 60):
        v = str(max(now, last or 0))
        db.execute("INSERT INTO system_state(key,value,mac) VALUES ('last_seen',?,?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value, mac=excluded.mac",
                   (v, security.mac(inst.secret_key, "last_seen:" + v)))
    return True


# ------------------------------------------------------------------ status
def revoked_ids(db, inst, pub):
    r = db.one("SELECT envelope FROM license_revocations WHERE id=1")
    if r is None:
        return set()
    try:
        return set(verify_envelope(json.loads(r["envelope"]), pub)["revoked"])
    except Exception:
        return set()


def enabled(inst):
    """Licensing can be switched off per deployment (config "license_enabled": false or AM_LICENSE=off), e.g. for a
    company running its own copy. The code stays in place so it can be switched back on with one setting."""
    return bool(inst.config.get("license_enabled", True))


def compute_status(db, inst, now=None):
    now_ts = int(now if now is not None else time.time())
    dep = deployment_id(inst)
    base = {"state": "missing", "locked": True, "deployment_id": dep, "license": None, "days_left": None, "grace_until": None}
    if not enabled(inst):
        return dict(base, state="disabled", locked=False, disabled=True)      # license None -> no user limit
    pub = load_public_key(inst)
    if pub is None:
        return dict(base, state="no_key")
    row = db.one("SELECT envelope, activated_at, activated_by FROM license_store WHERE id=1")
    if row is None:
        return base
    try:
        payload = verify_envelope(json.loads(row["envelope"]), pub)
        _check_payload(payload)
    except (LicenseError, ValueError):
        return dict(base, state="invalid")
    info = {"license_id": payload["license_id"], "company": payload["company"], "issued_at": payload["issued_at"],
            "expires_at": payload.get("expires_at"), "grace_days": int(payload.get("grace_days", 0)),
            "max_users": payload["max_users"], "features": payload.get("features", []),
            "edition": payload.get("edition", ""), "activated_at": row["activated_at"]}
    base["license"] = info
    if payload["deployment_id"] != dep:
        return dict(base, state="mismatch")
    if payload["license_id"] in revoked_ids(db, inst, pub):
        return dict(base, state="revoked")
    if not clock_check(db, inst, now_ts, record=(now is None)):
        return dict(base, state="clock")
    exp = _expiry_dt(payload)
    if exp is None:
        return dict(base, state="valid", locked=False)
    left = exp.timestamp() - now_ts
    days_left = int(left // 86400) if left > 0 else -int((-left) // 86400) - 1
    base["days_left"] = days_left
    if left > 0:
        return dict(base, state="valid", locked=False)
    grace_end = exp + datetime.timedelta(days=info["grace_days"])
    base["grace_until"] = grace_end.strftime("%Y-%m-%d")
    if now_ts < grace_end.timestamp():
        return dict(base, state="grace", locked=False)
    return dict(base, state="expired")


class Manager:
    """Caches the status for a few seconds and records state changes."""
    def __init__(self, db, inst, ttl=15):
        self.db, self.inst, self.ttl = db, inst, ttl
        self._cache, self._at, self._lock = None, 0, threading.Lock()
        self._last_logged = None

    def invalidate(self):
        with self._lock:
            self._cache = None

    def status(self):
        with self._lock:
            if self._cache is not None and time.time() - self._at < self.ttl:
                return self._cache
        st = compute_status(self.db, self.inst)
        with self._lock:
            self._cache, self._at = st, time.time()
            if st["state"] != self._last_logged:
                if self._last_logged is not None or st["state"] not in ("valid", "missing"):
                    try:
                        log_event(self.db, "state_" + st["state"], {"license_id": (st["license"] or {}).get("license_id")})
                    except Exception:
                        pass
                self._last_logged = st["state"]
        return st

    def is_locked(self):
        return self.status()["locked"]

    def has_feature(self, name):
        s = self.status()
        if s["state"] == "disabled":
            return True
        return (not s["locked"]) and s["license"] is not None and name in s["license"]["features"]

    def max_users(self):
        s = self.status()
        return s["license"]["max_users"] if s["license"] else 0


# ------------------------------------------------------------------ activation / renewal
def activation_request(db, inst, company_name):
    req = {"v": 1, "product": PRODUCT, "company": company_name, "deployment_id": deployment_id(inst),
           "app_version": VERSION, "created": now_iso(), "nonce": uuid.uuid4().hex[:8]}
    return base64.urlsafe_b64encode(json.dumps(req, sort_keys=True, ensure_ascii=False).encode("utf-8")).decode("ascii")


def activate(db, inst, manager, text, actor_name=""):
    pub = load_public_key(inst)
    if pub is None:
        raise LicenseError("license_no_key", "This build has no vendor key, so licences cannot be verified")
    env = parse_text(text)
    payload = verify_envelope(env, pub)
    _check_payload(payload)
    if payload["deployment_id"] != deployment_id(inst):
        log_event(db, "rejected_wrong_deployment", {"license_id": payload["license_id"]})
        raise LicenseError("license_mismatch", "This licence was issued for a different server")
    if payload["license_id"] in revoked_ids(db, inst, pub):
        log_event(db, "rejected_revoked", {"license_id": payload["license_id"]})
        raise LicenseError("license_revoked", "This licence has been revoked")
    exp = _expiry_dt(payload)
    if exp is not None:
        grace = datetime.timedelta(days=int(payload.get("grace_days", 0)))
        if time.time() >= (exp + grace).timestamp():
            log_event(db, "rejected_expired", {"license_id": payload["license_id"]})
            raise LicenseError("license_expired", "This licence has already expired")
    active = db.one("SELECT COUNT(*) c FROM users WHERE is_active=1")["c"]
    if active > payload["max_users"]:
        raise LicenseError("license_users_exceeded",
                           "The licence allows %d users but %d are active" % (payload["max_users"], active))
    prev = db.one("SELECT license_id FROM license_store WHERE id=1")
    with db.tx():
        db.execute("INSERT INTO license_store(id,envelope,license_id,activated_at,activated_by) VALUES (1,?,?,?,?) "
                   "ON CONFLICT(id) DO UPDATE SET envelope=excluded.envelope, license_id=excluded.license_id, "
                   "activated_at=excluded.activated_at, activated_by=excluded.activated_by",
                   (json.dumps(env, sort_keys=True, ensure_ascii=False), payload["license_id"], now_iso(), actor_name))
        log_event(db, "renewed" if prev else "activated",
                  {"license_id": payload["license_id"], "company": payload["company"], "by": actor_name,
                   "expires_at": payload.get("expires_at"), "max_users": payload["max_users"]})
    manager.invalidate()
    return payload


def apply_revocations(db, inst, manager, text, actor_name=""):
    pub = load_public_key(inst)
    if pub is None:
        raise LicenseError("license_no_key", "No vendor key")
    env = parse_text(text)
    payload = verify_envelope(env, pub)
    if not isinstance(payload.get("revoked"), list) or not isinstance(payload.get("serial"), int):
        raise LicenseError("license_format", "Not a revocation list")
    cur = db.one("SELECT serial FROM license_revocations WHERE id=1")
    if cur is not None and payload["serial"] <= cur["serial"]:
        raise LicenseError("revocation_old", "This revocation list is older than the one already installed")
    with db.tx():
        db.execute("INSERT INTO license_revocations(id,envelope,serial) VALUES (1,?,?) "
                   "ON CONFLICT(id) DO UPDATE SET envelope=excluded.envelope, serial=excluded.serial",
                   (json.dumps(env, sort_keys=True), payload["serial"]))
        log_event(db, "revocations_applied", {"serial": payload["serial"], "count": len(payload["revoked"]), "by": actor_name})
    manager.invalidate()
    return payload


def refresh_online(db, inst, manager):
    """Optional: fetch the signed revocation list from the vendor. Offline deployments simply never call this."""
    url = inst.config.get("license_server_url")
    if not url:
        return False
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            text = r.read(1_000_000).decode("utf-8")
        apply_revocations(db, inst, manager, text, "online-check")
        return True
    except LicenseError as e:
        if e.code != "revocation_old":
            log_event(db, "online_check_rejected", {"code": e.code})
        return False
    except Exception as e:
        log_event(db, "online_check_failed", {"error": str(e)[:200]})
        return False


def events(db, limit=100):
    return [dict(r, detail=json.loads(r["detail"])) for r in
            db.query("SELECT id,ts,event,detail FROM license_events ORDER BY id DESC LIMIT ?", (limit,))]
