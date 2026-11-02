"""Pure Python constrained Delaunay triangulation.

* Unconstrained triangulation: port of the sweep-hull algorithm of
  *Delaunator* (mapbox, ISC licence, (c) Vladimir Agafonkin) - O(n log n).
* Constraints (breaklines, boundaries): Sloan's edge-flipping insertion
  followed by local Delaunay restoration.
* Clipping: removal of triangles outside boundary / inside hole rings
  (depth flood fill) and optional "max edge length" trimming of the hull.

Coordinates should be shifted near the origin by the caller (see tin.py) to
keep floating point precision with large survey coordinates.

Half-edge conventions (identical to Delaunator):
    triangle t owns half-edges 3t, 3t+1, 3t+2
    half-edge e starts at vertex ``tri[e]`` and ends at ``tri[next(e)]``
    ``half[e]`` is the opposite half-edge or -1 on the hull
"""
from __future__ import annotations

import math
from collections import deque
from fractions import Fraction
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

EPSILON = 2.0 ** -52


class TriangulationError(Exception):
    """Raised when the input cannot be triangulated."""


def _nxt(e: int) -> int:
    return e - 2 if e % 3 == 2 else e + 1


def _prv(e: int) -> int:
    return e + 2 if e % 3 == 0 else e - 1


_CCW_ERR = (3.0 + 16.0 * 2.0 ** -53) * 2.0 ** -53
_ICC_ERR = 2.0e-15   # conservative bound for the incircle expression below


def _ccw(ax, ay, bx, by, cx, cy):
    """Robust orientation: > 0 counter-clockwise, < 0 clockwise, 0 collinear (exact sign).

    Fast floating point evaluation with a forward error bound (Shewchuk); falls back to
    exact rational arithmetic only for nearly degenerate input.
    """
    detleft = (bx - ax) * (cy - ay)
    detright = (by - ay) * (cx - ax)
    det = detleft - detright
    if abs(det) > _CCW_ERR * (abs(detleft) + abs(detright)):
        return det
    F = Fraction
    exact = (F(bx) - F(ax)) * (F(cy) - F(ay)) - (F(by) - F(ay)) * (F(cx) - F(ax))
    if exact == 0:
        return 0.0
    v = float(exact)
    return v if v != 0.0 else (5e-324 if exact > 0 else -5e-324)


def _in_circle(ax, ay, bx, by, cx, cy, px, py) -> bool:
    """Delaunator's incircle test (True = p inside the circumcircle of the clockwise triangle abc), robust."""
    dx = ax - px
    dy = ay - py
    ex = bx - px
    ey = by - py
    fx = cx - px
    fy = cy - py
    ap = dx * dx + dy * dy
    bp = ex * ex + ey * ey
    cp = fx * fx + fy * fy
    det = dx * (ey * cp - bp * fy) - dy * (ex * cp - bp * fx) + ap * (ex * fy - ey * fx)
    perm = (abs(dx) * (abs(ey * cp) + abs(bp * fy)) + abs(dy) * (abs(ex * cp) + abs(bp * fx))
            + ap * (abs(ex * fy) + abs(ey * fx)))
    if abs(det) > _ICC_ERR * perm:
        return det < 0
    F = Fraction
    Dx, Dy = F(ax) - F(px), F(ay) - F(py)
    Ex, Ey = F(bx) - F(px), F(by) - F(py)
    Fx, Fy = F(cx) - F(px), F(cy) - F(py)
    Ap, Bp, Cp = Dx * Dx + Dy * Dy, Ex * Ex + Ey * Ey, Fx * Fx + Fy * Fy
    return Dx * (Ey * Cp - Bp * Fy) - Dy * (Ex * Cp - Bp * Fx) + Ap * (Ex * Fy - Ey * Fx) < 0


def _circumradius(ax, ay, bx, by, cx, cy) -> float:
    dx = bx - ax
    dy = by - ay
    ex = cx - ax
    ey = cy - ay
    bl = dx * dx + dy * dy
    cl = ex * ex + ey * ey
    den = dx * ey - dy * ex
    if den == 0.0:
        return math.inf
    d = 0.5 / den
    x = (ey * bl - dy * cl) * d
    y = (dx * cl - ex * bl) * d
    return x * x + y * y


def _circumcenter(ax, ay, bx, by, cx, cy):
    dx = bx - ax
    dy = by - ay
    ex = cx - ax
    ey = cy - ay
    bl = dx * dx + dy * dy
    cl = ex * ex + ey * ey
    d = 0.5 / (dx * ey - dy * ex)
    return ax + (ey * bl - dy * cl) * d, ay + (dx * cl - ex * bl) * d


def _pseudo_angle(dx, dy):
    s = abs(dx) + abs(dy)
    if s == 0.0:
        return 0.0
    p = dx / s
    return (3.0 - p if dy > 0 else 1.0 + p) / 4.0


class Delaunator:
    """Unconstrained Delaunay triangulation of 2D points (sweep-hull)."""

    def __init__(self, xs: Sequence[float], ys: Sequence[float]):
        n = len(xs)
        self.xs = xs
        self.ys = ys
        self.n = n
        max_tri = max(2 * n - 5, 0)
        self.tri: List[int] = [0] * (max_tri * 3)
        self.half: List[int] = [0] * (max_tri * 3)
        self.tlen = 0
        self.hull: List[int] = []
        if n < 3:
            self.tri = []
            self.half = []
            return
        self._build()

    # -- helpers ---------------------------------------------------------
    def _link(self, a: int, b: int) -> None:
        self.half[a] = b
        if b != -1:
            self.half[b] = a

    def _add_triangle(self, i0, i1, i2, a, b, c) -> int:
        t = self.tlen
        tri = self.tri
        tri[t] = i0
        tri[t + 1] = i1
        tri[t + 2] = i2
        self._link(t, a)
        self._link(t + 1, b)
        self._link(t + 2, c)
        self.tlen += 3
        return t

    def _hash_key(self, x, y) -> int:
        return int(math.floor(_pseudo_angle(x - self._cx, y - self._cy) * self._hash_size)) % self._hash_size

    def _legalize(self, a: int) -> int:
        tri = self.tri
        half = self.half
        xs = self.xs
        ys = self.ys
        stack = self._edge_stack
        i = 0
        ar = 0
        while True:
            b = half[a]
            a0 = a - a % 3
            ar = a0 + (a + 2) % 3
            if b == -1:
                if i == 0:
                    break
                i -= 1
                a = stack[i]
                continue
            b0 = b - b % 3
            al = a0 + (a + 1) % 3
            bl = b0 + (b + 2) % 3
            p0 = tri[ar]
            pr = tri[a]
            pl = tri[al]
            p1 = tri[bl]
            if _in_circle(xs[p0], ys[p0], xs[pr], ys[pr], xs[pl], ys[pl], xs[p1], ys[p1]):
                tri[a] = p1
                tri[b] = p0
                hbl = half[bl]
                if hbl == -1:
                    e = self._hull_start
                    while True:
                        if self._hull_tri[e] == bl:
                            self._hull_tri[e] = a
                            break
                        e = self._hull_prev[e]
                        if e == self._hull_start:
                            break
                self._link(a, hbl)
                self._link(b, half[ar])
                self._link(ar, bl)
                br = b0 + (b + 1) % 3
                if i < len(stack):
                    stack[i] = br
                    i += 1
                else:
                    stack.append(br)
                    i += 1
            else:
                if i == 0:
                    break
                i -= 1
                a = stack[i]
        return ar

    # -- main --------------------------------------------------------------
    def _build(self) -> None:
        xs = self.xs
        ys = self.ys
        n = self.n
        self._edge_stack: List[int] = [0] * 512
        self._hash_size = max(1, int(math.ceil(math.sqrt(n))))
        hull_prev = [0] * n
        hull_next = [0] * n
        hull_tri = [0] * n
        hull_hash = [-1] * self._hash_size
        self._hull_prev = hull_prev
        self._hull_next = hull_next
        self._hull_tri = hull_tri

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0

        i0 = min(range(n), key=lambda i: (xs[i] - cx) ** 2 + (ys[i] - cy) ** 2)
        i0x, i0y = xs[i0], ys[i0]
        i1 = -1
        min_dist = math.inf
        for i in range(n):
            if i == i0:
                continue
            d = (xs[i] - i0x) ** 2 + (ys[i] - i0y) ** 2
            if 0 < d < min_dist:
                i1 = i
                min_dist = d
        if i1 < 0:
            raise TriangulationError("all points are identical")
        i1x, i1y = xs[i1], ys[i1]
        min_radius = math.inf
        i2 = -1
        for i in range(n):
            if i == i0 or i == i1:
                continue
            r = _circumradius(i0x, i0y, i1x, i1y, xs[i], ys[i])
            if r < min_radius:
                i2 = i
                min_radius = r
        if min_radius == math.inf or i2 < 0:
            raise TriangulationError("all points are collinear - a terrain needs a 2D spread of points")
        i2x, i2y = xs[i2], ys[i2]

        if _ccw(i0x, i0y, i1x, i1y, i2x, i2y) > 0:
            i1, i2 = i2, i1
            i1x, i1y, i2x, i2y = i2x, i2y, i1x, i1y

        self._cx, self._cy = _circumcenter(i0x, i0y, i1x, i1y, i2x, i2y)
        ccx, ccy = self._cx, self._cy
        dists = [(xs[i] - ccx) ** 2 + (ys[i] - ccy) ** 2 for i in range(n)]
        ids = sorted(range(n), key=dists.__getitem__)

        self._hull_start = i0
        hull_size = 3
        hull_next[i0] = hull_prev[i2] = i1
        hull_next[i1] = hull_prev[i0] = i2
        hull_next[i2] = hull_prev[i1] = i0
        hull_tri[i0] = 0
        hull_tri[i1] = 1
        hull_tri[i2] = 2
        hull_hash[self._hash_key(i0x, i0y)] = i0
        hull_hash[self._hash_key(i1x, i1y)] = i1
        hull_hash[self._hash_key(i2x, i2y)] = i2

        self.tlen = 0
        self._add_triangle(i0, i1, i2, -1, -1, -1)

        xp = yp = 0.0
        hs = self._hash_size
        for k, i in enumerate(ids):
            x = xs[i]
            y = ys[i]
            if k > 0 and abs(x - xp) <= EPSILON and abs(y - yp) <= EPSILON:
                continue
            xp = x
            yp = y
            if i == i0 or i == i1 or i == i2:
                continue

            start = 0
            key = self._hash_key(x, y)
            for j in range(hs):
                start = hull_hash[(key + j) % hs]
                if start != -1 and start != hull_next[start]:
                    break
            start = hull_prev[start]
            e = start
            while True:
                q = hull_next[e]
                if _ccw(x, y, xs[e], ys[e], xs[q], ys[q]) > 0:
                    break
                e = q
                if e == start:
                    e = -1
                    break
            if e == -1:
                continue

            t = self._add_triangle(e, i, hull_next[e], -1, -1, hull_tri[e])
            hull_tri[i] = self._legalize(t + 2)
            hull_tri[e] = t
            hull_size += 1

            nn = hull_next[e]
            while True:
                q = hull_next[nn]
                if not _ccw(x, y, xs[nn], ys[nn], xs[q], ys[q]) > 0:
                    break
                t = self._add_triangle(nn, i, q, hull_tri[i], -1, hull_tri[nn])
                hull_tri[i] = self._legalize(t + 2)
                hull_next[nn] = nn
                hull_size -= 1
                nn = q

            if e == start:
                while True:
                    q = hull_prev[e]
                    if not _ccw(x, y, xs[q], ys[q], xs[e], ys[e]) > 0:
                        break
                    t = self._add_triangle(q, i, e, -1, hull_tri[e], hull_tri[q])
                    self._legalize(t + 2)
                    hull_tri[q] = t
                    hull_next[e] = e
                    hull_size -= 1
                    e = q

            self._hull_start = hull_prev[i] = e
            hull_next[e] = hull_prev[nn] = i
            hull_next[i] = nn
            hull_hash[self._hash_key(x, y)] = i
            hull_hash[self._hash_key(xs[e], ys[e])] = e

        hull = []
        e = self._hull_start
        for _ in range(hull_size):
            hull.append(e)
            e = hull_next[e]
        self.hull = hull
        del self.tri[self.tlen:]
        del self.half[self.tlen:]


class ConstrainedTriangulation:
    """Delaunay triangulation with constrained edges and clipping.

    After construction call :meth:`insert_constraint` for each segment, then
    :meth:`triangles` to get CCW triangles (vertex index triples).
    """

    def __init__(self, xs: Sequence[float], ys: Sequence[float]):
        self.xs = list(xs)
        self.ys = list(ys)
        d = Delaunator(self.xs, self.ys)
        self.tri = d.tri
        self.half = d.half
        self.hull = d.hull
        self.alive = [True] * (len(self.tri) // 3)
        self.fixed: Set[Tuple[int, int]] = set()
        self.region_edges: Set[Tuple[int, int]] = set()
        self.vert_edge = [-1] * len(self.xs)
        for e, v in enumerate(self.tri):
            if self.vert_edge[v] == -1 or self.half[e] == -1:
                # prefer hull edges so that rotations start at the boundary
                self.vert_edge[v] = e
        self.failed_constraints: List[Tuple[int, int]] = []
        self.failed_region = 0
        span = max(max(self.xs) - min(self.xs), max(self.ys) - min(self.ys), 1e-9)
        self._snap = span * 1e-7   # vertices closer than this to a constraint lie on it

    # -- topology helpers -------------------------------------------------
    def _edges_around(self, v: int) -> Iterable[int]:
        start = self.vert_edge[v]
        if start < 0:
            return
        half = self.half
        e = start
        while True:
            yield e
            t = half[_prv(e)]
            if t == -1:
                break
            e = t
            if e == start:
                return
        e = start
        while True:
            t = half[e]
            if t == -1:
                return
            e = _nxt(t)
            if e == start:
                return
            yield e

    def find_edge(self, u: int, v: int) -> int:
        tri = self.tri
        for e in self._edges_around(u):
            if tri[_nxt(e)] == v:
                return e
            p = _prv(e)
            if tri[p] == v:
                return p
        return -1

    def _flip(self, a: int) -> int:
        """Flip the edge of half-edge ``a`` (must be interior). Returns new diagonal half-edge."""
        tri = self.tri
        half = self.half
        b = half[a]
        a0 = a - a % 3
        b0 = b - b % 3
        al = a0 + (a + 1) % 3
        ar = a0 + (a + 2) % 3
        bl = b0 + (b + 2) % 3
        br = b0 + (b + 1) % 3
        p0 = tri[ar]
        pr = tri[a]
        pl = tri[al]
        p1 = tri[bl]
        tri[a] = p1
        tri[b] = p0
        hbl = half[bl]
        har = half[ar]
        half[a] = hbl
        if hbl != -1:
            half[hbl] = a
        half[b] = har
        if har != -1:
            half[har] = b
        half[ar] = bl
        half[bl] = ar
        ve = self.vert_edge
        ve[p0] = ar if half[b] != -1 else b
        ve[p1] = bl if half[a] != -1 else a
        ve[pr] = br
        ve[pl] = al
        # keep hull-edge preference for boundary vertices
        if half[br] == -1:
            ve[pr] = br
        if half[al] == -1:
            ve[pl] = al
        if half[b] == -1:
            ve[p0] = b
        if half[a] == -1:
            ve[p1] = a
        return ar

    @staticmethod
    def _key(u: int, v: int) -> Tuple[int, int]:
        return (u, v) if u < v else (v, u)

    def _orient(self, a: int, b: int, c: int) -> float:
        """Orientation with a scale-relative collinearity tolerance (sin(angle) ~ 1e-10)."""
        xs = self.xs
        ys = self.ys
        ax, ay = xs[a], ys[a]
        val = _ccw(ax, ay, xs[b], ys[b], xs[c], ys[c])
        tol = 1e-10 * (abs(xs[b] - ax) + abs(ys[b] - ay)) * (abs(xs[c] - ax) + abs(ys[c] - ay))
        if abs(val) <= tol:
            return 0.0
        return val

    def _side(self, a: int, b: int, c: int, lab: float) -> float:
        """Side of c relative to segment ab; 0 when c is within the snap distance of the line."""
        xs = self.xs
        ys = self.ys
        val = _ccw(xs[a], ys[a], xs[b], ys[b], xs[c], ys[c])
        if abs(val) <= self._snap * lab:
            return 0.0
        return val

    def _on_segment(self, a: int, b: int, c: int) -> bool:
        """c strictly between a and b (assuming collinear)."""
        xs = self.xs
        ys = self.ys
        dot = (xs[c] - xs[a]) * (xs[b] - xs[a]) + (ys[c] - ys[a]) * (ys[b] - ys[a])
        len2 = (xs[b] - xs[a]) ** 2 + (ys[b] - ys[a]) ** 2
        return 0.0 < dot < len2

    def _is_delaunay(self, e: int) -> bool:
        tri = self.tri
        b = self.half[e]
        if b == -1:
            return True
        xs = self.xs
        ys = self.ys
        a0 = e - e % 3
        ar = a0 + (e + 2) % 3
        al = a0 + (e + 1) % 3
        bl = (b - b % 3) + (b + 2) % 3
        p0 = tri[ar]
        pr = tri[e]
        pl = tri[al]
        p1 = tri[bl]
        return not _in_circle(xs[p0], ys[p0], xs[pr], ys[pr], xs[pl], ys[pl], xs[p1], ys[p1])

    # -- constraints --------------------------------------------------------
    def insert_constraint(self, a: int, b: int, region: bool = False) -> bool:
        """Force segment a-b into the triangulation. Returns False if it failed."""
        todo = [(a, b)]
        ok = True
        guard = 0
        while todo:
            guard += 1
            if guard > 100000:
                return False
            u, v = todo.pop()
            if u == v:
                continue
            res = self._insert_segment(u, v)
            if res is None:
                self.failed_constraints.append((u, v))
                if region:
                    self.failed_region += 1
                ok = False
                continue
            if isinstance(res, tuple):
                # split at collinear vertex
                c = res[1]
                todo.append((c, v))
                todo.append((u, c))
                continue
            key = self._key(u, v)
            self.fixed.add(key)
            if region:
                self.region_edges.add(key)
        return ok

    def _insert_segment(self, a: int, b: int):
        """Returns True on success, ('split', c) to split, or None on failure."""
        if self.find_edge(a, b) >= 0:
            return True
        tri = self.tri
        half = self.half
        lab = math.hypot(self.xs[b] - self.xs[a], self.ys[b] - self.ys[a])
        # 1) find first crossed edge around a
        crossed: List[Tuple[int, int]] = []
        first = -1
        for e in self._edges_around(a):
            u = tri[_nxt(e)]
            w = tri[_prv(e)]
            ou = self._side(a, b, u, lab)
            ow = self._side(a, b, w, lab)
            if ou == 0.0 and self._on_segment(a, b, u):
                return ("split", u)
            if ow == 0.0 and self._on_segment(a, b, w):
                return ("split", w)
            if (ou > 0 > ow) or (ou < 0 < ow):
                # the direction a->b must lie inside the angle (u, a, w) of this triangle
                xs = self.xs
                ys = self.ys
                ux, uy = xs[u] - xs[a], ys[u] - ys[a]
                wx, wy = xs[w] - xs[a], ys[w] - ys[a]
                dx, dy = xs[b] - xs[a], ys[b] - ys[a]
                s_all = ux * wy - uy * wx
                s1 = ux * dy - uy * dx
                if s_all * s1 > 0:
                    first = _nxt(e)
                    break
        if first < 0:
            return None
        c = first
        guard = 0
        while True:
            guard += 1
            if guard > len(tri):
                return None
            u = tri[c]
            w = tri[_nxt(c)]
            if self._key(u, w) in self.fixed:
                # crossing another constraint: split at intersection is not supported,
                # keep the earlier constraint and give up on this one
                return None
            crossed.append((u, w))
            t = half[c]
            if t == -1:
                return None
            v = tri[_prv(t)]
            if v == b:
                break
            ov = self._side(a, b, v, lab)
            if ov == 0.0:
                if self._on_segment(a, b, v):
                    # flip the crossed edges up to v and continue from there
                    if not self._sloan(a, v, crossed):
                        return None
                    return ("split", v)
                return None
            ou = self._side(a, b, u, lab)
            # t goes w -> u, next(t): u -> v, prev(t): v -> w
            if (ov > 0) == (ou > 0):
                c = _prv(t)
            else:
                c = _nxt(t)
        if not self._sloan(a, b, crossed):
            return None
        return True

    def _sloan(self, a: int, b: int, crossed: List[Tuple[int, int]]) -> bool:
        queue = deque(crossed)
        lab = math.hypot(self.xs[b] - self.xs[a], self.ys[b] - self.ys[a])
        new_edges: List[Tuple[int, int]] = []
        tri = self.tri
        stall = 0
        while queue:
            u, w = queue.popleft()
            e = self.find_edge(u, w)
            if e < 0:
                stall = 0
                continue
            f = self.half[e]
            if f == -1:
                return False
            r = tri[_prv(e)]
            s = tri[_prv(f)]
            o1 = self._orient(r, s, u)
            o2 = self._orient(r, s, w)
            if o1 * o2 < 0:
                ne = self._flip(e)
                p = tri[ne]
                q = tri[_nxt(ne)]
                stall = 0
                if (p == a and q == b) or (p == b and q == a):
                    continue
                if p in (a, b) or q in (a, b):
                    new_edges.append((p, q))
                    continue
                op = self._side(a, b, p, lab)
                oq = self._side(a, b, q, lab)
                if op * oq < 0 and self._orient(p, q, a) * self._orient(p, q, b) < 0:
                    queue.append((p, q))
                else:
                    new_edges.append((p, q))
            else:
                queue.append((u, w))
                stall += 1
                if stall > len(queue) + 2:
                    return False
        if self.find_edge(a, b) < 0:
            return False
        key_ab = self._key(a, b)
        # restore Delaunay property on new edges
        changed = True
        loops = 0
        while changed and loops < 50:
            changed = False
            loops += 1
            for idx, (p, q) in enumerate(new_edges):
                if self._key(p, q) == key_ab or self._key(p, q) in self.fixed:
                    continue
                e = self.find_edge(p, q)
                if e < 0 or self.half[e] == -1:
                    continue
                if not self._is_delaunay(e):
                    ne = self._flip(e)
                    new_edges[idx] = (tri[ne], tri[_nxt(ne)])
                    changed = True
        return True

    # -- clipping -------------------------------------------------------------
    def clip_regions(self, rings: Optional[Sequence[Sequence[Tuple[float, float]]]] = None) -> None:
        """Keep triangles at odd depth relative to region constraints (boundary/holes).

        Depth 0 = outside the outer boundary. Crossing a region edge increments the depth.
        If a region segment could not be enforced the flood fill would leak, so the triangles
        are then classified by an even-odd point-in-polygon test of their centroid against
        ``rings`` (same coordinate frame as the triangulation).
        """
        if self.failed_region and rings:
            self._clip_by_rings(rings)
            return
        if not self.region_edges:
            return
        ntri = len(self.tri) // 3
        depth = [-1] * ntri
        tri = self.tri
        half = self.half
        region = self.region_edges
        seeds = deque()
        for e in range(len(tri)):
            if half[e] == -1:
                t = e // 3
                key = self._key(tri[e], tri[_nxt(e)])
                d = 1 if key in region else 0
                if depth[t] == -1 or d < depth[t]:
                    depth[t] = d
        # 0-1 BFS
        order = sorted((t for t in range(ntri) if depth[t] >= 0), key=lambda t: depth[t])
        seeds.extend(order)
        while seeds:
            t = seeds.popleft()
            dt = depth[t]
            for k in range(3):
                e = 3 * t + k
                f = half[e]
                if f == -1:
                    continue
                n = f // 3
                key = self._key(tri[e], tri[_nxt(e)])
                nd = dt + (1 if key in region else 0)
                if depth[n] == -1 or nd < depth[n]:
                    depth[n] = nd
                    if key in region:
                        seeds.append(n)
                    else:
                        seeds.appendleft(n)
        for t in range(ntri):
            if depth[t] % 2 == 0:
                self.alive[t] = False

    def _clip_by_rings(self, rings: Sequence[Sequence[Tuple[float, float]]]) -> None:
        index = RingIndex(rings)
        tri = self.tri
        xs = self.xs
        ys = self.ys
        for t in range(len(tri) // 3):
            if not self.alive[t]:
                continue
            a, b, c = tri[3 * t], tri[3 * t + 1], tri[3 * t + 2]
            if not index.inside((xs[a] + xs[b] + xs[c]) / 3.0, (ys[a] + ys[b] + ys[c]) / 3.0):
                self.alive[t] = False

    def trim_long_edges(self, max_len: float) -> int:
        """Remove boundary triangles that have an exposed edge longer than max_len."""
        if max_len <= 0:
            return 0
        tri = self.tri
        half = self.half
        xs = self.xs
        ys = self.ys
        alive = self.alive
        ml2 = max_len * max_len

        def exposed(e: int) -> bool:
            f = half[e]
            return f == -1 or not alive[f // 3]

        queue = deque(t for t in range(len(tri) // 3) if alive[t] and any(exposed(3 * t + k) for k in range(3)))
        removed = 0
        while queue:
            t = queue.popleft()
            if not alive[t]:
                continue
            kill = False
            for k in range(3):
                e = 3 * t + k
                if exposed(e):
                    if self._key(tri[e], tri[_nxt(e)]) in self.fixed:
                        continue
                    a = tri[e]
                    b = tri[_nxt(e)]
                    if (xs[a] - xs[b]) ** 2 + (ys[a] - ys[b]) ** 2 > ml2:
                        kill = True
                        break
            if kill:
                alive[t] = False
                removed += 1
                for k in range(3):
                    f = half[3 * t + k]
                    if f != -1 and alive[f // 3]:
                        queue.append(f // 3)
        return removed

    def triangles(self) -> List[Tuple[int, int, int]]:
        """Alive triangles, counter-clockwise (y up)."""
        tri = self.tri
        out = []
        for t, ok in enumerate(self.alive):
            if ok:
                a = tri[3 * t]
                b = tri[3 * t + 1]
                c = tri[3 * t + 2]
                out.append((a, c, b))  # Delaunator output is clockwise for y-up axes
        return out


class RingIndex:
    """Even-odd point-in-polygon test for many rings, accelerated by horizontal row buckets."""

    def __init__(self, rings: Sequence[Sequence[Tuple[float, float]]], rows: int = 0):
        edges = []
        for ring in rings:
            n = len(ring)
            for i in range(n):
                x1, y1 = ring[i][0], ring[i][1]
                x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
                if y1 != y2:
                    edges.append((x1, y1, x2, y2))
        self.edges = edges
        ys = [e[1] for e in edges] + [e[3] for e in edges] or [0.0, 1.0]
        self.y0 = min(ys)
        self.y1 = max(ys)
        self.rows = rows or max(1, min(4096, len(edges) // 4 + 1))
        self.h = (self.y1 - self.y0) / self.rows or 1.0
        self.buckets: List[List[int]] = [[] for _ in range(self.rows)]
        for k, (x1, y1, x2, y2) in enumerate(edges):
            r0 = int((min(y1, y2) - self.y0) / self.h)
            r1 = int((max(y1, y2) - self.y0) / self.h)
            for r in range(max(0, r0), min(self.rows - 1, r1) + 1):
                self.buckets[r].append(k)

    def inside(self, x: float, y: float) -> bool:
        if y < self.y0 or y > self.y1:
            return False
        r = min(self.rows - 1, int((y - self.y0) / self.h))
        res = False
        for k in self.buckets[r]:
            x1, y1, x2, y2 = self.edges[k]
            if (y1 > y) != (y2 > y):
                if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                    res = not res
        return res


def triangulate(xs: Sequence[float], ys: Sequence[float],
                constraints: Optional[Iterable[Tuple[int, int]]] = None,
                region_constraints: Optional[Iterable[Tuple[int, int]]] = None,
                max_edge: float = 0.0) -> Tuple[List[Tuple[int, int, int]], List[Tuple[int, int]]]:
    """Convenience wrapper. Returns (triangles, failed_constraints)."""
    ct = ConstrainedTriangulation(xs, ys)
    for (a, b) in region_constraints or []:
        ct.insert_constraint(a, b, region=True)
    for (a, b) in constraints or []:
        ct.insert_constraint(a, b)
    ct.clip_regions()  # no ring fallback available in this low level helper
    if max_edge > 0:
        ct.trim_long_edges(max_edge)
    return ct.triangles(), ct.failed_constraints
