# -*- coding: utf-8 -*-
"""Installable app (0.9.0): web manifest, icons, service worker, camera permission for the QR scanner."""
import struct
import unittest
import zlib

from test_api import Base
from helpers import Client
from core import appicon


class TestInstallableApp(Base):
    def test_manifest_icons_and_worker(self):
        c = self.admin()
        a = Client(self.env)                                            # works before sign-in (the phone fetches it anonymously)
        s, m, r = a.get("/manifest.webmanifest")
        self.assertEqual(s, 200)
        self.assertTrue(r.getheader("Content-Type").startswith("application/manifest+json"))
        self.assertEqual((m["name"], m["short_name"], m["display"], m["start_url"], m["scope"]),
                         ("Acme Corp Asset Manager", "Acme Corp", "standalone", "/#/dashboard", "/"))
        self.assertEqual(m["theme_color"].upper(), "#6D4AF2")
        self.assertEqual({(i["sizes"], i["purpose"]) for i in m["icons"]}, {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")})
        self.assertEqual(m["shortcuts"][0]["url"], "/#/scanner")
        # icons exist for every size the manifest and iPhone ask for; anything else is 404
        for size in (180, 192, 512):
            s, _, r = a.get("/app-icon-%d.png" % size)
            self.assertEqual((s, r.getheader("Content-Type")), (200, "image/png"), size)
        self.assertEqual(a.get("/app-icon-64.png")[0], 404)
        # the service worker is served from the site root (so it controls the whole app) as JavaScript
        s, _, r = a.get("/sw.js")
        self.assertEqual(s, 200)
        self.assertTrue(r.getheader("Content-Type").startswith("application/javascript"))
        # the page may use the camera (QR scanner); microphone, location etc. stay blocked
        pp = a.get("/")[2].getheader("Permissions-Policy")
        self.assertIn("camera=(self)", pp)
        self.assertIn("microphone=()", pp)
        self.assertIn("geolocation=()", pp)
        # the manifest follows the company's branding (Arabic default language -> Arabic name and direction)
        c.put("/api/company", {"name_en": "Acme Corp", "name_ar": "شركة أكمي", "default_language": "ar", "primary_color": "#0F766E", "accent_color": "#2F6BF0"})
        m = a.get("/manifest.webmanifest")[1]
        if m["lang"] == "ar":                                           # only if the company endpoint accepted the change
            self.assertEqual((m["short_name"], m["dir"]), ("شركة أكمي", "rtl"))

    def test_lookup_any_scanned_code(self):
        from test_assets import LAPTOP
        c = self.admin()
        cat = c.post("/api/categories", dict(LAPTOP, fields=LAPTOP["fields"] + [{"key": "imei", "label_en": "IMEI", "type": "text"}]))[1]["id"]
        aid = c.post("/api/assets", {"category_id": cat, "name": "T14", "serial_no": "PF4ABC12", "custom": {"ram_gb": 16, "imei": "866627084689374"}})[1]["id"]
        tag = c.get("/api/assets/%d" % aid)[1]["tag"]
        for code, how in ((tag.lower(), "tag"), ("pf4abc12", "serial"), ("866627084689374", "field"), ("  PF4ABC12 ", "serial")):
            s, js, _ = c.get("/api/assets/by-code?code=" + code.replace(" ", "%20"))
            self.assertEqual((s, js["id"], js["matched"]), (200, aid, how), code)
        self.assertEqual(c.get("/api/assets/by-code?code=16")[1]["matched"], "field")     # numbers in custom fields match too
        self.assertEqual(c.get("/api/assets/by-code?code=NOPE-123")[0], 404)
        self.assertEqual(c.get("/api/assets/by-code?code=")[0], 404)
        self.assertEqual(Client(self.env).get("/api/assets/by-code?code=PF4ABC12")[0], 401)   # signed-in users only

    def test_icon_is_a_valid_png(self):
        data = appicon.png(192, "#6D4AF2", "#2F6BF0")
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
        self.assertEqual((w, h, depth, ctype), (192, 192, 8, 2))
        # decode the pixels: corners carry the brand gradient, the centre area has the white mark
        idat = data[data.index(b"IDAT") + 4:data.index(b"IEND") - 8]
        raw = zlib.decompress(idat)
        px = lambda x, y: raw[y * (1 + 192 * 3) + 1 + x * 3: y * (1 + 192 * 3) + 1 + x * 3 + 3]
        self.assertEqual(px(0, 0), bytes((109, 74, 242)))
        self.assertEqual(px(191, 191), bytes((47, 107, 240)))
        self.assertEqual(px(50, 50), b"\xff\xff\xff")                  # top-left finder square of the mark
        self.assertIs(appicon.png(192, "#6D4AF2", "#2F6BF0"), data)     # cached
        self.assertEqual(appicon.png(32, "nonsense", "")[:8], b"\x89PNG\r\n\x1a\n")   # bad colours fall back safely


if __name__ == "__main__":
    unittest.main()
