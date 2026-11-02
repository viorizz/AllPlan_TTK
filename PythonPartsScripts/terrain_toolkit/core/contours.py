"""Contour (isoline) extraction from a TIN, with smoothing, simplification and labels."""
from __future__ import annotations

import bisect
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import geom
from .tin import TIN

Point3 = Tuple[float, float, float]


@dataclass
class Contour:
    level: float
    points: List[Point3]
    closed: bool
    major: bool = False

    def length(self) -> float:
        return geom.polyline_length(self.points)


@dataclass
class Label:
    text: str
    x: float
    y: float
    z: float
    angle_deg: float
    level: float = 0.0


@dataclass
class ContourSet:
    contours: List[Contour] = field(default_factory=list)
    labels: List[Label] = field(default_factory=list)

    @property
    def major(self) -> List[Contour]:
        return [c for c in self.contours if c.major]

    @property
    def minor(self) -> List[Contour]:
        return [c for c in self.contours if not c.major]


def make_levels(zmin: float, zmax: float, interval: float, base: float = 0.0) -> List[float]:
    if interval <= 0:
        raise ValueError("contour interval must be > 0")
    k0 = math.ceil((zmin - base) / interval - 1e-9)
    k1 = math.floor((zmax - base) / interval + 1e-9)
    if k1 - k0 > 20000:
        raise ValueError(f"too many contour levels ({k1 - k0 + 1}); increase the interval")
    return [round(base + k * interval, 10) for k in range(k0, k1 + 1)]


def is_major(level: float, major_interval: float, base: float = 0.0) -> bool:
    if major_interval <= 0:
        return False
    r = (level - base) / major_interval
    return abs(r - round(r)) < 1e-6


def isolines(tin: TIN, levels: Sequence[float], values: Optional[Sequence[float]] = None) -> Dict[float, List[Tuple[List[Point3], bool]]]:
    """Raw isolines per level as (points, closed). ``values`` overrides vertex z as the scalar.

    The 3D z of each returned point is the surface elevation; the isoline follows ``values``.
    Lines are oriented with higher values on the left.
    """
    pts = tin.points
    val = values if values is not None else [p[2] for p in pts]
    levels = sorted(set(levels))
    if not levels:
        return {}
    buckets: Dict[int, List[int]] = defaultdict(list)
    for t, (a, b, c) in enumerate(tin.triangles):
        va, vb, vc = val[a], val[b], val[c]
        lo = min(va, vb, vc)
        hi = max(va, vb, vc)
        i0 = bisect.bisect_left(levels, lo)
        i1 = bisect.bisect_right(levels, hi)
        for k in range(i0, i1):
            buckets[k].append(t)

    out: Dict[float, List[Tuple[List[Point3], bool]]] = {}
    for k, tris in buckets.items():
        lev = levels[k]
        point_of: Dict[Tuple[int, int], Point3] = {}
        start_map: Dict[Tuple[int, int], int] = {}
        segs: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []

        def edge_point(u: int, v: int) -> Tuple[int, int]:
            key = (u, v) if u < v else (v, u)
            if key not in point_of:
                vu, vv = val[u], val[v]
                t = 0.0 if vv == vu else (lev - vu) / (vv - vu)
                t = min(max(t, 0.0), 1.0)
                pu, pv = pts[u], pts[v]
                point_of[key] = (pu[0] + (pv[0] - pu[0]) * t, pu[1] + (pv[1] - pu[1]) * t,
                                 pu[2] + (pv[2] - pu[2]) * t)
            return key

        for t in tris:
            tri = tin.triangles[t]
            above = [val[i] >= lev for i in tri]
            if all(above) or not any(above):
                continue
            exit_key = entry_key = None
            for j in range(3):
                u = tri[j]
                v = tri[(j + 1) % 3]
                if above[j] and not above[(j + 1) % 3]:
                    exit_key = edge_point(u, v)
                elif not above[j] and above[(j + 1) % 3]:
                    entry_key = edge_point(u, v)
            if exit_key is None or entry_key is None or exit_key == entry_key:
                continue
            start_map[exit_key] = len(segs)
            segs.append((exit_key, entry_key))

        ends = {s[1] for s in segs}
        used = [False] * len(segs)
        lines: List[Tuple[List[Point3], bool]] = []

        def walk(i0: int) -> Tuple[List[Point3], bool]:
            chain = [segs[i0][0]]
            i = i0
            closed = False
            while True:
                used[i] = True
                nxt_key = segs[i][1]
                chain.append(nxt_key)
                j = start_map.get(nxt_key)
                if j is None:
                    break
                if used[j]:
                    closed = j == i0
                    break
                i = j
            coords: List[Point3] = []
            for key in chain:
                p = point_of[key]
                if coords and abs(coords[-1][0] - p[0]) < 1e-12 and abs(coords[-1][1] - p[1]) < 1e-12:
                    continue
                coords.append(p)
            return coords, closed

        for i, s in enumerate(segs):
            if not used[i] and s[0] not in ends:
                lines.append(walk(i))
        for i in range(len(segs)):
            if not used[i]:
                lines.append(walk(i))
        out[lev] = [(c, cl) for c, cl in lines if len(c) >= 2]
    return out


def generate_contours(tin: TIN, interval: float, major_interval: float = 0.0, base: float = 0.0,
                      smooth_iterations: int = 0, simplify_tol: float = 0.0, min_length: float = 0.0,
                      zmin: Optional[float] = None, zmax: Optional[float] = None) -> ContourSet:
    lo, hi = tin.z_range()
    if zmin is not None:
        lo = max(lo, zmin)
    if zmax is not None:
        hi = min(hi, zmax)
    levels = make_levels(lo, hi, interval, base)
    raw = isolines(tin, levels)
    cs = ContourSet()
    for lev in sorted(raw):
        major = is_major(lev, major_interval, base)
        for pts, closed in raw[lev]:
            p = pts
            if simplify_tol > 0 and len(p) > 2:
                if closed:
                    ring = p[:-1] if p[0] == p[-1] else p
                    p2 = geom.douglas_peucker(ring + [ring[0]], simplify_tol)
                    p = list(p2)
                else:
                    p = geom.douglas_peucker(p, simplify_tol)
            if smooth_iterations > 0 and len(p) > 2:
                if closed:
                    ring = p[:-1] if (p[0][0] == p[-1][0] and p[0][1] == p[-1][1]) else p
                    sm = geom.chaikin(ring, smooth_iterations, closed=True)
                    p = sm + [sm[0]]
                else:
                    p = geom.chaikin(p, smooth_iterations, closed=False)
                p = [(q[0], q[1], lev) for q in p]
            else:
                p = [(q[0], q[1], lev) for q in p]
            if closed and (p[0][0] != p[-1][0] or p[0][1] != p[-1][1]):
                p = p + [p[0]]
            c = Contour(lev, p, closed, major)
            if min_length > 0 and c.length() < min_length:
                continue
            cs.contours.append(c)
    return cs


def place_labels(contours: Sequence[Contour], spacing: float, fmt: Callable[[float], str],
                 min_length: float = 0.0, only_major: bool = True) -> List[Label]:
    """Labels along contours every ``spacing`` (first at spacing/2)."""
    labels: List[Label] = []
    if spacing <= 0:
        return labels
    for c in contours:
        if only_major and not c.major:
            continue
        length = c.length()
        if length < max(min_length, 1e-9):
            continue
        n = max(1, int(length // spacing))
        step = length / n
        for i in range(n):
            st = step * (i + 0.5)
            (x, y), (ux, uy) = geom.offset_point_along([(p[0], p[1]) for p in c.points], st)
            labels.append(Label(fmt(c.level), x, y, c.level, geom.readable_angle_deg(ux, uy), c.level))
    return labels


def format_level(decimals: int) -> Callable[[float], str]:
    def fmt(v: float) -> str:
        return f"{v:.{max(0, decimals)}f}"
    return fmt
