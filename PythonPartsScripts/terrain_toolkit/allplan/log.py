"""Logging and error reporting for the Allplan side.

Every message goes to
    * the Allplan Trace window (print), and
    * a log file:  %USERPROFILE%\\Documents\\AllplanTerrainToolkit\\terrain_toolkit.log
Errors additionally open a message box that tells where the log file is.

The module does not need Allplan to import (useful for tests).
"""
from __future__ import annotations

import datetime
import functools
import os
import platform
import sys
import tempfile
import time
import traceback
from typing import Any, Callable, Optional

from .. import __version__

_LOG_DIR: Optional[str] = None
_VERBOSE = False


def log_dir() -> str:
    global _LOG_DIR
    if _LOG_DIR is None:
        candidates = []
        home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        if home:
            candidates.append(os.path.join(home, "Documents", "AllplanTerrainToolkit"))
        candidates.append(os.path.join(tempfile.gettempdir(), "AllplanTerrainToolkit"))
        for c in candidates:
            try:
                os.makedirs(c, exist_ok=True)
                test = os.path.join(c, ".write_test")
                with open(test, "w", encoding="utf-8") as fh:
                    fh.write("ok")
                os.remove(test)
                _LOG_DIR = c
                break
            except OSError:
                continue
        if _LOG_DIR is None:
            _LOG_DIR = tempfile.gettempdir()
    return _LOG_DIR


def log_file() -> str:
    return os.path.join(log_dir(), "terrain_toolkit.log")


def set_verbose(flag: bool) -> None:
    global _VERBOSE
    _VERBOSE = bool(flag)


def _write(line: str) -> None:
    path = log_file()
    try:
        if os.path.exists(path) and os.path.getsize(path) > 5 * 1024 * 1024:
            old = path + ".1"
            if os.path.exists(old):
                os.remove(old)
            os.rename(path, old)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def log(msg: str, level: str = "INFO") -> None:
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp} [{level}] {msg}"
    _write(line)
    if level != "DEBUG" or _VERBOSE:
        try:
            print(f"[TerrainToolkit] {msg}")
        except Exception:  # pragma: no cover - print never fails in practice
            pass


def debug(msg: str) -> None:
    if _VERBOSE:
        log(msg, "DEBUG")
    else:
        _write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [DEBUG] {msg}")


def warn(msg: str) -> None:
    log(msg, "WARNING")


def section(title: str) -> None:
    _write("")
    log("=" * 20 + f" {title} (Terrain Toolkit {__version__}) " + "=" * 20)


def log_exception(context: str) -> str:
    tb = traceback.format_exc()
    log(f"ERROR in {context}:\n{tb}", "ERROR")
    return tb


def show_message(text: str, error: bool = False) -> None:
    """Message box in Allplan, or print when Allplan is not available."""
    try:
        import NemAll_Python_Utility as AllplanUtil  # type: ignore
        AllplanUtil.ShowMessageBox(text, AllplanUtil.MB_OK)
    except Exception:
        print(("ERROR: " if error else "") + text)


def user_error_text(exc: BaseException, context: str) -> str:
    from ..core.tin import TerrainError
    if isinstance(exc, TerrainError):
        head = f"{context}:\n\n{exc}"
    else:
        head = (f"{context} failed with an unexpected error:\n\n"
                f"{type(exc).__name__}: {exc}")
    return (f"{head}\n\nDetails were written to the Trace window and to:\n{log_file()}\n\n"
            "Please send this log file when reporting the problem.")


def guarded(context: str, default: Any = None, show: bool = True) -> Callable:
    """Decorator: log and display any exception instead of letting Allplan swallow it."""
    def deco(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - we want to report everything
                log_exception(context)
                if show:
                    show_message(user_error_text(exc, context), error=True)
                return default
        return wrapper
    return deco


class Timer:
    def __init__(self, label: str):
        self.label = label
        self.t0 = 0.0

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *exc):
        log(f"{self.label}: {time.time() - self.t0:.2f} s")
        return False


def environment_report() -> str:
    lines = [
        f"Terrain Toolkit version : {__version__}",
        f"Python                  : {sys.version.split()[0]} ({sys.executable})",
        f"Platform                : {platform.platform()}",
        f"Log file                : {log_file()}",
    ]
    try:
        import NemAll_Python_AllplanSettings as AllplanSettings  # type: ignore
        try:
            lines.append(f"Allplan version         : {AllplanSettings.AllplanVersion.Version()}")
        except Exception:
            pass
        for name in ("GetUsrPath", "GetStdPath", "GetEtcPath", "GetPrgPath"):
            try:
                lines.append(f"{name:<24}: {getattr(AllplanSettings.AllplanPaths, name)()}")
            except Exception:
                pass
    except Exception:
        lines.append("Allplan modules         : not available (running outside Allplan)")
    return "\n".join(lines)
