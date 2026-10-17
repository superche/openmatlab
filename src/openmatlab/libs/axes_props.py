"""Remaining axes, ruler, figure and text properties (M13 G-E4 #771).

* **Ticks.** ``XTick``/``YTick``/``ZTick`` in ``'auto'`` mode are computed from the limits with the
  same 1/2/5 x 10^k rule as the nice auto limits (#770; whole decades on log axes). Auto tick labels
  are ``sprintf(TickLabelFormat, tick / 10^Exponent)`` (``'%g'`` by default; ``10^{k}`` on log axes).
  Setting ``XTick`` or ``XTickLabel`` switches the matching mode to ``'manual'``; setting the mode
  back to ``'auto'`` recomputes. ``xtickangle``/``ytickangle``/``ztickangle`` set ``*TickLabelRotation``.
* **Rulers.** ``ax.XAxis``/``YAxis``/``ZAxis`` are ``matlab.graphics.axis.decorator.NumericRuler``
  objects whose ``Limits``, ``TickValues``, ``TickLabels``, ``Direction``, ``Scale``, ``Color``,
  ``TickLabelRotation``, ``Label``... read and write the axes properties. With ``yyaxis`` the
  ``YAxis`` is a 2-by-1 array (left; right).
* **Units.** Changing ``Units`` converts ``Position`` (and ``OuterPosition``) of figures, axes,
  legends, colorbars and text, as MATLAB does. Pixel positions are 1-based (normalized 0 is pixel 1);
  physical units use the root ``ScreenPixelsPerInch`` (96); ``characters`` are approximated as
  5 x 13.125 pixels. Text positions convert between ``data``, ``normalized`` and the physical units
  relative to the axes box (no 1-based offset).
* **Fonts.** Title and axis labels follow the axes ``FontSize`` times ``TitleFontSizeMultiplier`` /
  ``LabelFontSizeMultiplier`` until their own ``FontSize`` is set; titles are bold.
* **Rendering.** Manual ticks and labels, label rotation, ``TickDir``, ``Box``, axes ``Color``,
  ``XColor``/``YColor``, grid colour and alpha, fonts and the ``tex``/``latex``/``none`` interpreters
  (TeX is translated to Matplotlib mathtext; text Matplotlib cannot parse is drawn literally, never an
  error) are applied best-effort to the Matplotlib view.
"""

from __future__ import annotations

import re
from typing import List, Optional

import numpy as np

from openmatlab.graphics import handle_model as hm
from openmatlab.graphics.handle_model import GObj
from openmatlab.libs import chart_builtins as cb
from openmatlab.libs import graphics_builtins as gb
from openmatlab.libs import layout_builtins as _lay  # noqa: F401  (patch order: after G-E3)
from openmatlab.numerics.ndarray_value import NDArrayValue

_err, _arr, _is_text, _is_cell = gb._err, gb._arr, gb._is_text, gb._is_cell

# ------------------------------------------------------------------ documented defaults
hm.CLASS_NAMES.setdefault("numericruler", "NumericRuler")
gb.FULL_CLASS.setdefault("numericruler", "matlab.graphics.axis.decorator.NumericRuler")
_CALLBACKS = {"ButtonDownFcn": "", "CreateFcn": "", "DeleteFcn": "", "ContextMenu": None, "UIContextMenu": None,
              "BeingDeleted": "off"}
cb.KNOWN_PROPS["*"].update(_CALLBACKS)
cb.KNOWN_PROPS["axes"].update({
    "TickLabelInterpreter": "tex", "GridColor": [0.15, 0.15, 0.15], "GridAlpha": 0.15,
    "MinorGridColor": [0.1, 0.1, 0.1], "MinorGridAlpha": 0.25, "GridColorMode": "auto",
    "ZAxis": None, "Legend": None, "ZTickLabelRotation": 0.0, "XTickLabelRotationMode": "auto",
    "YTickLabelRotationMode": "auto", "ZTickLabelRotationMode": "auto", "XAxisLocationMode": "auto",
    "FontAngle": "normal", "TitleFontWeight": "bold", "TitleHorizontalAlignment": "center",
    "LabelFontSizeMultiplier": 1.1, "TitleFontSizeMultiplier": 1.1, "FontSizeMode": "auto",
    "Subtitle": None, "BoxStyle": "back", "XLimitMethod": "tickaligned", "YLimitMethod": "tickaligned",
    "ZLimitMethod": "tickaligned", "Interactions": None, "Toolbar": None, "InnerPosition": None,
    "XRuler": None, "YRuler": None, "ZRuler": None})
cb.KNOWN_PROPS["figure"].update({
    "OuterPosition": None, "InnerPosition": None, "CloseRequestFcn": "closereq", "SizeChangedFcn": "",
    "ResizeFcn": "", "WindowButtonDownFcn": "", "WindowButtonUpFcn": "", "WindowButtonMotionFcn": "",
    "WindowScrollWheelFcn": "", "KeyPressFcn": "", "KeyReleaseFcn": "", "WindowKeyPressFcn": "",
    "WindowKeyReleaseFcn": "", "GraphicsSmoothing": "on", "DockControls": "on", "WindowState": "normal",
    "CurrentCharacter": "", "SelectionType": "normal", "CurrentObject": None, "UIContextMenu": None,
    "PaperPositionMode": "auto", "BackingStore": "on", "DoubleBuffer": "on"})
for _t in ("line", "stair", "stem", "errorbar", "quiver"):
    cb.KNOWN_PROPS[_t] = dict(cb.KNOWN_PROPS[_t], MarkerIndices=None, SeriesIndex=1.0, XDataSource="",
                              YDataSource="", ZDataSource="", XDataMode="manual")
cb.KNOWN_PROPS["text"] = dict(cb.KNOWN_PROPS["text"], LineWidth=0.5, LineStyle="-", Editing="off",
                              FontUnits="points", FontSmoothing="on")

_AXES_PROPS_RULER = {"Limits": "Lim", "LimitsMode": "LimMode", "TickValues": "Tick", "TickValuesMode": "TickMode",
                     "TickLabels": "TickLabel", "TickLabelsMode": "TickLabelMode", "Direction": "Dir",
                     "Scale": "Scale", "Color": "Color", "TickLabelRotation": "TickLabelRotation",
                     "TickLabelRotationMode": "TickLabelRotationMode", "MinorTick": "MinorTick", "Label": "Label",
                     "MinorTickValues": None}
_AXES_SHARED_RULER = {"TickDirection": "TickDir", "TickLength": "TickLength", "FontSize": "FontSize",
                      "FontName": "FontName", "FontWeight": "FontWeight", "FontAngle": "FontAngle",
                      "LineWidth": "LineWidth", "TickLabelInterpreter": "TickLabelInterpreter"}
_RULER_OWN = {"Exponent": 0.0, "ExponentMode": "auto", "TickLabelFormat": "%g", "Visible": "on",
              "TickLabelColor": None, "SecondaryLabel": None, "FirstCrossoverValue": -np.inf,
              "TickLabelGapOffset": 2.0, "LabelHorizontalAlignment": "center", "TickDirectionMode": "auto",
              "HandleVisibility": "off", "Tag": "", "UserData": None}
cb.KNOWN_PROPS["numericruler"] = dict(_RULER_OWN)

_UNITS = ("pixels", "normalized", "inches", "centimeters", "points", "characters")
_TEXT_UNITS = _UNITS[:-1] + ("data", "characters")


# ------------------------------------------------------------------ ticks
def auto_ticks(lim, scale=None) -> List[float]:
    """Tick values for limits ``lim`` (our own 1/2/5 x 10^k rule, at most 10 intervals; #770)."""
    lo, hi = float(lim[0]), float(lim[1])
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
        return []
    if scale == "log":
        if lo <= 0:
            return []
        a, b = int(np.ceil(np.log10(lo) - 1e-9)), int(np.floor(np.log10(hi) + 1e-9))
        step = max(1, int(np.ceil((b - a) / 10.0))) if b > a else 1
        return [float(10.0 ** e) for e in range(a, b + 1, step)]
    e = np.floor(np.log10(hi - lo)) - 1
    for k in range(4):
        for mlt in (1.0, 2.0, 5.0):
            step = mlt * 10.0 ** (e + k)
            first = np.ceil(lo / step - 1e-9)
            last = np.floor(hi / step + 1e-9)
            if last - first <= 10:
                return [float(np.round(i * step, 12)) + 0.0 for i in np.arange(first, last + 1)]
    return [lo, hi]


def _fmt(fmt: str, x: float) -> str:
    try:
        s = fmt % x
    except (TypeError, ValueError):
        s = "%g" % x
    return "0" if s in ("-0",) else s


def _ruler_own(a: GObj, ax: str, side: Optional[str] = None) -> dict:
    r = a.props.setdefault("_rulers", {})
    key = ax + (side or "")
    if key not in r:
        r[key] = {}
    return r[key]


def tick_values(a: GObj, ax: str) -> List[float]:
    p = a.props
    if p.get(f"{ax}TickMode", "auto") == "manual" and f"{ax}Tick" in p:
        return [float(x) for x in np.ravel(p[f"{ax}Tick"])]
    lim = p.get(f"{ax}Lim") or cb.known(a).get(f"{ax}Lim") or [0.0, 1.0]
    return auto_ticks(lim, p.get(f"{ax}Scale"))


def tick_labels(a: GObj, ax: str) -> List[str]:
    p = a.props
    if p.get(f"{ax}TickLabelMode", "auto") == "manual" and f"{ax}TickLabel" in p:
        v = p[f"{ax}TickLabel"]
        return list(v) if isinstance(v, list) else [str(v)]
    ticks = tick_values(a, ax)
    if p.get(f"{ax}Scale") == "log":
        return [f"10^{{{int(round(np.log10(t)))}}}" if t > 0 and abs(np.log10(t) - round(np.log10(t))) < 1e-9
                else _fmt("%g", t) for t in ticks]
    own = _ruler_own(a, ax)
    fmt = own.get("TickLabelFormat", "%g")
    ex = float(own.get("Exponent", 0.0)) if own.get("ExponentMode") == "manual" else 0.0
    return [_fmt(fmt, t / 10.0 ** ex) for t in ticks]


# ------------------------------------------------------------------ units
def _ppi(m) -> float:
    return float(m.root.props.get("ScreenPixelsPerInch", 96.0))


def _scale(m, units: str, box) -> tuple:
    """Pixels per unit in x and y; ``box`` is the container size in pixels (for normalized)."""
    ppi = _ppi(m)
    return {"pixels": (1.0, 1.0), "inches": (ppi, ppi), "centimeters": (ppi / 2.54, ppi / 2.54),
            "points": (ppi / 72.0, ppi / 72.0), "characters": (5.0, 13.125),
            "normalized": (float(box[0]), float(box[1]))}[units]


def figure_px(m, f: GObj) -> tuple:
    pos = f.props.get("Position") or cb.known(f)["Position"]
    u = f.props.get("Units", "pixels")
    px = convert_rect(m, list(pos), u, "pixels", _screen(m))
    return float(px[2]), float(px[3])


def _screen(m) -> tuple:
    s = m.root.props.get("ScreenSize") or cb.KNOWN_PROPS["root"]["ScreenSize"]
    return float(s[2]), float(s[3])


def convert_rect(m, pos, src: str, dst: str, box, offset=1.0) -> List[float]:
    """Convert [x y w h] between units inside a container of ``box`` pixels (pixels are 1-based)."""
    if src == dst:
        return [float(v) for v in pos]
    pos = [float(v) for v in pos] + [0.0] * (4 - len(pos))
    sx, sy = _scale(m, src, box)
    if src == "pixels":
        x, y = pos[0], pos[1]
    else:
        x, y = offset + pos[0] * sx, offset + pos[1] * sy
    w, h = pos[2] * sx, pos[3] * sy
    tx, ty = _scale(m, dst, box)
    if dst == "pixels":
        return [x, y, w, h]
    return [(x - offset) / tx, (y - offset) / ty, w / tx, h / ty]


def _container_px(m, o: GObj) -> tuple:
    p = o.parent
    while p is not None and p.type not in ("figure", "root"):
        p = p.parent
    if p is None or p.type == "root":
        return _screen(m)
    return figure_px(m, p)


def axes_px(m, a: GObj) -> tuple:
    """Axes box size in pixels."""
    pos = a.props.get("Position") or cb.known(a)["Position"]
    px = convert_rect(m, pos, a.props.get("Units", "normalized"), "pixels", _container_px(m, a))
    return px[2], px[3]


def _data_to_norm(a: GObj, x: float, k: str) -> float:
    lim = a.props.get(f"{k}Lim") or [0.0, 1.0]
    lo, hi = float(lim[0]), float(lim[1])
    if a.props.get(f"{k}Scale") == "log" and lo > 0 and hi > 0 and x > 0:
        n = (np.log10(x) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
    else:
        n = (x - lo) / (hi - lo) if hi != lo else 0.0
    return 1.0 - n if a.props.get(f"{k}Dir") == "reverse" else n


def _norm_to_data(a: GObj, n: float, k: str) -> float:
    lim = a.props.get(f"{k}Lim") or [0.0, 1.0]
    lo, hi = float(lim[0]), float(lim[1])
    n = 1.0 - n if a.props.get(f"{k}Dir") == "reverse" else n
    if a.props.get(f"{k}Scale") == "log" and lo > 0 and hi > 0:
        return float(10.0 ** (np.log10(lo) + n * (np.log10(hi) - np.log10(lo))))
    return float(lo + n * (hi - lo))


def convert_text_pos(m, t: GObj, pos, src: str, dst: str) -> List[float]:
    a = t.parent
    pos = [float(v) for v in pos] + [0.0] * (3 - len(pos))
    if src == dst or a is None or a.type != "axes":
        return pos
    box = axes_px(m, a)
    if src == "data":
        n = [_data_to_norm(a, pos[0], "X"), _data_to_norm(a, pos[1], "Y")]
    else:
        sx, sy = _scale(m, src, box)
        n = [pos[0] * sx / box[0], pos[1] * sy / box[1]]
    if dst == "data":
        return [_norm_to_data(a, n[0], "X"), _norm_to_data(a, n[1], "Y"), pos[2]]
    tx, ty = _scale(m, dst, box)
    return [n[0] * box[0] / tx, n[1] * box[1] / ty, pos[2]]


def norm_rect(m, o: GObj) -> Optional[List[float]]:
    """Normalized [x y w h] of an axes inside its figure (for rendering)."""
    pos = o.props.get("Position")
    if pos is None:
        return None
    return convert_rect(m, pos, o.props.get("Units", "normalized"), "normalized", _container_px(m, o))


# ------------------------------------------------------------------ rulers
def _ruler(m, a: GObj, ax: str, side: Optional[str] = None) -> GObj:
    store = a.__dict__.setdefault("_ruler_objs", {})
    key = ax + (side or "")
    r = store.get(key)
    if r is None or not r.alive:
        r = GObj(m._new_id(), "numericruler", a, {})
        r.axis, r.side = ax, side
        m.objs[r.id] = r
        store[key] = r
    return r


def _ruler_target(r: GObj, name: str):
    """(object, key) a ruler property maps to, or None for ruler-own properties."""
    a, ax = r.parent, r.axis
    if name in _AXES_PROPS_RULER:
        suffix = _AXES_PROPS_RULER[name]
        if suffix is None:
            return None
        if suffix == "Label":
            return a, f"{ax}Label"
        if r.side is not None and a.props.get("_yyactive") not in (None, r.side) and suffix in ("Lim", "LimMode"):
            return a.props["_yy"][r.side], "Y" + suffix
        if r.side is not None and suffix == "Color":
            return None
        return a, ax + suffix
    if name in _AXES_SHARED_RULER:
        return a, _AXES_SHARED_RULER[name]
    return None


def _canon_ruler(name: str) -> str:
    for k in list(_AXES_PROPS_RULER) + list(_AXES_SHARED_RULER) + list(_RULER_OWN) + ["Type", "Parent", "Children"]:
        if k.lower() == name.lower():
            return k
    raise _err(f"Unrecognized property {name} for class NumericRuler.", "MATLAB:class:InvalidProperty")


# ------------------------------------------------------------------ get / set hooks
_get_base = gb._get_prop
_set_base = gb._set_prop


def _is_label(o: GObj) -> Optional[str]:
    a = o.parent
    if o.type != "text" or a is None or a.type != "axes":
        return None
    for k in ("Title", "XLabel", "YLabel", "ZLabel", "Subtitle"):
        if a.props.get(k) is o:
            return k
    return None


def _get_prop(m, o: GObj, name: str):
    if o.type == "numericruler":
        k = _canon_ruler(name)
        if k == "Type":
            return gb._cv("numericruler")
        if k == "Parent":
            return gb._h(o.parent.id)
        if k == "Children":
            return NDArrayValue(np.zeros((0, 0)))
        tgt = _ruler_target(o, k)
        if tgt is None:
            own = _ruler_own(o.parent, o.axis, o.side) if o.side is None else o.props
            v = own.get(k, o.props.get(k, _RULER_OWN.get(k)))
            if k == "Color" and v is None:  # yyaxis sides default to the first two ColorOrder colours
                v = hm.COLOR_ORDER[0 if o.side == "left" else 1].tolist()
            if k == "MinorTickValues":
                v = []
            return gb._to_value(m, o, k, v)
        obj, key = tgt
        if isinstance(obj, dict):
            return gb._to_value(m, o, key, obj.get(key))
        return _get_prop(m, obj, key)
    k = gb._canon(o, name)
    if o.type == "axes":
        for ax in "XYZ":
            if k == f"{ax}Tick":
                return gb._to_value(m, o, k, tick_values(o, ax))
            if k == f"{ax}TickLabel":
                return gb._row_cells(tick_labels(o, ax))
            if k in (f"{ax}Axis", f"{ax}Ruler"):
                if ax == "Y" and o.props.get("_yyactive") is not None:
                    ids = [_ruler(m, o, "Y", "left").id, _ruler(m, o, "Y", "right").id]
                    return gb._hcol(ids)
                return gb._h(_ruler(m, o, ax).id)
        if k == "InnerPosition":
            return _get_base(m, o, "Position")
        if k == "Legend":
            lg = getattr(o, "legend", None)
            return gb._h(lg.id) if lg is not None and lg.alive else NDArrayValue(np.zeros((0, 0)))
    if o.type == "figure" and k in ("InnerPosition", "OuterPosition") and k not in o.props:
        return _get_base(m, o, "Position")
    if o.type == "text" and k == "FontWeight" and k not in o.props and _is_label(o) in ("Title",):
        return gb._cv("bold")
    if o.type == "line" and k == "MarkerIndices" and k not in o.props:
        n = len(np.ravel(o.props.get("YData") or []))
        return NDArrayValue(np.arange(1, n + 1, dtype=float).reshape(1, -1))
    return _get_base(m, o, name)


def _label_fontsizes(a: GObj) -> None:
    fs = float(a.props.get("FontSize", 10.0))
    tm = float(a.props.get("TitleFontSizeMultiplier", 1.1))
    lm = float(a.props.get("LabelFontSizeMultiplier", 1.1))
    for k, mult in (("Title", tm), ("XLabel", lm), ("YLabel", lm), ("ZLabel", lm), ("Subtitle", 1.0)):
        t = a.props.get(k)
        if isinstance(t, GObj) and not t.props.get("_fsmanual"):
            t.props["FontSize"] = float(np.round(fs * mult, 10))


def _set_units(m, o: GObj, new: str) -> None:
    allowed = _TEXT_UNITS if o.type == "text" else _UNITS
    if new not in allowed:
        raise _err(f"Invalid value for 'Units' property: '{new}'.", "MATLAB:datatypes:InvalidEnumValue")
    old = o.props.get("Units") or cb.known(o).get("Units") or "normalized"
    if o.type == "text":
        if "Position" in o.props or "Position" in cb.known(o):
            pos = o.props.get("Position") or cb.known(o)["Position"]
            o.props["Position"] = convert_text_pos(m, o, pos, old, new)
        o.props["Units"] = new
        return
    box = _screen(m) if o.type == "figure" else _container_px(m, o)
    for k in ("Position", "OuterPosition"):
        pos = o.props.get(k)
        if pos is None:
            pos = cb.known(o).get(k)
        if pos is not None and len(np.ravel(pos)) == 4:
            o.props[k] = convert_rect(m, list(np.ravel(pos)), old, new, box)
    o.props["Units"] = new


def _set_prop(m, o: GObj, name: str, v) -> None:
    if o.type == "numericruler":
        k = _canon_ruler(name)
        if k in ("Type", "Parent", "Children"):
            raise _err(f"Unable to set the '{k}' property of class 'NumericRuler' because it is read-only.",
                       "MATLAB:class:SetProhibited")
        tgt = _ruler_target(o, k)
        if tgt is None:
            own = _ruler_own(o.parent, o.axis) if o.side is None else o.props
            if k == "Exponent":
                x = _arr(v, "set").reshape(-1)
                if x.size != 1 or x[0] != np.round(x[0]):
                    raise _err("Value must be a scalar integer for 'Exponent'.", "MATLAB:hg:InvalidValue")
                own["Exponent"], own["ExponentMode"] = float(x[0]), "manual"
            elif k == "TickLabelFormat":
                if not _is_text(v):
                    raise _err("Value must be a character vector for 'TickLabelFormat'.", "MATLAB:hg:InvalidValue")
                own[k] = v.text
            elif k == "Color":
                own[k] = gb._color(v, "set")
            elif _is_text(v):
                own[k] = v.text
            else:
                a_ = _arr(v, "set").astype(float).reshape(-1)
                own[k] = float(a_[0]) if a_.size == 1 else a_.tolist()
            return
        obj, key = tgt
        if isinstance(obj, dict):  # the inactive yyaxis side
            lim = _arr(v, "set").reshape(-1).astype(float) if key == "YLim" else None
            if lim is not None:
                if lim.size != 2 or not lim[0] < lim[1]:
                    raise _err("Value must be a 1x2 vector of numeric type in which the second element is larger "
                               "than the first and may be Inf.", "MATLAB:hg:shaped_arrays:LimitsWithInfsType")
                obj["YLim"], obj["YLimMode"] = lim.tolist(), "manual"
            elif _is_text(v):
                obj[key] = v.text
            return
        _set_prop(m, obj, key, v)
        return
    k = gb._canon(o, name)
    if k == "Units" and o.type in ("figure", "axes", "text", "legend", "colorbar", "tiledlayout") and _is_text(v):
        _set_units(m, o, v.text.lower())
        return
    if o.type == "axes":
        if k == "InnerPosition":
            k = "Position"
        for ax in "XYZ":
            if k == f"{ax}Tick":
                t = _arr(v, "set").astype(float).reshape(-1) if hasattr(v, "backend_buffer") else None
                if t is None:
                    raise _err("Value must be a vector of increasing numeric values.",
                               "MATLAB:hg:shaped_arrays:IncreasingVectorType")
                if t.size > 1 and np.any(np.diff(t) <= 0):
                    raise _err("Value must be a vector of increasing numeric values.",
                               "MATLAB:hg:shaped_arrays:IncreasingVectorType")
                o.props[k], o.props[k + "Mode"] = t.tolist(), "manual"
                return
            if k == f"{ax}TickLabel":
                o.props[k], o.props[k + "Mode"] = _labels(v), "manual"
                return
            if k in (f"{ax}TickMode", f"{ax}TickLabelMode", f"{ax}TickLabelRotationMode"):
                if not _is_text(v) or v.text not in ("auto", "manual"):
                    raise _err(f"Invalid value for '{k}' property.", "MATLAB:datatypes:InvalidEnumValue")
                if v.text == "manual" and k.endswith("TickMode"):
                    o.props[f"{ax}Tick"] = tick_values(o, ax)
                if v.text == "manual" and k.endswith("TickLabelMode"):
                    o.props[f"{ax}TickLabel"] = tick_labels(o, ax)
                o.props[k] = v.text
                return
            if k == f"{ax}TickLabelRotation":
                x = _arr(v, "set").astype(float).reshape(-1)
                if x.size != 1 or not np.isfinite(x[0]):
                    raise _err(f"Value must be a finite scalar for '{k}'.", "MATLAB:hg:InvalidValue")
                o.props[k], o.props[k + "Mode"] = float(x[0]), "manual"
                return
            if k == f"{ax}Dir" and (not _is_text(v) or v.text not in ("normal", "reverse")):
                raise _err(f"Invalid value for '{k}' property.", "MATLAB:datatypes:InvalidEnumValue")
            if k == f"{ax}Scale" and (not _is_text(v) or v.text not in ("linear", "log")):
                raise _err(f"Invalid value for '{k}' property.", "MATLAB:datatypes:InvalidEnumValue")
        if k in ("TickLabelInterpreter",) and (not _is_text(v) or v.text not in ("tex", "latex", "none")):
            raise _err(f"Invalid value for '{k}' property.", "MATLAB:datatypes:InvalidEnumValue")
        if k == "TickDir" and (not _is_text(v) or v.text not in ("in", "out", "both", "none")):
            raise _err("Invalid value for 'TickDir' property.", "MATLAB:datatypes:InvalidEnumValue")
    if k == "Interpreter" and (not _is_text(v) or v.text not in ("tex", "latex", "none")):
        raise _err("Invalid value for 'Interpreter' property.", "MATLAB:datatypes:InvalidEnumValue")
    if o.type == "figure" and k in ("InnerPosition", "OuterPosition"):
        k = "Position"
    if o.type == "text" and k == "Position" and hasattr(v, "backend_buffer"):
        p = _arr(v, "set").astype(float).reshape(-1)
        if p.size not in (2, 3):
            raise _err("Value must be a 1x2 or 1x3 vector for 'Position'.", "MATLAB:hg:InvalidValue")
        o.props["Position"] = (p.tolist() + [0.0])[:3]
        return
    if k == "Position" and o.type in ("figure", "axes", "legend", "colorbar") and hasattr(v, "backend_buffer"):
        p = _arr(v, "set").astype(float).reshape(-1)
        if p.size != 4 or p[2] < 0 or p[3] < 0:
            raise _err("Value must be a 4-element vector [left bottom width height] with nonnegative width and "
                       "height.", "MATLAB:hg:shaped_arrays:PositionType")
    _set_base(m, o, k, v)
    if o.type == "axes":
        if k in ("FontSize", "TitleFontSizeMultiplier", "LabelFontSizeMultiplier"):
            _label_fontsizes(o)
        if k == "Position" and getattr(o, "layout", None) is None:
            o.props["_rect"] = norm_rect(m, o)
            o.position = None
    if o.type == "text" and k == "FontSize":
        o.props["_fsmanual"] = True


def _labels(v) -> List[str]:
    if _is_cell(v):
        r, c = v.shape
        out = []
        for i in range(r):
            for j in range(c):
                x = v.get(i, j)
                out.append(x.text if _is_text(x) else _num_label(x))
        return out
    if _is_text(v):
        b = np.asarray(v.backend_buffer()) if hasattr(v, "backend_buffer") else None
        if b is not None and b.ndim == 2 and b.shape[0] > 1:  # char matrix: one label per row
            return ["".join(chr(int(c)) if not isinstance(c, str) else c for c in row).rstrip() for row in b]
        return [v.text] if v.text != "" else []
    if hasattr(v, "backend_buffer"):
        return [_fmt("%g", float(x)) for x in np.ravel(np.asarray(v.backend_buffer(), dtype=float), order="F")]
    raise _err("Invalid value for 'TickLabel' property.", "MATLAB:hg:InvalidValue")


def _num_label(x) -> str:
    try:
        a = np.asarray(x.backend_buffer(), dtype=float).reshape(-1)
        return _fmt("%g", float(a[0])) if a.size == 1 else ""
    except Exception:  # noqa: BLE001 - non-numeric cell content becomes an empty label
        return ""


gb._get_prop = _get_prop
gb._set_prop = _set_prop

_known_base = cb.known


def _known(o: GObj):
    if o.type == "numericruler":
        d = dict(_RULER_OWN)
        for k in list(_AXES_PROPS_RULER) + list(_AXES_SHARED_RULER):
            d.setdefault(k, None)
        return d
    return _known_base(o)


cb.known = _known


# ------------------------------------------------------------------ rendering
_GREEK = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi pi rho sigma tau upsilon "
          "phi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega infty pm mp times div "
          "leq geq neq approx equiv partial nabla int sum prod sqrt cdot circ rightarrow leftarrow uparrow "
          "downarrow leftrightarrow Rightarrow Leftarrow forall exists in subset supset cup cap angle "
          "propto sim ldots varepsilon vartheta varphi varsigma").split()
_TEX_TOKEN = re.compile(r"(\\(?:" + "|".join(sorted(_GREEK, key=len, reverse=True)) + r")(?![A-Za-z]))"
                        r"|([\^_])(\{[^{}]*\}|[^{])"
                        r"|(\\(?:bf|it|rm|sl)\b ?)|(\\color(?:\{[^{}]*\}|\[[^\]]*\]\{[^{}]*\}))|(\\fontsize\{[^{}]*\})"
                        r"|(\\fontname\{[^{}]*\})|(\$)")


def _mathtext_ok(s: str) -> bool:
    try:
        from matplotlib.mathtext import MathTextParser

        if s.count("$") - s.count(r"\$") >= 2:
            MathTextParser("path").parse(s)
        return True
    except Exception:  # noqa: BLE001 - unparseable mathtext is drawn literally
        return False


def _literal(s: str) -> str:
    return s.replace("$", r"\$")


def to_mpl_text(s: str, interpreter: str = "tex") -> str:
    """MATLAB text with the given interpreter -> a Matplotlib string that never fails to draw."""
    s = "" if s is None else str(s)
    if interpreter == "none":
        return _literal(s)
    if interpreter == "latex":
        return s if _mathtext_ok(s) else _literal(s.replace("$", ""))

    def rep(mt):
        if mt.group(1):
            return "$" + mt.group(1) + "$"
        if mt.group(2):
            body = mt.group(3)
            body = body[1:-1] if body.startswith("{") else body
            body = re.sub(r"([#%&~])", r"\\\1", body)
            return "$" + mt.group(2) + "{" + (body or r"\ ") + "}$"
        if mt.group(8):
            return r"\$"
        return ""  # \bf, \it, \rm, \color, \fontsize, \fontname: style only

    out = _TEX_TOKEN.sub(rep, s).replace("$$", "")
    return out if _mathtext_ok(out) else _literal(s)


def _text_kw(t: GObj, default_size=None) -> dict:
    p = t.props
    kw = {}
    fs = p.get("FontSize", default_size)
    if fs:
        kw["fontsize"] = float(fs)
    fw = p.get("FontWeight") or ("bold" if _is_label(t) == "Title" else None)
    if fw in ("bold", "normal"):
        kw["fontweight"] = fw
    if p.get("FontAngle") in ("italic", "oblique"):
        kw["fontstyle"] = p["FontAngle"]
    c = p.get("Color")
    if isinstance(c, list) and len(c) == 3:
        kw["color"] = c
    return kw


def _draw_text(ax, c: GObj, model) -> None:
    p = c.props
    s = p.get("String", "")
    s = "\n".join(s) if isinstance(s, list) else str(s)
    pos = list(p.get("Position") or [0, 0, 0])
    units = p.get("Units", "data")
    kw = _text_kw(c)
    ha = p.get("HorizontalAlignment", "left")
    va = {"middle": "center", "cap": "top", "baseline": "baseline"}.get(p.get("VerticalAlignment", "middle"),
                                                                      p.get("VerticalAlignment", "middle"))
    if units not in ("data",):
        pos = convert_text_pos(model, c, pos, units, "normalized")
        kw["transform"] = ax.transAxes
    bg = p.get("BackgroundColor")
    ec = p.get("EdgeColor")
    if (isinstance(bg, list) and len(bg) == 3) or (isinstance(ec, list) and len(ec) == 3):
        kw["bbox"] = {"facecolor": bg if isinstance(bg, list) else "none",
                      "edgecolor": ec if isinstance(ec, list) else "none"}
    ax.text(pos[0], pos[1], to_mpl_text(s, p.get("Interpreter", "tex")), ha=ha if ha in ("left", "center", "right")
            else "left", va=va if va in ("top", "bottom", "center", "baseline") else "center",
            rotation=float(p.get("Rotation", 0.0) or 0.0), **kw)


_extra_prev = hm.EXTRA_DRAW


def _extra(ax, c, model):
    if c.type == "text":
        try:
            _draw_text(ax, c, model)
            return
        except Exception:  # noqa: BLE001 - best-effort rendering never fails the script
            pass
    if _extra_prev is not None:
        _extra_prev(ax, c, model)


hm.EXTRA_DRAW = _extra
_post_prev = hm.POST_DRAW


def _apply_axis(ax, a: GObj, k: str) -> None:
    p = a.props
    axis = ax.xaxis if k == "X" else ax.yaxis
    interp = p.get("TickLabelInterpreter", "tex")
    if p.get(f"{k}TickMode") == "manual" or p.get(f"{k}TickLabelMode") == "manual":
        ticks = tick_values(a, k)
        (ax.set_xticks if k == "X" else ax.set_yticks)(ticks)
        if p.get(f"{k}TickLabelMode") == "manual":
            labels = tick_labels(a, k)
            labels = (labels * (len(ticks) // max(len(labels), 1) + 1))[: len(ticks)] if labels else [""] * len(ticks)
            (ax.set_xticklabels if k == "X" else ax.set_yticklabels)([to_mpl_text(s, interp) for s in labels])
    rot = p.get(f"{k}TickLabelRotation")
    if rot:
        for lab in axis.get_ticklabels():
            lab.set_rotation(float(rot))
    col = p.get(f"{k}Color")
    if isinstance(col, list) and len(col) == 3:
        ax.tick_params(axis=k.lower(), colors=col)
    own = (p.get("_rulers") or {}).get(k) or {}
    if own.get("Visible") == "off":
        ax.tick_params(axis=k.lower(), labelbottom=False, labelleft=False, bottom=False, left=False)


def _post(ax, a):
    if _post_prev is not None:
        _post_prev(ax, a)
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            _post_axes(ax, a)
        except Exception:  # noqa: BLE001 - best-effort rendering never fails the script
            pass


def _post_axes(ax, a: GObj) -> None:
    p = a.props
    fs = float(p.get("FontSize", 10.0))
    ax.tick_params(labelsize=fs)
    td = p.get("TickDir")
    if td in ("in", "out"):
        ax.tick_params(direction=td)
    elif td == "both":
        ax.tick_params(direction="inout")
    for k in "XY":
        _apply_axis(ax, a, k)
    for key, setter in (("Title", ax.set_title), ("XLabel", ax.set_xlabel), ("YLabel", ax.set_ylabel)):
        t = p.get(key)
        if isinstance(t, GObj):
            s = t.props.get("String", "")
            s = "\n".join(s) if isinstance(s, list) else str(s)
            if t.props.get("Visible") == "off":
                s = ""
            setter(to_mpl_text(s, t.props.get("Interpreter", "tex")), **_text_kw(t, fs * 1.1))
    if p.get("Box") == "off":
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    c = p.get("Color")
    if isinstance(c, list) and len(c) == 3:
        ax.set_facecolor(c)
    elif c == "none":
        ax.set_facecolor("none")
    if p.get("XGrid") == "on" or p.get("YGrid") == "on":
        gc = p.get("GridColor", [0.15, 0.15, 0.15])
        ga = float(p.get("GridAlpha", 0.15))
        style = p.get("GridLineStyle", "-")
        ax.grid(False)
        if p.get("XGrid") == "on":
            ax.xaxis.grid(True, color=gc, alpha=max(ga, 0.15), linestyle=style if style != "none" else "")
        if p.get("YGrid") == "on":
            ax.yaxis.grid(True, color=gc, alpha=max(ga, 0.15), linestyle=style if style != "none" else "")
    lw = p.get("LineWidth")
    if lw:
        for sp in ax.spines.values():
            sp.set_linewidth(float(lw))
    if p.get("XAxisLocation") == "top":
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position("top")
    if p.get("YAxisLocation") == "right" and p.get("_yyactive") is None:
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")


hm.POST_DRAW = _post


# ------------------------------------------------------------------ builtins
def _tickangle(axis):
    key = f"{axis}TickLabelRotation"

    def f(ev, args, nargout):
        m = gb.model(ev)
        a, rest = cb._axes(m, args)
        if not rest:
            return (gb._get_prop(m, a, key),)
        if len(rest) != 1 or _is_text(rest[0]) or not hasattr(rest[0], "backend_buffer"):
            raise _err(f"{axis.lower()}tickangle: expected a scalar angle in degrees.", "MATLAB:narginchk:tooManyInputs"
                       if len(rest) > 1 else "MATLAB:hg:InvalidValue")
        _set_prop(m, a, key, rest[0])
        gb._render(m, a)
        return ()
    return f


def _text(ev, args, nargout):
    """text(...) with 'Units' among the name-value pairs: x, y are already in those units (MATLAB)."""
    args = list(args)
    units = None
    i = len(args) - 2
    while i >= 0:
        if _is_text(args[i]) and args[i].text.lower() == "units" and _is_text(args[i + 1]):
            if units is None:
                units = args[i + 1].text.lower()
            del args[i:i + 2]
        i -= 1
    if units is None:
        return cb._text_fn(ev, args, nargout)
    if units not in _TEXT_UNITS:
        raise _err(f"Invalid value for 'Units' property: '{units}'.", "MATLAB:datatypes:InvalidEnumValue")
    m = gb.model(ev)
    out = cb._text_fn(ev, args, 1)
    for hid in np.ravel(np.asarray(out[0].backend_buffer(), dtype=float)):
        m.get(float(hid)).props["Units"] = units
    gb._render(m, m.get(float(np.ravel(np.asarray(out[0].backend_buffer()))[0])))
    return out if nargout else ()


INTRINSICS = {k: gb._wrap(v) for k, v in {
    "text": _text, "xtickangle": _tickangle("X"), "ytickangle": _tickangle("Y"), "ztickangle": _tickangle("Z"),
}.items()}
