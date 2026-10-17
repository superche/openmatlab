"""Descriptive statistics (M3-E4, #628): quantile/prctile, moving-window statistics, histc.

quantile/prctile use MATLAB's default method: sorted, NaN-free data of length n
sit at cumulative probabilities ``(i - 0.5)/n``; p is linearly interpolated
between them and clamped to the min/max outside ``[0.5/n, 1 - 0.5/n]``.
Moving windows: a scalar k is centred (``k`` odd: ``(k-1)/2`` each side; even:
``k/2`` back, ``k/2 - 1`` forward); ``[kb kf]`` is explicit. Endpoints default
to 'shrink'; 'discard', 'fill' and a numeric fill value are supported, as are
'includenan'/'omitnan'. histc counts ``edges(k) <= x < edges(k+1)`` and the last
bin counts ``x == edges(end)``; the second output is the bin index (0 outside).
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _nd(a):
    a = np.asarray(a, dtype=float)
    return NDArrayValue(a.reshape(1, 1) if a.ndim == 0 else a)


def _arr(v, name):
    if getattr(v, "is_cell", False) or getattr(v, "is_struct", False) or getattr(v, "is_string", False):
        raise _err(f"Invalid data type. First argument to {name} must be numeric.", f"MATLAB:{name}:invalidInput")
    a = np.asarray(v.backend_buffer(), dtype=float)
    return a.reshape(1, 1) if a.ndim == 0 else a


def _text(v):
    t = getattr(v, "text", None)
    if t is None and getattr(v, "is_string", False):
        t = str(v.data.flat[0])
    return t


def _first_dim(a):
    for i, s in enumerate(a.shape):
        if s != 1:
            return i
    return 0


def _dim(v, name):
    d = np.asarray(v.backend_buffer(), dtype=float).reshape(-1)
    if d.size != 1 or d[0] < 1 or d[0] != int(d[0]):
        raise _err("Dimension argument must be a positive integer scalar.", f"MATLAB:{name}:invalidDim")
    return int(d[0]) - 1


def _pad(a, ax):
    while a.ndim <= ax:
        a = a[..., np.newaxis]
    return a


# -- quantile / prctile ------------------------------------------------------------------
def _q1(v, p):
    v = np.sort(v[~np.isnan(v)])
    n = v.size
    if n == 0:
        return np.full(p.shape, np.nan)
    if n == 1:
        return np.full(p.shape, v[0])
    return np.interp(p, (np.arange(1, n + 1) - 0.5) / n, v)  # np.interp clamps at both ends


def _quantile_impl(name, scale):
    def fn(args, *, nargout=1):
        if len(args) < 2:
            raise _err(f"Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
        a = _arr(args[0], name)
        p = np.asarray(args[1].backend_buffer(), dtype=float).reshape(-1) / scale
        if np.any(np.isnan(p)) or np.any(p < 0) or np.any(p > 1):
            lim = "[0,100]" if scale == 100 else "[0,1]"
            raise _err(f"P must be a scalar or a vector of values in the interval {lim}.", f"MATLAB:{name}:BadPercents")
        rest = [x for x in args[2:]]
        ax = None
        while rest:
            t = _text(rest[0])
            if t is not None and t.lower() == "method":
                if len(rest) < 2 or (_text(rest[1]) or "").lower() not in ("exact",):
                    raise _err("Only the 'exact' method is supported.", f"MATLAB:{name}:invalidMethod")
                rest = rest[2:]
                continue
            if t is not None and t.lower() == "all":
                a, ax = a.reshape(-1, 1), 0
            else:
                ax = _dim(rest[0], name)
            rest = rest[1:]
        if ax is None:
            ax = _first_dim(a)
        a = _pad(a, ax)
        moved = np.moveaxis(a, ax, -1)
        out = np.empty(moved.shape[:-1] + (p.size,))
        for idx in np.ndindex(moved.shape[:-1]):
            out[idx] = _q1(moved[idx], p)
        return [_nd(np.moveaxis(out, -1, ax))]

    return fn


# -- moving-window statistics ------------------------------------------------------------
def _reducers():
    def var(w, norm=0):
        if w.size == 1:
            return 0.0
        return np.var(w, ddof=0 if norm else 1) if w.size else np.nan

    return {
        "movmean": lambda w: np.mean(w) if w.size else np.nan,
        "movsum": np.sum,
        "movmedian": lambda w: np.median(w) if w.size else np.nan,
        "movmax": lambda w: np.max(w) if w.size else np.nan,
        "movmin": lambda w: np.min(w) if w.size else np.nan,
        "movprod": np.prod,
        "movvar": var,
        "movstd": lambda w, norm=0: np.sqrt(var(w, norm)),
        "movmad": lambda w: np.median(np.abs(w - np.median(w))) if w.size else np.nan,
    }


_RED = _reducers()


def _window(v, name):
    k = np.asarray(v.backend_buffer(), dtype=float).reshape(-1)
    if k.size == 1:
        if not k[0] > 0:
            raise _err("Window length must be a positive scalar or a two-element vector.", f"MATLAB:{name}:invalidWindow")
        kk = k[0]
        if kk == int(kk):
            kk = int(kk)
            return (kk // 2, kk // 2 - 1) if kk % 2 == 0 else ((kk - 1) // 2, (kk - 1) // 2)
        return int(np.floor(kk / 2)), int(np.floor(kk / 2))  # non-integer: floor(k/2) each side
    if k.size == 2 and np.all(k >= 0):
        return int(np.floor(k[0])), int(np.floor(k[1]))
    raise _err("Window length must be a positive scalar or a two-element vector.", f"MATLAB:{name}:invalidWindow")


def _moving(name):
    red = _RED[name]
    weighted = name in ("movvar", "movstd")  # movvar(A, k, w, dim): normalisation weight first

    def fn(args, *, nargout=1):
        if len(args) < 2:
            raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
        a = _arr(args[0], name)
        kb, kf = _window(args[1], name)
        kraw = np.asarray(args[1].backend_buffer(), dtype=float).reshape(-1)
        ax, endpoints, omit, norm, sp = None, "shrink", name in ("movmax", "movmin"), 0, None
        rest = list(args[2:])
        npos = 0
        while rest:
            t = _text(rest[0])
            if t is None:
                if weighted and npos == 0:
                    wv = np.asarray(rest[0].backend_buffer(), dtype=float).reshape(-1)
                    if wv.size > 1 or (wv.size == 1 and wv[0] not in (0, 1)):
                        raise _err("Normalization weight must be 0 or 1.", f"MATLAB:{name}:invalidWeight")
                    norm = int(wv[0]) if wv.size else 0
                else:
                    ax = _dim(rest[0], name)
                npos += 1
                rest = rest[1:]
                continue
            tl = t.lower()
            if tl in ("omitnan", "omitmissing"):
                omit, rest = True, rest[1:]
            elif tl in ("includenan", "includemissing"):
                omit, rest = False, rest[1:]
            elif tl == "endpoints" and len(rest) > 1:
                e = _text(rest[1])
                if e is None:
                    endpoints = float(np.asarray(rest[1].backend_buffer(), dtype=float).reshape(-1)[0])
                elif e.lower() in ("shrink", "discard", "fill"):
                    endpoints = e.lower()
                else:
                    raise _err("Endpoints must be 'shrink', 'discard', 'fill' or a numeric scalar.", f"MATLAB:{name}:invalidEndpoints")
                rest = rest[2:]
            elif tl == "samplepoints" and len(rest) > 1:
                sp = np.asarray(rest[1].backend_buffer(), dtype=float).reshape(-1)
                if sp.size > 1 and np.any(np.diff(sp) <= 0):
                    raise _err("Sample points must be sorted and contain unique elements.", f"MATLAB:{name}:SamplePointsNotSorted")
                rest = rest[2:]
            else:
                raise _err(f"Invalid option '{t}'.", f"MATLAB:{name}:invalidOption")
        if ax is None:
            ax = _first_dim(a)
        a = _pad(a, ax)
        moved = np.moveaxis(a, ax, -1)
        n = moved.shape[-1]
        if sp is not None and sp.size != n:
            raise _err("Sample points must have the same length as the operating dimension.", f"MATLAB:{name}:SamplePointsLength")
        if sp is not None:  # window [t - k/2, t + k/2) for scalar k, [t - kb, t + kf] for [kb kf]
            if kraw.size == 1:
                lo_t, hi_t, closed = sp - kraw[0] / 2, sp + kraw[0] / 2, False
            else:
                lo_t, hi_t, closed = sp - kraw[0], sp + kraw[1], True
            spans = [(int(np.searchsorted(sp, lo_t[i], "left")),
                      int(np.searchsorted(sp, hi_t[i], "right" if closed else "left")) - 1) for i in range(n)]
            edge = [lo_t[i] < sp[0] or hi_t[i] > sp[-1] for i in range(n)]
        else:
            spans = [(i - kb, i + kf) for i in range(n)]
            edge = [lo < 0 or hi >= n for lo, hi in spans]
        out = np.empty(moved.shape)
        for idx in np.ndindex(moved.shape[:-1]):
            row = moved[idx]
            for i in range(n):
                lo, hi = spans[i]
                if edge[i] and endpoints != "shrink":
                    out[idx + (i,)] = np.nan if endpoints in ("fill", "discard") else endpoints
                    continue
                w = row[max(lo, 0):min(hi, n - 1) + 1]
                if omit:
                    w = w[~np.isnan(w)]
                out[idx + (i,)] = red(w, norm) if weighted else red(w)
        if endpoints == "discard":
            keep = [i for i in range(n) if not edge[i]]
            out = out[..., keep]
        return [_nd(np.moveaxis(out, -1, ax))]

    return fn


# -- histc -------------------------------------------------------------------------------
def _histc(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    a = _arr(args[0], "histc")
    e = np.asarray(args[1].backend_buffer(), dtype=float).reshape(-1)
    if e.size and np.any(np.diff(e) < 0):
        raise _err("Edge vector must be monotonically non-decreasing.", "MATLAB:histc:InvalidInput")
    ax = _dim(args[2], "histc") if len(args) > 2 else _first_dim(a)
    a = _pad(a, ax)
    m = e.size
    # bin index: last k with e[k] <= x, valid when x < e[k+1] or x == e[-1]
    k = np.searchsorted(e, a, side="right") - 1
    ok = (k >= 0) & ~np.isnan(a)
    if m:
        ok &= (k < m - 1) | (a == e[-1])
    k = np.where(ok, k, -1)
    moved = np.moveaxis(k, ax, -1)
    counts = np.zeros(moved.shape[:-1] + (m,))
    for idx in np.ndindex(moved.shape[:-1]):
        kk = moved[idx]
        counts[idx] = np.bincount(kk[kk >= 0], minlength=m)[:m]
    out = [_nd(np.moveaxis(counts, -1, ax))]
    if nargout > 1:
        out.append(_nd(k + 1))
    return out


def register(builtins: Dict[str, Callable]) -> None:
    builtins["quantile"] = _quantile_impl("quantile", 1.0)
    builtins["prctile"] = _quantile_impl("prctile", 100.0)
    for name in _RED:
        builtins[name] = _moving(name)
    builtins["histc"] = _histc
