"""mldivide / mrdivide and helpers (Epic #496), following the MATLAB docs:
square -> LU with partial pivoting (+ singular / RCOND warnings), otherwise
least squares with column-pivoted QR giving the *basic* solution (+ rank
deficient warning). NumPy only."""

from __future__ import annotations

import numpy as np

from openmatlab.runtime import warnings as mw

EPS = np.finfo(np.float64).eps


class LinalgError(ValueError):
    pass


def _f(a):
    a = np.asarray(a)
    if a.dtype == np.bool_ or np.issubdtype(a.dtype, np.integer):
        a = a.astype(np.float64)
    return a.astype(np.complex128) if np.iscomplexobj(a) else a.astype(np.float64)


def _lu_solve(a, b):
    """Gaussian elimination with partial pivoting; zero pivots give Inf/NaN (as LAPACK)."""
    n = a.shape[0]
    a, b = a.copy(), b.copy()
    singular = False
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in range(n):
            p = k + int(np.argmax(np.abs(a[k:, k])))
            if p != k:
                a[[k, p]], b[[k, p]] = a[[p, k]], b[[p, k]]
            if a[k, k] == 0:
                singular = True
                continue
            f = a[k + 1:, k] / a[k, k]
            a[k + 1:, k:] -= np.outer(f, a[k, k:])
            b[k + 1:] -= np.outer(f, b[k])
        x = np.zeros_like(b)
        for k in range(n - 1, -1, -1):
            x[k] = (b[k] - a[k, k + 1:] @ x[k + 1:]) / a[k, k]
    return x, singular


def rcond(a) -> float:
    try:
        inv = np.linalg.inv(a)
    except np.linalg.LinAlgError:
        return 0.0
    na, ni = np.linalg.norm(a, 1), np.linalg.norm(inv, 1)
    if not np.isfinite(ni) or na == 0:
        return 0.0
    return float(1.0 / (na * ni))


def _pivoted_qr_basic(a, b):
    """Basic least-squares solution via Householder QR with column pivoting."""
    m, n = a.shape
    r = a.copy()
    qtb = b.copy()
    perm = np.arange(n)
    norms = np.linalg.norm(r, axis=0)
    k_max = min(m, n)
    for k in range(k_max):
        j = k + int(np.argmax(np.linalg.norm(r[k:, k:], axis=0)))
        if j != k:
            r[:, [k, j]] = r[:, [j, k]]
            perm[[k, j]] = perm[[j, k]]
        x = r[k:, k]
        nx = np.linalg.norm(x)
        if nx == 0:
            continue
        alpha = -np.exp(1j * np.angle(x[0])) * nx if np.iscomplexobj(r) else (-np.sign(x[0]) or -1.0) * nx
        v = x.copy()
        v[0] -= alpha
        vn = np.linalg.norm(v)
        if vn == 0:
            continue
        v = v / vn
        r[k:, k:] -= 2.0 * np.outer(v, v.conj() @ r[k:, k:])
        qtb[k:] -= 2.0 * np.outer(v, v.conj() @ qtb[k:])
    del norms
    diag = np.abs(np.diag(r[:k_max, :k_max])) if k_max else np.zeros(0)
    tol = max(m, n) * EPS * (diag[0] if diag.size else 0.0)
    rank = int(np.sum(diag > tol))
    x = np.zeros((n, b.shape[1]), dtype=np.result_type(r, qtb))
    if rank:
        rr = r[:rank, :rank]
        y = np.linalg.solve(np.triu(rr), qtb[:rank]) if rank else None
        x[perm[:rank]] = y
    return x, rank, tol


def mldivide(a, b):
    a, b = _f(a), _f(b)
    if a.ndim > 2 or b.ndim > 2:
        raise LinalgError("Arguments must be 2-D, or at least one argument must be scalar. Use LDIVIDE (.\\) for elementwise left division.")
    if a.size == 1:
        with np.errstate(divide="ignore", invalid="ignore"):
            return b / a.reshape(())
    if a.shape[0] != b.shape[0]:
        raise LinalgError("Matrix dimensions must agree.")
    m, n = a.shape
    if b.shape[1] == 0 or m == 0 or n == 0:
        return np.zeros((n, b.shape[1]), dtype=np.result_type(a, b))
    if m == n:
        x, singular = _lu_solve(a, b.astype(np.result_type(a, b)))
        if singular:
            mw.emit("Matrix is singular to working precision.")
        else:
            rc = rcond(a)
            if rc < EPS:
                mw.emit(f"Matrix is close to singular or badly scaled. Results may be inaccurate. RCOND = {rc:e}.")
        return x
    x, rank, tol = _pivoted_qr_basic(a, b.astype(np.result_type(a, b)))
    if rank < min(m, n):
        mw.emit(f"Rank deficient, rank = {rank}, tol = {tol:e}.")
    return x


def mrdivide(b, a):
    """B/A = (A.'\\B.').'"""
    b, a = _f(b), _f(a)
    if a.size == 1:
        with np.errstate(divide="ignore", invalid="ignore"):
            return b / a.reshape(())
    if b.ndim > 2 or a.ndim > 2:
        raise LinalgError("Arguments must be 2-D, or at least one argument must be scalar. Use RDIVIDE (./) for elementwise right division.")
    if b.shape[1] != a.shape[1]:
        raise LinalgError("Matrix dimensions must agree.")
    return mldivide(a.T, b.T).T
