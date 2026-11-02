"""Conversion between the terrain core (metres, plain tuples) and Allplan objects (millimetres).

Every Allplan call that is not 100 % certain for all versions is wrapped so that a
failure is logged with the details needed to fix it, instead of crashing the tool.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import NemAll_Python_BaseElements as AllplanBaseElements  # type: ignore
import NemAll_Python_BasisElements as AllplanBasisElements  # type: ignore
import NemAll_Python_Geometry as AllplanGeo  # type: ignore

from ..core.tin import TIN, TerrainError, build_tin, tin_from_mesh
from . import log

MM = 1000.0          # metres -> Allplan internal millimetres
Point3 = Tuple[float, float, float]
RGB = Tuple[int, int, int]


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------
def p3(p: Sequence[float]) -> "AllplanGeo.Point3D":
    return AllplanGeo.Point3D(p[0] * MM, p[1] * MM, p[2] * MM)


def p2(x: float, y: float) -> "AllplanGeo.Point2D":
    return AllplanGeo.Point2D(x * MM, y * MM)


def from_mm(p) -> Point3:
    return (p.X / MM, p.Y / MM, getattr(p, "Z", 0.0) / MM)


# ---------------------------------------------------------------------------
# properties & colours
# ---------------------------------------------------------------------------
_COLOR_CACHE: Dict[RGB, int] = {}
_COLOR_FAIL_LOGGED = False


def color_id(rgb: RGB) -> int:
    """Nearest Allplan colour number for an RGB value."""
    global _COLOR_FAIL_LOGGED
    rgb = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    if rgb in _COLOR_CACHE:
        return _COLOR_CACHE[rgb]
    cid = 1
    try:
        cid = int(AllplanBaseElements.GetIdByColor(AllplanBasisElements.ARGB(rgb[0], rgb[1], rgb[2], 0)))
    except Exception as exc:  # noqa: BLE001
        if not _COLOR_FAIL_LOGGED:
            log.warn(f"GetIdByColor failed ({exc}); using colour 1. Analysis colours will not be shown.")
            _COLOR_FAIL_LOGGED = True
    _COLOR_CACHE[rgb] = cid
    return cid


_PROP_FIELDS = ("Pen", "Stroke", "Color", "Layer", "ColorByLayer", "PenByLayer", "StrokeByLayer",
                "DrawOrder", "HelpConstruction")


def props(base=None, rgb: Optional[RGB] = None, color: Optional[int] = None):
    """Copy of ``base`` common properties (or global ones) with an optional colour override."""
    cp = AllplanBaseElements.CommonProperties()
    try:
        cp.GetGlobalProperties()
    except Exception:  # noqa: BLE001
        pass
    if base is not None:
        for f in _PROP_FIELDS:
            try:
                setattr(cp, f, getattr(base, f))
            except Exception:  # noqa: BLE001
                pass
    if rgb is not None:
        color = color_id(rgb)
    if color is not None:
        try:
            cp.ColorByLayer = False
        except Exception:  # noqa: BLE001
            pass
        cp.Color = int(color)
    return cp


# ---------------------------------------------------------------------------
# polyhedron (mesh) creation
# ---------------------------------------------------------------------------
_PTYPE = None


def _polyhedron_type():
    global _PTYPE
    if _PTYPE is not None:
        return _PTYPE
    names = {}
    try:
        names = dict(AllplanGeo.PolyhedronType.names)
    except Exception:  # noqa: BLE001
        pass
    for key in ("tFaces", "tSurface", "tShell"):
        if key in names:
            _PTYPE = names[key]
            break
    else:
        cand = [k for k in names if "face" in k.lower() or "surf" in k.lower()]
        if cand:
            _PTYPE = names[cand[0]]
        elif "tVolume" in names:
            _PTYPE = names["tVolume"]
    log.debug(f"Polyhedron types available: {list(names.keys())}; using {_PTYPE}")
    return _PTYPE


def _order_triangles(tris: List[Tuple[Point3, Point3, Point3]]) -> List[Tuple[Point3, Point3, Point3]]:
    """Spatially coherent order so that chunks form compact patches."""
    if len(tris) < 2:
        return tris
    xs = [(t[0][0] + t[1][0] + t[2][0]) / 3 for t in tris]
    ys = [(t[0][1] + t[1][1] + t[2][1]) / 3 for t in tris]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    n = max(1, int(math.sqrt(len(tris) / 2000.0)) + 1)
    cw = (x1 - x0) / n or 1.0
    ch = (y1 - y0) / n or 1.0

    def key(i):
        cx = min(int((xs[i] - x0) / cw), n - 1)
        cy = min(int((ys[i] - y0) / ch), n - 1)
        return (cy, cx if cy % 2 == 0 else n - 1 - cx)
    order = sorted(range(len(tris)), key=key)
    return [tris[i] for i in order]


def triangles_to_polyhedra(tris: Sequence[Tuple[Point3, Point3, Point3]], max_faces: int = 30000) -> List[object]:
    """Build one or more surface Polyhedron3D from 3D triangles (metres)."""
    tris = [t for t in tris if t is not None]
    if not tris:
        return []
    if len(tris) > max_faces:
        tris = _order_triangles(list(tris))
    out = []
    for start in range(0, len(tris), max_faces):
        chunk = tris[start:start + max_faces]
        vid: Dict[Tuple[float, float, float], int] = {}
        verts: List[Point3] = []
        faces: List[Tuple[int, int, int]] = []
        for t in chunk:
            ids = []
            for p in t:
                k = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
                i = vid.get(k)
                if i is None:
                    i = len(verts)
                    vid[k] = i
                    verts.append(p)
                ids.append(i)
            if len(set(ids)) == 3:
                faces.append((ids[0], ids[1], ids[2]))
        poly = mesh_to_polyhedron(verts, faces)
        if poly is not None:
            out.append(poly)
    return out


def tin_to_polyhedra(tin: TIN, max_faces: int = 30000) -> List[object]:
    if len(tin.triangles) <= max_faces:
        p = mesh_to_polyhedron(tin.points, tin.triangles)
        return [p] if p is not None else []
    return triangles_to_polyhedra([tin.tri_points(t) for t in range(len(tin.triangles))], max_faces)


def mesh_to_polyhedron(verts: Sequence[Point3], faces: Sequence[Tuple[int, int, int]]):
    """Indexed triangle mesh (metres) -> Allplan Polyhedron3D (mm). Returns None if invalid."""
    poly = AllplanGeo.Polyhedron3D()
    ptype = _polyhedron_type()
    if ptype is not None:
        try:
            poly.SetType(ptype)
        except Exception as exc:  # noqa: BLE001
            log.warn(f"Polyhedron3D.SetType failed: {exc}")
    builder = AllplanGeo.Polyhedron3DBuilder(poly)
    for v in verts:
        builder.AppendVertex(p3(v))
    edge_idx: Dict[Tuple[int, int], int] = {}
    for a, b, c in faces:
        for u, w in ((a, b), (b, c), (c, a)):
            key = (u, w) if u < w else (w, u)
            if key not in edge_idx:
                edge_idx[key] = len(edge_idx)
                poly.AppendEdge(AllplanGeo.GeometryEdge(key[0], key[1]))
    for a, b, c in faces:
        face = poly.CreateFace(3)
        for u, w in ((a, b), (b, c), (c, a)):
            key = (u, w) if u < w else (w, u)
            face.AppendEdge(AllplanGeo.OrientedEdge(edge_idx[key], u == key[0]))
    builder.Complete()
    valid = True
    try:
        valid = bool(poly.IsValid())
    except Exception:  # noqa: BLE001
        pass
    if not valid:
        log.warn(f"Allplan reports the polyhedron ({len(faces)} faces) as invalid; it is created anyway. "
                 "If nothing appears, please send the log.")
    return poly


def model3d(geo, cp):
    return AllplanBasisElements.ModelElement3D(cp, geo)


def model2d(geo, cp):
    return AllplanBasisElements.ModelElement2D(cp, geo)


def polyline3d(points: Sequence[Point3]):
    return AllplanGeo.Polyline3D([p3(p) for p in points])


def polyline2d(points: Sequence[Sequence[float]]):
    pl = AllplanGeo.Polyline2D()
    for p in points:
        pl += p2(p[0], p[1])
    return pl


def cross3d(p: Point3, size: float, cp) -> List[object]:
    x, y, z = p
    h = size / 2.0
    return [model3d(AllplanGeo.Line3D(p3((x - h, y, z)), p3((x + h, y, z))), cp),
            model3d(AllplanGeo.Line3D(p3((x, y - h, z)), p3((x, y + h, z))), cp)]


_ALIGN = {
    "left_bottom": "eLeftBottom", "left_center": "eLeftMiddle", "left_top": "eLeftTop",
    "center_bottom": "eMiddleBottom", "center_center": "eMiddleMiddle", "center_top": "eMiddleTop",
    "right_bottom": "eRightBottom", "right_center": "eRightMiddle", "right_top": "eRightTop",
}


def text(txt: str, x: float, y: float, height_mm: float, angle_deg: float, anchor: str, cp):
    """2D text at plan position (metres); height in mm on paper."""
    tp = AllplanBasisElements.TextProperties()
    tp.Height = float(height_mm)
    tp.Width = float(height_mm)
    try:
        names = AllplanBasisElements.TextAlignment.names
        tp.Alignment = names.get(_ALIGN.get(anchor, "eLeftBottom"), names.get("eLeftBottom"))
    except Exception:  # noqa: BLE001
        pass
    try:
        tp.TextAngle = AllplanGeo.Angle.FromDeg(float(angle_deg))
    except Exception:  # noqa: BLE001
        pass
    return AllplanBasisElements.TextElement(cp, tp, txt, p2(x, y))


def filling(regions, rgb: RGB, cp) -> List[object]:
    """Coloured 2D fillings for dissolved regions [(outer, holes), ...]."""
    out = []
    fp = AllplanBasisElements.FillingProperties()
    col = AllplanBasisElements.ARGB(int(rgb[0]), int(rgb[1]), int(rgb[2]), 0)
    fp.FirstColor = col
    try:
        fp.SecondColor = col
        fp.UseGradientFilling = False
    except Exception:  # noqa: BLE001
        pass
    for outer, holes in regions:
        poly = AllplanGeo.Polygon2D()
        for ring in [outer] + list(holes):
            if len(ring) < 3:
                continue
            for p in ring:
                poly += p2(p[0], p[1])
            poly += p2(ring[0][0], ring[0][1])
        out.append(AllplanBasisElements.FillingElement(cp, fp, poly))
    return out


# ---------------------------------------------------------------------------
# reading selected Allplan elements
# ---------------------------------------------------------------------------
@dataclass
class Collected:
    points: List[Point3] = field(default_factory=list)
    lines3d: List[List[Point3]] = field(default_factory=list)              # open or closed 3D lines
    lines2d: List[List[Tuple[float, float]]] = field(default_factory=list)  # 2D lines (no z)
    meshes: List[Tuple[List[Point3], Optional[List[Tuple[int, int, int]]]]] = field(default_factory=list)
    unsupported: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    count: int = 0

    def all_lines_xy(self) -> List[List[Tuple[float, float]]]:
        return [[(p[0], p[1]) for p in l] for l in self.lines3d] + self.lines2d

    def summary(self) -> str:
        s = (f"{self.count} element(s): {len(self.points)} point(s), {len(self.lines3d)} 3D line(s), "
             f"{len(self.lines2d)} 2D line(s), {len(self.meshes)} mesh(es)")
        if self.unsupported:
            s += " | ignored: " + ", ".join(f"{k} x{v}" for k, v in self.unsupported.items())
        return s


_DIR_LOGGED = set()


def _log_api_once(obj, label: str) -> None:
    name = type(obj).__name__
    if name in _DIR_LOGGED:
        return
    _DIR_LOGGED.add(name)
    try:
        members = [m for m in dir(obj) if not m.startswith("_")]
        log.debug(f"API of {label} {name}: {members}")
    except Exception:  # noqa: BLE001
        pass


def _points_of(geo) -> Optional[List]:
    pts = getattr(geo, "Points", None)
    if pts is None:
        return None
    try:
        return list(pts)
    except TypeError:
        return None


def _try_polyhedron_faces(geo, nverts: int) -> Optional[List[Tuple[int, int, int]]]:
    """Best effort extraction of triangle vertex indices from a Polyhedron3D."""
    try:
        nf = geo.GetFacesCount()
        ne = geo.GetEdgesCount()
    except Exception:  # noqa: BLE001
        return None
    try:
        edges = []
        for i in range(ne):
            e = geo.GetEdge(i)
            if isinstance(e, tuple):
                e = e[-1]
            _log_api_once(e, "polyhedron edge")
            s = getattr(e, "Start", None)
            t = getattr(e, "End", None)
            if s is None or t is None:
                return None
            edges.append((int(s), int(t)))
        faces = []
        for i in range(nf):
            f = geo.GetFace(i)
            if isinstance(f, tuple):
                f = f[-1]
            _log_api_once(f, "polyhedron face")
            cnt = f.GetEdgeCount() if hasattr(f, "GetEdgeCount") else f.GetEdgesCount()
            loop = []
            for j in range(cnt):
                oe = f.GetEdge(j)
                if isinstance(oe, tuple):
                    oe = oe[-1]
                _log_api_once(oe, "oriented edge")
                idx = getattr(oe, "EdgeIndex", None)
                if idx is None:
                    idx = getattr(oe, "Index", None)
                pos = getattr(oe, "Positive", None)
                if pos is None:
                    pos = getattr(oe, "Orientation", True)
                if idx is None:
                    return None
                a, b = edges[int(idx)]
                loop.append(a if pos else b)
            for k in range(1, len(loop) - 1):
                faces.append((loop[0], loop[k], loop[k + 1]))
        if faces and all(0 <= i < nverts for f in faces for i in f):
            return faces
    except Exception as exc:  # noqa: BLE001
        log.debug(f"Polyhedron face extraction not available ({type(exc).__name__}: {exc}); "
                  "vertices will be re-triangulated.")
    return None


def collect(adapters: Iterable, read_faces: bool = True) -> Collected:
    """Extract terrain geometry from selected Allplan elements (BaseElementAdapter)."""
    col = Collected()
    for ele in adapters:
        col.count += 1
        try:
            geo = ele.GetGeometry()
        except Exception as exc:  # noqa: BLE001
            col.unsupported[f"<GetGeometry failed: {exc}>"] += 1
            continue
        geos = list(geo) if isinstance(geo, (list, tuple)) else [geo]
        for g in geos:
            _add_geometry(col, g, read_faces, ele)
    log.log("Selection: " + col.summary())
    return col


def _add_geometry(col: Collected, g, read_faces: bool, ele=None) -> None:
    if g is None:
        col.unsupported["<no geometry>"] += 1
        return
    name = type(g).__name__
    try:
        if name == "Point3D":
            col.points.append(from_mm(g))
        elif name == "Point2D":
            col.unsupported["Point2D (no elevation)"] += 1
        elif name in ("Line3D",):
            col.lines3d.append([from_mm(g.StartPoint), from_mm(g.EndPoint)])
        elif name in ("Line2D",):
            col.lines2d.append([(g.StartPoint.X / MM, g.StartPoint.Y / MM), (g.EndPoint.X / MM, g.EndPoint.Y / MM)])
        elif name in ("Polyline3D", "Polygon3D", "Spline3D", "BSpline3D"):
            pts = _points_of(g)
            if pts:
                line = [from_mm(p) for p in pts]
                if name == "Polygon3D" and line and line[0] != line[-1]:
                    line.append(line[0])
                col.lines3d.append(line)
                if name in ("Spline3D", "BSpline3D"):
                    log.debug(f"{name}: using its control/fit points as a polyline (approximation).")
        elif name in ("Polyline2D", "Polygon2D", "Spline2D", "BSpline2D"):
            pts = _points_of(g)
            if pts:
                line = [(p.X / MM, p.Y / MM) for p in pts]
                if name == "Polygon2D" and line and line[0] != line[-1]:
                    line.append(line[0])
                col.lines2d.append(line)
        elif name == "Polyhedron3D":
            verts = [from_mm(v) for v in g.GetVertices()]
            faces = _try_polyhedron_faces(g, len(verts)) if read_faces else None
            col.meshes.append((verts, faces))
            log.debug(f"Polyhedron3D: {len(verts)} vertices, faces {'read' if faces else 'not read (re-triangulate)'}")
        elif hasattr(g, "StartPoint") and hasattr(g, "EndPoint") and hasattr(g.StartPoint, "Z"):
            col.lines3d.append([from_mm(g.StartPoint), from_mm(g.EndPoint)])
            col.unsupported[f"{name} (approximated by its chord)"] += 1
        else:
            col.unsupported[name] += 1
            _log_api_once(g, "unsupported geometry")
    except Exception as exc:  # noqa: BLE001
        col.unsupported[f"{name} (read error: {exc})"] += 1
        log.log_exception(f"reading {name}")


def collected_to_tin(col: Collected, log_fn=None) -> TIN:
    """Merge selected meshes and points into one TIN."""
    meshes = [m for m in col.meshes if m[0]]
    if len(meshes) == 1 and meshes[0][1] and not col.points:
        verts, faces = meshes[0]
        return tin_from_mesh(verts, faces)
    pts: List[Point3] = list(col.points)
    for verts, _ in meshes:
        pts.extend(verts)
    if len(pts) < 3:
        raise TerrainError("No terrain found in the selection: select a terrain mesh (polyhedron) "
                           "or 3D points.")
    return build_tin(pts, breaklines=[l for l in col.lines3d if len(l) >= 2], log=log_fn)


def closed_rings(col: Collected, min_vertices: int = 3) -> List[List[Tuple[float, float, Optional[float]]]]:
    """Closed outlines from the selection (3D keeps z, 2D gets z=None)."""
    rings = []
    for l in col.lines3d:
        if len(l) >= min_vertices + 1 and abs(l[0][0] - l[-1][0]) < 1e-6 and abs(l[0][1] - l[-1][1]) < 1e-6:
            rings.append([(p[0], p[1], p[2]) for p in l[:-1]])
    for l in col.lines2d:
        if len(l) >= min_vertices + 1 and abs(l[0][0] - l[-1][0]) < 1e-6 and abs(l[0][1] - l[-1][1]) < 1e-6:
            rings.append([(p[0], p[1], None) for p in l[:-1]])
    return rings
