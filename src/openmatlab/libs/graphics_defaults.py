"""Default property values: ``set(groot, 'DefaultLineLineWidth', 2)`` (M13 G-E4 #771 / G-E7 #774).

``Default<Type><Property>`` can be set on the root, a figure or an axes. It applies to objects of that
type created later below that object; the nearest ancestor wins. Supported types: Figure, Axes, Line,
Text, Patch, Surface, Image, Light, Rectangle, Legend, ColorBar. ``get(h, 'DefaultLineLineWidth')`` returns
the default in effect at ``h`` (the factory value when none is set); ``get(h, 'default')`` returns a
struct of the defaults set on ``h``; ``set(h, 'Default...', 'remove')`` removes one and
``'factory'`` sets the factory value. A default does not override a value that the creating function
gives explicitly (for example a LineSpec style or the ColorOrder colour of ``plot``): it replaces the
creating function's factory value only. Axes title and label text follow the axes font rules, not
``DefaultText*``. ``DefaultFigureWindowStyle = 'docked'`` docks new figures in the Workbench Figures panel.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

import numpy as np

from openmatlab.graphics import handle_model as hm
from openmatlab.graphics.handle_model import GObj
from openmatlab.libs import axes_props as ap
from openmatlab.libs import chart_builtins as cb
from openmatlab.libs import graphics_builtins as gb

_err, _is_text = gb._err, gb._is_text

TYPES = {"figure": "Figure", "axes": "Axes", "line": "Line", "text": "Text", "patch": "Patch",
         "surface": "Surface", "image": "Image", "light": "Light", "rectangle": "Rectangle", "legend": "Legend",
         "colorbar": "ColorBar"}
_EXTRA = {"axes": ("XGrid", "YGrid", "ZGrid", "Box", "NextPlot", "XLim", "YLim", "Visible", "ColorOrderIndex"),
          "figure": ("Color", "Name", "NumberTitle", "Visible", "WindowStyle", "Position", "Units"),
          "text": ("String", "FontSize", "Color"), "line": ("Color", "LineWidth", "LineStyle")}
_HOLDERS = ("root", "figure", "axes")
_STATE = {"label": False}


def _defaults(o: GObj) -> Dict[str, Dict[str, Any]]:
    d = o.__dict__.get("defaults")
    if d is None:
        d = {}
        o.defaults = d
    return d


def _valid_props(typ: str):
    names = set(cb.KNOWN_PROPS.get("*", {})) | set(cb.KNOWN_PROPS.get(typ, {})) | set(_EXTRA.get(typ, ()))
    return {n.lower(): n for n in names if not n.startswith("_")}


def parse_default(name: str):
    """'DefaultLineLineWidth' -> ('line', 'LineWidth') or None."""
    low = name.lower()
    if not low.startswith("default") or len(low) <= 7:
        return None
    rest = low[7:]
    for typ in sorted(TYPES, key=len, reverse=True):
        if rest.startswith(typ) and len(rest) > len(typ):
            props = _valid_props(typ)
            p = props.get(rest[len(typ):])
            if p is None:
                raise _err(f"{name} is an invalid default property name.", "MATLAB:hg:InvalidDefaultProperty")
            return typ, p
    raise _err(f"{name} is an invalid default property name.", "MATLAB:hg:InvalidDefaultProperty")


def _stored_value(m, typ: str, prop: str, v) -> Dict[str, Any]:
    """Validate v by setting it on a scratch object; return the stored property entries."""
    scratch = GObj(-1.0, typ, None, {})
    before = dict(scratch.props)
    gb._set_prop(m, scratch, prop, v)
    return {k: x for k, x in scratch.props.items() if before.get(k, object()) is not x and not k.startswith("_")}


def _lookup(o: Optional[GObj], typ: str, prop: str):
    while o is not None:
        d = o.__dict__.get("defaults") or {}
        ent = d.get(typ, {}).get(prop)
        if ent is not None:
            return ent
        o = o.parent
    return None


_get_prev = gb._get_prop
_set_prev = gb._set_prop


def _get_prop(m, o: GObj, name: str):
    if o.type in _HOLDERS and isinstance(name, str) and name.lower().startswith("default"):
        if name.lower() == "default":
            from openmatlab.runtime.struct_value import StructValue

            keys, vals = [], {}
            for typ, ents in _defaults(o).items():
                for prop, ent in ents.items():
                    k = f"default{TYPES[typ]}{prop}"
                    keys.append(k)
                    vals[k] = gb._to_value(m, o, prop, ent[prop])
            return StructValue((1, 1), tuple(keys), (vals,))
        typ, prop = parse_default(name)
        ent = _lookup(o, typ, prop)
        if ent is not None:
            return gb._to_value(m, o, prop, ent[prop])
        return gb._to_value(m, o, prop, cb.KNOWN_PROPS.get(typ, {}).get(prop, cb.KNOWN_PROPS["*"].get(prop)))
    return _get_prev(m, o, name)


def _set_prop(m, o: GObj, name: str, v) -> None:
    if o.type in _HOLDERS and isinstance(name, str) and name.lower().startswith("default"):
        typ, prop = parse_default(name)
        ents = _defaults(o).setdefault(typ, {})
        if _is_text(v) and v.text.lower() == "remove":
            ents.pop(prop, None)
            return
        if _is_text(v) and v.text.lower() == "factory":
            fac = cb.KNOWN_PROPS.get(typ, {}).get(prop, cb.KNOWN_PROPS["*"].get(prop))
            ents[prop] = {prop: copy.deepcopy(fac)}
            return
        ents[prop] = _stored_value(m, typ, prop, v)
        return
    _set_prev(m, o, name, v)


gb._get_prop = _get_prop
gb._set_prop = _set_prop


def _same(a, b) -> bool:
    try:
        if isinstance(a, (list, tuple, np.ndarray)) or isinstance(b, (list, tuple, np.ndarray)):
            return np.array_equal(np.asarray(a, dtype=object), np.asarray(b, dtype=object))
        return a == b
    except Exception:  # noqa: BLE001 - incomparable values are different
        return False


def apply_defaults(o: GObj, explicit: Dict[str, Any]) -> None:
    if o.type not in TYPES or (o.type == "text" and _STATE["label"]):
        return
    p, chain = o.parent, []
    while p is not None:
        d = p.__dict__.get("defaults")
        if d and d.get(o.type):
            chain.append(d[o.type])
        p = p.parent
    if not chain:
        return
    factory = cb.known(o)
    done = set()
    for ents in chain:  # nearest ancestor first
        for prop, ent in ents.items():
            if prop in done:
                continue
            done.add(prop)
            if prop in explicit and not _same(explicit[prop], factory.get(prop, explicit[prop] if prop not in factory
                                                                               else object())):
                continue
            for k, x in ent.items():
                o.props[k] = copy.deepcopy(x)


_init_prev = GObj.__init__


def _init(self, hid, typ, parent, props):
    _init_prev(self, hid, typ, parent, props)
    if parent is not None and hid != -1.0:
        apply_defaults(self, props)


GObj.__init__ = _init

_text_prev = hm.Model._text


def _text(self, parent, s=""):
    prev, _STATE["label"] = _STATE["label"], True
    try:
        return _text_prev(self, parent, s)
    finally:
        _STATE["label"] = prev


hm.Model._text = _text
_reset_prev = hm.Model._reset_axes


def _reset_axes(self, a, keep_position=True):
    _reset_prev(self, a, keep_position)
    ap._label_fontsizes(a)


hm.Model._reset_axes = _reset_axes
