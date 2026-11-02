"""Diagnostics: environment report, Allplan API check, self-test geometry and element inspection.

The output of this tool (log file) is what the developer needs to fix API differences.
"""
from __future__ import annotations

import math
import traceback

from ...core import contours as ct
from ...core.tin import build_tin
from .. import geo, log
from ..tool_base import TerrainTool, ToolOutput

EVT_INSPECT = 2001

API_CHECKS = {
    "NemAll_Python_Geometry": ["Point3D", "Point2D", "Polyline3D", "Polyline2D", "Polygon2D", "Line3D",
                               "Polyhedron3D", "Polyhedron3DBuilder", "GeometryEdge", "OrientedEdge",
                               "PolyhedronType", "Angle", "Matrix3D"],
    "NemAll_Python_BaseElements": ["CommonProperties", "CreateElements", "GetIdByColor", "GetElement"],
    "NemAll_Python_BasisElements": ["ModelElement3D", "ModelElement2D", "TextElement", "TextProperties",
                                    "TextAlignment", "FillingElement", "FillingProperties", "ARGB"],
    "NemAll_Python_IFW_Input": ["InputFunctionStarter", "PostElementSelection", "ElementSelectFilterSetting",
                                "HighlightService", "InputStringConvert"],
    "NemAll_Python_IFW_ElementAdapter": ["BaseElementAdapterList"],
    "NemAll_Python_Utility": ["ShowMessageBox", "MB_OK"],
}


class DiagnosticsTool(TerrainTool):
    TITLE = "Terrain Diagnostics"
    ROLES = (("inspect", "elements to inspect"),)

    def execute(self) -> ToolOutput:
        rep = [log.environment_report(), "", "API check:"]
        missing = 0
        for mod_name, names in API_CHECKS.items():
            try:
                mod = __import__(mod_name)
            except Exception as exc:  # noqa: BLE001
                rep.append(f"  {mod_name}: IMPORT FAILED ({exc})")
                missing += len(names)
                continue
            miss = [n for n in names if not hasattr(mod, n)]
            missing += len(miss)
            rep.append(f"  {mod_name}: {'OK' if not miss else 'MISSING ' + ', '.join(miss)}")
        try:
            import NemAll_Python_Geometry as AllplanGeo  # type: ignore
            rep.append(f"  PolyhedronType names: {list(AllplanGeo.PolyhedronType.names.keys())}")
            import NemAll_Python_BasisElements as AllplanBasisElements  # type: ignore
            rep.append(f"  TextAlignment names: {list(AllplanBasisElements.TextAlignment.names.keys())}")
            for cls in (AllplanGeo.Polyhedron3D, AllplanBasisElements.TextProperties,
                        AllplanBasisElements.FillingProperties):
                rep.append(f"  dir({cls.__name__}): {[m for m in dir(cls) if not m.startswith('_')]}")
        except Exception as exc:  # noqa: BLE001
            rep.append(f"  (introspection failed: {exc})")
        for line in rep:
            log.log(line)

        out = ToolOutput(show_message=True)
        if self.bparam("CreateTestGeometry", True):
            ox = self.fparam("TestX", 0.0)
            oy = self.fparam("TestY", 0.0)
            oz = self.fparam("TestZ", 0.0)
            steps = []
            pts = [(ox + x, oy + y, oz + 3.0 * math.exp(-((x - 10) ** 2 + (y - 10) ** 2) / 40.0))
                   for x in range(0, 21, 2) for y in range(0, 21, 2)]
            tin = build_tin(pts)
            steps.append(f"test TIN: {len(tin.triangles)} triangles")
            try:
                for poly in geo.tin_to_polyhedra(tin):
                    out.elements.append(geo.model3d(poly, geo.props(None, rgb=(120, 180, 90))))
                steps.append("polyhedron: OK")
            except Exception:  # noqa: BLE001
                steps.append("polyhedron: FAILED\n" + traceback.format_exc())
            try:
                cs = ct.generate_contours(tin, 0.5, 2.5)
                for c in cs.contours:
                    out.elements.append(geo.model3d(geo.polyline3d(c.points), geo.props(None, rgb=(150, 75, 0))))
                steps.append(f"contours: OK ({len(cs.contours)})")
            except Exception:  # noqa: BLE001
                steps.append("contours: FAILED\n" + traceback.format_exc())
            try:
                out.elements.append(geo.text("Terrain Toolkit test", ox, oy - 2.0, 3.0, 0.0, "left_top", geo.props(None)))
                steps.append("text: OK")
            except Exception:  # noqa: BLE001
                steps.append("text: FAILED\n" + traceback.format_exc())
            try:
                ring = [(ox + 22, oy), (ox + 30, oy), (ox + 30, oy + 8), (ox + 22, oy + 8)]
                out.elements.extend(geo.filling([(ring, [])], (220, 60, 60), geo.props(None)))
                steps.append("filling: OK")
            except Exception:  # noqa: BLE001
                steps.append("filling: FAILED\n" + traceback.format_exc())
            for s in steps:
                log.log(s)
            out.report_lines = steps
        out.summary = (f"API check: {'all OK' if missing == 0 else f'{missing} missing name(s)'}\n"
                       f"Test geometry: {len(out.elements)} element(s)\n"
                       f"Full report in:\n{log.log_file()}")
        return out

    def on_custom_event(self, event_id: int) -> None:
        if event_id != EVT_INSPECT:
            return

        @log.guarded("Inspect selection")
        def _inspect():
            eles = self.selection("inspect")
            if not eles:
                log.show_message("Select one or more elements first (they are highlighted), then press 'Inspect'.")
                return
            log.section("Inspect selection")
            for i, e in enumerate(eles):
                lines = [f"--- element {i + 1}"]
                for fn in ("GetDisplayName", "GetModelElementUUID", "Is3DElement", "IsGeneralElement"):
                    try:
                        lines.append(f"  {fn}: {getattr(e, fn)()}")
                    except Exception as exc:  # noqa: BLE001
                        lines.append(f"  {fn}: <{exc}>")
                try:
                    t = e.GetElementAdapterType()
                    lines.append(f"  adapter type: {t.GetTypeName()} / {t.GetDisplayName()}")
                except Exception as exc:  # noqa: BLE001
                    lines.append(f"  adapter type: <{exc}>")
                try:
                    g = e.GetGeometry()
                    lines.append(f"  geometry type: {type(g).__name__}")
                    lines.append(f"  geometry members: {[m for m in dir(g) if not m.startswith('_')]}")
                    lines.append(f"  geometry repr: {str(g)[:500]}")
                except Exception as exc:  # noqa: BLE001
                    lines.append(f"  geometry: <{exc}>")
                for ln in lines:
                    log.log(ln)
            col = geo.collect(eles)
            log.log("Terrain Toolkit would read: " + col.summary())
            log.show_message(f"{len(eles)} element(s) inspected.\n{col.summary()}\n\nDetails in:\n{log.log_file()}")
        _inspect()
