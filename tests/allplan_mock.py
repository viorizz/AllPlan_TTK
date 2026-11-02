"""Minimal stand-ins for the Allplan Python API so that the PythonParts can be smoke tested
outside Allplan. Only the calls used by the toolkit are emulated; unknown attributes raise
AttributeError exactly like a real API mismatch would."""
from __future__ import annotations

import sys
import types
import xml.etree.ElementTree as ET

CREATED = []        # lists passed to CreateElements
MESSAGES = []       # texts passed to ShowMessageBox


def reset():
    CREATED.clear()
    MESSAGES.clear()


# --------------------------------------------------------------------------- geometry
geo = types.ModuleType("NemAll_Python_Geometry")


class Point2D:
    def __init__(self, x=0.0, y=0.0):
        self.X, self.Y = float(x), float(y)


class Point3D:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        if isinstance(x, Point3D):
            x, y, z = x.X, x.Y, x.Z
        self.X, self.Y, self.Z = float(x), float(y), float(z)


class _PointList:
    def __init__(self, pts=None):
        self.Points = list(pts or [])

    def __iadd__(self, p):
        self.Points.append(p)
        return self

    def Count(self):
        return len(self.Points)


class Polyline3D(_PointList):
    def __init__(self, pts=None):
        super().__init__(pts)
        assert all(isinstance(p, Point3D) for p in self.Points)


class Polyline2D(_PointList):
    pass


class Polygon2D(_PointList):
    pass


class Polygon3D(_PointList):
    pass


class Line3D:
    def __init__(self, a, b):
        assert isinstance(a, Point3D) and isinstance(b, Point3D)
        self.StartPoint, self.EndPoint = a, b


class Line2D:
    def __init__(self, a, b):
        self.StartPoint, self.EndPoint = a, b


class GeometryEdge:
    def __init__(self, a, b):
        self.Start, self.End = int(a), int(b)


class OrientedEdge:
    def __init__(self, idx, positive):
        self.EdgeIndex, self.Positive = int(idx), bool(positive)


class _Face:
    def __init__(self, n):
        self.n = n
        self.edges = []

    def AppendEdge(self, e, positive=None):
        if positive is not None:
            e = OrientedEdge(e, positive)
        self.edges.append(e)


class _PolyType:
    names = {"tVolume": 1, "tFaces": 2, "tEdges": 3}


class Polyhedron3D:
    def __init__(self):
        self.vertices, self.edges, self.faces, self.type = [], [], [], None

    def SetType(self, t):
        self.type = t

    def AppendEdge(self, e):
        assert isinstance(e, GeometryEdge)
        self.edges.append(e)

    def CreateFace(self, n):
        f = _Face(n)
        self.faces.append(f)
        return f

    def IsValid(self):
        nv = len(self.vertices)
        for f in self.faces:
            if len(f.edges) != f.n:
                return False
            loop = []
            for oe in f.edges:
                e = self.edges[oe.EdgeIndex]
                a, b = (e.Start, e.End) if oe.Positive else (e.End, e.Start)
                loop.append((a, b))
            for i in range(len(loop)):
                if loop[i][1] != loop[(i + 1) % len(loop)][0]:
                    return False
        return all(0 <= e.Start < nv and 0 <= e.End < nv for e in self.edges)

    def GetVertices(self):
        return list(self.vertices)

    def GetFacesCount(self):
        return len(self.faces)

    def GetEdgesCount(self):
        return len(self.edges)

    def GetEdge(self, i):
        return self.edges[i]

    def GetFace(self, i):
        return self.faces[i]


def _face_count(self):
    return len(self.edges)


_Face.GetEdgeCount = _face_count
_Face.GetEdge = lambda self, j: self.edges[j]


class Polyhedron3DBuilder:
    def __init__(self, poly):
        self.poly = poly

    def AppendVertex(self, p):
        assert isinstance(p, Point3D)
        self.poly.vertices.append(p)

    def Complete(self):
        return True


class Angle:
    def __init__(self, rad=0.0):
        self.Rad = rad

    @staticmethod
    def FromDeg(d):
        import math
        return Angle(math.radians(d))


class Matrix3D:
    pass


for _n, _o in dict(Point2D=Point2D, Point3D=Point3D, Polyline3D=Polyline3D, Polyline2D=Polyline2D,
                   Polygon2D=Polygon2D, Polygon3D=Polygon3D, Line3D=Line3D, Line2D=Line2D,
                   GeometryEdge=GeometryEdge, OrientedEdge=OrientedEdge, Polyhedron3D=Polyhedron3D,
                   Polyhedron3DBuilder=Polyhedron3DBuilder, PolyhedronType=_PolyType, Angle=Angle,
                   Matrix3D=Matrix3D).items():
    setattr(geo, _n, _o)

# --------------------------------------------------------------------------- elements
base = types.ModuleType("NemAll_Python_BaseElements")


class CommonProperties:
    def __init__(self):
        self.Pen = 1
        self.Stroke = 1
        self.Color = 1
        self.Layer = 0
        self.ColorByLayer = False
        self.PenByLayer = False
        self.StrokeByLayer = False
        self.DrawOrder = 0
        self.HelpConstruction = False

    def GetGlobalProperties(self):
        return None


def CreateElements(doc, matrix, elements, modify, asso):
    assert isinstance(matrix, Matrix3D)
    elements = list(elements)
    for e in elements:
        assert isinstance(e, (ModelElement3D, ModelElement2D, TextElement, FillingElement)), type(e)
    CREATED.append(elements)
    return elements


def GetIdByColor(argb):
    assert isinstance(argb, ARGB)
    return 1 + (argb.r * 7 + argb.g * 3 + argb.b) % 255


base.CommonProperties = CommonProperties
base.CreateElements = CreateElements
base.GetIdByColor = GetIdByColor
base.GetElement = lambda adapter: None

basis = types.ModuleType("NemAll_Python_BasisElements")


class ARGB:
    def __init__(self, r, g, b, a=0):
        self.r, self.g, self.b, self.a = r, g, b, a


class ModelElement3D:
    def __init__(self, cp, geo_obj):
        assert isinstance(cp, CommonProperties), type(cp)
        assert isinstance(geo_obj, (Polyhedron3D, Polyline3D, Line3D, Point3D)), type(geo_obj)
        if isinstance(geo_obj, Polyhedron3D):
            assert geo_obj.IsValid(), "invalid polyhedron"
        self.cp, self.geo = cp, geo_obj


class ModelElement2D:
    def __init__(self, cp, geo_obj):
        assert isinstance(cp, CommonProperties)
        assert isinstance(geo_obj, (Polyline2D, Polygon2D, Line2D)), type(geo_obj)
        self.cp, self.geo = cp, geo_obj


class TextProperties:
    __slots__ = ("Height", "Width", "Alignment", "TextAngle", "Font")


class _TextAlignment:
    names = {f"e{h}{v}": i for i, (h, v) in enumerate(
        [(h, v) for h in ("Left", "Middle", "Right") for v in ("Bottom", "Middle", "Top")])}


class TextElement:
    def __init__(self, cp, tp, text, pnt):
        assert isinstance(tp, TextProperties) and isinstance(pnt, Point2D) and isinstance(text, str)
        self.cp, self.tp, self.text, self.pnt = cp, tp, text, pnt


class FillingProperties:
    __slots__ = ("FirstColor", "SecondColor", "UseGradientFilling")


class FillingElement:
    def __init__(self, cp, fp, poly):
        assert isinstance(fp, FillingProperties) and isinstance(poly, Polygon2D)
        assert poly.Count() >= 4
        self.cp, self.fp, self.poly = cp, fp, poly


for _n, _o in dict(ARGB=ARGB, ModelElement3D=ModelElement3D, ModelElement2D=ModelElement2D,
                   TextProperties=TextProperties, TextAlignment=_TextAlignment, TextElement=TextElement,
                   FillingProperties=FillingProperties, FillingElement=FillingElement).items():
    setattr(basis, _n, _o)

util = types.ModuleType("NemAll_Python_Utility")
util.MB_OK = 0


def ShowMessageBox(text, flags):
    MESSAGES.append(text)
    return 1


util.ShowMessageBox = ShowMessageBox

settings_mod = types.ModuleType("NemAll_Python_AllplanSettings")

# --------------------------------------------------------------------------- input
ifw = types.ModuleType("NemAll_Python_IFW_Input")
PENDING_SELECTION = []


class PostElementSelection:
    def GetSelectedElements(self, doc):
        out = list(PENDING_SELECTION)
        PENDING_SELECTION.clear()
        return out


class ElementSelectFilterSetting:
    pass


class InputFunctionStarter:
    started = 0

    @staticmethod
    def StartElementSelect(text, setting, post, mark):
        assert isinstance(post, PostElementSelection)
        InputFunctionStarter.started += 1

    @staticmethod
    def RemoveFunction():
        return None


class HighlightService:
    @staticmethod
    def CancelAllHighlightedElements(doc_id):
        return None

    @staticmethod
    def HighlightElements(lst):
        return None


class CoordinateInput:
    def GetInputViewDocument(self):
        return "doc"

    def GetInputViewDocumentID(self):
        return 1

    def InitFirstElementInput(self, prompt):
        return None


for _n, _o in dict(PostElementSelection=PostElementSelection, ElementSelectFilterSetting=ElementSelectFilterSetting,
                   InputFunctionStarter=InputFunctionStarter, HighlightService=HighlightService,
                   InputStringConvert=lambda s: s, CoordinateInput=CoordinateInput).items():
    setattr(ifw, _n, _o)

adapter = types.ModuleType("NemAll_Python_IFW_ElementAdapter")
adapter.BaseElementAdapterList = lambda lst: list(lst)


class MockElement:
    """Stands in for a BaseElementAdapter."""
    _n = 0

    def __init__(self, geometry):
        MockElement._n += 1
        self.uuid = f"uuid-{MockElement._n}"
        self.geometry = geometry

    def GetGeometry(self):
        return self.geometry

    def GetModelElementUUID(self):
        return self.uuid


# --------------------------------------------------------------------------- framework
base_interactor = types.ModuleType("BaseInteractor")


class BaseInteractor:
    pass


base_interactor.BaseInteractor = BaseInteractor

palette_mod = types.ModuleType("BuildingElementPaletteService")


class BuildingElementPaletteService:
    def __init__(self, build_ele_list, composite, script_name, control_props, pyp_file_name):
        self.build_ele = build_ele_list[0]
        self.shown = False

    def show_palette(self, name):
        self.shown = True

    def update_palette(self, page, rebuild):
        return None

    def modify_element_property(self, page, name, value):
        getattr(self.build_ele, name).value = value

    def close_palette(self):
        self.shown = False


palette_mod.BuildingElementPaletteService = BuildingElementPaletteService

cer = types.ModuleType("CreateElementResult")


class CreateElementResult:
    def __init__(self, *a, **k):
        pass


cer.CreateElementResult = CreateElementResult


class Prop:
    def __init__(self, value):
        self.value = value


class BuildElement:
    """build_ele created from the defaults of a .pyp file."""

    def __init__(self, pyp_path):
        self.script_name = pyp_path
        self.pyp_file_name = pyp_path
        root = ET.parse(pyp_path).getroot()
        for p in root.iter("Parameter"):
            name = p.findtext("Name")
            vtype = p.findtext("ValueType")
            if vtype in ("Expander", "Row", "Button", "RadioButton", "Separator"):
                continue
            raw = p.findtext("Value")
            if vtype == "Double":
                v = float(raw)
            elif vtype == "Integer":
                v = int(raw)
            elif vtype == "CheckBox":
                v = raw in ("True", "1")
            elif vtype == "RadioButtonGroup":
                v = int(raw)
            elif vtype == "CommonProperties":
                v = CommonProperties()
            else:
                v = raw or ""
            setattr(self, name, Prop(v))


def install():
    for name, mod in {"NemAll_Python_Geometry": geo, "NemAll_Python_BaseElements": base,
                      "NemAll_Python_BasisElements": basis, "NemAll_Python_Utility": util,
                      "NemAll_Python_AllplanSettings": settings_mod, "NemAll_Python_IFW_Input": ifw,
                      "NemAll_Python_IFW_ElementAdapter": adapter, "BaseInteractor": base_interactor,
                      "BuildingElementPaletteService": palette_mod, "CreateElementResult": cer}.items():
        sys.modules[name] = mod
