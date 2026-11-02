# Terrain Toolkit for Allplan 2026

PythonParts that add terrain-modelling tools Allplan doesn't have, or only has in basic form.
All the maths runs in plain Python (no extra packages), and the results are created as normal
Allplan elements at their real coordinates.

| # | Tool | What it does | Gap it fills (compared with the built-in DTM tools) |
|---|------|--------------|------------------------------|
| 1 | **Terrain Mesh (TIN)** | Builds a constrained Delaunay mesh from 3D points, meshes and files (LandXML, XYZ/CSV/TXT, ESRI ASC, OBJ). Supports breaklines, an outer boundary, holes, concave outlines (max edge length), spike removal, grid thinning, and simplification to a vertical tolerance. | Data clean-up before meshing, decimation of LiDAR and dense surveys, reading French survey files with decimal commas, a LandXML copy of every terrain |
| 2 | **Contours** | Major and minor contours, smoothing, simplification, labels placed along the line and kept readable, 2D or 3D output | Label control, smoothing, minimum length, elevation range |
| 3 | **Slope / Aspect / Elevation** | Slope maps in % or degrees, aspect (4/8/16 sectors), exact elevation bands. Output as a coloured 3D mesh and/or 2D fillings, with a legend and an area table (CSV) | Not available in Allplan |
| 4 | **Cut & Fill** | Exact volumes from an overlay of existing vs design (or a reference elevation), inside an optional boundary. Adds a depth heat map, isopachs, the zero line, a swell factor and a CSV report | Allplan computes the volume, but gives no depth map, isopachs or report |
| 5 | **Profile & Sections** | Long section with station/elevation table, cross sections at an interval, a second surface, the alignment draped in 3D, station labels, CSV | Printable long and cross sections drawn automatically |
| 6 | **Drainage** | Flow arrows, steepest-descent flow paths, local low points, ponding depth map and volume (priority-flood depression filling) | Not available in Allplan |
| 7 | **Platform** | Pad at a fixed elevation, at the elevation that **balances cut and fill**, or from a 3D outline. Adds cut/fill daylight slopes, the daylight line, volumes, and the design surface as LandXML | Cut/fill balance optimisation; slopes split into cut and fill |
| 8 | **Import / Export** | Exports a terrain (from the model or a file) to LandXML, OBJ, XYZ, CSV or ESRI ASCII grid, with the coordinate shift added back | Exchange with Civil 3D, Covadis, Mensura, GIS and so on |
| 9 | **Diagnostics** | Checks the API, draws a test terrain, and inspects selected elements | Fast feedback loop while testing (see below) |

---

## 1. Installation

You need Allplan 2026 on Windows 11. Pick **one** of the two methods.

### A. Plugin package (`dist/TerrainToolkit.allep`)
Install `TerrainToolkit.allep` with the Allplan **Plugin Manager**, the same way you install the
official PythonParts SDK. A *Terrain Toolkit* task area with the 9 tools appears.

### B. Manual installation (`dist/TerrainToolkit_manual_install.zip`)
1. Unzip the file anywhere.
2. Double-click `install.bat`. It asks for your USR folder (to find it in Allplan: *Allmenu > Service > File Explorer >
   My own CAD documents*; usually `C:\Users\<you>\Documents\Nemetschek\Allplan\2026\Usr\Local`).
3. Restart Allplan. Open the tools from **Library > Private > Terrain Toolkit**.

Without the script, copy the folders `Library`, `PythonPartsScripts` and `PythonPartsActionbar`
into the USR folder yourself.

> **After an update** restart Allplan. Allplan keeps already-imported Python modules in memory.

---

## 2. First test (5 minutes)

1. Start **Diagnostics**, then press **Run self-test**. You should see a small green hill, brown contours, a
   text and a red square near the origin, plus a message saying "API check: all OK".
   *If something fails, send me the log (see section 4). That is the most useful first feedback.*
2. Start **Terrain Mesh**. Under *2. Points from file* select **File**, then pick
   `samples/site_points_local.xyz`. Press **Create**. You get a 120 x 90 m terrain mesh near the origin.
3. Start **Contours**. Click the mesh in the model (it is highlighted), then press **Create**.
4. Try **Slope / Aspect / Elevation**, **Drainage** (the sample has a depression and a stream) and
   **Cut & Fill**. For Cut & Fill, choose the existing terrain from the selection, set the design to *File*, and pick
   `samples/site_design.xml`. The result should be close to cut ≈ 427 m³ and fill ≈ 1 492 m³.
5. **Platform**: draw a closed polyline on the mesh, pick it as *Platform outline*, choose
   *Balance cut = fill*, then press **Create**.
6. Real-world coordinates: `samples/site_points_lambert93.csv` (semicolon separated, decimal comma) has the
   same points in Lambert-93. Load it with **Shift X = 651200** and **Shift Y = 6862400** and it lands at the same place.

---

## 3. How the tools work

Every tool uses the same workflow:

* **Section 1, Selection in the model.** Selection starts as soon as the tool opens. The radio button
  *Next selection is* sets what the next selection is used for (terrain, breaklines, boundary,
  alignment...). Selections add up, and the counter shows what you have picked.
  *Clear current* and *Clear all* reset them.
* **Section 2, Source.** Each surface comes either from the **selection** (a terrain polyhedron, or 3D points) or from
  a **file**. Points from a file and breaklines/boundaries from the model can be combined.
* **Create** runs the tool and creates plain Allplan elements in the active drawing file:
  polyhedra, 3D/2D polylines, texts and fillings. Each Create should be **one undo step** (please confirm).
* **ESC** closes the tool. The palette values are remembered for next time.

### Units and coordinates
* Every value in the palettes is in **metres**. Allplan's internal millimetres are handled for you.
* **File units** converts files written in mm, cm or ft.
* **Coordinate shift** holds the real-world coordinates of the Allplan origin. On import it is subtracted, and on export
  it is added back. The value is remembered across tools. Use it with Lambert-93, UTM, LV95 and similar systems so that
  Allplan works near its origin (this avoids display jitter).
* Every terrain built by *Terrain Mesh* is also saved as LandXML in real-world coordinates:
  `Documents\AllplanTerrainToolkit\terrains\<name>.xml`.

### Tool notes
* **Breaklines** are selected 3D lines or polylines. A 2D line has no elevation, so it is ignored with a warning. Breaklines
  that cross each other are split at the crossing. The crossing takes the elevation of the line selected first.
* **Boundary and holes** are closed polylines or polygons. A 2D boundary takes its elevation from the terrain.
* **Analysis colours.** The 3D mesh uses the closest Allplan colour number. The 2D fillings use exact RGB.
  *Lift 3D map* places the coloured mesh a few cm above the terrain so it stays visible.
* **Cut & Fill sign convention:** design **below** existing = **cut** (red), design above = **fill** (blue).
* **Platform slopes** are given as H:V. `1.5` means 3H:2V and `2` means 2H:1V.

---

## 4. Errors and feedback (what to send me)

Every message is written to:

* the Allplan **Trace** window (lines start with `[TerrainToolkit]`), and
* the log file **`%USERPROFILE%\Documents\AllplanTerrainToolkit\terrain_toolkit.log`**
  (the *Open log folder* button in every palette opens it).

When something fails, a **message box** shows the error and the path of the log.
If a tool doesn't even open, the reason is logged to the same file.

**To report a problem, send:**
1. the log file (or the end of it),
2. which tool you used and what you selected,
3. a screenshot of the result, if the result looks wrong rather than causing an error.

To get more detail, tick **Verbose log** in the palette before you press Create.
To check how an element is read (for example a terrain made with Allplan's own DTM), select it in
**Diagnostics** and press **Inspect**. Its type and API members go to the log.

---

## 5. Known limitations and unverified points (please test these first)

I wrote this without access to Allplan. Everything Allplan-independent is covered by 40 automated tests,
and the Allplan side was run end-to-end against a mock of the API. The following API details still need checking
on a real Allplan 2026 install:

| Point | Where | Fallback if it fails |
|---|---|---|
| Surface polyhedron type (`PolyhedronType.tFaces`) and the polyhedron builder | `allplan/geo.py` | Logged; Diagnostics lists the available types |
| Reading triangles back from a selected polyhedron | `geo._try_polyhedron_faces` | Vertices are re-triangulated (same result for a Delaunay TIN) |
| Several rings in a `Polygon2D` (fillings with holes) | `geo.filling` | Holes may appear filled, so use the 3D map output |
| `GetIdByColor` for analysis colours | `geo.color_id` | Logged; everything is drawn in colour 1 |
| Splines, arcs and Allplan's DTM elements as input | `geo._add_geometry` | Ignored; listed in the log ("ignored: ...") |

Other limitations:
* Plain elements are created, not parametric PythonPart objects. To change a result, run the tool again.
* Everything is pure Python. Expect about 2 s to triangulate 100 000 points. Thin very large LiDAR sets first (thinning cell, or simplify).
* Volumes are exact on the triangulated surfaces. Platform slopes are computed on a grid; its resolution is set by *Computation grid*.

---

## 6. For developers

```
PythonPartsScripts/terrain_toolkit/
    core/        pure Python algorithms (triangulation, contours, analysis, volumes, profiles,
                 drainage, grading, file formats) - no Allplan import
    allplan/     logging, Allplan conversion, shared interactor, one class per tool (allplan/tools)
    Terrain*.py  thin entry scripts referenced by the .pyp files (generated)
Library/Terrain Toolkit/*.pyp   palettes (generated)
tests/                          pytest suite + Allplan API mock
tools/                          generators: build_pyp.py, make_icons.py, make_samples.py, build_package.py
```

```bash
python -m pytest tests          # 40 tests, about 10 s
python tools/build_pyp.py       # regenerate palettes + entry scripts after editing the spec
python tools/build_package.py   # dist/TerrainToolkit.allep and the manual-install zip
```

The triangulation is a port of the sweep-hull algorithm of *Delaunator* (Mapbox, ISC licence) with
Shewchuk-style robust predicates. Constraints are added with Sloan's edge-flip algorithm.
