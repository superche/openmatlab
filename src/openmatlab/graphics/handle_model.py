"""MATLAB handle-graphics object model (Epic #537).

The object tree (root 0 -> figures -> axes -> line/bar/scatter/histogram/
text, plus legends) is the source of truth. Handles are doubles: a figure's
handle is its Number; every other object gets a unique non-integer id, so a
figure and a line can never alias. ``get``/``set`` work on this tree with
case-insensitive property names. After each change the touched figure is
re-rendered through the session's GraphicsBackend (matplotlib Agg in CI),
so ``saveas`` and the desktop figure list see what the model says.
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional

import numpy as np

# MATLAB's default axes ColorOrder (R2014b+)
COLOR_ORDER = np.array([
    [0, 0.4470, 0.7410], [0.8500, 0.3250, 0.0980], [0.9290, 0.6940, 0.1250],
    [0.4940, 0.1840, 0.5560], [0.4660, 0.6740, 0.1880], [0.3010, 0.7450, 0.9330],
    [0.6350, 0.0780, 0.1840],
])
SPEC_COLORS = {"r": [1, 0, 0], "g": [0, 1, 0], "b": [0, 0, 1], "c": [0, 1, 1], "m": [1, 0, 1],
               "y": [1, 1, 0], "k": [0, 0, 0], "w": [1, 1, 1]}
SPEC_STYLES = ("--", "-.", "-", ":")
SPEC_MARKERS = "o+*.xsd^v<>ph"
CLASS_NAMES = {"root": "Root", "figure": "Figure", "axes": "Axes", "line": "Line", "bar": "Bar",
               "scatter": "Scatter", "histogram": "Histogram", "text": "Text", "legend": "Legend"}


class GraphicsError(Exception):
    def __init__(self, msg, ident=""):
        super().__init__(msg)
        self.identifier = ident


class GObj:
    def __init__(self, hid: float, typ: str, parent: Optional["GObj"], props: Dict[str, Any]):
        self.id = hid
        self.type = typ
        self.parent = parent
        self.children: List[GObj] = []  # creation order; MATLAB lists newest first
        self.props = {"Type": typ}
        self.props.update(props)
        self.alive = True


def parse_linespec(s: str):
    """'r--o' -> (color|None, style|None, marker|None); None when not a LineSpec."""
    color = style = marker = None
    i = 0
    while i < len(s):
        two = s[i:i + 2]
        if two in ("--", "-."):
            if style:
                return None
            style, i = two, i + 2
            continue
        ch = s[i]
        if ch in "-:":
            if style:
                return None
            style = ch
        elif ch in SPEC_COLORS:
            if color:
                return None
            color = ch
        elif ch in SPEC_MARKERS:
            if marker:
                return None
            marker = ch
        else:
            return None
        i += 1
    return color, style, marker


class Model:
    def __init__(self) -> None:
        self.objs: Dict[float, GObj] = {}
        self.root = GObj(0.0, "root", None, {"CurrentFigure": None})
        self.objs[0.0] = self.root
        self._ids = itertools.count(1)
        self.current_figure: Optional[GObj] = None
        self.backend: Any = None

    # ------------------------------------------------------------ ids / lookup
    def _new_id(self) -> float:
        return 1000.0 + next(self._ids) + 0.0137  # never an integer -> never a figure number

    def get(self, hid: float) -> GObj:
        o = self.objs.get(float(hid))
        if o is None or not o.alive:
            raise GraphicsError("Invalid or deleted object.", "MATLAB:class:InvalidHandle")
        return o

    def is_handle(self, hid: float) -> bool:
        o = self.objs.get(float(hid))
        return o is not None and o.alive

    def sync_backend(self) -> None:
        """Drop figures the host closed directly (desktop figure manager)."""
        be = self.backend
        figs = getattr(be, "_figures", None)
        if figs is None:
            return
        for f in list(self.figures()):
            idx = int(f.id) - 1
            if f.props.get("_rendered") and (idx >= len(figs) or figs[idx] is None):
                self._delete(f, render=False)

    # ------------------------------------------------------------ tree
    def figures(self) -> List[GObj]:
        return [c for c in self.root.children if c.alive]

    def new_figure(self, number: Optional[int] = None) -> GObj:
        if number is None:
            used = {int(f.id) for f in self.figures()}
            number = next(n for n in itertools.count(1) if n not in used)
        f = GObj(float(number), "figure", self.root, {
            "Number": float(number), "Name": "", "Color": [0.94, 0.94, 0.94],
            "Visible": "on", "NumberTitle": "on"})
        f.current_axes = None
        self.objs[f.id] = f
        self.root.children.append(f)
        self.current_figure = f
        return f

    def gcf(self) -> GObj:
        self.sync_backend()
        if self.current_figure is None or not self.current_figure.alive:
            figs = self.figures()
            self.current_figure = figs[-1] if figs else self.new_figure()
        return self.current_figure

    def new_axes(self, fig: GObj, position=None) -> GObj:
        a = GObj(self._new_id(), "axes", fig, {})
        a.position = position
        self._reset_axes(a, keep_position=False)
        self.objs[a.id] = a
        fig.children.append(a)
        fig.current_axes = a
        return a

    def _text(self, parent: GObj, s: str = "") -> GObj:
        t = GObj(self._new_id(), "text", parent, {"String": s, "FontSize": 11.0, "Color": [0.15, 0.15, 0.15]})
        self.objs[t.id] = t
        return t

    def _reset_axes(self, a: GObj, keep_position=True) -> None:
        for c in list(a.children):
            self._delete(c, render=False)
        a.children = []
        for k in ("Title", "XLabel", "YLabel"):
            old = a.props.get(k)
            if old is not None:
                old.alive = False
        if keep_position:  # replace-mode plotting resets the stored axes properties (#772); keep the layout ones
            for k in list(a.props):
                if k in RESET_ON_REPLACE:
                    del a.props[k]
        a.props.update({
            "Title": self._text(a), "XLabel": self._text(a), "YLabel": self._text(a),
            "XGrid": "off", "YGrid": "off", "Box": "on", "NextPlot": a.props.get("NextPlot", "replace") if keep_position else "replace",
            "XLimMode": "auto", "YLimMode": "auto", "XLim": [0.0, 1.0], "YLim": [0.0, 1.0],
            "ColorOrderIndex": 1.0, "Visible": "on",
        })
        a.legend = None

    def gca(self) -> GObj:
        f = self.gcf()
        a = getattr(f, "current_axes", None)
        if a is None or not a.alive:
            axs = [c for c in f.children if c.type == "axes" and c.alive]
            a = axs[-1] if axs else self.new_axes(f)
            f.current_axes = a
        return a

    def _delete(self, o: GObj, render=True) -> None:
        for c in list(o.children):
            self._delete(c, render=False)
        o.alive = False
        if o.parent is not None and o in o.parent.children:
            o.parent.children.remove(o)
        if o.type == "figure":
            if self.backend is not None and o.props.get("_rendered"):
                try:
                    self.backend.close(o.id)
                except Exception:
                    pass
            if self.current_figure is o:
                figs = self.figures()
                self.current_figure = figs[-1] if figs else None
        elif o.type == "axes":
            f = o.parent
            if getattr(f, "current_axes", None) is o:
                axs = [c for c in f.children if c.type == "axes" and c.alive]
                f.current_axes = axs[-1] if axs else None
            if render:
                self.render(f)
        elif render:
            self.render(self.figure_of(o))

    def delete(self, o: GObj) -> None:
        self._delete(o)

    def figure_of(self, o: GObj) -> Optional[GObj]:
        while o is not None and o.type != "figure":
            o = o.parent
        return o

    def next_color(self, a: GObj):
        i = int(a.props["ColorOrderIndex"]) - 1
        a.props["ColorOrderIndex"] = float((i + 1) % len(COLOR_ORDER) + 1)
        return COLOR_ORDER[i % len(COLOR_ORDER)].tolist()

    def prepare_axes_for_plot(self, a: GObj) -> None:
        if a.props["NextPlot"] == "replace":
            self._reset_axes(a)

    def add_child(self, a: GObj, typ: str, props: Dict[str, Any]) -> GObj:
        o = GObj(self._new_id(), typ, a, props)
        self.objs[o.id] = o
        a.children.append(o)
        self.autoscale(a)
        return o

    # ------------------------------------------------------------ limits
    def data_extent(self, a: GObj):
        xs, ys = [], []
        for c in a.children:
            if not c.alive:
                continue
            if c.type in ("line", "scatter"):
                xs.append(np.asarray(c.props["XData"], float).ravel())
                ys.append(np.asarray(c.props["YData"], float).ravel())
            elif c.type == "bar":
                x = np.asarray(c.props["XData"], float).ravel()
                w = float(c.props.get("BarWidth", 0.8)) / 2
                xs.append(np.concatenate([x - w, x + w]))
                ys.append(np.concatenate([np.asarray(c.props["YData"], float).ravel(), [0.0]]))
            elif c.type == "histogram":
                xs.append(np.asarray(c.props["BinEdges"], float).ravel())
                ys.append(np.concatenate([np.asarray(c.props["Values"], float).ravel(), [0.0]]))
            elif c.type == "image":
                xd, yd = c.props.get("XData") or [], c.props.get("YData") or []
                if len(xd) and len(yd):
                    xs.append(np.array([min(xd) - 0.5, max(xd) + 0.5]))
                    ys.append(np.array([min(yd) - 0.5, max(yd) + 0.5]))
            elif c.type == "rectangle":
                x, y, w, h = (list(c.props.get("Position", [0, 0, 1, 1])) + [1] * 4)[:4]
                xs.append(np.array([x, x + w], float))
                ys.append(np.array([y, y + h], float))
            elif c.type != "text" and "XData" in c.props and "YData" in c.props:  # Epic #772 charts
                try:
                    x = np.asarray(c.props["XData"], float).ravel()
                    y = np.asarray(c.props["YData"], float).ravel()
                except (TypeError, ValueError):
                    continue
                if c.type == "errorbar":
                    lo = np.asarray(c.props.get("YNegativeDelta") or 0.0, float).ravel()
                    hi = np.asarray(c.props.get("YPositiveDelta") or 0.0, float).ravel()
                    y = np.concatenate([y - lo, y + hi]) if lo.size in (1, y.size) and hi.size in (1, y.size) else y
                if c.type in ("stem", "area"):
                    y = np.concatenate([y, [float(c.props.get("BaseValue", 0.0))]])
                if c.type == "quiver":
                    x = np.concatenate([x, x + np.asarray(c.props.get("UData") or [], float).ravel()[: x.size]])
                    y = np.concatenate([y, y + np.asarray(c.props.get("VData") or [], float).ravel()[: y.size]])
                xs.append(x)
                ys.append(y)
        def rng(parts):
            v = np.concatenate(parts) if parts else np.array([])
            v = v[np.isfinite(v)]
            if v.size == 0:
                return [0.0, 1.0]
            lo, hi = float(v.min()), float(v.max())
            if lo == hi:
                lo, hi = lo - 1.0, hi + 1.0
            return [lo, hi]
        return rng(xs), rng(ys)

    def autoscale(self, a: GObj) -> None:
        xl, yl = self.data_extent(a)
        if a.props["XLimMode"] == "auto":
            a.props["XLim"] = xl
        if a.props["YLimMode"] == "auto":
            a.props["YLim"] = yl

    # ------------------------------------------------------------ rendering
    def render(self, fig: Optional[GObj]) -> None:
        be = self.backend
        if fig is None or not fig.alive or be is None or not hasattr(be, "render_figure"):
            return
        be.render_figure(int(fig.id), lambda mfig: draw_figure(self, fig, mfig))
        fig.props["_rendered"] = True


RESET_ON_REPLACE = {"XScale", "YScale", "XDir", "YDir", "CLim", "CLimMode", "XTick", "YTick", "XTickLabel",
                    "YTickLabel", "XTickMode", "YTickMode", "ZLim", "View", "ZLabel"}
EXTRA_DRAW = None  # chart types of Epic #772 (set by openmatlab.libs.chart_builtins)
POST_DRAW = None


def _style(s):
    return {"none": "None"}.get(s, s)


def draw_figure(model: Model, fig: GObj, mfig) -> None:
    mfig.clear()
    for a in fig.children:
        if a.type != "axes" or not a.alive:
            continue
        pos = getattr(a, "position", None)
        ax = mfig.add_subplot(*pos) if pos else mfig.add_subplot(1, 1, 1)
        for c in a.children:
            if not c.alive:
                continue
            p = c.props
            label = p.get("DisplayName") or None
            try:
                if c.type == "line":
                    mk = p.get("Marker", "none")
                    ax.plot(np.ravel(p["XData"]), np.ravel(p["YData"]), color=p["Color"],
                            linestyle=_style(p["LineStyle"]), linewidth=float(p["LineWidth"]),
                            marker=None if mk == "none" else mk, label=label)
                elif c.type == "bar":
                    ax.bar(np.ravel(p["XData"]), np.ravel(p["YData"]), width=float(p["BarWidth"]),
                           color=p["FaceColor"], label=label)
                elif c.type == "scatter":
                    ax.scatter(np.ravel(p["XData"]), np.ravel(p["YData"]), s=float(np.ravel(p["SizeData"])[0]),
                               color=p["CData"], label=label)
                elif c.type == "histogram":
                    e = np.ravel(p["BinEdges"])
                    ax.bar(e[:-1], np.ravel(p["Values"]), width=np.diff(e), align="edge",
                           color=p["FaceColor"], edgecolor="k", label=label)
                elif EXTRA_DRAW is not None:
                    try:
                        EXTRA_DRAW(ax, c, model)
                    except Exception:  # best-effort rendering never fails the script (#772)
                        pass
            except Exception:  # best-effort rendering never fails the script (#772)
                pass
        ax.set_title(a.props["Title"].props["String"])
        ax.set_xlabel(a.props["XLabel"].props["String"])
        ax.set_ylabel(a.props["YLabel"].props["String"])
        ax.grid(a.props["XGrid"] == "on" or a.props["YGrid"] == "on")
        ax.set_xlim(*a.props["XLim"])
        ax.set_ylim(*a.props["YLim"])
        if a.props.get("Visible") == "off":
            ax.set_axis_off()
        if POST_DRAW is not None:
            try:
                POST_DRAW(ax, a)
            except Exception:
                pass
        if a.legend is not None and a.legend.alive:
            names = list(a.legend.props["String"])
            if names:
                ax.legend(names[: len(ax.lines) + len(ax.collections) + len(ax.containers)] or names)
