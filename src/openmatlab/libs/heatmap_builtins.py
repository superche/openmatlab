"""heatmap for a matrix or a table (M14 V-E4, Epic #997).

The chart is an axes child of type ``heatmap`` (class
``matlab.graphics.chart.HeatmapChart``). Colour is an ``image`` on that same
axes, so tiledlayout / nexttile / title / xlabel keep working, and a matplotlib
colorbar is painted only for this chart. Existing ``imagesc`` pictures are left
alone: their colorbar object is still not drawn.

Matrix form uses the columns and rows in the order given. Table form aggregates
by the x and y variables: a count when ``ColorVariable`` is omitted, otherwise
the mean of that variable (NaN cells stay missing). ``ColorMethod`` accepts
``count`` and ``mean`` only.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np

from openmatlab.graphics import handle_model as hm
from openmatlab.graphics.handle_model import GObj
from openmatlab.libs import chart_builtins as cb
from openmatlab.libs import graphics_builtins as gb
from openmatlab.numerics.ndarray_value import NDArrayValue

_err = gb._err

gb.FULL_CLASS["heatmap"] = "matlab.graphics.chart.HeatmapChart"
hm.CLASS_NAMES.setdefault("heatmap", "HeatmapChart")

cb.KNOWN_PROPS["heatmap"] = {
    "ColorData": [], "XDisplayLabels": [], "YDisplayLabels": [], "ColorLimits": [0.0, 1.0],
    "ColorbarVisible": "on", "Colormap": "parula", "FontSize": 10.0, "Title": "", "XLabel": "",
    "YLabel": "", "MissingDataColor": [0.85, 0.85, 0.85],
}

_PROPS = {
    "colorlimits": "ColorLimits", "title": "Title", "xlabel": "XLabel", "ylabel": "YLabel",
    "colormap": "Colormap", "colorbarvisible": "ColorbarVisible", "xdisplaylabels": "XDisplayLabels",
    "ydisplaylabels": "YDisplayLabels", "fontsize": "FontSize", "missingdatacolor": "MissingDataColor",
    "colorvariable": "ColorVariable", "colormethod": "ColorMethod",
}


def _matrix(v) -> np.ndarray:
    if not hasattr(v, "backend_buffer"):
        raise _err("Color data must be a 2-D numeric matrix.", "OpenMATLAB:heatmap:ColorData")
    buf = np.asarray(v.backend_buffer())
    if buf.dtype.kind not in "biuf":
        raise _err("Color data must be a 2-D numeric matrix.", "OpenMATLAB:heatmap:ColorData")
    c = np.array(buf, dtype=float, copy=True)
    if c.ndim == 1:
        c = c.reshape(1, -1)
    if c.ndim != 2 or c.size == 0:
        raise _err("Color data must be a 2-D numeric matrix.", "OpenMATLAB:heatmap:ColorData")
    return c


def _as_labels(v) -> List[str]:
    from openmatlab.runtime.table_value import texts

    tx = texts(v)
    if tx is not None:
        return [str(s) for s in tx]
    if not hasattr(v, "backend_buffer"):
        raise _err("Labels must be a cell array of text or a numeric vector.", "OpenMATLAB:heatmap:Labels")
    arr = np.asarray(v.backend_buffer(), dtype=float).reshape(-1, order="F")
    return ["%g" % float(x) for x in arr]


def _name(v, what: str) -> str:
    if gb._is_text(v):
        return v.text
    if getattr(v, "is_string", False) and v.numel() == 1:
        from openmatlab.runtime.table_value import text as ttext

        return ttext(v)
    raise _err(f"heatmap: {what} must be a variable name.", "OpenMATLAB:heatmap:TableVariable")


def _categories(keys: Sequence[str]) -> List[str]:
    seen: List[str] = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    nums = []
    for s in seen:
        try:
            nums.append(float(s))
        except ValueError:
            return seen
    if any(not np.isfinite(v) for v in nums):
        return seen
    order = sorted(range(len(seen)), key=lambda i: (nums[i], seen[i]))
    return [seen[i] for i in order]


def _column_text(col, n: int) -> Optional[List[str]]:
    from openmatlab.runtime.table_value import texts

    tx = texts(col)
    if tx is not None and len(tx) == n:
        return [str(s) for s in tx]
    return None


def _column_keys(col, n: int) -> List[str]:
    tx = _column_text(col, n)
    if tx is not None:
        return tx
    if not hasattr(col, "backend_buffer"):
        raise _err("heatmap: x and y variables must be text or numeric.", "OpenMATLAB:heatmap:TableVariable")
    arr = np.asarray(col.backend_buffer(), dtype=float).reshape(n, -1, order="F")
    if arr.shape[1] != 1:
        raise _err("heatmap: x and y variables must be a single column.", "OpenMATLAB:heatmap:TableVariable")
    return ["%g" % float(v) for v in arr[:, 0]]


def _column_numeric(col, n: int) -> np.ndarray:
    if not hasattr(col, "backend_buffer"):
        raise _err("ColorVariable must be numeric.", "OpenMATLAB:heatmap:ColorVariable")
    arr = np.asarray(col.backend_buffer(), dtype=float).reshape(n, -1, order="F")
    if arr.shape[1] != 1:
        raise _err("ColorVariable must be a single numeric column.", "OpenMATLAB:heatmap:ColorVariable")
    return arr[:, 0]


def _from_table(tbl, xvar, yvar, color, method: str):
    n = int(tbl.nrows)
    xkeys = _column_keys(tbl.cols[tbl.var_index(_name(xvar, "x"))], n)
    ykeys = _column_keys(tbl.cols[tbl.var_index(_name(yvar, "y"))], n)
    xcats, ycats = _categories(xkeys), _categories(ykeys)
    if not xcats or not ycats:
        raise _err("heatmap: the table has no rows to aggregate.", "OpenMATLAB:heatmap:EmptyTable")
    xi = {lab: j for j, lab in enumerate(xcats)}
    yi = {lab: i for i, lab in enumerate(ycats)}
    if method == "count":
        grid = np.zeros((len(ycats), len(xcats)))
        for xk, yk in zip(xkeys, ykeys):
            grid[yi[yk], xi[xk]] += 1.0
        return grid, xcats, ycats
    values = _column_numeric(tbl.cols[tbl.var_index(_name(color, "ColorVariable"))], n)
    buckets = [[[] for _ in xcats] for _ in ycats]
    for xk, yk, cv in zip(xkeys, ykeys, values):
        buckets[yi[yk]][xi[xk]].append(float(cv))
    grid = np.full((len(ycats), len(xcats)), np.nan)
    for i, row in enumerate(buckets):
        for j, vals in enumerate(row):
            fin = [v for v in vals if np.isfinite(v)]
            if fin:
                grid[i, j] = float(np.mean(fin))
    return grid, xcats, ycats


def _opts(nv):
    out = {}
    for k, v in gb._name_values(list(nv), "heatmap"):
        key = _PROPS.get(k.lower())
        if key is None:
            raise _err(f"Unrecognized property {k} for class HeatmapChart.", "MATLAB:class:InvalidProperty")
        out[key] = v
    return out


def _limits(v) -> List[float]:
    lim = np.asarray(gb._arr(v, "heatmap"), dtype=float).reshape(-1)
    if lim.size != 2 or not (np.isfinite(lim[0]) and np.isfinite(lim[1]) and lim[0] < lim[1]):
        raise _err("ColorLimits must be a 2-element vector of increasing numeric values.",
                   "OpenMATLAB:heatmap:ColorLimits")
    return [float(lim[0]), float(lim[1])]


def _cmap_array(v):
    if v is None:
        return np.asarray(cb._parula(256), float), "parula"
    if gb._is_text(v):
        name = v.text.strip().lower()
        if name == "default":
            name = "parula"
        if name not in cb.CMAPS:
            raise _err(f"heatmap: unknown colormap '{v.text}'.", "MATLAB:colormap:InvalidName")
        return np.asarray(cb._cmap(name, 256), float), name
    cm = np.asarray(gb._arr(v, "heatmap"), dtype=float)
    if cm.ndim != 2 or cm.shape[1] != 3 or np.any(cm < 0) or np.any(cm > 1):
        raise _err("Colormap must be an m-by-3 array of values in the range [0, 1].", "MATLAB:hg:ColorMapOutOfRange")
    return cm, cm.tolist()


def _override_labels(current: List[str], v, axis: str) -> List[str]:
    labels = _as_labels(v)
    if len(labels) != len(current):
        raise _err(f"{axis}DisplayLabels must have one entry for each {axis.lower()} category.",
                   "OpenMATLAB:heatmap:Labels")
    return labels


def _text_on(a, key: str, s: str) -> None:
    t = a.props.get(key)
    if isinstance(t, GObj):
        t.props["String"] = s


def _heatmap(ev, args, nargout):
    m = gb.model(ev)
    a, rest = gb._target_axes(m, list(args))
    if not rest:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    table = getattr(rest[0], "is_table", False)
    if table:
        if len(rest) < 3 or gb._is_text(rest[1]) and rest[1].text.lower() in _PROPS:
            raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
        # table, xvar, yvar, then name-value. A text xvar is a name, not a property,
        # so peel three positional arguments before looking for pairs.
        lead, nv = rest[:3], rest[3:]
    else:
        lead = []
        i = 0
        while i < len(rest):
            item = rest[i]
            # An even tail that starts with text is name-value, known or not.
            # Odd tails stay positional, so heatmap('ab','cd', C) is still x, y, C.
            if gb._is_text(item) and (len(rest) - i) % 2 == 0:
                break
            lead.append(item)
            i += 1
        nv = rest[i:]
    opts = _opts(nv)
    explicit_method = "ColorMethod" in opts
    method = "mean"
    if explicit_method:
        if not gb._is_text(opts["ColorMethod"]):
            raise _err("ColorMethod must be 'count' or 'mean'.", "OpenMATLAB:heatmap:ColorMethod")
        method = opts["ColorMethod"].text.lower()
        if method not in ("count", "mean"):
            raise _err("ColorMethod must be 'count' or 'mean'.", "OpenMATLAB:heatmap:ColorMethod")
    if table:
        if not explicit_method and "ColorVariable" not in opts:
            method = "count"
        if method == "count" and "ColorVariable" in opts:
            raise _err("ColorMethod 'count' does not take ColorVariable.", "OpenMATLAB:heatmap:ColorMethod")
        if method == "mean" and "ColorVariable" not in opts:
            raise _err("ColorMethod 'mean' needs ColorVariable.", "OpenMATLAB:heatmap:ColorMethod")
        cdata, xlabels, ylabels = _from_table(lead[0], lead[1], lead[2], opts.get("ColorVariable"), method)
    else:
        if "ColorVariable" in opts or "ColorMethod" in opts:
            raise _err("ColorVariable and ColorMethod apply to table input.", "OpenMATLAB:heatmap:TableVariable")
        if len(lead) == 1:
            cdata = _matrix(lead[0])
            xlabels = ["%g" % i for i in range(1, cdata.shape[1] + 1)]
            ylabels = ["%g" % i for i in range(1, cdata.shape[0] + 1)]
        elif len(lead) == 3:
            xlabels, ylabels = _as_labels(lead[0]), _as_labels(lead[1])
            cdata = _matrix(lead[2])
            if len(xlabels) != cdata.shape[1] or len(ylabels) != cdata.shape[0]:
                raise _err("Color data must be length(y) by length(x).", "OpenMATLAB:heatmap:SizeMismatch")
        else:
            raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if "XDisplayLabels" in opts:
        xlabels = _override_labels(xlabels, opts["XDisplayLabels"], "X")
    if "YDisplayLabels" in opts:
        ylabels = _override_labels(ylabels, opts["YDisplayLabels"], "Y")
    a = a or m.gca()
    fig = a.parent
    fig.current_axes = a
    m.current_figure = fig
    rows, cols = cdata.shape
    fin = cdata[np.isfinite(cdata)]
    if "ColorLimits" in opts:
        clim = _limits(opts["ColorLimits"])
    elif fin.size and float(fin.min()) < float(fin.max()):
        clim = [float(fin.min()), float(fin.max())]
    else:
        clim = [0.0, 1.0]
    visible = "on"
    if "ColorbarVisible" in opts:
        if not gb._is_text(opts["ColorbarVisible"]) or opts["ColorbarVisible"].text.lower() not in ("on", "off"):
            raise _err("ColorbarVisible must be 'on' or 'off'.", "OpenMATLAB:heatmap:ColorbarVisible")
        visible = opts["ColorbarVisible"].text.lower()
    cmap, cmap_stored = _cmap_array(opts.get("Colormap"))
    bad = [0.85, 0.85, 0.85]
    if "MissingDataColor" in opts:
        bad = gb._color(opts["MissingDataColor"], "heatmap")
    fs = 8.0 if max(rows, cols) >= 10 else 10.0
    if "FontSize" in opts:
        x = np.asarray(gb._arr(opts["FontSize"], "heatmap"), dtype=float).reshape(-1)
        if x.size != 1 or not (np.isfinite(x[0]) and x[0] > 0):
            raise _err("FontSize must be a positive scalar.", "MATLAB:hg:InvalidValue")
        fs = float(x[0])
    title = opts["Title"].text if "Title" in opts and gb._is_text(opts["Title"]) else ""
    xlab = opts["XLabel"].text if "XLabel" in opts and gb._is_text(opts["XLabel"]) else ""
    ylab = opts["YLabel"].text if "YLabel" in opts and gb._is_text(opts["YLabel"]) else ""
    if ("Title" in opts and not gb._is_text(opts["Title"])) or ("XLabel" in opts and not gb._is_text(opts["XLabel"])) \
            or ("YLabel" in opts and not gb._is_text(opts["YLabel"])):
        raise _err("Title, XLabel, and YLabel must be text.", "OpenMATLAB:heatmap:Text")
    image = cb._new(m, a, "image", {
        "CData": cdata.tolist(), "XData": [1.0, float(cols)], "YData": [1.0, float(rows)],
        "CDataMapping": "scaled", "_Heatmap": True, "_CMap": cmap.tolist(), "_Missing": bad,
    })
    a.props.update({
        "YDir": "reverse", "CLim": clim, "CLimMode": "manual",
        "XTick": [float(i) for i in range(1, cols + 1)], "XTickMode": "manual",
        "YTick": [float(i) for i in range(1, rows + 1)], "YTickMode": "manual",
        "XTickLabel": list(xlabels), "XTickLabelMode": "manual",
        "YTickLabel": list(ylabels), "YTickLabelMode": "manual",
        "XTickLabelRotation": 90.0 if cols >= 8 else 0.0, "XTickLabelRotationMode": "manual",
        "TickLabelInterpreter": "none", "FontSize": fs,
        "XLim": [0.5, cols + 0.5], "YLim": [0.5, rows + 0.5], "XLimMode": "manual", "YLimMode": "manual",
        "_Heatmap": "on", "_ColorbarVisible": visible,
    })
    for key, mult in (("Title", 1.1), ("XLabel", 1.0), ("YLabel", 1.0)):
        t = a.props.get(key)
        if isinstance(t, GObj):
            t.props["FontSize"] = fs * mult
    _text_on(a, "Title", title)
    _text_on(a, "XLabel", xlab)
    _text_on(a, "YLabel", ylab)
    chart = GObj(m._new_id(), "heatmap", a, {
        "ColorData": cdata.tolist(), "XDisplayLabels": list(xlabels), "YDisplayLabels": list(ylabels),
        "ColorLimits": clim, "ColorbarVisible": visible, "Colormap": cmap_stored, "FontSize": fs,
        "Title": title, "XLabel": xlab, "YLabel": ylab, "MissingDataColor": bad,
        "DisplayName": "", "Tag": "",
    })
    chart.image = image
    m.objs[chart.id] = chart
    a.children.append(chart)
    gb._render(m, a)
    return (gb._h(chart.id),) if nargout else ()


def _draw_heat(ax, c) -> None:
    from matplotlib.colors import ListedColormap

    p = c.props
    cd = np.asarray(p.get("CData") or [[0.0]], float)
    if cd.ndim == 1:
        cd = cd.reshape(1, -1)
    cols = cd.shape[1] if cd.ndim == 2 else 1
    rows = cd.shape[0] if cd.ndim == 2 else 1
    xd = (list(np.ravel(p.get("XData") or [1, cols])) * 2)[:2]
    yd = (list(np.ravel(p.get("YData") or [1, rows])) * 2)[:2]
    parent = c.parent
    clim = (parent.props.get("CLim") if parent is not None else None) or [0.0, 1.0]
    if not (clim[0] < clim[1]):
        clim = [0.0, 1.0]
    colors = np.asarray(p.get("_CMap") or cb._parula(256), float)
    cmap = ListedColormap(colors)
    bad = p.get("_Missing") or [0.85, 0.85, 0.85]
    cmap.set_bad(tuple(bad[:3]))
    extent = (xd[0] - 0.5, xd[-1] + 0.5, yd[-1] + 0.5, yd[0] - 0.5)
    shown = cd if np.isfinite(cd).all() else np.ma.masked_invalid(cd)
    ax.imshow(shown, extent=extent, aspect="auto", interpolation="nearest",
              vmin=float(clim[0]), vmax=float(clim[1]), cmap=cmap)


_prev_extra = hm.EXTRA_DRAW


def _extra(ax, c, model):
    if c.type == "image" and c.props.get("_Heatmap"):
        _draw_heat(ax, c)
        return
    if _prev_extra is not None:
        _prev_extra(ax, c, model)


hm.EXTRA_DRAW = _extra
_prev_post = hm.POST_DRAW


def _post(ax, a):
    if _prev_post is not None:
        _prev_post(ax, a)
    if a.props.get("_Heatmap") != "on":
        return
    rotated = False
    for lab in ax.get_xticklabels():
        if lab.get_rotation():
            lab.set_ha("right")
            lab.set_va("center")
            rotated = True
    if rotated:
        ax.tick_params(axis="x", pad=1)
        ax.xaxis.labelpad = 52
    if a.props.get("_ColorbarVisible", "on") != "on" or not ax.images:
        return
    ax.figure.colorbar(ax.images[-1], ax=ax, fraction=0.046, pad=0.03)


def _figure_pre(mfig, model, fig) -> None:
    """A heatmap's category labels need a larger figure than the default 2-D charts."""
    if not any(c.alive and c.type == "axes" and c.props.get("_Heatmap") == "on" for c in fig.children):
        return
    wide = any(c.alive and c.type == "tiledlayout" for c in fig.children)
    mfig.set_size_inches(13.5, 8.0) if wide else mfig.set_size_inches(6.4, 5.2)
    if wide:
        # right stops short of the page so the colorbar tick labels sit inside
        # the canvas. exportgraphics still pads the crop; print keeps this canvas
        # when nothing hangs off the edge (Epic #998).
        mfig.subplots_adjust(left=0.06, right=0.90, bottom=0.22, top=0.88, wspace=0.72, hspace=0.46)


hm.POST_DRAW = _post


def _figure_post(mfig, model, fig) -> None:
    for c in fig.children:
        if not c.alive:
            continue
        if c.type == "tiledlayout":
            title = c.props.get("Title")
            xlab = c.props.get("XLabel")
            if isinstance(title, GObj) and str(title.props.get("String") or ""):
                mfig.suptitle(str(title.props["String"]), fontsize=11)
            note = xlab.props.get("String") if isinstance(xlab, GObj) else ""
            if note:
                mfig.text(0.5, 0.01, str(note), ha="center", va="bottom", fontsize=8,
                          transform=mfig.transFigure)
        elif c.type == "textboxshape":
            s = c.props.get("String") or ""
            if isinstance(s, list):
                s = "\n".join(str(x) for x in s)
            if not str(s):
                continue
            pos = list(c.props.get("Position") or [0.0, 0.0, 1.0, 0.04])
            mfig.text(float(pos[0]), float(pos[1]), str(s), ha="left", va="bottom", fontsize=8,
                      transform=mfig.transFigure)


hm.FIGURE_PRE = _figure_pre
hm.FIGURE_POST = _figure_post

INTRINSICS = {"heatmap": gb._wrap(_heatmap)}
