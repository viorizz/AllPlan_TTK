"""Generate the PythonPart palette files (.pyp) and the thin entry scripts for every tool.

Run:  python tools/build_pyp.py
Single source of truth for the palettes: edit this file, not the generated .pyp files.
"""
from __future__ import annotations

import os
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(ROOT, "Library", "Terrain Toolkit")
SCRIPT_DIR = os.path.join(ROOT, "PythonPartsScripts", "terrain_toolkit")
PACKAGE = "terrain_toolkit"

TERRAIN_FILTER = ("Terrain files (*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts)|"
                  "*.xml;*.landxml;*.xyz;*.csv;*.txt;*.asc;*.obj;*.pts|All files (*.*)|*.*|")
CSV_FILTER = "CSV files (*.csv)|*.csv|All files (*.*)|*.*|"


# ---------------------------------------------------------------------------
# tiny DSL
# ---------------------------------------------------------------------------
def P(name, text, value, vtype, **extra):
    return {"Name": name, "Text": text, "Value": value, "ValueType": vtype, **extra}


def dbl(name, text, value, **kw):
    return P(name, text, value, "Double", **kw)


def integer(name, text, value, **kw):
    return P(name, text, value, "Integer", **kw)


def chk(name, text, value=True, **kw):
    return P(name, text, "True" if value else "False", "CheckBox", **kw)


def string(name, text, value="", **kw):
    return P(name, text, value, "String", **kw)


def info(name, text, value="", **kw):
    return P(name, text, value, "Text", **kw)


def combo(name, text, value, values, **kw):
    return P(name, text, value, "StringComboBox", ValueList="|".join(values), **kw)


def props(name, text, **kw):
    return {"Name": name, "Text": text, "Value": None, "ValueType": "CommonProperties", **kw}


def radio(name, text, value, options, **kw):
    children = [{"Name": f"{name}_{i}", "Text": label, "Value": str(v), "ValueType": "RadioButton"}
                for i, (label, v) in enumerate(options)]
    return {"Name": name, "Text": text, "Value": str(value), "ValueType": "RadioButtonGroup", "children": children, **kw}


def expander(name, text, children, **kw):
    return {"Name": name, "Text": text, "ValueType": "Expander", "children": children, **kw}


def row(name, text, children, **kw):
    return {"Name": name, "Text": text, "ValueType": "Row", "children": children, **kw}


def button(name, row_text, text, event_id, **kw):
    return row(f"{name}Row", row_text, [{"Name": name, "Text": text, "EventId": str(event_id), "ValueType": "Button"}], **kw)


def open_file(name, text, filt=TERRAIN_FILTER, ext="xml", **kw):
    return P(name, text, "", "String", ValueDialog="OpenFileDialog", FileFilter=filt, FileExtension=ext, **kw)


def save_file(name, text, filt=CSV_FILTER, ext="csv", **kw):
    return P(name, text, "", "String", ValueDialog="SaveFileDialog", FileFilter=filt, FileExtension=ext, **kw)


def sep(name):
    return {"Name": name, "ValueType": "Separator"}


# ---------------------------------------------------------------------------
# shared blocks
# ---------------------------------------------------------------------------
def selection_block(roles, note=""):
    items = [radio("SelectRole", "Next selection is", 0, [(label, i) for i, label in enumerate(roles)])]
    items.append(info("SelectionInfo", "Selected", "nothing yet"))
    items.append(row("ClearRow", "Selection", [
        {"Name": "ClearButton", "Text": "Clear current", "EventId": "1002", "ValueType": "Button"},
        {"Name": "ClearAllButton", "Text": "Clear all", "EventId": "1003", "ValueType": "Button"}]))
    if note:
        items.insert(0, info("SelectionNote", note, ""))
    return expander("SelectionExp", "1. Selection in the model", items)


def file_options(prefix="", visible=None, with_shift=True):
    vis = {"Visible": visible} if visible else {}
    items = [
        combo("FileUnits", "File units", "m", ["m", "mm", "cm", "dm", "km", "ft", "us-ft"], **vis),
        combo("FileLayout", "Point file columns", "auto",
              ["auto", "XYZ", "PXYZ", "PXYZD", "PYXZ", "YXZ", "PNEZ", "PNEZD", "PENZ", "PENZD", "NEZ", "ENZ"], **vis),
        integer("GridStep", "ASC grid: use every n-th cell", 1, MinValue="1", MaxValue="100", **vis),
        chk("ObjYUp", "OBJ file is Y-up", False, **vis),
    ]
    if with_shift:
        items += [
            info("ShiftInfo", "Coordinate shift = real-world coordinates of the Allplan origin (m)", "", **vis),
            row("ShiftRow", "Shift X / Y (m)", [dbl("ShiftX", "X", 0.0), dbl("ShiftY", "Y", 0.0)], **vis),
            dbl("ShiftZ", "Shift Z (m)", 0.0, **vis),
        ]
    return items


def source_block(title="2. Terrain source", src="TerrainSource", fil="TerrainFile", label="Terrain", shift=True):
    items = [radio(src, f"{label} from", 0, [("Selection in model", 0), ("File (LandXML, XYZ/CSV, ASC, OBJ)", 1)]),
             open_file(fil, f"{label} file", Visible=f"{src} == 1")]
    items += file_options(visible=f"{src} == 1", with_shift=shift)
    return expander(f"{src}Exp", title, items)


def output_view_block(default_mode=2):
    return [radio("OutputMode", "Output", default_mode, [("3D coloured mesh", 0), ("2D colour fillings", 1), ("Both", 2)]),
            dbl("LiftMesh", "Lift 3D map above terrain (m)", 0.02, Visible="OutputMode != 1"),
            chk("Legend", "Legend", True),
            dbl("DrawingScale", "Drawing scale 1 :", 500.0, MinValue="1"),
            dbl("TextHeight", "Text height (mm)", 2.5, MinValue="0.1"),
            integer("MaxFaces", "Max. faces per mesh element", 30000, MinValue="1000"),
            props("BaseProp", "Format")]


def run_block():
    return expander("RunExp", "Create", [
        button("RunButton", "Run the tool", "Create", 1001),
        info("ResultInfo", "Last result", "-"),
        chk("ShowResult", "Show result message", False),
    ])


def diag_block():
    return expander("DiagExp", "Diagnostics", [
        chk("VerboseLog", "Verbose log (Trace window)", False),
        row("DiagRow", "Log", [
            {"Name": "OpenLogButton", "Text": "Open log folder", "EventId": "1098", "ValueType": "Button"},
            {"Name": "EnvButton", "Text": "Environment", "EventId": "1099", "ValueType": "Button"}]),
    ])


# ---------------------------------------------------------------------------
# tool definitions
# ---------------------------------------------------------------------------
TOOLS = []


def tool(script, title, module, cls, pages):
    TOOLS.append({"script": script, "title": title, "module": module, "cls": cls, "pages": pages})


tool("TerrainMesh", "Terrain Mesh (TIN)", "mesh", "TerrainMeshTool", [("Terrain mesh", [
    selection_block(["Terrain points / meshes", "Breaklines (3D lines)", "Outer boundary (closed)", "Holes (closed)"]),
    source_block("2. Points from file (optional)", label="Points"),
    expander("CleanExp", "3. Triangulation & cleaning", [
        dbl("MaxEdge", "Max. outer edge length (m, 0 = convex hull)", 0.0, MinValue="0"),
        dbl("DedupeTol", "Merge points closer than (m)", 0.001, MinValue="0"),
        dbl("ThinCell", "Grid thinning cell (m, 0 = off)", 0.0, MinValue="0"),
        chk("RemoveSpikes", "Remove spikes / outliers", False),
        dbl("SpikeThreshold", "Spike threshold (m)", 1.0, Visible="RemoveSpikes == True"),
        chk("Simplify", "Simplify (keep vertical tolerance)", False),
        dbl("SimplifyTol", "Vertical tolerance (m)", 0.05, Visible="Simplify == True"),
    ]),
    expander("OutExp", "4. Output", [
        chk("CreateMesh", "Terrain mesh (polyhedron)", True),
        props("MeshProp", "Mesh format", Visible="CreateMesh == True"),
        integer("MaxFaces", "Max. faces per mesh element", 30000, MinValue="1000"),
        chk("CreateOutline", "Outline (3D polyline)", False),
        props("OutlineProp", "Outline format", Visible="CreateOutline == True"),
        chk("CreateBreaklines", "Enforced breaklines (3D)", False),
        props("BreaklineProp", "Breakline format", Visible="CreateBreaklines == True"),
        chk("CreatePoints", "Points as 3D crosses", False),
        dbl("PointSize", "Cross size (m)", 0.25, Visible="CreatePoints == True"),
        props("PointProp", "Point format", Visible="CreatePoints == True"),
        chk("SaveLandXML", "Save a LandXML copy (terrain library)", True),
        string("TerrainName", "Terrain name", "Terrain", Visible="SaveLandXML == True"),
    ]),
    run_block(), diag_block()])])

tool("TerrainContours", "Terrain Contours", "contours_tool", "ContoursTool", [("Contours", [
    selection_block(["Terrain mesh / points"]),
    source_block(),
    expander("ContourExp", "3. Contours", [
        dbl("Interval", "Interval (m)", 0.5, MinValue="0.001"),
        integer("MajorEvery", "Major contour every n-th line (0 = none)", 5, MinValue="0"),
        dbl("BaseElevation", "Base elevation (m)", 0.0),
        chk("LimitRange", "Limit elevation range", False),
        row("RangeRow", "From / to (m)", [dbl("MinElevation", "min", 0.0), dbl("MaxElevation", "max", 1000.0)],
            Visible="LimitRange == True"),
        integer("Smooth", "Smoothing passes (0-3)", 0, MinValue="0", MaxValue="3"),
        dbl("SimplifyTol", "Simplify tolerance (m, 0 = off)", 0.0, MinValue="0"),
        dbl("MinLength", "Drop contours shorter than (m)", 0.0, MinValue="0"),
        radio("Dimension", "Create as", 0, [("3D polylines at elevation", 0), ("2D polylines", 1)]),
        props("MajorProp", "Major format"),
        props("MinorProp", "Minor format"),
    ]),
    expander("LabelExp", "4. Labels", [
        chk("LabelMajor", "Label major contours", True),
        chk("LabelMinor", "Label minor contours", False),
        dbl("LabelSpacing", "Label spacing (m)", 50.0, MinValue="1"),
        dbl("TextHeight", "Text height (mm)", 2.0, MinValue="0.1"),
        integer("Decimals", "Decimals", 1, MinValue="0", MaxValue="4"),
        props("LabelProp", "Label format"),
    ]),
    run_block(), diag_block()])])

tool("TerrainAnalysis", "Terrain Analysis (slope, aspect, elevation)", "analysis_tool", "AnalysisTool", [("Analysis", [
    selection_block(["Terrain mesh / points"]),
    source_block(),
    expander("AnaExp", "3. Analysis", [
        radio("AnalysisType", "Map", 0, [("Slope (%)", 0), ("Slope (degrees)", 1), ("Aspect / exposure", 2),
                                         ("Elevation bands", 3)]),
        string("SlopeBreaksPct", "Class limits (%)", "0;2;5;10;15;25;50", Visible="AnalysisType == 0"),
        string("SlopeBreaksDeg", "Class limits (deg)", "0;5;10;15;20;30;45", Visible="AnalysisType == 1"),
        radio("AspectSectors", "Sectors", 1, [("4", 0), ("8", 1), ("16", 2)], Visible="AnalysisType == 2"),
        dbl("FlatSlope", "Flat below (%)", 1.0, Visible="AnalysisType == 2"),
        string("ElevationBreaks", "Band limits (m, empty = automatic)", "", Visible="AnalysisType == 3"),
        integer("ClassCount", "Automatic: about n bands", 8, MinValue="2", MaxValue="30", Visible="AnalysisType == 3"),
        integer("Decimals", "Decimals", 2, MinValue="0", MaxValue="4", Visible="AnalysisType == 3"),
        combo("ColorRamp", "Colours", "auto", ["auto", "slope", "terrain", "spectral", "cutfill", "water", "aspect"]),
        chk("ReverseColors", "Reverse colours", False),
    ]),
    expander("ViewExp", "4. Output", output_view_block() + [save_file("ReportFile", "Area table (CSV, optional)")]),
    run_block(), diag_block()])])

tool("TerrainCutFill", "Terrain Cut & Fill (volumes)", "cutfill_tool", "CutFillTool", [("Cut & fill", [
    selection_block(["Existing terrain", "Design surface", "Boundary (optional, closed)"]),
    source_block("2a. Existing terrain source", label="Existing terrain"),
    expander("CompareExp", "2b. Compare with", [
        radio("CompareMode", "Compare with", 0, [("Design surface", 0), ("Reference elevation", 1)]),
        dbl("ReferenceElevation", "Reference elevation (m)", 0.0, Visible="CompareMode == 1"),
        radio("DesignSource", "Design surface from", 0, [("Selection in model", 0), ("File", 1)],
              Visible="CompareMode == 0"),
        open_file("DesignFile", "Design file", Visible="CompareMode == 0 and DesignSource == 1"),
        dbl("SwellFactor", "Swell factor applied to cut", 1.0, MinValue="0.1"),
    ]),
    expander("MapExp", "3. Map & lines", [
        chk("HeatMap", "Cut/fill depth map", True),
        string("DepthBreaks", "Depth class limits (m)", "-2;-1;-0.5;-0.1;0.1;0.5;1;2", Visible="HeatMap == True"),
        chk("MapOnDesign", "Draw map at design level", True, Visible="HeatMap == True"),
        chk("Isopachs", "Isopach lines (equal depth)", False),
        dbl("IsopachInterval", "Isopach interval (m)", 0.5, Visible="Isopachs == True"),
        props("IsopachProp", "Isopach format", Visible="Isopachs == True"),
        props("ZeroLineProp", "Zero line (cut/fill limit) format", Visible="Isopachs == True"),
        chk("ResultTexts", "Write volumes as texts in the model", True),
    ]),
    expander("ViewExp", "4. Output", output_view_block(1) + [save_file("ReportFile", "Volume report (CSV, optional)")]),
    expander("RunExp", "Create", [button("RunButton", "Run the tool", "Create", 1001),
                                  info("ResultInfo", "Last result", "-"),
                                  chk("ShowResult", "Show result message", True)]),
    diag_block()])])

tool("TerrainProfile", "Terrain Profile & Sections", "profile_tool", "ProfileTool", [("Profile", [
    selection_block(["Terrain (ground)", "Second surface (optional)", "Alignment (polyline)"]),
    source_block(),
    expander("DesignExp", "2b. Second surface from file (optional)", [
        radio("DesignSource", "Second surface from", 0, [("Selection in model", 0), ("File", 1)]),
        open_file("DesignFile", "Second surface file", Visible="DesignSource == 1"),
        string("GroundName", "Name of ground line", "Ground"),
        string("DesignName", "Name of second line", "Design"),
    ]),
    expander("ProfExp", "3. Drawing", [
        radio("ProfileMode", "Create", 0, [("Long section", 0), ("Cross sections", 1), ("Both", 2)]),
        chk("Reverse", "Reverse alignment direction", False),
        dbl("StationInterval", "Station interval (m)", 20.0, MinValue="0.1"),
        dbl("VExaggeration", "Vertical exaggeration", 10.0, MinValue="0.1"),
        dbl("ZInterval", "Elevation grid interval (m)", 1.0, MinValue="0.01"),
        chk("Grid", "Grid", True),
        chk("Table", "Station / elevation table", True),
        string("Title", "Title", "Long section"),
        dbl("SectionInterval", "Cross section interval (m)", 20.0, Visible="ProfileMode != 0"),
        row("WidthRow", "Width left / right (m)", [dbl("LeftWidth", "L", 15.0), dbl("RightWidth", "R", 15.0)],
            Visible="ProfileMode != 0"),
        integer("SectionColumns", "Sections per row", 4, MinValue="1", Visible="ProfileMode != 0"),
        chk("SectionLinesInPlan", "Section lines in plan", True, Visible="ProfileMode != 0"),
        props("SectionLineProp", "Section line format", Visible="ProfileMode != 0"),
        dbl("DrawingScale", "Drawing scale 1 :", 500.0, MinValue="1"),
        dbl("TextHeight", "Text height (mm)", 2.5, MinValue="0.1"),
        integer("Decimals", "Decimals", 2, MinValue="0", MaxValue="4"),
        chk("AutoPlace", "Place drawing right of the terrain", True),
        row("PlaceRow", "Drawing origin X / Y (m)", [dbl("PlaceX", "X", 0.0), dbl("PlaceY", "Y", 0.0)],
            Visible="AutoPlace == False"),
        props("GroundProp", "Ground line format"),
        props("DesignProp", "Second line format"),
        props("GridProp", "Grid format"),
        props("FrameProp", "Frame format"),
        props("TextProp", "Text format"),
    ]),
    expander("PlanExp", "4. In plan", [
        chk("Drape3D", "Alignment draped on terrain (3D)", True),
        props("DrapeProp", "Draped line format", Visible="Drape3D == True"),
        chk("StationLabels", "Station labels along the alignment", False),
        save_file("ReportFile", "Profile points (CSV, optional)"),
    ]),
    run_block(), diag_block()])])

tool("TerrainDrainage", "Terrain Drainage (water flow)", "drainage_tool", "DrainageTool", [("Drainage", [
    selection_block(["Terrain mesh / points", "Flow start points / lines (optional)"]),
    source_block(),
    expander("ArrowExp", "3. Flow direction", [
        chk("Arrows", "Flow arrows", True),
        dbl("ArrowSpacing", "Arrow grid spacing (m, 0 = per triangle)", 5.0, Visible="Arrows == True"),
        dbl("ArrowLength", "Arrow length (m, 0 = auto)", 0.0, Visible="Arrows == True"),
        dbl("MinSlope", "Ignore slopes below (%)", 0.5, Visible="Arrows == True"),
        chk("ScaleArrows", "Scale arrows by slope", False, Visible="Arrows == True"),
        props("ArrowProp", "Arrow format", Visible="Arrows == True"),
        chk("FlowPaths", "Flow paths (steepest descent)", False),
        dbl("SeedSpacing", "Start grid spacing if no start points (m, 0 = auto)", 0.0, Visible="FlowPaths == True"),
        dbl("MinPathLength", "Drop paths shorter than (m)", 0.0, Visible="FlowPaths == True"),
        props("FlowPathProp", "Flow path format", Visible="FlowPaths == True"),
    ]),
    expander("PondExp", "4. Low points & ponding", [
        chk("Sinks", "Mark local low points", True),
        chk("SinkLabels", "Label low point elevations", True, Visible="Sinks == True"),
        dbl("SinkSize", "Marker size (m, 0 = auto)", 0.0, Visible="Sinks == True"),
        props("SinkProp", "Low point format", Visible="Sinks == True"),
        chk("Ponding", "Ponding depth map (depressions)", True),
        dbl("MinDepth", "Minimum ponding depth (m)", 0.02, Visible="Ponding == True"),
        string("PondingBreaks", "Depth class limits (m)", "0.02;0.1;0.25;0.5;1", Visible="Ponding == True"),
    ] + output_view_block()),
    run_block(), diag_block()])])

tool("TerrainPlatform", "Terrain Platform (pad grading)", "platform_tool", "PlatformTool", [("Platform", [
    selection_block(["Existing terrain", "Platform outline (closed)"]),
    source_block(),
    expander("PadExp", "3. Platform", [
        radio("ElevationMode", "Pad elevation", 0, [("Fixed elevation", 0), ("Balance cut = fill", 1),
                                                    ("From 3D outline (best-fit plane)", 2)]),
        dbl("Elevation", "Elevation (m)", 0.0, Visible="ElevationMode == 0"),
        dbl("SwellFactor", "Balance: fill = cut x factor", 1.0, Visible="ElevationMode == 1"),
        dbl("CutRatio", "Cut slope H:V (e.g. 1.5 = 3/2)", 1.5, MinValue="0.01"),
        dbl("FillRatio", "Fill slope H:V (e.g. 2 = 2/1)", 2.0, MinValue="0.01"),
        dbl("MaxReach", "Max. slope width (m)", 50.0, MinValue="0.1"),
        dbl("GridCell", "Computation grid (m, 0 = auto)", 0.0, MinValue="0"),
    ]),
    expander("POutExp", "4. Output", [
        chk("PadMesh", "Pad surface", True),
        chk("Outline3D", "Pad outline (3D)", True),
        props("PadProp", "Pad format"),
        chk("SlopeMesh", "Slope surfaces", True),
        props("CutSlopeProp", "Cut slope format", Visible="SlopeMesh == True"),
        props("FillSlopeProp", "Fill slope format", Visible="SlopeMesh == True"),
        chk("DaylightLine", "Daylight line (slope toe / crest)", True),
        props("DaylightProp", "Daylight format", Visible="DaylightLine == True"),
        chk("DesignMesh", "Complete design surface (terrain + platform)", False),
        props("DesignProp", "Design surface format", Visible="DesignMesh == True"),
        chk("SaveDesign", "Save design surface as LandXML", True),
        string("DesignName", "Design name", "Platform_design", Visible="SaveDesign == True"),
        chk("ResultTexts", "Pad elevation text", True),
        dbl("TextHeight", "Text height (mm)", 2.5),
        integer("MaxFaces", "Max. faces per mesh element", 30000, MinValue="1000"),
    ]),
    expander("RunExp", "Create", [button("RunButton", "Run the tool", "Create", 1001),
                                  info("ResultInfo", "Last result", "-"),
                                  chk("ShowResult", "Show result message", True)]),
    diag_block()])])

tool("TerrainExchange", "Terrain Import/Export", "exchange_tool", "ExchangeTool", [("Export", [
    selection_block(["Terrain mesh / points"]),
    source_block("2. Terrain source (a file here = format conversion)", shift=False),
    expander("ExportExp", "3. Export", [
        radio("ExportFormat", "Format", 0, [("LandXML", 0), ("OBJ", 1), ("XYZ", 2), ("CSV", 3), ("ESRI ASCII grid", 4)]),
        save_file("ExportFile", "Export to", "All files (*.*)|*.*|", "xml"),
        string("SurfaceName", "Surface name (LandXML)", "Terrain", Visible="ExportFormat == 0"),
        dbl("GridCell", "Grid cell size (m)", 1.0, Visible="ExportFormat == 4"),
        combo("ExportUnits", "Output units", "m", ["m", "mm", "cm", "ft", "us-ft"]),
        integer("Decimals", "Decimals", 3, MinValue="0", MaxValue="8"),
        chk("ApplyShift", "Add the coordinate shift (real-world coordinates)", True),
        row("ExShiftRow", "Shift X / Y (m)", [dbl("ShiftX", "X", 0.0), dbl("ShiftY", "Y", 0.0)],
            Visible="ApplyShift == True"),
        dbl("ShiftZ", "Shift Z (m)", 0.0, Visible="ApplyShift == True"),
    ]),
    expander("RunExp", "Create", [button("RunButton", "Export", "Export", 1001), info("ResultInfo", "Last result", "-")]),
    diag_block()])])

tool("TerrainDiagnostics", "Terrain Toolkit Diagnostics", "diagnostics_tool", "DiagnosticsTool", [("Diagnostics", [
    expander("DiagInfoExp", "What this does", [
        info("DiagInfo1", "1. 'Run self-test' checks the Allplan API and draws a small test terrain", ""),
        info("DiagInfo2", "2. Select elements, then 'Inspect' writes their API details to the log", ""),
        info("DiagInfo3", "3. Send the log file (button 'Open log folder') to the developer", ""),
    ]),
    selection_block(["Elements to inspect"]),
    expander("TestExp", "Self-test", [
        chk("CreateTestGeometry", "Create test geometry", True),
        row("TestRow", "Test origin X / Y (m)", [dbl("TestX", "X", 0.0), dbl("TestY", "Y", 0.0)]),
        dbl("TestZ", "Test origin Z (m)", 0.0),
        button("RunButton", "Run self-test", "Run self-test", 1001),
        button("InspectButton", "Inspect selected elements", "Inspect", 2001),
        info("ResultInfo", "Last result", "-"),
    ]),
    diag_block()])])


# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------
TAG_ORDER = ["Name", "Text", "Value", "ValueType", "ValueList", "ValueDialog", "FileFilter", "FileExtension",
             "EventId", "MinValue", "MaxValue", "Visible", "Enable"]


def param_xml(p, ind):
    sp = "  " * ind
    lines = [f"{sp}<Parameter>"]
    keys = [k for k in TAG_ORDER if k in p] + [k for k in p if k not in TAG_ORDER and k != "children"]
    for k in keys:
        v = p[k]
        if k == "Value" and v is None:
            lines.append(f"{sp}  <Value/>")
            continue
        if k == "Text" and v == "":
            lines.append(f"{sp}  <Text/>")
            continue
        lines.append(f"{sp}  <{k}>{escape(str(v))}</{k}>")
    if "children" in p:
        lines.append(f"{sp}  <Parameters>")
        for c in p["children"]:
            lines.extend(param_xml(c, ind + 2))
        lines.append(f"{sp}  </Parameters>")
    lines.append(f"{sp}</Parameter>")
    return lines


def pyp_xml(t):
    out = ["<?xml version='1.0' encoding='UTF-8'?>",
           '<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">',
           "  <Script>",
           f"    <Name>{PACKAGE}\\{t['script']}.py</Name>",
           f"    <Title>{escape(t['title'])}</Title>",
           "    <Version>1.0</Version>",
           "    <Interactor>True</Interactor>",
           "    <ReadLastInput>True</ReadLastInput>",
           "  </Script>"]
    for i, (text, params) in enumerate(t["pages"]):
        out += ["  <Page>", f"    <Name>Page{i + 1}</Name>", f"    <Text>{escape(text)}</Text>", "    <Parameters>"]
        for p in params:
            out.extend(param_xml(p, 3))
        out += ["    </Parameters>", "  </Page>"]
    out.append("</Element>")
    return "\n".join(out) + "\n"


ENTRY = '''"""Terrain Toolkit - {title} (entry script referenced by {script}.pyp). Generated by tools/build_pyp.py."""
import os as _os
import sys as _sys

_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.append(_ROOT)

try:
    from terrain_toolkit.allplan.tool_base import make_entry_points as _make
    from terrain_toolkit.allplan.tools.{module} import {cls} as _Tool
except Exception:  # make import problems visible: Trace window + log file + message box
    import datetime as _dt
    import traceback as _tb
    _msg = _tb.format_exc()
    print("[TerrainToolkit] could not load {script}:\\n" + _msg)
    try:
        _dir = _os.path.join(_os.environ.get("USERPROFILE", _os.path.expanduser("~")), "Documents", "AllplanTerrainToolkit")
        _os.makedirs(_dir, exist_ok=True)
        with open(_os.path.join(_dir, "terrain_toolkit.log"), "a", encoding="utf-8") as _fh:
            _fh.write(f"{{_dt.datetime.now()}} [ERROR] loading {script}:\\n{{_msg}}\\n")
        import NemAll_Python_Utility as _U
        _U.ShowMessageBox("Terrain Toolkit could not be loaded ({script}).\\n\\n" + _msg[-1500:], _U.MB_OK)
    except Exception:
        pass
    raise

check_allplan_version, create_preview, create_element, create_interactor = _make(_Tool)
'''


def main():
    os.makedirs(LIB_DIR, exist_ok=True)
    for t in TOOLS:
        with open(os.path.join(LIB_DIR, f"{t['script']}.pyp"), "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write(pyp_xml(t))
        with open(os.path.join(SCRIPT_DIR, f"{t['script']}.py"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(ENTRY.format(**t))
        print("generated", t["script"])


if __name__ == "__main__":
    main()
