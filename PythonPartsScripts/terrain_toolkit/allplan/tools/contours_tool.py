"""Contours: major/minor isolines with smoothing, simplification and labels."""
from __future__ import annotations

from ...core import contours as ct
from ...core.tin import TerrainError
from .. import geo, log
from ..tool_base import TerrainTool, ToolOutput


class ContoursTool(TerrainTool):
    TITLE = "Terrain Contours"
    ROLES = (("terrain", "terrain mesh / points"),)

    def execute(self) -> ToolOutput:
        tin = self.terrain()
        interval = self.fparam("Interval", 0.5)
        if interval <= 0:
            raise TerrainError("The contour interval must be greater than 0.")
        every = max(0, self.iparam("MajorEvery", 5))
        major_interval = interval * every if every > 0 else 0.0
        base = self.fparam("BaseElevation", 0.0)
        zlo = self.fparam("MinElevation", 0.0) if self.bparam("LimitRange", False) else None
        zhi = self.fparam("MaxElevation", 0.0) if self.bparam("LimitRange", False) else None
        with log.Timer("Contour generation"):
            cs = ct.generate_contours(tin, interval, major_interval, base,
                                      smooth_iterations=self.iparam("Smooth", 0),
                                      simplify_tol=self.fparam("SimplifyTol", 0.0),
                                      min_length=self.fparam("MinLength", 0.0), zmin=zlo, zmax=zhi)
        as_3d = self.iparam("Dimension", 0) == 0
        out = ToolOutput()
        cp_major = geo.props(self.param("MajorProp"))
        cp_minor = geo.props(self.param("MinorProp"))
        for c in cs.contours:
            cp = cp_major if c.major else cp_minor
            if as_3d:
                out.elements.append(geo.model3d(geo.polyline3d(c.points), cp))
            else:
                out.elements.append(geo.model2d(geo.polyline2d([(p[0], p[1]) for p in c.points]), cp))
        n_labels = 0
        if self.bparam("LabelMajor", True) or self.bparam("LabelMinor", False):
            cp_lab = geo.props(self.param("LabelProp"))
            fmt = ct.format_level(self.iparam("Decimals", 1))
            spacing = self.fparam("LabelSpacing", 50.0)
            th = self.fparam("TextHeight", 2.0)
            sel = [c for c in cs.contours if (c.major and self.bparam("LabelMajor", True))
                   or (not c.major and self.bparam("LabelMinor", False))]
            labels = ct.place_labels(sel, spacing, fmt, min_length=spacing * 0.3, only_major=False)
            for lab in labels:
                out.elements.append(geo.text(lab.text, lab.x, lab.y, th, lab.angle_deg, "center_center", cp_lab))
            n_labels = len(labels)
        levels = sorted({c.level for c in cs.contours})
        out.summary = (f"{len(cs.contours)} contour line(s) ({len(cs.major)} major) on {len(levels)} level(s)"
                       + (f" from {levels[0]:.2f} to {levels[-1]:.2f} m" if levels else "")
                       + f"\n{n_labels} label(s)")
        if not cs.contours:
            out.summary += "\nNo contour found: check the interval / elevation range."
        return out
