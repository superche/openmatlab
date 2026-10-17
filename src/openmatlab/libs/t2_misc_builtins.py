"""linsolve, isstrprop, cplxpair, dsearchn (C-E5 #765 T2 burn-down).

Clean-room, NumPy only, against the documented MATLAB syntaxes.
"""

from __future__ import annotations

import unicodedata
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

from .burndown_builtins import _err, _is_text, _need


def _arr(v) -> np.ndarray:
    buf = getattr(v, "backend_buffer", None)
    if buf is None:
        raise _err(f"Expected a numeric array, not '{v.matlab_class()}'.", "MATLAB:invalidType")
    a = np.asarray(buf())
    return a.reshape(1, 1) if a.ndim == 0 else a


def _txt(v):
    return getattr(v, "text", None) if _is_text(v) else None


# ---- linsolve ----------------------------------------------------------------------------------

_LINSOLVE_FIELDS = ("LT", "UT", "UHESS", "SYM", "POSDEF", "RECT", "TRANSA")


def _linsolve(B: Dict[str, Callable]):
    def fn(args, *, nargout=1):
        _need(args, 2, "linsolve")
        A, b = args[0], args[1]
        transa = False
        if len(args) > 2:
            opts = args[2]
            if not getattr(opts, "is_struct", False):
                raise _err("linsolve: OPTS must be a structure.", "MATLAB:linsolve:InvalidOpts")
            for f in opts.fields:
                if f not in _LINSOLVE_FIELDS:
                    raise _err(f"linsolve: invalid option field '{f}'.", "MATLAB:linsolve:InvalidOpts")
            if "TRANSA" in opts.fields:
                transa = bool(np.all(_arr(opts.get("TRANSA"))))
        if transa:
            A = B["ctranspose"]([A], nargout=1)[0]
        x = B["mldivide"]([A, b], nargout=1)[0]
        if nargout < 2:
            return (x,)
        m, n = _arr(A).shape[:2]
        r = B["rcond"]([A], nargout=1)[0] if m == n else B["rank"]([A], nargout=1)[0]
        return (x, r)
    return fn


# ---- isstrprop ---------------------------------------------------------------------------------

def _graphic(c: str) -> bool:
    return c.isprintable() and not c.isspace()


_PROPS = {
    "alpha": str.isalpha,
    "alphanum": str.isalnum,
    "digit": lambda c: "0" <= c <= "9",
    "lower": str.islower,
    "upper": str.isupper,
    "wspace": str.isspace,
    "punct": lambda c: _graphic(c) and not c.isalnum(),
    "cntrl": lambda c: unicodedata.category(c) == "Cc",
    "graphic": _graphic,
    "graph": _graphic,
    "print": lambda c: _graphic(c) or c == " ",
    "xdigit": lambda c: c in "0123456789abcdefABCDEF",
}


def _isstrprop(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    _need(args, 2, "isstrprop")
    kind = (_txt(args[1]) or "").lower()
    if kind not in _PROPS:
        raise _err(f"isstrprop: unknown category '{_txt(args[1]) or ''}'.", "MATLAB:isstrprop:InvalidCategory")
    force = False
    for k in range(2, len(args) - 1, 2):
        if (_txt(args[k]) or "").lower() == "forcecelloutput":
            force = bool(np.all(_arr(args[k + 1])))
        else:
            raise _err("isstrprop: unknown option.", "MATLAB:isstrprop:InvalidOption")
    test = _PROPS[kind]

    def one(v):
        if getattr(v, "matlab_class", lambda: "")() == "char":
            rows = list(getattr(v, "rows", None) or [v.text])
            shape = v.shape
            out = np.array([[test(ch) for ch in r] for r in rows], dtype=bool).reshape(shape)
            return NDArrayValue(out)
        if getattr(v, "matlab_class", lambda: "")() == "string" and v.numel() == 1:
            s = str(v.data.flat[0])
            return NDArrayValue(np.array([[test(ch) for ch in s]], dtype=bool).reshape(1, len(s)))
        a = _arr(v)  # numbers are tested as character codes
        return NDArrayValue(np.vectorize(lambda x: test(chr(int(x))), otypes=[bool])(a) if a.size else a.astype(bool))

    v = args[0]
    if isinstance(v, CellValue):
        objs = v.to_obj()
        out = np.empty(objs.shape, dtype=object)
        for ix in np.ndindex(*objs.shape):
            out[ix] = one(objs[ix])
        return (CellValue.from_obj(out),)
    r = one(v)
    if force:
        o = np.empty((1, 1), dtype=object)
        o[0, 0] = r
        return (CellValue.from_obj(o),)
    return (r,)


# ---- cplxpair ----------------------------------------------------------------------------------

def _pair_vector(z: np.ndarray, tol: float) -> np.ndarray:
    z = np.asarray(z, dtype=complex)
    n = z.size
    if n == 0:
        return z
    realm = np.abs(z.imag) <= tol * np.abs(z)
    reals = np.sort(z[realm].real).astype(complex)
    cz = z[~realm]
    if cz.size % 2:
        raise _err("Complex numbers can't be paired.", "MATLAB:cplxpair:ComplexValuesPaired")
    order = np.argsort(cz.real, kind="stable")
    cz = list(cz[order])
    out = []
    while cz:
        a = cz.pop(0)
        best, k = None, -1
        for i, b in enumerate(cz):
            if abs(b - np.conj(a)) <= tol * max(abs(a), abs(b)):
                if best is None or abs(b - np.conj(a)) < abs(best - np.conj(a)):
                    best, k = b, i
        if best is None:
            raise _err("Complex numbers can't be paired.", "MATLAB:cplxpair:ComplexValuesPaired")
        cz.pop(k)
        lo, hi = (a, best) if a.imag < 0 else (best, a)
        re = (lo.real + hi.real) / 2
        im = abs(lo.imag - hi.imag) / 2
        out += [complex(re, -im), complex(re, im)]
    return np.array(out + list(reals), dtype=complex)


def _cplxpair(args, *, nargout=1):
    _need(args, 1, "cplxpair")
    z = _arr(args[0])
    tol = 100 * np.finfo(float).eps
    if len(args) > 1 and _arr(args[1]).size:
        tol = float(_arr(args[1]).reshape(-1)[0])
        if not 0 <= tol < 1:
            tol = 100 * np.finfo(float).eps
    if z.size == 0:
        return (NDArrayValue(z.copy()),)
    if len(args) > 2:
        dim = int(_arr(args[2]).reshape(-1)[0]) - 1
    else:
        dim = next((k for k, s in enumerate(z.shape) if s != 1), 0)
    zz = np.moveaxis(z.astype(complex), dim, -1)
    out = np.empty_like(zz)
    for ix in np.ndindex(*zz.shape[:-1]):
        out[ix] = _pair_vector(zz[ix], tol)
    out = np.moveaxis(out, -1, dim)
    if np.all(out.imag == 0):
        out = out.real
    return (NDArrayValue(np.ascontiguousarray(out)),)


# ---- dsearchn ----------------------------------------------------------------------------------

def _inside(p: np.ndarray, x: np.ndarray, tri: np.ndarray) -> bool:
    for simplex in tri:
        v = x[simplex]
        T = (v[1:] - v[0]).T
        try:
            lam = np.linalg.solve(T, p - v[0])
        except np.linalg.LinAlgError:
            continue
        if np.all(lam >= -1e-12) and lam.sum() <= 1 + 1e-12:
            return True
    return False


def _dsearchn(args, *, nargout=1):
    _need(args, 2, "dsearchn")
    x = _arr(args[0]).astype(float)
    if len(args) == 2:
        tri, xi, outval = None, _arr(args[1]).astype(float), None
    else:
        tri = _arr(args[1]).astype(int) - 1 if _arr(args[1]).size else None
        xi = _arr(args[2]).astype(float)
        outval = float(_arr(args[3]).reshape(-1)[0]) if len(args) > 3 else None
    if xi.shape[1] != x.shape[1]:
        raise _err("dsearchn: X and XI must have the same number of columns.", "MATLAB:dsearchn:DimensionMismatch")
    d2 = ((xi[:, None, :] - x[None, :, :]) ** 2).sum(-1)
    k = d2.argmin(axis=1)
    d = np.sqrt(d2[np.arange(xi.shape[0]), k])
    idx = (k + 1).astype(float)
    if outval is not None and tri is not None:
        for i in range(xi.shape[0]):
            if not _inside(xi[i], x, tri):
                idx[i], d[i] = outval, outval
    return (NDArrayValue(idx.reshape(-1, 1)), NDArrayValue(d.reshape(-1, 1)))[:max(1, nargout)]


def register(builtins: Dict[str, Callable]) -> None:
    builtins["linsolve"] = _linsolve(builtins)
    builtins["isstrprop"] = _isstrprop
    builtins["cplxpair"] = _cplxpair
    builtins["dsearchn"] = _dsearchn
