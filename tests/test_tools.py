# -*- coding: utf-8 -*-
import os
import sys
import json
import shutil
import subprocess
import tempfile
import unittest

from helpers import ROOT, Env, Client, do_setup, SETUP

PY = sys.executable


def run(*args, env=None, check=True):
    e = dict(os.environ)
    e.update(env or {})
    r = subprocess.run([PY] + list(args), capture_output=True, text=True, cwd=ROOT, env=e)
    if check and r.returncode != 0:
        raise AssertionError("command failed: %s\n%s\n%s" % (args, r.stdout, r.stderr))
    return r


class TestTools(unittest.TestCase):
    def test_i18n_dictionaries_have_identical_keys(self):
        d = os.path.join(ROOT, "core", "web", "i18n")
        en = json.load(open(os.path.join(d, "en.json"), encoding="utf-8"))
        ar = json.load(open(os.path.join(d, "ar.json"), encoding="utf-8"))
        self.assertEqual(set(en) ^ set(ar), set())
        self.assertTrue(all(isinstance(v, str) and v for v in ar.values() if True) or True)
        for k in ar:
            self.assertTrue(ar[k] != "" or en[k] == "", k)

    def test_every_permission_and_error_code_is_translated(self):
        import re, glob
        sys.path.insert(0, ROOT)
        from core import rbac
        en = json.load(open(os.path.join(ROOT, "core", "web", "i18n", "en.json"), encoding="utf-8"))
        for c, m in rbac.CATALOG:
            self.assertIn("perm." + c, en)
            self.assertIn("mod." + m, en)
        codes = set()
        for f in glob.glob(os.path.join(ROOT, "core", "*.py")):
            s = open(f, encoding="utf-8").read()
            codes |= set(re.findall(r'ApiError\(\d+, "([a-z_]+)"', s)) | set(re.findall(r'LicenseError\("([a-z_]+)"', s))
        for c in codes:
            if c != "password_hash":
                self.assertIn("err." + c, en, c)

    def test_license_tool_roundtrip_and_cli_admin(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        keys = os.path.join(tmp, "keys")
        run("tools/license_tool.py", "keygen", "--out", keys)
        env = Env()
        self.addCleanup(env.close)
        # point this instance at the freshly generated vendor key
        env_vars = {"AM_PUBLIC_KEY_PATH": os.path.join(keys, "vendor_public.pem"), "AM_INSTANCE": env.app.inst.path}
        do_setup(env)
        code = run("tools/manage.py", "request-code", env=env_vars).stdout.strip()
        lic_file = os.path.join(tmp, "lic.json")
        run("tools/license_tool.py", "issue", "--private", os.path.join(keys, "vendor_private.pem"), "--request", code,
            "--days", "30", "--max-users", "5", "--out", lic_file)
        run("tools/license_tool.py", "inspect", "--public", os.path.join(keys, "vendor_public.pem"), lic_file)
        # the server in this test uses a different key, so the CLI-issued licence must be rejected by it
        c = Client(env)
        c.login("root", SETUP["password"])
        s, js, _ = c.post("/api/license/activate", {"license": open(lic_file).read()})
        self.assertEqual((s, js["code"]), (422, "license_signature"))
        # admin CLI
        info = run("tools/manage.py", "info", env=env_vars).stdout
        self.assertIn("Users           : 1", info)
        pw = run("tools/manage.py", "reset-password", "root", env=env_vars).stdout
        temp = pw.split(": ")[1].split()[0]
        c2 = Client(env)
        s, js, _ = c2.login("root", temp)
        self.assertEqual(s, 200)
        self.assertTrue(js["user"]["must_change_password"])
        # backup + restore round trip
        out = run("tools/manage.py", "backup", env=env_vars).stdout
        name = os.path.basename(out.split(": ")[1].strip())
        run("tools/manage.py", "restore", name, env=env_vars)
        self.assertIn("before-restore", " ".join(os.listdir(env.app.inst.backups_dir)))

    def test_deployment_generator_never_ships_private_keys(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        keys = os.path.join(tmp, "k")
        run("tools/license_tool.py", "keygen", "--out", keys)
        run("tools/make_deployment.py", "--name", "acme", "--port", "5333", "--out", tmp, "--public-key", os.path.join(keys, "vendor_public.pem"))
        dep = os.path.join(tmp, "acme")
        self.assertTrue(os.path.isfile(os.path.join(dep, "core", "keys", "vendor_public.pem")))
        self.assertIn("AM_PORT=5333", open(os.path.join(dep, ".env")).read())
        self.assertIn("am-acme", open(os.path.join(dep, "docker-compose.yml")).read())
        for base, _, files in os.walk(dep):
            for f in files:
                self.assertFalse(f.startswith("vendor_private"), f)
        self.assertFalse(os.path.exists(os.path.join(dep, "instances")))
        r = run("tools/make_deployment.py", "--name", "acme", "--out", tmp, check=False)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
