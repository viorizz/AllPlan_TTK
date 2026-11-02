"""Small persistent settings shared by all tools (JSON next to the log file)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from .log import log_dir, warn

_CACHE: Dict[str, Any] = {}
DEFAULTS: Dict[str, Any] = {
    "shift_x": 0.0,      # real-world coordinate (m) of the Allplan origin
    "shift_y": 0.0,
    "shift_z": 0.0,
    "last_terrain_file": "",
}


def _path() -> str:
    return os.path.join(log_dir(), "settings.json")


def load() -> Dict[str, Any]:
    if _CACHE:
        return _CACHE
    data = dict(DEFAULTS)
    try:
        if os.path.exists(_path()):
            with open(_path(), "r", encoding="utf-8") as fh:
                data.update(json.load(fh))
    except (OSError, ValueError) as exc:
        warn(f"Could not read settings ({exc}); using defaults.")
    _CACHE.update(data)
    return _CACHE


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def set_values(**kwargs: Any) -> None:
    data = load()
    data.update(kwargs)
    try:
        with open(_path(), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError as exc:
        warn(f"Could not save settings: {exc}")


def terrain_library_dir() -> str:
    d = os.path.join(log_dir(), "terrains")
    os.makedirs(d, exist_ok=True)
    return d
