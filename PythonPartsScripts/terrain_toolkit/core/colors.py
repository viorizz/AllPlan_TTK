"""Colour ramps (RGB 0-255) for analysis maps."""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

RGB = Tuple[int, int, int]

RAMPS: Dict[str, List[RGB]] = {
    # slope: flat = green, steep = red
    "slope": [(26, 150, 65), (166, 217, 106), (255, 255, 191), (253, 174, 97), (215, 25, 28), (128, 0, 38)],
    # hypsometric tints
    "terrain": [(0, 104, 55), (49, 163, 84), (173, 221, 142), (255, 255, 178), (254, 204, 92),
                (227, 137, 52), (166, 97, 26), (120, 80, 60), (200, 200, 200), (255, 255, 255)],
    # cut (red) -> no change (white) -> fill (blue)
    "cutfill": [(103, 0, 13), (203, 24, 29), (251, 106, 74), (252, 187, 161), (245, 245, 245),
                (158, 202, 225), (66, 146, 198), (8, 81, 156), (8, 48, 107)],
    # aspect wheel N, NE, E, SE, S, SW, W, NW (flat first)
    "aspect": [(200, 200, 200), (230, 0, 0), (255, 160, 0), (255, 255, 0), (0, 200, 0),
               (0, 200, 200), (0, 120, 255), (0, 0, 200), (200, 0, 200)],
    "water": [(222, 235, 247), (158, 202, 225), (66, 146, 198), (8, 81, 156), (8, 48, 107)],
    "spectral": [(94, 79, 162), (50, 136, 189), (102, 194, 165), (171, 221, 164), (230, 245, 152),
                 (254, 224, 139), (253, 174, 97), (244, 109, 67), (213, 62, 79), (158, 1, 66)],
}

RAMP_NAMES = list(RAMPS.keys())


def _lerp(a: RGB, b: RGB, t: float) -> RGB:
    return (int(round(a[0] + (b[0] - a[0]) * t)), int(round(a[1] + (b[1] - a[1]) * t)),
            int(round(a[2] + (b[2] - a[2]) * t)))


def sample_ramp(stops: Sequence[RGB], n: int) -> List[RGB]:
    if n <= 0:
        return []
    if n == 1:
        return [stops[len(stops) // 2]]
    out = []
    for i in range(n):
        pos = i / (n - 1) * (len(stops) - 1)
        k = min(int(pos), len(stops) - 2)
        out.append(_lerp(stops[k], stops[k + 1], pos - k))
    return out


def ramp(name: str, n: int, reverse: bool = False) -> List[RGB]:
    stops = RAMPS.get(name, RAMPS["spectral"])
    if name == "aspect":
        cols = list(stops[:n]) if n <= len(stops) else sample_ramp(stops, n)
    else:
        cols = sample_ramp(stops, n)
    return list(reversed(cols)) if reverse else cols


def diverging(n_neg: int, n_pos: int) -> List[RGB]:
    """Cut classes (red, darkest first) then fill classes (blue, lightest first)."""
    neg = sample_ramp(RAMPS["cutfill"][:5], n_neg + 1)[:-1] if n_neg > 0 else []
    pos = sample_ramp(RAMPS["cutfill"][4:], n_pos + 1)[1:] if n_pos > 0 else []
    return neg + pos


def parse_rgb_list(text: str) -> List[RGB]:
    """'255,0,0; 0,255,0' or '#ff0000;#00ff00' -> list of RGB."""
    out: List[RGB] = []
    for tok in text.replace("|", ";").split(";"):
        tok = tok.strip()
        if not tok:
            continue
        if tok.startswith("#") and len(tok) == 7:
            out.append((int(tok[1:3], 16), int(tok[3:5], 16), int(tok[5:7], 16)))
        else:
            parts = [int(float(v)) for v in tok.split(",")]
            if len(parts) == 3:
                out.append((parts[0], parts[1], parts[2]))
    return out
