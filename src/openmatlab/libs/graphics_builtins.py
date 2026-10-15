"""Graphics functions over the handle model (Epic #537).

figure gcf gca close clf cla hold ishold plot bar scatter histogram subplot
title xlabel ylabel legend grid axis xlim ylim get set saveas text delete
ishandle isgraphics. They are frame intrinsics: the object tree lives on the
session's PlotSurface, so every evaluator of a session shares it. Called as
statements they print nothing and leave ``ans`` alone (MATLAB).
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from openmatlab.graphics.handle_model import (CLASS_NAMES, SPEC_COLORS, GObj, GraphicsError, Model,
                                              parse_linespec)
from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def model(ev) -> Model:
    surf = ev.plots
    m = getattr(surf, "_gmodel", None)
    if m is None:
        m = Model()
        m.backend = getattr(surf, "_backend", None)
        try:
            setattr(surf, "_gmodel", m)
        except Exception:
            pass
    return m


# ------------------------------------------------------------- value helpers
def _is_text(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue)


def _is_cell(v):
    from openmatlab.runtime.cell_value import CellValue

    return isinstance(v, CellValue)


def _cv(s):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(s)


def _arr(v, fn="graphics"):
    if not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: expected a numeric argument", "MATLAB:invalidType")
    b = np.asarray(v.backend_buffer())
    return b.reshape(1, 1) if b.ndim == 0 else (b.reshape(1, -1) if b.ndim == 1 else b)


class GraphicsHandle(NDArrayValue):
    """A scalar graphics handle (M8 O-E6).

    It is still the numeric handle id for ``get``/``set``/arithmetic and ``==``,
    and also supports dot notation on the class model: ``h.Prop`` reads and
    ``h.Prop = v`` writes through the shared handle model, and ``isvalid`` /
    ``isobject`` report it as an object.
    """

    __slots__ = ("_model",)
    is_graphics_handle = True

    def __init__(self, hid: float, m: "Model") -> None:
        super().__init__(np.array([[float(hid)]]))
        self._model = m

    @property
    def hid(self) -> float:
        return float(self._data.reshape(-1)[0])

    def _obj(self) -> GObj:
        if not self._model.is_handle(self.hid):
            raise _err("Invalid or deleted object.", "MATLAB:class:InvalidHandle")
        return self._model.get(self.hid)

    @property
    def alive(self) -> bool:
        return self._model.is_handle(self.hid)

    def graphics_class(self) -> str:
        o = self._model.objs.get(self.hid) if hasattr(self._model, "objs") else None
        return CLASS_NAMES.get(o.type, o.type) if o is not None else "matlab.graphics.GraphicsPlaceholder"

    def get_prop(self, name: str):
        try:
            return _get_prop(self._model, self._obj(), name)
        except GraphicsError as e:
            raise _err(str(e), e.identifier) from None

    def set_prop(self, name: str, value):
        o = self._obj()
        try:
            _set_prop(self._model, o, name, value)
            if o.type == "axes":
                self._model.autoscale(o)
            f = self._model.figure_of(o)
            if f is not None:
                self._model.render(f)
        except GraphicsError as e:
            raise _err(str(e), e.identifier) from None
        return self  # handle semantics: the variable keeps the same handle


_CUR = {"model": None}


def _h(x) -> NDArrayValue:
    m = _CUR["model"]
    if m is None:
        return NDArrayValue(np.array([[float(x)]]))
    return GraphicsHandle(x, m)


def _hcol(ids) -> NDArrayValue:
    if not ids:
        return NDArrayValue(np.zeros((0, 1)))
    if len(ids) == 1:
        return _h(ids[0])  # scalar handle supports h.Prop (O-E6)
    return NDArrayValue(np.array(ids, dtype=float).reshape(-1, 1))


def _cells(items):
    from openmatlab.runtime.cell_value import CellValue

    if not items:
        return CellValue(rows=())
    return CellValue(rows=tuple((x,) for x in items))


def _cellstrs(v):
    r, c = v.shape
    return [v.get(i, j).text for j in range(c) for i in range(r)]


def _to_value(m: Model, o: GObj, key: str, val):
    from openmatlab.runtime.char_value import CharValue

    if isinstance(val, GObj):
        return _h(val.id)
    if key == "Children":
        kids = [c for c in o.children if c.alive and c.type != "legend"]
        return _hcol([c.id for c in reversed(kids)])
    if key == "Parent":
        return _h(o.parent.id) if o.parent is not None else NDArrayValue(np.zeros((0, 0)))
    if isinstance(val, str):
        return CharValue(val)
    if isinstance(val, list) and val and all(isinstance(x, str) for x in val):
        return _cells([CharValue(x) for x in val]) if False else _row_cells(val)
    if val is None:
        return NDArrayValue(np.zeros((0, 0)))
    a = np.asarray(val, dtype=float)
    return NDArrayValue(a.reshape(1, -1) if a.ndim <= 1 else a)


def _row_cells(strs):
    from openmatlab.runtime.cell_value import CellValue

    return CellValue(rows=(tuple(_cv(s) for s in strs),))


def _props_view(o: GObj) -> Dict[str, Any]:
    d = {k: v for k, v in o.props.items() if not k.startswith("_")}
    if o.type in ("figure", "axes", "root"):
        d["Children"] = None
    if o.type != "root":
        d["Parent"] = None
    if o.type == "figure":
        d["CurrentAxes"] = getattr(o, "current_axes", None)
    if o.type == "root":
        d["CurrentFigure"] = None
    return d


def _canon(o: GObj, name: str) -> str:
    view = _props_view(o)
    for k in view:
        if k.lower() == name.lower():
            return k
    raise _err(f"Unrecognized property {name} for class {CLASS_NAMES.get(o.type, o.type)}.", "MATLAB:class:InvalidProperty")


def _handles(m: Model, v, fn) -> List[GObj]:
    ids = _arr(v, fn).reshape(-1, order="F")
    try:
        return [m.get(i) for i in ids]
    except GraphicsError as e:
        raise _err(str(e), e.identifier) from None


def _get_prop(m: Model, o: GObj, name: str):
    k = _canon(o, name)
    if o.type == "root" and k == "CurrentFigure":
        f = m.current_figure if (m.current_figure is not None and m.current_figure.alive) else None
        return _h(f.id) if f else NDArrayValue(np.zeros((0, 0)))
    if o.type == "figure" and k == "CurrentAxes":
        a = getattr(o, "current_axes", None)
        return _h(a.id) if a is not None and a.alive else NDArrayValue(np.zeros((0, 0)))
    return _to_value(m, o, k, o.props.get(k))


# ------------------------------------------------------------- property set
_READ_ONLY = {"Type", "Children", "Parent", "Number", "Values"}
_ENUMS = {"XGrid": ("on", "off"), "YGrid": ("on", "off"), "Visible": ("on", "off"), "Box": ("on", "off"),
          "NextPlot": ("add", "replace", "replacechildren"), "XLimMode": ("auto", "manual"), "YLimMode": ("auto", "manual"),
          "LineStyle": ("-", "--", ":", "-.", "none")}


def _color(v, fn):
    if _is_text(v):
        s = v.text.lower()
        named = {"red": "r", "green": "g", "blue": "b", "cyan": "c", "magenta": "m", "yellow": "y", "black": "k", "white": "w"}
        s = named.get(s, s)
        if s in SPEC_COLORS:
            return [float(x) for x in SPEC_COLORS[s]]
        if s == "none":
            return "none"
        raise _err(f"{fn}: invalid color '{v.text}'", "MATLAB:hg:ColorSpec_InvalidColor")
    c = _arr(v, fn).reshape(-1).astype(float)
    if c.size != 3 or np.any(c < 0) or np.any(c > 1):
        raise _err(f"{fn}: color must be an RGB triplet with values in [0, 1]", "MATLAB:hg:ColorSpec_InvalidColor")
    return c.tolist()


def _set_prop(m: Model, o: GObj, name: str, v) -> None:
    k = _canon(o, name)
    if k in _READ_ONLY:
        raise _err(f"Unable to set the '{k}' property of class '{CLASS_NAMES.get(o.type, o.type)}' because it is read-only.", "MATLAB:class:SetProhibited")
    if k in _ENUMS:
        if not _is_text(v) or v.text not in _ENUMS[k]:
            raise _err(f"Invalid value for '{k}' property.", "MATLAB:datatypes:InvalidEnumValue")
        o.props[k] = v.text
    elif k in ("Color", "FaceColor", "CData", "EdgeColor"):
        o.props[k] = _color(v, "set")
    elif k in ("Title", "XLabel", "YLabel"):
        o.props[k] = _handles(m, v, "set")[0]
    elif k in ("String", "Name", "DisplayName", "Marker", "Interpreter", "Tag"):
        if _is_cell(v):
            o.props[k] = _cellstrs(v)
        elif _is_text(v):
            o.props[k] = v.text
        else:
            raise _err(f"Invalid value for '{k}' property.", "MATLAB:hg:InvalidValue")
    elif k in ("XLim", "YLim"):
        lim = _arr(v, "set").reshape(-1).astype(float)
        if lim.size != 2 or not lim[0] < lim[1]:
            raise _err("Value must be a 1x2 vector of numeric type in which the second element is larger than the first and may be Inf.", "MATLAB:hg:shaped_arrays:LimitsWithInfsType")
        o.props[k] = lim.tolist()
        o.props[k + "Mode"] = "manual"
    elif k in ("LineWidth", "BarWidth", "FontSize", "SizeData", "MarkerSize"):
        x = _arr(v, "set").astype(float)
        if np.any(x <= 0):
            raise _err(f"Value must be a positive scalar for '{k}'.", "MATLAB:hg:InvalidValue")
        o.props[k] = float(x.reshape(-1)[0]) if x.size == 1 else x.reshape(-1).tolist()
    elif k in ("XData", "YData"):
        o.props[k] = _arr(v, "set").astype(float).reshape(1, -1).tolist()[0]
        if o.parent is not None and o.parent.type == "axes":
            m.autoscale(o.parent)
    elif _is_text(v):
        o.props[k] = v.text
    else:
        a = _arr(v, "set").astype(float)
        o.props[k] = float(a.reshape(-1)[0]) if a.size == 1 else a.tolist()


def _render(m: Model, o: GObj) -> None:
    m.render(m.figure_of(o))


def _name_values(args, fn):
    if len(args) % 2:
        raise _err(f"{fn}: name-value arguments must come in pairs.", "MATLAB:hg:InvalidNameValuePair")
    out = []
    for i in range(0, len(args), 2):
        if not _is_text(args[i]):
            raise _err(f"{fn}: invalid parameter name.", "MATLAB:hg:InvalidNameValuePair")
        out.append((args[i].text, args[i + 1]))
    return out


def _target_axes(m: Model, args):
    """Leading axes handle argument (plot(ax, ...), title(ax, ...))."""
    if args and not _is_text(args[0]) and hasattr(args[0], "backend_buffer"):
        a = _arr(args[0]).reshape(-1)
        if a.size == 1 and m.is_handle(a[0]) and m.get(a[0]).type == "axes":
            return m.get(a[0]), list(args[1:])
    return None, list(args)


# ------------------------------------------------------------- figure/axes
def _figure(ev, args, nargout):
    m = model(ev)
    m.sync_backend()
    if args and not _is_text(args[0]):
        n = _arr(args[0], "figure").reshape(-1)[0]
        if m.is_handle(n) and m.get(n).type == "figure":
            f = m.get(n)
            m.current_figure = f
        else:
            if n != int(n) or n < 1:
                raise _err("figure: single argument must be a figure number (positive integer) or a figure handle.", "MATLAB:hg:figure:InvalidFigure")
            f = m.new_figure(int(n))
        rest = list(args[1:])
    else:
        f = m.new_figure()
        rest = list(args)
    for k, v in _name_values(rest, "figure"):
        _set_prop(m, f, k, v)
    m.render(f)
    return (_h(f.id),) if nargout else ()


def _gcf(ev, args, nargout):
    m = model(ev)
    f = m.gcf()
    m.render(f)
    return (_h(f.id),)


def _gca(ev, args, nargout):
    m = model(ev)
    a = m.gca()
    m.render(m.figure_of(a))
    return (_h(a.id),)


def _close(ev, args, nargout):
    m = model(ev)
    m.sync_backend()
    if not args:
        f = m.current_figure if m.current_figure is not None and m.current_figure.alive else None
        if f is not None:
            m.delete(f)
    elif _is_text(args[0]):
        w = args[0].text.lower()
        if w not in ("all", "force"):
            raise _err(f"close: unknown option '{args[0].text}'", "MATLAB:close:InvalidArgument")
        for f in m.figures():
            m.delete(f)
    else:
        for o in _handles(m, args[0], "close"):
            if o.type != "figure":
                raise _err("close: argument must be a figure handle.", "MATLAB:close:InvalidFigureHandle")
            m.delete(o)
    return (NDArrayValue(np.array([[1.0]])),) if nargout else ()


def _clf(ev, args, nargout):
    m = model(ev)
    f = m.gcf()
    for c in list(f.children):
        m._delete(c, render=False)
    f.current_axes = None
    m.render(f)
    return (_h(f.id),) if nargout else ()


def _cla(ev, args, nargout):
    m = model(ev)
    a, _ = _target_axes(m, args)
    a = a or m.gca()
    for c in list(a.children):
        m._delete(c, render=False)
    a.props["ColorOrderIndex"] = 1.0
    a.legend = None
    m.autoscale(a)
    _render(m, a)
    return (_h(a.id),) if nargout else ()


def _hold(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    if not rest:
        a.props["NextPlot"] = "replace" if a.props["NextPlot"] == "add" else "add"
    else:
        w = rest[0].text.lower() if _is_text(rest[0]) else ""
        if w in ("on", "all"):
            a.props["NextPlot"] = "add"
        elif w == "off":
            a.props["NextPlot"] = "replace"
        else:
            raise _err("hold: option must be 'on' or 'off'.", "MATLAB:hold:InvalidOption")
    return ()


def _ishold(ev, args, nargout):
    m = model(ev)
    f = m.current_figure
    on = bool(f is not None and f.alive and getattr(f, "current_axes", None) is not None
              and f.current_axes.alive and f.current_axes.props["NextPlot"] == "add")
    return (NDArrayValue(np.array([[on]])),)


def _subplot(ev, args, nargout):
    m = model(ev)
    if len(args) == 1 and not _is_text(args[0]):
        code = int(_arr(args[0], "subplot").reshape(-1)[0])
        r, c, p = code // 100, (code // 10) % 10, code % 10
    elif len(args) >= 3:
        r, c, p = (int(_arr(a, "subplot").reshape(-1)[0]) for a in args[:3])
    else:
        raise _err("subplot: expected subplot(m, n, p).", "MATLAB:subplot:InvalidInput")
    if r < 1 or c < 1 or not 1 <= p <= r * c:
        raise _err("Index exceeds number of subplots.", "MATLAB:subplot:IndexOutOfRange")
    f = m.gcf()
    pos = (r, c, p)
    for a in [x for x in f.children if x.type == "axes" and x.alive]:
        if getattr(a, "position", None) == pos:
            f.current_axes = a
            m.render(f)
            return (_h(a.id),) if nargout else ()
    for a in [x for x in f.children if x.type == "axes" and x.alive]:
        ap = getattr(a, "position", None)
        if ap is None or (ap[0], ap[1]) != (r, c):
            m._delete(a, render=False)  # overlapping axes are replaced (MATLAB)
    a = m.new_axes(f, pos)
    m.render(f)
    return (_h(a.id),) if nargout else ()


# ------------------------------------------------------------- plotting
def _xy_groups(args, fn):
    """Split plot args into (x, y, spec) groups and trailing name-value pairs."""
    groups = []
    i = 0
    n = len(args)
    while i < n and not _is_text(args[i]):
        x = _arr(args[i], fn).astype(float)
        if i + 1 < n and not _is_text(args[i + 1]):
            y = _arr(args[i + 1], fn).astype(float)
            i += 2
        else:
            y, x = x, None
            i += 1
        spec = None
        if i < n and _is_text(args[i]):
            ps = parse_linespec(args[i].text)
            if ps is not None and not (i + 1 < n and args[i].text.lower() in _LINE_PROPS):
                spec = ps
                i += 1
        groups.append((x, y, spec))
    return groups, list(args[i:])


_LINE_PROPS = {"linewidth", "color", "linestyle", "marker", "markersize", "displayname", "tag"}


def _columns(x, y):
    """MATLAB plot rules for vector/matrix x and y -> list of (x, y) 1-D pairs."""
    if x is None:
        if y.shape[0] == 1 or y.shape[1] == 1:
            yv = y.reshape(-1)
            return [(np.arange(1, yv.size + 1, dtype=float), yv)]
        return [(np.arange(1, y.shape[0] + 1, dtype=float), y[:, j]) for j in range(y.shape[1])]
    xv = x.reshape(-1) if 1 in x.shape else None
    yv = y.reshape(-1) if 1 in y.shape else None
    if xv is not None and yv is not None:
        if xv.size != yv.size:
            raise _err("Vectors must be the same length.", "MATLAB:plot:VectorLengthMismatch" if False else "MATLAB:samelen")
        return [(xv, yv)]
    if xv is not None:
        if y.shape[0] == xv.size:
            return [(xv, y[:, j]) for j in range(y.shape[1])]
        if y.shape[1] == xv.size:
            return [(xv, y[i, :]) for i in range(y.shape[0])]
        raise _err("Vectors must be the same length.", "MATLAB:samelen")
    if x.shape != y.shape:
        raise _err("Vectors must be the same length.", "MATLAB:samelen")
    return [(x[:, j], y[:, j]) for j in range(y.shape[1])]


def _plot(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    groups, nv = _xy_groups(rest, "plot")
    if not groups:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    pairs = _name_values(nv, "plot")
    m.prepare_axes_for_plot(a)
    ids = []
    for x, y, spec in groups:
        for xv, yv in _columns(x, y):
            col = None
            style, marker = "-", "none"
            if spec is not None:
                if spec[0]:
                    col = [float(c) for c in SPEC_COLORS[spec[0]]]
                if spec[2]:
                    marker = spec[2]
                    style = spec[1] or "none"
                elif spec[1]:
                    style = spec[1]
            o = m.add_child(a, "line", {
                "XData": xv.tolist(), "YData": yv.tolist(), "Color": col or m.next_color(a),
                "LineStyle": style, "LineWidth": 0.5, "Marker": marker, "MarkerSize": 6.0,
                "DisplayName": "", "Tag": ""})
            for k, v in pairs:
                _set_prop(m, o, k, v)
            ids.append(o.id)
    m.autoscale(a)
    _render(m, a)
    return (_hcol(ids),) if nargout else ()


def _bar(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    nums = [x for x in rest if not _is_text(x)]
    if not nums:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if len(nums) >= 2:
        x = _arr(nums[0], "bar").reshape(-1).astype(float)
        y = _arr(nums[1], "bar").reshape(-1).astype(float)
        rest_nv = list(rest[2:])
    else:
        y = _arr(nums[0], "bar").reshape(-1).astype(float)
        x = np.arange(1, y.size + 1, dtype=float)
        rest_nv = list(rest[1:])
    if x.size != y.size:
        raise _err("X and Y must be the same length.", "MATLAB:bar:XYLengthMismatch")
    width = 0.8
    if rest_nv and not _is_text(rest_nv[0]):
        width = float(_arr(rest_nv.pop(0), "bar").reshape(-1)[0])
    m.prepare_axes_for_plot(a)
    o = m.add_child(a, "bar", {"XData": x.tolist(), "YData": y.tolist(), "BarWidth": width,
                               "FaceColor": m.next_color(a), "DisplayName": "", "Tag": ""})
    for k, v in _name_values(rest_nv, "bar"):
        _set_prop(m, o, k, v)
    m.autoscale(a)
    _render(m, a)
    return (_h(o.id),) if nargout else ()


def _scatter(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    if len(rest) < 2:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    x = _arr(rest[0], "scatter").reshape(-1).astype(float)
    y = _arr(rest[1], "scatter").reshape(-1).astype(float)
    if x.size != y.size:
        raise _err("X and Y must be vectors of the same length.", "MATLAB:scatter:XYLengthMismatch")
    tail = list(rest[2:])
    size = 36.0
    if tail and not _is_text(tail[0]):
        s = _arr(tail.pop(0), "scatter").reshape(-1)
        size = s.tolist() if s.size > 1 else (float(s[0]) if s.size else 36.0)
    m.prepare_axes_for_plot(a)
    o = m.add_child(a, "scatter", {"XData": x.tolist(), "YData": y.tolist(), "SizeData": size,
                                   "CData": m.next_color(a), "Marker": "o", "DisplayName": "", "Tag": ""})
    for k, v in _name_values(tail, "scatter"):
        _set_prop(m, o, k, v)
    m.autoscale(a)
    _render(m, a)
    return (_h(o.id),) if nargout else ()


def _histogram(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    if not rest:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    data = _arr(rest[0], "histogram").reshape(-1).astype(float)
    tail = list(rest[1:])
    edges = None
    nbins = None
    if tail and not _is_text(tail[0]):
        e = _arr(tail.pop(0), "histogram").reshape(-1).astype(float)
        if e.size == 1:
            nbins = int(e[0])
        else:
            edges = e
    pairs = []
    for k, v in _name_values(tail, "histogram"):
        kl = k.lower()
        if kl == "binedges":
            edges = _arr(v, "histogram").reshape(-1).astype(float)
        elif kl == "numbins":
            nbins = int(_arr(v, "histogram").reshape(-1)[0])
        else:
            pairs.append((k, v))
    finite = data[np.isfinite(data)]
    if edges is None:
        if nbins is not None:
            if nbins < 1:
                raise _err("histogram: NumBins must be a positive integer.", "MATLAB:histogram:InvalidNumBins")
            lo, hi = (float(finite.min()), float(finite.max())) if finite.size else (0.0, 1.0)
            if lo == hi:
                lo, hi = lo - 0.5, hi + 0.5
            edges = np.linspace(lo, hi, nbins + 1)
        else:
            edges = np.histogram_bin_edges(finite if finite.size else np.array([0.0, 1.0]), bins="auto")
    if edges.size < 2 or np.any(np.diff(edges) <= 0):
        raise _err("histogram: BinEdges must be a monotonically increasing vector.", "MATLAB:histogram:InvalidBinEdges")
    values, _ = np.histogram(finite, bins=edges)
    m.prepare_axes_for_plot(a)
    o = m.add_child(a, "histogram", {"Data": data.tolist(), "BinEdges": edges.tolist(),
                                     "Values": values.astype(float).tolist(), "NumBins": float(edges.size - 1),
                                     "FaceColor": m.next_color(a), "DisplayName": "", "Tag": ""})
    for k, v in pairs:
        _set_prop(m, o, k, v)
    m.autoscale(a)
    _render(m, a)
    return (_h(o.id),) if nargout else ()


# ------------------------------------------------------------- decorations
def _label(key):
    def f(ev, args, nargout):
        m = model(ev)
        a, rest = _target_axes(m, args)
        a = a or m.gca()
        if not rest:
            raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
        s = rest[0]
        t = a.props[key]
        if _is_cell(s):
            t.props["String"] = "\n".join(_cellstrs(s))
        elif _is_text(s):
            t.props["String"] = "\n".join(s.rows) if len(s.rows) > 1 else s.text
        else:
            t.props["String"] = str(_arr(s).reshape(-1)[0])
        for k, v in _name_values(list(rest[1:]), key.lower()):
            _set_prop(m, t, k, v)
        _render(m, a)
        return (_h(t.id),) if nargout else ()
    return f


def _legend(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    kids = [c for c in a.children if c.alive]
    if rest and _is_text(rest[0]) and rest[0].text.lower() in ("off", "hide"):
        if a.legend is not None:
            a.legend.alive = False
        a.legend = None
        _render(m, a)
        return ()
    names: List[str] = []
    nv = []
    i = 0
    while i < len(rest):
        x = rest[i]
        if _is_cell(x):
            names += _cellstrs(x)
        elif _is_text(x) and x.text.lower() in ("location", "orientation", "box", "fontsize", "autoupdate") and i + 1 < len(rest):
            nv.append((x.text, rest[i + 1]))
            i += 1
        elif _is_text(x) and x.text.lower() in ("show", "boxoff", "boxon"):
            pass
        elif _is_text(x):
            names.append(x.text)
        i += 1
    if not names:
        names = [c.props.get("DisplayName") or f"data{k + 1}" for k, c in enumerate(kids)]
    for c, n in zip(kids, names):
        c.props["DisplayName"] = n
    if a.legend is not None:
        a.legend.alive = False
    lg = GObj(m._new_id(), "legend", a, {"String": names[: len(kids)] if kids else names,
                                          "Location": "northeast", "Visible": "on", "Box": "on"})
    m.objs[lg.id] = lg
    a.legend = lg
    for k, v in nv:
        if k.lower() == "location":
            lg.props["Location"] = v.text if _is_text(v) else "northeast"
    _render(m, a)
    return (_h(lg.id),) if nargout else ()


def _grid(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    if not rest:
        new = "off" if a.props["XGrid"] == "on" else "on"
    else:
        w = rest[0].text.lower() if _is_text(rest[0]) else ""
        if w not in ("on", "off", "minor"):
            raise _err("grid: option must be 'on', 'off' or 'minor'.", "MATLAB:grid:InvalidOption")
        new = "on" if w == "minor" else w
    a.props["XGrid"] = a.props["YGrid"] = new
    _render(m, a)
    return ()


def _lim(key):
    def f(ev, args, nargout):
        m = model(ev)
        a, rest = _target_axes(m, args)
        a = a or m.gca()
        if not rest:
            return (NDArrayValue(np.array([a.props[key]], dtype=float)),)
        v = rest[0]
        if _is_text(v):
            w = v.text.lower()
            if w == "auto":
                a.props[key + "Mode"] = "auto"
                m.autoscale(a)
            elif w == "manual":
                a.props[key + "Mode"] = "manual"
            elif w == "mode":
                return (_cv(a.props[key + "Mode"]),)
            elif w == "tight":
                xl, yl = m.data_extent(a)
                a.props[key] = xl if key == "XLim" else yl
                a.props[key + "Mode"] = "manual"
            else:
                raise _err(f"{key.lower()}: invalid option '{v.text}'.", "MATLAB:lim:InvalidOption")
        else:
            _set_prop(m, a, key, v)
        _render(m, a)
        return (NDArrayValue(np.array([a.props[key]], dtype=float)),) if nargout else ()
    return f


def _axis(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    for v in rest:
        if _is_text(v):
            w = v.text.lower()
            if w == "auto":
                a.props["XLimMode"] = a.props["YLimMode"] = "auto"
                m.autoscale(a)
            elif w == "tight":
                xl, yl = m.data_extent(a)
                a.props.update({"XLim": xl, "YLim": yl, "XLimMode": "manual", "YLimMode": "manual"})
            elif w in ("off", "on"):
                a.props["Visible"] = w
            elif w in ("equal", "image", "square", "normal", "manual", "ij", "xy", "fill", "vis3d"):
                if w == "manual":
                    a.props["XLimMode"] = a.props["YLimMode"] = "manual"
            else:
                raise _err(f"axis: unknown option '{v.text}'.", "MATLAB:axis:UnknownOption")
        else:
            lim = _arr(v, "axis").reshape(-1).astype(float)
            if lim.size not in (4, 6) or not (lim[0] < lim[1] and lim[2] < lim[3]):
                raise _err("Vector must have 4, 6, or 8 elements with increasing limit pairs.", "MATLAB:axis:WrongNumberElements")
            _set_prop(m, a, "XLim", NDArrayValue(lim[:2].reshape(1, 2)))
            _set_prop(m, a, "YLim", NDArrayValue(lim[2:4].reshape(1, 2)))
    _render(m, a)
    if nargout or not rest:
        return (NDArrayValue(np.array([a.props["XLim"] + a.props["YLim"]], dtype=float)),) if (nargout or not rest) and nargout else ()
    return ()


def _text_fn(ev, args, nargout):
    m = model(ev)
    a, rest = _target_axes(m, args)
    a = a or m.gca()
    if len(rest) < 3:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    x = float(_arr(rest[0]).reshape(-1)[0])
    y = float(_arr(rest[1]).reshape(-1)[0])
    s = rest[2].text if _is_text(rest[2]) else str(_arr(rest[2]).reshape(-1)[0])
    o = GObj(m._new_id(), "text", a, {"String": s, "Position": [x, y, 0.0], "FontSize": 10.0, "Color": [0.0, 0.0, 0.0]})
    m.objs[o.id] = o
    a.children.append(o)
    for k, v in _name_values(list(rest[3:]), "text"):
        _set_prop(m, o, k, v)
    _render(m, a)
    return (_h(o.id),) if nargout else ()


# ------------------------------------------------------------- get/set/misc
def _get(ev, args, nargout):
    from openmatlab.runtime.struct_value import StructValue

    m = model(ev)
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    objs = _handles(m, args[0], "get")
    if len(args) == 1:
        if len(objs) != 1:
            raise _err("get: a property struct needs a single handle.", "MATLAB:hg:InvalidHandleArray")
        o = objs[0]
        keys = sorted(_props_view(o))
        d = {k: _get_prop(m, o, k) for k in keys}
        return (StructValue((1, 1), tuple(keys), (d,)),)
    if not _is_text(args[1]):
        raise _err("get: property name must be a character vector.", "MATLAB:hg:InvalidPropertyName")
    vals = [_get_prop(m, o, args[1].text) for o in objs]
    if len(vals) == 1:
        return (vals[0],)
    return (_cells(vals),)


def _set(ev, args, nargout):
    m = model(ev)
    if len(args) < 3:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    objs = _handles(m, args[0], "set")
    for o in objs:
        for k, v in _name_values(list(args[1:]), "set"):
            _set_prop(m, o, k, v)
        if o.type == "axes":
            m.autoscale(o)
    for f in {id(m.figure_of(o)): m.figure_of(o) for o in objs}.values():
        m.render(f)
    return ()


def _saveas(ev, args, nargout):
    m = model(ev)
    if len(args) < 2 or not _is_text(args[1]):
        raise _err("saveas: usage saveas(fig, filename[, format]).", "MATLAB:saveas:InvalidInput")
    o = _handles(m, args[0], "saveas")[0]
    f = m.figure_of(o)
    if f is None:
        raise _err("saveas: handle is not a figure or a child of a figure.", "MATLAB:saveas:InvalidHandle")
    path = args[1].text
    fmt = args[2].text.lower() if len(args) > 2 and _is_text(args[2]) else None
    import os

    if fmt is None and "." not in os.path.basename(path):
        fmt = "fig"
    if fmt is not None and "." not in os.path.basename(path):
        path = f"{path}.{fmt}"
    ext = (fmt or os.path.splitext(path)[1][1:]).lower()
    ext = {"jpg": "jpeg", "tif": "tiff"}.get(ext, ext)
    if ext not in ("png", "jpeg", "pdf", "svg", "eps", "tiff"):
        raise _err(f"saveas: unsupported format '{ext}' (.fig files are not supported).", "MATLAB:saveas:badFormat")
    be = m.backend
    if be is None or not hasattr(be, "save_figure"):
        raise _err("saveas: no graphics backend available.", "MATLAB:saveas:noBackend")
    m.render(f)
    be.save_figure(int(f.id), path, ext)
    return ()


def _delete(ev, args, nargout):
    if not args or _is_text(args[0]) or _is_cell(args[0]) or getattr(args[0], "is_class_instance", False) \
            or getattr(args[0], "is_listener", False):
        # delete(filename): file builtin; delete(obj): handle-object delete (M8)
        fn = ev.functions.resolve("delete")
        out = tuple(fn(list(args), nargout=nargout))
        return out if nargout else ()
    m = model(ev)
    for o in _handles(m, args[0], "delete"):
        m.delete(o)
    return ()


def _ishandle(ev, args, nargout):
    m = model(ev)
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if not hasattr(args[0], "backend_buffer") or _is_text(args[0]):
        return (NDArrayValue(np.array([[False]])),)
    a = _arr(args[0])
    out = np.vectorize(lambda x: m.is_handle(x), otypes=[bool])(a) if a.size else np.zeros(a.shape, bool)
    return (NDArrayValue(out),)


def _wrap(fn):
    def call(ev, args, nargout):
        prev = _CUR["model"]
        try:
            _CUR["model"] = model(ev)  # scalar handles returned below carry the model (O-E6)
        except Exception:
            _CUR["model"] = None
        try:
            return fn(ev, args, nargout)
        except GraphicsError as e:
            raise _err(str(e), e.identifier) from None
        finally:
            _CUR["model"] = prev
    return call


INTRINSICS = {k: _wrap(v) for k, v in {
    "figure": _figure, "gcf": _gcf, "gca": _gca, "close": _close, "clf": _clf, "cla": _cla,
    "hold": _hold, "ishold": _ishold, "subplot": _subplot, "plot": _plot, "bar": _bar,
    "scatter": _scatter, "histogram": _histogram, "title": _label("Title"), "xlabel": _label("XLabel"),
    "ylabel": _label("YLabel"), "legend": _legend, "grid": _grid, "xlim": _lim("XLim"), "ylim": _lim("YLim"),
    "axis": _axis, "text": _text_fn, "get": _get, "set": _set, "saveas": _saveas, "delete": _delete,
    "ishandle": _ishandle, "isgraphics": _ishandle,
}.items()}

# called as statements these print nothing and do not set ans
STATEMENT_ZERO = set(INTRINSICS) - {"gcf", "gca", "ishold", "get", "ishandle", "isgraphics"}
