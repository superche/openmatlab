"""Core math, statistics, random numbers and timing (Epic #534).

Number theory and difference operators, statistics (median, mode, std, var,
cov, corrcoef), the Mersenne-Twister ``rand`` stream (bit-identical to
MATLAB's default ``twister`` generator for the same ``rng`` seed), ``tic``/
``toc``/``pause``, and the everyday numeric helpers MATLAB code expects:
``isnan`` and friends, degree trig, ``cross``/``dot``/``kron``, ``trapz``,
polynomials, ``interp1``, ``filter``/``conv``, ``histcounts``/``accumarray``,
``fzero``/``fminsearch``/``integral``.
"""

from __future__ import annotations

import math
import time
from typing import Callable, Dict, Sequence

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _arr(v, fn) -> np.ndarray:
    if not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: expected a numeric argument", "MATLAB:invalidType")
    b = np.asarray(v.backend_buffer())
    if b.ndim == 0:
        b = b.reshape(1, 1)
    elif b.ndim == 1:
        b = b.reshape(1, -1)
    return b


def _f(v, fn) -> np.ndarray:
    b = _arr(v, fn)
    return b.astype(np.complex128) if np.iscomplexobj(b) else b.astype(np.float64)


def _out(a) -> NDArrayValue:
    a = np.asarray(a)
    if np.iscomplexobj(a) and not np.any(a.imag):
        a = a.real
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    if a.dtype != bool and not np.issubdtype(a.dtype, np.integer) and a.dtype != np.float32:
        a = a.astype(np.complex128 if np.iscomplexobj(a) else np.float64)
    return NDArrayValue(a)


def _bool(a) -> NDArrayValue:
    return _out(np.asarray(a, dtype=bool))


def _s(v, fn) -> float:
    b = _arr(v, fn).reshape(-1)
    if b.size != 1:
        raise _err(f"{fn}: expected a scalar", "MATLAB:expectedScalar")
    return float(np.real(b[0]))


def _is_text(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue) or getattr(v, "is_string", False)


def _txt(v):
    return v.text if hasattr(v, "text") else str(v.data.flat[0])


def _first_dim(a: np.ndarray) -> int:
    for k, d in enumerate(a.shape):
        if d != 1:
            return k
    return 0


def _dim_arg(a, args, pos, fn):
    """0-based axis from an optional 1-based ``dim`` at ``args[pos]``."""
    if len(args) > pos and not _is_text(args[pos]) and _arr(args[pos], fn).size:
        d = int(_s(args[pos], fn))
        if d < 1:
            raise _err(f"{fn}: Dimension argument must be a positive integer scalar.", "MATLAB:getdimarg:invalidDim")
        return d - 1
    return _first_dim(a)


def _pad_axis(a, ax):
    while a.ndim <= ax:
        a = a[..., None]
    return a


def _call(fh, x):
    out = fh.call([NDArrayValue(np.asarray(x, dtype=float).reshape(np.shape(x) if np.ndim(x) == 2 else (1, -1) if np.ndim(x) else (1, 1)))], nargout=1)
    if not out:
        raise _err("function handle returned no value")
    return np.asarray(out[0].backend_buffer(), dtype=float)


# ----------------------------------------------------------------- elementwise
def _unary(fn, op):
    def f(args, *, nargout=1):
        if len(args) != 1:
            raise _err("Not enough input arguments." if not args else "Too many input arguments.",
                       "MATLAB:minrhs" if not args else "MATLAB:TooManyInputs")
        b = _arr(args[0], fn)
        with np.errstate(all="ignore"):
            return (_out(op(b)),)
    return f


def _fix(b):
    if np.issubdtype(b.dtype, np.integer) or b.dtype == bool:
        return b
    if np.iscomplexobj(b):
        return np.trunc(b.real) + 1j * np.trunc(b.imag)
    return np.trunc(b)


def _sign(b):
    if np.iscomplexobj(b):
        m = np.abs(b)
        return np.where(m == 0, 0, b / np.where(m == 0, 1, m))
    return np.sign(b.astype(float)) if b.dtype == bool else np.sign(b)


def _isnan(b):
    return np.isnan(b) if np.issubdtype(b.dtype, np.inexact) else np.zeros(b.shape, bool)


def _isinf(b):
    return np.isinf(b) if np.issubdtype(b.dtype, np.inexact) else np.zeros(b.shape, bool)


def _isfinite(b):
    return np.isfinite(b) if np.issubdtype(b.dtype, np.inexact) else np.ones(b.shape, bool)


def _binary(fn, op):
    def f(args, *, nargout=1):
        if len(args) != 2:
            raise _err(f"{fn}: expected two inputs", "MATLAB:minrhs" if len(args) < 2 else "MATLAB:TooManyInputs")
        a, b = _arr(args[0], fn), _arr(args[1], fn)
        try:
            np.broadcast_shapes(a.shape, b.shape)
        except ValueError:
            raise _err("Arrays have incompatible sizes for this operation.", "MATLAB:sizeDimensionsMustMatch") from None
        with np.errstate(all="ignore"):
            return (_out(op(a, b)),)
    return f


def _rem(a, b):
    if np.issubdtype(a.dtype, np.integer) or np.issubdtype(b.dtype, np.integer):
        dt = a.dtype if np.issubdtype(a.dtype, np.integer) else b.dtype
        af, bf = a.astype(float), b.astype(float)
        r = np.where(bf == 0, af, np.fmod(af, np.where(bf == 0, 1, bf)))
        return r.astype(dt)
    a, b = a.astype(float), b.astype(float)
    r = np.fmod(a, b)
    # MATLAB: rem(x, 0) is NaN; rem(x, Inf) is x for finite x
    r = np.where(np.isinf(b) & np.isfinite(a), a, r)
    return r


def _sind(b):
    b = b.astype(float)
    r = np.sin(np.deg2rad(np.mod(b, 360)))
    k = np.mod(b, 180) == 0
    r = np.where(k, 0.0, r)
    r = np.where(np.mod(b, 360) == 90, 1.0, r)
    return np.where(np.mod(b, 360) == 270, -1.0, r)


def _cosd(b):
    b = b.astype(float)
    r = np.cos(np.deg2rad(np.mod(b, 360)))
    r = np.where(np.mod(b - 90, 180) == 0, 0.0, r)
    r = np.where(np.mod(b, 360) == 0, 1.0, r)
    return np.where(np.mod(b, 360) == 180, -1.0, r)


def _tand(b):
    b = b.astype(float)
    m = np.mod(b, 180)
    r = np.tan(np.deg2rad(m))
    r = np.where(m == 0, 0.0, r)
    r = np.where(m == 90, np.inf * np.where(np.mod(b, 360) == 90, 1, -1), r)
    return np.where(m == 45, 1.0, np.where(m == 135, -1.0, r))


def _log2(args, *, nargout=1):
    b = _arr(args[0], "log2").astype(float) if not np.iscomplexobj(_arr(args[0], "log2")) else _arr(args[0], "log2")
    if nargout >= 2:
        f, e = np.frexp(np.real(b))
        return (_out(f), _out(e.astype(float)))
    with np.errstate(all="ignore"):
        if not np.iscomplexobj(b) and np.any(b < 0):
            b = b.astype(complex)
        return (_out(np.log2(b)),)


def _nthroot(args, *, nargout=1):
    x, n = _arr(args[0], "nthroot").astype(float), _arr(args[1], "nthroot").astype(float)
    if np.any((x < 0) & ((np.mod(n, 2) != 1) | (n != np.round(n)))):
        raise _err("If X is negative, N must be an odd integer.", "MATLAB:nthroot:NegXNotOddIntN")
    with np.errstate(all="ignore"):
        y = np.sign(x) * np.abs(x) ** (1.0 / n)
        # one Newton step for exact integer roots (MATLAB corrects the same way)
        corr = (y ** n - x) / (n * y ** (n - 1))
        y = np.where(np.isfinite(corr) & (y != 0), y - corr, y)
    return (_out(y),)


def _gcd_arr(a, b):
    a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
    if np.any(a != np.round(a)) or np.any(b != np.round(b)):
        raise _err("Inputs must be real integers.", "MATLAB:gcd:NonIntInputs")
    return np.gcd(np.abs(a).astype(np.int64), np.abs(b).astype(np.int64)).astype(float)


def _lcm_arr(a, b):
    g = _gcd_arr(a, b)
    a, b = np.broadcast_arrays(np.abs(np.asarray(a, float)), np.abs(np.asarray(b, float)))
    with np.errstate(all="ignore"):
        return np.where(g == 0, 0, a / np.where(g == 0, 1, g) * b)


def _primes(args, *, nargout=1):
    n = int(math.floor(_s(args[0], "primes")))
    if n < 2:
        return (_out(np.zeros((1, 0))),)
    sieve = np.ones(n + 1, bool)
    sieve[:2] = False
    for p in range(2, int(n ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p::p] = False
    return (_out(np.nonzero(sieve)[0].astype(float).reshape(1, -1)),)


def _isprime_scalar(n: float) -> bool:
    if n != math.floor(n) or n < 2:
        return False
    n = int(n)
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    r = int(math.isqrt(n))
    for k in range(3, r + 1, 2):
        if n % k == 0:
            return False
    return True


def _isprime(args, *, nargout=1):
    b = _arr(args[0], "isprime").astype(float)
    if np.any(b < 0) or np.any(b != np.round(b)):
        raise _err("All entries must be non-negative integers.", "MATLAB:isprime:InputNotPosInt")
    return (_bool(np.vectorize(_isprime_scalar, otypes=[bool])(b) if b.size else b.astype(bool)),)


def _factor(args, *, nargout=1):
    n = _s(args[0], "factor")
    if n < 0 or n != math.floor(n):
        raise _err("Input must be a nonnegative integer.", "MATLAB:factor:InputNotPosInt")
    n = int(n)
    if n < 4:
        return (_out(np.array([[float(n)]])),)
    out, p = [], 2
    while p * p <= n:
        while n % p == 0:
            out.append(float(p))
            n //= p
        p += 1 if p == 2 else 2
    if n > 1:
        out.append(float(n))
    return (_out(np.array([out])),)


def _nchoosek(args, *, nargout=1):
    v, k = _arr(args[0], "nchoosek"), int(_s(args[1], "nchoosek"))
    if v.size == 1:
        n = float(v.reshape(-1)[0])
        if n != math.floor(n) or n < 0 or k < 0 or k > n:
            raise _err("K must be an integer between 0 and N.", "MATLAB:nchoosek:KOutOfRange")
        return (_out(float(math.comb(int(n), k))),)
    from itertools import combinations

    flat = v.reshape(-1, order="F")
    rows = list(combinations(flat.tolist(), k))
    return (_out(np.array(rows, dtype=v.dtype if v.dtype != bool else float).reshape(len(rows), k)),)


def _factorial(args, *, nargout=1):
    b = _arr(args[0], "factorial").astype(float)
    if np.any(b < 0) or np.any(b != np.floor(b)):
        raise _err("N must be an array of real non-negative integers.", "MATLAB:factorial:NNegativeInt")
    with np.errstate(over="ignore"):
        r = np.vectorize(lambda x: float(math.factorial(int(x))) if x <= 170 else np.inf, otypes=[float])(b) if b.size else b
    return (_out(r),)


def _round_n(orig):
    def f(args, *, nargout=1):
        if len(args) <= 1:
            return orig(args, nargout=nargout)
        x = _arr(args[0], "round")
        n = int(_s(args[1], "round"))
        mode = _txt(args[2]).lower() if len(args) > 2 else "decimals"
        if np.issubdtype(x.dtype, np.integer):
            xf = x.astype(float)
        else:
            xf = x.astype(np.complex128 if np.iscomplexobj(x) else float)

        def rnd(v):
            if mode.startswith("sig"):
                with np.errstate(all="ignore"):
                    mag = np.where(v == 0, 0, np.floor(np.log10(np.abs(np.where(v == 0, 1, v)))))
                d = n - 1 - mag
            else:
                d = np.full(v.shape, float(n))
            s = 10.0 ** d
            with np.errstate(all="ignore"):
                r = np.sign(v) * np.floor(np.abs(v) * s + 0.5) / s
                # guard: representation error (2.675*100 = 267.49999...)
                alt = np.sign(v) * np.floor(np.round(np.abs(v) * s, 9) + 0.5) / s
            return np.where(np.isfinite(r), alt, v)

        if np.iscomplexobj(xf):
            res = rnd(xf.real) + 1j * rnd(xf.imag)
        else:
            res = rnd(xf)
        if np.issubdtype(x.dtype, np.integer):
            from openmatlab.numerics.intclass import saturate

            return (NDArrayValue(saturate(res, x.dtype)),)
        return (_out(res),)
    return f


# ----------------------------------------------------------------- differences / cumulative
def _diff(args, *, nargout=1):
    a = _arr(args[0], "diff")
    a = a.astype(float) if a.dtype == bool else a
    n = int(_s(args[1], "diff")) if len(args) > 1 and _arr(args[1], "diff").size else 1
    ax = _dim_arg(a, args, 2, "diff") if len(args) > 2 else None
    out = a
    for _ in range(n):
        axis = ax if ax is not None else _first_dim(out)
        if out.shape[axis] <= 1 and ax is None:
            if all(d <= 1 for d in out.shape):
                shp = list(out.shape)
                shp[axis] = 0
                return (_out(np.zeros(shp)),)
        out = np.diff(_pad_axis(out, axis), axis=axis)
    return (_out(out),)


def _cum(fn, op):
    def f(args, *, nargout=1):
        a = _arr(args[0], fn)
        a = a.astype(float) if a.dtype == bool else a
        int_dt = a.dtype if np.issubdtype(a.dtype, np.integer) else None
        if int_dt is not None:
            a = a.astype(float)  # computed in double, saturated back (MATLAB integer rules)
        ax = _dim_arg(a, args, 1, fn)
        rev = any(_is_text(x) and _txt(x).lower() == "reverse" for x in args[1:])
        a = _pad_axis(a, ax)
        src = np.flip(a, axis=ax) if rev else a
        if fn in ("cummax", "cummin"):
            # NaNs are skipped (MATLAB): carry the running value
            fill = -np.inf if fn == "cummax" else np.inf
            work = np.where(np.isnan(src), fill, src) if np.issubdtype(src.dtype, np.floating) else src
            r = op(work, axis=ax)
            if np.issubdtype(src.dtype, np.floating):
                seen = np.logical_or.accumulate(~np.isnan(src), axis=ax)
                r = np.where(seen, r, np.nan)
        else:
            r = op(src, axis=ax)
        if rev:
            r = np.flip(r, axis=ax)
        if int_dt is not None:
            from openmatlab.numerics.intclass import saturate

            return (NDArrayValue(saturate(r, int_dt)),)
        return (_out(r),)
    return f


# ----------------------------------------------------------------- statistics
def _flags(args):
    return {_txt(x).lower() for x in args if _is_text(x)}


def _nums(args):
    return [x for x in args if not _is_text(x)]


def _reduce(fn, a, ax, op, omit):
    a = _pad_axis(a, ax)
    if a.shape[ax] == 0:
        shp = list(a.shape)
        shp[ax] = 1
        return np.full(shp, np.nan)
    if omit:
        return op(a, axis=ax, keepdims=True, omit=True)
    return op(a, axis=ax, keepdims=True, omit=False)


def _median(args, *, nargout=1):
    a = _f(args[0], "median")
    omit = "omitnan" in _flags(args)
    nums = _nums(args[1:])
    if "all" in _flags(args):
        a, ax = a.reshape(-1, 1, order="F"), 0
    else:
        ax = int(_s(nums[0], "median")) - 1 if nums else _first_dim(a)
    if a.size == 0 and not nums and "all" not in _flags(args):
        return (_out(np.array([[np.nan]])),)

    def op(x, axis, keepdims, omit):
        with np.errstate(all="ignore"):
            if omit:
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    return np.nanmedian(x, axis=axis, keepdims=keepdims)
            return np.median(x, axis=axis, keepdims=keepdims)

    return (_out(_reduce("median", a, ax, op, omit)),)


def _mode(args, *, nargout=1):
    a = _arr(args[0], "mode")
    nums = _nums(args[1:])
    if a.shape == (0, 0) and not nums:
        a = a.reshape(0, 1)
    ax = int(_s(nums[0], "mode")) - 1 if nums else _first_dim(a)
    a = _pad_axis(a, ax)
    moved = np.moveaxis(a, ax, -1)
    shp = list(moved.shape[:-1]) + [1]
    flat = moved.reshape(-1, moved.shape[-1]) if moved.size else np.zeros((int(np.prod(shp)), 0), a.dtype)
    m, fq, cs = [], [], []
    for row in flat:
        r = row[~np.isnan(row)] if np.issubdtype(row.dtype, np.floating) else row
        if r.size == 0:
            m.append(np.nan if not np.issubdtype(a.dtype, np.integer) else 0)
            fq.append(0.0)
            cs.append(np.full((1, 1), np.nan, dtype=float if a.dtype == bool else a.dtype)
                      if np.issubdtype(a.dtype, np.floating) or a.dtype == bool else np.zeros((0, 0), a.dtype))
            continue
        vals, cnt = np.unique(r, return_counts=True)
        k = int(np.argmax(cnt))  # unique sorts ascending: ties -> smallest (MATLAB)
        m.append(vals[k])
        fq.append(float(cnt[k]))
        cs.append(vals[cnt == cnt[k]].reshape(-1, 1))
    dt = a.dtype if a.dtype != bool else float
    M = np.moveaxis(np.array(m, dtype=dt).reshape(shp), -1, ax)
    F = np.moveaxis(np.array(fq).reshape(shp), -1, ax)
    outs = [_out(M) if not np.issubdtype(a.dtype, np.integer) else NDArrayValue(M), _out(F)]
    if nargout > 2:
        from openmatlab.runtime.cell_value import CellValue

        idx = np.moveaxis(np.arange(len(cs)).reshape(shp), -1, ax)
        idx2 = idx.reshape(idx.shape[0], -1, order="F") if idx.ndim > 2 else idx
        rows = tuple(tuple(_out(cs[int(idx2[i, j])]) if cs[int(idx2[i, j])].dtype.kind != "i" and
                           cs[int(idx2[i, j])].dtype.kind != "u" else NDArrayValue(cs[int(idx2[i, j])])
                           for j in range(idx2.shape[1])) for i in range(idx2.shape[0]))
        outs.append(CellValue(rows=rows))
    return tuple(outs[:max(1, nargout)])


def _var_core(a, w, ax, omit):
    """(variance, mean) along ``ax``; ``w`` is 0, 1 or a weight vector."""
    if isinstance(w, np.ndarray) and w.ndim >= 2 and w.size == a.size and w.size != a.shape[ax] and \
            tuple(w.shape) + (1,) * (a.ndim - w.ndim) == tuple(a.shape) + (1,) * (w.ndim - a.ndim):
        if np.any(w < 0):  # a weight array the same size as A (documented form)
            raise _err("Weights must be non-negative and match the dimension length.", "MATLAB:var:invalidWgts")
        a = _pad_axis(a, ax)
        ww = w.reshape(a.shape)
        return _var_weighted(a, ww, ax, omit)
    a = _pad_axis(a, ax)
    if isinstance(w, np.ndarray):
        wv = w.reshape(-1)
        if wv.size != a.shape[ax] or np.any(wv < 0):
            raise _err("Weights must be non-negative and match the dimension length.", "MATLAB:var:invalidWgts")
        shp = [1] * a.ndim
        shp[ax] = -1
        return _var_weighted(a, wv.reshape(shp), ax, omit)
    return _var_plain(a, w, ax, omit)


def _var_weighted(a, ww, ax, omit):
    if True:
        if omit:
            ww = np.where(np.isnan(a), 0.0, ww)
            a0 = np.where(np.isnan(a), 0.0, a)
        else:
            ww, a0 = np.broadcast_to(ww, a.shape), a
        with np.errstate(all="ignore"):
            sw = np.sum(ww, axis=ax, keepdims=True)
            mu = np.sum(ww * a0, axis=ax, keepdims=True) / sw
            return np.sum(ww * np.abs(a0 - mu) ** 2, axis=ax, keepdims=True) / sw, mu


def _var_plain(a, w, ax, omit):
    if a.shape[ax] == 0:
        shp = list(a.shape)
        shp[ax] = 1
        return np.full(shp, np.nan), np.full(shp, np.nan)
    with np.errstate(all="ignore"):
        if omit:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                n = np.sum(~np.isnan(a), axis=ax, keepdims=True)
                mu = np.nanmean(a, axis=ax, keepdims=True)
                ss = np.nansum(np.abs(a - mu) ** 2, axis=ax, keepdims=True)
                ss = np.where(n == 0, np.nan, ss)
        else:
            n = a.shape[ax]
            mu = np.mean(a, axis=ax, keepdims=True)
            ss = np.sum(np.abs(a - mu) ** 2, axis=ax, keepdims=True)
        den = n - 1 if w == 0 else n
        den = np.where(np.asarray(n) == 1, 1, den)  # one sample: variance 0 (MATLAB)
        return ss / den, mu


def _varstd(fn, root):
    def f(args, *, nargout=1):
        if not args:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        single = args[0].matlab_class() == "single"
        a = _f(args[0], fn)
        flags = _flags(args)
        nums = _nums(args[1:])
        w = 0
        if nums:
            wb = _arr(nums[0], fn)
            if wb.size == 0:
                w = 0
            elif wb.size == 1:
                w = float(wb.reshape(-1)[0])
                if w not in (0.0, 1.0):
                    raise _err(f"{fn}: W must be 0, 1, or a vector of weights.", "MATLAB:var:invalidWgts")
            else:
                w = wb.astype(float)
        shape_back = None
        if "all" in flags or (len(nums) > 1 and _arr(nums[1], fn).size > 1):
            dims = list(range(max(a.ndim, 2))) if "all" in flags else sorted({int(d) - 1 for d in _arr(nums[1], fn).reshape(-1)})
            nd0 = max(a.ndim, 2)
            dims = [d for d in dims if d < nd0] or [nd0]  # dimensions past ndims(A) are singleton
            if isinstance(w, np.ndarray) and w.size == a.size and w.size > 1 and dims != [nd0]:
                wa = w.reshape(a.shape + (1,) * (max(nd0, max(dims) + 1) - a.ndim))
            else:
                wa = None
            nd = max(a.ndim, max(dims) + 1)
            a = a.reshape(a.shape + (1,) * (nd - a.ndim))
            keep = [d for d in range(nd) if d not in dims]
            shape_back = [1 if d in dims else a.shape[d] for d in range(nd)]
            a = np.transpose(a, keep + dims).reshape([a.shape[d] for d in keep] + [-1], order="F")
            ax = a.ndim - 1
            if wa is not None:
                w = np.transpose(wa, keep + dims).reshape(a.shape, order="F")
            if isinstance(w, np.ndarray) and w.size != a.shape[ax] and w.shape != a.shape:
                raise _err("Weights must be non-negative and match the dimension length.", "MATLAB:var:invalidWgts")
        else:
            ax = int(_s(nums[1], fn)) - 1 if len(nums) > 1 else _first_dim(a)
            if a.size == 0 and len(nums) < 2 and a.shape == (0, 0):
                nan = np.array([[np.nan]], dtype=np.float32 if single else float)
                return (_out(nan), _out(nan))[:max(1, nargout)]
        if shape_back is None and ax >= max(a.ndim, 2):  # singleton dimension past ndims(A)
            if isinstance(w, np.ndarray) and w.size > 1:
                raise _err("Weights must be non-negative and match the dimension length.", "MATLAB:var:invalidWgts")
            v, mu = np.where(np.isnan(a), np.nan, 0.0) * (1 if not np.iscomplexobj(a) else 1), a
        else:
            v, mu = _var_core(a, w, ax, "omitnan" in flags)
        if shape_back is not None:
            v, mu = v.reshape(shape_back), mu.reshape(shape_back)
        r = np.sqrt(v) if root else v
        if single:
            r, mu = r.astype(np.complex64 if np.iscomplexobj(r) else np.float32), mu.astype(np.complex64 if np.iscomplexobj(mu) else np.float32)
        return (_out(r), _out(mu))[:max(1, nargout)]
    return f


def _cov(args, *, nargout=1):
    """cov(A), cov(A,B), cov(..., w), cov(..., nanflag) as documented."""
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    flags = _flags(args)
    bad = flags - {"includenan", "omitrows", "partialrows"}
    if bad:
        raise _err("cov: invalid option.", "MATLAB:cov:unknownFlag")
    nums = _nums(args)
    x = _f(nums[0], "cov")
    w = 0
    if len(nums) == 3:
        w = nums[2]
        nums = nums[:2]
    elif len(nums) == 2:
        b = _arr(nums[1], "cov")
        if b.size == 1 and float(np.real(b.reshape(-1)[0])) in (0.0, 1.0) and x.size >= 1 and \
                (x.size == 1 or b.size != x.size):
            w = nums[1]
            nums = nums[:1]
        elif b.size > 1 and x.ndim == 2 and min(x.shape) > 1 and b.size == x.shape[0] and b.ndim == 2 and min(b.shape) == 1 \
                and x.size != b.size:
            w = nums[1]
            nums = nums[:1]
    single = any(v.matlab_class() == "single" for v in nums)  # data inputs only; w does not set the class
    if len(nums) == 2:
        y = _f(nums[1], "cov")
        if y.size != x.size:
            raise _err("cov: X and Y must have the same number of elements.", "MATLAB:cov:XYlengthMismatch")
        x = np.column_stack([x.reshape(-1, order="F"), y.reshape(-1, order="F")])
    else:
        if x.ndim > 2:
            raise _err("cov: inputs must be 2-D.", "MATLAB:cov:InputDim")
        if x.ndim == 2 and x.shape[0] == 1:
            x = x.reshape(-1, 1)
    wv = _arr(w, "cov").astype(float).reshape(-1) if not isinstance(w, int) else np.array([float(w)])
    if wv.size == 1:
        wflag = float(wv[0])
        if wflag not in (0.0, 1.0):
            raise _err("cov: W must be 0, 1, or a vector of weights.", "MATLAB:cov:invalidWgts")
        wvec = None
    else:
        if wv.size != x.shape[0] or np.any(wv < 0):
            raise _err("cov: W must be 0, 1, or a vector of weights.", "MATLAB:cov:invalidWgts")
        wflag, wvec = 1.0, wv
    if len(nums) == 1 and _arr(nums[0], "cov").shape == (0, 0):
        c = np.array([[np.nan]])  # cov([]) is NaN
        return (_out(c.astype(np.float32) if single else c),)
    if x.shape[1] == 0:
        return (_out(np.zeros((0, 0), dtype=np.float32 if single else float)),)

    def one(xx, ww):
        n = xx.shape[0]
        if n == 0:
            return np.full((xx.shape[1], xx.shape[1]), np.nan)
        if ww is not None:
            sw = ww.sum()
            mu = (ww[:, None] * xx).sum(axis=0, keepdims=True) / sw
            xc = xx - mu
            return (xc.conj().T @ (ww[:, None] * xc)) / sw
        xc = xx - xx.mean(axis=0, keepdims=True)
        den = n - 1 if (wflag == 0 and n > 1) else n
        return (xc.conj().T @ xc) / den

    nanrow = np.isnan(x)
    with np.errstate(all="ignore"):
        if "omitrows" in flags:
            keep = ~nanrow.any(axis=1)
            c = one(x[keep], None if wvec is None else wvec[keep])
        elif "partialrows" in flags:
            m = x.shape[1]
            c = np.empty((m, m), dtype=x.dtype)
            for i in range(m):
                for j in range(i, m):
                    keep = ~(nanrow[:, i] | nanrow[:, j])
                    sub = x[keep][:, [i, j]] if i != j else x[keep][:, [i]]
                    cc = one(sub, None if wvec is None else wvec[keep])
                    c[i, j] = cc[0, -1]
                    c[j, i] = np.conj(cc[0, -1]) if i != j else cc[0, 0]
        else:
            c = one(x, wvec)
    if single:
        c = c.astype(np.complex64 if np.iscomplexobj(c) else np.float32)
    return (_out(c),)


def _corrcoef(args, *, nargout=1):
    c = np.asarray(_cov(args)[0].backend_buffer())
    d = np.sqrt(np.real(np.diag(c)))
    with np.errstate(all="ignore"):
        r = c / np.outer(d, d)
    r = np.clip(np.real(r), -1, 1) if not np.iscomplexobj(r) else r
    np.fill_diagonal(r, 1.0)
    return (_out(r),)


def _range(args, *, nargout=1):
    a = _f(args[0], "range")
    ax = _dim_arg(a, args, 1, "range")
    a = _pad_axis(a, ax)
    return (_out(np.nanmax(a, axis=ax, keepdims=True) - np.nanmin(a, axis=ax, keepdims=True)),)


def _bounds(args, *, nargout=1):
    a = _f(args[0], "bounds")
    ax = _dim_arg(a, args, 1, "bounds")
    a = _pad_axis(a, ax)
    return (_out(np.nanmin(a, axis=ax, keepdims=True)), _out(np.nanmax(a, axis=ax, keepdims=True)))


# ----------------------------------------------------------------- random numbers
class _RNG:
    seed = 0
    kind = "twister"
    rs = np.random.RandomState(5489)  # MATLAB default: twister, seed 0 == MT seed 5489


def _mt_seed(seed: int) -> int:
    return 5489 if seed == 0 else seed


def _rng(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue

    def state():
        st = _RNG.rs.get_state()
        return StructValue.scalar([
            ("Type", CharValue(_RNG.kind)), ("Seed", NDArrayValue(np.array([[float(_RNG.seed)]]))),
            ("State", NDArrayValue(np.append(st[1].astype(float), float(st[2])).reshape(-1, 1))),
        ])

    prev = state()
    if not args:
        return (prev,)
    a0 = args[0]
    if getattr(a0, "is_struct", False):
        e = a0.elems[0]
        stv = np.asarray(e["State"].backend_buffer()).reshape(-1)
        _RNG.seed = int(np.asarray(e["Seed"].backend_buffer()).reshape(-1)[0])
        _RNG.rs.set_state(("MT19937", stv[:624].astype(np.uint32), int(stv[624]), 0, 0.0))
        return (prev,) if nargout >= 1 else ()
    if _is_text(a0):
        w = _txt(a0).lower()
        if w == "default":
            _RNG.seed, _RNG.kind = 0, "twister"
        elif w == "shuffle":
            _RNG.seed = int(time.time() * 1e6) % (2 ** 32)
        else:
            raise _err(f"rng: unknown option '{w}'", "MATLAB:rng:badFirstOpt")
    else:
        s = _s(a0, "rng")
        if s < 0 or s != math.floor(s) or s >= 2 ** 32:
            raise _err("The seed must be a nonnegative integer less than 2^32.", "MATLAB:rng:badSeed")
        _RNG.seed = int(s)
    if len(args) > 1 and _is_text(args[1]):
        gen = _txt(args[1]).lower()
        if gen not in ("twister", "v5uniform", "v5normal", "v4"):
            raise _err(f"rng: generator '{gen}' is not supported; only 'twister'", "MATLAB:rng:unsupportedGenerator")
        _RNG.kind = "twister"
    _RNG.rs = np.random.RandomState(_mt_seed(_RNG.seed))
    return (prev,) if nargout >= 1 else ()


def _size_args(args, fn):
    from openmatlab.libs.numeric_builtins import _shapeN

    nums = [a for a in args if not _is_text(a)]
    texts = [_txt(a).lower() for a in args if _is_text(a)]
    if nums and any(_arr(x, fn).size > 1 for x in nums) and len(nums) == 1:
        shp = tuple(int(x) for x in _arr(nums[0], fn).reshape(-1))
    elif not nums:
        shp = (1, 1)
    elif len(nums) == 1:
        n = int(_s(nums[0], fn))
        shp = (n, n)
    else:
        shp = tuple(int(_s(x, fn)) for x in nums)
    shp = tuple(max(0, d) for d in shp)
    cls = "double"
    for t in texts:
        if t in ("single", "double"):
            cls = t
        elif t == "like":
            pass
        else:
            raise _err(f"{fn}: unsupported option '{t}'", "MATLAB:rand:invalidOption")
    return shp, cls


def _uniform(shp):
    n = int(np.prod(shp)) if shp else 1
    v = _RNG.rs.random_sample(n)
    return v.reshape(shp, order="F")  # column-major fill: same stream order as MATLAB


def _rand(args, *, nargout=1):
    shp, cls = _size_args(args, "rand")
    a = _uniform(shp)
    return (NDArrayValue(a.astype(np.float32)) if cls == "single" else _out(a),)


def _randn(args, *, nargout=1):
    shp, cls = _size_args(args, "randn")
    n = int(np.prod(shp)) if shp else 1
    a = _RNG.rs.standard_normal(n).reshape(shp, order="F")
    return (NDArrayValue(a.astype(np.float32)) if cls == "single" else _out(a),)


def _randi(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    lim = _arr(args[0], "randi").astype(float).reshape(-1)
    lo, hi = (1.0, lim[0]) if lim.size == 1 else (lim[0], lim[1])
    if hi < lo or lo != math.floor(lo) or hi != math.floor(hi):
        raise _err("The first input must be a positive integer or an interval of integers.", "MATLAB:randi:invalidLimits")
    shp, cls = _size_args(args[1:], "randi")
    u = _uniform(shp)
    r = lo + np.floor(u * (hi - lo + 1))
    return (_out(np.minimum(r, hi)),)


def _randperm(args, *, nargout=1):
    n = int(_s(args[0], "randperm"))
    k = int(_s(args[1], "randperm")) if len(args) > 1 else n
    if k > n or k < 0:
        raise _err("K must be less than or equal to N.", "MATLAB:randperm:inputKTooLarge")
    p = np.argsort(_RNG.rs.random_sample(n), kind="stable") + 1
    return (_out(p[:k].astype(float).reshape(1, -1)),)


# ----------------------------------------------------------------- timing
_TIC = {"t": None}


def _tic(args, *, nargout=1):
    now = time.perf_counter_ns()
    if nargout >= 1:
        return (NDArrayValue(np.array([[now]], dtype=np.uint64)),)
    _TIC["t"] = now
    return ()


def _toc(args, *, nargout=1):
    now = time.perf_counter_ns()
    if args:
        start = int(np.asarray(args[0].backend_buffer()).reshape(-1)[0])
    else:
        if _TIC["t"] is None:
            raise _err("You must call TIC without an output argument before calling TOC without an input argument.", "MATLAB:toc:callTicFirstNoInputs")
        start = _TIC["t"]
    el = (now - start) / 1e9
    if nargout >= 1:
        return (_out(el),)
    import sys

    sys.stdout.write(f"Elapsed time is {el:.6f} seconds.\n")
    return ()


def _pause(args, *, nargout=1):
    if not args:
        return ()
    if _is_text(args[0]):
        return ()  # pause on/off/query: no state to model
    s = _s(args[0], "pause")
    if s < 0 or not np.isfinite(s):
        raise _err("pause: time must be a nonnegative finite number", "MATLAB:pause:invalidInput")
    time.sleep(min(s, 3600.0))
    return ()


# ----------------------------------------------------------------- vectors / polynomials
def _vec(v, fn):
    return _f(v, fn).reshape(-1, order="F")


def _cross(args, *, nargout=1):
    a, b = _f(args[0], "cross"), _f(args[1], "cross")
    if a.shape != b.shape:
        raise _err("A and B must be of the same size.", "MATLAB:cross:InputSizeMismatch")
    ax = _dim_arg(a, args, 2, "cross") if len(args) > 2 else next((k for k, d in enumerate(a.shape) if d == 3), None)
    if ax is None or a.shape[ax] != 3:
        raise _err("A and B must have at least one dimension of length 3.", "MATLAB:cross:InvalidDimAorB")
    return (_out(np.cross(a, b, axis=ax)),)


def _dot(args, *, nargout=1):
    a, b = _f(args[0], "dot"), _f(args[1], "dot")
    if a.size == b.size and (min(a.shape) == 1 and min(b.shape) == 1):
        return (_out(np.vdot(a.reshape(-1), b.reshape(-1))),)
    if a.shape != b.shape:
        raise _err("A and B must be the same size.", "MATLAB:dot:InputSizeMismatch")
    ax = _dim_arg(a, args, 2, "dot")
    return (_out(np.sum(np.conj(a) * b, axis=ax, keepdims=True)),)


def _kron(args, *, nargout=1):
    from openmatlab.numerics import sparse as _sp

    if len(args) != 2:
        raise _err("kron: expected 2 arguments")
    if _sp.is_sparse(args[0]) or _sp.is_sparse(args[1]):
        out = _sp.kron(args[0], args[1])
        if out is not None:
            return (out,)
    return (_out(np.kron(_f(args[0], "kron"), _f(args[1], "kron"))),)


def _trapz_xy(args, fn):
    """trapz(Y), trapz(X,Y), trapz(...,dim): X is scalar spacing, a coordinate vector, or Y-sized."""
    if not args or len(args) > 3:
        raise _err(f"{fn}: wrong number of input arguments.", "MATLAB:narginchk:tooManyInputs" if args else "MATLAB:minrhs")
    dim = None
    if len(args) == 3:
        x, y, dim = _f(args[0], fn), _f(args[1], fn), args[2]
    elif len(args) == 2:
        a0, a1 = _f(args[0], fn), _f(args[1], fn)
        if a1.size == 1 and a0.size != 1:  # trapz(Y, dim)
            x, y, dim = None, a0, args[1]
        else:
            x, y = a0, a1
    else:
        x, y = None, _f(args[0], fn)
    if dim is not None:
        ax = int(_s(dim, fn)) - 1
        if ax < 0:
            raise _err(f"{fn}: DIM must be a positive integer.", "MATLAB:getdimarg:dimensionMustBePositiveInteger")
    else:
        ax = _first_dim(y)
    y = _pad_axis(y, ax)
    n = y.shape[ax]
    if x is None:
        sp = np.ones(max(n - 1, 0))
    elif x.size == 1:
        sp = np.full(max(n - 1, 0), float(np.real(x.reshape(-1)[0])) if not np.iscomplexobj(x) else x.reshape(-1)[0])
    elif x.ndim <= 2 and min(x.shape) == 1 and x.size == n:
        sp = np.diff(x.reshape(-1))
    elif x.shape == y.shape or (x.ndim < y.ndim and x.shape + (1,) * (y.ndim - x.ndim) == y.shape):
        sp = np.diff(x.reshape(y.shape), axis=ax)
        return sp, y, ax
    else:
        raise _err(f"{fn}: length of X and length of Y along DIM must match.", "MATLAB:trapz:LengthXMismatch")
    shp = [1] * y.ndim
    shp[ax] = -1
    return sp.reshape(shp), y, ax


def _trapz_seg(args, fn):
    sp, y, ax = _trapz_xy(args, fn)
    n = y.shape[ax]
    lo = np.take(y, range(0, n - 1), axis=ax)
    hi = np.take(y, range(1, n), axis=ax)
    return (lo + hi) / 2.0 * sp, y, ax


def _trapz(args, *, nargout=1):
    seg, y, ax = _trapz_seg(args, "trapz")
    return (_out(np.sum(seg, axis=ax, keepdims=True)),)


def _cumtrapz(args, *, nargout=1):
    seg, y, ax = _trapz_seg(args, "cumtrapz")
    zshape = list(y.shape)
    zshape[ax] = min(1, y.shape[ax])
    r = np.concatenate([np.zeros(zshape, dtype=seg.dtype), np.cumsum(seg, axis=ax)], axis=ax)
    return (_out(r),)


def _polyval(args, *, nargout=1):
    p, x = _vec(args[0], "polyval"), _f(args[1], "polyval")
    return (_out(np.polyval(p, x) if p.size else np.zeros(x.shape)),)


def _polyfit(args, *, nargout=1):
    x, y, n = _vec(args[0], "polyfit"), _vec(args[1], "polyfit"), int(_s(args[2], "polyfit"))
    if x.size != y.size:
        raise _err("The first two inputs must have the same number of elements.", "MATLAB:polyfit:XYSizeMismatch")
    V = np.vander(x, n + 1)
    p, *_ = np.linalg.lstsq(V, y, rcond=None)
    if x.size <= n:
        from openmatlab.runtime import warnings as _w

        _w.emit("Polynomial is not unique; degree >= number of data points.", "MATLAB:polyfit:PolyNotUnique")
    return (_out(np.real_if_close(p).reshape(1, -1)),)


def _roots(args, *, nargout=1):
    p = _vec(args[0], "roots")
    if p.size and not np.all(np.isfinite(p)):
        raise _err("Input to ROOTS must not contain NaN or Inf.", "MATLAB:roots:NonFiniteInput")
    r = np.roots(p) if p.size else np.zeros(0)
    return (_out(r.reshape(-1, 1)),)


def _conv(args, *, nargout=1):
    a, b = _f(args[0], "conv"), _f(args[1], "conv")
    shape = _txt(args[2]).lower() if len(args) > 2 else "full"
    av, bv = a.reshape(-1, order="F"), b.reshape(-1, order="F")
    c = np.convolve(av, bv)
    if shape == "same":
        start = (bv.size - 1) // 2 + ((bv.size - 1) % 2)
        start = int(np.ceil((bv.size - 1) / 2))
        c = c[start:start + av.size]
    elif shape == "valid":
        c = c[bv.size - 1: av.size] if av.size >= bv.size else np.zeros(0)
    col = a.shape[0] > 1 and a.shape[1] == 1 if a.ndim == 2 else False
    return (_out(c.reshape(-1, 1) if col else c.reshape(1, -1)),)


def _deconv(args, *, nargout=1):
    y, a = _vec(args[0], "deconv"), _vec(args[1], "deconv")
    if a.size == 0 or a[0] == 0:
        raise _err("First coefficient of A must be non-zero.", "MATLAB:deconv:ZeroCoef1")
    if y.size < a.size:
        return (_out(np.zeros((1, 1))), _out(y.reshape(1, -1)))
    q, r = np.polydiv(y, a)
    rr = np.zeros(y.size)
    rr[y.size - r.size:] = r
    return (_out(q.reshape(1, -1)), _out(rr.reshape(1, -1)))


def _filter(args, *, nargout=1):
    b, a, x = _vec(args[0], "filter"), _vec(args[1], "filter"), _f(args[2], "filter")
    if a.size == 0 or a[0] == 0:
        raise _err("First denominator filter coefficient must be non-zero.", "MATLAB:filter:firstCoeffNotNonZero")
    b, a = b / a[0], a / a[0]
    n = max(a.size, b.size)
    b = np.pad(b, (0, n - b.size))
    a = np.pad(a, (0, n - a.size))
    ax = _first_dim(x)
    xs = np.moveaxis(_pad_axis(x, ax), ax, 0)
    y = np.zeros(xs.shape, dtype=np.result_type(xs, b, a))
    z = np.zeros((n,) + xs.shape[1:], dtype=y.dtype)
    if len(args) > 3 and _arr(args[3], "filter").size:
        zi = _vec(args[3], "filter")
        z[: zi.size] = zi.reshape((-1,) + (1,) * (xs.ndim - 1))
    for k in range(xs.shape[0]):  # direct form II transposed (MATLAB's filter)
        y[k] = b[0] * xs[k] + z[0]
        for j in range(1, n):
            z[j - 1] = b[j] * xs[k] + z[j] - a[j] * y[k]
    zf = z[: n - 1]
    return (_out(np.moveaxis(y, 0, ax)), _out(zf.reshape(-1, 1) if xs.ndim == 2 and xs.shape[1] == 1 else zf))


def _interp1(args, *, nargout=1):
    texts = [_txt(a).lower() for a in args if _is_text(a)]
    nums = _nums(args)
    method = next((t for t in texts if t in ("linear", "nearest", "previous", "next", "pchip", "spline", "cubic")), "linear")
    extrap = "extrap" in texts
    if len(nums) == 2:
        y = _f(nums[0], "interp1")
        xi = _f(nums[1], "interp1")
        x = np.arange(1, y.reshape(-1).size + 1, dtype=float)
        extrapval = np.nan
    else:
        x, y, xi = _vec(nums[0], "interp1"), _f(nums[1], "interp1"), _f(nums[2], "interp1")
        extrapval = _s(nums[3], "interp1") if len(nums) > 3 else np.nan
    yv = y.reshape(-1, order="F") if min(y.shape) == 1 else None
    if yv is None:
        raise _err("interp1: matrix Y is not supported yet", "MATLAB:interp1:unsupported")
    if x.size != yv.size:
        raise _err("The grid vectors must contain unique points and match Y.", "MATLAB:interp1:YInvalidNumRows")
    order = np.argsort(x, kind="stable")
    x, yv = x[order], yv[order]
    if np.any(np.diff(x) == 0):
        raise _err("The grid vectors must contain unique points.", "MATLAB:griddedInterpolant:NonUniqueCompVecsPtsErrId")
    q = xi.astype(float)
    if method == "linear":
        r = np.interp(q, x, yv)
        if extrap:
            lo, hi = q < x[0], q > x[-1]
            r = np.where(lo, yv[0] + (q - x[0]) * (yv[1] - yv[0]) / (x[1] - x[0]), r)
            r = np.where(hi, yv[-1] + (q - x[-1]) * (yv[-1] - yv[-2]) / (x[-1] - x[-2]), r)
    elif method == "nearest":
        idx = np.clip(np.searchsorted(x, q), 1, x.size - 1)
        left = x[idx - 1]
        right = x[idx]
        pick = np.where(q - left < right - q, idx - 1, idx)  # ties round up (MATLAB)
        r = yv[pick]
    elif method == "previous":
        idx = np.searchsorted(x, q, side="right") - 1
        r = np.where(idx >= 0, yv[np.clip(idx, 0, None)], np.nan)
    elif method == "next":
        idx = np.searchsorted(x, q, side="left")
        r = np.where(idx < x.size, yv[np.clip(idx, None, x.size - 1)], np.nan)
    else:
        raise _err(f"interp1: method '{method}' is not supported yet", "MATLAB:interp1:unsupportedMethod")
    if not extrap or method != "linear":
        out_side = (q < x[0]) | (q > x[-1])
        if not (extrap and method in ("nearest",)):
            r = np.where(out_side, extrapval, r)
    return (_out(r),)


def _histcounts(args, *, nargout=1):
    x = _vec(args[0], "histcounts")
    x = x[np.isfinite(x)]
    if len(args) > 1 and not _is_text(args[1]):
        e = _vec(args[1], "histcounts")
        if e.size == 1:
            nb = int(e[0])
            lo, hi = (float(x.min()), float(x.max())) if x.size else (0.0, 1.0)
            if lo == hi:
                lo, hi = lo - 0.5, hi + 0.5
            e = np.linspace(lo, hi, nb + 1)
    else:
        if x.size == 0:
            e = np.array([0.0, 1.0])
        else:
            lo, hi = float(x.min()), float(x.max())
            nb = max(1, int(np.ceil(np.sqrt(x.size)))) if lo != hi else 1
            e = np.histogram_bin_edges(x, bins=nb, range=(lo, hi) if lo != hi else (lo - 0.5, hi + 0.5))
    n, _ = np.histogram(x, bins=e)  # last bin closed on both sides, as MATLAB
    return (_out(n.astype(float).reshape(1, -1)), _out(e.reshape(1, -1)))


def _accumarray(args, *, nargout=1):
    subs = _arr(args[0], "accumarray").astype(float)
    vals = _f(args[1], "accumarray").reshape(-1, order="F")
    if np.any(subs < 1) or np.any(subs != np.floor(subs)):
        raise _err("First input SUBS must contain positive integer subscripts.", "MATLAB:accumarray:nonPosIntSubs")
    if subs.shape[0] == 1 and subs.shape[1] != 1 and subs.ndim == 2 and vals.size == subs.shape[1]:
        subs = subs.reshape(-1, 1)
    idx = subs.astype(int) - 1
    if idx.ndim == 1:
        idx = idx.reshape(-1, 1)
    if vals.size == 1:
        vals = np.full(idx.shape[0], vals[0])
    if len(args) > 2 and _arr(args[2], "accumarray").size:
        shp = tuple(int(v) for v in _arr(args[2], "accumarray").reshape(-1))
    else:
        shp = tuple(int(m) + 1 for m in idx.max(axis=0)) if idx.size else (0, 1)
        if len(shp) == 1:
            shp = (shp[0], 1)
    fh = args[3] if len(args) > 3 and hasattr(args[3], "call") else None
    out = np.zeros(shp, dtype=vals.dtype)
    if fh is None:
        np.add.at(out, tuple(idx[:, k] for k in range(idx.shape[1])) if idx.shape[1] > 1 else (idx[:, 0], np.zeros(idx.shape[0], int)), vals)
        return (_out(out),)
    groups: Dict[tuple, list] = {}
    for row, v in zip(idx, vals):
        key = tuple(row) if idx.shape[1] > 1 else (row[0], 0)
        groups.setdefault(key, []).append(v)
    for key, vs in groups.items():
        out[key] = float(_call(fh, np.array(vs).reshape(-1, 1)).reshape(-1)[0])
    return (_out(out),)


# ----------------------------------------------------------------- function functions
def _fzero(args, *, nargout=1):
    fh = args[0]
    if not hasattr(fh, "call"):
        raise _err("FZERO only accepts inputs of data type function_handle.", "MATLAB:fzero:InvalidFUN")
    x0 = _vec(args[1], "fzero")
    f = lambda t: float(_call(fh, t).reshape(-1)[0])  # noqa: E731
    if x0.size == 2:
        a, b = float(x0[0]), float(x0[1])
        fa, fb = f(a), f(b)
        if np.sign(fa) == np.sign(fb) and fa != 0 and fb != 0:
            raise _err("The function values at the interval endpoints must differ in sign.", "MATLAB:fzero:ValuesAtEndPtsSameSign")
    else:
        a = float(x0[0])
        fa = f(a)
        if fa == 0:
            return (_out(a), _out(0.0), _out(1.0))
        dx = abs(a) / 50 if a != 0 else 1 / 50
        b, fb = a, fa
        for _ in range(200):  # expand a bracket around x0 (MATLAB's search)
            lo, hi = a - dx, a + dx
            flo, fhi = f(lo), f(hi)
            if np.sign(flo) != np.sign(fa):
                b, fb = lo, flo
                break
            if np.sign(fhi) != np.sign(fa):
                b, fb = hi, fhi
                break
            dx *= np.sqrt(2)
        else:
            return (_out(np.nan), _out(np.nan), _out(-6.0))
    # Brent's method
    if abs(fa) < abs(fb):
        a, b, fa, fb = b, a, fb, fa
    c, fc, mflag, d = a, fa, True, 0.0
    for _ in range(500):
        if fb == 0 or abs(b - a) < 2 * np.finfo(float).eps * max(abs(b), 1.0):
            break
        if fa != fc and fb != fc:
            s = a * fb * fc / ((fa - fb) * (fa - fc)) + b * fa * fc / ((fb - fa) * (fb - fc)) + c * fa * fb / ((fc - fa) * (fc - fb))
        else:
            s = b - fb * (b - a) / (fb - fa)
        cond = (not ((3 * a + b) / 4 < s < b or b < s < (3 * a + b) / 4)) or \
            (mflag and abs(s - b) >= abs(b - c) / 2) or (not mflag and abs(s - b) >= abs(c - d) / 2)
        if cond:
            s = (a + b) / 2
            mflag = True
        else:
            mflag = False
        fs = f(s)
        d, c, fc = c, b, fb
        if np.sign(fa) * np.sign(fs) < 0:
            b, fb = s, fs
        else:
            a, fa = s, fs
        if abs(fa) < abs(fb):
            a, b, fa, fb = b, a, fb, fa
    return (_out(b), _out(fb), _out(1.0))


def _fminsearch(args, *, nargout=1):
    fh = args[0]
    x0 = _f(args[1], "fminsearch")
    shape = x0.shape
    f = lambda v: float(_call(fh, v.reshape(shape)).reshape(-1)[0])  # noqa: E731
    n = x0.size
    x = x0.reshape(-1).astype(float)
    simplex = [x.copy()]
    for k in range(n):  # MATLAB's initial simplex: 5% (or 0.00025 for zeros)
        y = x.copy()
        y[k] = y[k] * 1.05 if y[k] != 0 else 0.00025
        simplex.append(y)
    simplex = np.array(simplex)
    fv = np.array([f(s) for s in simplex])
    tolx = tolf = 1e-4
    maxit = 200 * n
    if len(args) > 2 and getattr(args[2], "is_struct", False):  # optimset options (M3-E3 #627)
        from openmatlab.libs.odeopt import _opt

        tolx = float(_opt(args[2], "TolX", tolx))
        tolf = float(_opt(args[2], "TolFun", tolf))
        maxit = int(_opt(args[2], "MaxIter", maxit))
    for it in range(maxit):
        order = np.argsort(fv, kind="stable")
        simplex, fv = simplex[order], fv[order]
        if np.max(np.abs(fv[1:] - fv[0])) <= tolf and np.max(np.abs(simplex[1:] - simplex[0])) <= tolx:
            break
        xbar = simplex[:-1].mean(axis=0)
        xr = 2 * xbar - simplex[-1]
        fr = f(xr)
        if fr < fv[0]:
            xe = 3 * xbar - 2 * simplex[-1]
            fe = f(xe)
            simplex[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < fv[-2]:
            simplex[-1], fv[-1] = xr, fr
        else:
            if fr < fv[-1]:
                xc = 1.5 * xbar - 0.5 * simplex[-1]
                fc = f(xc)
                ok = fc <= fr
            else:
                xc = 0.5 * xbar + 0.5 * simplex[-1]
                fc = f(xc)
                ok = fc < fv[-1]
            if ok:
                simplex[-1], fv[-1] = xc, fc
            else:
                for k in range(1, n + 1):
                    simplex[k] = simplex[0] + 0.5 * (simplex[k] - simplex[0])
                    fv[k] = f(simplex[k])
    k = int(np.argmin(fv))
    return (_out(simplex[k].reshape(shape)), _out(fv[k]))


def _integral(args, *, nargout=1):
    fh = args[0]
    a, b = _s(args[1], "integral"), _s(args[2], "integral")
    opts = {}
    i = 3
    while i + 1 < len(args):
        opts[_txt(args[i]).lower()] = _s(args[i + 1], "integral")
        i += 2
    abstol, reltol = opts.get("abstol", 1e-10), opts.get("reltol", 1e-6)
    sign = 1.0
    if a > b:
        a, b, sign = b, a, -1.0
    if a == b:
        return (_out(0.0),)
    # map infinite ranges with x = t / (1 - t^2)
    if np.isinf(a) or np.isinf(b):
        def g(t):
            x = t / (1 - t ** 2)
            return _call(fh, x).reshape(-1) * (1 + t ** 2) / (1 - t ** 2) ** 2
        lo = -1.0 if np.isinf(a) else a / (0.5 + np.sqrt(0.25 + a * a)) if a != 0 else 0.0
        hi = 1.0 if np.isinf(b) else b / (0.5 + np.sqrt(0.25 + b * b)) if b != 0 else 0.0
        lo, hi = lo + (1e-12 if np.isinf(a) else 0), hi - (1e-12 if np.isinf(b) else 0)
        func, A, B = g, lo, hi
    else:
        func, A, B = (lambda x: _call(fh, x).reshape(-1)), a, b
    # 15-point Gauss-Kronrod, adaptive bisection
    xgk = np.array([0.991455371120813, 0.949107912342759, 0.864864423359769, 0.741531185599394,
                    0.586087235467691, 0.405845151377397, 0.207784955007898, 0.0])
    wgk = np.array([0.022935322010529, 0.063092092629979, 0.104790010322250, 0.140653259715525,
                    0.169004726639267, 0.190350578064785, 0.204432940075298, 0.209482141084728])
    wg = np.array([0.129484966168870, 0.279705391489277, 0.381830050505119, 0.417959183673469])
    nodes = np.concatenate([-xgk[:-1], xgk[::-1]])
    wk = np.concatenate([wgk[:-1], wgk[::-1]])
    gi = [1, 3, 5, 7, 9, 11, 13]  # Gauss nodes inside the Kronrod set
    wgf = np.array([wg[0], wg[1], wg[2], wg[3], wg[2], wg[1], wg[0]])

    def seg(lo, hi):
        c, h = (lo + hi) / 2, (hi - lo) / 2
        fx = np.asarray(func(c + h * nodes), dtype=float).reshape(-1)
        if fx.size != nodes.size:
            raise _err("integral: the integrand must accept and return arrays (use .* ./ .^).", "MATLAB:integral:FxNotSameSizeAsX")
        k = h * np.dot(wk, fx)
        g = h * np.dot(wgf, fx[gi])
        return k, abs(k - g)

    stack = [(A, B)]
    total, err_total, evals = 0.0, 0.0, 0
    pending = [(A, B) + seg(A, B)]
    while pending and evals < 10000:
        lo, hi, val, err = pending.pop()
        evals += 1
        if err <= max(abstol, reltol * abs(val)) * (hi - lo) / (B - A) or (hi - lo) < 1e-12 * (B - A):
            total += val
            err_total += err
            continue
        mid = (lo + hi) / 2
        pending.append((lo, mid) + seg(lo, mid))
        pending.append((mid, hi) + seg(mid, hi))
    for lo, hi, val, err in pending:
        total += val
    return (_out(sign * total),)


def register(builtins: Dict[str, Callable]) -> None:
    table = {
        "fix": _unary("fix", _fix), "sign": _unary("sign", _sign), "isnan": _unary("isnan", _isnan),
        "isinf": _unary("isinf", _isinf), "isfinite": _unary("isfinite", _isfinite),
        "log1p": _unary("log1p", np.log1p), "expm1": _unary("expm1", np.expm1),
        "deg2rad": _unary("deg2rad", lambda b: b.astype(float) * (np.pi / 180)),
        "rad2deg": _unary("rad2deg", lambda b: b.astype(float) * (180 / np.pi)),
        "sind": _unary("sind", _sind), "cosd": _unary("cosd", _cosd), "tand": _unary("tand", _tand),
        "asind": _unary("asind", lambda b: np.rad2deg(np.arcsin(b.astype(float)))),
        "acosd": _unary("acosd", lambda b: np.rad2deg(np.arccos(b.astype(float)))),
        "atand": _unary("atand", lambda b: np.rad2deg(np.arctan(b.astype(float)))),
        "sec": _unary("sec", lambda b: 1 / np.cos(b.astype(float) if not np.iscomplexobj(b) else b)),
        "csc": _unary("csc", lambda b: 1 / np.sin(b.astype(float) if not np.iscomplexobj(b) else b)),
        "cot": _unary("cot", lambda b: 1 / np.tan(b.astype(float) if not np.iscomplexobj(b) else b)),
        "asec": _unary("asec", lambda b: np.arccos(1 / b.astype(float))),
        "acsc": _unary("acsc", lambda b: np.arcsin(1 / b.astype(float))),
        "acot": _unary("acot", lambda b: np.arctan(1 / b.astype(float))),
        "rem": _binary("rem", _rem), "hypot": _binary("hypot", lambda a, b: np.hypot(np.abs(a), np.abs(b))),
        "atan2": _binary("atan2", lambda a, b: np.arctan2(a.astype(float), b.astype(float))),
        "gcd": _binary("gcd", _gcd_arr), "lcm": _binary("lcm", _lcm_arr),
        "log2": _log2, "nthroot": _nthroot, "diff": _diff,
        "cumprod": _cum("cumprod", np.cumprod), "cummax": _cum("cummax", np.maximum.accumulate),
        "cummin": _cum("cummin", np.minimum.accumulate),
        "primes": _primes, "isprime": _isprime, "factor": _factor, "nchoosek": _nchoosek, "factorial": _factorial,
        "median": _median, "mode": _mode, "var": _varstd("var", False), "std": _varstd("std", True),
        "cov": _cov, "corrcoef": _corrcoef, "range": _range, "bounds": _bounds,
        "rng": _rng, "rand": _rand, "randn": _randn, "randi": _randi, "randperm": _randperm,
        "tic": _tic, "toc": _toc, "pause": _pause,
        "flintmax": lambda args, nargout=1: (_out(2.0 ** 53 if not args or _txt(args[0]) != "single" else 2.0 ** 24),),
        "cross": _cross, "dot": _dot, "kron": _kron, "trapz": _trapz, "cumtrapz": _cumtrapz,
        "polyval": _polyval, "polyfit": _polyfit, "roots": _roots, "conv": _conv, "deconv": _deconv,
        "filter": _filter, "interp1": _interp1, "histcounts": _histcounts, "accumarray": _accumarray,
        "fzero": _fzero, "fminsearch": _fminsearch, "integral": _integral,
    }
    for k, v in table.items():
        builtins.setdefault(k, v)
    if "round" in builtins:
        builtins["round"] = _round_n(builtins["round"])


# statement forms that print / return nothing (MATLAB): handled by the evaluator
STATEMENT_ZERO = {"tic", "toc", "rng", "enumeration", "methods", "properties", "dbstack"}  # last three: M8 O-E5 listings
