"""2-D chart breadth and annotations over the handle model (Epic #772, M13 G-E5: G04, G07).

errorbar area stairs stem pie barh bar(matrix, grouped/stacked) patch fill rectangle
line loglog semilogx semilogy hist imagesc image pcolor contour contourf quiver spy
polar polarplot rose compass plotyy colorbar colormap caxis clim zlabel box drawnow
annotation axes. Every chart is a node of the graphics tree (``h.Type`` and
``class(h)`` follow MATLAB) rendered best-effort through the matplotlib backend.

``KNOWN_PROPS`` lists documented properties that are accepted and stored without
further behaviour (``Units``, ``XTick``, ``XDir``, ``Interpreter``...): scripts that set
them run, and ``get`` returns the stored value or the documented default.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import numpy as np

from openmatlab.graphics import handle_model as hm
from openmatlab.graphics.handle_model import COLOR_ORDER, SPEC_COLORS, GObj, parse_linespec
from openmatlab.libs import graphics_builtins as gb
from openmatlab.numerics.ndarray_value import NDArrayValue

_err, _arr, _is_text, _is_cell, _cv, _h, _hcol = gb._err, gb._arr, gb._is_text, gb._is_cell, gb._cv, gb._h, gb._hcol

# type -> (short class, full class)
NEW_TYPES = {
    "errorbar": ("ErrorBar", "matlab.graphics.chart.primitive.ErrorBar"),
    "area": ("Area", "matlab.graphics.chart.primitive.Area"),
    "stair": ("Stair", "matlab.graphics.chart.primitive.Stair"),
    "stem": ("Stem", "matlab.graphics.chart.primitive.Stem"),
    "patch": ("Patch", "matlab.graphics.primitive.Patch"),
    "rectangle": ("Rectangle", "matlab.graphics.primitive.Rectangle"),
    "image": ("Image", "matlab.graphics.primitive.Image"),
    "surface": ("Surface", "matlab.graphics.primitive.Surface"),
    "contour": ("Contour", "matlab.graphics.chart.primitive.Contour"),
    "quiver": ("Quiver", "matlab.graphics.chart.primitive.Quiver"),
    "colorbar": ("ColorBar", "matlab.graphics.illustration.ColorBar"),
    "arrowshape": ("Arrow", "matlab.graphics.shape.Arrow"),
    "doubleendarrowshape": ("DoubleEndArrow", "matlab.graphics.shape.DoubleEndArrow"),
    "lineshape": ("Line", "matlab.graphics.shape.Line"),
    "textarrowshape": ("TextArrow", "matlab.graphics.shape.TextArrow"),
    "textboxshape": ("TextBox", "matlab.graphics.shape.TextBox"),
    "rectangleshape": ("Rectangle", "matlab.graphics.shape.Rectangle"),
    "ellipseshape": ("Ellipse", "matlab.graphics.shape.Ellipse"),
}
for _t, (_s, _f) in NEW_TYPES.items():
    hm.CLASS_NAMES.setdefault(_t, _s)
    gb.FULL_CLASS.setdefault(_t, _f)

_ANY = {"Visible": "on", "Tag": "", "UserData": None, "HandleVisibility": "on", "HitTest": "on",
        "Clipping": "on", "PickableParts": "visible", "Selected": "off", "BusyAction": "queue",
        "Interruptible": "on", "DisplayName": "", "Units": "data"}
_LINEISH = {"Color": [0.0, 0.447, 0.741], "LineStyle": "-", "LineWidth": 0.5, "Marker": "none",
            "MarkerSize": 6.0, "MarkerEdgeColor": "auto", "MarkerFaceColor": "none", "ZData": [],
            "XData": [], "YData": [], "AlignVertexCenters": "off", "LineJoin": "round"}
_FACEISH = {"FaceColor": [0.0, 0.447, 0.741], "EdgeColor": [0.0, 0.0, 0.0], "FaceAlpha": 1.0,
            "EdgeAlpha": 1.0, "LineStyle": "-", "LineWidth": 0.5, "Marker": "none", "MarkerSize": 6.0,
            "MarkerEdgeColor": "auto", "MarkerFaceColor": "none", "CData": [], "FaceVertexCData": [],
            "XData": [], "YData": [], "ZData": [], "Vertices": [], "Faces": [], "CDataMapping": "scaled",
            "FaceLighting": "flat", "BaseValue": 0.0, "ShowBaseLine": "on", "Horizontal": "off"}
_TEXT = {"Interpreter": "tex", "FontSize": 10.0, "FontWeight": "normal", "FontName": "Helvetica",
         "FontAngle": "normal", "HorizontalAlignment": "left", "VerticalAlignment": "middle",
         "Rotation": 0.0, "Position": [0.0, 0.0, 0.0], "Units": "data", "Color": [0.0, 0.0, 0.0],
         "BackgroundColor": "none", "EdgeColor": "none", "Margin": 3.0, "String": "", "Extent": [0, 0, 0, 0]}
_AXIS = {}
for _ax in "XYZ":
    _AXIS.update({f"{_ax}Tick": [], f"{_ax}TickLabel": [], f"{_ax}TickMode": "auto", f"{_ax}TickLabelMode": "auto",
                  f"{_ax}Dir": "normal", f"{_ax}Color": [0.15, 0.15, 0.15], f"{_ax}Scale": "linear",
                  f"{_ax}MinorTick": "off", f"{_ax}MinorGrid": "off", f"{_ax}TickLabelRotation": 0.0})
KNOWN_PROPS: Dict[str, Dict[str, Any]] = {
    "*": _ANY,
    "figure": {"Units": "pixels", "Position": [100.0, 100.0, 560.0, 420.0], "Colormap": None, "Renderer": "opengl",
               "PaperUnits": "inches", "PaperPosition": [0.25, 2.5, 8.0, 6.0], "PaperSize": [8.5, 11.0],
               "PaperPositionMode": "auto", "InvertHardcopy": "on", "WindowStyle": "normal", "MenuBar": "figure",
               "ToolBar": "auto", "Resize": "on", "Alphamap": [], "PaperOrientation": "portrait",
               "PaperType": "usletter", "Pointer": "arrow", "IntegerHandle": "on", "FileName": "",
               "CurrentPoint": [0.0, 0.0], "RendererMode": "auto", "Clipping": "on"},
    "root": {"ShowHiddenHandles": "off", "ScreenSize": [1.0, 1.0, 1920.0, 1080.0], "Units": "pixels",
             "ScreenPixelsPerInch": 96.0, "RecursionLimit": 500.0, "PointerLocation": [0.0, 0.0],
             "FixedWidthFontName": "Courier", "Format": "short", "FormatSpacing": "loose", "MonitorPositions": [1.0, 1.0, 1920.0, 1080.0], "Children": None},
    "axes": dict(_AXIS, **{"Units": "normalized", "Position": [0.13, 0.11, 0.775, 0.815],
                           "OuterPosition": [0.0, 0.0, 1.0, 1.0], "XAxisLocation": "bottom", "YAxisLocation": "left",
                           "ZLim": [-1.0, 1.0], "ZLimMode": "auto", "ZGrid": "off", "CLim": [0.0, 1.0],
                           "CLimMode": "auto", "Color": [1.0, 1.0, 1.0], "FontSize": 10.0, "FontName": "Helvetica",
                           "FontWeight": "normal", "LineWidth": 0.5, "TickDir": "in", "TickLength": [0.01, 0.025],
                           "Layer": "bottom", "GridLineStyle": "-", "MinorGridLineStyle": ":", "DataAspectRatio": [1, 1, 1],
                           "DataAspectRatioMode": "auto", "PlotBoxAspectRatio": [1, 1, 1], "View": [0.0, 90.0],
                           "ZLabel": None, "ColorOrder": COLOR_ORDER.tolist(), "LineStyleOrder": "-",
                           "Projection": "orthographic", "TitleFontSizeMultiplier": 1.1, "LabelFontSizeMultiplier": 1.1,
                           "XAxis": None, "YAxis": None, "TightInset": [0.05, 0.05, 0.01, 0.01], "SortMethod": "depth",
                           "ActivePositionProperty": "outerposition", "PositionConstraint": "outerposition",
                           "Colormap": None, "AmbientLightColor": [1, 1, 1], "Clipping": "on", "ClippingStyle": "3dbox",
                           "FontUnits": "points", "CameraPosition": [0, 0, 1], "CameraTarget": [0, 0, 0],
                           "CameraUpVector": [0, 1, 0], "CameraViewAngle": 6.6, "LineStyleOrderIndex": 1.0,
                           "ALim": [0.0, 1.0], "ALimMode": "auto"}),
    "line": _LINEISH,
    "errorbar": dict(_LINEISH, **{"YNegativeDelta": [], "YPositiveDelta": [], "XNegativeDelta": [],
                                  "XPositiveDelta": [], "LData": [], "UData": [], "CapSize": 6.0}),
    "stair": _LINEISH, "stem": dict(_LINEISH, BaseValue=0.0, ShowBaseLine="on"),
    "bar": dict(_FACEISH, BarLayout="grouped", BarWidth=0.8, Horizontal="off"),
    "area": _FACEISH, "patch": _FACEISH, "surface": dict(_FACEISH, EdgeColor=[0.0, 0.0, 0.0], MeshStyle="both"),
    "rectangle": dict(_FACEISH, FaceColor="none", Curvature=[0.0, 0.0], Position=[0.0, 0.0, 1.0, 1.0]),
    "image": {"CData": [], "XData": [], "YData": [], "CDataMapping": "direct", "AlphaData": 1.0,
              "AlphaDataMapping": "none", "Interpolation": "nearest"},
    "contour": dict(_FACEISH, LevelList=[], LevelStep=0.0, Fill="off", ShowText="off", LevelListMode="auto",
                    TextList=[], ZData=[]),
    "quiver": dict(_LINEISH, UData=[], VData=[], WData=[], AutoScale="on", AutoScaleFactor=0.9, MaxHeadSize=0.2,
                   ShowArrowHead="on"),
    "scatter": {"MarkerEdgeColor": "flat", "MarkerFaceColor": "none", "LineWidth": 0.5, "ZData": [],
                "MarkerEdgeAlpha": 1.0, "MarkerFaceAlpha": 1.0, "SizeData": 36.0},
    "histogram": {"FaceAlpha": 0.6, "EdgeColor": [0.0, 0.0, 0.0], "Orientation": "vertical",
                  "DisplayStyle": "bar", "BinMethod": "auto", "LineWidth": 0.5, "LineStyle": "-", "BinWidth": 1.0,
                  "BinLimits": [0.0, 1.0], "Normalization": "count"},
    "text": _TEXT,
    "legend": {"Interpreter": "tex", "FontSize": 9.0, "Orientation": "vertical", "Box": "on",
               "Color": [1.0, 1.0, 1.0], "EdgeColor": [0.15, 0.15, 0.15], "TextColor": [0.0, 0.0, 0.0],
               "Units": "normalized", "Position": [0.7, 0.8, 0.2, 0.1], "AutoUpdate": "on", "NumColumns": 1.0,
               "FontName": "Helvetica", "FontWeight": "normal", "LineWidth": 0.5, "Title": None,
               "ItemHitFcn": "", "TextColor_": None},
    "colorbar": {"Location": "eastoutside", "Limits": [0.0, 1.0], "Ticks": [], "TickLabels": [],
                 "Label": None, "Units": "normalized", "Position": [0.83, 0.11, 0.04, 0.815], "Direction": "normal",
                 "FontSize": 9.0, "Color": [0.15, 0.15, 0.15], "TickLabelInterpreter": "tex", "Box": "on",
                 "LineWidth": 0.5, "AxisLocation": "out", "TickDirection": "in", "XTick": [], "YTick": [],
                 "XTickLabel": [], "YTickLabel": [], "YAxisLocation": "right", "XAxisLocation": "bottom",
                 "TickLength": 0.01, "FontName": "Helvetica", "Visible": "on"},
}
for _t in ("arrowshape", "doubleendarrowshape", "lineshape", "textarrowshape", "textboxshape",
           "rectangleshape", "ellipseshape"):
    KNOWN_PROPS[_t] = dict(_TEXT, **{"X": [0.3, 0.4], "Y": [0.3, 0.4], "Units": "normalized",
                                     "Position": [0.3, 0.3, 0.1, 0.1], "LineStyle": "-", "LineWidth": 0.5,
                                     "HeadStyle": "vback2", "HeadLength": 10.0, "HeadWidth": 10.0,
                                     "FaceColor": "none", "FitBoxToText": "off", "Color": [0.0, 0.0, 0.0],
                                     "TextEdgeColor": "none", "TextBackgroundColor": "none", "TextColor": [0.0, 0.0, 0.0],
                                     "TextLineWidth": 0.5, "TextMargin": 2.0, "TextRotation": 0.0,
                                     "Head1Style": "vback2", "Head2Style": "vback2", "Head1Length": 10.0,
                                     "Head2Length": 10.0, "Head1Width": 10.0, "Head2Width": 10.0, "FaceAlpha": 1.0})


def known(o: GObj) -> Dict[str, Any]:
    d = dict(KNOWN_PROPS["*"])
    d.update(KNOWN_PROPS.get(o.type, {}))
    return d


# ------------------------------------------------------------- helpers
def _m(ev):
    return gb.model(ev)


def _axes(m, args):
    a, rest = gb._target_axes(m, args)
    return a or m.gca(), rest


def _vec(v, fn):
    return _arr(v, fn).astype(float).reshape(-1, order="F")


def _split(args):
    """Leading numeric args, then an optional LineSpec, then name-value pairs."""
    nums: List[Any] = []
    i = 0
    while i < len(args) and not _is_text(args[i]) and not _is_cell(args[i]):
        nums.append(args[i])
        i += 1
    spec = None
    if i < len(args) and _is_text(args[i]):
        ps = parse_linespec(args[i].text)
        if ps is not None and args[i].text and (len(args) - i) % 2 == 1:
            spec, i = ps, i + 1
    return nums, spec, list(args[i:])


def _apply(m, o, nv, fn):
    pairs = gb._name_values(nv, fn) if len(nv) % 2 == 0 else gb._name_values(nv[1:], fn)
    for k, v in pairs:
        gb._set_prop(m, o, k, v)


def _spec_props(spec, base_color):
    col, style, marker = base_color, "-", "none"
    if spec is not None:
        if spec[0]:
            col = [float(c) for c in SPEC_COLORS[spec[0]]]
        if spec[2]:
            marker = spec[2]
            style = spec[1] or "none"
        elif spec[1]:
            style = spec[1]
    return col, style, marker


def _finish(m, a, ids, nargout, col=False):
    m.autoscale(a)
    gb._render(m, a)
    if not nargout:
        return ()
    return (_hcol(ids) if (col or len(ids) != 1) else _h(ids[0]),)


def _new(m, a, typ, props, fresh=True):
    if fresh:
        m.prepare_axes_for_plot(a)
    base = {"DisplayName": "", "Tag": ""}
    base.update(props)
    return m.add_child(a, typ, base)


# ------------------------------------------------------------- line family
def _line(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    nums, spec, nv = _split(rest)
    ids = []
    if len(nums) >= 2:
        x, y = _arr(nums[0], "line").astype(float), _arr(nums[1], "line").astype(float)
        cols = gb._columns(x, y) if x.size and y.size else [(x.reshape(-1), y.reshape(-1))]
    else:
        cols = [(np.array([0.0, 1.0]), np.array([0.0, 1.0]))]
    z = _vec(nums[2], "line").tolist() if len(nums) >= 3 else []
    for xv, yv in cols:
        o = _new(m, a, "line", {"XData": xv.tolist(), "YData": yv.tolist(), "ZData": z,
                                "Color": m.next_color(a) if False else [0.0, 0.447, 0.741], "LineStyle": "-",
                                "LineWidth": 0.5, "Marker": "none", "MarkerSize": 6.0}, fresh=False)
        _apply(m, o, nv, "line")
        ids.append(o.id)
    return _finish(m, a, ids, nargout, col=len(ids) > 1)


def _logplot(xs, ys):
    def f(ev, args, nargout):
        m = _m(ev)
        out = gb.INTRINSICS["plot"](ev, args, 1)
        a = m.gca()
        a.props["XScale"], a.props["YScale"] = xs or a.props.get("XScale", "linear"), ys or a.props.get("YScale", "linear")
        gb._render(m, a)
        return out if nargout else ()
    return f


def _errorbar(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    nums, spec, nv = _split(rest)
    orient = None
    if nv and _is_text(nv[0]) and nv[0].text.lower() in ("horizontal", "vertical", "both"):
        orient = nv.pop(0).text.lower()
    if nums and len(nums) == 1:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    v = [_vec(x, "errorbar") for x in nums]
    if len(v) == 2:
        y, e = v
        x = np.arange(1, y.size + 1, dtype=float)
        neg = pos = e
    elif len(v) == 3:
        x, y, e = v
        neg = pos = e
    elif len(v) >= 4:
        x, y, neg, pos = v[:4]
    else:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if x.size != y.size:
        raise _err("X and Y must be the same length.", "MATLAB:errorbar:XYLengthMismatch")
    neg, pos = np.broadcast_to(neg, y.shape), np.broadcast_to(pos, y.shape)
    col, style, marker = _spec_props(spec, None)
    m.prepare_axes_for_plot(a)
    hor = orient == "horizontal"
    o = _new(m, a, "errorbar", {"XData": x.tolist(), "YData": y.tolist(), "Color": col or m.next_color(a),
                                 "LineStyle": style, "LineWidth": 0.5, "Marker": marker, "MarkerSize": 6.0,
                                 ("XNegativeDelta" if hor else "YNegativeDelta"): neg.tolist(),
                                 ("XPositiveDelta" if hor else "YPositiveDelta"): pos.tolist(),
                                 "LData": neg.tolist(), "UData": pos.tolist()}, fresh=False)
    _apply(m, o, nv, "errorbar")
    return _finish(m, a, [o.id], nargout)


def _xy_or_y(nums, fn):
    if len(nums) >= 2:
        x, y = _arr(nums[0], fn).astype(float), _arr(nums[1], fn).astype(float)
        return gb._columns(x, y)
    if not nums:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    return gb._columns(None, _arr(nums[0], fn).astype(float))


def _series(typ, fn):
    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = _axes(m, args)
        nums, spec, nv = _split(rest)
        extra = {}
        if typ in ("stem", "area") and len(nums) == 3:  # stem(x,y,'filled')/area(x,y,basevalue)
            extra["BaseValue"] = float(_vec(nums.pop(), fn)[0])
        if nv and _is_text(nv[0]) and nv[0].text.lower() == "filled":
            nv.pop(0)
            extra["MarkerFaceColor"] = "auto"
        cols = _xy_or_y(nums, fn)
        m.prepare_axes_for_plot(a)
        ids = []
        for xv, yv in cols:
            col, style, marker = _spec_props(spec, None)
            if typ == "stem" and marker == "none":
                marker = "o"
            c = col or m.next_color(a)
            props = {"XData": xv.tolist(), "YData": yv.tolist(), "LineStyle": style, "LineWidth": 0.5,
                     "Marker": marker, "MarkerSize": 6.0}
            if typ == "area":
                props.update({"FaceColor": c, "EdgeColor": [0.0, 0.0, 0.0], "BaseValue": 0.0})
            else:
                props["Color"] = c
            props.update(extra)
            o = _new(m, a, typ, props, fresh=False)
            _apply(m, o, nv, fn)
            ids.append(o.id)
        return _finish(m, a, ids, nargout, col=len(ids) > 1)
    return f


# ------------------------------------------------------------- bars / pies / hist
def _bars(horizontal):
    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = _axes(m, args)
        nums = []
        i = 0
        while i < len(rest) and not _is_text(rest[i]):
            nums.append(rest[i])
            i += 1
        tail = list(rest[i:])
        layout = "grouped"
        while tail and _is_text(tail[0]) and tail[0].text.lower() in ("grouped", "stacked", "hist", "histc", "overlaid"):
            layout = tail.pop(0).text.lower()
        spec = None
        if tail and _is_text(tail[0]) and len(tail) % 2 == 1:
            spec = parse_linespec(tail.pop(0).text)
        if not nums:
            raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
        width = 0.8
        if len(nums) == 3 or (len(nums) == 2 and _arr(nums[1], "bar").size == 1 and _arr(nums[0], "bar").size > 1):
            width = float(_vec(nums.pop(), "bar")[0])
        y = _arr(nums[-1], "bar").astype(float)
        if 1 in y.shape:
            y = y.reshape(-1, 1)
        x = _vec(nums[0], "bar") if len(nums) == 2 else np.arange(1, y.shape[0] + 1, dtype=float)
        if x.size != y.shape[0]:
            raise _err("X and Y must be the same length.", "MATLAB:bar:XYLengthMismatch")
        m.prepare_axes_for_plot(a)
        ids = []
        for j in range(y.shape[1]):
            c = [float(v) for v in SPEC_COLORS[spec[0]]] if spec and spec[0] else m.next_color(a)
            o = _new(m, a, "bar", {"XData": x.tolist(), "YData": y[:, j].tolist(), "BarWidth": width,
                                   "FaceColor": c, "BarLayout": "stacked" if layout == "stacked" else "grouped",
                                   "Horizontal": "on" if horizontal else "off", "_group": (j, y.shape[1]),
                                   "_stackbase": (y[:, :j].sum(axis=1).tolist() if layout == "stacked" else None)},
                     fresh=False)
            _apply(m, o, tail, "bar")
            ids.append(o.id)
        return _finish(m, a, ids, nargout, col=len(ids) > 1)
    return f


def _pie(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    if not rest:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    x = _vec(rest[0], "pie")
    if np.any(x < 0):
        raise _err("Values must be nonnegative.", "MATLAB:pie:NegativeData")
    labels = None
    for r in rest[1:]:
        if _is_cell(r):
            labels = gb._cellstrs(r)
    tot = x.sum()
    frac = x / tot if tot > 1 or tot == 0 else x
    m.prepare_axes_for_plot(a)
    ids = []
    t0 = np.pi / 2
    for k, fr in enumerate(frac):
        th = np.linspace(t0, t0 - 2 * np.pi * fr, max(int(abs(fr) * 100), 2) + 1)
        px, py = np.r_[0.0, np.cos(th)], np.r_[0.0, np.sin(th)]
        c = COLOR_ORDER[k % len(COLOR_ORDER)].tolist()
        p = _new(m, a, "patch", {"XData": px.tolist(), "YData": py.tolist(), "FaceColor": c,
                                 "EdgeColor": [0.0, 0.0, 0.0]}, fresh=False)
        mid = (t0 + th[-1]) / 2
        s = labels[k] if labels and k < len(labels) else ("%d%%" % round(fr * 100) if fr * 100 >= 1 or fr == 0 else "< 1%")
        t = GObj(m._new_id(), "text", a, {"String": s, "Position": [1.2 * np.cos(mid), 1.2 * np.sin(mid), 0.0],
                                           "FontSize": 10.0, "Color": [0.0, 0.0, 0.0], "HorizontalAlignment": "center"})
        m.objs[t.id] = t
        a.children.append(t)
        ids += [p.id, t.id]
        t0 = th[-1]
    a.props.update({"XLim": [-1.2, 1.2], "YLim": [-1.2, 1.2], "XLimMode": "manual", "YLimMode": "manual", "Visible": "off"})
    gb._render(m, a)
    return (gb.GraphicsHandle(np.array(ids, float).reshape(1, -1), m),) if nargout else ()


def _hist(ev, args, nargout):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    y = _arr(args[0], "hist").astype(float)
    cols = [y.reshape(-1)] if 1 in y.shape else [y[:, j] for j in range(y.shape[1])]
    data = np.concatenate(cols) if cols else np.array([])
    fin = data[np.isfinite(data)]
    lo, hi = (float(fin.min()), float(fin.max())) if fin.size else (0.0, 1.0)
    if lo == hi:
        lo, hi = lo - 0.5, hi + 0.5
    if len(args) > 1 and not _is_text(args[1]) and _arr(args[1], "hist").size > 1:
        centers = _vec(args[1], "hist")
        mids = (centers[1:] + centers[:-1]) / 2
        edges = np.r_[-np.inf, mids, np.inf]
    else:
        n = int(_vec(args[1], "hist")[0]) if len(args) > 1 and not _is_text(args[1]) else 10
        e = np.linspace(lo, hi, n + 1)
        centers = (e[1:] + e[:-1]) / 2
        edges = e.copy()
        edges[0], edges[-1] = -np.inf, np.inf
    counts = np.stack([np.histogram(c[np.isfinite(c)], bins=edges)[0] for c in cols], axis=1).astype(float)
    if nargout:
        if 1 in y.shape:
            counts = counts.reshape(1, -1)
        out = (NDArrayValue(counts),)
        if nargout > 1:
            out += (NDArrayValue(centers.reshape(1, -1)),)
        return out
    return _bars(False)(ev, [NDArrayValue(centers.reshape(-1, 1)), NDArrayValue(counts), NDArrayValue(np.array([[1.0]]))], 0)


# ------------------------------------------------------------- patches
def _patch_like(typ):
    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = _axes(m, args)
        ids = []
        if rest and _is_text(rest[0]):  # patch('XData', x, 'YData', y, ...) / patch('Faces',..., 'Vertices',...)
            o = _new(m, a, "patch", {"FaceColor": [0.0, 0.0, 0.0], "EdgeColor": [0.0, 0.0, 0.0]}, fresh=False)
            _apply(m, o, rest, typ)
            return _finish(m, a, [o.id], nargout)
        groups = []
        i = 0
        while i + 2 < len(rest) + 1 and i + 1 < len(rest) and not _is_text(rest[i]):
            x = _arr(rest[i], typ).astype(float)
            y = _arr(rest[i + 1], typ).astype(float)
            j = i + 2
            z = None
            if j < len(rest) and not _is_text(rest[j]) and j + 1 < len(rest) and not _is_text(rest[j + 1]) and typ == "patch":
                z, j = _arr(rest[j], typ).astype(float), j + 1
            c = None
            if j < len(rest):
                c, j = rest[j], j + 1
            groups.append((x, y, z, c))
            i = j
            if typ == "patch":
                break
        nv = list(rest[i:])
        if typ == "fill":
            m.prepare_axes_for_plot(a)
        for x, y, z, c in groups:
            if 1 in x.shape:
                x = x.reshape(-1, 1)
            if 1 in y.shape:
                y = y.reshape(-1, 1)
            for k in range(max(x.shape[1], y.shape[1])):
                xv, yv = x[:, min(k, x.shape[1] - 1)], y[:, min(k, y.shape[1] - 1)]
                fc: Any = [0.0, 0.0, 0.0]
                cdata: Any = []
                if c is not None and _is_text(c):
                    ps = parse_linespec(c.text)
                    fc = gb._color(c, typ) if ps is None or not ps[0] else [float(v) for v in SPEC_COLORS[ps[0]]]
                elif c is not None:
                    cv = _arr(c, typ).astype(float)
                    if cv.size == 3 and 1 in cv.shape and np.all((cv >= 0) & (cv <= 1)) and xv.size != 3:
                        fc = cv.reshape(-1).tolist()
                    else:
                        fc, cdata = "flat", cv.tolist()
                o = _new(m, a, "patch", {"XData": xv.tolist(), "YData": yv.tolist(),
                                         "ZData": z.reshape(-1).tolist() if z is not None else [],
                                         "FaceColor": fc, "CData": cdata, "EdgeColor": [0.0, 0.0, 0.0]}, fresh=False)
                _apply(m, o, nv, typ)
                ids.append(o.id)
        return _finish(m, a, ids, nargout, col=len(ids) > 1)
    return f


def _rectangle(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    o = _new(m, a, "rectangle", {"Position": [0.0, 0.0, 1.0, 1.0], "FaceColor": "none",
                                 "EdgeColor": [0.0, 0.0, 0.0], "Curvature": [0.0, 0.0]}, fresh=False)
    _apply(m, o, rest, "rectangle")
    return _finish(m, a, [o.id], nargout)


# ------------------------------------------------------------- images / fields
def _image_like(scaled):
    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = _axes(m, args)
        nums, _, nv = _split(rest)
        if nums and len(nums) in (2,) and _arr(nums[-1], "imagesc").size == 2 and not scaled:
            pass
        clim = None
        if scaled and len(nums) in (2, 4) and _arr(nums[-1], "imagesc").size == 2:
            clim = _vec(nums.pop(), "imagesc").tolist()
        if not nums:
            if nv:
                o = _new(m, a, "image", {"CData": []}, fresh=True)
                _apply(m, o, nv, "image")
                return _finish(m, a, [o.id], nargout)
            raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
        c = np.asarray(_arr(nums[-1], "image") if _arr(nums[-1], "image").ndim == 2 else np.asarray(nums[-1].backend_buffer()), float)
        if hasattr(nums[-1], "backend_buffer"):
            c = np.asarray(nums[-1].backend_buffer(), dtype=float)
            if c.ndim < 2:
                c = c.reshape(1, -1)
        r, k = c.shape[0], c.shape[1]
        xd = _vec(nums[0], "image")[[0, -1]].tolist() if len(nums) >= 3 else [1.0, float(k)]
        yd = _vec(nums[1], "image")[[0, -1]].tolist() if len(nums) >= 3 else [1.0, float(r)]
        o = _new(m, a, "image", {"CData": c.tolist(), "XData": xd, "YData": yd,
                                 "CDataMapping": "scaled" if scaled else "direct"})
        _apply(m, o, nv, "image")
        fin = c[np.isfinite(c)]
        if scaled:
            a.props["CLim"] = clim or ([float(fin.min()), float(fin.max())] if fin.size and fin.min() < fin.max() else [0.0, 1.0])
        a.props["YDir"] = "reverse"
        return _finish(m, a, [o.id], nargout)
    return f


def _grid_xyz(nums, fn):
    if len(nums) >= 3:
        x, y, z = (_arr(v, fn).astype(float) for v in nums[:3])
        rest = nums[3:]
    else:
        z = _arr(nums[0], fn).astype(float)
        x, y = np.arange(1, z.shape[1] + 1, dtype=float), np.arange(1, z.shape[0] + 1, dtype=float)
        rest = nums[1:]
    return x, y, z, rest


def _contour(filled):
    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = _axes(m, args)
        nums, spec, nv = _split(rest)
        if not nums:
            raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
        x, y, z, more = _grid_xyz(nums, "contour")
        fin = z[np.isfinite(z)]
        lo, hi = (float(fin.min()), float(fin.max())) if fin.size else (0.0, 1.0)
        if more:
            lv = _vec(more[0], "contour")
            levels = np.linspace(lo, hi, int(lv[0]) + 2)[1:-1] if lv.size == 1 else lv
        else:
            levels = np.linspace(lo, hi, 10)[1:-1] if hi > lo else np.array([lo])
        o = _new(m, a, "contour", {"XData": x.tolist(), "YData": y.tolist(), "ZData": z.tolist(),
                                   "LevelList": np.atleast_1d(levels).tolist(), "Fill": "on" if filled else "off",
                                   "LineColor": "flat" if not filled else [0.0, 0.0, 0.0], "LineStyle": "-"})
        _apply(m, o, nv, "contour")
        a.props["CLim"] = [lo, hi] if hi > lo else [lo, lo + 1]
        out = _finish(m, a, [o.id], nargout)
        if nargout:
            return (NDArrayValue(np.zeros((2, 0))),) + out if nargout >= 1 else out
        return out
    return f


def _pcolor(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    nums, _, nv = _split(rest)
    if not nums:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    x, y, z, _ = _grid_xyz(nums, "pcolor")
    o = _new(m, a, "surface", {"XData": x.tolist(), "YData": y.tolist(), "ZData": np.zeros_like(z).tolist(),
                               "CData": z.tolist(), "FaceColor": "flat", "EdgeColor": [0.0, 0.0, 0.0]})
    _apply(m, o, nv, "pcolor")
    fin = z[np.isfinite(z)]
    if fin.size and fin.min() < fin.max():
        a.props["CLim"] = [float(fin.min()), float(fin.max())]
    return _finish(m, a, [o.id], nargout)


def _quiver(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    nums, spec, nv = _split(rest)
    if len(nums) >= 4:
        x, y, u, v = (_arr(t, "quiver").astype(float) for t in nums[:4])
    elif len(nums) >= 2:
        u, v = (_arr(t, "quiver").astype(float) for t in nums[:2])
        x, y = np.meshgrid(np.arange(1, u.shape[1] + 1.0), np.arange(1, u.shape[0] + 1.0))
    else:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if x.shape != u.shape and x.size * y.size == u.size:
        x, y = np.meshgrid(x.reshape(-1), y.reshape(-1))
    col, style, marker = _spec_props(spec, None)
    o = _new(m, a, "quiver", {"XData": x.reshape(-1).tolist(), "YData": y.reshape(-1).tolist(),
                              "UData": u.reshape(-1).tolist(), "VData": v.reshape(-1).tolist(),
                              "Color": col or m.next_color(a), "LineStyle": style, "Marker": marker, "LineWidth": 0.5})
    _apply(m, o, nv, "quiver")
    return _finish(m, a, [o.id], nargout)


def _spy(ev, args, nargout):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    s = args[0]
    d = s.to_dense() if hasattr(s, "to_dense") else s
    z = np.asarray(_arr(d, "spy"))
    r, c = np.nonzero(z.T)
    m = _m(ev)
    a = m.gca()
    m.prepare_axes_for_plot(a)
    o = _new(m, a, "line", {"XData": (r + 1.0).tolist(), "YData": (c + 1.0).tolist(), "Color": [0.0, 0.447, 0.741],
                            "LineStyle": "none", "Marker": ".", "MarkerSize": 6.0, "LineWidth": 0.5}, fresh=False)
    a.props.update({"XLim": [0.0, z.shape[1] + 1.0], "YLim": [0.0, z.shape[0] + 1.0], "XLimMode": "manual",
                    "YLimMode": "manual", "YDir": "reverse"})
    gb._xlabel_set = None
    a.props["XLabel"].props["String"] = f"nz = {int(np.count_nonzero(z))}"
    return _finish(m, a, [o.id], nargout)


def _polar(rho_first=False):
    def f(ev, args, nargout):
        nums, spec, nv = _split(list(args))
        if not nums:
            raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
        if len(nums) == 1:
            r = _arr(nums[0], "polar").astype(float)
            th = np.arange(r.size, dtype=float).reshape(r.shape) * 2 * np.pi / max(r.size, 1)
        else:
            th, r = (_arr(v, "polar").astype(float) for v in nums[:2])
        th, r = np.broadcast_arrays(th, r)
        x, y = r * np.cos(th), r * np.sin(th)
        pargs = [NDArrayValue(x), NDArrayValue(y)] + ([_cv(args[len(nums)].text)] if spec is not None else []) + nv
        return gb.INTRINSICS["plot"](ev, pargs, nargout)
    return f


def _rose(ev, args, nargout):
    th = _vec(args[0], "rose") if args else np.array([])
    n = int(_vec(args[1], "rose")[0]) if len(args) > 1 and _arr(args[1], "rose").size == 1 else 20
    edges = np.linspace(0, 2 * np.pi, n + 1)
    cnt, _ = np.histogram(np.mod(th, 2 * np.pi), bins=edges)
    t = np.repeat(edges, 2)[1:-1]
    rr = np.repeat(cnt, 2).astype(float)
    xs = np.c_[np.zeros(n), np.zeros(n)].ravel()
    tt = np.stack([np.zeros(n), edges[:-1], edges[1:], np.zeros(n)], 1).ravel()
    rv = np.stack([np.zeros(n), cnt, cnt, np.zeros(n)], 1).ravel().astype(float)
    del t, rr, xs
    if nargout:
        return (NDArrayValue(tt.reshape(1, -1)), NDArrayValue(rv.reshape(1, -1)))[:nargout]
    return _polar()(ev, [NDArrayValue(tt.reshape(1, -1)), NDArrayValue(rv.reshape(1, -1))], 0)


def _compass(ev, args, nargout):
    nums, spec, nv = _split(list(args))
    if len(nums) >= 2:
        u, v = _vec(nums[0], "compass"), _vec(nums[1], "compass")
    else:
        b = np.asarray(nums[0].backend_buffer()).reshape(-1) if nums else np.array([])
        u, v = np.real(b).astype(float), np.imag(b).astype(float)
    xs = np.stack([np.zeros_like(u), u, np.full_like(u, np.nan)], 1).ravel()
    ys = np.stack([np.zeros_like(v), v, np.full_like(v, np.nan)], 1).ravel()
    return gb.INTRINSICS["plot"](ev, [NDArrayValue(xs.reshape(1, -1)), NDArrayValue(ys.reshape(1, -1))], nargout)


def _plotyy(ev, args, nargout):
    m = _m(ev)
    if len(args) < 4:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    f = m.gcf()
    a1 = m.gca()
    h1 = gb.INTRINSICS["plot"](ev, [gb._h(a1.id)] + list(args[:2]), 1)[0]
    a2 = m.new_axes(f, getattr(a1, "position", None))
    a2.props.update({"YAxisLocation": "right", "Color": "none"})
    h2 = gb.INTRINSICS["plot"](ev, [gb._h(a2.id)] + list(args[2:4]), 1)[0]
    f.current_axes = a1
    gb._render(m, a1)
    if not nargout:
        return ()
    return (gb.GraphicsHandle(np.array([[a1.id], [a2.id]]), m), h1, h2)[:nargout]


# ------------------------------------------------------------- colour / axes decorations
def _parula(n):
    """Clean-room parula approximation (blue -> teal -> yellow), not MATLAB's table."""
    k = np.array([[0.2081, 0.1663, 0.5292], [0.0592, 0.3599, 0.8683], [0.0780, 0.5041, 0.8384],
                  [0.0239, 0.6287, 0.6377], [0.3946, 0.7232, 0.4116], [0.8008, 0.7497, 0.2245],
                  [0.9932, 0.8384, 0.1720], [0.9763, 0.9831, 0.0538]])
    t = np.linspace(0, 1, n)
    s = np.linspace(0, 1, len(k))
    return np.stack([np.interp(t, s, k[:, j]) for j in range(3)], 1)


def _colormap(ev, args, nargout):
    m = _m(ev)
    f = m.gcf()
    rest = list(args)
    if rest and not _is_text(rest[0]) and hasattr(rest[0], "backend_buffer"):
        h = _arr(rest[0], "colormap").reshape(-1)
        if h.size == 1 and m.is_handle(h[0]) and len(rest) > 1:
            rest = rest[1:]
    if rest:
        v = rest[0]
        if _is_text(v):
            name, size = v.text.strip().lower(), 64
            call = re.fullmatch(r"(\w+)\s*\(\s*(\d+)\s*\)", name)  # the 'bone(16)' expression form
            if call:
                name, size = call.group(1), int(call.group(2))
            if name == "default":
                name = "parula"
            if name not in CMAPS:
                raise _err(f"colormap: unknown colormap '{v.text}'.", "MATLAB:colormap:InvalidName")
            cm = _cmap(name, size)
        else:
            cm = np.asarray(_arr(v, "colormap"), float)
            if cm.ndim != 2 or cm.shape[1] != 3 or np.any(cm < 0) or np.any(cm > 1):
                raise _err("Colormap must be an m-by-3 array of values in the range [0, 1].", "MATLAB:hg:ColorMapOutOfRange")
        f.props["Colormap"] = cm.tolist()
        gb._render(m, m.gca() if getattr(f, "current_axes", None) is None else f.current_axes)
        return ()
    cm = f.props.get("Colormap")
    return (NDArrayValue(np.asarray(cm, float) if cm is not None else _parula(64)),)


def _cmap(name, n):
    t = np.linspace(0, 1, n) if n > 1 else np.zeros(n)
    if name == "gray":
        return np.stack([t, t, t], 1)
    if name == "jet":
        f = lambda c: np.clip(np.minimum(4 * t - c + 1.5, -4 * t + c + 1.5), 0, 1)  # noqa: E731
        return np.stack([f(3.0), f(2.0), f(1.0)], 1) if n else np.zeros((0, 3))
    if name == "hot":
        return np.stack([np.clip(3 * t, 0, 1), np.clip(3 * t - 1, 0, 1), np.clip(3 * t - 2, 0, 1)], 1)
    if name == "cool":
        return np.stack([t, 1 - t, np.ones(n)], 1)
    if name == "spring":
        return np.stack([np.ones(n), t, 1 - t], 1)
    if name == "summer":
        return np.stack([t, 0.5 + t / 2, 0.4 * np.ones(n)], 1)
    if name == "autumn":
        return np.stack([np.ones(n), t, np.zeros(n)], 1)
    if name == "winter":
        return np.stack([np.zeros(n), t, 1 - t / 2], 1)
    if name == "bone":
        return (7 * np.stack([t, t, t], 1) + _cmap("hot", n)[:, ::-1]) / 8
    if name == "copper":
        return np.clip(np.stack([1.25 * t, 0.7812 * t, 0.4975 * t], 1), 0, 1)
    if name == "pink":
        return np.sqrt((2 * np.stack([t, t, t], 1) + _cmap("hot", n)) / 3)
    if name == "white":
        return np.ones((n, 3))
    if name == "hsv":
        h = np.linspace(0, 1, n, endpoint=False) if n else t
        i = np.floor(h * 6).astype(int) % 6
        f = h * 6 - np.floor(h * 6)
        q, u = 1 - f, f
        r = np.choose(i, [np.ones(n), q, np.zeros(n), np.zeros(n), u, np.ones(n)])
        g = np.choose(i, [u, np.ones(n), np.ones(n), q, np.zeros(n), np.zeros(n)])
        b = np.choose(i, [np.zeros(n), np.zeros(n), u, np.ones(n), np.ones(n), q])
        return np.stack([r, g, b], 1) if n else np.zeros((0, 3))
    if name == "lines":
        return COLOR_ORDER[np.arange(n) % len(COLOR_ORDER)]
    if name == "turbo":  # clean-room approximation
        k = np.array([[0.19, 0.07, 0.23], [0.27, 0.51, 0.97], [0.10, 0.85, 0.75], [0.64, 0.99, 0.24],
                      [0.98, 0.73, 0.21], [0.89, 0.27, 0.05], [0.48, 0.02, 0.01]])
        sp = np.linspace(0, 1, len(k))
        return np.stack([np.interp(t, sp, k[:, j]) for j in range(3)], 1)
    return _parula(n)


CMAPS = ("parula", "jet", "gray", "hot", "cool", "spring", "summer", "autumn", "winter", "bone", "copper",
         "pink", "white", "hsv", "lines", "turbo")


def _cmap_fn(name):
    def f(ev, args, nargout):
        n = int(_vec(args[0], name)[0]) if args else 64
        n = max(n, 0)
        return (NDArrayValue(np.asarray(_cmap(name, n), float).reshape(n, 3)),)
    return f


def _parula_fn(ev, args, nargout):
    n = int(_vec(args[0], "parula")[0]) if args else 64
    return (NDArrayValue(_parula(max(n, 0)).reshape(max(n, 0), 3)),)


def _clim(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    if not rest:
        return (NDArrayValue(np.array([a.props.get("CLim", [0.0, 1.0])], float)),)
    if _is_text(rest[0]):
        a.props["CLimMode"] = rest[0].text.lower()
    else:
        lim = _vec(rest[0], "caxis")
        if lim.size != 2 or not lim[0] < lim[1]:
            raise _err("Limits must be a 2-element vector of increasing numeric values.", "MATLAB:caxis:InvalidLimits")
        a.props["CLim"], a.props["CLimMode"] = lim.tolist(), "manual"
    gb._render(m, a)
    return ()


def _colorbar(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    if rest and _is_text(rest[0]) and rest[0].text.lower() in ("off", "hide", "delete"):
        for c in [c for c in a.parent.children if c.type == "colorbar" and getattr(c, "axes", None) is a]:
            m._delete(c, render=False)
        gb._render(m, a)
        return ()
    loc = "eastoutside"
    if rest and _is_text(rest[0]) and len(rest) % 2 == 1:
        loc = rest.pop(0).text
    f = a.parent
    o = GObj(m._new_id(), "colorbar", f, {"Location": loc, "Limits": list(a.props.get("CLim", [0.0, 1.0]))})
    o.axes = a
    lab = m._text(o)
    o.props["Label"] = lab
    o.props["Title"] = m._text(o)  # title(colorbar, ...) / get(hc, 'Title') (#771)
    m.objs[o.id] = o
    f.children.append(o)
    _apply(m, o, rest, "colorbar")
    gb._render(m, a)
    return (_h(o.id),) if nargout else ()


def _zlabel(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    t = a.props.get("ZLabel")
    if not isinstance(t, GObj):
        t = m._text(a)
        a.props["ZLabel"] = t
    if rest:
        s = rest[0]
        t.props["String"] = "\n".join(gb._cellstrs(s)) if _is_cell(s) else (s.text if _is_text(s) else "")
        _apply(m, t, list(rest[1:]), "zlabel")
    return (_h(t.id),) if nargout else ()


def _box(ev, args, nargout):
    m = _m(ev)
    a, rest = _axes(m, args)
    if not rest:
        a.props["Box"] = "off" if a.props.get("Box") == "on" else "on"
    else:
        w = rest[0].text.lower() if _is_text(rest[0]) else ""
        if w not in ("on", "off"):
            raise _err("box: option must be 'on' or 'off'.", "MATLAB:box:InvalidOption")
        a.props["Box"] = w
    gb._render(m, a)
    return ()


def _drawnow(ev, args, nargout):
    return ()


def _axes_fn(ev, args, nargout):
    m = _m(ev)
    if len(args) == 1 and not _is_text(args[0]):
        h = _arr(args[0], "axes").reshape(-1)
        if h.size == 1 and m.is_handle(h[0]) and m.get(h[0]).type == "figure":
            f = m.get(h[0])
            m.current_figure = f
            a = m.new_axes(f)
            a.position = None
            m.render(f)
            return (_h(a.id),) if nargout else ()
        if h.size == 1 and m.is_handle(h[0]) and m.get(h[0]).type == "axes":
            a = m.get(h[0])
            f = a.parent
            f.current_axes = a
            m.current_figure = f
            return (_h(a.id),) if nargout else ()
        raise _err("axes: argument must be an axes handle.", "MATLAB:hg:InvalidAxesHandle")
    rest = list(args)
    f = None
    if rest and not _is_text(rest[0]):
        h = _arr(rest[0], "axes").reshape(-1)
        if h.size == 1 and m.is_handle(h[0]) and m.get(h[0]).type == "figure":
            f = m.get(h[0])
            rest = rest[1:]
    nv = gb._name_values(rest, "axes")
    for k, v in nv:
        if k.lower() == "parent":
            f = gb._handles(m, v, "axes")[0]
    f = f or m.gcf()
    a = m.new_axes(f)
    a.position = None
    for k, v in nv:
        if k.lower() != "parent":
            gb._set_prop(m, a, k, v)
    m.render(f)
    return (_h(a.id),) if nargout else ()


_ANN = {"line": "lineshape", "arrow": "arrowshape", "doublearrow": "doubleendarrowshape",
        "textarrow": "textarrowshape", "textbox": "textboxshape", "rectangle": "rectangleshape",
        "ellipse": "ellipseshape"}


def _annotation(ev, args, nargout):
    m = _m(ev)
    rest = list(args)
    f = None
    if rest and not _is_text(rest[0]):
        f = gb._handles(m, rest.pop(0), "annotation")[0]
        f = m.figure_of(f)
    f = f or m.gcf()
    if not rest or not _is_text(rest[0]) or rest[0].text.lower() not in _ANN:
        raise _err("annotation: type must be one of line, arrow, doublearrow, textarrow, textbox, rectangle, ellipse.",
                   "MATLAB:annotation:InvalidType")
    kind = rest.pop(0).text.lower()
    props: Dict[str, Any] = {"Units": "normalized", "Color": [0.0, 0.0, 0.0], "String": ""}
    if rest and not _is_text(rest[0]):
        p = _vec(rest.pop(0), "annotation")
        if kind in ("line", "arrow", "doublearrow", "textarrow"):
            if not rest or _is_text(rest[0]):
                raise _err("annotation: line-type annotations need X and Y vectors.", "MATLAB:annotation:InvalidXY")
            props.update({"X": p.tolist(), "Y": _vec(rest.pop(0), "annotation").tolist()})
        else:
            if p.size != 4:
                raise _err("annotation: position must be a 4-element vector.", "MATLAB:annotation:InvalidPosition")
            props["Position"] = p.tolist()
    o = GObj(m._new_id(), _ANN[kind], f, props)
    m.objs[o.id] = o
    f.children.append(o)
    _apply(m, o, rest, "annotation")
    m.render(f)
    return (_h(o.id),) if nargout else ()


def _text_fn(ev, args, nargout):
    """text(x, y, str) / text(x, y, z, str) / text(..., Name, Value) / text('String', s, ...)."""
    m = _m(ev)
    a, rest = _axes(m, args)
    nums = []
    while rest and not _is_text(rest[0]) and not _is_cell(rest[0]) and len(nums) < 3:
        nums.append(rest.pop(0))
    if len(nums) == 1 or (nums and not rest):
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    s: Any = ""
    if nums:
        sv = rest.pop(0)
        s = "\n".join(gb._cellstrs(sv)) if _is_cell(sv) else ("\n".join(sv.rows) if len(getattr(sv, "rows", [])) > 1 else sv.text)
    xs = [_vec(v, "text") for v in nums] if nums else [np.array([0.0]), np.array([0.0])]
    n = max(x.size for x in xs)
    ids = []
    for i in range(max(n, 1) if nums else 1):
        pos = [float(x[min(i, x.size - 1)]) if x.size else 0.0 for x in xs] + [0.0] * (3 - len(xs))
        o = GObj(m._new_id(), "text", a, {"String": s, "Position": pos, "FontSize": 10.0, "Color": [0.0, 0.0, 0.0]})
        m.objs[o.id] = o
        a.children.append(o)
        _apply(m, o, rest, "text")
        ids.append(o.id)
    gb._render(m, a)
    return (_hcol(ids) if len(ids) > 1 else _h(ids[0]),) if nargout else ()


# ------------------------------------------------------------- rendering
def _c(v, default=None):
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return v
    return default


def draw_extra(ax, c, model) -> None:
    p = c.props
    t = c.type
    lab = p.get("DisplayName") or None
    ls = {"none": "None"}.get(p.get("LineStyle", "-"), p.get("LineStyle", "-"))
    mk = p.get("Marker", "none")
    mk = None if mk == "none" else mk
    if t == "errorbar":
        ax.errorbar(p["XData"], p["YData"], yerr=[p.get("YNegativeDelta") or 0, p.get("YPositiveDelta") or 0]
                    if p.get("YNegativeDelta") else None,
                    xerr=[p.get("XNegativeDelta"), p.get("XPositiveDelta")] if p.get("XNegativeDelta") else None,
                    color=_c(p.get("Color")), linestyle=ls, marker=mk, label=lab)
    elif t == "stair":
        ax.step(p["XData"], p["YData"], where="post", color=_c(p.get("Color")), linestyle=ls, marker=mk, label=lab)
    elif t == "stem":
        ax.stem(p["XData"], p["YData"], bottom=float(p.get("BaseValue", 0.0)), label=lab)
    elif t == "area":
        ax.fill_between(p["XData"], p["YData"], float(p.get("BaseValue", 0.0)), color=_c(p.get("FaceColor")), label=lab)
    elif t == "patch":
        if len(p.get("XData") or []) >= 1:
            ax.fill(np.ravel(p["XData"]), np.ravel(p["YData"]), color=_c(p.get("FaceColor"), (0.5, 0.5, 0.5)),
                    edgecolor=_c(p.get("EdgeColor"), "k"), label=lab)
    elif t == "rectangle":
        import matplotlib.patches as mp

        x, y, w, h = (list(p.get("Position", [0, 0, 1, 1])) + [1, 1, 1, 1])[:4]
        ax.add_patch(mp.Rectangle((x, y), w, h, fill=_c(p.get("FaceColor")) is not None,
                                  facecolor=_c(p.get("FaceColor"), "none"), edgecolor=_c(p.get("EdgeColor"), "k")))
    elif t == "image":
        cd = np.asarray(p.get("CData") or [[0]], float)
        xd, yd = p.get("XData") or [1, cd.shape[1]], p.get("YData") or [1, cd.shape[0]]
        xd, yd = (list(np.ravel(xd)) * 2)[:2], (list(np.ravel(yd)) * 2)[:2]
        if cd.ndim == 3:
            cd = np.clip(cd, 0, 1)
        ax.imshow(cd, extent=(xd[0] - 0.5, xd[-1] + 0.5, yd[-1] + 0.5, yd[0] - 0.5), aspect="auto")
    elif t == "contour":
        z = np.asarray(p["ZData"], float)
        x, y = np.asarray(p["XData"], float), np.asarray(p["YData"], float)
        lv = sorted(set(np.ravel(p.get("LevelList") or [])))
        if z.ndim == 2 and min(z.shape) >= 2 and len(lv) >= 1:
            (ax.contourf if p.get("Fill") == "on" else ax.contour)(x, y, z, levels=lv if len(lv) > 1 else None)
    elif t == "surface":
        z = np.asarray(p.get("CData"), float)
        if z.ndim == 2 and min(z.shape) >= 2:
            ax.pcolormesh(np.asarray(p["XData"], float), np.asarray(p["YData"], float), z, shading="auto")
    elif t == "quiver":
        ax.quiver(p["XData"], p["YData"], p["UData"], p["VData"], color=_c(p.get("Color")))
    elif t == "text":
        pos = p.get("Position") or [0, 0, 0]
        ax.text(pos[0], pos[1], str(p.get("String", "")))


def draw_post(ax, a) -> None:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _draw_post(ax, a)


def _draw_post(ax, a) -> None:
    for k, setter in (("XScale", ax.set_xscale), ("YScale", ax.set_yscale)):
        v = a.props.get(k)
        if v in ("log", "linear"):
            try:
                setter(v)
            except Exception:
                pass
    if a.props.get("YDir") == "reverse" and not ax.yaxis_inverted():
        ax.invert_yaxis()
    if a.props.get("XDir") == "reverse" and not ax.xaxis_inverted():
        ax.invert_xaxis()


hm.EXTRA_DRAW = draw_extra
hm.POST_DRAW = draw_post

INTRINSICS = {k: gb._wrap(v) for k, v in {
    "line": _line, "loglog": _logplot("log", "log"), "semilogx": _logplot("log", None),
    "semilogy": _logplot(None, "log"), "errorbar": _errorbar, "area": _series("area", "area"),
    "stairs": _series("stair", "stairs"), "stem": _series("stem", "stem"), "bar": _bars(False),
    "barh": _bars(True), "pie": _pie, "hist": _hist, "patch": _patch_like("patch"), "fill": _patch_like("fill"),
    "rectangle": _rectangle, "imagesc": _image_like(True), "image": _image_like(False), "pcolor": _pcolor,
    "contour": _contour(False), "contourf": _contour(True), "quiver": _quiver, "spy": _spy,
    "polar": _polar(), "polarplot": _polar(), "rose": _rose, "compass": _compass, "plotyy": _plotyy,
    "colormap": _colormap, "caxis": _clim, "clim": _clim, "colorbar": _colorbar,
    "zlabel": _zlabel, "box": _box, "drawnow": _drawnow, "annotation": _annotation, "axes": _axes_fn, "text": _text_fn,
}.items()}
INTRINSICS.update({c: _cmap_fn(c) for c in CMAPS})
STATEMENT_ZERO = set(INTRINSICS) - set(CMAPS)
