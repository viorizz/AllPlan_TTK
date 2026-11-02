"""Longitudinal profile and cross sections along a selected alignment (polyline)."""
from __future__ import annotations

from typing import List, Tuple

from ...core import geom, profiles
from ...core.tin import TerrainError
from .. import geo, log, output
from ..tool_base import TerrainTool, ToolOutput


class ProfileTool(TerrainTool):
    TITLE = "Terrain Profile & Sections"
    ROLES = (("terrain", "terrain (reference ground)"), ("design", "second surface (optional)"),
             ("alignment", "alignment (polyline)"))

    def execute(self) -> ToolOutput:
        tin = self.terrain()
        design = None
        if self.selection("design") or self.iparam("DesignSource", 0) == 1:
            design = self.terrain("design", "DesignSource", "DesignFile")
        col = self.collect("alignment")
        lines = col.all_lines_xy()
        if not lines:
            raise TerrainError("Select the alignment: a 2D/3D line or polyline (third radio button).")
        alignment = max(lines, key=geom.polyline_length)
        if len(lines) > 1:
            log.warn("Several lines selected as alignment: the longest one is used.")
        if self.bparam("Reverse", False):
            alignment = list(reversed(alignment))
        length = geom.polyline_length(alignment)
        vertex_st = []
        acc = 0.0
        for i in range(len(alignment) - 1):
            vertex_st.append(acc)
            acc += geom.dist(alignment[i], alignment[i + 1])
        vertex_st.append(acc)

        scale = self.fparam("DrawingScale", 500.0)
        th_mm = self.fparam("TextHeight", 2.5)
        style = profiles.ProfileStyle(
            v_exaggeration=self.fparam("VExaggeration", 10.0), station_interval=self.fparam("StationInterval", 20.0),
            z_interval=self.fparam("ZInterval", 1.0), text_height=output.model_text_height(th_mm, scale),
            decimals=self.iparam("Decimals", 2), draw_grid=self.bparam("Grid", True),
            draw_table=self.bparam("Table", True), title=str(self.param("Title", "Long section")))
        name_g = str(self.param("GroundName", "Ground")) or "Ground"
        name_d = str(self.param("DesignName", "Design")) or "Design"
        style_props = {"frame": geo.props(self.param("FrameProp")), "grid": geo.props(self.param("GridProp")),
                       "profile:0": geo.props(self.param("GroundProp")), "profile:1": geo.props(self.param("DesignProp")),
                       "axis": geo.props(self.param("GridProp")), "tick": geo.props(self.param("FrameProp")),
                       "text": geo.props(self.param("TextProp"))}
        default_cp = geo.props(None)
        out = ToolOutput()
        mode = self.iparam("ProfileMode", 0)

        xmin, ymin, xmax, ymax = tin.bbox()
        if self.bparam("AutoPlace", True):
            ox, oy = xmax + output.model_text_height(th_mm, scale) * 25, ymin
        else:
            ox, oy = self.fparam("PlaceX", 0.0), self.fparam("PlaceY", 0.0)

        csv_rows: List[Tuple] = []
        ground = profiles.sample_profile(tin, alignment)
        if not ground:
            raise TerrainError("The alignment does not cross the terrain.")
        series = [(name_g, ground)]
        if design is not None:
            dparts = profiles.sample_profile(design, alignment)
            if dparts:
                series.append((name_d, dparts))
            else:
                log.warn("The alignment does not cross the second surface.")
        for part in ground:
            for s in part:
                csv_rows.append((f"{s[0]:.3f}", f"{s[1]:.3f}", f"{s[2]:.3f}", f"{s[3]:.3f}"))

        height_used = 0.0
        if mode in (0, 2):
            dr = profiles.profile_drawing(series, length, style, vertex_st)
            out.elements.extend(output.drawing_elements(dr, (ox, oy), th_mm, scale, style_props, default_cp))
            height_used = dr.height
            log.log(f"Long section: length {length:.2f} m, drawn at ({ox:.2f}, {oy:.2f})")
        if mode in (1, 2):
            left = self.fparam("LeftWidth", 15.0)
            right = self.fparam("RightWidth", 15.0)
            interval = self.fparam("SectionInterval", 20.0)
            secs = profiles.cross_section_lines(alignment, interval, left, right)
            sec_data = []
            cp_sec = geo.props(self.param("SectionLineProp"))
            for st, line in secs:
                s_series = [(name_g, profiles.sample_profile(tin, line))]
                if design is not None:
                    s_series.append((name_d, profiles.sample_profile(design, line)))
                sec_data.append((st, s_series))
                if self.bparam("SectionLinesInPlan", True):
                    out.elements.append(geo.model2d(geo.polyline2d(line), cp_sec))
                    out.elements.append(geo.text(f"{st:.{style.decimals}f}", line[0][0], line[0][1], th_mm * 0.8,
                                                 geom.readable_angle_deg(line[1][0] - line[0][0], line[1][1] - line[0][1]),
                                                 "right_center", cp_sec))
            sdr = profiles.sections_drawing(sec_data, left, style, columns=max(1, self.iparam("SectionColumns", 4)))
            sy = oy - height_used - output.model_text_height(th_mm, scale) * 10 if mode == 2 else oy
            out.elements.extend(output.drawing_elements(sdr, (ox, sy), th_mm, scale, style_props, default_cp))
            log.log(f"{len(secs)} cross section(s)")
        if self.bparam("Drape3D", True):
            cp = geo.props(self.param("DrapeProp"))
            for part in tin.drape_polyline(alignment):
                out.elements.append(geo.model3d(geo.polyline3d(part), cp))
        if self.bparam("StationLabels", False):
            cp = geo.props(self.param("TextProp"))
            for st in profiles.station_marks(length, style.station_interval):
                (x, y), (ux, uy) = geom.offset_point_along(alignment, st)
                ang = geom.readable_angle_deg(-uy, ux)
                out.elements.append(geo.text(f"{st:.{style.decimals}f}", x, y, th_mm * 0.8, ang, "left_center", cp))
        output.write_csv(str(self.param("ReportFile", "")), ["Station", "X", "Y", "Z"], csv_rows)
        zs = [s[3] for p in ground for s in p]
        out.summary = (f"Alignment length {length:.2f} m, ground {min(zs):.2f} .. {max(zs):.2f} m"
                       + (" (+ second surface)" if len(series) > 1 else ""))
        return out
