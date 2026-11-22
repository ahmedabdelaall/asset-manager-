# -*- coding: utf-8 -*-
"""Company identity and branding. Nothing about any particular company is hard-coded in the product."""
import os
import hashlib

from .errors import ApiError
from .util import now_iso, text, choice, color

LOGO_MAX = 1024 * 1024


def _sniff(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


MIME = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def get(db):
    r = db.one("SELECT * FROM company WHERE id=1")
    return dict(r) if r else None


def branding(db):
    c = get(db)
    if c is None:
        return {"configured": False, "name_en": "", "name_ar": "", "app_name_en": "Asset Manager", "app_name_ar": "إدارة الأصول",
                "primary_color": "#6D4AF2", "accent_color": "#2F6BF0", "default_language": "en", "default_theme": "light",
                "logo": None}
    return {"configured": True, "name_en": c["name_en"], "name_ar": c["name_ar"], "app_name_en": c["app_name_en"],
            "app_name_ar": c["app_name_ar"], "primary_color": c["primary_color"], "accent_color": c["accent_color"],
            "default_language": c["default_language"], "default_theme": c["default_theme"],
            "logo": ("/brand/logo?v=" + c["logo_hash"][:10]) if c["logo_file"] else None}


def create(db, data):
    if get(db) is not None:
        raise ApiError(409, "already_configured", "Company is already configured")
    vals = _validate(data, creating=True)
    db.execute("INSERT INTO company(id,name_en,name_ar,app_name_en,app_name_ar,primary_color,accent_color,default_language,default_theme,updated_at) "
               "VALUES (1,?,?,?,?,?,?,?,?,?)",
               (vals["name_en"], vals["name_ar"], vals["app_name_en"], vals["app_name_ar"], vals["primary_color"],
                vals["accent_color"], vals["default_language"], vals["default_theme"], now_iso()))


def _validate(d, creating=False):
    name_en = text(d, "name_en", maxlen=120, required=False)
    name_ar = text(d, "name_ar", maxlen=120, required=False)
    if not name_en and not name_ar:
        raise ApiError(422, "company_name_required", "Enter the company name in English or Arabic", field="name_en")
    return {"name_en": name_en or name_ar, "name_ar": name_ar or name_en,
            "app_name_en": text(d, "app_name_en", maxlen=60, required=False, default="Asset Manager") or "Asset Manager",
            "app_name_ar": text(d, "app_name_ar", maxlen=60, required=False, default="إدارة الأصول") or "إدارة الأصول",
            "primary_color": color(d, "primary_color", "#6D4AF2"), "accent_color": color(d, "accent_color", "#2F6BF0"),
            "default_language": choice(d, "default_language", ("en", "ar"), "en"),
            "default_theme": choice(d, "default_theme", ("light", "dark", "system"), "light")}


def update(db, data):
    old = get(db)
    if old is None:
        raise ApiError(409, "not_configured", "Company is not configured yet")
    v = _validate(data)
    # receipt terms are optional in the request: keep the stored text when the client does not send them
    v["receipt_terms_en"] = text(data, "receipt_terms_en", maxlen=3000, required=False) if "receipt_terms_en" in data else old["receipt_terms_en"]
    v["receipt_terms_ar"] = text(data, "receipt_terms_ar", maxlen=3000, required=False) if "receipt_terms_ar" in data else old["receipt_terms_ar"]
    db.execute("UPDATE company SET name_en=?,name_ar=?,app_name_en=?,app_name_ar=?,primary_color=?,accent_color=?,"
               "default_language=?,default_theme=?,receipt_terms_en=?,receipt_terms_ar=?,updated_at=? WHERE id=1",
               (v["name_en"], v["name_ar"], v["app_name_en"], v["app_name_ar"], v["primary_color"], v["accent_color"],
                v["default_language"], v["default_theme"], v["receipt_terms_en"], v["receipt_terms_ar"], now_iso()))
    return v


def set_logo(db, inst, data):
    if not data:
        raise ApiError(400, "no_file", "No file received")
    if len(data) > LOGO_MAX:
        raise ApiError(413, "logo_too_large", "The logo must be smaller than 1 MB")
    ext = _sniff(data)
    if not ext:
        raise ApiError(400, "logo_bad_type", "Use a PNG, JPG or WebP image")
    folder = os.path.join(inst.uploads_dir, "branding")
    os.makedirs(folder, exist_ok=True)
    name = "logo.%s" % ext
    for old in os.listdir(folder):
        if old.startswith("logo."):
            os.remove(os.path.join(folder, old))
    with open(os.path.join(folder, name), "wb") as f:
        f.write(data)
    db.execute("UPDATE company SET logo_file=?, logo_hash=?, updated_at=? WHERE id=1",
               (name, hashlib.sha256(data).hexdigest(), now_iso()))


def remove_logo(db, inst):
    c = get(db)
    if c and c["logo_file"]:
        try:
            os.remove(os.path.join(inst.uploads_dir, "branding", c["logo_file"]))
        except OSError:
            pass
    db.execute("UPDATE company SET logo_file=NULL, logo_hash=NULL, updated_at=? WHERE id=1", (now_iso(),))


def logo_file(db, inst):
    c = get(db)
    if not c or not c["logo_file"]:
        return None
    p = os.path.join(inst.uploads_dir, "branding", c["logo_file"])
    return (p, MIME[c["logo_file"].rsplit(".", 1)[1]]) if os.path.isfile(p) else None
