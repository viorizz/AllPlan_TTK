"""Point cloud / TIN reduction: grid thinning, spike removal and tolerance-driven simplification."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from .tin import TIN, build_tin

Point3 = Tuple[float, float, float]


def thin_grid(points: Sequence[Sequence[float]], cell: float, mode: str = "mean") -> List[Point3]:
    """Keep one point per square cell. mode: mean | min | max | median | nearest (to cell centre)."""
    if cell <= 0:
        return [(p[0], p[1], p[2]) for p in points]
    buckets: Dict[Tuple[int, int], List[Sequence[float]]] = defaultdict(list)
    for p in points:
        buckets[(int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell)))].append(p)
    out: List[Point3] = []
    for (ix, iy), pts in buckets.items():
        if mode == "min":
            p = min(pts, key=lambda q: q[2])
            out.append((p[0], p[1], p[2]))
        elif mode == "max":
            p = max(pts, key=lambda q: q[2])
            out.append((p[0], p[1], p[2]))
        elif mode == "median":
            s = sorted(pts, key=lambda q: q[2])
            p = s[len(s) // 2]
            out.append((p[0], p[1], p[2]))
        elif mode == "nearest":
            cx = (ix + 0.5) * cell
            cy = (iy + 0.5) * cell
            p = min(pts, key=lambda q: (q[0] - cx) ** 2 + (q[1] - cy) ** 2)
            out.append((p[0], p[1], p[2]))
        else:
            n = len(pts)
            out.append((sum(q[0] for q in pts) / n, sum(q[1] for q in pts) / n, sum(q[2] for q in pts) / n))
    return out


def find_spikes(tin: TIN, threshold: float) -> List[int]:
    """Vertices whose elevation differs from the median of their neighbours by more than threshold."""
    nb = tin.vertex_neighbors()
    out = []
    for v, ns in enumerate(nb):
        if len(ns) < 3:
            continue
        zs = sorted(tin.points[w][2] for w in ns)
        m = len(zs)
        med = zs[m // 2] if m % 2 else 0.5 * (zs[m // 2 - 1] + zs[m // 2])
        if abs(tin.points[v][2] - med) > threshold:
            out.append(v)
    return out


def remove_spikes(points: Sequence[Sequence[float]], threshold: float, iterations: int = 2) -> Tuple[List[Point3], int]:
    pts = [(p[0], p[1], p[2]) for p in points]
    removed = 0
    for _ in range(max(1, iterations)):
        tin = build_tin(pts)
        spikes = set(find_spikes(tin, threshold))
        if not spikes:
            break
        removed += len(spikes)
        pts = [p for i, p in enumerate(tin.points) if i not in spikes]
    return pts, removed


def simplify_points(points: Sequence[Sequence[float]], tolerance: float, max_iterations: int = 40,
                    max_points: int = 0, log=None) -> Tuple[List[Point3], float]:
    """Reduce a dense point set to a TIN that stays within ``tolerance`` (vertical) of all input points.

    Greedy refinement in batches: start from the convex hull, then repeatedly add the worst
    point of every triangle whose error exceeds the tolerance.
    Returns (kept points, max remaining error).
    """
    pts = [(float(p[0]), float(p[1]), float(p[2])) for p in points]
    if len(pts) < 4:
        return pts, 0.0
    full = build_tin(pts)
    pts = full.points
    hull_ids = sorted({i for ring in full.boundary_rings() for i in ring})
    kept = set(hull_ids)
    if len(kept) < 3:
        kept.update(range(min(3, len(pts))))
    worst = math.inf
    for it in range(max_iterations):
        sub = build_tin([pts[i] for i in sorted(kept)])
        best_per_tri: Dict[int, Tuple[float, int]] = {}
        worst = 0.0
        for i, p in enumerate(pts):
            if i in kept:
                continue
            t = sub.locate(p[0], p[1])
            if t < 0:
                kept.add(i)
                continue
            a, b, c = sub.triangles[t]
            pa, pb, pc = sub.points[a], sub.points[b], sub.points[c]
            from .tin import _barycentric
            bc = _barycentric(p[0], p[1], pa, pb, pc)
            if bc is None:
                continue
            z = bc[0] * pa[2] + bc[1] * pb[2] + bc[2] * pc[2]
            err = abs(p[2] - z)
            if err > worst:
                worst = err
            if err > tolerance:
                cur = best_per_tri.get(t)
                if cur is None or err > cur[0]:
                    best_per_tri[t] = (err, i)
        if log:
            log(f"simplify iteration {it + 1}: {len(kept)} points, max error {worst:.4f}")
        if not best_per_tri:
            break
        for _, i in best_per_tri.values():
            kept.add(i)
        if max_points and len(kept) >= max_points:
            break
    return [pts[i] for i in sorted(kept)], worst
