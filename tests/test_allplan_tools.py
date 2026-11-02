"""End-to-end smoke tests of every PythonPart with a mocked Allplan API.

They exercise the real entry scripts, the real .pyp defaults, the selection workflow,
the conversion to Allplan objects and the error reporting.
"""
import importlib
import math
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "PythonPartsScripts"))

import allplan_mock as am  # noqa: E402

am.install()
LIB = os.path.join(ROOT, "Library", "Terrain Toolkit")


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from terrain_toolkit.allplan import log, settings
    log._LOG_DIR = None
    settings._CACHE.clear()
    am.reset()
    yield


def hill_mm(x, y):
    return (100.0 + 6.0 * math.exp(-((x - 50) ** 2 + (y - 50) ** 2) / 500.0) + 0.04 * x) * 1000.0


def point_elements(n=600, seed=1):
    rnd = random.Random(seed)
    pts = [(rnd.random() * 100, rnd.random() * 100) for _ in range(n)] + [(0, 0), (100, 0), (0, 100), (100, 100)]
    return [am.MockElement(am.Point3D(x * 1000, y * 1000, hill_mm(x, y))) for x, y in pts]


def polyline_element(pts_m, closed=False, z=None):
    pts = list(pts_m) + ([pts_m[0]] if closed else [])
    if z is None:
        return am.MockElement(am.Polyline2D([am.Point2D(p[0] * 1000, p[1] * 1000) for p in pts]))
    return am.MockElement(am.Polyline3D([am.Point3D(p[0] * 1000, p[1] * 1000, z(p) * 1000) for p in pts]))


def start(script):
    build_ele = am.BuildElement(os.path.join(LIB, f"{script}.pyp"))
    mod = importlib.import_module(f"terrain_toolkit.{script}")
    assert mod.check_allplan_version(build_ele, "2026.0")
    tool = mod.create_interactor(am.CoordinateInput(), LIB, None, [build_ele], None, None, [])
    return tool, build_ele


def select(tool, role_index, elements):
    tool.modify_element_property(0, "SelectRole", role_index)
    am.PENDING_SELECTION.extend(elements)
    tool.process_mouse_msg(0, None, None)


def set_(tool, **kw):
    for k, v in kw.items():
        tool.modify_element_property(0, k, v)


def run(tool):
    n0 = len(am.CREATED)
    tool.on_control_event(1001)
    errors = [m for m in am.MESSAGES if "failed" in m or "error" in m.lower()]
    assert not errors, errors[0]
    assert len(am.CREATED) == n0 + 1, "CreateElements was not called"
    return am.CREATED[-1]


def kinds(elements):
    out = {}
    for e in elements:
        k = type(e).__name__ + ":" + type(getattr(e, "geo", e)).__name__
        out[k] = out.get(k, 0) + 1
    return out


def make_mesh_element():
    tool, _ = start("TerrainMesh")
    select(tool, 0, point_elements())
    created = run(tool)
    polys = [e for e in created if isinstance(getattr(e, "geo", None), am.Polyhedron3D)]
    assert polys
    return [am.MockElement(p.geo) for p in polys]


# --------------------------------------------------------------------------- tests
def test_mesh_from_selection_with_breakline_boundary_and_hole(tmp_path):
    tool, be = start("TerrainMesh")
    select(tool, 0, point_elements())
    select(tool, 1, [polyline_element([(10, 10), (90, 80)], z=lambda p: hill_mm(*p) / 1000 + 0.5)])
    select(tool, 2, [polyline_element([(2, 2), (98, 2), (98, 98), (2, 98)], closed=True)])
    select(tool, 3, [polyline_element([(40, 40), (55, 40), (55, 55), (40, 55)], closed=True)])
    assert "Terrain points / meshes: 604" in be.SelectionInfo.value
    set_(tool, CreateOutline=True, CreateBreaklines=True)
    created = run(tool)
    k = kinds(created)
    assert k["ModelElement3D:Polyhedron3D"] == 1
    assert k["ModelElement3D:Polyline3D"] >= 3  # 2 outline rings + breakline
    poly = [e.geo for e in created if isinstance(e.geo, am.Polyhedron3D)][0]
    assert poly.type == am._PolyType.names["tFaces"]
    assert os.path.exists(os.path.join(str(tmp_path), "Documents", "AllplanTerrainToolkit", "terrains", "Terrain.xml"))


def test_mesh_from_point_file_with_shift(tmp_path):
    f = tmp_path / "pts.csv"
    rnd = random.Random(2)
    rows = ["Pt;X;Y;Z"]
    for i in range(300):
        x, y = rnd.random() * 50, rnd.random() * 50
        rows.append(f"{i + 1};{651000 + x:.3f};{6862000 + y:.3f};{hill_mm(x, y) / 1000:.3f}".replace(".", ","))
    f.write_text("\n".join(rows), encoding="utf-8")
    tool, _ = start("TerrainMesh")
    set_(tool, TerrainSource=1, TerrainFile=str(f), ShiftX=651000.0, ShiftY=6862000.0, MaxFaces=1000)
    created = run(tool)
    polys = [e.geo for e in created if isinstance(e.geo, am.Polyhedron3D)]
    assert len(polys) >= 1
    xs = [v.X for p in polys for v in p.vertices]
    assert 0 <= min(xs) and max(xs) <= 50000.0 + 1e-6   # shifted to the Allplan origin, in mm


def test_contours_from_existing_mesh_element():
    mesh = make_mesh_element()
    tool, _ = start("TerrainContours")
    select(tool, 0, mesh)
    set_(tool, Interval=0.5, Smooth=1, LabelSpacing=20.0)
    created = run(tool)
    k = kinds(created)
    assert k.get("ModelElement3D:Polyline3D", 0) > 5
    assert k.get("TextElement:TextElement", 0) > 0


def test_analysis_all_kinds():
    mesh = make_mesh_element()
    for kind in (0, 1, 2, 3):
        tool, _ = start("TerrainAnalysis")
        select(tool, 0, mesh)
        set_(tool, AnalysisType=kind, OutputMode=2)
        created = run(tool)
        k = kinds(created)
        assert k.get("ModelElement3D:Polyhedron3D", 0) >= 2, (kind, k)
        assert k.get("FillingElement:FillingElement", 0) >= 2, (kind, k)


def test_cutfill_reference_elevation_and_design(tmp_path):
    mesh = make_mesh_element()
    tool, _ = start("TerrainCutFill")
    select(tool, 0, mesh)
    set_(tool, CompareMode=1, ReferenceElevation=102.0, Isopachs=True, ReportFile=str(tmp_path / "vol.csv"))
    created = run(tool)
    assert am.MESSAGES and "Cut" in am.MESSAGES[-1]
    assert (tmp_path / "vol.csv").exists()
    assert kinds(created).get("FillingElement:FillingElement", 0) > 0
    # design surface = flat plane polyhedron created from points
    design_pts = [am.MockElement(am.Point3D(x * 1000, y * 1000, 101500.0)) for x in range(0, 101, 20) for y in range(0, 101, 20)]
    tool, _ = start("TerrainCutFill")
    select(tool, 0, mesh)
    select(tool, 1, design_pts)
    select(tool, 2, [polyline_element([(20, 20), (80, 20), (80, 80), (20, 80)], closed=True)])
    run(tool)
    assert "Fill" in am.MESSAGES[-1]


def test_profile_and_sections():
    mesh = make_mesh_element()
    tool, _ = start("TerrainProfile")
    select(tool, 0, mesh)
    select(tool, 2, [polyline_element([(5, 50), (50, 60), (95, 40)])])
    set_(tool, ProfileMode=2, StationLabels=True)
    created = run(tool)
    k = kinds(created)
    assert k.get("ModelElement2D:Polyline2D", 0) > 10
    assert k.get("TextElement:TextElement", 0) > 10
    assert k.get("ModelElement3D:Polyline3D", 0) >= 1


def test_drainage():
    mesh = make_mesh_element()
    tool, _ = start("TerrainDrainage")
    select(tool, 0, mesh)
    select(tool, 1, [am.MockElement(am.Point3D(60000, 55000, 0))])
    set_(tool, FlowPaths=True)
    created = run(tool)
    assert kinds(created).get("ModelElement3D:Polyline3D", 0) > 10


def test_drainage_ponding_in_bowl():
    pts = [am.MockElement(am.Point3D(x * 1000, y * 1000, ((x - 25) ** 2 + (y - 25) ** 2) * 10.0))
           for x in range(0, 51, 5) for y in range(0, 51, 5)]
    tool, _ = start("TerrainDrainage")
    select(tool, 0, pts)
    created = run(tool)
    assert kinds(created).get("FillingElement:FillingElement", 0) > 0


def test_platform_balance():
    mesh = make_mesh_element()
    tool, _ = start("TerrainPlatform")
    select(tool, 0, mesh)
    select(tool, 1, [polyline_element([(35, 35), (65, 35), (65, 60), (35, 60)], closed=True)])
    set_(tool, ElevationMode=1, GridCell=0.5)
    created = run(tool)
    assert "Cut" in am.MESSAGES[-1] and "Fill" in am.MESSAGES[-1]
    assert kinds(created).get("ModelElement3D:Polyhedron3D", 0) >= 2


def test_exchange_all_formats(tmp_path):
    mesh = make_mesh_element()
    for fmt, ext in ((0, "xml"), (1, "obj"), (2, "xyz"), (3, "csv"), (4, "asc")):
        tool, _ = start("TerrainExchange")
        select(tool, 0, mesh)
        out = tmp_path / f"t.{ext}"
        set_(tool, ExportFormat=fmt, ExportFile=str(out), GridCell=2.0, ShiftX=1000.0)
        am.MESSAGES.clear()
        tool.on_control_event(1001)
        assert out.exists() and out.stat().st_size > 100, fmt
    first = (tmp_path / "t.xyz").read_text().split()[0]
    assert float(first) >= 1000.0  # shift added back


def test_diagnostics_selftest_and_inspect():
    tool, _ = start("TerrainDiagnostics")
    created = run(tool)
    assert kinds(created).get("ModelElement3D:Polyhedron3D", 0) == 1
    select(tool, 0, point_elements(5))
    tool.on_control_event(2001)
    assert "inspected" in am.MESSAGES[-1]


def test_errors_are_reported_not_raised():
    tool, _ = start("TerrainContours")
    tool.on_control_event(1001)   # nothing selected
    assert am.MESSAGES, "an error message box must be shown"
    assert "No terrain found" in am.MESSAGES[-1]
    assert "terrain_toolkit.log" in am.MESSAGES[-1]
    from terrain_toolkit.allplan import log
    assert "No terrain found" in open(log.log_file(), encoding="utf-8").read()


def test_escape_closes():
    tool, _ = start("TerrainMesh")
    assert tool.on_cancel_function() is True
