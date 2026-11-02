"""Small, dependency-free 2D/3D geometry helpers used by the terrain core.

Every function works on plain tuples ``(x, y)`` or ``(x, y, z)`` so the module
can be unit-tested outside of Allplan.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence, Tuple

Point2 = Tuple[float, float]
Point3 = Tuple[float, float, float]


def orient(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    """Twice the signed area of triangle abc (> 0 if counter-clockwise)."""
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def dist2(a: Sequence[float], b: Sequence[float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def dist(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(dist2(a, b))


def dist3(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def polygon_area(poly: Sequence[Sequence[float]]) -> float:
    """Signed area (shoelace). Positive for counter-clockwise rings."""
    n = len(poly)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = poly[i][0], poly[i][1]
        x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        area += x1 * y2 - x2 * y1
    return area * 0.5


def open_ring(poly: Sequence[Sequence[float]]) -> List[Sequence[float]]:
    """Remove a duplicated closing vertex if present."""
    pts = list(poly)
    if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-12 and abs(pts[0][1] - pts[-1][1]) < 1e-12:
        pts.pop()
    return pts


def point_in_polygon(x: float, y: float, poly: Sequence[Sequence[float]]) -> bool:
    """Even-odd rule point in polygon test (ring may be open or closed)."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i][0], poly[i][1]
        xj, yj = poly[j][0], poly[j][1]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> Tuple[float, float]:
    """Return (distance, t) from point to segment ab, t in [0, 1] is the projection parameter."""
    dx = bx - ax
    dy = by - ay
    len2 = dx * dx + dy * dy
    if len2 == 0.0:
        return math.hypot(px - ax, py - ay), 0.0
    t = ((px - ax) * dx + (py - ay) * dy) / len2
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    cx = ax + t * dx
    cy = ay + t * dy
    return math.hypot(px - cx, py - cy), t


def distance_to_polygon_boundary(x: float, y: float, poly: Sequence[Sequence[float]]) -> float:
    best = math.inf
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        d, _ = point_segment_distance(x, y, a[0], a[1], b[0], b[1])
        if d < best:
            best = d
    return best


def segment_intersection(ax: float, ay: float, bx: float, by: float,
                         cx: float, cy: float, dx: float, dy: float) -> Optional[Tuple[float, float]]:
    """Parameters (t, u) of the proper intersection of segments ab and cd, or None."""
    rx = bx - ax
    ry = by - ay
    sx = dx - cx
    sy = dy - cy
    den = rx * sy - ry * sx
    if den == 0.0:
        return None
    qpx = cx - ax
    qpy = cy - ay
    t = (qpx * sy - qpy * sx) / den
    u = (qpx * ry - qpy * rx) / den
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return t, u
    return None


def polyline_length(pts: Sequence[Sequence[float]]) -> float:
    return sum(dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def densify(pts: Sequence[Sequence[float]], max_seg: float, closed: bool = False) -> List[Tuple[float, ...]]:
    """Insert intermediate vertices so that no segment is longer than ``max_seg``.

    Works for 2D and 3D points (z is interpolated linearly).
    """
    if max_seg <= 0 or len(pts) < 2:
        return [tuple(p) for p in pts]
    src = list(pts) + ([pts[0]] if closed else [])
    out: List[Tuple[float, ...]] = []
    for i in range(len(src) - 1):
        a = src[i]
        b = src[i + 1]
        seg = dist(a, b)
        n = max(1, int(math.ceil(seg / max_seg)))
        for k in range(n):
            t = k / n
            out.append(tuple(a[j] + (b[j] - a[j]) * t for j in range(len(a))))
    if not closed:
        out.append(tuple(src[-1]))
    return out


def douglas_peucker(pts: Sequence[Sequence[float]], tol: float) -> List[Sequence[float]]:
    """Iterative Douglas-Peucker simplification in plan (x, y)."""
    n = len(pts)
    if n < 3 or tol <= 0:
        return list(pts)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i0, i1 = stack.pop()
        a = pts[i0]
        b = pts[i1]
        best = -1.0
        idx = -1
        for i in range(i0 + 1, i1):
            d, _ = point_segment_distance(pts[i][0], pts[i][1], a[0], a[1], b[0], b[1])
            if d > best:
                best = d
                idx = i
        if idx >= 0 and best > tol:
            keep[idx] = True
            stack.append((i0, idx))
            stack.append((idx, i1))
    return [p for p, k in zip(pts, keep) if k]


def chaikin(pts: Sequence[Sequence[float]], iterations: int = 1, closed: bool = False) -> List[Tuple[float, ...]]:
    """Chaikin corner cutting smoothing. End points of open lines are kept."""
    cur = [tuple(p) for p in pts]
    for _ in range(max(0, iterations)):
        if len(cur) < 3:
            break
        new: List[Tuple[float, ...]] = []
        m = len(cur)
        rng = range(m) if closed else range(m - 1)
        if not closed:
            new.append(cur[0])
        for i in rng:
            a = cur[i]
            b = cur[(i + 1) % m]
            new.append(tuple(0.75 * a[j] + 0.25 * b[j] for j in range(len(a))))
            new.append(tuple(0.25 * a[j] + 0.75 * b[j] for j in range(len(a))))
        if not closed:
            new.append(cur[-1])
        cur = new
    return cur


def bbox(points: Iterable[Sequence[float]]) -> Tuple[float, float, float, float]:
    xmin = ymin = math.inf
    xmax = ymax = -math.inf
    for p in points:
        x = p[0]
        y = p[1]
        if x < xmin:
            xmin = x
        if x > xmax:
            xmax = x
        if y < ymin:
            ymin = y
        if y > ymax:
            ymax = y
    return xmin, ymin, xmax, ymax


def triangle_normal(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> Point3:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)


def triangle_area_3d(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> float:
    nx, ny, nz = triangle_normal(a, b, c)
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def offset_point_along(pts: Sequence[Sequence[float]], station: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Point and unit direction at a given station (chainage) along a 2D polyline."""
    if len(pts) < 2:
        raise ValueError("polyline needs at least two points")
    acc = 0.0
    for i in range(len(pts) - 1):
        a = pts[i]
        b = pts[i + 1]
        seg = dist(a, b)
        if seg == 0.0:
            continue
        if acc + seg >= station or i == len(pts) - 2:
            t = (station - acc) / seg
            t = min(max(t, 0.0), 1.0)
            ux = (b[0] - a[0]) / seg
            uy = (b[1] - a[1]) / seg
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), (ux, uy)
        acc += seg
    a = pts[-2]
    b = pts[-1]
    seg = dist(a, b) or 1.0
    return (b[0], b[1]), ((b[0] - a[0]) / seg, (b[1] - a[1]) / seg)


def readable_angle_deg(dx: float, dy: float) -> float:
    """Direction angle in degrees, flipped so text placed along it stays readable."""
    ang = math.degrees(math.atan2(dy, dx))
    if ang > 90.0:
        ang -= 180.0
    elif ang <= -90.0:
        ang += 180.0
    return ang


def offset_polygon_vertices(poly: Sequence[Sequence[float]], dist_out: float) -> List[Point2]:
    """Simple mitred offset of a closed ring (positive = outwards for CCW rings)."""
    pts = open_ring(poly)
    n = len(pts)
    if n < 3:
        return [(p[0], p[1]) for p in pts]
    sign = 1.0 if polygon_area(pts) > 0 else -1.0
    out = []
    for i in range(n):
        p0 = pts[i - 1]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1 = math.hypot(*e1) or 1.0
        l2 = math.hypot(*e2) or 1.0
        n1 = (e1[1] / l1 * sign, -e1[0] / l1 * sign)
        n2 = (e2[1] / l2 * sign, -e2[0] / l2 * sign)
        bx = n1[0] + n2[0]
        by = n1[1] + n2[1]
        bl = math.hypot(bx, by)
        if bl < 1e-9:
            out.append((p1[0] + n1[0] * dist_out, p1[1] + n1[1] * dist_out))
            continue
        bx /= bl
        by /= bl
        cos_half = bx * n1[0] + by * n1[1]
        scale = dist_out / max(cos_half, 0.2)
        out.append((p1[0] + bx * scale, p1[1] + by * scale))
    return out
