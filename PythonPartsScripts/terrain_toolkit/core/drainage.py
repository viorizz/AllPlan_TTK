"""Surface water analysis on a TIN: flow arrows, steepest-descent flow paths,
local sinks and ponding (depression) depth via priority flood."""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import geom
from .tin import TIN

Point3 = Tuple[float, float, float]


def mean_edge_length(tin: TIN, sample: int = 2000) -> float:
    edges = tin.edges()
    if not edges:
        return 1.0
    step = max(1, len(edges) // sample)
    pts = tin.points
    vals = [geom.dist(pts[u], pts[v]) for u, v in edges[::step]]
    return sum(vals) / len(vals)


def flow_arrows(tin: TIN, spacing: float = 0.0, length: float = 0.0, min_slope_pct: float = 0.5,
                head_ratio: float = 0.3, scale_by_slope: bool = False) -> List[List[Point3]]:
    """Downhill arrows as 3D polylines [tail, tip, head1, tip, head2] draped at surface level.

    spacing > 0 places arrows on a regular grid, otherwise one per triangle centroid.
    """
    arrows: List[List[Point3]] = []
    me = mean_edge_length(tin)
    if length <= 0:
        length = (spacing if spacing > 0 else me) * 0.6

    def make(x: float, y: float, t: int) -> Optional[List[Point3]]:
        gx, gy = tin.triangle_gradient(t)
        s = math.hypot(gx, gy)
        if s * 100.0 < min_slope_pct or s == 0:
            return None
        ux, uy = -gx / s, -gy / s
        L = length * (min(1.0, 0.25 + s) if scale_by_slope else 1.0)
        x0, y0 = x - ux * L / 2, y - uy * L / 2
        x1, y1 = x + ux * L / 2, y + uy * L / 2
        z0 = tin.z_at(x0, y0)
        z1 = tin.z_at(x1, y1)
        zc = tin.z_at(x, y) or 0.0
        z0 = zc + s * L / 2 if z0 is None else z0
        z1 = zc - s * L / 2 if z1 is None else z1
        hl = L * head_ratio
        ang = math.radians(25.0)
        ca, sa = math.cos(ang), math.sin(ang)
        hx1 = x1 - hl * (ux * ca - uy * sa)
        hy1 = y1 - hl * (uy * ca + ux * sa)
        hx2 = x1 - hl * (ux * ca + uy * sa)
        hy2 = y1 - hl * (uy * ca - ux * sa)
        zh = z1 + s * hl * ca
        return [(x0, y0, z0), (x1, y1, z1), (hx1, hy1, zh), (x1, y1, z1), (hx2, hy2, zh)]

    if spacing > 0:
        xmin, ymin, xmax, ymax = tin.bbox()
        y = ymin + spacing / 2
        while y < ymax:
            x = xmin + spacing / 2
            while x < xmax:
                t = tin.locate(x, y)
                if t >= 0:
                    a = make(x, y, t)
                    if a:
                        arrows.append(a)
                x += spacing
            y += spacing
    else:
        for t in range(len(tin.triangles)):
            pa, pb, pc = tin.tri_points(t)
            a = make((pa[0] + pb[0] + pc[0]) / 3, (pa[1] + pb[1] + pc[1]) / 3, t)
            if a:
                arrows.append(a)
    return arrows


def flow_path(tin: TIN, x: float, y: float, step: float = 0.0, max_length: float = 0.0,
              min_drop: float = 1e-6) -> List[Point3]:
    """Trace water from (x, y) following the steepest descent until a sink or the edge of the surface."""
    if step <= 0:
        step = mean_edge_length(tin) / 4.0
    if max_length <= 0:
        xmin, ymin, xmax, ymax = tin.bbox()
        max_length = 4.0 * ((xmax - xmin) + (ymax - ymin))
    z = tin.z_at(x, y)
    if z is None:
        return []
    path = [(x, y, z)]
    travelled = 0.0
    prev_dir = None
    stuck = 0
    while travelled < max_length:
        t = tin.locate(x, y)
        if t < 0:
            break
        gx, gy = tin.triangle_gradient(t)
        s = math.hypot(gx, gy)
        if s < 1e-12:
            break
        ux, uy = -gx / s, -gy / s
        nx, ny = x + ux * step, y + uy * step
        nz = tin.z_at(nx, ny)
        if nz is None:
            # leaving the surface: clip to the outline and stop
            hits = [h for h in tin.intersect_segment((x, y), (nx, ny)) if h[0] > 1e-9]
            if hits:
                h = hits[-1]
                path.append((h[1], h[2], h[3]))
            break
        if nz > z - min_drop:
            # oscillation in a channel: try the averaged direction of both triangles
            t2 = tin.locate(nx, ny)
            if t2 >= 0 and prev_dir is not None:
                g2x, g2y = tin.triangle_gradient(t2)
                s2 = math.hypot(g2x, g2y)
                if s2 > 0:
                    ax, ay = ux + (-g2x / s2), uy + (-g2y / s2)
                    al = math.hypot(ax, ay)
                    if al > 1e-9:
                        ax, ay = ax / al, ay / al
                        nx, ny = x + ax * step, y + ay * step
                        nz = tin.z_at(nx, ny)
            if nz is None or nz > z - min_drop:
                stuck += 1
                if stuck > 3:
                    break
                step *= 0.5
                continue
        stuck = 0
        travelled += math.hypot(nx - x, ny - y)
        prev_dir = (nx - x, ny - y)
        x, y, z = nx, ny, nz
        path.append((x, y, z))
    return _thin_path(path, step * 0.5)


def _thin_path(path: List[Point3], tol: float) -> List[Point3]:
    if len(path) < 3:
        return path
    return [tuple(p) for p in geom.douglas_peucker(path, tol * 0.2)]  # type: ignore[misc]


def flow_paths_grid(tin: TIN, spacing: float, min_length: float = 0.0) -> List[List[Point3]]:
    xmin, ymin, xmax, ymax = tin.bbox()
    out = []
    y = ymin + spacing / 2
    while y < ymax:
        x = xmin + spacing / 2
        while x < xmax:
            if tin.z_at(x, y) is not None:
                p = flow_path(tin, x, y)
                if len(p) >= 2 and geom.polyline_length(p) >= min_length:
                    out.append(p)
            x += spacing
        y += spacing
    return out


@dataclass
class DepressionResult:
    filled_z: List[float]
    depth: List[float]
    sinks: List[int] = field(default_factory=list)       # vertex ids of local minima (interior)
    ponding_volume: float = 0.0
    ponding_area: float = 0.0
    max_depth: float = 0.0


def depressions(tin: TIN, min_depth: float = 0.01) -> DepressionResult:
    """Priority-flood depression filling (Barnes et al. 2014) on the TIN vertex graph.

    Water leaves the model only across its outline. ``depth`` is how much water would pond
    on each vertex before spilling.
    """
    pts = tin.points
    n = len(pts)
    nbrs = tin.vertex_neighbors()
    boundary = set()
    for ring in tin.boundary_rings():
        boundary.update(ring)
    filled = [p[2] for p in pts]
    done = [False] * n
    heap: List[Tuple[float, int]] = []
    for v in boundary:
        heapq.heappush(heap, (filled[v], v))
        done[v] = True
    if not heap and n:
        v = min(range(n), key=lambda i: pts[i][2])
        heapq.heappush(heap, (filled[v], v))
        done[v] = True
    while heap:
        zc, v = heapq.heappop(heap)
        for w in nbrs[v]:
            if done[w]:
                continue
            done[w] = True
            if filled[w] < zc:
                filled[w] = zc
            heapq.heappush(heap, (filled[w], w))
    depth = [filled[i] - pts[i][2] for i in range(n)]
    sinks = []
    for v in range(n):
        if v in boundary or not nbrs[v]:
            continue
        if all(pts[w][2] > pts[v][2] for w in nbrs[v]):
            sinks.append(v)
    res = DepressionResult(filled, depth, sinks)
    # volume / area with linear depth on triangles (only where depth > min_depth somewhere)
    for a, b, c in tin.triangles:
        da, db, dc = depth[a], depth[b], depth[c]
        if max(da, db, dc) <= min_depth:
            continue
        pa, pb, pc = pts[a], pts[b], pts[c]
        area = 0.5 * abs(geom.orient(pa[0], pa[1], pb[0], pb[1], pc[0], pc[1]))
        res.ponding_volume += area * (da + db + dc) / 3.0
        res.ponding_area += area
    res.max_depth = max(depth) if depth else 0.0
    return res
