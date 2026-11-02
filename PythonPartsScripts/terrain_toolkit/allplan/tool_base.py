"""Generic interactor used by every Terrain Toolkit PythonPart.

Workflow in Allplan:
    1. the palette opens and an element selection starts immediately
    2. the radio buttons "Select ..." choose what the next selection is used for
       (terrain, breaklines, boundary, alignment, ...). Selections accumulate.
    3. the "Create" button runs the tool and creates plain Allplan elements
       at their real (absolute) coordinates.
    4. ESC closes the tool.
Any exception is logged (Trace + log file) and shown in a message box.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import NemAll_Python_BaseElements as AllplanBaseElements  # type: ignore
import NemAll_Python_Geometry as AllplanGeo  # type: ignore
import NemAll_Python_IFW_ElementAdapter as AllplanEleAdapter  # type: ignore
import NemAll_Python_IFW_Input as AllplanIFW  # type: ignore
from BaseInteractor import BaseInteractor  # type: ignore
from BuildingElementPaletteService import BuildingElementPaletteService  # type: ignore

from ..core import io_formats
from ..core.tin import TIN, TerrainError, build_tin
from . import geo, log, settings

EVT_RUN = 1001
EVT_CLEAR = 1002
EVT_CLEAR_ALL = 1003
EVT_OPEN_LOG = 1098
EVT_ENV = 1099

UNIT_FACTORS = {"m": 1.0, "mm": 0.001, "cm": 0.01, "dm": 0.1, "km": 1000.0, "ft": 0.3048, "us-ft": 1200.0 / 3937.0}


@dataclass
class ToolOutput:
    elements: List[Any] = field(default_factory=list)
    summary: str = ""
    show_message: bool = False
    report_lines: List[str] = field(default_factory=list)


class TerrainTool(BaseInteractor):
    """Base class: subclasses set TITLE, ROLES and implement execute()."""

    TITLE = "Terrain tool"
    ROLES: Sequence[Tuple[str, str]] = ()
    ROLE_PARAM = "SelectRole"
    INFO_PARAM = "SelectionInfo"
    RESULT_PARAM = "ResultInfo"

    # ------------------------------------------------------------------ setup
    def __init__(self, coord_input, pyp_path, global_str_table_service, build_ele_list, build_ele_composite,
                 control_props_list, modify_uuid_list):
        self.coord_input = coord_input
        self.pyp_path = pyp_path
        self.build_ele_list = build_ele_list
        self.build_ele = build_ele_list[0]
        self.document = coord_input.GetInputViewDocument()
        self.selected: Dict[str, List[Any]] = {key: [] for key, _ in self.ROLES}
        self.post_sel = None
        self.palette_service = None
        log.set_verbose(bool(self.param("VerboseLog", False)))
        log.section(self.TITLE)
        log.debug(log.environment_report())
        self.palette_service = BuildingElementPaletteService(build_ele_list, build_ele_composite,
                                                             self.build_ele.script_name, control_props_list,
                                                             self.build_ele.pyp_file_name)
        self.prefill_shift()
        self.on_start()
        self.set_param(self.RESULT_PARAM, "-")
        self.update_info(refresh=False)
        self.palette_service.show_palette(self.build_ele.pyp_file_name)
        self.start_selection()

    def on_start(self) -> None:
        """Hook for subclasses (e.g. prefill parameters from settings)."""

    def prefill_shift(self) -> None:
        """Use the last coordinate shift (shared by all tools) when the palette has none."""
        if hasattr(self.build_ele, "ShiftX") and not any(self.shift()):
            self.set_param("ShiftX", float(settings.get("shift_x", 0.0)))
            self.set_param("ShiftY", float(settings.get("shift_y", 0.0)))
            self.set_param("ShiftZ", float(settings.get("shift_z", 0.0)))

    # -------------------------------------------------------------- parameters
    def param(self, name: str, default: Any = None) -> Any:
        prop = getattr(self.build_ele, name, None)
        if prop is None:
            return default
        try:
            return prop.value
        except Exception:  # noqa: BLE001
            return default

    def set_param(self, name: str, value: Any) -> None:
        prop = getattr(self.build_ele, name, None)
        if prop is not None:
            try:
                prop.value = value
            except Exception as exc:  # noqa: BLE001
                log.debug(f"set_param({name}) failed: {exc}")

    def fparam(self, name: str, default: float = 0.0) -> float:
        v = self.param(name, default)
        try:
            if isinstance(v, str):
                v = v.replace(",", ".")
            return float(v)
        except (TypeError, ValueError):
            return default

    def iparam(self, name: str, default: int = 0) -> int:
        try:
            return int(float(self.param(name, default)))
        except (TypeError, ValueError):
            return default

    def bparam(self, name: str, default: bool = False) -> bool:
        v = self.param(name, default)
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes")
        return bool(v)

    def log_params(self) -> None:
        values = {}
        for name in sorted(vars(self.build_ele).keys()):
            obj = getattr(self.build_ele, name, None)
            if obj is None or name.startswith("_") or not hasattr(obj, "value"):
                continue
            try:
                v = obj.value
            except Exception:  # noqa: BLE001
                continue
            if isinstance(v, (int, float, str, bool)):
                values[name] = v
        log.log(f"Parameters: {values}")

    def refresh_palette(self) -> None:
        if self.palette_service is not None:
            try:
                self.palette_service.update_palette(-1, True)
            except Exception as exc:  # noqa: BLE001
                log.debug(f"update_palette failed: {exc}")

    # --------------------------------------------------------------- selection
    def current_role(self) -> Optional[Tuple[str, str]]:
        if not self.ROLES:
            return None
        idx = self.iparam(self.ROLE_PARAM, 0)
        idx = max(0, min(idx, len(self.ROLES) - 1))
        return self.ROLES[idx]

    def selection_wanted(self) -> bool:
        return self.current_role() is not None

    def start_selection(self, remove_running: bool = False) -> None:
        if remove_running:
            try:
                AllplanIFW.InputFunctionStarter.RemoveFunction()
            except Exception:  # noqa: BLE001
                pass
        role = self.current_role() if self.selection_wanted() else None
        if role is None:
            self.post_sel = None
            try:
                self.coord_input.InitFirstElementInput(AllplanIFW.InputStringConvert(
                    f"{self.TITLE}: set the options and press 'Create'"))
            except Exception as exc:  # noqa: BLE001
                log.debug(f"InitFirstElementInput failed: {exc}")
            return
        self.post_sel = AllplanIFW.PostElementSelection()
        setting = AllplanIFW.ElementSelectFilterSetting()
        AllplanIFW.InputFunctionStarter.StartElementSelect(f"{self.TITLE} - select {role[1]}", setting,
                                                           self.post_sel, True)

    @staticmethod
    def _key(ele) -> str:
        for fn in ("GetModelElementUUID", "GetElementUUID"):
            try:
                return str(getattr(ele, fn)())
            except Exception:  # noqa: BLE001
                continue
        return str(id(ele))

    def add_selection(self, elements) -> None:
        role = self.current_role()
        if role is None:
            return
        lst = self.selected[role[0]]
        known = {self._key(e) for e in lst}
        added = 0
        for e in elements:
            k = self._key(e)
            if k not in known:
                lst.append(e)
                known.add(k)
                added += 1
        log.log(f"Selected {added} new element(s) as '{role[1]}' (total {len(lst)}).")
        self.highlight()
        self.update_info()

    def highlight(self) -> None:
        try:
            AllplanIFW.HighlightService.CancelAllHighlightedElements(self.coord_input.GetInputViewDocumentID())
            all_ele = [e for lst in self.selected.values() for e in lst]
            if all_ele:
                AllplanIFW.HighlightService.HighlightElements(AllplanEleAdapter.BaseElementAdapterList(all_ele))
        except Exception as exc:  # noqa: BLE001
            log.debug(f"Highlight failed: {exc}")

    def update_info(self, refresh: bool = True) -> None:
        if self.ROLES:
            parts = [f"{label.split(' (')[0][:1].upper()}{label.split(' (')[0][1:]}: {len(self.selected[key])}"
                     for key, label in self.ROLES]
            self.set_param(self.INFO_PARAM, " | ".join(parts))
        if refresh:
            self.refresh_palette()

    def clear_selection(self, all_roles: bool = False) -> None:
        if all_roles:
            for k in self.selected:
                self.selected[k] = []
        else:
            role = self.current_role()
            if role:
                self.selected[role[0]] = []
        self.highlight()
        self.update_info()

    def selection(self, key: str) -> List[Any]:
        return self.selected.get(key, [])

    def collect(self, key: str, read_faces: bool = True) -> geo.Collected:
        return geo.collect(self.selection(key), read_faces)

    # ----------------------------------------------------------- terrain input
    def unit_factor(self, name: str = "FileUnits") -> float:
        return UNIT_FACTORS.get(str(self.param(name, "m")).strip().lower(), 1.0)

    def shift(self) -> Tuple[float, float, float]:
        return (self.fparam("ShiftX", 0.0), self.fparam("ShiftY", 0.0), self.fparam("ShiftZ", 0.0))

    def load_file_terrain(self, path: str, build_options: Optional[dict] = None) -> Tuple[TIN, str]:
        """Load a terrain file and convert it to model metres relative to the Allplan origin."""
        path = (path or "").strip().strip('"')
        if not path:
            raise TerrainError("No terrain file selected.")
        f = self.unit_factor()
        sx, sy, sz = self.shift()
        layout = str(self.param("FileLayout", "auto"))
        with log.Timer(f"Reading {os.path.basename(path)}"):
            tin, pts, bls, desc = io_formats.load_terrain_file(path, layout=layout,
                                                              grid_step=self.iparam("GridStep", 1),
                                                              obj_y_up=self.bparam("ObjYUp", False), log=log.log)

        def tr(p):
            return (p[0] * f - sx, p[1] * f - sy, p[2] * f - sz)

        if tin is not None:
            tin = TIN([tr(p) for p in tin.points], tin.triangles, compact=False,
                      breaklines=[[tr(p) for p in bl] for bl in tin.breaklines])
        else:
            opts = build_options or {}
            tin = build_tin([tr(p) for p in pts], breaklines=[[tr(p) for p in bl] for bl in bls], log=log.log, **opts)
        settings.set_values(last_terrain_file=path, shift_x=sx, shift_y=sy, shift_z=sz)
        log.log(f"Terrain from file: {desc}; {len(tin.points)} vertices, {len(tin.triangles)} triangles.")
        self.check_coordinates(tin)
        return tin, desc

    def check_coordinates(self, tin: TIN) -> None:
        xmin, ymin, xmax, ymax = tin.bbox()
        if max(abs(xmin), abs(ymin), abs(xmax), abs(ymax)) > 1.0e5:
            log.warn("Terrain coordinates are far from the Allplan origin (> 100 km). If Allplan shows display "
                     "artefacts, enter a coordinate shift (e.g. the rounded first point) in the palette.")

    def terrain(self, role_key: str = "terrain", source_param: str = "TerrainSource",
                file_param: str = "TerrainFile") -> TIN:
        """Terrain from the selection (default) or from a file depending on the palette."""
        if self.iparam(source_param, 0) == 1:
            tin, _ = self.load_file_terrain(str(self.param(file_param, "")))
            return tin
        col = self.collect(role_key)
        return geo.collected_to_tin(col, log_fn=log.log)

    # ----------------------------------------------------------------- running
    def execute(self) -> Optional[ToolOutput]:  # pragma: no cover - overridden
        raise NotImplementedError

    def run(self) -> None:
        @log.guarded(self.TITLE)
        def _run():
            log.section(f"{self.TITLE}: Create")
            log.set_verbose(self.bparam("VerboseLog", False))
            self.log_params()
            t0 = time.time()
            out = self.execute()
            if out is None:
                return
            created = 0
            if out.elements:
                with log.Timer(f"Creating {len(out.elements)} Allplan element(s)"):
                    AllplanBaseElements.CreateElements(self.document, AllplanGeo.Matrix3D(), out.elements, [], None)
                created = len(out.elements)
            dt = time.time() - t0
            text = out.summary.strip()
            for line in out.report_lines:
                log.log(line)
            log.log(f"{text}\n{created} element(s) created in {dt:.1f} s.")
            self.set_param(self.RESULT_PARAM, (text.splitlines() or ["Done"])[0][:120])
            self.refresh_palette()
            if out.show_message or self.bparam("ShowResult", False):
                log.show_message(f"{self.TITLE}\n\n{text}\n\n{created} element(s) created.")
        _run()

    # ------------------------------------------------------- interactor events
    def modify_element_property(self, page, name, value):
        try:
            self.palette_service.modify_element_property(page, name, value)
            if name == "VerboseLog":
                log.set_verbose(bool(value))
            self.on_param_changed(name, value)
            if name in (self.ROLE_PARAM, "TerrainSource"):
                self.start_selection(remove_running=True)
            self.update_info(refresh=False)
            self.palette_service.update_palette(-1, False)
        except Exception:  # noqa: BLE001
            log.log_exception("modify_element_property")

    def on_param_changed(self, name: str, value: Any) -> None:
        """Hook for subclasses."""

    def on_control_event(self, event_id):
        try:
            if event_id == EVT_RUN:
                self.run()
            elif event_id == EVT_CLEAR:
                self.clear_selection(False)
            elif event_id == EVT_CLEAR_ALL:
                self.clear_selection(True)
            elif event_id == EVT_OPEN_LOG:
                path = log.log_dir()
                log.log(f"Log folder: {path}")
                if hasattr(os, "startfile"):
                    os.startfile(path)  # type: ignore[attr-defined]
            elif event_id == EVT_ENV:
                rep = log.environment_report()
                log.log(rep)
                log.show_message(rep)
            else:
                self.on_custom_event(event_id)
        except Exception:  # noqa: BLE001
            log.log_exception(f"on_control_event({event_id})")
        return True

    def on_custom_event(self, event_id: int) -> None:
        """Hook for subclasses."""

    def process_mouse_msg(self, mouse_msg, pnt, msg_info):
        try:
            if self.post_sel is None:
                return True
            elements = self.post_sel.GetSelectedElements(self.document)
            if len(elements):
                self.add_selection(list(elements))
            self.start_selection()
        except Exception:  # noqa: BLE001
            log.log_exception("process_mouse_msg")
        return True

    def on_cancel_function(self):
        try:
            AllplanIFW.InputFunctionStarter.RemoveFunction()
        except Exception:  # noqa: BLE001
            pass
        try:
            AllplanIFW.HighlightService.CancelAllHighlightedElements(self.coord_input.GetInputViewDocumentID())
        except Exception:  # noqa: BLE001
            pass
        try:
            if self.palette_service is not None:
                self.palette_service.close_palette()
        except Exception:  # noqa: BLE001
            pass
        log.log(f"{self.TITLE} closed.")
        return True

    def on_preview_draw(self):
        return None

    def on_mouse_leave(self):
        return None

    def on_value_input_control_enter(self):
        return True

    def set_active_palette_page_index(self, active_page_index):
        return None

    def on_shortcut_control_input(self, value):
        return True

    def _super_call(self, name: str, *args):
        fn = getattr(super(), name, None)
        if fn is None:
            return None
        try:
            return fn(*args)
        except Exception as exc:  # noqa: BLE001
            log.debug(f"BaseInteractor.{name} not usable: {exc}")
            return None

    def execute_save_favorite(self, file_name):
        return self._super_call("execute_save_favorite", file_name)

    def execute_load_favorite(self, file_name):
        return self._super_call("execute_load_favorite", file_name)

    def reset_param_values(self, build_ele_list):
        return self._super_call("reset_param_values", build_ele_list)

    def update_after_favorite_read(self):
        return self._super_call("update_after_favorite_read")


# ---------------------------------------------------------------------------
# entry point helpers for the scripts referenced by the .pyp files
# ---------------------------------------------------------------------------
def make_entry_points(tool_cls):
    def check_allplan_version(build_ele, version):
        log.debug(f"Allplan version reported: {version}")
        return True

    def create_preview(build_ele, doc):
        try:
            from CreateElementResult import CreateElementResult  # type: ignore
        except Exception:  # noqa: BLE001
            return ([], [])
        try:
            from Utils import LibraryBitmapPreview  # type: ignore
            png = os.path.join(str(build_ele.pyp_file_path), os.path.splitext(os.path.basename(
                str(build_ele.pyp_file_name)))[0] + ".png")
            if os.path.exists(png):
                return CreateElementResult(LibraryBitmapPreview.create_library_bitmap_preview(png))
        except Exception as exc:  # noqa: BLE001
            log.debug(f"library preview not available: {exc}")
        return CreateElementResult()

    def create_element(build_ele, doc):
        try:
            from CreateElementResult import CreateElementResult  # type: ignore
            return CreateElementResult()
        except Exception:  # noqa: BLE001
            return ([], [])

    def create_interactor(coord_input, pyp_path, global_str_table_service, build_ele_list,
                          build_ele_composite, control_props_list, modify_uuid_list):
        try:
            return tool_cls(coord_input, pyp_path, global_str_table_service, build_ele_list,
                            build_ele_composite, control_props_list, modify_uuid_list)
        except Exception as exc:
            log.log_exception(f"starting {tool_cls.TITLE}")
            log.show_message(log.user_error_text(exc, f"Starting {tool_cls.TITLE}"), error=True)
            raise

    return check_allplan_version, create_preview, create_element, create_interactor
