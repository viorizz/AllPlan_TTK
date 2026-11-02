"""Draw simple tool icons (PNG, pure Python) for the Allplan action bar and library previews."""
from __future__ import annotations

import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(ROOT, "PythonPartsActionbar", "terrain_toolkit")
LIB_DIR = os.path.join(ROOT, "Library", "Terrain Toolkit")


def png(path: str, w: int, h: int, pixel) -> None:
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(pixel(x / (w - 1), 1.0 - y / (h - 1)))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(data)


def hill(u, v):
    return 0.55 * math.exp(-((u - 0.6) ** 2 + (v - 0.55) ** 2) / 0.08) + 0.25 * u


def icon(kind: str):
    def px(u, v):
        h = hill(u, v)
        bg = (0, 0, 0, 0)
        border = min(u, v, 1 - u, 1 - v) < 0.04
        if border:
            return (60, 60, 60, 255)
        if kind == "mesh":
            gu, gv = (u * 6) % 1, (v * 6) % 1
            on = gu < 0.08 or gv < 0.08 or abs(gu - gv) < 0.08
            return (40, 110, 40, 255) if on else (190, 225, 170, 255)
        if kind == "contours":
            f = (h * 12) % 1
            return (130, 70, 20, 255) if f < 0.16 else (245, 235, 210, 255)
        if kind == "analysis":
            cols = [(26, 150, 65), (166, 217, 106), (255, 255, 191), (253, 174, 97), (215, 25, 28)]
            return cols[min(4, int(h / 0.75 * 5))] + (255,)
        if kind == "cutfill":
            d = h - 0.35
            return (215, 48, 39, 255) if d > 0.05 else ((69, 117, 180, 255) if d < -0.05 else (240, 240, 240, 255))
        if kind == "profile":
            y = 0.35 + 0.25 * math.sin(u * 5) * 0.6 + 0.1 * u
            if abs(v - y) < 0.04:
                return (20, 20, 20, 255)
            if (u * 5) % 1 < 0.03 or (v * 5) % 1 < 0.03:
                return (170, 170, 170, 255)
            return (250, 250, 250, 255)
        if kind == "drainage":
            if abs(v - (0.85 - 0.7 * u)) < 0.05 or abs(v - (0.2 + 0.6 * (u - 0.5) ** 2)) < 0.04:
                return (30, 90, 200, 255)
            return (225, 238, 250, 255)
        if kind == "platform":
            if 0.3 < u < 0.7 and 0.3 < v < 0.7:
                return (150, 150, 150, 255)
            if 0.18 < u < 0.82 and 0.18 < v < 0.82:
                return (210, 170, 120, 255)
            return (170, 210, 150, 255)
        if kind == "exchange":
            if abs(v - 0.5) < 0.06 and 0.2 < u < 0.8:
                return (40, 40, 160, 255)
            if abs(abs(u - 0.8) - (0.18 - abs(v - 0.5))) < 0.05 and u > 0.6:
                return (40, 40, 160, 255)
            return (235, 235, 250, 255)
        if kind == "diagnostics":
            r = math.hypot(u - 0.5, v - 0.5)
            if abs(r - 0.3) < 0.05 or (abs(u - 0.5) < 0.05 and 0.2 < v < 0.8 and False):
                return (200, 120, 0, 255)
            return (255, 245, 220, 255)
        return bg
    return px


TOOLS = {"TerrainMesh": "mesh", "TerrainContours": "contours", "TerrainAnalysis": "analysis",
         "TerrainCutFill": "cutfill", "TerrainProfile": "profile", "TerrainDrainage": "drainage",
         "TerrainPlatform": "platform", "TerrainExchange": "exchange", "TerrainDiagnostics": "diagnostics"}


def main() -> None:
    os.makedirs(ICON_DIR, exist_ok=True)
    for name, kind in TOOLS.items():
        png(os.path.join(ICON_DIR, f"{name}_24.png"), 24, 24, icon(kind))
        png(os.path.join(ICON_DIR, f"{name}_128.png"), 128, 128, icon(kind))
        png(os.path.join(LIB_DIR, f"{name}.png"), 128, 128, icon(kind))
    print("icons written")


if __name__ == "__main__":
    main()
