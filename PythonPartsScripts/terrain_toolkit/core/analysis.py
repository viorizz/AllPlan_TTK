"""Surface analysis: slope, aspect and elevation-band maps.

Results are expressed as *classes*. Each class carries
    * the 3D triangles that belong to it (for a coloured 3D mesh) and
    * dissolved 2D regions (outer ring + holes) for coloured 2D fillings.
"""
from __future__ import annotations

import bisect
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Hashable, List, Optional, Sequence, Tuple

from . import geom
from .tin import TIN

Point3 = Tuple[float, float, float]
Region = Tuple[List[Tuple[float, float]], List[List[Tuple[float, float]]]]


@dataclass
class AnalysisClass:
    index: int
    label: str
    lower: Optional[float]
    upper: Optional[float]
    color: Tuple[int, int, int] = (128, 128, 128)
    triangles: List[Tuple[Point3, Point3, Point3]] = field(default_factory=list)
    regions: List[Region] = field(default_factory=list)
    area_2d: float = 0.0
    area_3d: float = 0.0


@dataclass
class AnalysisResult:
    kind: str
    unit: str
    classes: List[AnalysisClass]
    total_area_2d: float = 0.0

    def table(self) -> List[Tuple[str, float, float]]:
        tot = self.total_area_2d or 1.0
        return [(c.label, c.area_2d, 100.0 * c.area_2d / tot) for c in self.classes]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def parse_breaks(text: str) -> List[float]:
    """'0;5;10;15' or '0|5|10' or '0 5 10' -> sorted unique floats."""
    raw = text.replace("|", ";").replace(" ", ";").replace("\t", ";")
    vals = []
    for tok in raw.split(";"):
        tok = tok.strip()
        if not tok:
            continue
        vals.append(float(tok.replace(",", ".")))
    return sorted(set(vals))


def class_labels(breaks: Sequence[float], unit: str, open_ends: bool = True, decimals: int = 1) -> List[Tuple[str, Optional[float], Optional[float]]]:
    out = []
    f = f"{{:.{decimals}f}}"
    if open_ends:
        out.append((f"< {f.format(breaks[0])} {unit}".strip(), None, breaks[0]))
    for i in range(len(breaks) - 1):
        out.append((f"{f.format(breaks[i])} - {f.format(breaks[i + 1])} {unit}".strip(), breaks[i], breaks[i + 1]))
    if open_ends:
        out.append((f"> {f.format(breaks[-1])} {unit}".strip(), breaks[-1], None))
    return out


def dissolve(polygons: Sequence[Sequence[Hashable]], coords: Dict[Hashable, Tuple[float, float]]) -> List[Region]:
    """Merge adjacent CCW polygons (given as vertex keys) into regions with holes."""
    count: Dict[Tuple[Hashable, Hashable], int] = defaultdict(int)
    for poly in polygons:
        n = len(poly)
        for i in range(n):
            count[(poly[i], poly[(i + 1) % n])] += 1
    out_edges: Dict[Hashable, List[Hashable]] = defaultdict(list)
    for (u, v), c in count.items():
        if (v, u) in count:
            continue
        out_edges[u].append(v)

    rings: List[List[Tuple[float, float]]] = []
    used = set()
    for u0 in list(out_edges.keys()):
        for v0 in out_edges[u0]:
            if (u0, v0) in used:
                continue
            ring_keys = [u0]
            used.add((u0, v0))
            prev, cur = u0, v0
            guard = 0
            while cur != u0 and guard < 10_000_000:
                guard += 1
                ring_keys.append(cur)
                cands = [w for w in out_edges.get(cur, []) if (cur, w) not in used]
                if not cands:
                    break
                if len(cands) > 1:
                    # choose the left-most turn so that rings stay simple at pinch vertices
                    px, py = coords[prev]
                    cx, cy = coords[cur]
                    ang_in = math.atan2(cy - py, cx - px)

                    def turn(w):
                        wx, wy = coords[w]
                        a = math.atan2(wy - cy, wx - cx) - ang_in
                        while a <= -math.pi:
                            a += 2 * math.pi
                        while a > math.pi:
                            a -= 2 * math.pi
                        return a
                    cands.sort(key=turn, reverse=True)
                w = cands[0]
                used.add((cur, w))
                prev, cur = cur, w
            if len(ring_keys) >= 3:
                rings.append([coords[k] for k in ring_keys])

    outers = [r for r in rings if geom.polygon_area(r) > 0]
    holes = [r for r in rings if geom.polygon_area(r) < 0]
    regions: List[Region] = [(o, []) for o in outers]
    areas = [geom.polygon_area(o) for o in outers]
    for h in holes:
        hx, hy = h[0]
        # use a point slightly inside the hole edge midpoint to avoid vertex coincidence
        if len(h) >= 2:
            hx = (h[0][0] + h[1][0]) / 2.0
            hy = (h[0][1] + h[1][1]) / 2.0
        best = -1
        best_area = math.inf
        for i, o in enumerate(outers):
            if areas[i] < best_area and geom.point_in_polygon(hx, hy, o):
                best = i
                best_area = areas[i]
        if best >= 0:
            regions[best][1].append(h)
    return regions


def _tri_area2d(a, b, c) -> float:
    return 0.5 * abs(geom.orient(a[0], a[1], b[0], b[1], c[0], c[1]))


# ---------------------------------------------------------------------------
# per-triangle classification (slope / aspect)
# ---------------------------------------------------------------------------
def classify_triangles(tin: TIN, value_fn: Callable[[int], Optional[float]],
                       classes: List[AnalysisClass], kind: str, unit: str,
                       dissolve_regions: bool = True,
                       bin_fn: Optional[Callable[[Optional[float]], int]] = None) -> AnalysisResult:
    pts = tin.points
    groups: Dict[int, List[int]] = defaultdict(list)
    for t in range(len(tin.triangles)):
        v = value_fn(t)
        idx = bin_fn(v) if bin_fn else _bin(v, classes)
        if idx < 0:
            continue
        groups[idx].append(t)
    total = 0.0
    for idx, tris in groups.items():
        cls = classes[idx]
        polys = []
        for t in tris:
            a, b, c = tin.triangles[t]
            pa, pb, pc = pts[a], pts[b], pts[c]
            cls.triangles.append((pa, pb, pc))
            ar = _tri_area2d(pa, pb, pc)
            cls.area_2d += ar
            cls.area_3d += geom.triangle_area_3d(pa, pb, pc)
            polys.append((a, b, c))
        total += cls.area_2d
        if dissolve_regions:
            coords = {i: (pts[i][0], pts[i][1]) for poly in polys for i in poly}
            cls.regions = dissolve(polys, coords)
    return AnalysisResult(kind, unit, classes, total)


def _bin(v: Optional[float], classes: List[AnalysisClass]) -> int:
    if v is None:
        return -1
    for c in classes:
        lo_ok = c.lower is None or v >= c.lower
        hi_ok = c.upper is None or v < c.upper
        if lo_ok and hi_ok:
            return c.index
    return -1


def slope_analysis(tin: TIN, breaks: Sequence[float], unit: str = "%", colors: Optional[Sequence[Tuple[int, int, int]]] = None,
                   dissolve_regions: bool = True) -> AnalysisResult:
    """Slope classes. unit: '%' (percent) or 'deg' (degrees)."""
    labels = class_labels(breaks, "%" if unit == "%" else "°", open_ends=True)
    # values below the first break cannot exist for slopes >= 0 when first break is 0
    classes = [AnalysisClass(i, lab, lo, hi) for i, (lab, lo, hi) in enumerate(labels)]
    if breaks and breaks[0] <= 0:
        classes = classes[1:]
        for i, c in enumerate(classes):
            c.index = i
    _apply_colors(classes, colors)

    def val(t: int) -> float:
        s = tin.triangle_slope(t)
        return s * 100.0 if unit == "%" else math.degrees(math.atan(s))

    return classify_triangles(tin, val, classes, "slope", unit, dissolve_regions)


ASPECT_NAMES_8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def aspect_analysis(tin: TIN, sectors: int = 8, flat_slope_pct: float = 1.0,
                    colors: Optional[Sequence[Tuple[int, int, int]]] = None,
                    dissolve_regions: bool = True) -> AnalysisResult:
    """Exposure classes (direction the slope faces). Triangles flatter than flat_slope_pct are 'Flat'."""
    if sectors not in (4, 8, 16):
        sectors = 8
    names = {4: ["N", "E", "S", "W"], 8: ASPECT_NAMES_8,
             16: ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]}[sectors]
    classes = [AnalysisClass(0, "Flat", None, None)]
    width = 360.0 / sectors
    for i, n in enumerate(names):
        lo = (i * width - width / 2.0) % 360.0
        classes.append(AnalysisClass(i + 1, n, lo, (lo + width) % 360.0))
    _apply_colors(classes, colors)

    def val(t: int) -> Optional[float]:
        if tin.triangle_slope(t) * 100.0 < flat_slope_pct:
            return -1.0
        a = tin.triangle_aspect(t)
        return -1.0 if a is None else a

    def bin_fn(v: Optional[float]) -> int:
        if v is None:
            return -1
        if v < 0:
            return 0
        return 1 + int(((v + width / 2.0) % 360.0) // width) % sectors

    return classify_triangles(tin, val, classes, "aspect", "°", dissolve_regions, bin_fn)


def _apply_colors(classes: List[AnalysisClass], colors: Optional[Sequence[Tuple[int, int, int]]]) -> None:
    if not colors:
        return
    for i, c in enumerate(classes):
        c.color = tuple(colors[i % len(colors)])  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# exact band slicing (elevation bands, cut/fill depth bands)
# ---------------------------------------------------------------------------
def slice_bands(tin: TIN, levels: Sequence[float], values: Optional[Sequence[float]] = None,
                dissolve_regions: bool = True) -> Tuple[List[List[Tuple[Point3, Point3, Point3]]], List[List[Region]], List[float], List[float]]:
    """Cut every triangle exactly at ``levels`` of a scalar field (default: elevation).

    Returns (triangles per band, regions per band, 2D area per band, 3D area per band) where
    band i covers [levels[i-1], levels[i]) and band 0 is below levels[0], last is above levels[-1].
    """
    pts = tin.points
    val = list(values) if values is not None else [p[2] for p in pts]
    levels = sorted(set(levels))
    nb = len(levels) + 1
    band_tris: List[List[Tuple[Point3, Point3, Point3]]] = [[] for _ in range(nb)]
    band_polys: List[List[List[Hashable]]] = [[] for _ in range(nb)]
    area2 = [0.0] * nb
    area3 = [0.0] * nb
    coord: Dict[Hashable, Point3] = {}

    def vkey(i: int) -> Hashable:
        if i not in coord:
            coord[i] = pts[i]
        return i

    def ekey(u: int, v: int, k: int) -> Hashable:
        a, b = (u, v) if u < v else (v, u)
        key = ("e", a, b, k)
        if key not in coord:
            lev = levels[k]
            va, vb = val[a], val[b]
            t = 0.0 if vb == va else (lev - va) / (vb - va)
            t = min(max(t, 0.0), 1.0)
            pa, pb = pts[a], pts[b]
            coord[key] = (pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t, pa[2] + (pb[2] - pa[2]) * t)
        return key

    def band_of(v: float) -> int:
        return bisect.bisect_right(levels, v)

    for (a, b, c) in tin.triangles:
        tri = (a, b, c)
        vs = [val[a], val[b], val[c]]
        bands = [band_of(v) for v in vs]
        bmin = min(bands)
        bmax = max(bands)
        if bmin == bmax:
            poly_keys = [vkey(a), vkey(b), vkey(c)]
            _emit(poly_keys, bmin, coord, band_tris, band_polys, area2, area3)
            continue
        # polygon of the triangle as list of (key, value); insert crossing points on edges
        ring: List[Tuple[Hashable, float]] = []
        for j in range(3):
            u = tri[j]
            w = tri[(j + 1) % 3]
            ring.append((vkey(u), val[u]))
            vu, vw = val[u], val[w]
            if vu == vw:
                continue
            lo, hi = (vu, vw) if vu < vw else (vw, vu)
            ks = list(range(bisect.bisect_right(levels, lo), bisect.bisect_left(levels, hi)))
            if vu > vw:
                ks.reverse()
            for k in ks:
                if lo < levels[k] < hi:
                    ring.append((ekey(u, w, k), levels[k]))
        for band in range(bmin, bmax + 1):
            lo = levels[band - 1] if band > 0 else -math.inf
            hi = levels[band] if band < len(levels) else math.inf
            poly = _clip_ring(ring, lo, hi)
            if len(poly) >= 3:
                _emit(poly, band, coord, band_tris, band_polys, area2, area3)

    regions: List[List[Region]] = [[] for _ in range(nb)]
    if dissolve_regions:
        coords2 = {k: (p[0], p[1]) for k, p in coord.items()}
        for i in range(nb):
            if band_polys[i]:
                regions[i] = dissolve(band_polys[i], coords2)
    return band_tris, regions, area2, area3


def _clip_ring(ring: List[Tuple[Hashable, float]], lo: float, hi: float) -> List[Hashable]:
    """Keep ring vertices whose value is in [lo, hi] - crossing points were pre-inserted."""
    out = []
    eps = 1e-12
    for key, v in ring:
        if lo - eps <= v <= hi + eps:
            if not out or out[-1] != key:
                out.append(key)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def _emit(poly_keys, band, coord, band_tris, band_polys, area2, area3) -> None:
    p0 = coord[poly_keys[0]]
    pts2 = [coord[k] for k in poly_keys]
    if abs(geom.polygon_area(pts2)) < 1e-14:
        return
    band_polys[band].append(list(poly_keys))
    for i in range(1, len(poly_keys) - 1):
        p1 = coord[poly_keys[i]]
        p2 = coord[poly_keys[i + 1]]
        a2 = _tri_area2d(p0, p1, p2)
        if a2 <= 0:
            continue
        band_tris[band].append((p0, p1, p2))
        area2[band] += a2
        area3[band] += geom.triangle_area_3d(p0, p1, p2)


def elevation_bands(tin: TIN, breaks: Sequence[float], colors: Optional[Sequence[Tuple[int, int, int]]] = None,
                    dissolve_regions: bool = True, unit: str = "m", decimals: int = 2) -> AnalysisResult:
    breaks = sorted(set(breaks))
    band_tris, regions, a2, a3 = slice_bands(tin, breaks, None, dissolve_regions)
    labels = class_labels(breaks, unit, open_ends=True, decimals=decimals)
    classes = []
    for i, (lab, lo, hi) in enumerate(labels):
        c = AnalysisClass(i, lab, lo, hi, triangles=band_tris[i], regions=regions[i], area_2d=a2[i], area_3d=a3[i])
        classes.append(c)
    _apply_colors(classes, colors)
    classes = [c for c in classes if c.triangles]
    return AnalysisResult("elevation", unit, classes, sum(a2))


def auto_breaks(zmin: float, zmax: float, count: int) -> List[float]:
    """'Nice' class breaks covering [zmin, zmax] with about ``count`` classes."""
    if count < 1 or zmax <= zmin:
        return [zmin]
    raw = (zmax - zmin) / count
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if step >= raw:
            break
    start = math.floor(zmin / step) * step
    out = []
    v = start + step
    while v < zmax - 1e-9:
        out.append(round(v, 10))
        v += step
    return out or [round((zmin + zmax) / 2.0, 10)]
