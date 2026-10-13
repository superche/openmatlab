"""Native sparse direct solve for S\\b (#522), NumPy only.

Strategy, cheapest first, all on the compressed ``Store`` (never m*n):
1. diagonal: x = b ./ d
2. triangular (lower or upper): column-oriented substitution
3. banded: Gaussian elimination with partial pivoting in a sliding
   (kl+1) x (2kl+ku+1) window; work O(n * kl * (kl+ku)).
4. general: reverse Cuthill-McKee reordering, then (3) when the permuted
   bandwidth fits the work budget.

Any case that would need MATLAB's singular / RCOND warnings (zero pivot, or
pivot ratio below eps) returns ``None`` so the dense solver reproduces the
exact diagnostics. Non-square systems, non-finite data and over-budget
fill also return ``None``.
"""

from __future__ import annotations

from collections import deque

import numpy as np

EPS = np.finfo(float).eps
WORK_BUDGET = 4e8


def solve(st, b):
    """x = S \\ b for a Store ``st`` and a dense 2-D ``b``; None -> dense path."""
    m, n = st.shape
    if m != n or n == 0 or b.ndim != 2 or b.shape[0] != n or st.nnz == 0:
        return None
    if st.dtype == np.bool_:
        st = st.astype(np.float64)
    if not (np.all(np.isfinite(st.data)) and np.all(np.isfinite(b))):
        return None
    dt = np.result_type(st.data, b, np.float64)
    b = b.astype(dt)
    r, c = st.rows, st.cols
    if np.all(r == c):
        if st.nnz != n:
            return None
        d = st.data.astype(dt)
        if not _well_conditioned(d):
            return None
        return b / d[:, None]
    if np.all(r >= c):
        return _triangular(st, b, dt, lower=True)
    if np.all(r <= c):
        return _triangular(st, b, dt, lower=False)
    kl, ku = int(np.max(r - c)), int(np.max(c - r))
    if _band_work(n, kl, ku) <= WORK_BUDGET:
        return _banded(st, b, dt, kl, ku)
    perm = _rcm(st)
    inv = np.empty(n, dtype=np.int64)
    inv[perm] = np.arange(n)
    pr, pc = inv[r], inv[c]
    kl, ku = int(np.max(pr - pc)), int(np.max(pc - pr))
    if _band_work(n, kl, ku) > WORK_BUDGET:
        return None
    from openmatlab.numerics.sparse_store import Store

    ps = Store(n, n, pr, pc, st.data)
    y = _banded(ps, b[perm], dt, max(kl, 0), max(ku, 0))
    if y is None:
        return None
    x = np.empty_like(y)
    x[perm] = y
    return x


def _band_work(n, kl, ku):
    return float(n) * (kl + 1) * (2 * kl + ku + 1)


def _well_conditioned(piv):
    a = np.abs(piv)
    return a.size and a.min() > 0 and a.min() / a.max() >= EPS


def _triangular(st, b, dt, *, lower):
    n = st.n
    diag_mask = st.rows == st.cols
    if int(diag_mask.sum()) != n:
        return None  # a structural zero on the diagonal: singular
    d = np.zeros(n, dtype=dt)
    d[st.cols[diag_mask]] = st.data[diag_mask]
    if not _well_conditioned(d):
        return None
    ptr = st.indptr
    rows, vals = st.rows, st.data.astype(dt)
    x = b.copy()
    order = range(n) if lower else range(n - 1, -1, -1)
    for j in order:
        x[j] /= d[j]
        lo, hi = ptr[j], ptr[j + 1]
        if hi - lo > 1:
            rr, vv = rows[lo:hi], vals[lo:hi]
            off = rr != j
            x[rr[off]] -= vv[off, None] * x[j]
    return x


def _banded(st, b, dt, kl, ku):
    """Banded LU with partial pivoting; rows streamed from a CSR view."""
    n = st.n
    w = kl + ku + kl + 1  # U gains up to kl extra superdiagonals from row swaps
    t = st.transpose()  # CSR of st: row i entries are t's column i
    tptr, tcols, tvals = t.indptr, t.rows, t.data.astype(dt)

    def load(i, start):
        out = np.zeros(w, dtype=dt)
        lo, hi = tptr[i], tptr[i + 1]
        out[tcols[lo:hi] - start] = tvals[lo:hi]
        return out

    win = np.zeros((kl + 1, w), dtype=dt)
    for q in range(min(kl + 1, n)):
        win[q] = load(q, 0)
    rhs = b.copy()
    U = np.zeros((n, w), dtype=dt)
    piv_abs = np.zeros(n)
    for k in range(n):
        h = min(kl + 1, n - k)
        col = np.abs(win[:h, 0])
        p = int(np.argmax(col))
        if col[p] == 0:
            return None
        if p:
            win[[0, p]] = win[[p, 0]]
            rhs[[k, k + p]] = rhs[[k + p, k]]
        pivot = win[0, 0]
        piv_abs[k] = abs(pivot)
        if h > 1:
            l = win[1:h, 0] / pivot
            win[1:h] -= l[:, None] * win[0]
            rhs[k + 1:k + h] -= l[:, None] * rhs[k]
        U[k] = win[0]
        # slide: drop row k, shift columns left by one, stream in row k+kl+1
        win[:-1] = win[1:]
        win[:, :-1] = win[:, 1:].copy()
        win[:, -1] = 0
        nxt = k + kl + 1
        win[-1] = load(nxt, k + 1) if nxt < n else 0
    if piv_abs.min() / piv_abs.max() < EPS:
        return None
    x = np.zeros_like(rhs)
    for k in range(n - 1, -1, -1):
        e = min(w, n - k)
        s = rhs[k] - (U[k, 1:e, None] * x[k + 1:k + e]).sum(axis=0) if e > 1 else rhs[k]
        x[k] = s / U[k, 0]
    return x


def _rcm(st):
    """Reverse Cuthill-McKee ordering of the symmetric pattern of st."""
    n = st.n
    r = np.concatenate([st.rows, st.cols])
    c = np.concatenate([st.cols, st.rows])
    keep = r != c
    r, c = r[keep], c[keep]
    order = np.lexsort((c, r))
    r, c = r[order], c[order]
    ptr = np.searchsorted(r, np.arange(n + 1))
    deg = np.diff(ptr)
    seen = np.zeros(n, bool)
    out = []
    for start in np.argsort(deg, kind="stable"):
        if seen[start]:
            continue
        seen[start] = True
        q = deque([int(start)])
        while q:
            v = q.popleft()
            out.append(v)
            nb = np.unique(c[ptr[v]:ptr[v + 1]])
            nb = nb[~seen[nb]]
            if nb.size:
                nb = nb[np.argsort(deg[nb], kind="stable")]
                seen[nb] = True
                q.extend(int(x) for x in nb)
    return np.array(out[::-1], dtype=np.int64)
