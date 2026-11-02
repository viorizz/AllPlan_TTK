"""Longitudinal profiles and cross sections, plus their 2D drawing layout."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from . import geom
from .tin import TIN

Point2 = Tuple[float, float]
Sample = Tuple[float, float, float, float]  # station, x, y, z


def sample_profile(tin: TIN, polyline: Sequence[Sequence[float]]) -> List[List[Sample]]:
    """Exact profile of the surface below a plan polyline, split where it leaves the surface."""
    parts: List[List[Sample]] = []
    cur: List[Sample] = []
    acc = 0.0
    for i in range(len(polyline) - 1):
        a = polyline[i]
        b = polyline[i + 1]
        seg = geom.dist(a, b)
        if seg == 0:
            continue
        hits = tin.intersect_segment(a, b)
        prev_s = None
        for (s, x, y, z) in hits:
            st = acc + s * seg
            if cur and abs(cur[-1][0] - st) < 1e-9:
                continue
            if cur and prev_s is not None:
                mx = a[0] + (b[0] - a[0]) * (s + prev_s) / 2
                my = a[1] + (b[1] - a[1]) * (s + prev_s) / 2
                if tin.z_at(mx, my) is None:
                    parts.append(cur)
                    cur = []
            elif cur and prev_s is None and s > 1e-9:
                mx = a[0] + (b[0] - a[0]) * s / 2
                my = a[1] + (b[1] - a[1]) * s / 2
                if tin.z_at(mx, my) is None:
                    parts.append(cur)
                    cur = []
            cur.append((st, x, y, z))
            prev_s = s
        if not hits and cur:
            parts.append(cur)
            cur = []
        acc += seg
    if cur:
        parts.append(cur)
    return [p for p in parts if len(p) >= 2]


def z_at_station(parts: Sequence[Sequence[Sample]], station: float) -> Optional[float]:
    for part in parts:
        if part[0][0] - 1e-9 <= station <= part[-1][0] + 1e-9:
            for i in range(len(part) - 1):
                s0, s1 = part[i][0], part[i + 1][0]
                if s0 - 1e-9 <= station <= s1 + 1e-9:
                    if s1 == s0:
                        return part[i][3]
                    t = (station - s0) / (s1 - s0)
                    return part[i][3] + (part[i + 1][3] - part[i][3]) * t
    return None


def station_marks(length: float, interval: float, vertices: Optional[Sequence[float]] = None) -> List[float]:
    marks = set()
    if interval > 0:
        n = int(math.floor(length / interval + 1e-9))
        for k in range(n + 1):
            marks.add(round(k * interval, 9))
    marks.add(0.0)
    marks.add(round(length, 9))
    for v in vertices or []:
        marks.add(round(v, 9))
    return sorted(marks)


def cross_section_lines(alignment: Sequence[Sequence[float]], interval: float, left: float, right: float,
                        start: float = 0.0) -> List[Tuple[float, List[Point2]]]:
    """Section lines perpendicular to the alignment. Left is to the left of the direction of travel."""
    length = geom.polyline_length(alignment)
    out = []
    st = start
    while st <= length + 1e-9:
        (x, y), (ux, uy) = geom.offset_point_along([(p[0], p[1]) for p in alignment], st)
        nx, ny = -uy, ux  # left normal
        out.append((st, [(x + nx * left, y + ny * left), (x - nx * right, y - ny * right)]))
        if interval <= 0:
            break
        st += interval
    return out


# ---------------------------------------------------------------------------
# drawing layout
# ---------------------------------------------------------------------------
@dataclass
class Drawing:
    """2D primitives in model units: polylines with a style key and texts."""
    lines: List[Tuple[List[Point2], str]] = field(default_factory=list)
    texts: List[Tuple[str, float, float, float, float, str]] = field(default_factory=list)  # text,x,y,height,angle,anchor
    width: float = 0.0
    height: float = 0.0

    def add_text(self, text: str, x: float, y: float, h: float, angle: float = 0.0, anchor: str = "left_bottom") -> None:
        self.texts.append((text, x, y, h, angle, anchor))

    def translate(self, dx: float, dy: float) -> None:
        self.lines = [([(p[0] + dx, p[1] + dy) for p in pts], st) for pts, st in self.lines]
        self.texts = [(t, x + dx, y + dy, h, a, an) for (t, x, y, h, a, an) in self.texts]


@dataclass
class ProfileStyle:
    v_exaggeration: float = 10.0
    station_interval: float = 20.0
    z_interval: float = 1.0
    text_height: float = 2.0         # model units (m)
    decimals: int = 2
    draw_grid: bool = True
    draw_table: bool = True
    datum: Optional[float] = None    # reference elevation of the bottom line
    title: str = ""


def _nice_floor(v: float, step: float) -> float:
    return math.floor(v / step) * step if step > 0 else v


def profile_drawing(series: Sequence[Tuple[str, Sequence[Sequence[Sample]]]], length: float,
                    style: ProfileStyle, vertex_stations: Optional[Sequence[float]] = None) -> Drawing:
    """Lay out a long section. series = [(name, parts), ...]; first series is the reference ground."""
    dr = Drawing()
    v = style.v_exaggeration if style.v_exaggeration > 0 else 1.0
    th = style.text_height
    zs = [s[3] for _, parts in series for part in parts for s in part]
    if not zs:
        return dr
    zmin, zmax = min(zs), max(zs)
    zi = style.z_interval if style.z_interval > 0 else max((zmax - zmin) / 5.0, 0.1)
    datum = style.datum if style.datum is not None else _nice_floor(zmin - zi, zi)
    ztop = math.ceil((zmax + zi * 0.5) / zi) * zi
    h = (ztop - datum) * v
    marks = station_marks(length, style.station_interval, vertex_stations)

    row_h = th * 7.0
    n_rows = (1 + len(series)) if style.draw_table else 0
    table_h = n_rows * row_h
    y0 = table_h  # profile frame sits above the table

    def X(st: float) -> float:
        return st

    def Y(z: float) -> float:
        return y0 + (z - datum) * v

    # frame
    dr.lines.append(([(0, y0), (length, y0), (length, y0 + h), (0, y0 + h), (0, y0)], "frame"))
    # grid
    if style.draw_grid:
        z = datum + zi
        while z < ztop - 1e-9:
            dr.lines.append(([(0, Y(z)), (length, Y(z))], "grid"))
            z += zi
        for st in marks:
            if 0 < st < length:
                dr.lines.append(([(X(st), y0), (X(st), y0 + h)], "grid"))
    # elevation scale on the left
    z = datum
    while z <= ztop + 1e-9:
        dr.lines.append(([(-th, Y(z)), (0, Y(z))], "frame"))
        dr.add_text(f"{z:.{style.decimals}f}", -th * 1.5, Y(z), th, 0.0, "right_center")
        z += zi
    dr.add_text(f"Ref. {datum:.{style.decimals}f}", 0, y0 - th * 0.5 if not style.draw_table else y0 + th * 0.5,
                th, 0.0, "left_bottom")
    # profiles
    for idx, (name, parts) in enumerate(series):
        for part in parts:
            pts = [(X(s[0]), Y(s[3])) for s in part]
            dr.lines.append((pts, f"profile:{idx}"))
    # table
    if style.draw_table:
        rows = ["Distance"] + [name for name, _ in series]
        for r in range(n_rows + 1):
            yy = r * row_h
            dr.lines.append(([(-th * 14, yy), (length, yy)], "frame"))
        dr.lines.append(([(-th * 14, 0), (-th * 14, table_h)], "frame"))
        dr.lines.append(([(0, 0), (0, table_h)], "frame"))
        for r, name in enumerate(rows):
            yy = table_h - (r + 0.5) * row_h
            dr.add_text(name, -th * 13.5, yy, th, 0.0, "left_center")
        for st in marks:
            dr.lines.append(([(X(st), table_h - row_h), (X(st), table_h)], "tick"))
            dr.add_text(f"{st:.{style.decimals}f}", X(st), table_h - row_h * 0.5, th * 0.8, 90.0, "center_center")
            for r, (name, parts) in enumerate(series):
                zv = z_at_station(parts, st)
                yy = table_h - (r + 1.5) * row_h
                if zv is not None:
                    dr.add_text(f"{zv:.{style.decimals}f}", X(st), yy, th * 0.8, 90.0, "center_center")
    if style.title:
        dr.add_text(style.title, 0, y0 + h + th * 1.5, th * 1.4, 0.0, "left_bottom")
    dr.width = length + th * 14
    dr.height = y0 + h + th * 3
    return dr


def sections_drawing(sections: Sequence[Tuple[float, Sequence[Tuple[str, Sequence[Sequence[Sample]]]]]],
                     left: float, style: ProfileStyle, columns: int = 4, gap: float = 0.0) -> Drawing:
    """Arrange several cross sections in a grid. Each section: (station, series)."""
    out = Drawing()
    if not sections:
        return out
    cells: List[Drawing] = []
    for st, series in sections:
        # convert stations to offsets: offset 0 at the alignment, negative to the left
        shifted = []
        for name, parts in series:
            shifted.append((name, [[(s[0] - left, s[1], s[2], s[3]) for s in part] for part in parts]))
        d = _section_cell(st, shifted, style)
        cells.append(d)
    cw = max(c.width for c in cells) + (gap or style.text_height * 6)
    ch = max(c.height for c in cells) + (gap or style.text_height * 6)
    for i, c in enumerate(cells):
        col = i % max(1, columns)
        row = i // max(1, columns)
        c.translate(col * cw, -row * ch)
        out.lines.extend(c.lines)
        out.texts.extend(c.texts)
    out.width = cw * min(columns, len(cells))
    out.height = ch * ((len(cells) + columns - 1) // columns)
    return out


def _section_cell(station: float, series, style: ProfileStyle) -> Drawing:
    dr = Drawing()
    v = style.v_exaggeration if style.v_exaggeration > 0 else 1.0
    th = style.text_height
    offs = [s[0] for _, parts in series for p in parts for s in p]
    zs = [s[3] for _, parts in series for p in parts for s in p]
    if not zs:
        dr.add_text(f"Station {station:.{style.decimals}f}: no surface", 0, 0, th)
        dr.width = th * 20
        dr.height = th * 3
        return dr
    omin, omax = min(offs), max(offs)
    zi = style.z_interval if style.z_interval > 0 else 1.0
    datum = _nice_floor(min(zs) - zi * 0.5, zi)
    ztop = math.ceil((max(zs) + zi * 0.5) / zi) * zi

    def Y(z):
        return (z - datum) * v

    dr.lines.append(([(omin, 0), (omax, 0), (omax, Y(ztop)), (omin, Y(ztop)), (omin, 0)], "frame"))
    if style.draw_grid:
        z = datum + zi
        while z < ztop - 1e-9:
            dr.lines.append(([(omin, Y(z)), (omax, Y(z))], "grid"))
            z += zi
    dr.lines.append(([(0, 0), (0, Y(ztop))], "axis"))
    for idx, (name, parts) in enumerate(series):
        for part in parts:
            dr.lines.append(([(s[0], Y(s[3])) for s in part], f"profile:{idx}"))
    zc = None
    for _, parts in series[:1]:
        zc = z_at_station(parts, 0.0)
    label = f"Station {station:.{style.decimals}f}"
    if zc is not None:
        label += f"   z = {zc:.{style.decimals}f}"
    dr.add_text(label, omin, Y(ztop) + th * 0.8, th, 0.0, "left_bottom")
    dr.add_text(f"{datum:.{style.decimals}f}", omin - th * 0.5, 0, th * 0.8, 0.0, "right_center")
    dr.translate(-omin, 0)
    dr.width = omax - omin
    dr.height = Y(ztop) + th * 3
    return dr
