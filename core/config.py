# -*- coding: utf-8 -*-
"""Instance configuration.

The master code (this package) never contains company data. Everything that belongs to a
single company lives in its own *instance folder*: config, secrets, database, uploads, backups.
"""
import os
import json
import uuid
import secrets

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 8080,
    "https": False,                 # set true when served behind HTTPS (adds Secure cookie flag)
    "trust_proxy": False,           # trust X-Forwarded-For / X-Forwarded-Proto from a reverse proxy
    "session_idle_minutes": 30,
    "session_absolute_hours": 12,
    "max_upload_mb": 25,
    "backup_keep": 14,
    "auto_backup_hour": 2,          # local hour of day for the automatic daily backup (-1 disables)
    "license_server_url": "",       # optional: online revocation-list URL (offline mode works without it)
    "public_key_path": "",          # optional override for the vendor public key
    "allowed_hosts": [],            # optional: only answer requests for these Host names (e.g. ["assets.mycompany.com"])
}


class Instance:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        for sub in ("", "uploads", "backups", "logs"):
            os.makedirs(os.path.join(self.path, sub), exist_ok=True)
        self.config = dict(DEFAULTS)
        cfg_path = os.path.join(self.path, "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8-sig") as f:
                self.config.update(json.load(f))
        else:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULTS, f, indent=2)
        _b = lambda v: str(v).strip().lower() in ("1", "true", "yes", "on")
        _l = lambda v: [x.strip() for x in str(v).split(",") if x.strip()]
        for env, key, cast in (("AM_HOST", "host", str), ("AM_PORT", "port", int), ("AM_HTTPS", "https", _b),
                               ("AM_TRUST_PROXY", "trust_proxy", _b), ("AM_ALLOWED_HOSTS", "allowed_hosts", _l),
                               ("AM_PUBLIC_KEY_PATH", "public_key_path", str), ("AM_LICENSE_SERVER_URL", "license_server_url", str),
                               ("AM_SESSION_IDLE_MINUTES", "session_idle_minutes", int), ("AM_BACKUP_KEEP", "backup_keep", int)):
            if os.environ.get(env):
                self.config[key] = cast(os.environ[env])
        self.secret_key = self._load_secret()
        self.install_id = self._load_install_id()

    # --- secrets (never shipped with the master, never inside the database)
    def _load_secret(self):
        p = os.path.join(self.path, "secrets.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return bytes.fromhex(json.load(f)["secret_key"])
        key = secrets.token_bytes(32)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"secret_key": key.hex()}, f)
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
        return key

    def _load_install_id(self):
        p = os.path.join(self.path, "install_id")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
        iid = uuid.uuid4().hex
        with open(p, "w", encoding="utf-8") as f:
            f.write(iid)
        return iid

    @property
    def db_path(self):
        return os.path.join(self.path, "data.db")

    @property
    def uploads_dir(self):
        return os.path.join(self.path, "uploads")

    @property
    def backups_dir(self):
        return os.path.join(self.path, "backups")

    @property
    def setup_code_path(self):
        return os.path.join(self.path, "SETUP_CODE.txt")
