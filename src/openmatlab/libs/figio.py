"""Figure files and export (M13 G-E6 #773): savefig/openfig/hgsave/hgload, exportgraphics, print.

**The ``.fig`` format is OpenMATLAB's own and is not compatible with MATLAB ``.fig`` files** (Shaw's
decision 2026-10-16, M13 doc). A file is a zip archive with two members:

* ``openmatlab-fig.json``: ``{"format": "openmatlab-fig", "version": 1}``.
* ``figure.json``: the property tree of each saved figure. Every object stores its ``Type``, its
  stored properties and its children in creation order. References between objects (``Title``,
  ``XLabel``, legends, the current axes, layout tiles) are encoded as ``{"$ref": n}``. NaN and Inf
  are encoded as strings, so the JSON is standard.

``openfig`` rebuilds the tree with new handles and a new figure number, so the loaded tree has
zero property difference from the saved one apart from handle ids and ``Number``. MATLAB values
stored in ``UserData`` and similar properties are kept when they are numeric, logical or char arrays.
Other MATLAB values (structs, cells, objects) are stored as ``[]`` and listed in the file's
``dropped`` field. A MATLAB ``.fig`` (a MAT file) is rejected with ``MATLAB:openfig:InvalidFile``.

``exportgraphics`` and ``print`` render the figure through Matplotlib at the requested
resolution (``Resolution``, ``-rN``; 150 dpi by default for both). A figure without a heatmap
exports at ``Position`` in pixels / ``ScreenPixelsPerInch``. A heatmap figure keeps the canvas
the renderer already sized for the category labels (13.5 by 8 inches when it also has a tiled
layout). ``exportgraphics`` then crops to a padded tight box so the layout title, colorbar
labels and footnote stay inside the page. ``print`` keeps the canvas unless an artist extends
past it, in which case the page grows to include that artist. An axes export includes that
axes' colorbar.
"""

from __future__ import annotations

import json
import math
import os
import zipfile
from typing import Any, Dict, List, Optional

import numpy as np

from openmatlab.graphics.handle_model import GObj
from openmatlab.libs import graphics_builtins as gb
from openmatlab.numerics.ndarray_value import NDArrayValue

_err, _arr, _is_text, _is_cell = gb._err, gb._arr, gb._is_text, gb._is_cell

FORMAT = "openmatlab-fig"
VERSION = 1
_SKIP_ATTRS = {"id", "type", "parent", "children", "props", "alive", "_ruler_objs"}


# ------------------------------------------------------------------ encode
class _Enc:
    def __init__(self):
        self.dropped: List[str] = []

    def val(self, v, where: str):
        if isinstance(v, GObj):
            return {"$ref": v.id}
        if isinstance(v, bool) or v is None or isinstance(v, str):
            return v
        if isinstance(v, (int, np.integer)):
            return int(v)
        if isinstance(v, (float, np.floating)):
            f = float(v)
            return f if math.isfinite(f) else {"$num": repr(f)}
        if isinstance(v, dict):
            return {"$dict": {str(k): self.val(x, where) for k, x in v.items()}}
        if isinstance(v, tuple):
            return {"$tuple": [self.val(x, where) for x in v]}
        if isinstance(v, list):
            return [self.val(x, where) for x in v]
        if isinstance(v, np.ndarray):
            return {"$nd": self.val(v.tolist(), where)}
        mv = self.matlab(v)
        if mv is not None:
            return mv
        self.dropped.append(where)
        return None

    def matlab(self, v):
        from openmatlab.runtime.char_value import CharValue

        if isinstance(v, CharValue):
            return {"$char": v.text}
        if hasattr(v, "backend_buffer") and not getattr(v, "is_graphics_handle", False):
            try:
                b = np.asarray(v.backend_buffer())
            except Exception:  # noqa: BLE001 - not an array value
                return None
            if b.dtype.kind in "biuf":
                return {"$array": self.val(b.astype(float).tolist() if b.dtype.kind != "b" else b.tolist(), ""),
                        "shape": list(b.shape), "class": "logical" if b.dtype.kind == "b" else str(b.dtype)}
        return None


def _encode_obj(enc: _Enc, o: GObj) -> Dict[str, Any]:
    props = {k: enc.val(v, f"{o.type}.{k}") for k, v in o.props.items() if k not in ("_rendered",)}
    attrs = {k: enc.val(v, f"{o.type}.{k}") for k, v in o.__dict__.items() if k not in _SKIP_ATTRS}
    return {"id": o.id, "type": o.type, "props": props, "attrs": attrs,
            "children": [_encode_obj(enc, c) for c in o.children if c.alive]}


def save_figures(m, figs: List[GObj], path: str) -> None:
    enc = _Enc()
    for f in figs:
        f.props["FileName"] = os.path.abspath(path)
    tree = [_encode_obj(enc, f) for f in figs]
    # a legend or a referenced text may live outside Children (Title/XLabel...); store referenced orphans too
    seen = set()

    def walk(n):
        seen.add(n["id"])
        for c in n["children"]:
            walk(c)
    for n in tree:
        walk(n)
    extra = []
    for f in figs:
        for o in _all_refs(f):
            if o.id not in seen and o.alive:
                seen.add(o.id)
                extra.append({"parent": o.parent.id if o.parent is not None else None, **_encode_obj(enc, o)})
    doc = {"figures": tree, "orphans": extra, "dropped": sorted(set(enc.dropped))}
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("openmatlab-fig.json", json.dumps({"format": FORMAT, "version": VERSION}))
            z.writestr("figure.json", json.dumps(doc))
    except OSError as e:
        raise _err(f"Unable to write file {path}: {e.strerror or e}.", "MATLAB:savefig:FileNotWritable") from None


def _all_refs(f: GObj):
    out = []

    def scan(v):
        if isinstance(v, GObj):
            out.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                scan(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                scan(x)

    def walk(o):
        for v in list(o.props.values()) + [v for k, v in o.__dict__.items() if k not in _SKIP_ATTRS]:
            scan(v)
        for c in o.children:
            walk(c)
    walk(f)
    return out


# ------------------------------------------------------------------ decode
class _Dec:
    def __init__(self, m):
        self.m = m
        self.map: Dict[float, GObj] = {}
        self.fix: List[tuple] = []

    def val(self, v):
        if isinstance(v, list):
            return [self.val(x) for x in v]
        if not isinstance(v, dict):
            return v
        if "$ref" in v:
            return _Ref(v["$ref"])
        if "$num" in v:
            return float(v["$num"])
        if "$dict" in v:
            return {k: self.val(x) for k, x in v["$dict"].items()}
        if "$tuple" in v:
            return tuple(self.val(x) for x in v["$tuple"])
        if "$nd" in v:
            return np.asarray(self.val(v["$nd"]))
        if "$char" in v:
            from openmatlab.runtime.char_value import CharValue

            return CharValue(v["$char"])
        if "$array" in v:
            a = np.asarray(self.val(v["$array"]), dtype=bool if v.get("class") == "logical" else float)
            return NDArrayValue(a.reshape(v.get("shape") or a.shape))
        raise ValueError("bad value")

    def obj(self, n, parent: Optional[GObj]) -> GObj:
        hid = self.m._new_id() if n["type"] != "figure" else None
        o = GObj(hid if hid is not None else 0.0, n["type"], parent, {})
        o.props = {k: self.val(v) for k, v in n["props"].items()}
        for k, v in n.get("attrs", {}).items():
            setattr(o, k, self.val(v))
        self.map[float(n["id"])] = o
        if hid is not None:
            self.m.objs[o.id] = o
        for c in n.get("children", []):
            o.children.append(self.obj(c, o))
        return o

    def resolve(self, v):
        if isinstance(v, _Ref):
            return self.map.get(float(v.id))
        if isinstance(v, dict):
            return {k: self.resolve(x) for k, x in v.items()}
        if isinstance(v, tuple):
            return tuple(self.resolve(x) for x in v)
        if isinstance(v, list):
            return [self.resolve(x) for x in v]
        return v


class _Ref:
    __slots__ = ("id",)

    def __init__(self, i):
        self.id = i


def _read(path: str) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            head = json.loads(z.read("openmatlab-fig.json"))
            if head.get("format") != FORMAT:
                raise KeyError
            if int(head.get("version", 0)) > VERSION:
                raise _err(f"openfig: {path} was written by a newer OpenMATLAB (format version {head['version']}).",
                           "MATLAB:openfig:InvalidFile")
            return json.loads(z.read("figure.json"))
    except (zipfile.BadZipFile, KeyError, ValueError, UnicodeDecodeError):
        raise _err(f"openfig: '{path}' is not an OpenMATLAB figure file. OpenMATLAB .fig files use their own format; "
                   "MATLAB .fig files are not supported.", "MATLAB:openfig:InvalidFile") from None
    except OSError as e:
        raise _err(f"openfig: unable to read '{path}': {e.strerror or e}.", "MATLAB:openfig:FileNotFound") from None


def load_figures(m, path: str, visible: Optional[str]) -> List[GObj]:
    doc = _read(path)
    dec = _Dec(m)
    figs = []
    try:
        for n in doc.get("figures", []):
            used = {int(f.id) for f in m.figures()}
            number = next(i for i in range(1, 10 ** 6) if i not in used)
            f = dec.obj(n, m.root)
            f.id = float(number)
            f.props["Number"] = float(number)
            m.objs[f.id] = f
            m.root.children.append(f)
            figs.append(f)
        for n in doc.get("orphans", []):
            p = dec.map.get(float(n["parent"])) if n.get("parent") is not None else None
            dec.obj(n, p)
        for o in dec.map.values():
            o.props = {k: dec.resolve(v) for k, v in o.props.items()}
            for k, v in list(o.__dict__.items()):
                if k not in _SKIP_ATTRS:
                    setattr(o, k, dec.resolve(v))
    except (KeyError, TypeError, ValueError):
        for f in figs:
            m._delete(f, render=False)
        raise _err(f"openfig: '{path}' is a damaged OpenMATLAB figure file.", "MATLAB:openfig:InvalidFile") from None
    for f in figs:
        if not hasattr(f, "current_axes"):
            f.current_axes = None
        f.props["FileName"] = os.path.abspath(path)
        f.props.pop("_rendered", None)
        if visible is not None:
            f.props["Visible"] = visible
        m.current_figure = f
        m.render(f)
    return figs


# ------------------------------------------------------------------ builtins
def _path_arg(v, fn) -> str:
    if not _is_text(v):
        raise _err(f"{fn}: file name must be a character vector or string scalar.", f"MATLAB:{fn}:InvalidFileName")
    return v.text


def _with_ext(p: str, ext: str) -> str:
    return p if os.path.splitext(os.path.basename(p))[1] else p + ext


def _figs_of(m, v, fn) -> List[GObj]:
    out = []
    for i in _arr(v, fn).reshape(-1, order="F"):
        if not m.is_handle(i) or m.get(i).type != "figure":
            raise _err(f"{fn}: the first argument must be a valid figure handle.", f"MATLAB:{fn}:InvalidHandle")
        out.append(m.get(i))
    return out


def _savefig(ev, args, nargout):
    m = gb.model(ev)
    args = [a for a in args if not (_is_text(a) and a.text.lower() == "compact")]
    if args and not _is_text(args[0]):
        figs = _figs_of(m, args.pop(0), "savefig")
    else:
        figs = [m.gcf()]
    path = _with_ext(_path_arg(args[0], "savefig") if args else "Untitled.fig", ".fig")
    if len(args) > 1:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    save_figures(m, figs, path)
    return ()


def _resolve_file(path: str, fn: str) -> str:
    for cand in (path, _with_ext(path, ".fig")):
        if os.path.isfile(cand):
            return cand
    raise _err(f"{fn}: file '{path}' not found.", f"MATLAB:{fn}:FileNotFound")


def _openfig(ev, args, nargout):
    m = gb.model(ev)
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    path = _resolve_file(_path_arg(args[0], "openfig"), "openfig")
    mode, vis = "new", None
    for a in args[1:]:
        w = a.text.lower() if _is_text(a) else None
        if w in ("new", "reuse"):
            mode = w
        elif w in ("visible", "invisible"):
            vis = "on" if w == "visible" else "off"
        else:
            raise _err("openfig: options are 'new', 'reuse', 'visible' and 'invisible'.", "MATLAB:openfig:InvalidOption")
    if mode == "reuse":
        full = os.path.abspath(path)
        same = [f for f in m.figures() if f.props.get("FileName") == full]
        if same:
            if vis is not None:
                same[-1].props["Visible"] = vis
            m.current_figure = same[-1]
            return (gb._h(same[-1].id),) if nargout else ()
    figs = load_figures(m, path, vis)
    out = gb._h(figs[0].id) if len(figs) == 1 else gb._hcol([f.id for f in figs])
    return (out,) if nargout else ()


def _hgsave(ev, args, nargout):
    return _savefig(ev, args, nargout)


def _hgload(ev, args, nargout):
    m = gb.model(ev)
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    path = _resolve_file(_path_arg(args[0], "hgload"), "hgload")
    figs = load_figures(m, path, None)
    return (gb._h(figs[0].id) if len(figs) == 1 else gb._hcol([f.id for f in figs]),)


# ------------------------------------------------------------------ export
_EXPORT_FORMATS = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "tif": "tiff", "tiff": "tiff", "gif": "gif",
                   "pdf": "pdf", "eps": "eps", "svg": "svg"}


def _figure_inches(m, f: GObj):
    from openmatlab.libs import axes_props as ap

    w, h = ap.figure_px(m, f)
    ppi = float(m.root.props.get("ScreenPixelsPerInch", 96.0))
    return max(w, 1.0) / ppi, max(h, 1.0) / ppi


# Inches of white kept around a tight crop so a title, colorbar tick or footnote
# is not shaved by the page edge. print uses the same pad only when it has to grow.
_CROP_PAD_IN = 0.16
_OVERFLOW_EPS_IN = 0.02


def _heatmap_canvas(f: GObj) -> bool:
    return any(c.alive and c.type == "axes" and c.props.get("_Heatmap") == "on" for c in f.children)


def _as_inches(mfig, bb):
    """Artist boxes come back in pixels; the figure tight box is already in inches."""
    from matplotlib.transforms import Bbox, TransformedBbox

    if bb is None:
        return None
    ext = bb.extents if isinstance(bb, TransformedBbox) else bb.transformed(mfig.dpi_scale_trans.inverted()).extents
    ext = [float(v) for v in ext]
    if not all(math.isfinite(v) for v in ext):
        return None
    return Bbox.from_extents(*ext)


def _content_bbox(mfig):
    mfig.canvas.draw()
    return _as_inches(mfig, mfig.get_tightbbox(mfig.canvas.get_renderer()))


def _panel_axes(mfig):
    """Matplotlib axes that correspond to graphics axes. Colorbar axes are extra."""
    caxes = set()
    for ax in mfig.axes:
        for im in list(getattr(ax, "images", [])):
            cbar = getattr(im, "colorbar", None)
            cax = getattr(cbar, "ax", None) if cbar is not None else None
            if cax is not None:
                caxes.add(cax)
    return [ax for ax in mfig.axes if ax not in caxes]


def _axes_bbox(mfig, ax, pad: float):
    """The axes plus its colorbar, in inches. A bare axes has no colorbar."""
    from matplotlib.transforms import Bbox

    renderer = mfig.canvas.get_renderer()
    boxes = []
    bb = _as_inches(mfig, ax.get_tightbbox(renderer))
    if bb is not None:
        boxes.append(bb)
    seen = set()
    for artist in list(getattr(ax, "images", [])) + list(getattr(ax, "collections", [])):
        cbar = getattr(artist, "colorbar", None)
        cax = getattr(cbar, "ax", None) if cbar is not None else None
        if cax is None or id(cax) in seen:
            continue
        seen.add(id(cax))
        cb = _as_inches(mfig, cax.get_tightbbox(renderer))
        if cb is not None:
            boxes.append(cb)
    if not boxes:
        return None
    return Bbox.union(boxes).padded(pad)


def _export_bbox(mfig, o: GObj, f: GObj, crop: bool):
    """Page box in inches, or None to keep the canvas (print of a figure that fits)."""
    if crop and o.type == "axes":
        panels = _panel_axes(mfig)
        idx = [c for c in f.children if c.type == "axes" and c.alive].index(o)
        if idx < len(panels):
            mfig.canvas.draw()
            boxed = _axes_bbox(mfig, panels[idx], 0.05)
            if boxed is not None:
                return boxed
    content = _content_bbox(mfig)
    if content is None:
        return None
    if crop:
        return content.padded(_CROP_PAD_IN)
    w, h = (float(v) for v in mfig.get_size_inches())
    sticks_out = (content.x0 < -_OVERFLOW_EPS_IN or content.y0 < -_OVERFLOW_EPS_IN
                  or content.x1 > w + _OVERFLOW_EPS_IN or content.y1 > h + _OVERFLOW_EPS_IN)
    if sticks_out:
        return content.padded(_CROP_PAD_IN)
    return None


def render_to_file(m, o: GObj, path: str, fmt: str, dpi: float, background=None, crop_axes: bool = False) -> None:
    f = m.figure_of(o)
    be = m.backend
    if f is None or be is None or not hasattr(be, "render_figure"):
        raise _err("No graphics backend available.", "MATLAB:print:noBackend")
    m.render(f)
    mfig = be._figures[int(f.id) - 1] if 0 < int(f.id) <= len(getattr(be, "_figures", [])) else None
    if mfig is None:
        raise _err("The figure is not open.", "MATLAB:print:InvalidFigure")
    old = mfig.get_size_inches().copy()
    kw: Dict[str, Any] = {"format": "jpeg" if fmt == "jpeg" else fmt, "dpi": float(dpi)}
    if background == "none":
        kw["transparent"] = True
    elif isinstance(background, list):
        kw["facecolor"] = background
    else:
        col = f.props.get("Color")
        kw["facecolor"] = col if isinstance(col, list) and len(col) == 3 else "white"
        if background == "white" or f.props.get("InvertHardcopy", "on") == "on":
            kw["facecolor"] = "white"
    try:
        # Heatmap layout (category labels, colorbar, footnote) is drawn on the
        # canvas FIGURE_PRE sized. Squashing that back to the default Position
        # piles the labels on top of each other and clips the colorbar.
        if not _heatmap_canvas(f):
            mfig.set_size_inches(*_figure_inches(m, f))
        boxed = _export_bbox(mfig, o, f, crop_axes)
        if boxed is not None:
            kw["bbox_inches"] = boxed
        if fmt == "gif":
            import io

            from PIL import Image

            buf = io.BytesIO()
            kw["format"] = "png"
            mfig.savefig(buf, **kw)
            buf.seek(0)
            Image.open(buf).convert("P").save(path, format="GIF")
        else:
            mfig.savefig(path, **kw)
    except OSError as e:
        raise _err(f"Unable to write file {path}: {e.strerror or e}.", "MATLAB:print:FileWriteError") from None
    finally:
        mfig.set_size_inches(*old)


def _exportgraphics(ev, args, nargout):
    m = gb.model(ev)
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    hs = gb._handles(m, args[0], "exportgraphics")
    if len(hs) != 1 or hs[0].type not in ("figure", "axes", "tiledlayout", "legend", "colorbar"):
        raise _err("exportgraphics: first argument must be a figure, axes or tiled chart layout.",
                   "MATLAB:exportgraphics:InvalidObject")
    o = hs[0]
    path = _path_arg(args[1], "exportgraphics")
    ext = os.path.splitext(path)[1][1:].lower()
    if ext not in _EXPORT_FORMATS:
        raise _err(f"exportgraphics: unsupported file extension '.{ext}' (use .png, .jpg, .tif, .gif, .pdf, .eps or .svg).",
                   "MATLAB:exportgraphics:InvalidFileExtension")
    opts = {"resolution": 150.0, "background": None, "contenttype": "auto", "append": False}
    nv = gb._name_values(list(args[2:]), "exportgraphics")
    for k, v in nv:
        k = k.lower()
        if k == "resolution":
            r = _arr(v, "exportgraphics").reshape(-1)
            if r.size != 1 or not r[0] > 0:
                raise _err("exportgraphics: 'Resolution' must be a positive scalar.", "MATLAB:exportgraphics:InvalidResolution")
            opts["resolution"] = float(r[0])
        elif k == "backgroundcolor":
            if _is_text(v) and v.text.lower() in ("none", "current", "white"):
                opts["background"] = v.text.lower() if v.text.lower() != "current" else "current"
            else:
                opts["background"] = gb._color(v, "exportgraphics")
        elif k == "contenttype":
            if not _is_text(v) or v.text.lower() not in ("auto", "vector", "image"):
                raise _err("exportgraphics: 'ContentType' must be 'auto', 'vector' or 'image'.",
                           "MATLAB:exportgraphics:InvalidContentType")
        elif k == "append":
            if bool(np.ravel(_arr(v, "exportgraphics"))[0]):
                raise _err("exportgraphics: 'Append' is not supported.", "MATLAB:exportgraphics:AppendNotSupported")
        elif k in ("colorspace", "padding"):
            continue
        else:
            raise _err(f"exportgraphics: unknown parameter '{k}'.", "MATLAB:exportgraphics:InvalidParameter")
    bg = opts["background"]
    if bg is None:
        bg = "white"
    elif bg == "current":
        bg = None
    render_to_file(m, o, path, _EXPORT_FORMATS[ext], opts["resolution"], background=bg,
                   crop_axes=True)  # exportgraphics crops tightly to the content (MATLAB)
    return ()


_PRINT_DEVICES = {"png": ("png", ".png"), "jpeg": ("jpeg", ".jpg"), "jpg": ("jpeg", ".jpg"), "tiff": ("tiff", ".tif"),
                  "tiffn": ("tiff", ".tif"), "pdf": ("pdf", ".pdf"), "eps": ("eps", ".eps"), "epsc": ("eps", ".eps"),
                  "eps2": ("eps", ".eps"), "epsc2": ("eps", ".eps"), "svg": ("svg", ".svg"), "meta": None,
                  "bmp": None}


def _print(ev, args, nargout):
    """print(fig, filename, formattype, '-rN', ...) / print -dpng file / print(filename)."""
    m = gb.model(ev)
    fig, dev, fname, dpi = None, None, None, 150.0
    for a in args:
        if _is_text(a):
            t = a.text
            if t.startswith("-d"):
                dev = t[2:].lower()
            elif t.startswith("-r"):
                try:
                    dpi = float(t[2:])
                except ValueError:
                    raise _err(f"print: invalid resolution '{t}'.", "MATLAB:print:InvalidResolution") from None
                if dpi <= 0:
                    dpi = 96.0  # -r0: screen resolution (MATLAB)
            elif t.startswith("-f"):
                try:
                    fig = gb._h(float(t[2:]))
                except ValueError:
                    raise _err(f"print: invalid figure option '{t}'.", "MATLAB:print:InvalidFigure") from None
            elif t in ("-clipboard",) or t.startswith("-P"):
                raise _err("print: printing to a printer or the clipboard is not supported; give a file name.",
                           "MATLAB:print:NoPrinter")
            elif t.startswith("-"):
                continue  # -painters, -opengl, -vector, -image, -loose, -noui, -fillpage, -bestfit
            else:
                fname = t
        else:
            fig = a
    if fname is None:
        raise _err("print: printing to a printer is not supported; give a file name.", "MATLAB:print:NoPrinter")
    if dev is None:
        ext = os.path.splitext(os.path.basename(fname))[1][1:].lower()
        dev = {"jpg": "jpeg", "tif": "tiff"}.get(ext, ext) or "png"
    if dev not in _PRINT_DEVICES or _PRINT_DEVICES[dev] is None:
        raise _err(f"print: unsupported device '-d{dev}'.", "MATLAB:print:InvalidDevice")
    fmt, ext = _PRINT_DEVICES[dev]
    if not os.path.splitext(os.path.basename(fname))[1]:
        fname += ext
    o = gb._handles(m, fig, "print")[0] if fig is not None else m.gcf()
    o = m.figure_of(o) or o
    render_to_file(m, o, fname, fmt, dpi)
    return ()


INTRINSICS = {k: gb._wrap(v) for k, v in {
    "savefig": _savefig, "openfig": _openfig, "hgsave": _hgsave, "hgload": _hgload,
    "exportgraphics": _exportgraphics, "print": _print,
}.items()}
STATEMENT_ZERO = {"savefig", "hgsave", "exportgraphics", "print"}
