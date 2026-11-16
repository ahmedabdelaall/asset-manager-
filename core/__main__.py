# -*- coding: utf-8 -*-
"""Run with:  python -m core   (instance folder from AM_INSTANCE, default ./instances/default)"""
import os
from .server import serve

if __name__ == "__main__":
    serve(os.environ.get("AM_INSTANCE", os.path.join("instances", "default")))
