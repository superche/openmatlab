"""Core string functions (Epic #536).

strsplit/strjoin/strfind/strcat/strvcat/str2num, mat2str/int2str,
dec2bin/bin2dec/dec2hex/hex2dec, blanks/deblank. Char-vector and cellstr
inputs follow MATLAB; string-array inputs are converted where MATLAB returns
the same class.
"""

from __future__ import annotations

import math
import re
from typing import Callable, Dict, List

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _cv(text="", rows=None):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(rows=tuple(rows)) if rows is not None else CharValue(text)


def _is_cell(v):
    from openmatlab.runtime.cell_value import CellValue

    return isinstance(v, CellValue)


def _is_char(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue) and not getattr(v, "is_string", False)


def _is_text(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue)


def _grid(v):
    r, c = v.shape
    return [[v.get(i, j) for j in range(c)] for i in range(r)]


def _mk_cell(grid):
    from openmatlab.runtime.cell_value import CellValue

    if not grid or not grid[0]:
        return CellValue(rows=())
    return CellValue(rows=tuple(tuple(r) for r in grid))


def _row_cell(items):
    return _mk_cell([list(items)]) if items else _mk_cell([])


def _text(v, fn, what="input"):
    if _is_text(v) and len(v.rows) <= 1:
        return v.text
    raise _err(f"{fn}: {what} must be a character vector or string scalar.", f"MATLAB:{fn}:InvalidInput")


def _cellstrs(v, fn):
    if not _is_cell(v):
        raise _err(f"{fn}: input must be a cell array of character vectors.", f"MATLAB:{fn}:InvalidCellType")
    g = _grid(v)
    flat = [g[i][j] for j in range(len(g[0]) if g else 0) for i in range(len(g))]
    out = []
    for x in flat:
        if not _is_text(x) or len(x.rows) > 1:
            raise _err(f"{fn}: input must be a cell array of character vectors.", f"MATLAB:{fn}:InvalidCellType")
        out.append(x.text)
    return out


def _num(v, fn):
    if not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: input must be numeric.", f"MATLAB:{fn}:InvalidInput")
    b = np.asarray(v.backend_buffer())
    return b.reshape(1, 1) if b.ndim == 0 else (b.reshape(1, -1) if b.ndim == 1 else b)


def _scalar(v, fn):
    return float(_num(v, fn).reshape(-1)[0])


def _escape(s):
    return (s.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\"))


# ----------------------------------------------------------- split / join
def _strsplit(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    s = _text(args[0], "strsplit", "first input")
    rest = list(args[1:])
    delims = None
    if rest and not (_is_text(rest[0]) and rest[0].text.lower() in ("collapsedelimiters", "delimitertype") and len(rest) % 2 == 0):
        d = rest.pop(0)
        delims = _cellstrs(d, "strsplit") if _is_cell(d) else [_text(d, "strsplit", "delimiter")]
    collapse, regex = True, False
    while rest:
        if len(rest) < 2:
            raise _err("strsplit: parameter name/value pairs must come in pairs.", "MATLAB:strsplit:ParamValuePairs")
        k, v = rest.pop(0), rest.pop(0)
        key = _text(k, "strsplit").lower()
        if key == "collapsedelimiters":
            collapse = bool(_scalar(v, "strsplit"))
        elif key == "delimitertype":
            regex = _text(v, "strsplit").lower() == "regularexpression"
        else:
            raise _err(f"strsplit: unknown parameter '{k.text}'.", "MATLAB:strsplit:UnknownParameter")
    if delims is None:
        pats = [r"\s"]
    else:
        pats = [d if regex else re.escape(_escape(d)) for d in delims]
        pats.sort(key=len, reverse=True)
    pat = "(?:%s)" % "|".join(pats)
    if collapse:
        pat = "(?:%s)+" % pat
    parts = re.split(pat, s)
    matches = [m.group(0) for m in re.finditer(pat, s)]
    items = [_cv(p) for p in parts]
    out = _row_cell(items)
    if nargout > 1:
        return out, _row_cell([_cv(m) for m in matches])
    return (out,)


def _strjoin(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    parts = _cellstrs(args[0], "strjoin")
    if len(args) < 2:
        return (_cv(" ".join(parts)),)
    d = args[1]
    if _is_cell(d):
        ds = _cellstrs(d, "strjoin")
        if len(ds) != max(len(parts) - 1, 0):
            raise _err("strjoin: the number of delimiters must be one less than the number of strings.", "MATLAB:strjoin:WrongNumberOfDelimiterElements")
        out = "".join(p + (ds[i] if i < len(ds) else "") for i, p in enumerate(parts))
        return (_cv(out),)
    return (_cv(_escape(_text(d, "strjoin", "delimiter")).join(parts)),)


def _find_all(s, p):
    if not p or len(p) > len(s):
        return []
    return [i + 1 for i in range(len(s) - len(p) + 1) if s[i:i + len(p)] == p]


def _idx_val(idx):
    if not idx:
        return NDArrayValue(np.zeros((1, 0)))
    return NDArrayValue(np.array(idx, dtype=float).reshape(1, -1))


def _strfind(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    s, p = args[0], args[1]
    pat = _text(p, "strfind", "pattern")
    if _is_cell(s):
        g = _grid(s)
        for row in g:
            for x in row:
                if not _is_text(x):
                    raise _err("strfind: cell array input must contain only character vectors.", "MATLAB:strfind:InvalidCellInput")
        return (_mk_cell([[_idx_val(_find_all(x.text, pat)) for x in row] for row in g]),)
    return (_idx_val(_find_all(_text(s, "strfind", "first input"), pat)),)


# ----------------------------------------------------------- concat
def _strcat(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if any(_is_cell(a) for a in args):
        shape = None
        for a in args:
            if _is_cell(a) and a.shape != (1, 1):
                if shape is not None and a.shape != shape:
                    raise _err("strcat: all cell inputs must be the same size or scalar.", "MATLAB:strcat:InvalidInputSize")
                shape = a.shape
        shape = shape or (1, 1)
        r, c = shape
        out = []
        for i in range(r):
            row = []
            for j in range(c):
                txt = ""
                for a in args:
                    if _is_cell(a):
                        x = a.get(0, 0) if a.shape == (1, 1) else a.get(i, j)
                        txt += x.text
                    else:
                        txt += a.text  # char args keep whitespace when any input is a cell (MATLAB)
                row.append(_cv(txt))
            out.append(row)
        return (_mk_cell(out),)
    if all(_is_char(a) for a in args):
        rowsets = [list(a.rows) or [""] for a in args]
        n = max(len(r) for r in rowsets)
        if any(len(r) not in (1, n) for r in rowsets):
            raise _err("strcat: char inputs must have the same number of rows or be single rows.", "MATLAB:strcat:InvalidInputSize")
        lines = []
        for i in range(n):
            lines.append("".join((r[0] if len(r) == 1 else r[i]).rstrip(" \t\n\v\f\r\0") for r in rowsets))
        return (_cv(lines[0]) if n == 1 else _cv(rows=_pad(lines)),)
    # string arrays or numbers: MATLAB string concatenation keeps whitespace
    txt = "".join(a.text if _is_text(a) else "".join(chr(int(x)) for x in _num(a, "strcat").reshape(-1)) for a in args)
    if any(getattr(a, "is_string", False) for a in args):
        from openmatlab.runtime.char_value import CharValue

        try:
            return (CharValue.string(txt),)
        except AttributeError:
            pass
    return (_cv(txt),)


def _pad(lines):
    w = max([len(x) for x in lines] + [0])
    return [x.ljust(w) for x in lines]


def _strvcat(args, *, nargout=1):
    lines = []
    for a in args:
        if _is_cell(a):
            lines += [x for x in _cellstrs(a, "strvcat") if x]
        elif _is_text(a):
            lines += [r for r in a.rows if r]
        else:
            lines.append("".join(chr(int(x)) for x in _num(a, "strvcat").reshape(-1)))
    if not lines:
        return (_cv(""),)
    return (_cv(rows=_pad(lines)),)


def _blanks(args, *, nargout=1):
    n = _scalar(args[0], "blanks") if args else 0
    if n < 0 or n != math.floor(n):
        raise _err("blanks: N must be a non-negative integer.", "MATLAB:blanks:invalidInput")
    return (_cv(" " * int(n)),)


_WS = " \t\n\v\f\r\0"


def _deblank(args, *, nargout=1):
    a = args[0]
    if _is_cell(a):
        return (_mk_cell([[_deblank([x])[0] for x in row] for row in _grid(a)]),)
    if not _is_text(a):
        raise _err("deblank: input must be a character array or cell array of character vectors.", "MATLAB:deblank:NonStringInput")
    if len(a.rows) > 1:
        w = max([len(r.rstrip(_WS)) for r in a.rows] + [0])
        return (_cv(rows=[r[:w] for r in a.rows]),)
    return (_cv(a.text.rstrip(_WS)),)


# ----------------------------------------------------------- numbers <-> text
def _str2num(args, *, nargout=1):
    a = args[0] if args else None
    if not _is_text(a):
        raise _err("str2num: input must be a character vector or string scalar.", "MATLAB:str2num:InvalidArgument")
    src = ";".join(a.rows) if len(a.rows) > 1 else a.text
    from openmatlab.host.repl import ReplSession
    from openmatlab.runtime.session import Session

    from openmatlab.runtime import frames as _frames

    s = Session.create_default()
    try:
        with _frames.isolated():  # a nested session is its own base workspace
            ReplSession(s).run_line("__str2num_v__ = [" + src + "];")
        v = s.workspace.get("__str2num_v__")
        ok = True
    except BaseException:  # noqa: BLE001 - any failure means ok = false (MATLAB)
        v, ok = NDArrayValue(np.zeros((0, 0))), False
    return (v, NDArrayValue(np.array([[ok]])))[: max(nargout, 1)]


def _g(x, prec):
    if isinstance(x, (bool, np.bool_)):
        return "true" if x else "false"
    if isinstance(x, complex) or np.iscomplexobj(x):
        x = complex(x)
        re_, im = _g(x.real, prec), _g(abs(x.imag), prec)
        return f"{re_}{'-' if x.imag < 0 or (x.imag == 0 and math.copysign(1, x.imag) < 0) else '+'}{im}i"
    x = float(x)
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    s = "%.*g" % (prec, x)
    if "e" in s:
        m, e = s.split("e")
        s = f"{m}e{int(e):+03d}"
    return s


def _mat2str(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    a = args[0]
    prec = 15
    cls = False
    for x in args[1:]:
        if _is_text(x):
            if x.text.lower() == "class":
                cls = True
            else:
                raise _err(f"mat2str: unknown option '{x.text}'.", "MATLAB:mat2str:UnknownOption")
        else:
            prec = int(_scalar(x, "mat2str"))
    if _is_char(a):
        rows = ["'" + r.replace("'", "''") + "'" for r in a.rows] or ["''"]
        return (_cv(rows[0] if len(rows) == 1 else "[" + ";".join(rows) + "]"),)
    if _is_cell(a) or not hasattr(a, "backend_buffer"):
        raise _err("mat2str: input must be a 2-D numeric, logical or char array.", "MATLAB:mat2str:TwoDInput")
    b = np.asarray(a.backend_buffer())
    b = b.reshape(1, 1) if b.ndim == 0 else b
    if b.ndim > 2:
        raise _err("mat2str: input matrix must be 2-D.", "MATLAB:mat2str:TwoDInput")
    if b.dtype == np.bool_:
        fmt = lambda v: "true" if v else "false"  # noqa: E731
    elif np.issubdtype(b.dtype, np.integer):
        fmt = lambda v: str(int(v))  # noqa: E731
    else:
        fmt = lambda v: _g(v, prec)  # noqa: E731
    if b.size == 1:
        body = fmt(b.reshape(-1)[0])
    elif b.size == 0:
        body = "zeros(%d,%d)" % b.shape
    else:
        body = "[" + ";".join(" ".join(fmt(v) for v in row) for row in b.tolist()) + "]"
    if cls and b.dtype != np.bool_:
        cname = a.matlab_class() if hasattr(a, "matlab_class") else "double"
        body = f"{cname}({body})"
    return (_cv(body),)


def _round_half_away(b):
    return np.where(b >= 0, np.floor(b + 0.5), np.ceil(b - 0.5))


def _int2str(args, *, nargout=1):
    a = args[0]
    if _is_char(a):
        b = np.array([[ord(c) for c in r] for r in a.rows], dtype=float)
    else:
        b = _num(a, "int2str")
        if np.iscomplexobj(b):
            b = b.real
        b = b.astype(float)
    r = _round_half_away(b)
    from openmatlab.libs.numeric_builtins import BUILTINS

    return BUILTINS["num2str"]([NDArrayValue(r)], nargout=1)


def _digits_matrix(vals, base, ndig, fn):
    alpha = "0123456789ABCDEF"
    out = []
    for v in vals:
        if v < 0 or v != math.floor(v) or math.isnan(v):
            raise _err(f"{fn}: D must be a non-negative integer.", f"MATLAB:{fn}:NegativeInput" if v < 0 else f"MATLAB:{fn}:NonIntegerInput")
        n = int(v)
        s = ""
        while n:
            s = alpha[n % base] + s
            n //= base
        out.append(s or "0")
    w = max([len(s) for s in out] + [ndig])
    return [s.rjust(w, "0") for s in out]


def _twos(raw, base, ndig, fn):
    """dec2bin/dec2hex: non-integers truncate; negatives are two's complement in the smallest of
    8/16/32/64 bits that holds them (documented MATLAB behaviour since R2020a)."""
    ints = []
    for v in raw:
        if isinstance(v, float):
            if not math.isfinite(v):
                raise _err(f"{fn}: D must be finite.", f"MATLAB:{fn}:InvalidInput")
            v = int(v)  # truncation toward zero
        ints.append(int(v))
    strs = []
    for v in ints:
        if v < 0:
            w = next((b for b in (8, 16, 32, 64) if v >= -(1 << (b - 1))), 64)
            v = max(v, -(1 << 63)) + (1 << w)
        strs.append(np.base_repr(v, base) if v else "0")
    width = max(max(len(t) for t in strs), ndig)
    return [t.rjust(width, "0") for t in strs]


def _dec2base(fn, base):
    def f(args, *, nargout=1):
        if not args:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        buf = getattr(args[0], "backend_buffer", None)
        raw = np.asarray(buf()) if buf is not None and not _is_text(args[0]) else None
        if raw is not None and np.iscomplexobj(raw):
            raise _err(f"{fn}: input must be real.", f"MATLAB:{fn}:InvalidInput")
        if raw is not None and raw.size and (raw.dtype.kind in "iu" or np.any(raw < 0) or np.any(raw != np.trunc(raw))):
            ndig = int(_scalar(args[1], fn)) if len(args) > 1 else 0
            flat = raw.reshape(-1, order="F")
            vals = [int(x) for x in flat] if raw.dtype.kind in "iu" else [float(x) for x in flat.astype(float)]
            rows = _twos(vals, base, ndig, fn)
            return (_cv(rows[0]) if len(rows) == 1 else _cv(rows=rows),)
        vals = _num(args[0], fn).astype(float).reshape(-1, order="F").tolist()
        ndig = int(_scalar(args[1], fn)) if len(args) > 1 else 0
        if not vals:
            return (_cv(""),)
        rows = _digits_matrix(vals, base, ndig, fn)
        return (_cv(rows[0]) if len(rows) == 1 else _cv(rows=rows),)
    return f


def _base2dec(fn, base):
    valid = "01" if base == 2 else "0123456789abcdef"

    def f(args, *, nargout=1):
        a = args[0] if args else None
        if _is_cell(a):
            strs = _cellstrs(a, fn)
        elif _is_text(a):
            strs = list(a.rows)
        else:
            raise _err(f"{fn}: input must be a character array or cell array of character vectors.", f"MATLAB:{fn}:InputMustBeStringOrCellstr")
        out = []
        for s in strs:
            t = s.replace(" ", "").lower()
            if fn == "hex2dec" and t.startswith("0x"):
                t = t[2:]
            if fn == "bin2dec" and t.startswith("0b"):
                t = t[2:]
            if not t:
                out.append(0.0)
                continue
            if any(c not in valid for c in t):
                raise _err(f"{fn}: input contains invalid characters.", f"MATLAB:{fn}:IllegalHexadecimal" if base == 16 else "MATLAB:bin2dec:IllegalBinaryString")
            out.append(float(int(t, base)))
        if not out:
            return (NDArrayValue(np.zeros((0, 1))),)
        return (NDArrayValue(np.array(out).reshape(-1, 1)),)
    return f


def register(builtins: Dict[str, Callable]) -> None:
    table = {
        "strsplit": _strsplit, "strjoin": _strjoin, "strfind": _strfind, "strcat": _strcat,
        "strvcat": _strvcat, "str2num": _str2num, "mat2str": _mat2str, "int2str": _int2str,
        "dec2bin": _dec2base("dec2bin", 2), "dec2hex": _dec2base("dec2hex", 16),
        "bin2dec": _base2dec("bin2dec", 2), "hex2dec": _base2dec("hex2dec", 16),
        "blanks": _blanks, "deblank": _deblank,
    }
    for k, v in table.items():
        builtins.setdefault(k, v)


def _flip_wrap(name, orig):
    """fliplr/flipud/flip on char and cell arrays (MATLAB flips any array)."""

    def f(args, *, nargout=1):
        if args and (_is_char(args[0]) or _is_cell(args[0])):
            a = args[0]
            if _is_char(a):
                g = [list(r) for r in a.rows] or [[]]
            else:
                g = _grid(a)
            dim = {"fliplr": 2, "flipud": 1}.get(name)
            if dim is None:
                dim = int(_scalar(args[1], name)) if len(args) > 1 else (1 if len(g) > 1 else 2)
            if dim == 2:
                g = [row[::-1] for row in g]
            elif dim == 1:
                g = g[::-1]
            if _is_char(a):
                return (_cv(rows=["".join(r) for r in g]) if len(g) != 1 else _cv("".join(g[0])),)
            return (_mk_cell(g),)
        return orig(args, nargout=nargout)
    return f


def register_late(builtins: Dict[str, Callable]) -> None:
    for n in ("fliplr", "flipud", "flip"):
        if n in builtins:
            builtins[n] = _flip_wrap(n, builtins[n])
