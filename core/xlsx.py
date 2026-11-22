# -*- coding: utf-8 -*-
"""Minimal .xlsx writer and reader using only the standard library.

Writer: several sheets, bold header row, column widths, optional right-to-left sheets, text/number cells.
Reader: first worksheet as a list of rows; shared/inline strings, numbers, booleans and dates (by cell style).
Untrusted input is size-limited and documents with a DOCTYPE are rejected (no entity expansion)."""
import io
import re
import zipfile
import datetime
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from .errors import ApiError

MAX_UNCOMPRESSED = 60 * 1024 * 1024
MAX_ROWS = 5000
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
_BAD_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


# ------------------------------------------------------------------ writer
def _col(n):
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref, v, style):
    st = ' s="%d"' % style if style else ""
    if v is None or v == "":
        return '<c r="%s"%s/>' % (ref, st)
    if isinstance(v, bool):
        return '<c r="%s"%s t="b"><v>%d</v></c>' % (ref, st, 1 if v else 0)
    if isinstance(v, (int, float)):
        return '<c r="%s"%s><v>%r</v></c>' % (ref, st, v)
    s = _BAD_XML.sub("", str(v))      # inline strings are always text in Excel - never evaluated as formulas
    return '<c r="%s"%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, st, escape(s))


def write(sheets):
    """sheets: list of dicts {name, rows: [[...]], widths: [..] optional, rtl: bool optional}. First row is the header."""
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    n = len(sheets)
    z.writestr("[Content_Types].xml",
               '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
               '<Default Extension="xml" ContentType="application/xml"/>'
               '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
               '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
               + "".join('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1) for i in range(n))
               + '</Types>')
    z.writestr("_rels/.rels",
               '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
               '</Relationships>')
    names, used = [], set()
    for s in sheets:
        nm = re.sub(r"[\[\]:*?/\\]", "", s["name"])[:31] or "Sheet"
        base, k = nm, 1
        while nm.lower() in used:
            k += 1
            nm = (base[:28] + " %d" % k)
        used.add(nm.lower())
        names.append(nm)
    z.writestr("xl/workbook.xml",
               '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<workbook xmlns="%s" xmlns:r="%s"><sheets>' % (NS["m"], NS["r"])
               + "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(nm, {'"': "&quot;"}), i + 1, i + 1) for i, nm in enumerate(names))
               + '</sheets></workbook>')
    z.writestr("xl/_rels/workbook.xml.rels",
               '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               + "".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1) for i in range(n))
               + '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (n + 1)
               + '</Relationships>')
    z.writestr("xl/styles.xml",
               '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<styleSheet xmlns="%s">' % NS["m"]
               + '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>'
               '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
               '<fill><patternFill patternType="solid"><fgColor rgb="FF4B3FC9"/><bgColor indexed="64"/></patternFill></fill></fills>'
               '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
               '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
               '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
               '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs>'
               '</styleSheet>')
    for i, s in enumerate(sheets):
        rows = s["rows"]
        widths = s.get("widths") or [max(10, min(50, max((len(str(r[c])) for r in rows if c < len(r) and r[c] is not None), default=8) + 2))
                                     for c in range(max((len(r) for r in rows), default=0))]
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="%s">' % NS["m"],
               '<sheetViews><sheetView workbookViewId="0"%s>' % (' rightToLeft="1"' if s.get("rtl") else ""),
               '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>' if rows else '</sheetView></sheetViews>']
        if widths:
            out.append("<cols>" + "".join('<col min="%d" max="%d" width="%d" customWidth="1"/>' % (c + 1, c + 1, w) for c, w in enumerate(widths)) + "</cols>")
        out.append("<sheetData>")
        for r, row in enumerate(rows):
            out.append('<row r="%d">' % (r + 1) + "".join(_cell("%s%d" % (_col(c), r + 1), v, 1 if r == 0 else 0) for c, v in enumerate(row)) + "</row>")
        out.append("</sheetData></worksheet>")
        z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), "".join(out))
    z.close()
    return buf.getvalue()


# ------------------------------------------------------------------ reader
def _xml(z, name):
    data = z.read(name)
    if b"<!DOCTYPE" in data[:2048].upper() or b"<!ENTITY" in data.upper():
        raise ApiError(400, "file_unreadable", "The file could not be read")
    return ET.fromstring(data)


def _ref_col(ref):
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return n - 1


DATE_FMT_IDS = set(range(14, 23)) | {27, 30, 36, 45, 46, 47, 50, 57}


def _date_styles(z):
    try:
        root = _xml(z, "xl/styles.xml")
    except KeyError:
        return set()
    custom = {}
    nf = root.find("m:numFmts", NS)
    if nf is not None:
        for f in nf.findall("m:numFmt", NS):
            code = re.sub(r'"[^"]*"|\[[^\]]*\]', "", f.get("formatCode", "").lower())
            custom[int(f.get("numFmtId"))] = "y" in code or "d" in code
    out = set()
    xfs = root.find("m:cellXfs", NS)
    if xfs is not None:
        for i, xf in enumerate(xfs.findall("m:xf", NS)):
            fid = int(xf.get("numFmtId", "0"))
            if fid in DATE_FMT_IDS or custom.get(fid):
                out.add(i)
    return out


def _serial_to_date(v):
    return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(v)))).isoformat()


def read(data):
    """Rows of the first worksheet. Values: str, float, bool, or 'YYYY-MM-DD' for date-formatted cells."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ApiError(400, "file_unreadable", "The file could not be read")
    if sum(i.file_size for i in z.infolist()) > MAX_UNCOMPRESSED:
        raise ApiError(413, "too_large", "The file is too large")
    try:
        wb = _xml(z, "xl/workbook.xml")
        first = wb.find("m:sheets/m:sheet", NS)
        rid = first.get("{%s}id" % NS["r"])
        rels = _xml(z, "xl/_rels/workbook.xml.rels")
        target = next(r.get("Target") for r in rels.findall("pr:Relationship", NS) if r.get("Id") == rid)
        target = target.lstrip("/")
        path = target if target.startswith("xl/") else "xl/" + target
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in _xml(z, "xl/sharedStrings.xml").findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        dates = _date_styles(z)
        sheet = _xml(z, path)
    except ApiError:
        raise
    except Exception:
        raise ApiError(400, "file_unreadable", "The file could not be read")
    rows = []
    for row in sheet.iter("{%s}row" % NS["m"]):
        vals = {}
        for c in row.findall("m:c", NS):
            col = _ref_col(c.get("r", "A"))
            t = c.get("t", "n")
            v = c.find("m:v", NS)
            if t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
            elif v is None:
                continue
            elif t == "s":
                val = shared[int(v.text)] if v.text and int(v.text) < len(shared) else ""
            elif t == "b":
                val = v.text == "1"
            elif t in ("str", "e"):
                val = v.text or ""
            else:
                try:
                    val = _serial_to_date(v.text) if int(c.get("s", "0")) in dates else float(v.text)
                except (TypeError, ValueError):
                    val = v.text or ""
            vals[col] = val
        if vals:
            idx = int(row.get("r", len(rows) + 1)) - 1
            while len(rows) < idx:
                rows.append([])
            rows.append([vals.get(i, "") for i in range(max(vals) + 1)])
        if len(rows) > MAX_ROWS + 1:
            raise ApiError(413, "too_many_rows", "Too many rows (maximum %d)" % MAX_ROWS)
    return rows


def read_csv(data):
    import csv
    for enc in ("utf-8-sig", "cp1256", "latin-1"):
        try:
            s = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = s[:4096]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    rows = [r for r in csv.reader(io.StringIO(s), delimiter=delim)]
    if len(rows) > MAX_ROWS + 1:
        raise ApiError(413, "too_many_rows", "Too many rows (maximum %d)" % MAX_ROWS)
    return rows
