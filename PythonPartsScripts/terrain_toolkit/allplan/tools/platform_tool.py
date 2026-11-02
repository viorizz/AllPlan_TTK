"""Platform grading: pad at a fixed / balanced / outline elevation with daylight cut & fill slopes."""
from __future__ import annotations

import os
import re

from ...core import io_formats
from ...core.grading import PlatformSpec, grade_platform
from ...core.tin import TerrainError
from .. import geo, log, settings
from ..tool_base import TerrainTool, ToolOutput


class PlatformTool(TerrainTool):
    TITLE = "Terrain Platform"
    ROLES = (("terrain", "existing terrain"), ("outline", "platform outline (closed polyline)"))

    def execute(self) -> ToolOutput:
        tin = self.terrain()
        rings = geo.closed_rings(self.collect("outline"))
        if not rings:
            raise TerrainError("Select the platform outline: a closed 2D/3D polyline or polygon (second radio button).")
        ring = max(rings, key=lambda r: abs(_area(r)))
        mode = self.iparam("ElevationMode", 0)
        spec = PlatformSpec(
            outline=[(p[0], p[1], p[2]) for p in ring],
            elevation=self.fparam("Elevation", 0.0) if mode == 0 else None,
            use_outline_z=(mode == 2),
            cut_ratio=self.fparam("CutRatio", 1.5),
            fill_ratio=self.fparam("FillRatio", 2.0),
            max_reach=self.fparam("MaxReach", 50.0),
            cell=self.fparam("GridCell", 0.0),
            balance=(mode == 1),
            balance_factor=self.fparam("SwellFactor", 1.0) or 1.0,
        )
        if mode == 2 and any(p[2] is None for p in ring):
            raise TerrainError("'Elevation from outline' needs a 3D outline; the selected outline is 2D.")
        with log.Timer("Platform grading"):
            res = grade_platform(tin, spec, log=log.log)
        for w in res.warnings:
            log.warn(w)
        out = ToolOutput(show_message=self.bparam("ShowResult", True))
        maxf = max(1000, self.iparam("MaxFaces", 30000))
        if self.bparam("PadMesh", True) and res.pad_tin is not None:
            cp = geo.props(self.param("PadProp"))
            out.elements.extend(geo.model3d(p, cp) for p in geo.tin_to_polyhedra(res.pad_tin, maxf))
        if self.bparam("SlopeMesh", True):
            cpc = geo.props(self.param("CutSlopeProp"))
            cpf = geo.props(self.param("FillSlopeProp"))
            out.elements.extend(geo.model3d(p, cpc) for p in geo.triangles_to_polyhedra(res.cut_slope_triangles, maxf))
            out.elements.extend(geo.model3d(p, cpf) for p in geo.triangles_to_polyhedra(res.fill_slope_triangles, maxf))
        if self.bparam("DaylightLine", True) and res.daylight:
            cp = geo.props(self.param("DaylightProp"))
            out.elements.append(geo.model3d(geo.polyline3d(res.daylight + [res.daylight[0]]), cp))
        if self.bparam("Outline3D", True):
            cp = geo.props(self.param("PadProp"))
            out.elements.append(geo.model3d(geo.polyline3d(res.outline3d + [res.outline3d[0]]), cp))
        if self.bparam("DesignMesh", False) and res.design_tin is not None:
            cp = geo.props(self.param("DesignProp"))
            out.elements.extend(geo.model3d(p, cp) for p in geo.tin_to_polyhedra(res.design_tin, maxf))
        saved = ""
        if self.bparam("SaveDesign", True) and res.design_tin is not None:
            name = re.sub(r"[^A-Za-z0-9_\-]+", "_", str(self.param("DesignName", "Platform_design")) or "Platform_design")
            path = os.path.join(settings.terrain_library_dir(), f"{name}.xml")
            sx, sy, sz = float(settings.get("shift_x", 0.0)), float(settings.get("shift_y", 0.0)), float(settings.get("shift_z", 0.0))
            io_formats.write_landxml(path, res.design_tin.transformed(1.0, sx, sy, sz), name)
            saved = path
        lines = [f"Pad: {res.pad_elevation_info}"]
        if res.volumes is not None:
            v = res.volumes
            lines += [f"Cut  : {v.cut:10.2f} m³ ({v.cut_area:.1f} m²)",
                      f"Fill : {v.fill:10.2f} m³ ({v.fill_area:.1f} m²)",
                      f"Net (fill-cut): {v.fill - v.cut:.2f} m³",
                      f"Footprint incl. slopes: {v.total_area:.1f} m²"]
        if res.warnings:
            lines += ["Warnings:"] + [f"  - {w}" for w in res.warnings]
        if saved:
            lines.append(f"Design surface saved: {saved}")
        if self.bparam("ResultTexts", True):
            cp = geo.props(self.param("PadProp"))
            cx = sum(p[0] for p in res.outline3d) / len(res.outline3d)
            cy = sum(p[1] for p in res.outline3d) / len(res.outline3d)
            out.elements.append(geo.text(f"{res.outline3d[0][2]:.2f}" if mode != 2 else "plane",
                                         cx, cy, self.fparam("TextHeight", 2.5), 0.0, "center_center", cp))
        out.summary = "\n".join(lines)
        return out


def _area(ring) -> float:
    a = 0.0
    n = len(ring)
    for i in range(n):
        a += ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1]
    return a / 2.0
