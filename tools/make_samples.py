"""Create the sample data in samples/ (synthetic but realistic site, metres).

    site_points_local.xyz        2 500 survey points near the Allplan origin (X Y Z, space separated)
    site_points_lambert93.csv    same site in real-world coordinates (Pt;X;Y;Z;Code, decimal comma)
    site_existing.xml            LandXML TIN of the existing ground (local coordinates)
    site_design.xml              LandXML design surface: platform + access ramp (local coordinates)
    site_dem_2m.asc              ESRI ASCII grid, 2 m cells (local coordinates)
"""
from __future__ import annotations

import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "PythonPartsScripts"))

from terrain_toolkit.core import io_formats  # noqa: E402
from terrain_toolkit.core.tin import build_tin  # noqa: E402

OUT = os.path.join(ROOT, "samples")
SHIFT = (651200.0, 6862400.0)  # Lambert-93 like offset


def ground(x: float, y: float) -> float:
    """Valley with a stream, a hill and a gentle general slope (120 x 90 m)."""
    z = 152.0 + 0.045 * x + 0.02 * y
    z += 7.5 * math.exp(-((x - 85) ** 2 + (y - 62) ** 2) / 450.0)          # hill
    z -= 2.2 * math.exp(-((y - 0.35 * x - 18) ** 2) / 30.0)                # stream valley
    z -= 1.0 * math.exp(-((x - 35) ** 2 + (y - 55) ** 2) / 60.0)           # small depression (ponding)
    z += 0.35 * math.sin(x / 6.0) * math.cos(y / 7.0)
    return round(z, 3)


def design(x: float, y: float, base: float) -> float:
    """Platform 40 x 25 m at 156.50 with 2:1 slopes back to ground, plus a 6 % ramp."""
    px0, px1, py0, py1, zp = 45.0, 85.0, 20.0, 45.0, 156.50
    dx = max(px0 - x, 0.0, x - px1)
    dy = max(py0 - y, 0.0, y - py1)
    d = math.hypot(dx, dy)
    zf = zp - d / 2.0
    zc = zp + d / 1.5
    return min(max(base, zf), zc)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    rnd = random.Random(42)
    pts = []
    for _ in range(2500):
        x, y = rnd.uniform(0, 120), rnd.uniform(0, 90)
        pts.append((round(x, 3), round(y, 3), ground(x, y)))
    for x in range(0, 121, 10):
        for y in (0, 90):
            pts.append((float(x), float(y), ground(x, y)))
    for y in range(0, 91, 10):
        for x in (0, 120):
            pts.append((float(x), float(y), ground(x, y)))
    io_formats.write_point_file(os.path.join(OUT, "site_points_local.xyz"), pts, " ", 3)
    with open(os.path.join(OUT, "site_points_lambert93.csv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("Pt;X;Y;Z;Code\n")
        for i, (x, y, z) in enumerate(pts):
            code = "TN"
            fh.write(f"{i + 1};{x + SHIFT[0]:.3f};{y + SHIFT[1]:.3f};{z:.3f};{code}\n".replace(".", ","))
    tin = build_tin(pts)
    io_formats.write_landxml(os.path.join(OUT, "site_existing.xml"), tin, "Existing ground")
    dpts = [(x, y, round(design(x, y, ground(x, y)), 3)) for x in range(0, 121, 2) for y in range(0, 91, 2)]
    dtin = build_tin(dpts)
    io_formats.write_landxml(os.path.join(OUT, "site_design.xml"), dtin, "Design platform")
    io_formats.write_ascii_grid(os.path.join(OUT, "site_dem_2m.asc"), tin, 2.0)
    print("samples written to", OUT)


if __name__ == "__main__":
    main()
