"""String residuals (#483): missing/ismissing, sort/unique on strings, split of
string columns, sprintf/compose, regexp family, extract*/insert*/pad/reverse,
num2str/str2double."""

from __future__ import annotations

import re
from typing import Callable, Dict

import numpy as np

from openmatlab.libs.string_builtins import _err, _kind, _scalar_text, _text_in, _text_out
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime import string_array as sa
from openmatlab.runtime.value import Array


def _cellcol(items):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    return CellValue(rows=(tuple(CharValue(x) if isinstance(x, str) else x for x in items),)) if items else \
        CellValue(rows=())


# ----- missing -----

def _missing(args, *, nargout=1):
    if args:
        raise _err("missing: takes no arguments")
    from openmatlab.runtime.missing_value import MissingValue

    return (MissingValue(),)  # class 'missing'; converts by context (#504)


def _ismissing(args, *, nargout=1):
    if len(args) != 1:
        raise _err("ismissing: expected 1 argument")
    v = args[0]
    if getattr(v, "is_missing_value", False):
        return (NDArrayValue(np.array([[True]])),)
    if sa.is_string(v):
        g = sa.to_grid(v)
        return (NDArrayValue(np.array([[x is None for x in row] for row in g], dtype=bool).reshape(g.shape)),)
    if isinstance(v, Array):
        b = np.asarray(v.backend_buffer())
        if b.dtype == np.bool_ or np.issubdtype(b.dtype, np.integer):
            return (NDArrayValue(np.zeros(b.shape, dtype=bool)),)
        return (NDArrayValue(np.isnan(b)),)
    shape = getattr(v, "shape", (1, 1))
    return (NDArrayValue(np.zeros(shape, dtype=bool)),)


# ----- sort / unique on strings -----

def _str_sort(old):
    def _fn(args, *, nargout=1):
        if not args or not sa.is_string(args[0]):
            return old(args, nargout=nargout)
        g = sa.to_grid(args[0])
        descend = any(_kind(a) in ("char", "string") and _scalar_text("sort", a, "flag").lower() == "descend"
                      for a in args[1:])
        if g.shape[0] == 1 or g.shape[1] == 1:
            flat = list(g.reshape(-1))
            present = sorted((k for k, x in enumerate(flat) if x is not None), key=lambda k: flat[k], reverse=descend)
            order = present + [k for k, x in enumerate(flat) if x is None]  # missing last
            out = np.array([flat[k] for k in order], dtype=object).reshape(g.shape)
            idx = np.array([k + 1.0 for k in order]).reshape(g.shape)
        else:  # columns
            out = np.empty(g.shape, dtype=object)
            idx = np.zeros(g.shape)
            for j in range(g.shape[1]):
                col = list(g[:, j])
                pres = sorted((k for k, x in enumerate(col) if x is not None), key=lambda k: col[k], reverse=descend)
                order = pres + [k for k, x in enumerate(col) if x is None]
                out[:, j] = [col[k] for k in order]
                idx[:, j] = [k + 1.0 for k in order]
        res = (sa.make(out), NDArrayValue(idx))
        return res[: max(1, nargout)]

    return _fn


def _str_unique(old):
    def _fn(args, *, nargout=1):
        if not args or not sa.is_string(args[0]):
            return old(args, nargout=nargout)
        g = sa.to_grid(args[0])
        flat = list(g.reshape(-1, order="F"))
        present = sorted({x for x in flat if x is not None})
        u = present + [None] * sum(1 for x in flat if x is None)  # each missing is distinct (MATLAB)
        first = [flat.index(x) + 1.0 for x in present] + [k + 1.0 for k, x in enumerate(flat) if x is None]
        pos = {x: k for k, x in enumerate(present)}
        miss = iter(range(len(present), len(u)))
        ic = [pos[x] + 1.0 if x is not None else next(miss) + 1.0 for x in flat]
        row = g.shape[0] == 1
        out = np.array(u, dtype=object).reshape((1, -1) if row else (-1, 1))
        res = (sa.make(out), NDArrayValue(np.array(first).reshape(-1, 1)), NDArrayValue(np.array(ic).reshape(-1, 1)))
        return res[: max(1, nargout)]

    return _fn


# ----- split of string columns -----

def _split_wrap(old):
    def _fn(args, *, nargout=1):
        if not args or not isinstance(args[0], sa.StringArray) or args[0].numel() == 1:
            return old(args, nargout=nargout)
        g = args[0].data
        if g.shape[1] != 1:
            raise _err("split: string-array input must be a column vector (N-by-1); "
                       "row inputs would produce an N-D result")
        rows = []
        for x in g[:, 0]:
            part = old((sa.make(np.array([[x]], dtype=object)), *args[1:]), nargout=1)[0]
            rows.append(list(sa.to_grid(part).reshape(-1)))
        if len({len(r) for r in rows}) > 1:
            raise _err("split: Element 2 of the text contains a different number of delimiters than element 1."
                       if len(rows) > 1 else "split: inconsistent delimiters")
        return (sa.make(np.array(rows, dtype=object)),)

    return _fn


# ----- sprintf / compose -----

_SPEC = re.compile(r"%(?P<flags>[-+ 0#]*)(?P<width>\d+|\*)?(?:\.(?P<prec>\d+))?(?P<conv>[diouxXfeEgGcs%])")


def _escapes(fmt: str) -> str:
    return (fmt.replace("\\\\", "\x00").replace("\\n", "\n").replace("\\t", "\t")
            .replace("\\r", "\r").replace("\x00", "\\"))


def _flat_args(args) -> list:
    out = []
    for a in args:
        if sa.is_string(a) or _kind(a) == "char":
            g = sa.to_grid(a, numbers=False)
            out.extend("<missing>" if x is None else x for x in g.reshape(-1, order="F"))
        elif type(a).__name__ == "CellValue":
            raise _err("sprintf: Function is not defined for 'cell' inputs.")
        elif isinstance(a, Array):
            out.extend(np.asarray(a.backend_buffer()).reshape(-1, order="F").tolist())
        else:
            raise _err(f"sprintf: Function is not defined for '{a.matlab_class()}' inputs.")
    return out


def _fmt_one(spec: re.Match, val) -> str:
    flags, width, prec, conv = spec["flags"], spec["width"] or "", spec["prec"], spec["conv"]
    p = f".{prec}" if prec is not None else ""
    if conv in "sc":
        if not isinstance(val, str):
            v = float(val.real if isinstance(val, complex) else val)
            val = chr(int(v)) if conv == "c" and v == int(v) else (
                str(int(v)) if v == int(v) else f"{v:g}" if conv == "s" else chr(int(v)))
        return f"%{flags}{width}{p}s" % val
    if isinstance(val, str):  # text for a numeric conversion: MATLAB prints the codes
        return "".join(_fmt_one(spec, float(ord(ch))) for ch in val)
    v = val.real if isinstance(val, complex) else val
    if isinstance(v, (bool, np.bool_)):
        v = int(v)
    if conv in "diouxX":
        if float(v) != int(v) or not np.isfinite(float(v)):
            if not np.isfinite(float(v)):
                return f"%{flags}{width}s" % ("NaN" if v != v else ("Inf" if v > 0 else "-Inf"))
            return f"%{flags}{width}e" % float(v)  # MATLAB switches to %e
        c = "d" if conv in "diu" else conv
        return f"%{flags}{width}{c}" % int(v)
    fv = float(v)
    if not np.isfinite(fv):
        return f"%{flags}{width}s" % ("NaN" if fv != fv else ("Inf" if fv > 0 else "-Inf"))
    return f"%{flags}{width}{p}{conv}" % fv


def _format(fmt: str, vals: list) -> str:
    fmt = _escapes(fmt)
    specs = [m for m in _SPEC.finditer(fmt) if m["conv"] != "%"]
    if not specs or not vals:
        out, k = [], 0
        for m in _SPEC.finditer(fmt):
            out.append(fmt[k:m.start()])
            out.append("%" if m["conv"] == "%" else "")
            k = m.end()
        out.append(fmt[k:])
        text = "".join(out)
        if not specs:
            return text
        # specs but no values: MATLAB stops at the first conversion
        first = specs[0]
        return _format(fmt[:first.start()].replace("%%", "%%"), []) if first.start() else ""
    out, i = [], 0
    while i < len(vals):
        k = 0
        for m in _SPEC.finditer(fmt):
            out.append(fmt[k:m.start()])
            k = m.end()
            if m["conv"] == "%":
                out.append("%")
                continue
            if i >= len(vals):
                k = len(fmt)  # MATLAB stops output at the first spec without data
                break
            out.append(_fmt_one(m, vals[i]))
            i += 1
        else:
            out.append(fmt[k:])
            continue
        break
    return "".join(out)


def _sprintf(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue

    if not args:
        raise _err("sprintf: not enough input arguments")
    k = _kind(args[0])
    if k not in ("char", "string"):
        raise _err("sprintf: Format must be a character vector or string scalar.")
    text = _format(_scalar_text("sprintf", args[0], "format"), _flat_args(args[1:]))
    return (sa.make(np.array([[text]], dtype=object)) if k == "string" else CharValue(text),)


def _compose(args, *, nargout=1):
    if not args:
        raise _err("compose: not enough input arguments")
    fmt = _scalar_text("compose", args[0], "format")
    if len(args) == 1:
        return (sa.make(np.array([[_format(fmt, [])]], dtype=object)),)
    grids = []
    for a in args[1:]:
        if sa.is_string(a) or _kind(a) == "char":
            grids.append(sa.to_grid(a, numbers=False))
        elif isinstance(a, Array):
            b = np.asarray(a.backend_buffer())
            grids.append(b.reshape(1, 1) if b.ndim == 0 else b)
        else:
            raise _err("compose: arguments must be text or numeric")
    shape = max((g.shape for g in grids), key=lambda s: int(np.prod(s)))
    if any(g.size not in (1, int(np.prod(shape))) for g in grids):
        raise _err("compose: argument sizes must match or be scalars")
    full = [np.broadcast_to(g, shape) if g.size == 1 else g.reshape(shape) for g in grids]
    out = np.empty(shape, dtype=object)
    for ix in np.ndindex(*shape):
        out[ix] = _format(fmt, [g[ix].item() if hasattr(g[ix], "item") else g[ix] for g in full])
    return (sa.make(out),)


# ----- regexp family -----

def _pyre(pat: str) -> str:
    # MATLAB named groups (?<name>...) -> Python (?P<name>...)
    return re.sub(r"\(\?<([A-Za-z]\w*)>", r"(?P<\1>", pat)


def _regexp(name: str, flags: int):
    def _fn(args, *, nargout=1):
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.runtime.char_value import CharValue

        if len(args) < 2:
            raise _err(f"{name}: not enough input arguments")
        k = _kind(args[0])
        if k not in ("char", "string"):
            raise _err(f"{name}: first argument must be a character vector or string scalar")
        text = _scalar_text(name, args[0], "text")
        try:
            rx = re.compile(_pyre(_scalar_text(name, args[1], "expression")), flags)
        except re.error as exc:
            raise _err(f"{name}: invalid expression: {exc}") from None
        opts = [_scalar_text(name, a, "option").lower() for a in args[2:]]
        once = "once" in opts
        if "ignorecase" in opts:
            rx = re.compile(rx.pattern, flags | re.IGNORECASE)
        opts = [o for o in opts if o not in ("once", "ignorecase", "matchcase")]
        ms = list(rx.finditer(text))
        if once:
            ms = ms[:1]

        def txt(x):
            return sa.make(np.array([[x]], dtype=object)) if k == "string" else CharValue(x)

        def lst(items, wrap=True):
            if once:
                return items[0] if items else (txt("") if wrap else NDArrayValue(np.zeros((1, 0))))
            if k == "string" and wrap and all(isinstance(i, str) for i in items):
                return sa.make(np.array([items], dtype=object)) if items else sa.StringArray(np.empty((1, 0), dtype=object))
            return _cellcol([i if not isinstance(i, str) else (txt(i) if wrap else i) for i in items])

        def toks(m):
            g = [x if x is not None else "" for x in m.groups()] if m.groups() else [m.group(0)]
            return CellValue(rows=(tuple(txt(x) for x in g),))

        outs = {
            "start": (NDArrayValue(np.array([[m.start() + 1.0 for m in ms]]).reshape(1, -1)) if not once
                      else NDArrayValue(np.array([[ms[0].start() + 1.0]])) if ms else NDArrayValue(np.zeros((1, 0)))),
            "end": (NDArrayValue(np.array([[float(m.end()) for m in ms]]).reshape(1, -1)) if not once
                    else NDArrayValue(np.array([[float(ms[0].end())]])) if ms else NDArrayValue(np.zeros((1, 0)))),
            "match": lst([m.group(0) for m in ms]) if not once else (txt(ms[0].group(0)) if ms else txt("")),
            "tokens": (_cellcol([toks(m) for m in ms]) if not once else
                       (toks(ms[0]) if ms else CellValue(rows=()))),
            "split": None,
            "names": None,
        }
        pieces, last = [], 0
        for m in rx.finditer(text):
            pieces.append(text[last:m.start()])
            last = m.end()
        pieces.append(text[last:])
        outs["split"] = (sa.make(np.array([pieces], dtype=object)) if k == "string"
                         else _cellcol([CharValue(p) for p in pieces]))
        outs["names"] = _names(ms[:1] if once else ms, rx)
        order = opts or ["start", "end", "tokenextents", "match", "tokens", "names", "split"]
        res = []
        for o in order[: max(1, nargout)]:
            if o == "tokenextents":
                res.append(_cellcol([NDArrayValue(np.array([[m.start(i) + 1.0, float(m.end(i))] for i in
                                                            range(1, (m.re.groups or 0) + 1)] or
                                                           [[m.start() + 1.0, float(m.end())]])) for m in ms]))
                continue
            if o not in outs:
                raise _err(f"{name}: unknown option '{o}'")
            res.append(outs[o])
        return tuple(res)

    return _fn


def _names(ms, rx):
    """regexp 'names': 1xN struct array, one element per match, fields = named tokens (#504).
    Without named tokens it is a 1x1 struct with no fields; with no match, 0x0 with the fields."""
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue

    keys = sorted(rx.groupindex, key=rx.groupindex.get)
    if not keys:
        return StructValue.scalar()
    elems = [{k: CharValue(m.group(k) or "") for k in keys} for m in ms]
    return StructValue.build((1, len(elems)) if elems else (0, 0), keys, elems)


def _regexprep(name: str, flags: int):
    def _fn(args, *, nargout=1):
        if len(args) < 3:
            raise _err(f"{name}: usage {name}(str, expression, replace)")
        k, g = _text_in(name, args[0])
        try:
            rx = re.compile(_pyre(_scalar_text(name, args[1], "expression")), flags)
        except re.error as exc:
            raise _err(f"{name}: invalid expression: {exc}") from None
        rep = _scalar_text(name, args[2], "replacement")
        rep = re.sub(r"\$(\d+)", r"\\g<\1>", rep.replace("\\", "\\\\")).replace("\\\\g<", "\\g<")
        rep = _escapes(rep) if "\\n" in rep or "\\t" in rep else rep
        opts = [_scalar_text(name, a, "option").lower() for a in args[3:]]
        count = 1 if "once" in opts else 0
        if "ignorecase" in opts:
            rx = re.compile(rx.pattern, flags | re.IGNORECASE)
        out = np.empty(g.shape, dtype=object)
        for ix in np.ndindex(*g.shape):
            out[ix] = None if g[ix] is None else rx.sub(rep, g[ix], count=count)
        return (_text_out(k, out),)

    return _fn


# ----- extract / insert / pad / reverse -----

def _pos_or_text(name, v):
    if isinstance(v, Array) and not sa.is_string(v):
        return int(np.asarray(v.backend_buffer()).reshape(-1)[0])
    return _scalar_text(name, v, "boundary")


def _textfn(name: str, nargs: tuple, fn):
    def _f(args, *, nargout=1):
        if len(args) not in nargs:
            raise _err(f"{name}: wrong number of input arguments")
        k, g = _text_in(name, args[0])
        extra = [_pos_or_text(name, a) for a in args[1:]]
        out = np.empty(g.shape, dtype=object)
        for ix in np.ndindex(*g.shape):
            out[ix] = None if g[ix] is None else fn(g[ix], *extra)
        return (_text_out(k, out),)

    return _f


def _find_after(x, s):
    if isinstance(s, int):
        return s
    i = x.find(s)
    return None if i < 0 else i + len(s)


def _find_before(x, s):
    if isinstance(s, int):
        return s - 1
    i = x.find(s)
    return None if i < 0 else i


def _between(x, a, b):
    i = _find_after(x, a) if not isinstance(a, int) else a - 1
    if i is None:
        return ""
    if isinstance(b, int):
        return x[i:b]
    j = x.find(b, i)
    return "" if j < 0 else x[i:j]


def _after(x, a):
    i = _find_after(x, a)
    return None if i is None else x[i:]


def _before(x, a):
    i = _find_before(x, a)
    return None if i is None else x[:i]


def _ins_after(x, a, t):
    i = _find_after(x, a)
    return x if i is None else x[:i] + t + x[i:]


def _ins_before(x, a, t):
    i = _find_before(x, a)
    return x if i is None else x[:i] + t + x[i:]


def _pad(args, *, nargout=1):
    if not 1 <= len(args) <= 4:
        raise _err("pad: usage pad(str[, n][, side][, char])")
    k, g = _text_in("pad", args[0])
    rest = list(args[1:])
    n = None
    if rest and isinstance(rest[0], Array) and not sa.is_string(rest[0]):
        n = int(np.asarray(rest.pop(0).backend_buffer()).reshape(-1)[0])
    side = _scalar_text("pad", rest.pop(0), "side").lower() if rest else "right"
    ch = _scalar_text("pad", rest.pop(0), "pad character") if rest else " "
    if side not in ("left", "right", "both") or len(ch) != 1:
        raise _err("pad: side must be 'left', 'right' or 'both' and the pad character a single character")
    width = n if n is not None else max((len(x) for x in g.flat if x is not None), default=0)

    def one(x):
        if len(x) >= width:
            return x
        d = width - len(x)
        if side == "left":
            return ch * d + x
        if side == "right":
            return x + ch * d
        return ch * (d // 2) + x + ch * (d - d // 2)

    out = np.empty(g.shape, dtype=object)
    for ix in np.ndindex(*g.shape):
        out[ix] = None if g[ix] is None else one(g[ix])
    return (_text_out(k, out),)


# ----- num2str / str2double -----

def _num2str(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue

    if not 1 <= len(args) <= 2:
        raise _err("num2str: usage num2str(A[, precision | format])")
    a = args[0]
    if _kind(a) in ("char", "charmat"):
        return (a,)
    if not isinstance(a, Array):
        raise _err("num2str: input must be numeric")
    b = np.asarray(a.backend_buffer())
    b = b.reshape(1, 1) if b.ndim == 0 else b
    if b.ndim > 2:
        b = b.reshape(b.shape[0], -1, order="F")
    if len(args) == 2:
        if _kind(args[1]) in ("char", "string"):
            fmt = _scalar_text("num2str", args[1], "format")
            return (CharValue(rows=[_format(fmt, list(row)) for row in b]) if b.shape[0] > 1 else
                    CharValue(_format(fmt, list(b.reshape(-1)))),)
        prec = int(np.asarray(args[1].backend_buffer()).reshape(-1)[0])
        one = lambda v: _g(v, prec)  # noqa: E731
    else:
        integer = b.dtype == np.bool_ or np.issubdtype(b.dtype, np.integer) or (
            not np.iscomplexobj(b) and np.all(np.isfinite(b) == np.isfinite(b)) and
            np.all((b == np.floor(b)) | ~np.isfinite(b)))
        one = (lambda v: _int_text(v)) if integer else (lambda v: _g(v, max(5, _digits(b) + 4)))
    if b.size != 1 and not np.iscomplexobj(b) and (len(args) == 2 or not integer):
        return (CharValue(rows=_num2str_float_matrix(b, prec if len(args) == 2 else None)),)
    cells = [[one(v) for v in row] for row in b.tolist()]
    if b.size == 1:
        return (CharValue(cells[0][0]),)
    w = max(len(c) for row in cells for c in row)
    rows = ["  ".join(c.rjust(w) for c in row) for row in cells]
    return (CharValue(rows=rows),)


def _num2str_float_matrix(b, prec):
    """MATLAB num2str layout for non-integer matrices (#505): every element uses
    %<w>.<d>g with d = clamp(floor(log10(max|x|)) + 5, 5, 16), or the given
    precision, and w = d + 7 (+1 if any element is negative). Then the blank
    columns common to all rows are trimmed from both sides."""
    f = np.abs(b[np.isfinite(b)].astype(float))
    if prec is None:
        top = f.max() if f.size else 0.0
        d = int(np.floor(np.log10(top))) if top > 0 else 0
        d = min(max(d + 5, 5), 16)
    else:
        d = prec
    w = d + 7 + (1 if np.any(b < 0) else 0)
    rows = ["".join(_g(v, d).rjust(w) for v in row) for row in b.tolist()]
    lead = min((len(r) - len(r.lstrip(" ")) for r in rows), default=0)
    rows = [r[lead:] for r in rows]
    tail = min((len(r) - len(r.rstrip(" ")) for r in rows), default=0)
    return [r[: len(r) - tail] if tail else r for r in rows]


def _digits(b) -> int:
    f = np.abs(np.asarray(b, dtype=float))
    f = f[np.isfinite(f) & (f > 0)]
    return int(np.floor(np.log10(f.max()))) + 1 if f.size and f.max() >= 1 else 0


def _int_text(v) -> str:
    if isinstance(v, (bool, np.bool_)):
        return str(int(v))
    fv = float(v)
    if fv != fv:
        return "NaN"
    if fv in (float("inf"), float("-inf")):
        return "Inf" if fv > 0 else "-Inf"
    return str(int(v))


def _g(v, prec: int) -> str:
    if isinstance(v, complex):
        im = f"{abs(v.imag):.{prec}g}"
        return f"{v.real:.{prec}g}{'-' if v.imag < 0 else '+'}{im}i"
    fv = float(v)
    if fv != fv:
        return "NaN"
    if fv in (float("inf"), float("-inf")):
        return "Inf" if fv > 0 else "-Inf"
    return f"{fv:.{prec}g}"


def _str2double(args, *, nargout=1):
    if len(args) != 1:
        raise _err("str2double: expected 1 argument")
    v = args[0]
    k = _kind(v)
    if k is None:
        shape = getattr(v, "shape", (1, 1))
        return (NDArrayValue(np.full(shape if k is None and not isinstance(v, Array) else (1, 1), np.nan)),)
    g = sa.to_grid(v, numbers=False, cells=True) if k != "char" else np.array([[v.text]], dtype=object)

    def conv(x):
        if x is None:
            return np.nan
        t = x.strip().replace(",", "")
        if re.fullmatch(r"[+-]?(inf|Inf|INF)", t):
            return float(t.replace("inf", "Inf").lower())
        if t.lower() == "nan":
            return np.nan
        try:
            return float(t) if re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eEdD][+-]?\d+)?", t) else np.nan
        except ValueError:
            return np.nan

    out = np.array([[conv(x) for x in row] for row in g], dtype=float).reshape(g.shape)
    return (NDArrayValue(out),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        missing=_missing, ismissing=_ismissing, sprintf=_sprintf, compose=_compose,
        regexp=_regexp("regexp", 0), regexpi=_regexp("regexpi", re.IGNORECASE),
        regexprep=_regexprep("regexprep", 0),
        extractBetween=_textfn("extractBetween", (3,), _between),
        extractAfter=_textfn("extractAfter", (2,), _after),
        extractBefore=_textfn("extractBefore", (2,), _before),
        insertAfter=_textfn("insertAfter", (3,), _ins_after),
        insertBefore=_textfn("insertBefore", (3,), _ins_before),
        reverse=_textfn("reverse", (1,), lambda x: x[::-1]),
        pad=_pad, num2str=_num2str, str2double=_str2double,
    )
    builtins["sort"] = _str_sort(builtins["sort"])
    builtins["unique"] = _str_unique(builtins["unique"])
    builtins["split"] = _split_wrap(builtins["split"])
