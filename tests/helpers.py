# -*- coding: utf-8 -*-
import os
import sys
import json
import shutil
import tempfile
import threading
import http.client
import datetime
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def make_keys(folder):
    priv = Ed25519PrivateKey.generate()
    pub_path = os.path.join(folder, "vendor_public.pem")
    with open(pub_path, "wb") as f:
        f.write(priv.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return priv, pub_path


class Env:
    """A throw-away instance + running server for tests."""
    def __init__(self, with_key=True, config=None):
        self.dir = tempfile.mkdtemp(prefix="am_test_")
        self.priv, self.pub_path = make_keys(self.dir)
        if with_key:
            os.environ["AM_PUBLIC_KEY_PATH"] = self.pub_path
        else:
            os.environ["AM_PUBLIC_KEY_PATH"] = os.path.join(self.dir, "missing.pem")
        inst = os.path.join(self.dir, "inst")
        if config:
            os.makedirs(inst, exist_ok=True)
            with open(os.path.join(inst, "config.json"), "w") as f:
                json.dump(config, f)
        from core.server import App, make_handler, Server
        self.app = App(inst)
        self.httpd = Server(("127.0.0.1", 0), make_handler(self.app))
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def issue_license(self, days=365, max_users=10, grace=14, deployment_id=None, features=None, expires=None):
        from license_tool import sign
        from core import PRODUCT, licensing
        import uuid
        today = datetime.date.today()
        payload = {"product": PRODUCT, "license_id": str(uuid.uuid4()), "company": "Test Co",
                   "deployment_id": deployment_id or licensing.deployment_id(self.app.inst),
                   "issued_at": today.isoformat(),
                   "expires_at": expires if expires is not None else (today + datetime.timedelta(days=days)).isoformat(),
                   "grace_days": grace, "max_users": max_users, "features": features or [], "edition": "test"}
        return json.dumps(sign(self.priv, payload)), payload

    def issue_revocations(self, serial, ids):
        from license_tool import sign
        from core import PRODUCT
        return json.dumps(sign(self.priv, {"product": PRODUCT, "serial": serial, "issued_at": "2026-01-01", "revoked": ids}))


class Client:
    def __init__(self, env):
        self.env, self.cookie, self.csrf = env, None, None

    def req(self, method, path, body=None, headers=None, raw=None, csrf=True):
        c = http.client.HTTPConnection("127.0.0.1", self.env.port, timeout=15)
        h = {"Host": "127.0.0.1:%d" % self.env.port}
        h.update(headers or {})
        if self.cookie:
            h["Cookie"] = "am_session=" + self.cookie
        if self.csrf and csrf and method != "GET":
            h["X-CSRF-Token"] = self.csrf
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        payload = r.read()
        try:
            js = json.loads(payload.decode("utf-8"))
        except Exception:
            js = None
        sc = r.getheader("Set-Cookie")
        if sc and "am_session=" in sc:
            val = sc.split("am_session=")[1].split(";")[0]
            self.cookie = val or None
        c.close()
        return r.status, js, r

    def get(self, p, **k): return self.req("GET", p, **k)
    def post(self, p, body=None, **k):
        if k.get("raw") is not None:
            return self.req("POST", p, None, **k)
        return self.req("POST", p, body if body is not None else {}, **k)
    def put(self, p, body=None, **k): return self.req("PUT", p, body if body is not None else {}, **k)
    def delete(self, p, **k): return self.req("DELETE", p, **k)

    def login(self, user, pw):
        s, js, r = self.post("/api/auth/login", {"username": user, "password": pw})
        if s == 200:
            self.csrf = js["csrf"]
        return s, js, r


SETUP = {"name_en": "Acme Corp", "name_ar": "شركة أكمي", "default_language": "en", "username": "root",
         "full_name": "Root Admin", "email": "root@acme.test", "password": "Sup3r-Secret-Pass"}


def do_setup(env, **over):
    c = Client(env)
    d = dict(SETUP, setup_code=env.app.setup_code)
    d.update(over)
    return c.post("/api/setup", d)
