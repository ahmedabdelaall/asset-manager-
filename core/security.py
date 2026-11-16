# -*- coding: utf-8 -*-
"""Password hashing, tokens and small crypto helpers (standard library only)."""
import re
import hmac
import base64
import hashlib
import secrets

_N, _R, _P = 2 ** 14, 8, 1
COMMON = {"password", "password1", "12345678", "123456789", "1234567890", "qwerty123", "admin123", "letmein123",
          "welcome123", "iloveyou1", "p@ssw0rd", "passw0rd", "administrator"}


def hash_password(password):
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt$%d$%d$%d$%s$%s" % (_N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(h).decode())


def verify_password(password, stored):
    try:
        algo, n, r, p, salt, h = stored.split("$")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                              dklen=len(base64.b64decode(h)))
        return hmac.compare_digest(calc, base64.b64decode(h))
    except Exception:
        return False


_DUMMY = hash_password("dummy-password-for-timing")


def dummy_verify(password):
    """Spend the same time as a real check so unknown usernames cannot be detected by timing."""
    verify_password(password, _DUMMY)


def password_problem(password, username=""):
    """Returns an error code or None."""
    if len(password) < 10:
        return "password_short"
    if len(password) > 200:
        return "password_long"
    if not re.search(r"[A-Za-z\u0600-\u06FF]", password) or not re.search(r"\d", password):
        return "password_weak"
    if password.lower() in COMMON or (username and password.lower() == username.lower()):
        return "password_common"
    return None


def new_token():
    return secrets.token_urlsafe(32)


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def temp_password():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    pw = "".join(secrets.choice(alphabet) for _ in range(12))
    return pw[:6] + str(secrets.randbelow(90) + 10) + pw[6:]


def mac(secret, text):
    return hmac.new(secret, text.encode("utf-8"), hashlib.sha256).hexdigest()


def safe_eq(a, b):
    return hmac.compare_digest(str(a), str(b))
