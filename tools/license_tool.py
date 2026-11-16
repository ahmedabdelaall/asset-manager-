#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VENDOR TOOL - keep this tool and the private key on YOUR computer only. Never ship them to customers.

  python tools/license_tool.py keygen   --out ./vendor_keys
  python tools/license_tool.py issue    --private ./vendor_keys/vendor_private.pem --request <code> --company "ACME" --days 365 --max-users 50
  python tools/license_tool.py revoke   --private ./vendor_keys/vendor_private.pem --serial 1 --id <license_id> --out revocations.json
  python tools/license_tool.py inspect  --public  ./vendor_keys/vendor_public.pem  licence.json
"""
import os
import sys
import json
import base64
import argparse
import datetime
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.licensing import canonical, verify_envelope, LicenseError
from core import PRODUCT


def load_private(path):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def sign(priv, payload):
    return {"alg": "ed25519", "payload": payload, "signature": base64.b64encode(priv.sign(canonical(payload))).decode("ascii")}


def cmd_keygen(a):
    os.makedirs(a.out, exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    pp, pb = os.path.join(a.out, "vendor_private.pem"), os.path.join(a.out, "vendor_public.pem")
    if os.path.exists(pp) and not a.force:
        sys.exit("A private key already exists there. Use --force only if you are sure (old licences stop working).")
    with open(pp, "wb") as f:
        f.write(priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    try:
        os.chmod(pp, 0o600)
    except OSError:
        pass
    with open(pb, "wb") as f:
        f.write(priv.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    print("Private key (SECRET - back it up safely, never share): " + pp)
    print("Public key (goes into the product):                    " + pb)
    print("Next: copy the public key to  core/keys/vendor_public.pem  and rebuild your releases.")


def cmd_issue(a):
    priv = load_private(a.private)
    company, dep = a.company, a.deployment_id
    if a.request:
        try:
            req = json.loads(base64.urlsafe_b64decode(a.request.strip().encode("ascii")).decode("utf-8"))
        except Exception:
            sys.exit("The activation request code is not valid.")
        if req.get("product") != PRODUCT:
            sys.exit("The request is for a different product.")
        dep = req["deployment_id"]
        company = company or req.get("company")
    if not dep or not company:
        sys.exit("Provide --request (recommended) or both --deployment-id and --company.")
    today = datetime.date.today()
    if a.perpetual:
        expires = None
    elif a.expires:
        expires = a.expires
    else:
        expires = (today + datetime.timedelta(days=a.days)).isoformat()
    payload = {"product": PRODUCT, "license_id": str(uuid.uuid4()), "company": company, "deployment_id": dep,
               "issued_at": today.isoformat(), "expires_at": expires, "grace_days": a.grace_days,
               "max_users": a.max_users, "features": [x for x in a.features.split(",") if x], "edition": a.edition}
    out = a.out or ("licence_%s.json" % company.replace(" ", "_"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(sign(priv, payload), f, ensure_ascii=False, indent=1)
    print("Licence written to %s\n  id=%s company=%s expires=%s users=%d" % (out, payload["license_id"], company, expires or "never", a.max_users))


def cmd_revoke(a):
    priv = load_private(a.private)
    payload = {"product": PRODUCT, "serial": a.serial, "issued_at": datetime.date.today().isoformat(), "revoked": a.id}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(sign(priv, payload), f, indent=1)
    print("Revocation list #%d written to %s (%d licences)." % (a.serial, a.out, len(a.id)))


def cmd_inspect(a):
    from cryptography.hazmat.primitives import serialization as s
    with open(a.public, "rb") as f:
        pub = s.load_pem_public_key(f.read())
    with open(a.file, "r", encoding="utf-8") as f:
        env = json.load(f)
    try:
        print(json.dumps(verify_envelope(env, pub), indent=1, ensure_ascii=False))
        print("SIGNATURE OK")
    except LicenseError as e:
        sys.exit("INVALID: " + e.message)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    k = sp.add_parser("keygen"); k.add_argument("--out", required=True); k.add_argument("--force", action="store_true"); k.set_defaults(f=cmd_keygen)
    i = sp.add_parser("issue"); i.add_argument("--private", required=True); i.add_argument("--request"); i.add_argument("--company")
    i.add_argument("--deployment-id"); i.add_argument("--days", type=int, default=365); i.add_argument("--expires"); i.add_argument("--perpetual", action="store_true")
    i.add_argument("--max-users", type=int, default=25); i.add_argument("--grace-days", type=int, default=14)
    i.add_argument("--features", default=""); i.add_argument("--edition", default="standard"); i.add_argument("--out"); i.set_defaults(f=cmd_issue)
    r = sp.add_parser("revoke"); r.add_argument("--private", required=True); r.add_argument("--serial", type=int, required=True)
    r.add_argument("--id", action="append", required=True); r.add_argument("--out", required=True); r.set_defaults(f=cmd_revoke)
    n = sp.add_parser("inspect"); n.add_argument("--public", required=True); n.add_argument("file"); n.set_defaults(f=cmd_inspect)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
