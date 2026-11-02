"""Terrain file formats: XYZ/CSV/TXT point files, LandXML, ESRI ASCII grid, Wavefront OBJ."""
from __future__ import annotations

import math
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .tin import TIN, TerrainError, tin_from_mesh

Point3 = Tuple[float, float, float]


@dataclass
class PointFileResult:
    points: List[Point3] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    codes: List[str] = field(default_factory=list)
    skipped_lines: int = 0
    header: Optional[str] = None
    delimiter: str = ""
    layout: str = ""
    decimal_comma: bool = False


_NUM = re.compile(r"^[+-]?(\d+([.,]\d*)?|[.,]\d+)([eE][+-]?\d+)?$")


def _is_num(tok: str) -> bool:
    return bool(_NUM.match(tok.strip()))


def _detect_delimiter(lines: Sequence[str]) -> Tuple[str, bool]:
    """Returns (delimiter, decimal_comma). delimiter '' means whitespace."""
    sample = [l for l in lines if l.strip() and not l.lstrip().startswith(("#", "//"))][:50]
    if not sample:
        return "", False
    for d in (";", "\t"):
        counts = [l.count(d) for l in sample]
        if min(counts) >= 2 and len(set(counts)) <= 2:
            # with ';' or tab, commas between digits are decimal separators
            return d, any(re.search(r"\d,\d", l) for l in sample)
    if all(len(l.split()) >= 3 for l in sample):
        toks = [t for l in sample for t in l.split()]
        has_comma_dec = any(re.fullmatch(r"[+-]?\d+,\d+", t) for t in toks)
        has_dot_dec = any(re.fullmatch(r"[+-]?\d+\.\d+", t) for t in toks)
        if has_comma_dec and not has_dot_dec:
            return "", True
        if not any("," in l for l in sample):
            return "", False
    counts = [l.count(",") for l in sample]
    if min(counts) >= 2:
        return ",", False
    return "", False


def _split(line: str, delim: str) -> List[str]:
    if delim == "":
        return line.split()
    return [t.strip() for t in line.split(delim)]


def read_point_file(path: str, layout: str = "auto", delimiter: str = "auto",
                    decimal_comma: Optional[bool] = None, skip_rows: int = 0,
                    max_points: int = 0) -> PointFileResult:
    """Read survey points.

    layout: 'auto', or letters naming the columns: X/E = easting, Y/N = northing, Z = elevation,
            P = point name, D = description/code, '-' = ignore. Examples: 'XYZ', 'PXYZ', 'PNEZD', 'PENZ', 'YXZ'.
    """
    if not os.path.isfile(path):
        raise TerrainError(f"Point file not found: {path}")
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        lines = fh.read().splitlines()
    res = PointFileResult()
    if delimiter == "auto":
        delim, dec = _detect_delimiter(lines[skip_rows:])
    else:
        delim = {"space": "", "whitespace": "", "tab": "\t"}.get(delimiter, delimiter)
        dec = False
    if decimal_comma is not None:
        dec = decimal_comma
    res.delimiter = delim or "whitespace"
    res.decimal_comma = dec

    def num(tok: str) -> float:
        t = tok.strip()
        if dec:
            t = t.replace(".", "").replace(",", ".") if t.count(",") == 1 and t.count(".") > 0 else t.replace(",", ".")
        return float(t)

    rows: List[List[str]] = []
    for ln, line in enumerate(lines):
        if ln < skip_rows:
            continue
        s = line.strip()
        if not s or s.startswith(("#", "//", "!")):
            continue
        toks = _split(s, delim)
        if delim == "" and dec is False and len(toks) > 1:
            pass
        rows.append(toks)

    lay = layout.upper().replace(" ", "")
    if lay in ("", "AUTO"):
        lay = _guess_layout(rows, num)
    res.layout = lay
    xi = _first(lay, "XE")
    yi = _first(lay, "YN")
    zi = _first(lay, "Z")
    pi = _first(lay, "P")
    di = _first(lay, "D")
    if xi < 0 or yi < 0 or zi < 0:
        raise TerrainError(f"Column layout '{lay}' must contain X(E), Y(N) and Z.")
    need = max(xi, yi, zi) + 1
    for toks in rows:
        if len(toks) < need:
            res.skipped_lines += 1
            continue
        try:
            x = num(toks[xi])
            y = num(toks[yi])
            z = num(toks[zi])
        except ValueError:
            if res.header is None and not res.points:
                res.header = " ".join(toks)
            else:
                res.skipped_lines += 1
            continue
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            res.skipped_lines += 1
            continue
        res.points.append((x, y, z))
        res.names.append(toks[pi] if 0 <= pi < len(toks) else str(len(res.points)))
        res.codes.append(toks[di] if 0 <= di < len(toks) else "")
        if max_points and len(res.points) >= max_points:
            break
    if not res.points:
        raise TerrainError(f"No valid points found in {os.path.basename(path)} (layout {lay}, "
                           f"delimiter '{res.delimiter}').")
    return res


def _first(layout: str, letters: str) -> int:
    for i, ch in enumerate(layout):
        if ch in letters:
            return i
    return -1


_HEADER_NAMES = {
    "X": {"x", "e", "east", "easting", "est", "rechtswert", "xcoord", "coordx"},
    "Y": {"y", "n", "north", "northing", "nord", "hochwert", "ycoord", "coordy"},
    "Z": {"z", "h", "elev", "elevation", "alt", "altitude", "height", "hauteur", "cote", "hoehe", "zcoord", "coordz"},
    "P": {"p", "pt", "point", "pointno", "name", "id", "num", "no", "nr", "matricule", "punkt", "pnr"},
    "D": {"d", "code", "desc", "description", "layer", "attribut", "attribute", "type", "remark"},
}


def _layout_from_header(tokens: List[str]) -> Optional[str]:
    lay = []
    for t in tokens:
        key = re.sub(r"[^a-z]", "", t.lower())
        letter = "-"
        for k, names in _HEADER_NAMES.items():
            if key in names:
                letter = k
                break
        lay.append(letter)
    s = "".join(lay)
    # LandXML/survey convention: if only N/E names were used, the mapping above already handles it
    if _first(s, "X") >= 0 and _first(s, "Y") >= 0 and _first(s, "Z") >= 0:
        return s
    return None


def _guess_layout(rows: List[List[str]], num) -> str:
    # 1) header names
    for r in rows[:5]:
        flags = []
        for t in r:
            try:
                num(t)
                flags.append(True)
            except ValueError:
                flags.append(False)
        if r and not any(flags):
            lay = _layout_from_header(r)
            if lay:
                return lay
            break
    # 2) numeric analysis (rows without any number are ignored)
    data = []
    used_rows = []
    for r in rows[:300]:
        flags = []
        for t in r:
            try:
                num(t)
                flags.append(True)
            except ValueError:
                flags.append(False)
        if any(flags):
            data.append(flags)
            used_rows.append(r)
    if not data:
        return "XYZ"
    width = max(len(f) for f in data)
    numeric_cols = []
    for c in range(width):
        vals = [f[c] for f in data if c < len(f)]
        if vals and sum(vals) >= 0.8 * len(vals):
            numeric_cols.append(c)
    if len(numeric_cols) < 3:
        return "XYZ"

    def col_vals(c):
        out = []
        for r in used_rows:
            if c < len(r):
                try:
                    out.append(num(r[c]))
                except ValueError:
                    pass
        return out
    cols = numeric_cols
    layout = ["-"] * width
    if len(cols) >= 4:
        v0 = col_vals(cols[0])
        if v0 and all(float(v).is_integer() for v in v0) and (max(v0) - min(v0)) < 1e6:
            layout[cols[0]] = "P"
            cols = cols[1:]
    layout[cols[0]] = "X"
    layout[cols[1]] = "Y"
    layout[cols[2]] = "Z"
    for c in range(width):
        if layout[c] == "-" and c not in numeric_cols and c > cols[2]:
            layout[c] = "D"
            break
    for c in range(width):
        if layout[c] == "-" and c not in numeric_cols and c < cols[0]:
            layout[c] = "P"
            break
    return "".join(layout)


def write_point_file(path: str, points: Sequence[Sequence[float]], delimiter: str = " ", decimals: int = 3,
                     names: Optional[Sequence[str]] = None) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for i, p in enumerate(points):
            row = [f"{p[0]:.{decimals}f}", f"{p[1]:.{decimals}f}", f"{p[2]:.{decimals}f}"]
            if names is not None:
                row.insert(0, str(names[i]))
            fh.write(delimiter.join(row) + "\n")


# ---------------------------------------------------------------------------
# LandXML
# ---------------------------------------------------------------------------
@dataclass
class LandXMLSurface:
    name: str
    points: List[Point3]
    faces: List[Tuple[int, int, int]]
    breaklines: List[List[Point3]] = field(default_factory=list)
    boundaries: List[List[Point3]] = field(default_factory=list)


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _nums(text: Optional[str]) -> List[float]:
    if not text:
        return []
    return [float(t) for t in text.replace(",", " ").split()]


def read_landxml(path: str) -> Tuple[List[LandXMLSurface], List[Point3]]:
    """Return (surfaces, cogo points). LandXML stores coordinates as Northing Easting Elevation."""
    if not os.path.isfile(path):
        raise TerrainError(f"LandXML file not found: {path}")
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise TerrainError(f"Invalid LandXML/XML file: {exc}") from exc
    root = tree.getroot()
    surfaces: List[LandXMLSurface] = []
    cg: List[Point3] = []
    for el in root.iter():
        tag = _strip_ns(el.tag)
        if tag == "CgPoint":
            v = _nums(el.text)
            if len(v) >= 3:
                cg.append((v[1], v[0], v[2]))
        elif tag == "Surface":
            name = el.get("name", f"Surface {len(surfaces) + 1}")
            id_map: Dict[str, int] = {}
            pts: List[Point3] = []
            faces: List[Tuple[int, int, int]] = []
            bls: List[List[Point3]] = []
            bnds: List[List[Point3]] = []
            for sub in el.iter():
                st = _strip_ns(sub.tag)
                if st == "P":
                    v = _nums(sub.text)
                    if len(v) >= 3:
                        id_map[sub.get("id", str(len(pts) + 1))] = len(pts)
                        pts.append((v[1], v[0], v[2]))
                elif st == "F":
                    if sub.get("i") == "1":
                        continue  # invisible face
                    toks = (sub.text or "").split()
                    if len(toks) >= 3:
                        try:
                            ids = [id_map[t] for t in toks[:3]]
                        except KeyError:
                            continue
                        faces.append((ids[0], ids[1], ids[2]))
                elif st in ("Breakline", "Boundary"):
                    for pl in sub.iter():
                        if _strip_ns(pl.tag) in ("PntList3D", "PntList2D"):
                            v = _nums(pl.text)
                            dim = 3 if _strip_ns(pl.tag) == "PntList3D" else 2
                            line = []
                            for k in range(0, len(v) - dim + 1, dim):
                                if dim == 3:
                                    line.append((v[k + 1], v[k], v[k + 2]))
                                else:
                                    line.append((v[k + 1], v[k], float("nan")))
                            if len(line) >= 2:
                                (bls if st == "Breakline" else bnds).append(line)
            surfaces.append(LandXMLSurface(name, pts, faces, bls, bnds))
    return surfaces, cg


def landxml_to_tin(path: str, surface_name: str = "") -> Tuple[TIN, str]:
    surfaces, cg = read_landxml(path)
    usable = [s for s in surfaces if s.points]
    if surface_name:
        usable = [s for s in usable if s.name == surface_name] or usable
    if usable:
        s = usable[0]
        if s.faces:
            return tin_from_mesh(s.points, s.faces), s.name
        from .tin import build_tin
        return build_tin(s.points, breaklines=s.breaklines), s.name
    if cg:
        from .tin import build_tin
        return build_tin(cg), "CgPoints"
    raise TerrainError("The LandXML file contains no surface and no CgPoints.")


def write_landxml(path: str, tin: TIN, name: str = "Terrain", units: str = "meter", decimals: int = 4,
                  description: str = "Allplan Terrain Toolkit") -> None:
    lin = "meter" if units.startswith("m") else units
    area = "squareMeter" if lin == "meter" else "squareFoot"
    vol = "cubicMeter" if lin == "meter" else "cubicFeet"
    zmin, zmax = tin.z_range()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        fh.write('<LandXML xmlns="http://www.landxml.org/schema/LandXML-1.2" version="1.2" '
                 'date="2026-01-01" time="00:00:00">\n')
        fh.write(f'  <Units><Metric linearUnit="{lin}" areaUnit="{area}" volumeUnit="{vol}" '
                 'temperatureUnit="celsius" pressureUnit="milliBars" angularUnit="decimal degrees" '
                 'directionUnit="decimal degrees"/></Units>\n')
        fh.write(f'  <Application name="{description}" version="1.0"/>\n')
        fh.write('  <Surfaces>\n')
        fh.write(f'    <Surface name="{_xml_escape(name)}">\n')
        fh.write(f'      <Definition surfType="TIN" area2DSurf="{tin.area_2d():.3f}" '
                 f'area3DSurf="{tin.area_3d():.3f}" elevMax="{zmax:.3f}" elevMin="{zmin:.3f}">\n')
        fh.write('        <Pnts>\n')
        f = decimals
        for i, p in enumerate(tin.points):
            fh.write(f'          <P id="{i + 1}">{p[1]:.{f}f} {p[0]:.{f}f} {p[2]:.{f}f}</P>\n')
        fh.write('        </Pnts>\n        <Faces>\n')
        for a, b, c in tin.triangles:
            fh.write(f'          <F>{a + 1} {b + 1} {c + 1}</F>\n')
        fh.write('        </Faces>\n      </Definition>\n')
        if tin.breaklines:
            fh.write('      <SourceData><Breaklines>\n')
            for k, bl in enumerate(tin.breaklines):
                coords = " ".join(f"{p[1]:.{f}f} {p[0]:.{f}f} {p[2]:.{f}f}" for p in bl)
                fh.write(f'        <Breakline name="BL{k + 1}"><PntList3D>{coords}</PntList3D></Breakline>\n')
            fh.write('      </Breaklines></SourceData>\n')
        fh.write('    </Surface>\n  </Surfaces>\n</LandXML>\n')


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------------------
# ESRI ASCII grid
# ---------------------------------------------------------------------------
@dataclass
class AsciiGrid:
    ncols: int
    nrows: int
    xll: float      # lower-left cell centre
    yll: float
    cell: float
    nodata: float
    values: List[List[float]]   # rows from top (north) to bottom

    def points(self, step: int = 1) -> List[Point3]:
        out = []
        step = max(1, step)
        for r in range(0, self.nrows, step):
            y = self.yll + (self.nrows - 1 - r) * self.cell
            row = self.values[r]
            for c in range(0, self.ncols, step):
                z = row[c]
                if z == self.nodata or not math.isfinite(z):
                    continue
                out.append((self.xll + c * self.cell, y, z))
        return out

    def to_tin(self, step: int = 1) -> TIN:
        """Regular grid triangulation (faster than Delaunay, exact for the raster)."""
        step = max(1, step)
        rows = list(range(0, self.nrows, step))
        cols = list(range(0, self.ncols, step))
        idx: Dict[Tuple[int, int], int] = {}
        pts: List[Point3] = []
        for r in rows:
            y = self.yll + (self.nrows - 1 - r) * self.cell
            for c in cols:
                z = self.values[r][c]
                if z == self.nodata or not math.isfinite(z):
                    continue
                idx[(r, c)] = len(pts)
                pts.append((self.xll + c * self.cell, y, z))
        tris = []
        for i in range(len(rows) - 1):
            for j in range(len(cols) - 1):
                a = idx.get((rows[i], cols[j]))
                b = idx.get((rows[i], cols[j + 1]))
                c = idx.get((rows[i + 1], cols[j]))
                d = idx.get((rows[i + 1], cols[j + 1]))
                if a is not None and b is not None and d is not None:
                    tris.append((a, b, d))
                if a is not None and d is not None and c is not None:
                    tris.append((a, d, c))
                if a is None and b is not None and c is not None and d is not None:
                    tris.append((b, d, c))
                if d is None and a is not None and b is not None and c is not None:
                    tris.append((a, b, c))
        if not tris:
            raise TerrainError("The grid has no valid cells.")
        return TIN(pts, tris, compact=True)


def read_ascii_grid(path: str) -> AsciiGrid:
    if not os.path.isfile(path):
        raise TerrainError(f"Grid file not found: {path}")
    header: Dict[str, float] = {}
    values: List[List[float]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            toks = s.split()
            key = toks[0].lower()
            if not values and key in ("ncols", "nrows", "xllcorner", "yllcorner", "xllcenter", "yllcenter",
                                      "cellsize", "nodata_value", "dx", "dy"):
                header[key] = float(toks[1].replace(",", "."))
                continue
            values.append([float(t.replace(",", ".")) for t in toks])
    try:
        ncols = int(header["ncols"])
        nrows = int(header["nrows"])
        cell = header.get("cellsize", header.get("dx", 0.0))
    except KeyError as exc:
        raise TerrainError(f"ESRI ASCII grid header is missing {exc}.") from exc
    flat = [v for row in values for v in row]
    if len(flat) < ncols * nrows:
        raise TerrainError(f"Grid has {len(flat)} values, expected {ncols * nrows}.")
    rows = [flat[r * ncols:(r + 1) * ncols] for r in range(nrows)]
    if "xllcenter" in header:
        xll, yll = header["xllcenter"], header["yllcenter"]
    else:
        xll = header.get("xllcorner", 0.0) + cell / 2.0
        yll = header.get("yllcorner", 0.0) + cell / 2.0
    return AsciiGrid(ncols, nrows, xll, yll, cell, header.get("nodata_value", -9999.0), rows)


def write_ascii_grid(path: str, tin: TIN, cell: float, nodata: float = -9999.0, decimals: int = 3) -> Tuple[int, int]:
    xmin, ymin, xmax, ymax = tin.bbox()
    ncols = int(math.floor((xmax - xmin) / cell)) + 1
    nrows = int(math.floor((ymax - ymin) / cell)) + 1
    if ncols * nrows > 25_000_000:
        raise TerrainError("Grid would be too large; increase the cell size.")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"ncols {ncols}\nnrows {nrows}\nxllcenter {xmin:.4f}\nyllcenter {ymin:.4f}\n"
                 f"cellsize {cell}\nNODATA_value {nodata}\n")
        for r in range(nrows):
            y = ymin + (nrows - 1 - r) * cell
            vals = []
            for c in range(ncols):
                z = tin.z_at(xmin + c * cell, y)
                vals.append(f"{z:.{decimals}f}" if z is not None else f"{nodata}")
            fh.write(" ".join(vals) + "\n")
    return ncols, nrows


# ---------------------------------------------------------------------------
# OBJ
# ---------------------------------------------------------------------------
def read_obj(path: str, y_up: bool = False) -> TIN:
    if not os.path.isfile(path):
        raise TerrainError(f"OBJ file not found: {path}")
    pts: List[Point3] = []
    faces: List[List[int]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("v "):
                v = [float(t) for t in line.split()[1:4]]
                if y_up:
                    pts.append((v[0], -v[2], v[1]))
                else:
                    pts.append((v[0], v[1], v[2]))
            elif line.startswith("f "):
                ids = []
                for tok in line.split()[1:]:
                    i = int(tok.split("/")[0])
                    ids.append(i - 1 if i > 0 else len(pts) + i)
                faces.append(ids)
    if not pts or not faces:
        raise TerrainError("OBJ file has no vertices/faces.")
    return tin_from_mesh(pts, faces)


def write_obj(path: str, tin: TIN, decimals: int = 4, origin: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
    ox, oy, oz = origin
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Allplan Terrain Toolkit\n")
        if any(origin):
            fh.write(f"# coordinates shifted by -({ox}, {oy}, {oz})\n")
        for p in tin.points:
            fh.write(f"v {p[0] - ox:.{decimals}f} {p[1] - oy:.{decimals}f} {p[2] - oz:.{decimals}f}\n")
        for a, b, c in tin.triangles:
            fh.write(f"f {a + 1} {b + 1} {c + 1}\n")


# ---------------------------------------------------------------------------
# generic loader
# ---------------------------------------------------------------------------
TERRAIN_FILE_FILTER = ("Terrain files (*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts)|"
                       "*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts|All files (*.*)|*.*|")


def load_terrain_file(path: str, layout: str = "auto", grid_step: int = 1, obj_y_up: bool = False,
                      log=None) -> Tuple[Optional[TIN], List[Point3], List[List[Point3]], str]:
    """Load any supported file. Returns (tin or None, points, breaklines, description).

    Point files return only points (the caller builds the TIN with its options).
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xml", ".landxml"):
        surfaces, cg = read_landxml(path)
        usable = [s for s in surfaces if s.points]
        if usable:
            s = usable[0]
            if s.faces:
                return tin_from_mesh(s.points, s.faces), s.points, s.breaklines, f"LandXML surface '{s.name}'"
            return None, s.points, s.breaklines, f"LandXML points of '{s.name}'"
        if cg:
            return None, cg, [], "LandXML CgPoints"
        raise TerrainError("LandXML file has no surface or points.")
    if ext == ".asc":
        g = read_ascii_grid(path)
        tin = g.to_tin(grid_step)
        return tin, tin.points, [], f"ESRI ASCII grid {g.ncols}x{g.nrows}, cell {g.cell}"
    if ext == ".obj":
        tin = read_obj(path, obj_y_up)
        return tin, tin.points, [], "OBJ mesh"
    res = read_point_file(path, layout)
    if log:
        log(f"Read {len(res.points)} points (layout {res.layout}, delimiter '{res.delimiter}', "
            f"decimal comma {res.decimal_comma}, skipped {res.skipped_lines} line(s)).")
    return None, res.points, [], f"point file ({res.layout})"
