"""3-D plotting, colour and image helpers (Epic #771, M13 G-E4: G05, G06).

plot3 scatter3 surf surfc mesh meshc waterfall contour3 bar3 sphere cylinder
ellipsoid view zlim shading lighting light camlight material imshow daspect
pbaspect clabel uistack xticks yticks zticks xticklabels yticklabels.

3-D objects live in the handle tree with MATLAB's ``Type``/class. Rendering is a
best-effort projection on the 2-D matplotlib axes (the model, not the pixels,
is the contract; see the G10 snapshot epic #774). ``view`` stores ``View``
[az el]; ``view(3)`` is MATLAB's default [-37.5 30].
"""

from __future__ import annotations

import numpy as np

from openmatlab.graphics import handle_model as hm
from openmatlab.graphics.handle_model import GObj
from openmatlab.libs import chart_builtins as cb
from openmatlab.libs import graphics_builtins as gb
from openmatlab.numerics.ndarray_value import NDArrayValue

_err, _arr, _is_text, _is_cell, _h, _hcol = gb._err, gb._arr, gb._is_text, gb._is_cell, gb._h, gb._hcol

hm.CLASS_NAMES.setdefault("hggroup", "Group")
gb.FULL_CLASS.setdefault("hggroup", "matlab.graphics.primitive.Group")
hm.CLASS_NAMES.setdefault("light", "Light")
gb.FULL_CLASS.setdefault("light", "matlab.graphics.primitive.Light")
cb.KNOWN_PROPS["light"] = {"Position": [1.0, 0.0, 1.0], "Style": "infinite", "Color": [1.0, 1.0, 1.0]}
cb.KNOWN_PROPS["surface"] = dict(cb.KNOWN_PROPS["surface"], FaceColor="flat", EdgeColor=[0.0, 0.0, 0.0],
                                 AlphaData=1.0, FaceAlpha=1.0, AmbientStrength=0.3, DiffuseStrength=0.8,
                                 SpecularStrength=0.9, SpecularExponent=10.0, BackFaceLighting="reverselit",
                                 EdgeLighting="none", MeshStyle="both", AlphaDataMapping="scaled")
cb.KNOWN_PROPS["scatter"] = dict(cb.KNOWN_PROPS["scatter"])

_DEFAULT_3D = [-37.5, 30.0]


def _m(ev):
    return gb.model(ev)


def _as3d(a):
    if a.props.get("View", [0.0, 90.0]) == [0.0, 90.0]:
        a.props["View"] = list(_DEFAULT_3D)


def _zrange(a):
    zs = []
    for c in a.children:
        if c.alive and c.props.get("ZData") is not None:
            try:
                z = np.asarray(c.props.get("ZData"), float).ravel()
            except (TypeError, ValueError):
                continue
            zs.append(z[np.isfinite(z)])
    v = np.concatenate(zs) if zs else np.array([])
    if not v.size:
        return [-1.0, 1.0]
    lo, hi = float(v.min()), float(v.max())
    return [lo - 1, hi + 1] if lo == hi else [lo, hi]


def _finish(m, a, ids, nargout, col=False):
    if a.props.get("ZLimMode", "auto") == "auto":
        a.props["ZLim"] = _zrange(a)
    return cb._finish(m, a, ids, nargout, col)


def _plot3(ev, args, nargout):
    m = _m(ev)
    a, rest = cb._axes(m, args)
    nums, spec, nv = cb._split(rest)
    if len(nums) < 3:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    m.prepare_axes_for_plot(a)
    x, y, z = (_arr(v, "plot3").astype(float) for v in nums[:3])
    xs = [x.reshape(-1)] if 1 in x.shape else [x[:, j] for j in range(x.shape[1])]
    ys = [y.reshape(-1)] if 1 in y.shape else [y[:, j] for j in range(y.shape[1])]
    zs = [z.reshape(-1)] if 1 in z.shape else [z[:, j] for j in range(z.shape[1])]
    n = max(len(xs), len(ys), len(zs))
    ids = []
    for k in range(n):
        xv, yv, zv = xs[min(k, len(xs) - 1)], ys[min(k, len(ys) - 1)], zs[min(k, len(zs) - 1)]
        if not (xv.size == yv.size == zv.size):
            raise _err("Vectors must be the same length.", "MATLAB:samelen")
        col, style, marker = cb._spec_props(spec, None)
        o = cb._new(m, a, "line", {"XData": xv.tolist(), "YData": yv.tolist(), "ZData": zv.tolist(),
                                   "Color": col or m.next_color(a), "LineStyle": style, "LineWidth": 0.5,
                                   "Marker": marker, "MarkerSize": 6.0}, fresh=False)
        cb._apply(m, o, nv, "plot3")
        ids.append(o.id)
    _as3d(a)
    return _finish(m, a, ids, nargout, col=True)


def _scatter3(ev, args, nargout):
    m = _m(ev)
    a, rest = cb._axes(m, args)
    if len(rest) < 3:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    z = cb._vec(rest[2], "scatter3")
    out = gb.INTRINSICS["scatter"](ev, [gb._h(a.id), rest[0], rest[1]] + list(rest[3:]), 1)
    o = m.get(float(np.asarray(out[0].backend_buffer()).reshape(-1)[0]))
    if z.size != len(o.props["XData"]):
        raise _err("X, Y and Z must be vectors of the same length.", "MATLAB:scatter3:XYZLengthMismatch")
    o.props["ZData"] = z.tolist()
    _as3d(a)
    return _finish(m, a, [o.id], nargout)


def _grid(nums, fn):
    if len(nums) >= 3:
        x, y, z = (_arr(v, fn).astype(float) for v in nums[:3])
        c = _arr(nums[3], fn).astype(float) if len(nums) > 3 else z
    elif nums:
        z = _arr(nums[0], fn).astype(float)
        x, y = np.meshgrid(np.arange(1, z.shape[1] + 1.0), np.arange(1, z.shape[0] + 1.0))
        c = _arr(nums[1], fn).astype(float) if len(nums) > 1 else z
    else:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if 1 in x.shape and 1 in y.shape and x.size * y.size == z.size and z.ndim == 2:
        x, y = np.meshgrid(x.reshape(-1), y.reshape(-1))
    if x.shape != z.shape or y.shape != z.shape:
        raise _err("Data dimensions must agree.", "MATLAB:surf:DataDimsMismatch")
    return x, y, z, c


def _surface_fn(kind):
    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = cb._axes(m, args)
        nums, _, nv = cb._split(rest)
        x, y, z, c = _grid(nums, kind)
        if kind in ("surf", "surfc", "mesh", "meshc", "waterfall"):
            m.prepare_axes_for_plot(a)
        mesh = kind.startswith("mesh") or kind == "waterfall"
        props = {"XData": x.tolist(), "YData": y.tolist(), "ZData": z.tolist(), "CData": c.tolist(),
                 "FaceColor": [1.0, 1.0, 1.0] if mesh else "flat", "EdgeColor": "flat" if mesh else [0.0, 0.0, 0.0],
                 "LineStyle": "-", "MeshStyle": "row" if kind == "waterfall" else "both"}
        if kind != "surface":
            props["_cls"] = "matlab.graphics.chart.primitive.Surface"  # surf/mesh; surface() stays primitive
        o = cb._new(m, a, "surface", props, fresh=False)
        cb._apply(m, o, nv, kind)
        ids = [o.id]
        if kind in ("surfc", "meshc"):
            lo, hi = float(np.nanmin(z)), float(np.nanmax(z))
            cc = cb._new(m, a, "contour", {"XData": x.tolist(), "YData": y.tolist(), "ZData": z.tolist(),
                                           "LevelList": np.linspace(lo, hi, 10)[1:-1].tolist(), "Fill": "off"}, fresh=False)
            ids.append(cc.id)
        fin = c[np.isfinite(c)]
        if fin.size and fin.min() < fin.max() and a.props.get("CLimMode", "auto") == "auto":
            a.props["CLim"] = [float(fin.min()), float(fin.max())]
        if kind != "surface":
            _as3d(a)
        return _finish(m, a, ids, nargout, col=len(ids) > 1)
    return f


def _contour3(ev, args, nargout):
    out = cb.INTRINSICS["contour"](ev, args, max(nargout, 0))
    m = _m(ev)
    _as3d(m.gca())
    return out


def _bar3(ev, args, nargout):
    m = _m(ev)
    a, rest = cb._axes(m, args)
    nums, _, nv = cb._split(rest)
    if not nums:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    z = _arr(nums[-1], "bar3").astype(float)
    if 1 in z.shape:
        z = z.reshape(-1, 1)
    m.prepare_axes_for_plot(a)
    ids = []
    for j in range(z.shape[1]):
        r = np.arange(1, z.shape[0] + 1.0)
        xx, yy = np.meshgrid([j + 0.6, j + 1.4], r)
        o = cb._new(m, a, "surface", {"XData": xx.tolist(), "YData": yy.tolist(),
                                      "ZData": np.c_[z[:, j], z[:, j]].tolist(), "CData": np.c_[z[:, j], z[:, j]].tolist(),
                                      "FaceColor": m.next_color(a), "EdgeColor": [0.0, 0.0, 0.0]}, fresh=False)
        ids.append(o.id)
    _as3d(a)
    return _finish(m, a, ids, nargout, col=True)


def _xyz_out(x, y, z, ev, args, nargout, ax_args):
    if nargout:
        return (NDArrayValue(x), NDArrayValue(y), NDArrayValue(z))[:max(nargout, 1)]
    return _surface_fn("surf")(ev, ax_args + [NDArrayValue(x), NDArrayValue(y), NDArrayValue(z)], 0)


def _sphere(ev, args, nargout):
    rest = list(args)
    ax = []
    if rest and hasattr(rest[0], "backend_buffer") and not _is_text(rest[0]):
        h = _arr(rest[0], "sphere").reshape(-1)
        m = _m(ev)
        if h.size == 1 and m.is_handle(h[0]) and h[0] != int(h[0]):
            ax = [rest.pop(0)]
    n = int(cb._vec(rest[0], "sphere")[0]) if rest else 20
    if n < 1:
        raise _err("sphere: N must be a positive integer.", "MATLAB:sphere:InvalidN")
    th = np.linspace(-np.pi, np.pi, n + 1)
    ph = np.linspace(-np.pi / 2, np.pi / 2, n + 1).reshape(-1, 1)
    x, y, z = np.cos(ph) * np.cos(th), np.cos(ph) * np.sin(th), np.sin(ph) * np.ones_like(th)
    x[:, [0, -1]] = np.cos(ph) * -1.0
    y[:, [0, -1]] = 0.0
    x[[0, -1], :] = 0.0
    y[[0, -1], :] = 0.0
    return _xyz_out(x, y, z, ev, args, nargout, ax)


def _cylinder(ev, args, nargout):
    r = cb._vec(args[0], "cylinder") if args else np.array([1.0, 1.0])
    if r.size == 1:
        r = np.array([r[0], r[0]])
    n = int(cb._vec(args[1], "cylinder")[0]) if len(args) > 1 else 20
    th = np.linspace(0, 2 * np.pi, n + 1)
    x = r.reshape(-1, 1) * np.cos(th)
    y = r.reshape(-1, 1) * np.sin(th)
    x[:, -1], y[:, -1] = x[:, 0], 0.0
    z = np.linspace(0, 1, r.size).reshape(-1, 1) * np.ones_like(th)
    return _xyz_out(x, y, z, ev, [], nargout, [])


def _ellipsoid(ev, args, nargout):
    if len(args) < 6:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    xc, yc, zc, xr, yr, zr = (float(cb._vec(v, "ellipsoid")[0]) for v in args[:6])
    n = int(cb._vec(args[6], "ellipsoid")[0]) if len(args) > 6 else 20
    th = np.linspace(-np.pi, np.pi, n + 1)
    ph = np.linspace(-np.pi / 2, np.pi / 2, n + 1).reshape(-1, 1)
    x = xc + xr * np.cos(ph) * np.cos(th)
    y = yc + yr * np.cos(ph) * np.sin(th)
    z = zc + zr * np.sin(ph) * np.ones_like(th)
    return _xyz_out(x, y, z, ev, [], nargout, [])


def _view(ev, args, nargout):
    m = _m(ev)
    a, rest = cb._axes(m, args)
    if not rest:
        v = a.props.get("View", [0.0, 90.0])
        if nargout >= 2:
            return (NDArrayValue(np.array([[v[0]]])), NDArrayValue(np.array([[v[1]]])))
        return (NDArrayValue(np.array([v], float)),)
    w = cb._vec(rest[0], "view")
    if len(rest) >= 2:
        v = [float(w[0]), float(cb._vec(rest[1], "view")[0])]
    elif w.size == 1:
        if w[0] == 2:
            v = [0.0, 90.0]
        elif w[0] == 3:
            v = list(_DEFAULT_3D)
        else:
            raise _err("view: scalar argument must be 2 or 3.", "MATLAB:view:InvalidInput")
    elif w.size == 2:
        v = [float(w[0]), float(w[1])]
    elif w.size == 3:
        x, y, z = w
        v = [float(np.degrees(np.arctan2(x, -y))), float(np.degrees(np.arctan2(z, np.hypot(x, y))))]
    else:
        raise _err("view: argument must be [az el], [x y z], 2 or 3.", "MATLAB:view:InvalidInput")
    a.props["View"] = v
    gb._render(m, a)
    return ()


def _zlim(ev, args, nargout):
    m = _m(ev)
    a, rest = cb._axes(m, args)
    if not rest:
        return (NDArrayValue(np.array([a.props.get("ZLim", _zrange(a))], float)),)
    v = rest[0]
    if _is_text(v):
        w = v.text.lower()
        if w == "auto":
            a.props["ZLimMode"] = "auto"
            a.props["ZLim"] = _zrange(a)
        elif w == "manual":
            a.props["ZLimMode"] = "manual"
        elif w == "mode":
            return (gb._cv(a.props.get("ZLimMode", "auto")),)
        elif w == "tight":
            a.props["ZLim"], a.props["ZLimMode"] = _zrange(a), "manual"
        else:
            raise _err(f"zlim: invalid option '{v.text}'.", "MATLAB:lim:InvalidOption")
    else:
        lim = cb._vec(v, "zlim")
        if lim.size != 2 or not lim[0] < lim[1]:
            raise _err("Value must be a 1x2 vector of numeric type in which the second element is larger than the first and may be Inf.", "MATLAB:hg:shaped_arrays:LimitsWithInfsType")
        a.props["ZLim"], a.props["ZLimMode"] = lim.tolist(), "manual"
    gb._render(m, a)
    return (NDArrayValue(np.array([a.props["ZLim"]], float)),) if nargout else ()


def _shading(ev, args, nargout):
    m = _m(ev)
    a, rest = cb._axes(m, args)
    w = rest[0].text.lower() if rest and _is_text(rest[0]) else ""
    if w not in ("flat", "faceted", "interp"):
        raise _err("shading: option must be 'flat', 'faceted' or 'interp'.", "MATLAB:shading:InvalidOption")
    for c in a.children:
        if c.alive and c.type in ("surface", "patch"):
            c.props["FaceColor"] = "interp" if w == "interp" else "flat"
            c.props["EdgeColor"] = [0.0, 0.0, 0.0] if w == "faceted" else "none"
    gb._render(m, a)
    return ()


def _light(ev, args, nargout):
    m = _m(ev)
    a = m.gca()
    o = GObj(m._new_id(), "light", a, {"Position": [1.0, 0.0, 1.0], "Style": "infinite", "Color": [1.0, 1.0, 1.0]})
    m.objs[o.id] = o
    a.children.append(o)
    rest = list(args)
    if rest and _is_text(rest[0]) and len(rest) % 2 == 1:
        rest.pop(0)  # camlight headlight/right/left
    cb._apply(m, o, rest, "light")
    return (_h(o.id),) if nargout else ()


def _noop_opt(name, opts=None):
    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = cb._axes(m, args)
        if opts is not None and rest and _is_text(rest[0]) and rest[0].text.lower() not in opts:
            raise _err(f"{name}: invalid option '{rest[0].text}'.", f"MATLAB:{name}:InvalidOption")
        return ()
    return f


def _aspect(prop):
    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = cb._axes(m, args)
        if not rest:
            return (NDArrayValue(np.array([a.props.get(prop, [1.0, 1.0, 1.0])], float)),)
        if _is_text(rest[0]):
            a.props[prop + "Mode"] = rest[0].text.lower()
        else:
            v = cb._vec(rest[0], prop)
            if v.size != 3 or np.any(v <= 0):
                raise _err(f"{prop} must be a 3-element vector of positive values.", "MATLAB:hg:InvalidValue")
            a.props[prop], a.props[prop + "Mode"] = v.tolist(), "manual"
        return ()
    return f


def _ticks(axis, labels):
    key = f"{axis}TickLabel" if labels else f"{axis}Tick"

    def f(ev, args, nargout):
        m = _m(ev)
        a, rest = cb._axes(m, args)
        if not rest:
            return (gb._get_prop(m, a, key),)
        if _is_text(rest[0]) and rest[0].text.lower() in ("auto", "manual", "mode"):
            w = rest[0].text.lower()
            if w == "mode":
                return (gb._cv(a.props.get(key + "Mode", "auto")),)
            a.props[key + "Mode"] = w
            return ()
        if not labels:
            v = cb._vec(rest[0], key.lower()) if _arr(rest[0], key.lower()).size else np.array([])
            if v.size > 1 and np.any(np.diff(v) <= 0):
                raise _err("Value must be a vector of increasing numeric values.", "MATLAB:hg:shaped_arrays:IncreasingVectorType")
        gb._set_prop(m, a, key, rest[0])
        a.props[key + "Mode"] = "manual"
        gb._render(m, a)
        return ()
    return f


def _imshow(ev, args, nargout):
    m = _m(ev)
    if not args or _is_text(args[0]):
        raise _err("imshow: image data required (reading image files is not supported).", "MATLAB:imshow:InvalidInput")
    c = np.asarray(args[0].backend_buffer())
    dt = c.dtype
    c = c.astype(float)
    if dt.kind == "b":
        c = c * 1.0
    elif dt == np.uint8:
        c = c / 255.0
    elif dt == np.uint16:
        c = c / 65535.0
    rng = None
    if len(args) > 1 and not _is_text(args[1]):
        r = cb._vec(args[1], "imshow")
        rng = r.tolist() if r.size == 2 else None
    if c.ndim == 2:
        lo, hi = rng or ([float(np.nanmin(c)), float(np.nanmax(c))] if len(args) > 1 and _arr(args[1], "imshow").size == 0 else [0.0, 1.0])
        g = np.clip((c - lo) / (hi - lo if hi > lo else 1.0), 0, 1)
        c = np.stack([g, g, g], axis=2)
    a = m.gca()
    o = cb._new(m, a, "image", {"CData": c.tolist(), "XData": [1.0, float(c.shape[1])], "YData": [1.0, float(c.shape[0])],
                                "CDataMapping": "direct"})
    a.props.update({"YDir": "reverse", "Visible": "off", "DataAspectRatio": [1.0, 1.0, 1.0]})
    return cb._finish(m, a, [o.id], nargout)


def _clabel(ev, args, nargout):
    return (_hcol([]),) if nargout else ()


def _uistack(ev, args, nargout):
    m = _m(ev)
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    objs = gb._handles(m, args[0], "uistack")
    w = args[1].text.lower() if len(args) > 1 and _is_text(args[1]) else "up"
    if w not in ("up", "down", "top", "bottom"):
        raise _err("uistack: option must be 'up', 'down', 'top' or 'bottom'.", "MATLAB:uistack:InvalidOption")
    for o in objs:
        p = o.parent
        if p is None:
            continue
        kids = p.children
        i = kids.index(o)
        kids.pop(i)
        # children are stored oldest first; MATLAB's top of the stack is the newest
        j = {"top": len(kids), "bottom": 0, "up": min(i + 1, len(kids)), "down": max(i - 1, 0)}[w]
        kids.insert(j, o)
    return ()


def _draw3d(ax, c, model):
    p = c.props
    if c.type == "surface":
        z = np.asarray(p.get("ZData"), float)
        x, y = np.asarray(p["XData"], float), np.asarray(p["YData"], float)
        cdat = np.asarray(p.get("CData"), float)
        if cdat.shape == z.shape and z.ndim == 2 and min(z.shape) >= 2:
            ax.pcolormesh(x, y, cdat, shading="auto")
        return True
    if c.type == "light":
        return True
    return False


_prev_extra = hm.EXTRA_DRAW


def _extra(ax, c, model):
    if not _draw3d(ax, c, model) and _prev_extra is not None:
        _prev_extra(ax, c, model)


hm.EXTRA_DRAW = _extra

INTRINSICS = {k: gb._wrap(v) for k, v in {
    "plot3": _plot3, "scatter3": _scatter3, "surf": _surface_fn("surf"), "surfc": _surface_fn("surfc"),
    "mesh": _surface_fn("mesh"), "meshc": _surface_fn("meshc"), "waterfall": _surface_fn("waterfall"),
    "surface": _surface_fn("surface"), "contour3": _contour3, "bar3": _bar3, "sphere": _sphere,
    "cylinder": _cylinder, "ellipsoid": _ellipsoid, "view": _view, "zlim": _zlim, "shading": _shading,
    "light": _light, "camlight": _light, "lighting": _noop_opt("lighting", ("flat", "gouraud", "none", "phong")),
    "material": _noop_opt("material", ("shiny", "dull", "metal", "default")), "imshow": _imshow,
    "daspect": _aspect("DataAspectRatio"), "pbaspect": _aspect("PlotBoxAspectRatio"), "clabel": _clabel,
    "uistack": _uistack, "xticks": _ticks("X", False), "yticks": _ticks("Y", False), "zticks": _ticks("Z", False),
    "xticklabels": _ticks("X", True), "yticklabels": _ticks("Y", True), "zticklabels": _ticks("Z", True),
}.items()}
STATEMENT_ZERO = set(INTRINSICS) - {"sphere", "cylinder", "ellipsoid"}
