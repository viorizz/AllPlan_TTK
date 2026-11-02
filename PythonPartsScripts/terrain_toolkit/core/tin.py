"""Triangulated Irregular Network (TIN) - the terrain surface model.

All coordinates are stored in *model units* chosen by the caller (the
Allplan layer uses metres internally and converts to millimetres when it
creates elements).
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import geom
from .delaunay import ConstrainedTriangulation, TriangulationError

Point3 = Tuple[float, float, float]
Tri = Tuple[int, int, int]


class TerrainError(Exception):
    """User-facing error with an explanation of what went wrong."""


# ---------------------------------------------------------------------------
# spatial grid index
# ---------------------------------------------------------------------------
class GridIndex:
    """Uniform grid of triangle ids for fast point location."""

    def __init__(self, points: Sequence[Point3], triangles: Sequence[Tri], target_per_cell: float = 2.0):
        self.points = points
        self.triangles = triangles
        if not triangles:
            self.x0 = self.y0 = 0.0
            self.cell = 1.0
            self.nx = self.ny = 1
            self.cells: Dict[int, List[int]] = {}
            return
        used = {i for t in triangles for i in t}
        xs = [points[i][0] for i in used]
        ys = [points[i][1] for i in used]
        self.x0 = min(xs)
        self.y0 = min(ys)
        w = max(xs) - self.x0
        h = max(ys) - self.y0
        area = max(w * h, 1e-12)
        cell = math.sqrt(area * target_per_cell / max(len(triangles), 1))
        if cell <= 0:
            cell = max(w, h, 1.0)
        self.cell = cell
        self.nx = max(1, int(w / cell) + 1)
        self.ny = max(1, int(h / cell) + 1)
        cells: Dict[int, List[int]] = defaultdict(list)
        x0 = self.x0
        y0 = self.y0
        nx = self.nx
        ny = self.ny
        for t, (a, b, c) in enumerate(triangles):
            pa = points[a]
            pb = points[b]
            pc = points[c]
            ix0 = int((min(pa[0], pb[0], pc[0]) - x0) / cell)
            ix1 = int((max(pa[0], pb[0], pc[0]) - x0) / cell)
            iy0 = int((min(pa[1], pb[1], pc[1]) - y0) / cell)
            iy1 = int((max(pa[1], pb[1], pc[1]) - y0) / cell)
            ix0 = max(ix0, 0)
            iy0 = max(iy0, 0)
            ix1 = min(ix1, nx - 1)
            iy1 = min(iy1, ny - 1)
            for iy in range(iy0, iy1 + 1):
                base = iy * nx
                for ix in range(ix0, ix1 + 1):
                    cells[base + ix].append(t)
        self.cells = cells

    def candidates(self, x: float, y: float) -> List[int]:
        ix = int((x - self.x0) / self.cell)
        iy = int((y - self.y0) / self.cell)
        if ix < 0 or iy < 0 or ix >= self.nx or iy >= self.ny:
            return []
        return self.cells.get(iy * self.nx + ix, [])

    def cells_in_box(self, xmin: float, ymin: float, xmax: float, ymax: float) -> Set[int]:
        ix0 = max(0, int((xmin - self.x0) / self.cell))
        iy0 = max(0, int((ymin - self.y0) / self.cell))
        ix1 = min(self.nx - 1, int((xmax - self.x0) / self.cell))
        iy1 = min(self.ny - 1, int((ymax - self.y0) / self.cell))
        out: Set[int] = set()
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                out.update(self.cells.get(iy * self.nx + ix, ()))
        return out

    def triangles_along_segment(self, ax: float, ay: float, bx: float, by: float) -> Set[int]:
        """Triangle ids in grid cells touched by segment ab (sampled walk)."""
        length = math.hypot(bx - ax, by - ay)
        steps = max(1, int(length / (self.cell * 0.5)) + 1)
        out: Set[int] = set()
        seen = set()
        for k in range(steps + 1):
            t = k / steps
            x = ax + (bx - ax) * t
            y = ay + (by - ay) * t
            ix = int((x - self.x0) / self.cell)
            iy = int((y - self.y0) / self.cell)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cx = ix + dx
                    cy = iy + dy
                    if 0 <= cx < self.nx and 0 <= cy < self.ny:
                        key = cy * self.nx + cx
                        if key not in seen:
                            seen.add(key)
                            out.update(self.cells.get(key, ()))
        return out


def _barycentric(px, py, a, b, c):
    det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if det == 0.0:
        return None
    l1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / det
    l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / det
    return l1, l2, 1.0 - l1 - l2


# ---------------------------------------------------------------------------
# TIN
# ---------------------------------------------------------------------------
class TIN:
    """Triangulated terrain surface."""

    def __init__(self, points: Sequence[Point3], triangles: Sequence[Tri], compact: bool = True,
                 breaklines: Optional[List[List[Point3]]] = None):
        pts = [(float(p[0]), float(p[1]), float(p[2])) for p in points]
        tris = [tuple(int(i) for i in t) for t in triangles]
        # make every triangle counter-clockwise and drop degenerate ones
        clean: List[Tri] = []
        for a, b, c in tris:
            if a == b or b == c or a == c:
                continue
            o = geom.orient(pts[a][0], pts[a][1], pts[b][0], pts[b][1], pts[c][0], pts[c][1])
            if o == 0.0:
                continue
            clean.append((a, b, c) if o > 0 else (a, c, b))
        if compact:
            used = sorted({i for t in clean for i in t})
            remap = {old: new for new, old in enumerate(used)}
            pts = [pts[i] for i in used]
            clean = [(remap[a], remap[b], remap[c]) for a, b, c in clean]
        self.points: List[Point3] = pts
        self.triangles: List[Tri] = clean
        self.breaklines: List[List[Point3]] = breaklines or []
        self._index: Optional[GridIndex] = None
        self._tri_nbrs: Optional[List[List[int]]] = None
        self._vert_nbrs: Optional[List[Set[int]]] = None
        self.info: Dict[str, object] = {}

    # -- basic properties ---------------------------------------------------
    def __len__(self) -> int:
        return len(self.triangles)

    @property
    def is_empty(self) -> bool:
        return not self.triangles

    def bbox(self) -> Tuple[float, float, float, float]:
        return geom.bbox(self.points)

    def z_range(self) -> Tuple[float, float]:
        zs = [p[2] for p in self.points]
        return (min(zs), max(zs)) if zs else (0.0, 0.0)

    def tri_points(self, t: int) -> Tuple[Point3, Point3, Point3]:
        a, b, c = self.triangles[t]
        return self.points[a], self.points[b], self.points[c]

    def area_2d(self) -> float:
        total = 0.0
        for a, b, c in self.triangles:
            pa, pb, pc = self.points[a], self.points[b], self.points[c]
            total += 0.5 * geom.orient(pa[0], pa[1], pb[0], pb[1], pc[0], pc[1])
        return total

    def area_3d(self) -> float:
        return sum(geom.triangle_area_3d(*self.tri_points(t)) for t in range(len(self.triangles)))

    # -- topology -----------------------------------------------------------
    def edge_map(self) -> Dict[Tuple[int, int], List[int]]:
        emap: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        for t, (a, b, c) in enumerate(self.triangles):
            for u, v in ((a, b), (b, c), (c, a)):
                emap[(u, v) if u < v else (v, u)].append(t)
        return emap

    def edges(self) -> List[Tuple[int, int]]:
        return list(self.edge_map().keys())

    def triangle_neighbors(self) -> List[List[int]]:
        """For each triangle, neighbour across edge (a,b), (b,c), (c,a) or -1."""
        if self._tri_nbrs is None:
            directed: Dict[Tuple[int, int], int] = {}
            for t, (a, b, c) in enumerate(self.triangles):
                directed[(a, b)] = t
                directed[(b, c)] = t
                directed[(c, a)] = t
            nbrs = []
            for a, b, c in self.triangles:
                nbrs.append([directed.get((b, a), -1), directed.get((c, b), -1), directed.get((a, c), -1)])
            self._tri_nbrs = nbrs
        return self._tri_nbrs

    def vertex_neighbors(self) -> List[Set[int]]:
        if self._vert_nbrs is None:
            nb: List[Set[int]] = [set() for _ in self.points]
            for a, b, c in self.triangles:
                nb[a].update((b, c))
                nb[b].update((a, c))
                nb[c].update((a, b))
            self._vert_nbrs = nb
        return self._vert_nbrs

    def boundary_rings(self) -> List[List[int]]:
        """Closed outline rings (vertex ids) of the TIN, outer and inner."""
        nxt: Dict[int, List[int]] = defaultdict(list)
        directed = set()
        for a, b, c in self.triangles:
            directed.update(((a, b), (b, c), (c, a)))
        for (u, v) in directed:
            if (v, u) not in directed:
                nxt[u].append(v)
        rings = []
        visited: Set[Tuple[int, int]] = set()
        for start in list(nxt.keys()):
            for v0 in nxt[start]:
                if (start, v0) in visited:
                    continue
                ring = [start]
                visited.add((start, v0))
                cur = v0
                guard = 0
                while cur != start and guard < len(self.points) + 5:
                    guard += 1
                    ring.append(cur)
                    cand = [w for w in nxt[cur] if (cur, w) not in visited]
                    if not cand:
                        break
                    w = cand[0]
                    visited.add((cur, w))
                    cur = w
                if len(ring) >= 3:
                    rings.append(ring)
        return rings

    # -- queries ------------------------------------------------------------
    @property
    def index(self) -> GridIndex:
        if self._index is None:
            self._index = GridIndex(self.points, self.triangles)
        return self._index

    def locate(self, x: float, y: float) -> int:
        pts = self.points
        best_t = -1
        best_err = 1e-9
        for t in self.index.candidates(x, y):
            a, b, c = self.triangles[t]
            bc = _barycentric(x, y, pts[a], pts[b], pts[c])
            if bc is None:
                continue
            m = min(bc)
            if m >= 0.0:
                return t
            if -m < best_err:
                best_err = -m
                best_t = t
        return best_t

    def z_at(self, x: float, y: float) -> Optional[float]:
        t = self.locate(x, y)
        if t < 0:
            return None
        a, b, c = self.triangles[t]
        pa, pb, pc = self.points[a], self.points[b], self.points[c]
        bc = _barycentric(x, y, pa, pb, pc)
        if bc is None:
            return None
        return bc[0] * pa[2] + bc[1] * pb[2] + bc[2] * pc[2]

    def triangle_gradient(self, t: int) -> Tuple[float, float]:
        """(dz/dx, dz/dy) of triangle t."""
        pa, pb, pc = self.tri_points(t)
        nx, ny, nz = geom.triangle_normal(pa, pb, pc)
        if nz == 0.0:
            return 0.0, 0.0
        return -nx / nz, -ny / nz

    def triangle_slope(self, t: int) -> float:
        """Slope as ratio (rise/run). Multiply by 100 for percent."""
        gx, gy = self.triangle_gradient(t)
        return math.hypot(gx, gy)

    def triangle_aspect(self, t: int) -> Optional[float]:
        """Downhill azimuth in degrees, clockwise from north (Y+). None for flat triangles."""
        gx, gy = self.triangle_gradient(t)
        if gx == 0.0 and gy == 0.0:
            return None
        az = math.degrees(math.atan2(-gx, -gy))
        return az % 360.0

    def intersect_segment(self, a: Sequence[float], b: Sequence[float]) -> List[Tuple[float, float, float, float]]:
        """Exact crossing points of a plan segment with TIN edges.

        Returns a list of (t, x, y, z) sorted by t (0..1 along the segment), including the
        end points when they lie on the surface.
        """
        ax, ay = a[0], a[1]
        bx, by = b[0], b[1]
        out: Dict[float, Tuple[float, float, float, float]] = {}
        pts = self.points
        for t_id in self.index.triangles_along_segment(ax, ay, bx, by):
            tri = self.triangles[t_id]
            for k in range(3):
                p = pts[tri[k]]
                q = pts[tri[(k + 1) % 3]]
                res = geom.segment_intersection(ax, ay, bx, by, p[0], p[1], q[0], q[1])
                if res is None:
                    continue
                s, u = res
                key = round(s, 10)
                if key not in out:
                    out[key] = (s, ax + (bx - ax) * s, ay + (by - ay) * s, p[2] + (q[2] - p[2]) * u)
        for s in (0.0, 1.0):
            x = ax + (bx - ax) * s
            y = ay + (by - ay) * s
            z = self.z_at(x, y)
            if z is not None:
                out[round(s, 10)] = (s, x, y, z)
        return [out[k] for k in sorted(out)]

    def drape_polyline(self, pts: Sequence[Sequence[float]]) -> List[List[Point3]]:
        """Project a plan polyline on the surface. Returns one or more 3D parts (gaps off-surface)."""
        parts: List[List[Point3]] = []
        cur: List[Point3] = []
        for i in range(len(pts) - 1):
            hits = self.intersect_segment(pts[i], pts[i + 1])
            if not hits:
                if cur:
                    parts.append(cur)
                    cur = []
                continue
            for (s, x, y, z) in hits:
                if cur and abs(cur[-1][0] - x) < 1e-9 and abs(cur[-1][1] - y) < 1e-9:
                    continue
                if cur and s > 0.0 and self.z_at((cur[-1][0] + x) / 2, (cur[-1][1] + y) / 2) is None:
                    parts.append(cur)
                    cur = []
                cur.append((x, y, z))
        if cur:
            parts.append(cur)
        return [p for p in parts if len(p) >= 2]

    def vertical_distance_stats(self, samples: Iterable[Point3]) -> Dict[str, float]:
        """Statistics of (sample.z - surface.z), e.g. to check a model against control points."""
        diffs = []
        for p in samples:
            z = self.z_at(p[0], p[1])
            if z is not None:
                diffs.append(p[2] - z)
        if not diffs:
            return {"count": 0}
        n = len(diffs)
        mean = sum(diffs) / n
        rms = math.sqrt(sum(d * d for d in diffs) / n)
        return {"count": n, "mean": mean, "rms": rms, "min": min(diffs), "max": max(diffs)}

    # -- transforms -----------------------------------------------------------
    def transformed(self, scale: float = 1.0, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> "TIN":
        pts = [((p[0] + dx) * scale, (p[1] + dy) * scale, (p[2] + dz) * scale) for p in self.points]
        return TIN(pts, self.triangles, compact=False,
                   breaklines=[[((p[0] + dx) * scale, (p[1] + dy) * scale, (p[2] + dz) * scale) for p in bl]
                               for bl in self.breaklines])

    def summary(self) -> Dict[str, float]:
        xmin, ymin, xmax, ymax = self.bbox() if self.points else (0, 0, 0, 0)
        zmin, zmax = self.z_range()
        return {
            "points": len(self.points),
            "triangles": len(self.triangles),
            "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax,
            "zmin": zmin, "zmax": zmax,
            "area_2d": self.area_2d(),
            "area_3d": self.area_3d(),
        }


# ---------------------------------------------------------------------------
# building
# ---------------------------------------------------------------------------
def _dedupe(points: Sequence[Point3], tol: float) -> Tuple[List[Point3], List[int]]:
    """Merge points closer than tol (plan). Returns unique points and old->new map."""
    if tol <= 0:
        tol = 1e-9
    cell = tol
    grid: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    unique: List[Point3] = []
    remap: List[int] = []
    t2 = tol * tol
    for p in points:
        ix = int(math.floor(p[0] / cell))
        iy = int(math.floor(p[1] / cell))
        found = -1
        for gx in (ix - 1, ix, ix + 1):
            for gy in (iy - 1, iy, iy + 1):
                for j in grid.get((gx, gy), ()):
                    q = unique[j]
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 <= t2:
                        found = j
                        break
                if found >= 0:
                    break
            if found >= 0:
                break
        if found < 0:
            found = len(unique)
            unique.append((float(p[0]), float(p[1]), float(p[2])))
            grid[(ix, iy)].append(found)
        remap.append(found)
    return unique, remap


def _split_crossing_lines(lines: List[List[Point3]]) -> List[List[Point3]]:
    """Insert vertices where line segments cross each other.

    Lines earlier in the list have priority: the crossing vertex takes their elevation.
    """
    segs = []
    for li, line in enumerate(lines):
        for si in range(len(line) - 1):
            segs.append((li, si, line[si], line[si + 1]))
    if len(segs) < 2:
        return lines
    xs = [s[2][0] for s in segs] + [s[3][0] for s in segs]
    ys = [s[2][1] for s in segs] + [s[3][1] for s in segs]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-9)
    cell = span / max(1.0, math.sqrt(len(segs)))
    grid: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for k, (_, _, a, b) in enumerate(segs):
        for ix in range(int(min(a[0], b[0]) // cell), int(max(a[0], b[0]) // cell) + 1):
            for iy in range(int(min(a[1], b[1]) // cell), int(max(a[1], b[1]) // cell) + 1):
                grid[(ix, iy)].append(k)
    inserts: Dict[Tuple[int, int], List[Tuple[float, Point3]]] = defaultdict(list)
    checked = set()
    for bucket in grid.values():
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                k1, k2 = bucket[i], bucket[j]
                pair = (k1, k2) if k1 < k2 else (k2, k1)
                if pair in checked:
                    continue
                checked.add(pair)
                l1, s1, a, b = segs[k1]
                l2, s2, c, d = segs[k2]
                if l1 == l2 and abs(s1 - s2) <= 1:
                    continue
                res = geom.segment_intersection(a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1])
                if res is None:
                    continue
                t, u = res
                if t <= 1e-9 or t >= 1 - 1e-9 or u <= 1e-9 or u >= 1 - 1e-9:
                    continue
                x = a[0] + (b[0] - a[0]) * t
                y = a[1] + (b[1] - a[1]) * t
                z1 = a[2] + (b[2] - a[2]) * t
                z2 = c[2] + (d[2] - c[2]) * u
                if l1 == l2:
                    zc = (z1 + z2) / 2.0
                else:
                    zc = z1 if l1 < l2 else z2
                p = (x, y, zc)
                inserts[(l1, s1)].append((t, p))
                inserts[(l2, s2)].append((u, p))
    if not inserts:
        return lines
    out = []
    for li, line in enumerate(lines):
        new = [line[0]]
        for si in range(len(line) - 1):
            for _, p in sorted(inserts.get((li, si), []), key=lambda tp: tp[0]):
                new.append(p)
            new.append(line[si + 1])
        out.append(new)
    return out


def _interp_missing_z(ring: List[Tuple[float, float, Optional[float]]], points: Sequence[Point3]) -> List[Point3]:
    """Give boundary vertices without elevation an elevation from the closest data points (IDW)."""
    need = [p for p in ring if p[2] is None]
    if not need:
        return [(p[0], p[1], float(p[2])) for p in ring]  # type: ignore[arg-type]
    prelim = None
    try:
        prelim = build_tin(points)
    except TerrainError:
        prelim = None
    out = []
    for p in ring:
        if p[2] is not None:
            out.append((p[0], p[1], float(p[2])))
            continue
        z = prelim.z_at(p[0], p[1]) if prelim is not None else None
        if z is None:
            best = sorted(points, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2)[:6]
            wsum = 0.0
            zsum = 0.0
            for q in best:
                d = math.hypot(q[0] - p[0], q[1] - p[1])
                if d < 1e-12:
                    wsum = 1.0
                    zsum = q[2]
                    break
                w = 1.0 / (d * d)
                wsum += w
                zsum += w * q[2]
            z = zsum / wsum if wsum else 0.0
        out.append((p[0], p[1], z))
    return out


def build_tin(points: Sequence[Sequence[float]],
              breaklines: Optional[Sequence[Sequence[Sequence[float]]]] = None,
              boundary: Optional[Sequence[Sequence[float]]] = None,
              holes: Optional[Sequence[Sequence[Sequence[float]]]] = None,
              max_edge: float = 0.0,
              dedupe_tol: float = 0.001,
              densify_constraints: float = 0.0,
              log=None) -> TIN:
    """Build a TIN from mass points, breaklines and an optional boundary/holes.

    Args:
        points:      iterable of (x, y, z)
        breaklines:  list of 3D polylines that triangle edges must follow
        boundary:    closed outline (x, y[, z]); triangles outside are removed
        holes:       closed rings; triangles inside are removed
        max_edge:    remove hull triangles whose outer edge is longer (concave outline)
        dedupe_tol:  points closer than this (plan) are merged
        densify_constraints: optional max segment length for breaklines/boundary
        log:         optional callable(str) for progress messages
    """
    def _log(msg: str) -> None:
        if log:
            log(msg)

    pts: List[Point3] = []
    for p in points:
        if len(p) < 3 or p[2] is None:
            continue
        x, y, z = float(p[0]), float(p[1]), float(p[2])
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            pts.append((x, y, z))

    lines: List[List[Point3]] = []
    for bl in breaklines or []:
        line = [(float(p[0]), float(p[1]), float(p[2])) for p in bl if len(p) >= 3 and p[2] is not None]
        if len(line) >= 2:
            if densify_constraints > 0:
                line = [tuple(q) for q in geom.densify(line, densify_constraints)]  # type: ignore[misc]
            lines.append(line)

    rings: List[Tuple[List[Point3], bool]] = []
    raw_rings = []
    if boundary:
        raw_rings.append((boundary, True))
    for h in holes or []:
        raw_rings.append((h, False))
    for ring, is_outer in raw_rings:
        r = geom.open_ring([(float(p[0]), float(p[1]), (float(p[2]) if len(p) > 2 and p[2] is not None else None))
                            for p in ring])
        if len(r) < 3:
            continue
        r3 = _interp_missing_z(r, pts + [q for l in lines for q in l])  # type: ignore[arg-type]
        if densify_constraints > 0:
            r3 = [tuple(q) for q in geom.densify(r3, densify_constraints, closed=True)]  # type: ignore[misc]
        rings.append((r3, is_outer))

    # split breaklines at crossings with each other and with boundary/hole rings
    n_lines = len(lines)
    combined = lines + [list(r) + [r[0]] for r, _ in rings]
    combined = _split_crossing_lines(combined)
    lines = combined[:n_lines]
    rings = [(combined[n_lines + i][:-1], rings[i][1]) for i in range(len(rings))]

    all_pts: List[Point3] = []
    # priority: rings, breaklines, then mass points (first wins on duplicates)
    for r, _ in rings:
        all_pts.extend(r)
    for l in lines:
        all_pts.extend(l)
    n_constraint = len(all_pts)
    all_pts.extend(pts)
    if len(all_pts) < 3:
        raise TerrainError(f"Not enough points to build a terrain (got {len(all_pts)}, need at least 3).")

    unique, remap = _dedupe(all_pts, dedupe_tol)
    _log(f"Points: {len(all_pts)} input, {len(unique)} after merging duplicates (tol {dedupe_tol}).")
    if len(unique) < 3:
        raise TerrainError("All points collapse onto fewer than 3 distinct locations.")

    ox = min(p[0] for p in unique)
    oy = min(p[1] for p in unique)
    xs = [p[0] - ox for p in unique]
    ys = [p[1] - oy for p in unique]
    try:
        ct = ConstrainedTriangulation(xs, ys)
    except TriangulationError as exc:
        raise TerrainError(str(exc)) from exc

    # constraints
    k = 0
    region_count = 0
    for r, _ in rings:
        ids = remap[k:k + len(r)]
        k += len(r)
        for i in range(len(ids)):
            a = ids[i]
            b = ids[(i + 1) % len(ids)]
            if a != b:
                ct.insert_constraint(a, b, region=True)
                region_count += 1
    bl_count = 0
    for l in lines:
        ids = remap[k:k + len(l)]
        k += len(l)
        for i in range(len(ids) - 1):
            if ids[i] != ids[i + 1]:
                ct.insert_constraint(ids[i], ids[i + 1])
                bl_count += 1
    assert k == n_constraint
    if ct.failed_constraints:
        _log(f"WARNING: {len(ct.failed_constraints)} constraint segment(s) could not be enforced "
             f"(crossing breaklines or degenerate geometry).")
    ct.clip_regions([[(p[0] - ox, p[1] - oy) for p in r] for r, _ in rings])
    if ct.failed_region:
        _log(f"NOTE: {ct.failed_region} boundary segment(s) could not be enforced exactly; "
             "triangles were clipped by their centre point instead.")
    removed = ct.trim_long_edges(max_edge) if max_edge > 0 else 0
    if removed:
        _log(f"Removed {removed} outer triangle(s) with edges longer than {max_edge}.")
    tris = ct.triangles()
    if not tris:
        raise TerrainError("Triangulation produced no triangles (check boundary / max edge length).")
    tin = TIN(unique, tris, compact=True, breaklines=lines)
    tin.info.update({
        "input_points": len(all_pts),
        "unique_points": len(unique),
        "breakline_segments": bl_count,
        "boundary_segments": region_count,
        "failed_constraints": len(ct.failed_constraints),
        "trimmed_triangles": removed,
    })
    _log(f"TIN: {len(tin.points)} vertices, {len(tin.triangles)} triangles.")
    return tin


def tin_from_mesh(points: Sequence[Sequence[float]], faces: Iterable[Sequence[int]]) -> TIN:
    """Wrap an existing mesh (e.g. LandXML / OBJ faces). Polygons are fan-triangulated."""
    tris: List[Tri] = []
    for f in faces:
        f = list(f)
        if len(f) < 3:
            continue
        for i in range(1, len(f) - 1):
            tris.append((f[0], f[i], f[i + 1]))
    pts = [(float(p[0]), float(p[1]), float(p[2])) for p in points]
    tin = TIN(pts, tris, compact=True)
    if tin.is_empty:
        raise TerrainError("The mesh contains no valid (non-vertical) triangles.")
    return tin
