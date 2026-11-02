"""Surface analysis maps: slope (% or degrees), aspect/exposure and elevation bands."""
from __future__ import annotations

from ...core import analysis, colors
from ...core.tin import TerrainError
from .. import log, output
from ..tool_base import TerrainTool, ToolOutput

KINDS = {0: "Slope (%)", 1: "Slope (degrees)", 2: "Aspect / exposure", 3: "Elevation bands"}


class AnalysisTool(TerrainTool):
    TITLE = "Terrain Analysis"
    ROLES = (("terrain", "terrain mesh / points"),)

    def execute(self) -> ToolOutput:
        tin = self.terrain()
        kind = self.iparam("AnalysisType", 0)
        mode = self.iparam("OutputMode", 2)
        dissolve = mode in (1, 2)
        ramp_name = str(self.param("ColorRamp", "auto"))
        reverse = self.bparam("ReverseColors", False)
        with log.Timer("Analysis"):
            if kind in (0, 1):
                text = str(self.param("SlopeBreaksPct" if kind == 0 else "SlopeBreaksDeg", ""))
                breaks = analysis.parse_breaks(text) if text.strip() else ([0, 2, 5, 10, 15, 25, 50] if kind == 0
                                                                             else [0, 5, 10, 15, 20, 30, 45])
                res = analysis.slope_analysis(tin, breaks, "%" if kind == 0 else "deg", None, dissolve)
                default_ramp = "slope"
            elif kind == 2:
                sectors = {0: 4, 1: 8, 2: 16}.get(self.iparam("AspectSectors", 1), 8)
                res = analysis.aspect_analysis(tin, sectors, self.fparam("FlatSlope", 1.0), None, dissolve)
                default_ramp = "aspect"
            elif kind == 3:
                text = str(self.param("ElevationBreaks", "")).strip()
                if text:
                    breaks = analysis.parse_breaks(text)
                else:
                    zmin, zmax = tin.z_range()
                    breaks = analysis.auto_breaks(zmin, zmax, max(2, self.iparam("ClassCount", 8)))
                res = analysis.elevation_bands(tin, breaks, None, dissolve, "m", self.iparam("Decimals", 2))
                default_ramp = "terrain"
            else:
                raise TerrainError(f"Unknown analysis type {kind}")
        name = default_ramp if ramp_name in ("", "auto") else ramp_name
        if kind == 2 and name == "aspect":
            cols = colors.RAMPS["aspect"][:1] + colors.sample_ramp(colors.RAMPS["aspect"][1:] + [colors.RAMPS["aspect"][1]],
                                                                   len(res.classes))[:len(res.classes) - 1]
        else:
            cols = colors.ramp(name, len(res.classes), reverse)
        for c, rgb in zip(res.classes, cols):
            c.color = rgb

        out = ToolOutput()
        base = self.param("BaseProp")
        lift = self.fparam("LiftMesh", 0.0)
        out.elements.extend(output.class_map_elements(res, mode, base, lift, max(1000, self.iparam("MaxFaces", 30000))))
        if self.bparam("Legend", True):
            xmin, ymin, xmax, ymax = tin.bbox()
            scale = self.fparam("DrawingScale", 500.0)
            th = self.fparam("TextHeight", 2.5)
            gap = output.model_text_height(th, scale) * 4
            out.elements.extend(output.analysis_legend(res, KINDS.get(kind, "Analysis"), xmax + gap, ymax, th, scale, base))
        lines = [f"{KINDS.get(kind)} - classes:"]
        rows = []
        for label, a2, pct in res.table():
            lines.append(f"  {label:<24} {a2:12.1f} m²  {pct:6.2f} %")
            rows.append((label, f"{a2:.2f}", f"{pct:.2f}"))
        out.report_lines = lines
        output.write_csv(str(self.param("ReportFile", "")), ["Class", "Area 2D (m2)", "Share (%)"], rows)
        out.summary = f"{KINDS.get(kind)}: {len(res.classes)} class(es), total plan area {res.total_area_2d:.1f} m²"
        return out
