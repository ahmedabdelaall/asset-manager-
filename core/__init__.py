import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "VERSION"), "r", encoding="utf-8") as _f:
    VERSION = _f.read().strip()
PRODUCT = "asset-master"
