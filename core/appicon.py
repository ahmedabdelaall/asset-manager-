# -*- coding: utf-8 -*-
"""Home-screen icon for the installable app, drawn in the company's brand colours without image libraries.

A full-bleed diagonal gradient (so it also works as a "maskable" icon that phones crop to a circle or squircle)
with a white QR-code mark kept inside the safe zone (central 50%)."""
import zlib
import struct
import threading

_CACHE, _LOCK = {}, threading.Lock()
SIZES = (180, 192, 512)

# 9x9 mark: three finder squares and a few modules - reads as "QR / scan"
MARK = ["1111.1111",
        "1..1.1..1",
        "1..1.1..1",
        "1111.1111",
        ".........",
        "1111.1.11",
        "1..1..1..",
        "1..1.11.1",
        "1111.1.11"]


def _rgb(h, fallback):
    h = (h or "").lstrip("#")
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) == 6 else fallback
    except ValueError:
        return fallback


def _chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png(size, primary="#6D4AF2", accent="#2F6BF0"):
    key = (size, primary, accent)
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    c1, c2 = _rgb(primary, (109, 74, 242)), _rgb(accent, (47, 107, 240))
    lo, span = 0.25 * size, 0.5 * size                     # mark area: central 50%
    cell = span / 9.0
    rows = []
    for y in range(size):
        row = bytearray(b"\x00")                           # filter: none
        my = int((y - lo) // cell) if lo <= y < lo + span else -1
        for x in range(size):
            mx = int((x - lo) // cell) if lo <= x < lo + span else -1
            if 0 <= mx < 9 and 0 <= my < 9 and MARK[my][mx] == "1":
                row += b"\xff\xff\xff"
            else:
                t = (x + y) / (2.0 * (size - 1))
                row += bytes(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        rows.append(bytes(row))
    data = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + \
        _chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + _chunk(b"IEND", b"")
    with _LOCK:
        if len(_CACHE) > 24:
            _CACHE.clear()
        _CACHE[key] = data
    return data
