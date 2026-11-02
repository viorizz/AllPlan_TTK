"""Terrain exchange: export a terrain (model selection or file) to LandXML / OBJ / XYZ / ESRI ASCII grid."""
from __future__ import annotations

import os

from ...core import io_formats
from ...core.tin import TerrainError
from .. import log, settings
from ..tool_base import TerrainTool, ToolOutput

FORMATS = {0: ("LandXML", ".xml"), 1: ("Wavefront OBJ", ".obj"), 2: ("XYZ points", ".xyz"),
           3: ("CSV points", ".csv"), 4: ("ESRI ASCII grid", ".asc")}


class ExchangeTool(TerrainTool):
    TITLE = "Terrain Import/Export"
    ROLES = (("terrain", "terrain mesh / points to export"),)

    def on_start(self) -> None:
        if not any(self.shift()):
            self.set_param("ShiftX", float(settings.get("shift_x", 0.0)))
            self.set_param("ShiftY", float(settings.get("shift_y", 0.0)))
            self.set_param("ShiftZ", float(settings.get("shift_z", 0.0)))

    def execute(self) -> ToolOutput:
        tin = self.terrain()
        fmt = self.iparam("ExportFormat", 0)
        name, ext = FORMATS.get(fmt, FORMATS[0])
        path = str(self.param("ExportFile", "")).strip().strip('"')
        if not path:
            raise TerrainError("Choose the output file ('Export to').")
        if not os.path.splitext(path)[1]:
            path += ext
        # back to real-world coordinates and output units
        sx, sy, sz = self.shift() if self.bparam("ApplyShift", True) else (0.0, 0.0, 0.0)
        f = self.unit_factor("ExportUnits")
        world = tin.transformed(1.0, sx, sy, sz)
        if f != 1.0:
            world = world.transformed(1.0 / f)
        dec = self.iparam("Decimals", 3)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if fmt == 0:
            io_formats.write_landxml(path, world, str(self.param("SurfaceName", "Terrain")) or "Terrain",
                                     units="meter" if f == 1.0 else "foot", decimals=max(dec, 3))
        elif fmt == 1:
            io_formats.write_obj(path, world, decimals=dec)
        elif fmt == 2:
            io_formats.write_point_file(path, world.points, " ", dec)
        elif fmt == 3:
            io_formats.write_point_file(path, world.points, ";", dec, names=[str(i + 1) for i in range(len(world.points))])
        elif fmt == 4:
            cell = self.fparam("GridCell", 1.0)
            if cell <= 0:
                raise TerrainError("The grid cell size must be > 0.")
            nc, nr = io_formats.write_ascii_grid(path, world, cell / f, decimals=dec)
            log.log(f"Grid {nc} x {nr} cells")
        log.log(f"Exported {name}: {path}")
        out = ToolOutput(show_message=True)
        out.summary = f"{name} written:\n{path}\n{len(world.points)} points, {len(world.triangles)} triangles"
        return out
