"""Surface water: flow direction arrows, flow paths, sinks and ponding depressions."""
from __future__ import annotations

from ...core import analysis, colors, drainage
from ...core.tin import TIN
from .. import geo, log, output
from ..tool_base import TerrainTool, ToolOutput


class DrainageTool(TerrainTool):
    TITLE = "Terrain Drainage"
    ROLES = (("terrain", "terrain mesh / points"), ("starts", "flow path start points / lines (optional)"))

    def execute(self) -> ToolOutput:
        tin = self.terrain()
        out = ToolOutput()
        lines = []
        me = drainage.mean_edge_length(tin)
        if self.bparam("Arrows", True):
            cp = geo.props(self.param("ArrowProp"))
            with log.Timer("Flow arrows"):
                arrows = drainage.flow_arrows(tin, spacing=self.fparam("ArrowSpacing", 0.0),
                                              length=self.fparam("ArrowLength", 0.0),
                                              min_slope_pct=self.fparam("MinSlope", 0.5),
                                              scale_by_slope=self.bparam("ScaleArrows", False))
            if len(arrows) > 20000:
                log.warn(f"{len(arrows)} arrows - consider a larger arrow spacing.")
            for a in arrows:
                out.elements.append(geo.model3d(geo.polyline3d(a), cp))
            lines.append(f"{len(arrows)} flow arrow(s)")
        if self.bparam("FlowPaths", False):
            cp = geo.props(self.param("FlowPathProp"))
            col = self.collect("starts")
            starts = [(p[0], p[1]) for p in col.points]
            for l in col.lines3d:
                starts.extend((p[0], p[1]) for p in l)
            for l in col.lines2d:
                starts.extend(l)
            paths = []
            with log.Timer("Flow paths"):
                if starts:
                    for (x, y) in starts:
                        p = drainage.flow_path(tin, x, y)
                        if len(p) >= 2:
                            paths.append(p)
                else:
                    spacing = self.fparam("SeedSpacing", 0.0) or me * 10
                    paths = drainage.flow_paths_grid(tin, spacing, min_length=self.fparam("MinPathLength", 0.0))
            for p in paths:
                out.elements.append(geo.model3d(geo.polyline3d(p), cp))
            lines.append(f"{len(paths)} flow path(s)")
        if self.bparam("Sinks", True) or self.bparam("Ponding", True):
            with log.Timer("Depression analysis"):
                dep = drainage.depressions(tin, self.fparam("MinDepth", 0.02))
            if self.bparam("Sinks", True):
                cp = geo.props(self.param("SinkProp"))
                size = self.fparam("SinkSize", 0.0) or me
                th = self.fparam("TextHeight", 2.0)
                for v in dep.sinks:
                    p = tin.points[v]
                    out.elements.extend(geo.cross3d(p, size, cp))
                    if self.bparam("SinkLabels", True):
                        out.elements.append(geo.text(f"{p[2]:.2f}", p[0] + size * 0.6, p[1], th, 0.0, "left_center", cp))
                lines.append(f"{len(dep.sinks)} local low point(s) (sinks)")
            if self.bparam("Ponding", True):
                min_d = self.fparam("MinDepth", 0.02)
                text = str(self.param("PondingBreaks", "")).strip()
                breaks = analysis.parse_breaks(text) if text else [min_d, 0.1, 0.25, 0.5, 1.0]
                breaks = sorted(set([b for b in breaks if b > 0]))
                if dep.max_depth > min_d and breaks:
                    water = TIN([(p[0], p[1], f) for p, f in zip(tin.points, dep.filled_z)], tin.triangles, compact=False)
                    band_tris, regions, a2, a3 = analysis.slice_bands(water, breaks, dep.depth,
                                                                      self.iparam("OutputMode", 2) in (1, 2))
                    labels = analysis.class_labels(breaks, "m", True, 2)
                    cols = [(0, 0, 0)] + colors.ramp("water", len(labels) - 1)
                    classes = []
                    for i, (lab, lo, hi) in enumerate(labels):
                        if i == 0:
                            continue  # below the minimum depth: dry
                        c = analysis.AnalysisClass(i, lab, lo, hi, cols[i], band_tris[i], regions[i], a2[i], a3[i])
                        if c.triangles:
                            classes.append(c)
                    res = analysis.AnalysisResult("ponding", "m", classes, sum(a2[1:]))
                    base = self.param("BaseProp")
                    out.elements.extend(output.class_map_elements(res, self.iparam("OutputMode", 2), base, 0.0,
                                                                  max(1000, self.iparam("MaxFaces", 30000))))
                    if self.bparam("Legend", True) and classes:
                        xmin, ymin, xmax, ymax = tin.bbox()
                        scale = self.fparam("DrawingScale", 500.0)
                        th = self.fparam("TextHeight", 2.0)
                        gap = output.model_text_height(th, scale) * 4
                        out.elements.extend(output.analysis_legend(res, "Ponding depth", xmax + gap, ymax, th, scale, base))
                    lines.append(f"Ponding: {dep.ponding_area:.1f} m², volume {dep.ponding_volume:.2f} m³, "
                                 f"max depth {dep.max_depth:.2f} m")
                else:
                    lines.append("No ponding depression deeper than the minimum depth.")
        out.summary = "\n".join(lines) if lines else "Nothing selected in the options."
        return out
