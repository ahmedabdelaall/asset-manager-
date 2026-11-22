# -*- coding: utf-8 -*-
import re
import time
import datetime

from .errors import ApiError


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_iso(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def text(d, key, minlen=0, maxlen=200, required=True, default="", multiline=None):
    """A trimmed string without control characters. Single-line fields (the default for maxlen < 1000, i.e. names,
    titles, tags) also lose line breaks, so they can never smuggle extra lines into e-mail headers, exports or logs."""
    v = d.get(key, default)
    if v is None:
        v = default
    if not isinstance(v, str):
        raise ApiError(400, "invalid_field", "Invalid value for %s" % key, field=key)
    if multiline is None:
        multiline = maxlen >= 1000
    v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
    v = (v.replace("\r\n", "\n").replace("\r", "\n") if multiline else re.sub(r"[\r\n  ]+", " ", v)).strip()
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


def date_field(d, key, required=False):
    """A calendar date as YYYY-MM-DD, or '' when optional and empty."""
    v = d.get(key)
    if v in (None, ""):
        if required:
            raise ApiError(422, "field_required", "%s is required" % key, field=key)
        return ""
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        raise ApiError(422, "invalid_date", "Use a valid date", field=key)
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        raise ApiError(422, "invalid_date", "Use a valid date", field=key)
    return v


def number(d, key, minimum=0, maximum=1e12, required=False):
    """A decimal number, or None when optional and empty."""
    v = d.get(key)
    if v in (None, ""):
        if required:
            raise ApiError(422, "field_required", "%s is required" % key, field=key)
        return None
    if isinstance(v, bool):
        raise ApiError(422, "invalid_number", "Enter a number", field=key)
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ApiError(422, "invalid_number", "Enter a number", field=key)
    if f != f or f < minimum or f > maximum:
        raise ApiError(422, "invalid_number", "Enter a number", field=key)
    return f


def ref_id(d, key, required=True):
    """A positive integer id, or None when optional and empty."""
    v = d.get(key)
    if v in (None, "", 0):
        if required:
            raise ApiError(422, "field_required", "%s is required" % key, field=key)
        return None
    if isinstance(v, bool):
        raise ApiError(422, "invalid_field", "Invalid value for %s" % key, field=key)
    try:
        i = int(v)
    except (TypeError, ValueError):
        raise ApiError(422, "invalid_field", "Invalid value for %s" % key, field=key)
    if i <= 0:
        raise ApiError(422, "invalid_field", "Invalid value for %s" % key, field=key)
    return i


def today_iso():
    """The calendar date where the company is (server local time - set TZ, e.g. TZ=Asia/Riyadh, in Docker).
    Timestamps stay in UTC; only "what day is it" (overdue, warranty, date checks) uses the local date."""
    return time.strftime("%Y-%m-%d", time.localtime())


def username_ok(u):
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9._\-]{2,39}", u))
