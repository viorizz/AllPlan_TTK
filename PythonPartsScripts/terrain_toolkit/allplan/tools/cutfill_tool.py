"""Cut & fill: volumes between existing and design surfaces (or a reference elevation),
with a depth heat map, isopach (equal depth) lines, legend and CSV report."""
from __future__ import annotations

import datetime

from ...core import analysis, colors, contours, volumes
from ...core.tin import TerrainError, TIN
from .. import geo, log, output
from ..tool_base import TerrainTool, ToolOutput


class CutFillTool(TerrainTool):
    TITLE = "Terrain Cut & Fill"
    ROLES = (("existing", "existing terrain"), ("design", "design surface"), ("boundary", "boundary (optional)"))

    def _surface(self, role: str, source_param: str, file_param: str) -> TIN:
        return self.terrain(role, source_param, file_param)

    def execute(self) -> ToolOutput:
        existing = self._surface("existing", "TerrainSource", "TerrainFile")
        mode = self.iparam("CompareMode", 0)
        design = None
        ref = None
        if mode == 0:
            design = self._surface("design", "DesignSource", "DesignFile")
        else:
            ref = self.fparam("ReferenceElevation", 0.0)
        boundary = None
        rings = geo.closed_rings(self.collect("boundary"))
        if rings:
            boundary = [(p[0], p[1]) for p in max(rings, key=lambda r: abs(_area(r)))]
        elif self.selection("boundary"):
            raise TerrainError("The selected boundary is not a closed polyline/polygon.")
        with log.Timer("Volume computation"):
            res = volumes.difference(existing, design, ref, boundary, exact=True, log=log.log)

        factor = self.fparam("SwellFactor", 1.0) or 1.0
        out = ToolOutput(show_message=self.bparam("ShowResult", True))
        base = self.param("BaseProp")
        mode_out = self.iparam("OutputMode", 1)
        if self.bparam("HeatMap", True) and res.diff_tin is not None:
            text = str(self.param("DepthBreaks", "")).strip()
            breaks = analysis.parse_breaks(text) if text else [-2.0, -1.0, -0.5, -0.1, 0.1, 0.5, 1.0, 2.0]
            dtin = res.diff_tin
            # colour the map at design level when available so it does not hide inside the terrain
            z_src = res.design_z if self.bparam("MapOnDesign", True) else [p[2] for p in dtin.points]
            map_tin = TIN([(p[0], p[1], z) for p, z in zip(dtin.points, z_src)], dtin.triangles, compact=False)
            band_tris, regions, a2, a3 = analysis.slice_bands(map_tin, breaks, res.diff_values, mode_out in (1, 2))
            labels = analysis.class_labels(breaks, "m", True, 2)
            n_neg = sum(1 for (_, lo, hi) in labels if hi is not None and hi <= 0)
            n_mid = sum(1 for (_, lo, hi) in labels if lo is not None and hi is not None and lo < 0 < hi)
            n_pos = len(labels) - n_neg - n_mid
            cols = colors.diverging(n_neg, n_pos, n_mid)
            classes = []
            for i, (lab, lo, hi) in enumerate(labels):
                c = analysis.AnalysisClass(i, lab, lo, hi, cols[i], band_tris[i], regions[i], a2[i], a3[i])
                if c.triangles:
                    classes.append(c)
            amap = analysis.AnalysisResult("cutfill", "m", classes, sum(a2))
            out.elements.extend(output.class_map_elements(amap, mode_out, base, self.fparam("LiftMesh", 0.0),
                                                          max(1000, self.iparam("MaxFaces", 30000))))
            if self.bparam("Legend", True):
                xmin, ymin, xmax, ymax = dtin.bbox()
                scale = self.fparam("DrawingScale", 500.0)
                th = self.fparam("TextHeight", 2.5)
                gap = output.model_text_height(th, scale) * 4
                out.elements.extend(output.analysis_legend(amap, "Cut (-) / Fill (+) depth", xmax + gap, ymax,
                                                           th, scale, base))
        if self.bparam("Isopachs", False) and res.diff_tin is not None:
            step = self.fparam("IsopachInterval", 0.5)
            if step > 0:
                dmin = min(res.diff_values)
                dmax = max(res.diff_values)
                levels = contours.make_levels(dmin, dmax, step, 0.0)
                iso = contours.isolines(res.diff_tin, levels, values=res.diff_values)
                cp_iso = geo.props(self.param("IsopachProp"))
                cp_zero = geo.props(self.param("ZeroLineProp"))
                for lev, lines in iso.items():
                    for pts, _closed in lines:
                        out.elements.append(geo.model3d(geo.polyline3d(pts), cp_zero if abs(lev) < 1e-9 else cp_iso))

        cut, fill = res.cut, res.fill
        lines = [
            f"Date: {datetime.datetime.now():%Y-%m-%d %H:%M}",
            f"Comparison: {'design surface' if mode == 0 else f'reference elevation {ref:.3f} m'}",
            f"Area analysed  : {res.total_area:12.2f} m²",
            f"Cut  (excav.)  : {cut:12.2f} m³   on {res.cut_area:10.2f} m²   max depth {res.max_cut:.3f} m",
            f"Fill (embank.) : {fill:12.2f} m³   on {res.fill_area:10.2f} m²   max height {res.max_fill:.3f} m",
            f"Net (fill-cut) : {fill - cut:12.2f} m³",
        ]
        if abs(factor - 1.0) > 1e-9:
            lines.append(f"Cut x swell factor {factor:.3f} = {cut * factor:.2f} m³  ->  balance {fill - cut * factor:.2f} m³")
        out.report_lines = lines
        output.write_csv(str(self.param("ReportFile", "")), ["Quantity", "Value", "Unit"], [
            ("Area analysed", f"{res.total_area:.3f}", "m2"),
            ("Cut volume", f"{cut:.3f}", "m3"), ("Cut area", f"{res.cut_area:.3f}", "m2"),
            ("Fill volume", f"{fill:.3f}", "m3"), ("Fill area", f"{res.fill_area:.3f}", "m2"),
            ("Net (fill - cut)", f"{fill - cut:.3f}", "m3"),
            ("Max cut depth", f"{res.max_cut:.3f}", "m"), ("Max fill height", f"{res.max_fill:.3f}", "m"),
            ("Swell factor", f"{factor:.3f}", "-"),
        ])
        if self.bparam("ResultTexts", True):
            xmin, ymin, xmax, ymax = res.diff_tin.bbox() if res.diff_tin else (0, 0, 0, 0)
            th = self.fparam("TextHeight", 2.5)
            scale = self.fparam("DrawingScale", 500.0)
            step = output.model_text_height(th, scale) * 1.6
            cp = geo.props(base)
            y = ymin - step * 2
            for ln in lines[1:]:
                out.elements.append(geo.text(ln, xmin, y, th, 0.0, "left_bottom", cp))
                y -= step
        out.summary = "\n".join(lines[2:])
        return out


def _area(ring) -> float:
    a = 0.0
    n = len(ring)
    for i in range(n):
        a += ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1]
    return a / 2.0
