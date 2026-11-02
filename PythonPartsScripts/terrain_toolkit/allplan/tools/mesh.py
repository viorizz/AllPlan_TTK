"""Terrain Mesh: build a TIN from survey points (file and/or model), breaklines, boundary and holes."""
from __future__ import annotations

import os
import re
from typing import List

from ...core import io_formats, simplify
from ...core.tin import TerrainError, build_tin
from .. import geo, log, settings
from ..tool_base import TerrainTool, ToolOutput


class TerrainMeshTool(TerrainTool):
    TITLE = "Terrain Mesh"
    ROLES = (("terrain", "terrain points / meshes"), ("breaklines", "breaklines (3D lines)"),
             ("boundary", "outer boundary (closed polyline)"), ("holes", "holes / voids (closed polylines)"))

    def on_start(self) -> None:
        # pre-fill the coordinate shift with the last used one
        if not any(self.shift()):
            self.set_param("ShiftX", float(settings.get("shift_x", 0.0)))
            self.set_param("ShiftY", float(settings.get("shift_y", 0.0)))
            self.set_param("ShiftZ", float(settings.get("shift_z", 0.0)))

    def execute(self) -> ToolOutput:
        pts: List = []
        bls: List = []
        file_desc = ""
        file_mesh = None
        # ---------------------------------------------------------- sources
        if self.iparam("TerrainSource", 0) == 1:
            path = str(self.param("TerrainFile", "")).strip().strip('"')
            if not path:
                raise TerrainError("Choose a terrain file (or switch the source to 'Selection in model').")
            f = self.unit_factor()
            sx, sy, sz = self.shift()
            tin_f, fpts, fbls, file_desc = io_formats.load_terrain_file(
                path, layout=str(self.param("FileLayout", "auto")), grid_step=self.iparam("GridStep", 1),
                obj_y_up=self.bparam("ObjYUp", False), log=log.log)

            def tr(p):
                return (p[0] * f - sx, p[1] * f - sy, p[2] * f - sz)
            pts.extend(tr(p) for p in fpts)
            bls.extend([tr(p) for p in bl] for bl in fbls)
            if tin_f is not None:
                file_mesh = (tin_f, tr)
            settings.set_values(last_terrain_file=path, shift_x=sx, shift_y=sy, shift_z=sz)
            log.log(f"File: {file_desc}, {len(fpts)} point(s), {len(fbls)} breakline(s)")

        col = self.collect("terrain")
        pts.extend(col.points)
        for verts, _faces in col.meshes:
            pts.extend(verts)
        # 3D lines selected as "terrain" contribute their vertices and act as breaklines too
        bls.extend(col.lines3d)
        bl_col = self.collect("breaklines")
        bls.extend(bl_col.lines3d)
        if bl_col.lines2d:
            log.warn(f"{len(bl_col.lines2d)} 2D line(s) selected as breaklines were ignored (they have no elevation).")
        boundary = None
        b_rings = geo.closed_rings(self.collect("boundary"))
        if b_rings:
            boundary = max(b_rings, key=lambda r: abs(_area(r)))
            if len(b_rings) > 1:
                log.warn("Several closed outlines selected as boundary: the largest one is used.")
        holes = geo.closed_rings(self.collect("holes"))
        if self.selection("boundary") and boundary is None:
            raise TerrainError("The selected boundary is not a closed polyline/polygon.")

        # ---------------------------------------------------------- cleaning
        thin = self.fparam("ThinCell", 0.0)
        if thin > 0 and pts:
            n0 = len(pts)
            pts = simplify.thin_grid(pts, thin, "mean")
            log.log(f"Grid thinning ({thin} m): {n0} -> {len(pts)} points")
        if self.bparam("RemoveSpikes", False) and len(pts) > 10:
            pts, removed = simplify.remove_spikes(pts, self.fparam("SpikeThreshold", 1.0))
            log.log(f"Spike removal: {removed} point(s) removed")
        if self.bparam("Simplify", False) and len(pts) > 10:
            n0 = len(pts)
            pts, err = simplify.simplify_points(pts, self.fparam("SimplifyTol", 0.05), log=log.debug)
            log.log(f"Simplification: {n0} -> {len(pts)} points (max vertical error {err:.3f} m)")

        # ---------------------------------------------------------- triangulate
        options = dict(max_edge=self.fparam("MaxEdge", 0.0), dedupe_tol=max(self.fparam("DedupeTol", 0.001), 1e-6))
        use_file_mesh = (file_mesh is not None and not bls and boundary is None and not holes and not col.count
                         and not self.bparam("Simplify", False) and not self.bparam("RemoveSpikes", False)
                         and thin <= 0)
        with log.Timer("Triangulation"):
            if use_file_mesh:
                tin_f, tr = file_mesh
                from ...core.tin import TIN
                tin = TIN([tr(p) for p in tin_f.points], tin_f.triangles, compact=False)
                log.log("Using the triangles stored in the file.")
            else:
                if len(pts) < 3 and not bls:
                    raise TerrainError("Select terrain points/meshes in the model (first radio button) "
                                       "or choose a terrain file.")
                tin = build_tin(pts, breaklines=bls, boundary=boundary, holes=holes, log=log.log, **options)
        self.check_coordinates(tin)

        # ---------------------------------------------------------- output
        out = ToolOutput()
        max_faces = max(1000, self.iparam("MaxFaces", 30000))
        if self.bparam("CreateMesh", True):
            cp = geo.props(self.param("MeshProp"))
            polys = geo.tin_to_polyhedra(tin, max_faces)
            out.elements.extend(geo.model3d(p, cp) for p in polys)
            log.log(f"Mesh: {len(polys)} polyhedron element(s)")
        if self.bparam("CreateOutline", False):
            cp = geo.props(self.param("OutlineProp"))
            for ring in tin.boundary_rings():
                pl = [tin.points[i] for i in ring] + [tin.points[ring[0]]]
                out.elements.append(geo.model3d(geo.polyline3d(pl), cp))
        if self.bparam("CreateBreaklines", False) and tin.breaklines:
            cp = geo.props(self.param("BreaklineProp"))
            for bl in tin.breaklines:
                out.elements.append(geo.model3d(geo.polyline3d(bl), cp))
        if self.bparam("CreatePoints", False):
            cp = geo.props(self.param("PointProp"))
            size = self.fparam("PointSize", 0.25)
            limit = 20000
            for p in tin.points[:limit]:
                out.elements.extend(geo.cross3d(p, size, cp))
            if len(tin.points) > limit:
                log.warn(f"Only the first {limit} points were drawn as crosses.")

        saved = ""
        if self.bparam("SaveLandXML", True):
            name = str(self.param("TerrainName", "Terrain")).strip() or "Terrain"
            safe = re.sub(r"[^A-Za-z0-9_\-]+", "_", name)
            path = os.path.join(settings.terrain_library_dir(), f"{safe}.xml")
            sx, sy, sz = self.shift()
            io_formats.write_landxml(path, tin.transformed(1.0, sx, sy, sz), name)
            saved = path
            log.log(f"Terrain saved as LandXML (real-world coordinates): {path}")

        zmin, zmax = tin.z_range()
        s = tin.summary()
        out.summary = (f"{s['points']} vertices, {s['triangles']} triangles\n"
                       f"Elevation {zmin:.3f} .. {zmax:.3f} m\n"
                       f"Plan area {s['area_2d']:.1f} m², surface area {s['area_3d']:.1f} m²")
        if tin.info.get("failed_constraints"):
            out.summary += f"\nWARNING: {tin.info['failed_constraints']} breakline segment(s) could not be enforced."
        if saved:
            out.summary += f"\nLandXML copy: {saved}"
        return out


def _area(ring) -> float:
    a = 0.0
    n = len(ring)
    for i in range(n):
        a += ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1]
    return a / 2.0
