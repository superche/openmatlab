"""Graphics object queries (Epic #769, M13 G-E2: G02).

findobj findall allchild ancestor groot gco. Traversal is depth-first, a parent
before its children, and children in MATLAB ``Children`` order (newest first).
``findobj`` skips objects whose ``HandleVisibility`` is not ``'on'``; ``findall``
does not. Property matching is case-insensitive on names; text values compare
exactly (``-regexp`` uses ``re.search``), numeric values with ``isequal``.
"""

from __future__ import annotations

import re
from typing import List

import numpy as np

from openmatlab.graphics.handle_model import GObj
from openmatlab.libs import graphics_builtins as gb
from openmatlab.numerics.ndarray_value import NDArrayValue

_err, _arr, _is_text, _is_cell, _h, _hcol = gb._err, gb._arr, gb._is_text, gb._is_cell, gb._h, gb._hcol


def _kids(o: GObj, include_hidden: bool) -> List[GObj]:
    out = [c for c in reversed(o.children) if c.alive]
    if o.type == "axes":
        extra = [o.props.get(k) for k in ("Title", "XLabel", "YLabel", "ZLabel")]
        if include_hidden:
            out += [x for x in extra if isinstance(x, GObj) and x.alive]
        lg = getattr(o, "legend", None)
        if lg is not None and lg.alive and lg not in out:
            pass  # legends are children of the figure in MATLAB; listed below
    if o.type == "figure":
        for a in [c for c in o.children if c.type == "axes" and c.alive]:
            lg = getattr(a, "legend", None)
            if lg is not None and lg.alive:
                out.insert(0, lg)
    return out


def _visible(o: GObj, include_hidden: bool) -> bool:
    return include_hidden or o.props.get("HandleVisibility", "on") == "on"


def _walk(o: GObj, depth, include_hidden, level=0):
    if not _visible(o, include_hidden):
        return
    yield o
    if depth is not None and level >= depth:
        return
    for c in _kids(o, include_hidden):
        yield from _walk(c, depth, include_hidden, level + 1)


def _value_matches(m, o, name, want, regexp):
    try:
        k = gb._canon(o, name)
    except Exception:
        return False
    if k == "Type" and o.type in gb.FULL_CLASS:
        got_s = o.type
    else:
        got = gb._get_prop(m, o, k)
        got_s = got.text if _is_text(got) else None
        if got_s is None:
            if _is_text(want) or regexp:
                return False
            try:
                g = np.asarray(got.backend_buffer(), dtype=float)
                w = np.asarray(want.backend_buffer(), dtype=float)
            except Exception:
                return False
            return g.shape == w.shape and bool(np.all((g == w) | (np.isnan(g) & np.isnan(w))))
    if not _is_text(want):
        return False
    return bool(re.search(want.text, got_s)) if regexp else got_s == want.text


def _parse(m, args):
    """-> (roots, depth, predicate) for findobj(h, ...) / findobj(...)."""
    roots = None
    rest = list(args)
    if rest and not _is_text(rest[0]):
        roots = gb._handles(m, rest.pop(0), "findobj") if _arr(rest[0] if False else args[0], "findobj").size else []
    depth = None
    if len(rest) >= 2 and _is_text(rest[0]) and rest[0].text.lower() == "-depth":
        d = float(_arr(rest[1], "findobj").reshape(-1)[0])
        depth = None if np.isinf(d) else int(d)
        rest = rest[2:]
    if rest and _is_text(rest[0]) and rest[0].text.lower() == "flat":
        depth = 0
        rest = rest[1:]

    # expression grammar: term (('-and'|'-or') term)*; term: ['-not'] (Name Value | '-regexp' Name Pat | '-property' Name)
    def term(i):
        neg = False
        while i < len(rest) and _is_text(rest[i]) and rest[i].text.lower() == "-not":
            neg, i = not neg, i + 1
        if i >= len(rest) or not _is_text(rest[i]):
            raise _err("findobj: invalid property name or option.", "MATLAB:findobj:InvalidArgument")
        w = rest[i].text
        wl = w.lower()
        if wl == "-regexp":
            if i + 2 >= len(rest) + 0 and i + 2 > len(rest):
                raise _err("findobj: -regexp needs a property name and a pattern.", "MATLAB:findobj:InvalidArgument")
            if i + 2 >= len(rest) + 1:
                raise _err("findobj: -regexp needs a property name and a pattern.", "MATLAB:findobj:InvalidArgument")
            name, pat = rest[i + 1].text, rest[i + 2]
            try:
                re.compile(pat.text)
            except re.error:
                raise _err("findobj: invalid regular expression.", "MATLAB:findobj:InvalidRegexp") from None
            f = lambda o: _value_matches(m, o, name, pat, True)  # noqa: E731
            i += 3
        elif wl == "-property":
            name = rest[i + 1].text if i + 1 < len(rest) and _is_text(rest[i + 1]) else ""

            def f(o, name=name):
                try:
                    gb._canon(o, name)
                    return True
                except Exception:
                    return False
            i += 2
        elif wl.startswith("-"):
            raise _err(f"findobj: unknown option '{w}'.", "MATLAB:findobj:InvalidArgument")
        else:
            if i + 1 >= len(rest):
                raise _err("findobj: a property name needs a value.", "MATLAB:findobj:InvalidArgument")
            want = rest[i + 1]
            f = lambda o, w=w, want=want: _value_matches(m, o, w, want, False)  # noqa: E731
            i += 2
        return (lambda o: not f(o)) if neg else f, i

    preds = []
    i = 0
    if rest:
        p, i = term(0)
        preds = [("and", p)]
        while i < len(rest):
            op = "and"
            if _is_text(rest[i]) and rest[i].text.lower() in ("-and", "-or", "-xor"):
                op = rest[i].text.lower()[1:]
                i += 1
            p, i = term(i)
            preds.append((op, p))

    def pred(o):
        r = True
        for op, p in preds:
            v = p(o)
            r = (r and v) if op == "and" else (r or v) if op == "or" else (r != v)
        return r
    return roots, depth, pred


def _find(include_hidden):
    def f(ev, args, nargout):
        m = gb.model(ev)
        roots, depth, pred = _parse(m, args)
        if roots is None:
            roots = [m.root]
        out, seen = [], set()
        for r in roots:
            for o in _walk(r, depth, include_hidden or r.type == "root" and False):
                if o.id not in seen and pred(o):
                    seen.add(o.id)
                    out.append(o.id)
        if not out:
            return (gb.GraphicsHandle(np.zeros((0, 1)), m),)
        return (_hcol(out),)
    return f


def _allchild(ev, args, nargout):
    m = gb.model(ev)
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    objs = gb._handles(m, args[0], "allchild")
    lists = [[c.id for c in _kids(o, True)] for o in objs]
    if len(objs) == 1:
        return (_hcol(lists[0]) if lists[0] else gb.GraphicsHandle(np.zeros((0, 1)), m),)
    from openmatlab.runtime.cell_value import CellValue

    return (CellValue(rows=tuple((_hcol(x) if x else gb.GraphicsHandle(np.zeros((0, 1)), m),) for x in lists)),)


def _ancestor(ev, args, nargout):
    m = gb.model(ev)
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if not _arr(args[0], "ancestor").size:
        return (NDArrayValue(np.zeros((0, 0))),)
    o = gb._handles(m, args[0], "ancestor")[0]
    types = gb._cellstrs(args[1]) if _is_cell(args[1]) else [args[1].text]
    types = [t.lower() for t in types]
    top = len(args) > 2 and _is_text(args[2]) and args[2].text.lower() == "toplevel"
    hit = None
    while o is not None:
        if o.type in types:
            hit = o
            if not top:
                break
        o = o.parent
    return (_h(hit.id) if hit is not None else NDArrayValue(np.zeros((0, 0))),)


def _groot(ev, args, nargout):
    gb.model(ev)
    return (_h(0.0),)


def _gco(ev, args, nargout):
    m = gb.model(ev)
    f = m.current_figure
    o = getattr(f, "current_object", None) if f is not None else None
    return (_h(o.id) if o is not None and o.alive else NDArrayValue(np.zeros((0, 0))),)


INTRINSICS = {k: gb._wrap(v) for k, v in {
    "findobj": _find(False), "findall": _find(True), "allchild": _allchild, "ancestor": _ancestor,
    "groot": _groot, "gco": _gco,
}.items()}
