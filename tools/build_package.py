"""Build the distributable packages into dist/.

    dist/TerrainToolkit.allep               Allplan 2026 plugin package (zip) for the Plugin Manager
    dist/TerrainToolkit_manual_install.zip  same content + install script, extract and run install.bat
"""
from __future__ import annotations

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
FOLDERS = ["Library", "PythonPartsScripts", "PythonPartsActionbar"]
FILES = ["install-config.yml", "requirements.in"]


def iter_files():
    for folder in FOLDERS:
        for base, dirs, files in os.walk(os.path.join(ROOT, folder)):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(base, f)
                yield full, os.path.relpath(full, ROOT)
    for f in FILES:
        yield os.path.join(ROOT, f), f


def main() -> None:
    os.makedirs(DIST, exist_ok=True)
    allep = os.path.join(DIST, "TerrainToolkit.allep")
    with zipfile.ZipFile(allep, "w", zipfile.ZIP_DEFLATED) as z:
        for full, rel in iter_files():
            z.write(full, rel.replace(os.sep, "/"))
    manual = os.path.join(DIST, "TerrainToolkit_manual_install.zip")
    with zipfile.ZipFile(manual, "w", zipfile.ZIP_DEFLATED) as z:
        for full, rel in iter_files():
            z.write(full, "TerrainToolkit/" + rel.replace(os.sep, "/"))
        for extra in ("install.bat", "install.ps1", "README.md"):
            z.write(os.path.join(ROOT, extra), "TerrainToolkit/" + extra)
        for f in sorted(os.listdir(os.path.join(ROOT, "samples"))):
            z.write(os.path.join(ROOT, "samples", f), "TerrainToolkit/samples/" + f)
    for p in (allep, manual):
        print(f"{p}  ({os.path.getsize(p) / 1024:.0f} kB)")


if __name__ == "__main__":
    main()
