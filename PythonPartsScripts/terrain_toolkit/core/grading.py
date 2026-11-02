"""Platform (pad) grading with daylight slopes and cut/fill balancing.

The design surface outside the pad at plan distance d from the pad outline is

    fill slope  z_f = e - d / fill_ratio      (used where terrain is below z_f)
    cut slope   z_c = e + d / cut_ratio       (used where terrain is above z_c)
    design      = clamp(terrain, z_f, z_c)

where e is the pad elevation at the closest point of the outline and the
ratios are horizontal:vertical (1.5 means 3H:2V). The daylight line is where
the slopes meet the terrain again.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from . import geom
from .contours import isolines
from .tin import TIN, TerrainError, build_tin
from .volumes import VolumeResult, difference

Point2 = Tuple[float, float]
Point3 = Tuple[float, float, float]


@dataclass
class PlatformSpec:
    outline: List[Sequence[float]]           # closed plan ring, optional z per vertex
    elevation: Optional[float] = None        # constant pad elevation (None + balance -> solved)
    use_outline_z: bool = False              # pad = best-fit plane through 3D outline vertices
    cut_ratio: float = 1.5                   # H:V
    fill_ratio: float = 2.0                  # H:V
    max_reach: float = 50.0                  # max horizontal slope width
    cell: float = 0.0                        # grid resolution (0 = automatic)
    balance: bool = False                    # solve the elevation so that cut == fill
    balance_factor: float = 1.0              # fill = cut * factor (swell/shrink compensation)


@dataclass
class PlatformResult:
    elevation_offset: float
    pad_elevation_info: str
    outline3d: List[Point3]
    daylight: List[Point3]
    pad_tin: Optional[TIN]
    slope_tin: Optional[TIN]
    design_tin: Optional[TIN]
    cut_slope_triangles: List[Tuple[Point3, Point3, Point3]] = field(default_factory=list)
    fill_slope_triangles: List[Tuple[Point3, Point3, Point3]] = field(default_factory=list)
    volumes: Optional[VolumeResult] = None
    warnings: List[str] = field(default_factory=list)


def _fit_plane(pts: Sequence[Sequence[float]]) -> Tuple[float, float, float]:
    """Least squares plane z = a x + b y + c."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    mz = sum(p[2] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    sxz = sum((p[0] - mx) * (p[2] - mz) for p in pts)
    syz = sum((p[1] - my) * (p[2] - mz) for p in pts)
    det = sxx * syy - sxy * sxy
    if abs(det) < 1e-12:
        return 0.0, 0.0, mz
    a = (sxz * syy - syz * sxy) / det
    b = (syz * sxx - sxz * sxy) / det
    return a, b, mz - a * mx - b * my


def _nearest_on_ring(x: float, y: float, ring: Sequence[Point2]) -> Tuple[float, float, float]:
    best = (math.inf, 0.0, 0.0)
    n = len(ring)
    for i in range(n):
        a = ring[i]
        b = ring[(i + 1) % n]
        d, t = geom.point_segment_distance(x, y, a[0], a[1], b[0], b[1])
        if d < best[0]:
            best = (d, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return best


class _Grid:
    def __init__(self, existing: TIN, ring: List[Point2], spec: PlatformSpec, plane):
        self.ring = ring
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        reach = spec.max_reach
        exmin, eymin, exmax, eymax = existing.bbox()
        self.xmin = max(min(xs) - reach, exmin)
        self.ymin = max(min(ys) - reach, eymin)
        self.xmax = min(max(xs) + reach, exmax)
        self.ymax = min(max(ys) + reach, eymax)
        if self.xmax <= self.xmin or self.ymax <= self.ymin:
            raise TerrainError("The platform outline is outside the terrain.")
        cell = spec.cell
        if cell <= 0:
            ext = max(max(xs) - min(xs), max(ys) - min(ys))
            cell = min(max(ext / 120.0, 0.05), 2.0)
            # keep the grid below ~120k nodes
            area = (self.xmax - self.xmin) * (self.ymax - self.ymin)
            cell = max(cell, math.sqrt(area / 120000.0))
        self.cell = cell
        self.nx = int(math.ceil((self.xmax - self.xmin) / cell)) + 1
        self.ny = int(math.ceil((self.ymax - self.ymin) / cell)) + 1
        self.nodes = []  # (x, y, T or None, inside, d, e_base)
        a, b, c = plane
        for j in range(self.ny):
            y = self.ymin + j * cell
            for i in range(self.nx):
                x = self.xmin + i * cell
                T = existing.z_at(x, y)
                inside = geom.point_in_polygon(x, y, ring)
                if inside:
                    d = 0.0
                    e = a * x + b * y + c
                else:
                    d, nx_, ny_ = _nearest_on_ring(x, y, ring)
                    e = a * nx_ + b * ny_ + c
                self.nodes.append((x, y, T, inside, d, e))

    def design(self, node, offset: float, spec: PlatformSpec) -> Optional[float]:
        x, y, T, inside, d, e = node
        e = e + offset
        if inside:
            return e
        if T is None:
            return None
        zf = e - d / spec.fill_ratio
        zc = e + d / spec.cut_ratio
        if T < zf:
            return zf
        if T > zc:
            return zc
        return T

    def net(self, offset: float, spec: PlatformSpec) -> Tuple[float, float]:
        cut = fill = 0.0
        a = self.cell * self.cell
        for node in self.nodes:
            T = node[2]
            if T is None:
                continue
            z = self.design(node, offset, spec)
            if z is None:
                continue
            dz = z - T
            if dz > 0:
                fill += dz * a
            else:
                cut -= dz * a
        return cut, fill


def grade_platform(existing: TIN, spec: PlatformSpec, log=None) -> PlatformResult:
    def _log(m):
        if log:
            log(m)

    ring3 = geom.open_ring(list(spec.outline))
    if len(ring3) < 3:
        raise TerrainError("The platform outline needs at least 3 vertices.")
    ring = [(float(p[0]), float(p[1])) for p in ring3]
    if geom.polygon_area(ring) < 0:
        ring.reverse()
        ring3 = list(reversed(ring3))
    if spec.cut_ratio <= 0 or spec.fill_ratio <= 0:
        raise TerrainError("Slope ratios must be > 0 (horizontal : vertical, e.g. 1.5).")

    warnings: List[str] = []
    if spec.use_outline_z:
        if any(len(p) < 3 or p[2] is None for p in ring3):
            raise TerrainError("'Use outline elevations' needs a 3D outline (z on every vertex).")
        plane = _fit_plane([(p[0], p[1], p[2]) for p in ring3])
        base_info = f"plane z = {plane[0]:.5f}*x + {plane[1]:.5f}*y + {plane[2]:.3f}"
        offset = 0.0
    else:
        plane = (0.0, 0.0, 0.0)
        offset = spec.elevation if spec.elevation is not None else 0.0
        base_info = "constant"

    grid = _Grid(existing, ring, spec, plane)
    _log(f"Grading grid {grid.nx} x {grid.ny} nodes, cell {grid.cell:.3f}")
    missing = sum(1 for nd in grid.nodes if nd[3] and nd[2] is None)
    if missing:
        warnings.append(f"{missing} grid node(s) inside the platform are outside the terrain model.")

    if spec.balance:
        ts = [nd[2] for nd in grid.nodes if nd[2] is not None]
        lo = min(ts) - 10.0 - (plane[2] if spec.use_outline_z else 0.0)
        hi = max(ts) + 10.0 - (plane[2] if spec.use_outline_z else 0.0)
        if spec.use_outline_z:
            lo, hi = -abs(max(ts) - min(ts)) - 10.0, abs(max(ts) - min(ts)) + 10.0
        k = spec.balance_factor if spec.balance_factor > 0 else 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            cut, fill = grid.net(mid, spec)
            if fill - cut * k > 0:
                hi = mid
            else:
                lo = mid
            if hi - lo < 1e-4:
                break
        offset = 0.5 * (lo + hi)
        _log(f"Balanced pad offset/elevation: {offset:.4f}")

    # --- daylight line: zero contour of h on a regular grid TIN
    pts = []
    vals = []
    nx, ny = grid.nx, grid.ny
    for idx, node in enumerate(grid.nodes):
        x, y, T, inside, d, e = node
        e = e + offset
        i = idx % nx
        j = idx // nx
        border = i == 0 or j == 0 or i == nx - 1 or j == ny - 1
        if T is None:
            h = -1.0
            T = e
        elif inside:
            h = 1.0 + abs(T - e)
        else:
            zf = e - d / spec.fill_ratio
            zc = e + d / spec.cut_ratio
            h = max(zf - T, T - zc)
            if d > spec.max_reach and h > 0:
                h = -1e-3
        if border and not inside:
            if h > 0:
                warnings.append("The slopes reach the limit of the terrain / max reach: daylight line is cut there.")
            h = -1.0
        pts.append((x, y, T))
        vals.append(h)
    tris = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            b = a + 1
            c = a + nx
            dd = c + 1
            tris.append((a, b, dd))
            tris.append((a, dd, c))
    gtin = TIN(pts, tris, compact=False)
    lines = isolines(gtin, [0.0], values=vals).get(0.0, [])
    loops = [l for l, closed in lines if closed and len(l) > 3]
    if not loops:
        raise TerrainError("Could not determine the daylight line (is the outline inside the terrain?).")
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    loops.sort(key=lambda l: abs(geom.polygon_area(l)), reverse=True)
    daylight2 = loops[0]
    daylight3: List[Point3] = []
    for p in geom.douglas_peucker(daylight2, grid.cell * 0.05):
        z = existing.z_at(p[0], p[1])
        daylight3.append((p[0], p[1], z if z is not None else p[2]))
    if len(daylight3) > 1 and daylight3[0][:2] == daylight3[-1][:2]:
        daylight3.pop()
    dl_ring = [(p[0], p[1]) for p in daylight3]
    if geom.polygon_area(dl_ring) < 0:
        daylight3.reverse()
        dl_ring.reverse()

    def pad_z(x: float, y: float) -> float:
        return plane[0] * x + plane[1] * y + plane[2] + offset

    outline3d = [(x, y, pad_z(x, y)) for x, y in ring]
    dens = geom.densify(outline3d, grid.cell * 2, closed=True)
    outline_dense = [(p[0], p[1], pad_z(p[0], p[1])) for p in dens]

    slope_nodes = []
    pad_nodes = []
    for node in grid.nodes:
        x, y, T, inside, d, e = node
        if T is None:
            continue
        if inside:
            if spec.use_outline_z:
                pad_nodes.append((x, y, pad_z(x, y)))
            continue
        if not geom.point_in_polygon(x, y, dl_ring):
            continue
        z = grid.design(node, offset, spec)
        if z is not None and abs(z - T) > 1e-6:
            slope_nodes.append((x, y, z))

    pad_tin = build_tin(outline_dense + pad_nodes, boundary=outline_dense)
    slope_tin = None
    try:
        slope_tin = build_tin(slope_nodes + outline_dense + daylight3,
                              breaklines=[outline_dense + [outline_dense[0]], daylight3 + [daylight3[0]]],
                              boundary=daylight3, holes=[outline_dense], dedupe_tol=grid.cell * 0.05)
    except TerrainError as exc:
        warnings.append(f"Slope mesh: {exc}")

    cut_tris: List[Tuple[Point3, Point3, Point3]] = []
    fill_tris: List[Tuple[Point3, Point3, Point3]] = []
    if slope_tin is not None:
        for t in range(len(slope_tin.triangles)):
            pa, pb, pc = slope_tin.tri_points(t)
            mx = (pa[0] + pb[0] + pc[0]) / 3
            my = (pa[1] + pb[1] + pc[1]) / 3
            mz = (pa[2] + pb[2] + pc[2]) / 3
            T = existing.z_at(mx, my)
            if T is None:
                continue
            (cut_tris if mz < T else fill_tris).append((pa, pb, pc))

    # full design surface = terrain outside the daylight line + slopes + pad
    outer_pts = [p for p in existing.points if not geom.point_in_polygon(p[0], p[1], dl_ring)]
    rings = existing.boundary_rings()
    outer_ring = None
    if rings:
        cand = [[existing.points[i] for i in r] for r in rings]
        cand.sort(key=lambda r: abs(geom.polygon_area(r)), reverse=True)
        outer_ring = cand[0]
    design_tin = None
    try:
        design_tin = build_tin(outer_pts + daylight3 + slope_nodes + outline_dense + pad_nodes,
                               breaklines=[daylight3 + [daylight3[0]], outline_dense + [outline_dense[0]]],
                               boundary=outer_ring, dedupe_tol=grid.cell * 0.05)
    except TerrainError as exc:
        warnings.append(f"Design surface: {exc}")

    vol = None
    if design_tin is not None:
        try:
            vol = difference(existing, design_tin, boundary=dl_ring)
        except TerrainError as exc:
            warnings.append(f"Volumes: {exc}")

    info = f"{base_info}, offset {offset:.3f}" if spec.use_outline_z else f"elevation {offset:.3f}"
    return PlatformResult(offset, info, outline3d, daylight3, pad_tin, slope_tin, design_tin,
                          cut_tris, fill_tris, vol, sorted(set(warnings)))
