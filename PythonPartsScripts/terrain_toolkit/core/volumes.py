"""Cut / fill volumes between two surfaces or between a surface and a reference elevation.

The method overlays both TINs exactly (all vertices of both surfaces plus all
edge/edge intersections, with the edges of both surfaces enforced as
constraints). On the resulting triangles the elevation difference is linear,
so cut and fill volumes are integrated exactly - including triangles where
the difference changes sign.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from . import geom
from .delaunay import ConstrainedTriangulation
from .tin import TIN, TerrainError, _dedupe

Point3 = Tuple[float, float, float]


@dataclass
class VolumeResult:
    cut: float = 0.0           # volume where design is BELOW existing (excavation)
    fill: float = 0.0          # volume where design is ABOVE existing (embankment)
    cut_area: float = 0.0
    fill_area: float = 0.0
    zero_area: float = 0.0
    total_area: float = 0.0
    max_cut: float = 0.0       # deepest excavation (positive number)
    max_fill: float = 0.0
    diff_tin: Optional[TIN] = None             # overlay mesh, z = existing elevation
    diff_values: List[float] = field(default_factory=list)   # design - existing per diff_tin vertex
    design_z: List[float] = field(default_factory=list)      # design elevation per diff_tin vertex

    @property
    def net(self) -> float:
        """fill - cut (positive = material must be imported)."""
        return self.fill - self.cut

    def as_dict(self) -> Dict[str, float]:
        return {"cut": self.cut, "fill": self.fill, "net": self.net, "cut_area": self.cut_area,
                "fill_area": self.fill_area, "total_area": self.total_area,
                "max_cut": self.max_cut, "max_fill": self.max_fill}


def _integrate_triangle(p: Sequence[Tuple[float, float]], d: Sequence[float]) -> Tuple[float, float, float, float]:
    """Return (positive volume, negative volume (>0), positive area, negative area) of linear d over triangle p."""
    area = 0.5 * geom.orient(p[0][0], p[0][1], p[1][0], p[1][1], p[2][0], p[2][1])
    area = abs(area)
    if area == 0.0:
        return 0.0, 0.0, 0.0, 0.0
    if d[0] >= 0 and d[1] >= 0 and d[2] >= 0:
        return area * (d[0] + d[1] + d[2]) / 3.0, 0.0, area if (d[0] + d[1] + d[2]) > 0 else 0.0, 0.0
    if d[0] <= 0 and d[1] <= 0 and d[2] <= 0:
        return 0.0, -area * (d[0] + d[1] + d[2]) / 3.0, 0.0, area
    pos_v, pos_a = _clip_part(p, d, True)
    neg_v, neg_a = _clip_part(p, d, False)
    return pos_v, neg_v, pos_a, neg_a


def _clip_part(p, d, positive: bool) -> Tuple[float, float]:
    """Integral of |d| over the part of the triangle where d has the given sign."""
    poly: List[Tuple[float, float, float]] = []
    n = 3
    for i in range(n):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % n]
        d1, d2 = d[i], d[(i + 1) % n]
        in1 = d1 >= 0 if positive else d1 <= 0
        in2 = d2 >= 0 if positive else d2 <= 0
        if in1:
            poly.append((x1, y1, d1))
        if in1 != in2:
            t = d1 / (d1 - d2)
            poly.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, 0.0))
    if len(poly) < 3:
        return 0.0, 0.0
    vol = 0.0
    area = 0.0
    x0, y0, d0 = poly[0]
    for i in range(1, len(poly) - 1):
        x1, y1, d1 = poly[i]
        x2, y2, d2 = poly[i + 1]
        a = 0.5 * abs(geom.orient(x0, y0, x1, y1, x2, y2))
        vol += a * abs(d0 + d1 + d2) / 3.0
        area += a
    return vol, area


def difference(existing: TIN, design: Optional[TIN] = None, reference_z: Optional[float] = None,
               boundary: Optional[Sequence[Sequence[float]]] = None, exact: bool = True,
               log=None) -> VolumeResult:
    """Volumes between ``existing`` and ``design`` (TIN) or a horizontal plane ``reference_z``.

    Positive difference (design above existing) is fill, negative is cut.
    ``boundary`` limits the computation to a closed plan polygon.
    """
    def _log(m):
        if log:
            log(m)

    if design is None and reference_z is None:
        raise TerrainError("Give either a design surface or a reference elevation.")

    bnd = geom.open_ring([(float(p[0]), float(p[1])) for p in boundary]) if boundary else None
    if bnd is not None and len(bnd) < 3:
        bnd = None

    pts: List[Tuple[float, float]] = []
    pts.extend((p[0], p[1]) for p in existing.points)
    n_e = len(existing.points)
    constraints_idx: List[Tuple[int, int]] = []
    if exact:
        constraints_idx.extend(existing.edges())
    if design is not None:
        pts.extend((p[0], p[1]) for p in design.points)
        if exact:
            constraints_idx.extend((n_e + u, n_e + v) for u, v in design.edges())
            n_int = 0
            for u, v in existing.edges():
                a = existing.points[u]
                b = existing.points[v]
                for t_id in design.index.triangles_along_segment(a[0], a[1], b[0], b[1]):
                    tri = design.triangles[t_id]
                    for k in range(3):
                        c = design.points[tri[k]]
                        d = design.points[tri[(k + 1) % 3]]
                        hit = geom.segment_intersection(a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1])
                        if hit is None:
                            continue
                        t, s = hit
                        if 1e-9 < t < 1 - 1e-9 and 1e-9 < s < 1 - 1e-9:
                            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                            n_int += 1
            _log(f"Overlay: {n_int} edge intersections.")
    bnd_idx: List[int] = []
    if bnd is not None:
        start = len(pts)
        pts.extend(bnd)
        bnd_idx = list(range(start, start + len(bnd)))
        surfaces = [existing] + ([design] if design is not None else [])
        for i in range(len(bnd)):
            a = bnd[i]
            b = bnd[(i + 1) % len(bnd)]
            for srf in surfaces:
                for hit in srf.intersect_segment(a, b):
                    pts.append((hit[1], hit[2]))

    span = max(1.0, max(abs(p[0]) for p in pts), max(abs(p[1]) for p in pts))
    tol = max(1e-4, span * 1e-9)   # merge overlay points closer than 0.1 mm
    uniq, remap = _dedupe([(x, y, 0.0) for x, y in pts], tol)

    ox = min(q[0] for q in uniq)
    oy = min(q[1] for q in uniq)
    ct = ConstrainedTriangulation([q[0] - ox for q in uniq], [q[1] - oy for q in uniq])

    if bnd_idx:
        ids = [remap[i] for i in bnd_idx]
        for i in range(len(ids)):
            a, b = ids[i], ids[(i + 1) % len(ids)]
            if a != b:
                ct.insert_constraint(a, b, region=True)
    seen = set()
    for (a0, b0) in constraints_idx:
        a, b = remap[a0], remap[b0]
        if a == b:
            continue
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        ct.insert_constraint(a, b)
    ct.clip_regions([[(x - ox, y - oy) for x, y in bnd]] if bnd is not None else None)
    if ct.failed_region:
        _log(f"NOTE: {ct.failed_region} boundary segment(s) not enforced exactly; centroid clipping used.")
    tris = ct.triangles()

    # elevations
    ze: List[Optional[float]] = []
    zd: List[Optional[float]] = []
    for q in uniq:
        ze.append(existing.z_at(q[0], q[1]))
        zd.append(reference_z if design is None else design.z_at(q[0], q[1]))

    res = VolumeResult()
    keep: List[Tuple[int, int, int]] = []
    for a, b, c in tris:
        if ze[a] is None or ze[b] is None or ze[c] is None or zd[a] is None or zd[b] is None or zd[c] is None:
            continue
        # domain check at centroid (concave outlines)
        cx = (uniq[a][0] + uniq[b][0] + uniq[c][0]) / 3.0
        cy = (uniq[a][1] + uniq[b][1] + uniq[c][1]) / 3.0
        if existing.z_at(cx, cy) is None or (design is not None and design.z_at(cx, cy) is None):
            continue
        keep.append((a, b, c))
        p2 = [(uniq[i][0], uniq[i][1]) for i in (a, b, c)]
        dv = [zd[i] - ze[i] for i in (a, b, c)]  # type: ignore[operator]
        fv, cv, fa, ca = _integrate_triangle(p2, dv)
        res.fill += fv
        res.cut += cv
        res.fill_area += fa
        res.cut_area += ca
        tri_area = 0.5 * abs(geom.orient(p2[0][0], p2[0][1], p2[1][0], p2[1][1], p2[2][0], p2[2][1]))
        res.total_area += tri_area
        for v in dv:
            if v > res.max_fill:
                res.max_fill = v
            if -v > res.max_cut:
                res.max_cut = -v
    res.zero_area = max(0.0, res.total_area - res.fill_area - res.cut_area)
    if not keep:
        raise TerrainError("The surfaces do not overlap (or the boundary is outside the terrain).")
    pts3 = [(uniq[i][0], uniq[i][1], ze[i] if ze[i] is not None else 0.0) for i in range(len(uniq))]
    diff_tin = TIN(pts3, keep, compact=False)
    res.diff_tin = diff_tin
    res.design_z = [zd[i] if zd[i] is not None else 0.0 for i in range(len(uniq))]
    res.diff_values = [res.design_z[i] - pts3[i][2] for i in range(len(uniq))]
    _log(f"Cut {res.cut:.3f}, fill {res.fill:.3f}, area {res.total_area:.3f}")
    return res


def grid_volume(existing: TIN, design_fn, cell: float, boundary: Optional[Sequence[Sequence[float]]] = None) -> Tuple[float, float]:
    """Fast approximate (cut, fill) by sampling cell centres. design_fn(x, y, z_existing) -> z_design."""
    xmin, ymin, xmax, ymax = existing.bbox()
    if boundary:
        bx = geom.bbox(boundary)
        xmin, ymin = max(xmin, bx[0]), max(ymin, bx[1])
        xmax, ymax = min(xmax, bx[2]), min(ymax, bx[3])
    cut = fill = 0.0
    a = cell * cell
    y = ymin + cell / 2
    while y < ymax:
        x = xmin + cell / 2
        while x < xmax:
            if boundary is None or geom.point_in_polygon(x, y, boundary):
                z = existing.z_at(x, y)
                if z is not None:
                    zd = design_fn(x, y, z)
                    if zd is not None:
                        d = zd - z
                        if d > 0:
                            fill += d * a
                        else:
                            cut -= d * a
            x += cell
        y += cell
    return cut, fill
