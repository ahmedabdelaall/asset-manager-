#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a company deployment from the official master.

  python tools/make_deployment.py --name acme --port 5222 --out ../deployments
Produces a self-contained folder:  <out>/<name>/  with
  - the product code copied from this master (read-only reference, never edited per company)
  - docker-compose.yml + .env for that company (own port, own data volume)
  - README with the exact commands
Company data lives in a Docker volume / instance folder, never inside the code.
"""
import os
import re
import sys
import shutil
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import VERSION

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "instances", ".git", "tests", "vendor_keys", "vendor_private*", ".env")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True, help="short company id, letters/digits/dash")
    p.add_argument("--port", type=int, default=5222)
    p.add_argument("--out", required=True)
    p.add_argument("--public-key", help="path to YOUR vendor public key (vendor_public.pem) to bake into this deployment")
    p.add_argument("--license", choices=("on", "off"), default="on", help="off = no licence needed (no lock, no user limit)")
    p.add_argument("--tz", default="Africa/Cairo", help="company time zone, e.g. Africa/Cairo or Asia/Riyadh")
    a = p.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]{1,30}", a.name):
        sys.exit("--name must be lowercase letters, digits or dashes")
    dest = os.path.join(a.out, a.name)
    if os.path.exists(dest):
        sys.exit("Already exists: " + dest)
    os.makedirs(dest)
    for item in ("core", "tools", "Dockerfile", "requirements.txt", "VERSION", "CHANGELOG.md", ".dockerignore"):
        s = os.path.join(ROOT, item)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(dest, item), ignore=IGNORE)
        elif os.path.exists(s):
            shutil.copy2(s, os.path.join(dest, item))
    for base, _, files in os.walk(dest):
        for f in files:
            if f.startswith("vendor_private"):
                shutil.rmtree(dest)
                sys.exit("SAFETY STOP: a private key was found in the master. Never keep it there.")
    keys = os.path.join(dest, "core", "keys")
    os.makedirs(keys, exist_ok=True)
    if a.public_key:
        shutil.copy2(a.public_key, os.path.join(keys, "vendor_public.pem"))
    elif a.license == "on" and not os.path.exists(os.path.join(keys, "vendor_public.pem")):
        print("WARNING: no vendor public key included - licences cannot be verified until you add core/keys/vendor_public.pem")
    with open(os.path.join(ROOT, "docker-compose.yml"), "r", encoding="utf-8") as f:
        comp = f.read()
    comp = comp.replace("assetmaster", "am-" + a.name)
    with open(os.path.join(dest, "docker-compose.yml"), "w", encoding="utf-8") as f:
        f.write(comp)
    with open(os.path.join(dest, ".env"), "w", encoding="utf-8") as f:
        f.write("AM_PORT=%d\nTZ=%s\nAM_LICENSE=%s\n" % (a.port, a.tz, a.license))
    with open(os.path.join(dest, "RELEASE.txt"), "w", encoding="utf-8") as f:
        f.write("Generated from Asset Master %s for '%s'.\nStart: docker compose up -d --build\nOpen: http://SERVER:%d\n" % (VERSION, a.name, a.port))
    print("Deployment created:", dest, "(from master v%s)" % VERSION)


if __name__ == "__main__":
    main()
