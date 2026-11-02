"""Shared output builders: coloured class maps, legends, 2D drawings, reports."""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Optional, Sequence, Tuple

from ..core import analysis, colors
from ..core.profiles import Drawing
from . import geo, log

RGB = Tuple[int, int, int]


def model_text_height(text_mm: float, scale: float) -> float:
    """Text height in model metres for a paper height in mm at drawing scale 1:scale."""
    return text_mm * max(scale, 1.0) / 1000.0


def class_map_elements(result: analysis.AnalysisResult, mode: int, base_props, z_offset: float = 0.0,
                       max_faces: int = 30000) -> List[object]:
    """mode: 0 = 3D coloured mesh, 1 = 2D fillings, 2 = both."""
    out: List[object] = []
    for cls in result.classes:
        if not cls.triangles:
            continue
        cp = geo.props(base_props, rgb=cls.color)
        if mode in (0, 2):
            tris = cls.triangles
            if z_offset:
                tris = [tuple((p[0], p[1], p[2] + z_offset) for p in t) for t in tris]  # type: ignore[misc]
            for poly in geo.triangles_to_polyhedra(tris, max_faces):
                out.append(geo.model3d(poly, cp))
        if mode in (1, 2) and cls.regions:
            out.extend(geo.filling(cls.regions, cls.color, cp))
    return out


def legend_elements(title: str, rows: Sequence[Tuple[str, RGB, str]], x: float, y: float, text_mm: float,
                    scale: float, base_props) -> List[object]:
    """Legend with colour boxes. rows = [(label, rgb, extra text e.g. area), ...]. (x, y) = top-left (m)."""
    th = model_text_height(text_mm, scale)
    box = th * 1.6
    gap = th * 0.6
    out: List[object] = []
    cp_text = geo.props(base_props)
    out.append(geo.text(title, x, y, text_mm * 1.3, 0.0, "left_bottom", cp_text))
    yy = y - th * 1.2
    for label, rgb, extra in rows:
        y0 = yy - box
        ring = [(x, y0), (x + box * 1.6, y0), (x + box * 1.6, yy), (x, yy)]
        cp = geo.props(base_props, rgb=rgb)
        out.extend(geo.filling([(ring, [])], rgb, cp))
        out.append(geo.model2d(geo.polyline2d(ring + [ring[0]]), cp_text))
        out.append(geo.text(label, x + box * 1.6 + gap, y0 + box / 2, text_mm, 0.0, "left_center", cp_text))
        if extra:
            out.append(geo.text(extra, x + box * 1.6 + gap + th * 14, y0 + box / 2, text_mm, 0.0, "left_center",
                                cp_text))
        yy = y0 - gap
    return out


def analysis_legend(result: analysis.AnalysisResult, title: str, x: float, y: float, text_mm: float,
                    scale: float, base_props, area_decimals: int = 1) -> List[object]:
    rows = []
    for cls in result.classes:
        pct = 100.0 * cls.area_2d / result.total_area_2d if result.total_area_2d else 0.0
        rows.append((cls.label, cls.color, f"{cls.area_2d:,.{area_decimals}f} m²  ({pct:.1f} %)".replace(",", " ")))
    return legend_elements(title, rows, x, y, text_mm, scale, base_props)


def drawing_elements(dr: Drawing, origin: Tuple[float, float], text_mm: float, scale: float,
                     style_props: Dict[str, object], default_props) -> List[object]:
    """Convert a core Drawing (model metres, local origin) to Allplan 2D elements."""
    ox, oy = origin
    th_model = model_text_height(text_mm, scale)
    out: List[object] = []
    for pts, style in dr.lines:
        if len(pts) < 2:
            continue
        cp = style_props.get(style)
        if cp is None and style.startswith("profile:"):
            cp = style_props.get("profile")
        cp = cp or default_props
        out.append(geo.model2d(geo.polyline2d([(p[0] + ox, p[1] + oy) for p in pts]), cp))
    cp_text = style_props.get("text") or default_props
    for (txt, x, y, h, ang, anchor) in dr.texts:
        mm = text_mm * (h / th_model) if th_model > 0 else text_mm
        out.append(geo.text(txt, x + ox, y + oy, mm, ang, anchor, cp_text))
    return out


def write_csv(path: str, header: Sequence[str], rows: Sequence[Sequence[object]]) -> Optional[str]:
    if not path:
        return None
    path = path.strip().strip('"')
    if not path:
        return None
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(header)
            for r in rows:
                w.writerow(r)
        log.log(f"Report written: {path}")
        return path
    except OSError as exc:
        log.warn(f"Could not write report {path}: {exc}")
        return None


def ramp_colors(name: str, n: int, reverse: bool = False) -> List[RGB]:
    return colors.ramp(name, n, reverse)
