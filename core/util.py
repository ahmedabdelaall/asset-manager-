# -*- coding: utf-8 -*-
import re
import time
import datetime

from .errors import ApiError


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_iso(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def text(d, key, minlen=0, maxlen=200, required=True, default=""):
    v = d.get(key, default)
    if v is None:
        v = default
    if not isinstance(v, str):
        raise ApiError(400, "invalid_field", "Invalid value for %s" % key, field=key)
    v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", v).strip()
    if required and len(v) < max(1, minlen):
        raise ApiError(422, "field_required", "%s is required" % key, field=key)
    if len(v) > maxlen:
        raise ApiError(422, "field_too_long", "%s is too long" % key, field=key)
    return v


def choice(d, key, options, default=None):
    v = d.get(key, default)
    if v not in options:
        raise ApiError(422, "invalid_field", "Invalid value for %s" % key, field=key)
    return v


def color(d, key, default):
    v = d.get(key, default)
    if not isinstance(v, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        raise ApiError(422, "invalid_color", "Colour must look like #6D4AF2", field=key)
    return v.upper()


def username_ok(u):
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9._\-]{2,39}", u))
