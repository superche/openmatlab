"""normest1, condest, normest (C-E5 #765 T2 burn-down).

Clean-room, NumPy only.  normest1 is the block 1-norm power method of Higham and Tisseur (SIAM J. Matrix
Anal. Appl. 21(4), 2000, Algorithm 2.4), which the MATLAB documentation cites; condest applies it to the
inverse through an LU solve; normest is the documented power iteration for the 2-norm.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics import linalg as la
from openmatlab.numerics.ndarray_value import NDArrayValue

from .burndown_builtins import _err, _is_text, _need


def _arr(v) -> np.ndarray:
    buf = getattr(v, "backend_buffer", None)
    if buf is None:
        raise _err(f"Expected a numeric array, not '{v.matlab_class()}'.", "MATLAB:invalidType")
    a = np.asarray(buf())
    a = a.astype(float) if a.dtype.kind in "biu" else a
    return a.reshape(1, 1) if a.ndim == 0 else a


def _val(a) -> NDArrayValue:
    a = np.asarray(a)
    return NDArrayValue(a.reshape(1, 1) if a.ndim == 0 else a)


def _empty(v) -> bool:
    return getattr(v, "backend_buffer", None) is not None and not _is_text(v) and _arr(v).size == 0


class _Op:
    """A matrix, or MATLAB's afun(flag, x, p1, ...) with flags 'dim', 'real', 'notransp', 'transp'."""

    def __init__(self, a, extra=()):
        from openmatlab.runtime.char_value import CharValue

        self._char = CharValue
        if hasattr(a, "call"):
            self.fh, self.extra = a, list(extra)
            self.n = int(self._f("dim", np.zeros((0, 0))).reshape(-1)[0])
            self.real = bool(np.all(self._f("real", np.zeros((0, 0)))))
        else:
            self.fh, self.A = None, _arr(a)
            if self.A.ndim != 2 or self.A.shape[0] != self.A.shape[1]:
                raise _err("The matrix must be square.", "MATLAB:square")
            self.n, self.real = self.A.shape[0], not np.iscomplexobj(self.A)

    def _f(self, flag, x):
        out = self.fh.call([self._char(flag), _val(x)] + self.extra, nargout=1)
        return _arr(out[0])

    def mul(self, x):
        return self.A @ x if self.fh is None else self._f("notransp", x)

    def tmul(self, x):
        return self.A.conj().T @ x if self.fh is None else self._f("transp", x)


def _sign(y):
    if np.iscomplexobj(y):
        a = np.abs(y)
        return np.where(a == 0, 1, y / np.where(a == 0, 1, a))
    return np.where(y >= 0, 1.0, -1.0)


def normest1_core(op: _Op, t: int = 2, X0=None, itmax: int = 5, rng=None):
    """(est, v, w, iterations) with w = A v and norm(w, 1) = est * norm(v, 1)."""
    n = op.n
    rng = rng or np.random.default_rng(0)
    if n == 0:
        return 0.0, np.zeros((0, 1)), np.zeros((0, 1)), 0
    if t >= n:  # exact: apply A to the identity
        Y = op.mul(np.eye(n))
        norms = np.abs(Y).sum(axis=0)
        j = int(np.argmax(norms))
        v = np.zeros((n, 1))
        v[j] = 1
        return float(norms[j]), v, Y[:, [j]], 1
    if X0 is not None:
        X = np.array(X0, dtype=float if op.real else complex)
    else:
        X = np.ones((n, t))
        if t > 1:
            X[:, 1:] = rng.choice([-1.0, 1.0], size=(n, t - 1))
        X /= n
    X = X / np.abs(X).sum(axis=0)
    est_old, best = 0.0, None
    S_old = None
    hist = set()
    it = 0
    for it in range(1, itmax + 1):
        Y = op.mul(X)
        norms = np.abs(Y).sum(axis=0)
        j = int(np.argmax(norms))
        est = float(norms[j])
        if best is None or est > est_old:
            best = (est, X[:, [j]].copy(), Y[:, [j]].copy())
        if it >= 2 and est <= est_old:
            break
        est_old = est
        S = _sign(Y)
        if op.real and S_old is not None and np.all(np.abs(S.T @ S_old).max(axis=1) == n):
            break
        S_old = S
        Z = op.tmul(S)
        h = np.abs(Z).max(axis=1)
        if it >= 2 and h.max() == h[int(np.argmax(np.abs(best[1]).reshape(-1)))]:
            break
        order = [int(i) for i in np.argsort(-h, kind="stable")]
        if t > 1 and all(i in hist for i in order[:t]):
            break
        fresh = [i for i in order if i not in hist][:t] or order[:t]
        X = np.zeros((n, len(fresh)))
        for c, i in enumerate(fresh):
            X[i, c] = 1
        hist.update(fresh)
    est, v, w = best
    return float(np.abs(w).sum() / np.abs(v).sum()), v, w, it


def _normest1(args, *, nargout=1):
    _need(args, 1, "normest1")
    t = 2
    if len(args) > 1 and not _empty(args[1]):
        t = int(_arr(args[1]).reshape(-1)[0])
    X0 = _arr(args[2]) if len(args) > 2 and not _empty(args[2]) else None
    op = _Op(args[0], args[3:])
    est, v, w, it = normest1_core(op, t, X0)
    return (_val(est), _val(v), _val(w), _val(float(it)))[:max(1, nargout)]


def _condest(args, *, nargout=1):
    _need(args, 1, "condest")
    A = _arr(args[0])
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise _err("condest: A must be a square matrix.", "MATLAB:square")
    t = int(_arr(args[1]).reshape(-1)[0]) if len(args) > 1 and not _empty(args[1]) else 2
    n = A.shape[0]
    if n == 0:
        return (_val(0.0), _val(np.zeros((0, 1))))[:max(1, nargout)]
    anorm = float(np.abs(A).sum(axis=0).max())
    lu, singular = la._lu_solve(A, np.eye(n, dtype=A.dtype))  # the same factorisation inv uses
    if singular or not np.all(np.isfinite(lu)):
        return (_val(np.inf), _val(np.zeros((0, 0))))[:max(1, nargout)]

    class _Inv(_Op):
        def __init__(self):
            self.fh, self.n, self.real = None, n, not np.iscomplexobj(A)
            self.A = lu

    est, vv, ww, _ = normest1_core(_Inv(), t)
    v = ww / np.abs(ww).sum()
    return (_val(anorm * est), _val(v))[:max(1, nargout)]


def _normest(args, *, nargout=1):
    _need(args, 1, "normest")
    S = _arr(args[0])
    tol = float(_arr(args[1]).reshape(-1)[0]) if len(args) > 1 else 1e-6
    x = np.abs(S).sum(axis=0).reshape(-1, 1).astype(S.dtype if np.iscomplexobj(S) else float)
    cnt = 0
    e = float(np.linalg.norm(x))
    if e == 0:
        return (_val(0.0), _val(0.0))[:max(1, nargout)]
    x = x / e
    e0 = 0.0
    while abs(e - e0) > tol * e:
        e0 = e
        Sx = S @ x
        if not np.any(Sx):
            Sx = np.random.default_rng(cnt).random(Sx.shape)
        e = float(np.linalg.norm(S.conj().T @ Sx)) / float(np.linalg.norm(Sx))
        x = (S.conj().T @ Sx)
        x = x / np.linalg.norm(x)
        cnt += 1
        if cnt > 100:
            break
    return (_val(e), _val(float(cnt)))[:max(1, nargout)]


def register(builtins: Dict[str, Callable]) -> None:
    builtins["normest1"] = _normest1
    builtins["condest"] = _condest
    builtins["normest"] = _normest
