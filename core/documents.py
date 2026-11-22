# -*- coding: utf-8 -*-
"""Files attached to assets, employees and assignments (e.g. invoices, photos, signed receipts).

Files are stored under uploads/docs/ with random names; the original name is only kept in the database.
The type is decided by the file's content (magic bytes), never by its name or the browser's claim."""
import io
import os
import re
import secrets
import hashlib
import zipfile
import urllib.parse

from . import rbac
from .errors import ApiError
from .util import now_iso, text

# entity -> (permission to see, permission to add/delete, table that must contain the id)
ENTITIES = {
    "asset": ("assets.view", "assets.manage", "assets"),
    "employee": ("employees.view", "employees.manage", "employees"),
    "assignment": ("assets.view", "assignments.manage", "assignments"),
}
INLINE = {"application/pdf", "image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_PER_ENTITY = 100


def sniff(data):
    """Return (extension, mime) for the supported file types, or None."""
    if data[:5] == b"%PDF-":
        return "pdf", "application/pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif", "image/gif"
    if data[:4] == b"PK\x03\x04":
        try:
            names = set(zipfile.ZipFile(io.BytesIO(data)).namelist())
        except zipfile.BadZipFile:
            return None
        if "[Content_Types].xml" in names:
            if any(n.startswith("word/") for n in names):
                return "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if any(n.startswith("xl/") for n in names):
                return "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return None


def _check(ctx, entity, write):
    if entity not in ENTITIES:
        raise ApiError(400, "bad_request", "Bad request")
    perm = ENTITIES[entity][1 if write else 0]
    if not rbac.user_has(ctx.db, ctx.user, perm):
        raise ApiError(403, "forbidden", "You do not have permission")


def _target(ctx, entity, eid):
    if ctx.db.one("SELECT 1 FROM %s WHERE id=?" % ENTITIES[entity][2], (eid,)) is None:
        raise ApiError(404, "not_found", "Not found")


def list_for(ctx, entity, eid):
    _check(ctx, entity, False)
    return [dict(r) for r in ctx.db.query(
        "SELECT d.id, d.filename, d.mime, d.size, d.note, d.created_at, u.username AS uploaded_by_name "
        "FROM documents d LEFT JOIN users u ON u.id=d.uploaded_by WHERE d.entity=? AND d.entity_id=? ORDER BY d.id DESC",
        (entity, eid))]


def clean_filename(name, ext):
    name = urllib.parse.unquote(name or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f\x7f\"<>:|?*]", "", name).strip(" .")[:120]
    base = name.rsplit(".", 1)[0] if "." in name else name
    return (base or "file") + "." + ext


def add(ctx, entity, eid, data, filename, note=""):
    _check(ctx, entity, True)
    _target(ctx, entity, eid)
    if not data:
        raise ApiError(400, "no_file", "No file received")
    kind = sniff(data)
    if kind is None:
        raise ApiError(400, "file_bad_type", "Use PDF, an image (PNG, JPG, WebP, GIF), Word or Excel")
    ext, mime = kind
    note = text({"n": note}, "n", maxlen=200, required=False)
    db = ctx.db
    if db.one("SELECT COUNT(*) c FROM documents WHERE entity=? AND entity_id=?", (entity, eid))["c"] >= MAX_PER_ENTITY:
        raise ApiError(409, "too_many_files", "Too many files on this record")
    rel = "docs/%s/%s.%s" % (now_iso()[:7], secrets.token_hex(16), ext)
    full = os.path.join(ctx.app.inst.uploads_dir, *rel.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)
    name = clean_filename(filename, ext)
    try:
        with db.tx():
            cur = db.execute("INSERT INTO documents(entity,entity_id,filename,stored,mime,size,sha256,note,uploaded_by,created_at) "
                             "VALUES (?,?,?,?,?,?,?,?,?,?)", (entity, eid, name, rel, mime, len(data),
                                                              hashlib.sha256(data).hexdigest(), note, ctx.user["id"], now_iso()))
            audit_entity, audit_id = _audit_target(db, entity, eid)
            ctx.audit("document.add", audit_entity, audit_id, {"file": name, "size": len(data), "document": cur.lastrowid, "on": entity})
    except BaseException:
        try:
            os.remove(full)
        except OSError:
            pass
        raise
    return cur.lastrowid


def _audit_target(db, entity, eid):
    """Signed receipts are shown on the asset's timeline."""
    if entity == "assignment":
        g = db.one("SELECT asset_id FROM assignments WHERE id=?", (eid,))
        return "asset", g["asset_id"]
    return entity, eid


def _get(ctx, did, write):
    d = ctx.db.one("SELECT * FROM documents WHERE id=?", (did,))
    if d is None:
        raise ApiError(404, "not_found", "Not found")
    _check(ctx, d["entity"], write)
    return d


def file_for(ctx, did):
    d = _get(ctx, did, False)
    full = os.path.join(ctx.app.inst.uploads_dir, *d["stored"].split("/"))
    if not os.path.isfile(full):
        raise ApiError(404, "file_missing", "The file is missing from the server")
    with open(full, "rb") as f:
        return d, f.read()


def remove(ctx, did):
    d = _get(ctx, did, True)
    db = ctx.db
    with db.tx():
        db.execute("DELETE FROM documents WHERE id=?", (did,))
        audit_entity, audit_id = _audit_target(db, d["entity"], d["entity_id"])
        ctx.audit("document.delete", audit_entity, audit_id, {"file": d["filename"], "document": did, "on": d["entity"]})
    try:
        os.remove(os.path.join(ctx.app.inst.uploads_dir, *d["stored"].split("/")))
    except OSError:
        pass


def disposition(filename, inline):
    ascii_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename) or "file"
    return '%s; filename="%s"; filename*=UTF-8\'\'%s' % ("inline" if inline else "attachment", ascii_name,
                                                        urllib.parse.quote(filename, safe=""))
