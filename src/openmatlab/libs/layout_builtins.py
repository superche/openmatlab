"""Axes layout (M13 G-E3 #770): tiledlayout / nexttile, yyaxis, subplot geometry, axis modes.

Design: docs/design/EPIC-770-layout.md.  A TiledChartLayout is a figure child of type ``tiledlayout``; its
tiles are axes that stay figure children in the tree (so every existing axes code path keeps working) and
point at the layout, which reports them as its ``Children`` and as their ``Parent``.  Tile and subplot
geometry is our own grid rule (documented as approximate, not MATLAB's pixel layout).
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from openmatlab.graphics import handle_model as hm
from openmatlab.graphics.handle_model import GObj
from openmatlab.libs import graphics_builtins as gb
from openmatlab.numerics.ndarray_value import NDArrayValue

_err, _arr, _is_text, _h = gb._err, gb._arr, gb._is_text, gb._h

gb.FULL_CLASS["tiledlayout"] = "matlab.graphics.layout.TiledChartLayout"
hm.CLASS_NAMES.setdefault("tiledlayout", "TiledChartLayout")

_SPACING = {"loose": 0.06, "compact": 0.03, "tight": 0.0, "none": 0.0}
_PADDING = {"loose": 0.07, "compact": 0.03, "tight": 0.0}
DEFAULT_AXES_POSITION = [0.13, 0.11, 0.775, 0.815]


# --- geometry -----------------------------------------------------------------------------------------------

def grid_rect(rows, cols, r0, c0, rs=1, cs=1, area=(0.0, 0.0, 1.0, 1.0), gap=(0.0, 0.0)):
    """[left bottom width height] of the cells (r0..r0+rs-1, c0..c0+cs-1) (0-based, row 0 at the top)."""
    x, y, w, h = area
    gx, gy = gap
    cw = (w - (cols - 1) * gx) / cols
    ch = (h - (rows - 1) * gy) / rows
    left = x + c0 * (cw + gx)
    top = y + h - r0 * (ch + gy)
    width = cs * cw + (cs - 1) * gx
    height = rs * ch + (rs - 1) * gy
    return [round(v, 4) + 0.0 for v in (left, top - height, width, height)]


def subplot_rect(rows, cols, cells: List[int]):
    """Plot box of subplot(m, n, p) over the default axes area: own gaps 0.105 (x) and 0.11 (y)."""
    rr = [(p - 1) // cols for p in cells]
    cc = [(p - 1) % cols for p in cells]
    return grid_rect(rows, cols, min(rr), min(cc), max(rr) - min(rr) + 1, max(cc) - min(cc) + 1,
                     area=tuple(DEFAULT_AXES_POSITION), gap=(0.105 if cols > 1 else 0.0, 0.11 if rows > 1 else 0.0))


def _overlap(p, q) -> bool:
    return (min(p[0] + p[2], q[0] + q[2]) - max(p[0], q[0]) > 1e-9
            and min(p[1] + p[3], q[1] + q[3]) - max(p[1], q[1]) > 1e-9)


# --- tiledlayout / nexttile -------------------------------------------------------------------------------

def _tiles(m, t) -> List[GObj]:
    return [c for c in t.parent.children if c.alive and c.type == "axes" and getattr(c, "layout", None) is t]


def _layout_of(m, fig) -> Optional[GObj]:
    ls = [c for c in fig.children if c.alive and c.type == "tiledlayout"]
    return ls[-1] if ls else None


def _place(t, a) -> None:
    rows, cols = (int(v) for v in t.props["GridSize"])
    k, (rs, cs) = a.tile, a.tile_span
    r0, c0 = (k - 1) // cols, (k - 1) % cols
    pad = _PADDING[t.props["Padding"]]
    gap = _SPACING[t.props["TileSpacing"]]
    rect = grid_rect(rows, cols, r0, c0, rs, cs, area=(pad, pad, 1 - 2 * pad, 1 - 2 * pad), gap=(gap, gap))
    a.props["Position"] = rect
    a.props["OuterPosition"] = rect
    last = k + (rs - 1) * cols + (cs - 1)
    a.position = (rows, cols, (k, last)) if last != k else (rows, cols, k)


def _flow_grid(n):
    cols = max(1, math.ceil(math.sqrt(n)))
    return [float(max(1, math.ceil(n / cols))), float(cols)]


def _tiledlayout(ev, args, nargout):
    m = gb.model(ev)
    rest = list(args)
    fig = None
    nums = 0
    while nums < len(rest) and not _is_text(rest[nums]):
        nums += 1
    # tiledlayout(parent, ...): a handle object, or a figure number before m, n / 'flow'
    if rest and not _is_text(rest[0]) and hasattr(rest[0], "backend_buffer") and (
            isinstance(rest[0], gb.GraphicsHandle) or nums == 3 or (nums == 1 and len(rest) > 1 and _is_text(rest[1])
                                                                    and rest[1].text.lower() in ("flow", "vertical", "horizontal"))):
        h = _arr(rest[0]).reshape(-1)
        if h.size == 1 and m.is_handle(h[0]) and m.get(h[0]).type == "figure":
            fig, rest = m.get(h[0]), rest[1:]
    fig = fig or m.gcf()
    arrangement, grid = "fixed", None
    if rest and _is_text(rest[0]) and rest[0].text.lower() in ("flow", "vertical", "horizontal"):
        arrangement, rest = rest[0].text.lower(), rest[1:]
    elif len(rest) >= 2 and not _is_text(rest[0]) and not _is_text(rest[1]):
        grid, rest = [float(_arr(rest[0]).reshape(-1)[0]), float(_arr(rest[1]).reshape(-1)[0])], rest[2:]
    elif rest and not _is_text(rest[0]) and _arr(rest[0]).size == 2:
        grid, rest = [float(v) for v in _arr(rest[0]).reshape(-1)], rest[1:]
    if grid is not None and (min(grid) < 1 or any(g != int(g) for g in grid)):
        raise _err("Grid size must be a pair of positive integers.", "MATLAB:tiledlayout:InvalidGridSize")
    if grid is None and arrangement == "fixed":
        arrangement = "flow"
    for c in list(fig.children):  # a new layout replaces the figure's axes and layouts
        if c.type in ("axes", "tiledlayout"):
            m._delete(c, render=False)
    fig.current_axes = None
    t = GObj(m._new_id(), "tiledlayout", fig, {
        "GridSize": grid or [1.0, 1.0], "TileSpacing": "loose", "Padding": "loose",
        "TileArrangement": arrangement, "TileIndexing": "rowmajor", "Units": "normalized",
        "OuterPosition": [0.0, 0.0, 1.0, 1.0], "InnerPosition": [0.07, 0.07, 0.86, 0.86],
        "Position": [0.07, 0.07, 0.86, 0.86], "Visible": "on", "HandleVisibility": "on", "Tag": "",
        "UserData": None})
    t.props["Title"] = m._text(t)
    t.props["Subtitle"] = m._text(t)
    t.props["XLabel"] = m._text(t)
    t.props["YLabel"] = m._text(t)
    m.objs[t.id] = t
    fig.children.append(t)
    for k, v in gb._name_values(rest, "tiledlayout"):
        _set_layout_prop(t, k, v)
    m.render(fig)
    return (_h(t.id),) if nargout else ()


def _set_layout_prop(t, k, v):
    key = k.lower()
    if key in ("tilespacing", "padding"):
        table = _SPACING if key == "tilespacing" else _PADDING
        w = (v.text if _is_text(v) else "").lower()
        if w == "normal":
            w = "loose"
        if w not in table:
            raise _err(f"Invalid value for '{k}'.", "MATLAB:hg:InvalidProperty")
        t.props["TileSpacing" if key == "tilespacing" else "Padding"] = w
        for a in _tiles(None, t):
            _place(t, a)
    elif key == "tileindexing":
        t.props["TileIndexing"] = v.text.lower()
    else:
        raise _err(f"Unrecognized property {k} for class TiledChartLayout.", "MATLAB:class:InvalidProperty")


def _occupied(t):
    rows, cols = (int(v) for v in t.props["GridSize"])
    used = set()
    for a in _tiles(None, t):
        r0, c0 = (a.tile - 1) // cols, (a.tile - 1) % cols
        for r in range(r0, r0 + a.tile_span[0]):
            for c in range(c0, c0 + a.tile_span[1]):
                used.add(r * cols + c + 1)
    return used


def _nexttile(ev, args, nargout):
    m = gb.model(ev)
    rest = list(args)
    t = None
    if rest and not _is_text(rest[0]) and hasattr(rest[0], "backend_buffer"):
        h = _arr(rest[0]).reshape(-1)
        if h.size == 1 and m.is_handle(h[0]) and m.get(h[0]).type == "tiledlayout":
            t, rest = m.get(h[0]), rest[1:]
    fig = m.gcf()
    t = t or _layout_of(m, fig)
    if t is None:  # nexttile without a layout creates a flow layout (documented)
        _tiledlayout(ev, [], 0)
        t = _layout_of(m, fig)
    fig = t.parent
    tile, span = None, (1, 1)
    nums = [_arr(v).reshape(-1) for v in rest if not _is_text(v)]
    if len(nums) == 2:
        tile, span = int(nums[0][0]), (int(nums[1][0]), int(nums[1][1]))
    elif len(nums) == 1 and nums[0].size == 2:
        span = (int(nums[0][0]), int(nums[0][1]))
    elif len(nums) == 1:
        tile = int(nums[0][0])
    if min(span) < 1 or (tile is not None and tile < 1):
        raise _err("Tile location must be a positive integer and span a pair of positive integers.",
                   "MATLAB:tiledlayout:InvalidTileLocation")
    flow = t.props["TileArrangement"] != "fixed"
    if flow:  # grow the grid until the requested tile exists
        n = max([tile or 0] + [a.tile for a in _tiles(m, t)] + [len(_occupied(t)) + 1])
        t.props["GridSize"] = _flow_grid(n) if t.props["TileArrangement"] == "flow" else (
            [float(n), 1.0] if t.props["TileArrangement"] == "vertical" else [1.0, float(n)])
    rows, cols = (int(v) for v in t.props["GridSize"])
    if tile is not None:
        for a in _tiles(m, t):
            if a.tile == tile:
                fig.current_axes = a
                m.current_figure = fig
                return (_h(a.id),) if nargout else ()
    else:
        used = _occupied(t)
        tile = next((k for k in range(1, rows * cols + 1)
                     if all((r * cols + c + 1) not in used and r < rows and c < cols
                            for r in range((k - 1) // cols, (k - 1) // cols + span[0])
                            for c in range((k - 1) % cols, (k - 1) % cols + span[1]))), None)
        if tile is None:
            raise _err("Tile location exceeds the number of tiles in the layout.", "MATLAB:tiledlayout:NoEmptyTiles")
    r0, c0 = (tile - 1) // cols, (tile - 1) % cols
    if tile > rows * cols or r0 + span[0] > rows or c0 + span[1] > cols:
        raise _err("Tile location exceeds the number of tiles in the layout.", "MATLAB:tiledlayout:InvalidTileLocation")
    a = m.new_axes(fig)
    a.layout, a.tile, a.tile_span = t, tile, span
    _place(t, a)
    if flow:
        for b in _tiles(m, t):
            _place(t, b)
    m.current_figure = fig
    m.render(fig)
    return (_h(a.id),) if nargout else ()


# --- yyaxis -------------------------------------------------------------------------------------------------

def _yyaxis(ev, args, nargout):
    m = gb.model(ev)
    a, rest = gb._target_axes(m, args)
    a = a or m.gca()
    if len(rest) != 1 or not _is_text(rest[0]) or rest[0].text.lower() not in ("left", "right"):
        raise _err("yyaxis: specify 'left' or 'right'.", "MATLAB:yyaxis:InvalidSide")
    side = rest[0].text.lower()
    if a.props.get("_yyactive") is None:
        for c in a.children:  # existing plots belong to the left side
            c.props.setdefault("_yside", "left")
        a.props["_yy"] = {"left": {}, "right": {"YLim": [0.0, 1.0], "YLimMode": "auto"}}
        a.props["_yyactive"] = "left"
    cur = a.props["_yyactive"]
    if side != cur:
        a.props["_yy"][cur] = {"YLim": a.props["YLim"], "YLimMode": a.props["YLimMode"]}
        nxt = a.props["_yy"][side]
        a.props["YLim"], a.props["YLimMode"] = nxt.get("YLim", [0.0, 1.0]), nxt.get("YLimMode", "auto")
        a.props["_yyactive"] = side
    a.props["YAxisLocation"] = side
    m.autoscale(a)
    gb._render(m, a)
    return ()


# --- subplot geometry and axis modes ----------------------------------------------------------------------

def _subplot(ev, args, nargout):
    m = gb.model(ev)
    f = m.gcf()
    if len(args) >= 2 and _is_text(args[0]) and args[0].text.lower() == "position":
        pos = [float(v) for v in _arr(args[1]).reshape(-1)]
        if len(pos) != 4:
            raise _err("Position must be a 4-element vector.", "MATLAB:subplot:InvalidPosition")
        for a in [x for x in f.children if x.type == "axes" and x.alive]:
            if _overlap(a.props.get("Position", DEFAULT_AXES_POSITION), pos):
                m._delete(a, render=False)
        a = m.new_axes(f)
        a.props["Position"] = pos
        a.props["_rect"] = pos
        m.render(f)
        return (_h(a.id),) if nargout else ()
    if len(args) == 1 and not _is_text(args[0]):
        code = int(_arr(args[0], "subplot").reshape(-1)[0])
        r, c, cells = code // 100, (code // 10) % 10, [code % 10]
    elif len(args) >= 3:
        r, c = (int(_arr(v, "subplot").reshape(-1)[0]) for v in args[:2])
        cells = sorted(int(v) for v in _arr(args[2], "subplot").reshape(-1))
    else:
        raise _err("subplot: expected subplot(m, n, p).", "MATLAB:subplot:InvalidInput")
    if r < 1 or c < 1 or not cells or not all(1 <= p <= r * c for p in cells):
        raise _err("Index exceeds number of subplots.", "MATLAB:subplot:IndexOutOfRange")
    rect = subplot_rect(r, c, cells)
    lo, hi = cells[0], cells[-1]
    key = (r, c, lo) if lo == hi else (r, c, (lo, hi))
    axs = [x for x in f.children if x.type == "axes" and x.alive and getattr(x, "layout", None) is None]
    for a in axs:
        if getattr(a, "position", None) == key:
            f.current_axes = a
            m.render(f)
            return (_h(a.id),) if nargout else ()
    for a in axs:
        if _overlap(a.props.get("Position", DEFAULT_AXES_POSITION), rect):
            m._delete(a, render=False)  # overlapping axes are replaced (documented)
    for t in [x for x in f.children if x.type == "tiledlayout" and x.alive]:
        m._delete(t, render=False)
    a = m.new_axes(f, key)
    a.props["Position"] = rect
    m.render(f)
    return (_h(a.id),) if nargout else ()


_axis_base = gb.INTRINSICS["axis"]


def _axis(ev, args, nargout):
    m = gb.model(ev)
    a, rest = gb._target_axes(m, args)
    a = a or m.gca()
    for v in rest:
        if not _is_text(v):
            continue
        w = v.text.lower()
        if w in ("equal", "image"):
            a.props.update({"DataAspectRatio": [1.0, 1.0, 1.0], "DataAspectRatioMode": "manual"})
        elif w == "square":
            a.props.update({"PlotBoxAspectRatio": [1.0, 1.0, 1.0], "PlotBoxAspectRatioMode": "manual",
                            "DataAspectRatioMode": "auto"})
        elif w == "normal":
            a.props.update({"DataAspectRatioMode": "auto", "PlotBoxAspectRatioMode": "auto"})
        elif w == "ij":
            a.props["YDir"] = "reverse"
        elif w == "xy":
            a.props["YDir"] = "normal"
    out = _axis_base(ev, args, nargout)
    if any(_is_text(v) and v.text.lower() == "image" for v in rest):  # 'image' = 'equal' + tight limits
        xl, yl = m.data_extent(a)
        a.props.update({"XLim": xl, "YLim": yl, "XLimMode": "manual", "YLimMode": "manual"})
        gb._render(m, a)
    return out


# --- property views --------------------------------------------------------------------------------------

_to_value_base = gb._to_value


def _to_value(m, o, key, val):
    if key == "Children" and o.type == "tiledlayout":
        return gb._hcol([c.id for c in reversed(_tiles(m, o))])
    if key == "Children" and o.type == "figure":
        kids = [c for c in o.children if c.alive and c.type != "legend" and getattr(c, "layout", None) is None]
        return gb._hcol([c.id for c in reversed(kids)])
    if key == "Parent" and getattr(o, "layout", None) is not None and o.layout.alive:
        return _h(o.layout.id)
    if key == "Layout" and o.type == "axes":
        from openmatlab.runtime.struct_value import StructValue

        if getattr(o, "layout", None) is None:
            return NDArrayValue(np.zeros((0, 0)))
        return StructValue.scalar([("Tile", NDArrayValue(np.array([[float(o.tile)]]))),
                                   ("TileSpan", NDArrayValue(np.array([[float(o.tile_span[0]), float(o.tile_span[1])]])))])
    return _to_value_base(m, o, key, val)


gb._to_value = _to_value

from openmatlab.libs import chart_builtins as cb  # noqa: E402

cb.KNOWN_PROPS["axes"].setdefault("PlotBoxAspectRatioMode", "auto")
cb.KNOWN_PROPS["axes"].setdefault("Layout", None)

_post_prev = hm.POST_DRAW


def _post(ax, a):
    if _post_prev is not None:
        _post_prev(ax, a)
    if a.props.get("DataAspectRatioMode") == "manual":
        ax.set_aspect("equal", adjustable="box")
    if a.props.get("PlotBoxAspectRatioMode") == "manual":
        try:
            ax.set_box_aspect(1.0)
        except Exception:  # noqa: BLE001 - best-effort rendering
            pass


hm.POST_DRAW = _post

INTRINSICS = {k: gb._wrap(v) for k, v in {
    "tiledlayout": _tiledlayout, "nexttile": _nexttile, "yyaxis": _yyaxis, "subplot": _subplot, "axis": _axis,
}.items()}
