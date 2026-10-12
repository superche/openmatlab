"""String-array builtins and text methods (Epic #482: #459, #460).

Every function works on string scalars/arrays, char row vectors and cellstr:
the input is turned into a text grid (``string_array.to_grid``), mapped, and
returned in the input's kind (string in → string out, char in → char out,
cellstr in → cell out), as MATLAB does.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime import string_array as sa
from openmatlab.runtime.value import Array, Value


def _err(msg: str):
    from openmatlab.libs.numeric_builtins import BuiltinError

    return BuiltinError(msg)


def _kind(v) -> str | None:
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    if sa.is_string(v):
        return "string"
    if isinstance(v, CharValue):
        return "char" if len(v.rows) <= 1 else "charmat"
    if isinstance(v, CellValue) and sa.to_grid(v, cells=True) is not None:
        return "cell"
    return None


def _text_in(name: str, v, *, charmat: bool = False):
    k = _kind(v)
    if k is None or (k == "charmat" and not charmat):
        raise _err(f"{name}: First argument must be text.")
    if k == "charmat":
        return k, np.array([[r] for r in v.rows], dtype=object)
    return k, sa.to_grid(v, numbers=False, cells=True)


def _text_out(kind: str, g: np.ndarray):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    if kind == "string":
        return sa.make(g)
    if kind == "char":
        return CharValue(g.flat[0] if g.size else "")
    if kind == "charmat":
        return CharValue(rows=[x for x in g.reshape(-1)])
    r, c = g.shape
    return CellValue(rows=tuple(tuple(CharValue(g[i, j]) for j in range(c)) for i in range(r)))


def _map(g: np.ndarray, fn) -> np.ndarray:
    out = np.empty(g.shape, dtype=object)
    for ix in np.ndindex(*g.shape):
        out[ix] = None if g[ix] is None else fn(g[ix])
    return out


def _logical(g: np.ndarray, fn) -> NDArrayValue:
    out = np.zeros(g.shape, dtype=bool)
    for ix in np.ndindex(*g.shape):
        out[ix] = False if g[ix] is None else bool(fn(g[ix]))
    return NDArrayValue(out)


def _scalar_text(name: str, v, what: str) -> str:
    try:
        g = sa.to_grid(v, numbers=False)
    except ValueError:
        g = None
    if g is None or g.size != 1 or g.flat[0] is None:
        raise _err(f"{name}: {what} must be a text scalar.")
    return g.flat[0]


def _patterns(name: str, v) -> list:
    g = sa.to_grid(v, numbers=False, cells=True)
    if g is None or any(x is None for x in g.flat):
        raise _err(f"{name}: Search term must be a text or string array.")
    return list(g.flat)


def _bool_opt(name: str, args, key: str, default: bool) -> bool:
    val = default
    rest = list(args)
    while rest:
        if len(rest) < 2:
            raise _err(f"{name}: name-value arguments must come in pairs")
        k = _scalar_text(name, rest[0], "option name")
        if k.lower() != key.lower():
            raise _err(f"{name}: unknown option '{k}'")
        b = np.asarray(rest[1].backend_buffer()) if isinstance(rest[1], Array) else None
        if b is None or b.size != 1:
            raise _err(f"{name}: {key} must be true or false")
        val = bool(b.reshape(-1)[0])
        rest = rest[2:]
    return val


# ----- construction / conversion -----

def _string(args, *, nargout=1):
    if len(args) != 1:
        raise _err("string: expected 1 argument")
    g = sa.to_grid(args[0], cells=True)
    if g is None:
        raise _err(f"string: Conversion from {args[0].matlab_class()} is not possible.")
    return (sa.make(g),)


def _strings(args, *, nargout=1):
    from openmatlab.libs.numeric_builtins import _shape2

    m, n = _shape2("strings", args) if args else (1, 1)
    g = np.empty((m, n), dtype=object)
    g[...] = ""
    return (sa.make(g),)


def _strlength(args, *, nargout=1):
    if len(args) != 1:
        raise _err("strlength: expected 1 argument")
    _, g = _text_in("strlength", args[0])
    out = np.array([[np.nan if x is None else float(len(x)) for x in row] for row in g]).reshape(g.shape)
    return (NDArrayValue(out),)


def _char_wrap(old):
    def _fn(args, *, nargout=1):
        from openmatlab.runtime.char_value import CharValue

        if len(args) == 1 and isinstance(args[0], sa.StringArray):
            g = args[0].data
            if any(x is None for x in g.flat):
                raise _err("char: Unable to convert a missing string.")
            rows = list(g.reshape(-1, order="F"))
            w = max((len(r) for r in rows), default=0)
            return (CharValue(rows=[r.ljust(w) for r in rows]) if rows and w else CharValue(""),)
        return old(args, nargout=nargout)

    return _fn


def _cellstr(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    if len(args) != 1:
        raise _err("cellstr: expected 1 argument")
    v = args[0]
    k = _kind(v)
    if k == "cell":
        return (v,)
    if k in ("char", "charmat"):
        rows = v.rows or ("",)
        return (CellValue(rows=tuple((CharValue(r.rstrip(" ")),) for r in rows)),)
    if k == "string":
        g = sa.to_grid(v)
        if any(x is None for x in g.flat):
            raise _err("cellstr: Unable to convert a missing string.")
        return (_text_out("cell", g),)
    raise _err("cellstr: Input must be a string array, character array, or cell array of character vectors.")


# ----- methods (#460) -----

def _case(name: str, fn):
    def _f(args, *, nargout=1):
        if len(args) != 1:
            raise _err(f"{name}: expected 1 argument")
        k, g = _text_in(name, args[0], charmat=True)
        return (_text_out(k, _map(g, fn)),)

    return _f


_WS = " \t\n\r\v\f\x00"


def _strip(args, *, nargout=1):
    if not 1 <= len(args) <= 3:
        raise _err("strip: usage strip(str[, side[, char]])")
    k, g = _text_in("strip", args[0])
    side = _scalar_text("strip", args[1], "side").lower() if len(args) >= 2 else "both"
    if side not in ("both", "left", "right", "leading", "trailing"):
        raise _err("strip: side must be 'both', 'left' or 'right'")
    chars = _scalar_text("strip", args[2], "strip character") if len(args) == 3 else _WS
    fn = {"both": lambda x: x.strip(chars), "left": lambda x: x.lstrip(chars),
          "leading": lambda x: x.lstrip(chars), "right": lambda x: x.rstrip(chars),
          "trailing": lambda x: x.rstrip(chars)}[side]
    return (_text_out(k, _map(g, fn)),)


def _strtrim(args, *, nargout=1):
    if len(args) != 1:
        raise _err("strtrim: expected 1 argument")
    k, g = _text_in("strtrim", args[0])
    return (_text_out(k, _map(g, lambda x: x.strip(_WS))),)


def _replace(name: str):
    def _f(args, *, nargout=1):
        if len(args) != 3:
            raise _err(f"{name}: usage {name}(str, old, new)")
        k, g = _text_in(name, args[0])
        olds = _patterns(name, args[1])
        new = _scalar_text(name, args[2], "replacement")

        def fn(x):
            for o in olds:
                if o:
                    x = x.replace(o, new)
            return x

        return (_text_out(k, _map(g, fn)),)

    return _f


def _match(name: str, test):
    def _f(args, *, nargout=1):
        if len(args) < 2:
            raise _err(f"{name}: usage {name}(str, pattern[, 'IgnoreCase', tf])")
        _, g = _text_in(name, args[0])
        pats = _patterns(name, args[1])
        ic = _bool_opt(name, args[2:], "IgnoreCase", False)
        if ic:
            pats = [p.lower() for p in pats]
        return (_logical(g, lambda x: any(test(x.lower() if ic else x, p) for p in pats)),)

    return _f


def _split(args, *, nargout=1):
    if not args:
        raise _err("split: not enough input arguments")
    k, g = _text_in("split", args[0])
    if g.size != 1:
        raise _err("split: string-array input is not supported yet; split one element at a time")
    rest = list(args[1:])
    delims = None
    if rest and not (len(rest) % 2 == 0 and _kind(rest[0]) in ("char", "string")
                     and str(sa.to_grid(rest[0], numbers=False).flat[0]).lower() == "collapsedelimiters"):
        delims = _patterns("split", rest[0])
        rest = rest[1:]
    collapse = _bool_opt("split", rest, "CollapseDelimiters", True)
    text = g.flat[0]
    if text is None:
        return (sa.make(np.array([[None]], dtype=object)),)
    seps = list(_WS[:-1]) if delims is None else [d for d in delims if d]
    parts, cur, i = [], "", 0
    while i < len(text):
        hit = next((d for d in sorted(seps, key=len, reverse=True) if text.startswith(d, i)), None)
        if hit is None:
            cur += text[i]
            i += 1
            continue
        parts.append(cur)
        cur = ""
        i += len(hit)
        if collapse:
            while True:
                again = next((d for d in sorted(seps, key=len, reverse=True) if text.startswith(d, i)), None)
                if again is None:
                    break
                i += len(again)
    parts.append(cur)
    out = np.empty((len(parts), 1), dtype=object)
    for j, p in enumerate(parts):
        out[j, 0] = p
    return (_text_out("string" if k == "string" else "cell", out),)


def _join(args, *, nargout=1):
    if not 1 <= len(args) <= 2:
        raise _err("join: usage join(str[, delimiter])")
    k, g = _text_in("join", args[0])
    delim = _scalar_text("join", args[1], "delimiter") if len(args) == 2 else " "
    if g.shape[0] > 1 and g.shape[1] > 1:
        rows = [[delim.join(row)] if None not in row else [None] for row in g.tolist()]
        out = np.array(rows, dtype=object).reshape(-1, 1)
    else:
        flat = list(g.flat)
        out = np.array([[None if None in flat else delim.join(flat)]], dtype=object)
    return (_text_out("string" if k == "string" else "char", out),)


def _strcmp(name: str, fold: bool):
    def _f(args, *, nargout=1):
        if len(args) != 2:
            raise _err(f"{name}: requires two inputs")
        a, b = args

        def grid(v):
            k = _kind(v)
            if k in ("string", "cell"):
                return sa.to_grid(v, numbers=False, cells=True), True
            if k == "char":
                return np.array([[v.text]], dtype=object), False
            return None, False

        ga, arr_a = grid(a)
        gb, arr_b = grid(b)
        if ga is None or gb is None:
            return (NDArrayValue(np.array([[False]])),)  # non-text: false (MATLAB)
        if not (arr_a or arr_b):
            x, y = ga.flat[0], gb.flat[0]
            return (NDArrayValue(np.array([[x.lower() == y.lower() if fold else x == y]])),)
        if not (ga.size == 1 or gb.size == 1 or ga.shape == gb.shape):
            raise _err(f"{name}: Inputs must be the same size or either one can be a scalar.")
        x, y = np.broadcast_arrays(ga, gb)
        out = np.zeros(x.shape, dtype=bool)
        for ix in np.ndindex(*x.shape):
            p, q = x[ix], y[ix]
            out[ix] = p is not None and q is not None and ((p.lower() == q.lower()) if fold else p == q)
        return (NDArrayValue(out),)

    return _f


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        string=_string, strings=_strings, strlength=_strlength, cellstr=_cellstr,
        upper=_case("upper", str.upper), lower=_case("lower", str.lower),
        strip=_strip, strtrim=_strtrim, replace=_replace("replace"), strrep=_replace("strrep"),
        contains=_match("contains", lambda x, p: p in x),
        startsWith=_match("startsWith", lambda x, p: x.startswith(p)),
        endsWith=_match("endsWith", lambda x, p: x.endswith(p)),
        split=_split, join=_join, strcmp=_strcmp("strcmp", False), strcmpi=_strcmp("strcmpi", True),
    )
    builtins["char"] = _char_wrap(builtins["char"])
