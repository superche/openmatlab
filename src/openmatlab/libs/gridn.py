"""interpn and interp3: gridded interpolation in N dimensions (C-E5 #765 T2 burn-down).

Clean-room, NumPy only, against the documented syntaxes.  'linear' and 'nearest' are evaluated in closed
form over the 2^n cell corners; 'pchip', 'spline' and 'makima' reduce one dimension at a time with the
one-dimensional rules of interp1, and 'cubic' with cubic convolution (uniform grids, as documented).  Query vectors of
different sizes or orientations are grid vectors (ndgrid for interpn, meshgrid for interp3); otherwise the
query arrays are points and the result has their size.  Out-of-range points get extrapval; without it,
'spline' and 'makima' extrapolate and the other methods give NaN (documented).
"""

from __future__ import annotations

from typing import Callable, Dict, List

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

from .interp import _interp_col

_METHODS = ("linear", "nearest", "pchip", "cubic", "spline", "makima")


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _a(v) -> np.ndarray:
    a = np.asarray(v.backend_buffer())
    a = a.astype(float) if a.dtype.kind in "biu" else a
    return a.reshape(1, 1) if a.ndim == 0 else a


def _text(v):
    return getattr(v, "text", None)


def _grid_vector(X: np.ndarray, k: int, nd: int) -> np.ndarray:
    if X.ndim >= 2 and sum(s > 1 for s in X.shape) > 1:  # a full ndgrid array: read it along dimension k
        idx = [0] * X.ndim
        idx[k] = slice(None)
        return np.asarray(X[tuple(idx)], dtype=float).reshape(-1)
    return np.asarray(X, dtype=float).reshape(-1)


def _is_vec(a: np.ndarray) -> bool:
    return sum(s > 1 for s in a.shape) <= 1


def _shape(V: np.ndarray, nd: int) -> tuple:
    return tuple(V.shape) + (1,) * (nd - V.ndim)


def keys_cubic(g: np.ndarray, y: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Cubic convolution (Keys 1981, a = -1/2) on a uniform grid, with Keys' end conditions."""
    n = g.size
    if n < 3:
        raise _err("The 'cubic' method requires at least three points in each dimension.", "MATLAB:interp:cubicNeedsThree")
    h = (g[-1] - g[0]) / (n - 1)
    if not np.allclose(np.diff(g), h, rtol=1e-9, atol=0):
        raise _err("The 'cubic' method requires uniformly spaced grid points; use 'spline'.", "MATLAB:interp:cubicNonuniform")
    ext = np.concatenate([[3 * y[0] - 3 * y[1] + y[2]], y, [3 * y[-1] - 3 * y[-2] + y[-3]]])
    s = (q - g[0]) / h
    k = np.clip(np.floor(s).astype(int), 0, n - 2)
    t = s - k
    p0, p1, p2, p3 = ext[k], ext[k + 1], ext[k + 2], ext[k + 3]
    return p1 + 0.5 * t * (p2 - p0 + t * (2 * p0 - 5 * p1 + 4 * p2 - p3 + t * (3 * (p1 - p2) + p3 - p0)))


def _col(method, g, row, q):
    return keys_cubic(g, row, q) if method == "cubic" else _interp_col(method, g, row, q, True)


def interp_points(grids: List[np.ndarray], V: np.ndarray, pts: List[np.ndarray], method: str, extrap: float):
    """Interpolate V (sorted ascending grids) at points pts[k] (flat arrays of equal length)."""
    nd = len(grids)
    V = V.reshape(tuple(g.size for g in grids))
    q = len(pts[0])
    out = np.zeros(q, dtype=V.dtype if np.iscomplexobj(V) else float)
    bad = np.zeros(q, dtype=bool)
    outside = extrap is not None or method not in ("spline", "makima")  # documented: these extrapolate by default
    for g, p in zip(grids, pts):
        bad |= np.isnan(p) | (outside & ((p < g[0]) | (p > g[-1])))
    if method in ("linear", "nearest"):
        idx, wts = [], []
        for g, p in zip(grids, pts):
            p = np.nan_to_num(np.clip(p, g[0], g[-1]))
            if g.size == 1:
                idx.append((np.zeros(q, int), np.zeros(q, int)))
                wts.append(np.zeros(q))
                continue
            i = np.clip(np.searchsorted(g, p, side="right") - 1, 0, g.size - 2)
            t = (p - g[i]) / (g[i + 1] - g[i])
            if method == "nearest":  # ties round up (MATLAB)
                t = (t >= 0.5).astype(float)
            idx.append((i, i + 1))
            wts.append(t)
        for corner in range(2 ** nd):
            w = np.ones(q)
            sub = []
            for k in range(nd):
                bit = (corner >> k) & 1
                sub.append(idx[k][bit])
                w = w * (wts[k] if bit else 1 - wts[k])
            if np.any(w):
                out = out + w * V[tuple(sub)]
    else:
        for j in range(q):
            if bad[j]:
                continue
            A = V
            for k in range(nd - 1, -1, -1):
                g = grids[k]
                flat = A.reshape(-1, g.size)
                A = np.array([_col(method, g, row, np.array([pts[k][j]]))[0] for row in flat])
                if k:
                    A = A.reshape(tuple(s.size for s in grids[:k]))
            out[j] = np.asarray(A).reshape(-1)[0]
    out[bad] = np.nan if extrap is None else extrap
    return out


def _parse_tail(args):
    method, extrap = "linear", None  # None: extrapval omitted
    nums = list(args)
    if len(nums) >= 2 and _text(nums[-2]) is not None and _text(nums[-1]) is None:
        extrap = float(_a(nums[-1]).reshape(-1)[0])
        nums.pop()
    if nums and _text(nums[-1]) is not None:
        method = _text(nums.pop()).lower()
        if method == "v5cubic":
            method = "cubic"
        if method not in _METHODS:
            raise _err(f"Invalid interpolation method '{method}'.", "MATLAB:interpn:InvalidMethod")
    return nums, method, extrap


def _evaluate(fn, grids, V, queries, method, extrap, grid_form):
    order = [np.argsort(g, kind="stable") for g in grids]
    grids = [g[o] for g, o in zip(grids, order)]
    V = V[np.ix_(*order)] if V.ndim == len(order) else V.reshape(tuple(g.size for g in grids))[np.ix_(*order)]
    for g in grids:
        if g.size > 1 and np.any(np.diff(g) == 0):
            raise _err("The grid vectors must contain unique points.", f"MATLAB:{fn}:NonUniqueGrid")
    if grid_form:
        mesh = np.meshgrid(*[q.reshape(-1) for q in queries], indexing="ij")
        shape = mesh[0].shape
        pts = [m.reshape(-1) for m in mesh]
    else:
        shape = queries[0].shape
        pts = [q.reshape(-1).astype(float) for q in queries]
    return interp_points(grids, V, pts, method, extrap).reshape(shape)


def _interpn_core(fn, args, nd_hint=None):
    nums, method, extrap = _parse_tail(args)
    if not nums:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    arrs = [_a(v) for v in nums]
    N = len(arrs)
    refine = None
    if N <= 2 and (N == 1 or arrs[1].size == 1):  # interpn(V) / interpn(V, k)
        V = arrs[0]
        nd = nd_hint or max(V.ndim, 2)
        refine = 1 if N == 1 else int(arrs[1].reshape(-1)[0])
        grids = [np.arange(1, s + 1, dtype=float) for s in _shape(V, nd)]
        queries = [np.linspace(1, s, (s - 1) * 2 ** refine + 1) if s > 1 else np.ones(1) for s in _shape(V, nd)]
        return grids, V, queries, method, extrap, True
    nd = nd_hint
    if nd is None and N >= 3 and max(arrs[0].ndim, 2) == N - 1 and arrs[1].size == arrs[-1].size:
        nd = N - 1  # interpn(V, Xq1, ..., Xqn)
    if nd is None:
        for cand in range(1, N):
            if N == 2 * cand + 1 and max(arrs[cand].ndim, 2) in (cand, max(cand, 2)):
                nd = cand
                break
        if nd is None:
            nd = N - 1
    if N == 2 * nd + 1:
        V = arrs[nd]
        grids = [_grid_vector(arrs[k], k, nd) for k in range(nd)]
        queries = arrs[nd + 1:]
    elif N == nd + 1:
        V = arrs[0]
        grids = [np.arange(1, s + 1, dtype=float) for s in _shape(V, nd)]
        queries = arrs[1:]
    else:
        raise _err("Wrong number of input arguments.", f"MATLAB:{fn}:nargin")
    if tuple(g.size for g in grids) != _shape(V, nd)[:nd]:
        raise _err("The lengths of the grid vectors must match the size of V.", f"MATLAB:{fn}:gridSizeMismatch")
    same = all(q.shape == queries[0].shape for q in queries)
    grid_form = all(_is_vec(q) for q in queries) and not same
    if not same and not grid_form:
        raise _err("The query arrays must have the same size, or be grid vectors.", f"MATLAB:{fn}:querySizeMismatch")
    return grids, V, queries, method, extrap, grid_form


def _interpn(args, *, nargout=1):
    grids, V, queries, method, extrap, grid_form = _interpn_core("interpn", args)
    return (NDArrayValue(np.ascontiguousarray(_evaluate("interpn", grids, V, queries, method, extrap, grid_form))),)


def _interp3(args, *, nargout=1):
    """interp3 uses meshgrid order: V is ny-by-nx-by-nz; X, Y are meshgrid arrays or vectors."""
    nums, method, extrap = _parse_tail(args)
    arrs = [_a(v) for v in nums]
    if len(arrs) in (1, 2) and (len(arrs) == 1 or arrs[1].size == 1):
        V = arrs[0]
        grids, Vp, queries, method, extrap, _ = _interpn_core("interp3", [NDArrayValue(np.transpose(V, (1, 0, 2)) if V.ndim == 3 else V.T)] + list(args[1:]), 3)
        r = _evaluate("interp3", grids, Vp, queries, method, extrap, True)
        return (NDArrayValue(np.ascontiguousarray(np.transpose(r, (1, 0, 2)))),)
    if len(arrs) == 7:
        X, Y, Z, V = arrs[:4]
        q = arrs[4:]
        gx = X[0, :, 0].reshape(-1) if X.ndim == 3 else X.reshape(-1)
        gy = Y[:, 0, 0].reshape(-1) if Y.ndim == 3 else Y.reshape(-1)
        gz = Z[0, 0, :].reshape(-1) if Z.ndim == 3 else Z.reshape(-1)
    elif len(arrs) == 4:
        V = arrs[0]
        q = arrs[1:]
        s = _shape(V, 3)
        gx, gy, gz = (np.arange(1, n + 1, dtype=float) for n in (s[1], s[0], s[2]))
    else:
        raise _err("Wrong number of input arguments.", "MATLAB:interp3:nargin")
    V3 = V.reshape(_shape(V, 3))
    Vp = np.transpose(V3, (1, 0, 2))
    same = all(a.shape == q[0].shape for a in q)
    if all(_is_vec(a) for a in q) and not same:
        r = _evaluate("interp3", [gx, gy, gz], Vp, q, method, extrap, True)
        return (NDArrayValue(np.ascontiguousarray(np.transpose(r, (1, 0, 2)))),)
    if not same:
        raise _err("Xq, Yq and Zq must be the same size, or grid vectors.", "MATLAB:interp3:querySizeMismatch")
    return (NDArrayValue(np.ascontiguousarray(_evaluate("interp3", [gx, gy, gz], Vp, q, method, extrap, False))),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins["interpn"] = _interpn
    builtins["interp3"] = _interp3
