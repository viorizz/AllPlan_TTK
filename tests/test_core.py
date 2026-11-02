"""Unit tests for the Allplan-independent terrain core. Run: python -m pytest tests"""
import math
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "PythonPartsScripts"))

from terrain_toolkit.core import analysis, contours, drainage, geom, io_formats, profiles, simplify, volumes  # noqa: E402
from terrain_toolkit.core.delaunay import ConstrainedTriangulation  # noqa: E402
from terrain_toolkit.core.grading import PlatformSpec, grade_platform  # noqa: E402
from terrain_toolkit.core.tin import TIN, TerrainError, build_tin  # noqa: E402


def hill(x, y):
    return 100.0 + 8.0 * math.exp(-((x - 50) ** 2 + (y - 50) ** 2) / 600.0) + 0.05 * x


def random_points(n=1500, seed=0, size=100.0, f=hill, offset=(0.0, 0.0)):
    rnd = random.Random(seed)
    pts = [(rnd.random() * size, rnd.random() * size) for _ in range(n)]
    pts += [(0, 0), (size, 0), (0, size), (size, size)]
    return [(x + offset[0], y + offset[1], f(x, y)) for x, y in pts]


# --------------------------------------------------------------------------- triangulation
def _incircle_ok(xs, ys, tris, sample=200, seed=1):
    rnd = random.Random(seed)
    n = len(xs)
    for (a, b, c) in tris[:sample]:
        for p in rnd.sample(range(n), min(n, 100)):
            if p in (a, b, c):
                continue
            m = [[xs[i] - xs[p], ys[i] - ys[p], (xs[i] - xs[p]) ** 2 + (ys[i] - ys[p]) ** 2] for i in (a, b, c)]
            det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                   - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                   + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            if det > 1e-7:
                return False
    return True


def test_delaunay_random_is_valid():
    rnd = random.Random(3)
    xs = [rnd.random() * 50 for _ in range(1500)]
    ys = [rnd.random() * 50 for _ in range(1500)]
    ct = ConstrainedTriangulation(xs, ys)
    tris = ct.triangles()
    assert len(tris) == 2 * 1500 - 2 - len(ct.hull)
    assert all(geom.orient(xs[a], ys[a], xs[b], ys[b], xs[c], ys[c]) > 0 for a, b, c in tris)
    assert _incircle_ok(xs, ys, tris)


def test_grid_and_collinear_inputs():
    pts = [(i, j, 0.0) for i in range(30) for j in range(30)]
    tin = build_tin(pts)
    assert len(tin.triangles) == 2 * 29 * 29
    with pytest.raises(TerrainError):
        build_tin([(i, 2 * i, 0) for i in range(10)])
    with pytest.raises(TerrainError):
        build_tin([(0, 0, 0), (1, 1, 1)])


def test_large_coordinates_precision():
    # Lambert-93 like coordinates
    pts = random_points(800, offset=(651234.0, 6862345.0))
    tin = build_tin(pts)
    z = tin.z_at(651234.0 + 50, 6862345.0 + 50)
    assert z == pytest.approx(hill(50, 50), abs=0.3)


def test_breaklines_are_enforced_and_crossings_split():
    pts = [(x, y, 0.0) for x, y, _ in random_points(1200, seed=4)]
    ridge = [(10, 10, 5.0), (90, 90, 5.0)]
    cross = [(10, 90, 3.0), (90, 10, 3.0)]
    tin = build_tin(pts, breaklines=[ridge, cross])
    assert tin.info["failed_constraints"] == 0
    # on the ridge the surface must follow the breakline elevation (crossing vertex takes ridge z)
    assert tin.z_at(30, 30) == pytest.approx(5.0, abs=1e-6)
    assert tin.z_at(70, 30) == pytest.approx(4.0, abs=1e-6)  # halfway between crossing (5) and end (3)
    assert tin.z_at(50, 50) == pytest.approx(5.0, abs=1e-6)


def test_boundary_hole_and_trim():
    pts = random_points(2000, seed=5)
    bnd = [(5, 5), (95, 5), (95, 95), (5, 95)]
    hole = [(40, 40), (60, 40), (60, 60), (40, 60)]
    tin = build_tin(pts, boundary=bnd, holes=[hole])
    assert tin.area_2d() == pytest.approx(90 * 90 - 20 * 20, rel=1e-9)
    assert tin.z_at(50, 50) is None
    assert tin.z_at(20, 20) is not None
    assert len(tin.boundary_rings()) == 2
    lshape = [(x, y, 0.0) for x in range(0, 41, 2) for y in range(0, 41, 2) if not (x > 21 and y > 21)]
    t2 = build_tin(lshape, max_edge=3.0)
    assert t2.area_2d() == pytest.approx(40 * 40 - 20 * 20, rel=0.02)


# --------------------------------------------------------------------------- contours
def test_contours_on_plane_are_straight_and_oriented():
    pts = [(x, y, 0.1 * x) for x in range(0, 101, 5) for y in range(0, 101, 5)]
    tin = build_tin(pts)
    cs = contours.generate_contours(tin, interval=1.0, major_interval=5.0)
    levels = sorted({c.level for c in cs.contours})
    # level 0 lies exactly on the lowest boundary edge and is (correctly) not produced
    assert levels[0] == 1.0 and levels[-1] >= 9.0
    for c in cs.contours:
        assert all(abs(p[0] - c.level * 10) < 1e-6 for p in c.points)
        assert not c.closed
    # higher ground (larger x) is on the left of the line direction -> line runs towards -y
    mid = [c for c in cs.contours if c.level == 5.0][0]
    assert mid.points[0][1] > mid.points[-1][1]
    assert {c.level for c in cs.major} <= {5.0, 10.0} and cs.major


def test_contours_closed_around_hill_and_labels():
    tin = build_tin(random_points(3000, seed=7, f=lambda x, y: 10 * math.exp(-((x - 50) ** 2 + (y - 50) ** 2) / 500.0)))
    cs = contours.generate_contours(tin, interval=1.0, major_interval=5.0, smooth_iterations=1)
    closed = [c for c in cs.contours if c.closed and c.level == 5.0]
    assert closed, "level 5 around the summit must be closed"
    r = math.sqrt(-500.0 * math.log(0.5))
    area = abs(geom.polygon_area(closed[0].points))
    assert area == pytest.approx(math.pi * r * r, rel=0.05)
    labels = contours.place_labels(cs.contours, 20.0, contours.format_level(1))
    assert labels and all(-90.0 < lab.angle_deg <= 90.0 for lab in labels)


# --------------------------------------------------------------------------- analysis
def test_slope_and_aspect_classes():
    pts = [(x, y, 0.1 * x) for x in range(0, 51, 5) for y in range(0, 51, 5)]  # 10 % slope facing west
    tin = build_tin(pts)
    res = analysis.slope_analysis(tin, [0, 5, 15, 30])
    by_label = {c.label: c for c in res.classes}
    assert by_label["5.0 - 15.0 %"].area_2d == pytest.approx(2500.0)
    assert len(by_label["5.0 - 15.0 %"].regions) == 1
    asp = analysis.aspect_analysis(tin, 8)
    west = [c for c in asp.classes if c.label == "W"][0]
    assert west.area_2d == pytest.approx(2500.0)


def test_elevation_bands_exact_areas():
    pts = [(x, y, 0.1 * x) for x in range(0, 101, 10) for y in range(0, 101, 10)]
    tin = build_tin(pts)
    res = analysis.elevation_bands(tin, [2.5, 5.0, 7.5])
    areas = [c.area_2d for c in res.classes]
    assert areas == pytest.approx([2500.0] * 4)
    assert sum(len(c.regions) for c in res.classes) == 4
    for c in res.classes:
        outer, holes = c.regions[0]
        assert abs(geom.polygon_area(outer)) == pytest.approx(2500.0)


def test_dissolve_with_hole():
    # ring of 8 unit squares around a hole
    coords = {}
    polys = []
    for i in range(4):
        for j in range(4):
            coords[(i, j)] = (float(i), float(j))
    for i in range(3):
        for j in range(3):
            if (i, j) == (1, 1):
                continue
            polys.append([(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)])
    regions = analysis.dissolve(polys, coords)
    assert len(regions) == 1
    outer, holes = regions[0]
    assert geom.polygon_area(outer) == pytest.approx(9.0)
    assert len(holes) == 1 and geom.polygon_area(holes[0]) == pytest.approx(-1.0)


# --------------------------------------------------------------------------- volumes
def test_volume_plane_offsets():
    a = build_tin([(x, y, 0.0) for x in range(11) for y in range(11)])
    b = build_tin([(x + 0.37, y + 0.21, 1.0) for x in range(-1, 11) for y in range(-1, 11)])
    r = volumes.difference(a, b)
    assert r.fill == pytest.approx(100.0)
    assert r.cut == pytest.approx(0.0)


def test_volume_sign_change_exact():
    a = build_tin(random_points(300, seed=2, size=10.0, f=lambda x, y: 0.0))
    b = build_tin([(x, y, x - 5.0) for x in (0, 3.3, 10) for y in (0, 10)])
    r = volumes.difference(a, b)
    assert r.cut == pytest.approx(125.0)
    assert r.fill == pytest.approx(125.0)
    assert r.cut_area == pytest.approx(50.0)


def test_volume_reference_plane_with_boundary():
    a = build_tin([(x, y, 0.0) for x in range(11) for y in range(11)])
    r = volumes.difference(a, reference_z=-2.0, boundary=[(2, 2), (8, 2), (8, 8), (2, 8)])
    assert r.cut == pytest.approx(72.0)
    assert r.total_area == pytest.approx(36.0)


# --------------------------------------------------------------------------- profiles
def test_profile_sampling_and_drawing():
    tin = build_tin([(x, y, 0.1 * x) for x in range(0, 101, 10) for y in range(0, 101, 10)])
    parts = profiles.sample_profile(tin, [(0, 50), (100, 50)])
    assert len(parts) == 1
    st = [s[0] for s in parts[0]]
    assert st[0] == pytest.approx(0.0) and st[-1] == pytest.approx(100.0)
    assert profiles.z_at_station(parts, 35.0) == pytest.approx(3.5)
    dr = profiles.profile_drawing([("Ground", parts)], 100.0, profiles.ProfileStyle(station_interval=25))
    assert dr.lines and dr.texts
    # off-surface gap
    gap = profiles.sample_profile(tin, [(-20, 50), (50, 50)])
    assert gap[0][0][0] == pytest.approx(20.0)
    secs = profiles.cross_section_lines([(10, 10), (90, 10)], 20.0, 5.0, 5.0)
    assert len(secs) == 5
    assert secs[0][1][0][1] == pytest.approx(15.0)  # left of +x direction is +y


# --------------------------------------------------------------------------- drainage
def test_flow_path_reaches_valley_and_depression_volume():
    # bowl: z = r^2 / 100, outlet nowhere -> ponding up to the rim
    pts = [(x, y, ((x - 50) ** 2 + (y - 50) ** 2) / 100.0) for x in range(0, 101, 5) for y in range(0, 101, 5)]
    tin = build_tin(pts)
    path = drainage.flow_path(tin, 80.0, 50.0)
    assert path[-1][2] < 1.0
    assert math.hypot(path[-1][0] - 50, path[-1][1] - 50) < 6
    dep = drainage.depressions(tin)
    assert dep.max_depth == pytest.approx(25.0, abs=0.01)
    assert dep.sinks
    arrows = drainage.flow_arrows(tin, spacing=20.0)
    assert arrows and len(arrows[0]) == 5


# --------------------------------------------------------------------------- grading
def test_platform_balance():
    tin = build_tin([(x, y, 0.1 * x) for x in range(0, 101, 4) for y in range(0, 101, 4)])
    spec = PlatformSpec(outline=[(40, 40), (60, 40), (60, 60), (40, 60)], balance=True, cut_ratio=1.5, fill_ratio=2.0)
    r = grade_platform(tin, spec)
    assert r.volumes is not None
    assert r.volumes.cut == pytest.approx(r.volumes.fill, rel=0.03)
    assert 4.5 < r.elevation_offset < 5.5
    assert len(r.daylight) > 4
    assert r.cut_slope_triangles and r.fill_slope_triangles


# --------------------------------------------------------------------------- simplify
def test_simplify_keeps_tolerance():
    pts = random_points(2500, seed=9)
    kept, err = simplify.simplify_points(pts, 0.05)
    assert len(kept) < len(pts) * 0.8
    assert err <= 0.05 + 1e-9
    thin = simplify.thin_grid(pts, 10.0)
    assert len(thin) <= 121
    spiky = pts + [(50.3, 50.7, 500.0)]
    clean, removed = simplify.remove_spikes(spiky, 5.0)
    assert removed >= 1 and max(p[2] for p in clean) < 200


# --------------------------------------------------------------------------- io
def test_point_file_formats(tmp_path):
    p = tmp_path / "pts.txt"
    p.write_text("# survey\nPt;X;Y;Z;Code\n1;651000,50;6862000,25;101,5;TN\n2;651010,50;6862000,25;102,5;TN\n"
                 "3;651000,50;6862010,25;103,5;TN\n", encoding="utf-8")
    r = io_formats.read_point_file(str(p))
    assert r.layout.startswith("PXYZ")
    assert r.points[0] == pytest.approx((651000.5, 6862000.25, 101.5))
    assert r.names[1] == "2" and r.codes[0] == "TN"
    p2 = tmp_path / "pnezd.csv"
    p2.write_text("1,6862000.25,651000.50,101.5,TN\n2,6862000.25,651010.50,102.5,TN\n", encoding="utf-8")
    r2 = io_formats.read_point_file(str(p2), layout="PNEZD")
    assert r2.points[1] == pytest.approx((651010.5, 6862000.25, 102.5))


def test_landxml_roundtrip(tmp_path):
    tin = build_tin(random_points(300, seed=11), breaklines=[[(10, 10, 100), (90, 90, 101)]])
    path = tmp_path / "t.xml"
    io_formats.write_landxml(str(path), tin, "EG")
    t2, name = io_formats.landxml_to_tin(str(path))
    assert name == "EG"
    assert len(t2.triangles) == len(tin.triangles)
    assert t2.z_at(33.3, 44.4) == pytest.approx(tin.z_at(33.3, 44.4))
    surfaces, _ = io_formats.read_landxml(str(path))
    assert len(surfaces[0].breaklines) == 1


def test_ascii_grid_and_obj(tmp_path):
    tin = build_tin(random_points(400, seed=12))
    g = tmp_path / "g.asc"
    io_formats.write_ascii_grid(str(g), tin, 5.0)
    grid = io_formats.read_ascii_grid(str(g))
    t2 = grid.to_tin()
    assert t2.z_at(50, 50) == pytest.approx(tin.z_at(50, 50), abs=0.2)
    o = tmp_path / "m.obj"
    io_formats.write_obj(str(o), tin)
    t3 = io_formats.read_obj(str(o))
    assert len(t3.triangles) == len(tin.triangles)


# --------------------------------------------------------------------------- robustness
def _hull_area(xs, ys):
    pts = sorted(set(zip(xs, ys)))

    def half(points):
        h = []
        for p in points:
            while len(h) >= 2 and geom.orient(h[-2][0], h[-2][1], h[-1][0], h[-1][1], p[0], p[1]) <= 0:
                h.pop()
            h.append(p)
        return h
    lower = half(pts)
    upper = half(list(reversed(pts)))
    return geom.polygon_area(lower[:-1] + upper[:-1])


@pytest.mark.parametrize("seed", range(6))
def test_degenerate_inputs_give_valid_planar_mesh(seed):
    """Grid points, many collinear points on the outline and on interior lines, near duplicates."""
    rnd = random.Random(seed)
    xs, ys = [], []
    for i in range(0, 41, 2):
        for j in range(0, 41, 2):
            xs.append(float(i)); ys.append(float(j))
    for _ in range(300):  # points exactly on the outline and on the diagonals
        t = rnd.random() * 40
        for x, y in ((t, 0.0), (40.0, t), (t, 40.0), (0.0, t), (t, t), (t, 40.0 - t)):
            xs.append(x); ys.append(y)
    for _ in range(200):  # near duplicates
        k = rnd.randrange(len(xs))
        xs.append(xs[k] + rnd.uniform(-1e-9, 1e-9)); ys.append(ys[k] + rnd.uniform(-1e-9, 1e-9))
    ct = ConstrainedTriangulation(xs, ys)
    tris = ct.triangles()
    area = sum(0.5 * geom.orient(xs[a], ys[a], xs[b], ys[b], xs[c], ys[c]) for a, b, c in tris)
    assert all(geom.orient(xs[a], ys[a], xs[b], ys[b], xs[c], ys[c]) > 0 for a, b, c in tris)
    assert area == pytest.approx(_hull_area(xs, ys), rel=1e-9)
    # constraints along the degenerate diagonals must all succeed
    pts = list(zip(xs, ys))
    i0 = pts.index((0.0, 0.0)); i1 = pts.index((40.0, 40.0)); i2 = pts.index((0.0, 40.0)); i3 = pts.index((40.0, 0.0))
    assert ct.insert_constraint(i0, i1)
    assert ct.insert_constraint(i2, i3)
    area2 = sum(0.5 * geom.orient(xs[a], ys[a], xs[b], ys[b], xs[c], ys[c]) for a, b, c in ct.triangles())
    assert area2 == pytest.approx(area, rel=1e-9)


def test_platform_volume_matches_independent_grid_estimate():
    def f(x, y):
        return 100.0 + 6.0 * math.exp(-((x - 50) ** 2 + (y - 50) ** 2) / 500.0) + 0.04 * x
    tin = build_tin(random_points(600, seed=1, f=f))
    r = grade_platform(tin, PlatformSpec(outline=[(35, 35), (65, 35), (65, 60), (35, 60)], balance=True, cell=0.5))
    dl = [(p[0], p[1]) for p in r.daylight]
    assert r.volumes.total_area == pytest.approx(abs(geom.polygon_area(dl)), rel=1e-6)
    c, fl = volumes.grid_volume(tin, lambda x, y, z: r.design_tin.z_at(x, y), 0.25, boundary=dl)
    assert r.volumes.cut == pytest.approx(c, rel=0.01)
    assert r.volumes.fill == pytest.approx(fl, rel=0.01)
