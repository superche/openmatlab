"""Compressed sparse column storage for MATLAB sparse matrices (Epic #520).

``Store`` keeps only the nonzeros of an m x n matrix, sorted column-major
(column, then row) and duplicate-free, with no explicit zeros. That ordering
is exactly CSC: ``indptr`` (column pointers) is derived on demand, ``rows`` is
the row-index array and ``data`` the values. Memory is O(nnz + n) for the
pointer view and O(nnz) otherwise; nothing here allocates m*n.

Every kernel returns ``None`` when it cannot reproduce dense IEEE semantics
exactly (e.g. ``S .* F`` where ``F`` holds Inf/NaN at a structural zero); the
caller then takes the dense path, so results never diverge from full math.
"""

from __future__ import annotations

import numpy as np

_FLOAT_DTYPES = (np.dtype(np.float64), np.dtype(np.complex128), np.dtype(np.bool_))


def _canon_dtype(dt) -> np.dtype:
    dt = np.dtype(dt)
    if dt == np.bool_:
        return dt
    return np.dtype(np.complex128) if np.issubdtype(dt, np.complexfloating) else np.dtype(np.float64)


class Store:
    __slots__ = ("m", "n", "rows", "cols", "data")

    def __init__(self, m: int, n: int, rows, cols, data, *, canonical: bool = False, dtype=None):
        self.m, self.n = int(m), int(n)
        rows = np.asarray(rows, dtype=np.int64).reshape(-1)
        cols = np.asarray(cols, dtype=np.int64).reshape(-1)
        data = np.asarray(data).reshape(-1)
        dt = _canon_dtype(dtype if dtype is not None else (data.dtype if data.size else np.float64))
        if data.dtype != dt:
            data = data.astype(dt)
        if not canonical:
            rows, cols, data = _coalesce(self.m, rows, cols, data)
        self.rows, self.cols, self.data = rows, cols, data

    # --- views ---------------------------------------------------------------
    @property
    def dtype(self) -> np.dtype:
        return self.data.dtype

    @property
    def shape(self):
        return (self.m, self.n)

    @property
    def nnz(self) -> int:
        return int(self.data.size)

    @property
    def indptr(self) -> np.ndarray:
        return np.searchsorted(self.cols, np.arange(self.n + 1)).astype(np.int64)

    @property
    def keys(self) -> np.ndarray:
        return self.cols * self.m + self.rows

    def to_dense(self) -> np.ndarray:
        out = np.zeros((self.m, self.n), dtype=self.dtype)
        out[self.rows, self.cols] = self.data
        return out

    def with_data(self, data, dtype=None) -> "Store":
        data = np.asarray(data)
        keep = data != 0
        return Store(self.m, self.n, self.rows[keep], self.cols[keep], data[keep], canonical=True,
                     dtype=dtype if dtype is not None else data.dtype)

    # --- constructors ----------------------------------------------------------
    @staticmethod
    def zeros(m, n, dtype=np.float64) -> "Store":
        e = np.zeros(0, dtype=np.int64)
        return Store(m, n, e, e, np.zeros(0, dtype=dtype), canonical=True, dtype=dtype)

    @staticmethod
    def from_dense(a) -> "Store":
        a = np.asarray(a)
        a = a.reshape(1, 1) if a.ndim == 0 else (a.reshape(1, -1) if a.ndim == 1 else a)
        cols, rows = np.nonzero(a.T)
        return Store(a.shape[0], a.shape[1], rows, cols, a[rows, cols], canonical=True, dtype=a.dtype)

    @staticmethod
    def eye(m, n) -> "Store":
        k = np.arange(min(m, n), dtype=np.int64)
        return Store(m, n, k, k, np.ones(k.size), canonical=True)

    @staticmethod
    def from_triplets(m, n, rows, cols, vals) -> "Store":
        """sparse(i,j,v,m,n): duplicates add (logical: OR)."""
        return Store(m, n, rows, cols, vals)

    # --- structure ops -----------------------------------------------------------
    def transpose(self, conj: bool = False) -> "Store":
        d = self.data.conj() if conj and self.dtype == np.complex128 else self.data
        order = np.lexsort((self.cols, self.rows))
        return Store(self.n, self.m, self.cols[order], self.rows[order], d[order], canonical=True, dtype=self.dtype)

    def reshape(self, m, n) -> "Store":
        k = self.keys
        cols, rows = np.divmod(k, m) if m else (k, k)
        return Store(m, n, rows, cols, self.data, canonical=True, dtype=self.dtype)

    def find(self):
        """(rows, cols, vals) in column-major order, 0-based."""
        return self.rows, self.cols, self.data

    def astype(self, dt) -> "Store":
        dt = _canon_dtype(dt)
        if dt == np.bool_:
            return Store(self.m, self.n, self.rows, self.cols, np.ones(self.nnz, bool), canonical=True, dtype=dt)
        return Store(self.m, self.n, self.rows, self.cols, self.data.astype(dt), canonical=True, dtype=dt)

    # --- arithmetic --------------------------------------------------------------
    def scale(self, k) -> "Store | None":
        k = np.asarray(k).reshape(-1)[0]
        if not np.isfinite(k):
            return None  # 0*Inf = NaN fills the matrix: dense semantics
        d = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
        return self.with_data(d * k)

    def neg(self) -> "Store":
        d = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
        return self.with_data(-d)

    def add(self, other: "Store", sign: float = 1.0) -> "Store":
        a = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
        b = other.data.astype(np.float64) if other.dtype == np.bool_ else other.data
        dt = np.result_type(a, b, np.float64)
        return Store(self.m, self.n, np.concatenate([self.rows, other.rows]),
                     np.concatenate([self.cols, other.cols]),
                     np.concatenate([a.astype(dt), sign * b.astype(dt)]), dtype=dt)

    def emul(self, other: "Store") -> "Store":
        ka, kb = self.keys, other.keys
        common, ia, ib = np.intersect1d(ka, kb, assume_unique=True, return_indices=True)
        a = self.data[ia].astype(np.float64) if self.dtype == np.bool_ else self.data[ia]
        b = other.data[ib].astype(np.float64) if other.dtype == np.bool_ else other.data[ib]
        v = a * b
        keep = v != 0
        return Store(self.m, self.n, self.rows[ia][keep], self.cols[ia][keep], v[keep], canonical=True, dtype=v.dtype)

    def emul_dense(self, f) -> "Store | None":
        f = np.asarray(f)
        if f.shape != self.shape or f.dtype == np.bool_ and False:
            return None
        if not np.all(np.isfinite(f)):
            return None
        a = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
        b = f[self.rows, self.cols]
        b = b.astype(np.float64) if b.dtype == np.bool_ else b
        return self.with_data(a * b)

    def ediv_dense(self, f) -> "Store | None":
        f = np.asarray(f)
        if f.size == 1:
            k = f.reshape(-1)[0]
            if k == 0 or not np.isfinite(k):
                return None
            return self.scale(1.0 / k)
        if f.shape != self.shape or not np.all(np.isfinite(f)) or np.any(f == 0):
            return None
        a = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
        return self.with_data(a / f[self.rows, self.cols])

    def map(self, fn) -> "Store | None":
        """Zero-preserving elementwise function (fn(0) == 0 required)."""
        with np.errstate(all="ignore"):
            z = fn(np.zeros(1, dtype=np.float64 if self.dtype == np.bool_ else self.dtype))
            if np.asarray(z).reshape(-1)[0] != 0:
                return None
            d = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
            return self.with_data(np.asarray(fn(d)))

    def matvec(self, x) -> "np.ndarray | None":
        """S @ X for dense 2-D X -> dense (m x k)."""
        x = np.asarray(x)
        if x.ndim != 2 or x.shape[0] != self.n or not np.all(np.isfinite(x)):
            return None
        a = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
        xx = x.astype(np.float64) if x.dtype == np.bool_ else x
        dt = np.result_type(a, xx, np.float64)
        out = np.zeros((self.m, x.shape[1]), dtype=dt)
        np.add.at(out, self.rows, a[:, None] * xx[self.cols, :])
        return out

    def rmatvec(self, x) -> "np.ndarray | None":
        """X @ S for dense 2-D X -> dense."""
        x = np.asarray(x)
        if x.ndim != 2 or x.shape[1] != self.m:
            return None
        t = self.transpose().matvec(x.T)
        return None if t is None else t.T.copy()

    def matmul(self, other: "Store") -> "Store":
        """Sparse * sparse without densifying (expand-and-coalesce)."""
        a = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
        b = other.data.astype(np.float64) if other.dtype == np.bool_ else other.data
        ptr = self.indptr
        counts = ptr[other.rows + 1] - ptr[other.rows]  # A col k entries for each B(k,j)
        total = int(counts.sum())
        if total == 0:
            return Store.zeros(self.m, other.n, np.result_type(a, b, np.float64))
        rep = np.repeat(np.arange(other.nnz), counts)
        starts = np.repeat(ptr[other.rows] - np.cumsum(counts) + counts, counts)
        pos = starts + np.arange(total)
        return Store(self.m, other.n, self.rows[pos], other.cols[rep], a[pos] * b[rep],
                     dtype=np.result_type(a, b, np.float64))

    def sum(self, axis: int) -> "Store":
        d = self.data.astype(np.float64) if self.dtype == np.bool_ else self.data
        if axis == 0:
            idx, n = self.cols, self.n
        else:
            idx, n = self.rows, self.m
        u, inv = np.unique(idx, return_inverse=True)
        s = np.zeros(u.size, dtype=d.dtype)
        np.add.at(s, inv, d)
        z = np.zeros(u.size, dtype=np.int64)
        if axis == 0:
            return Store(1, n, z, u, s, dtype=d.dtype)
        return Store(n, 1, u, z, s, dtype=d.dtype)

    def extreme(self, axis: int, is_max: bool) -> "Store | None":
        """max/min along axis including implicit zeros (real data only)."""
        if self.dtype == np.complex128 or np.any(np.isnan(self.data.astype(float))):
            return None
        d = self.data.astype(np.float64)
        idx, length, n = (self.cols, self.m, self.n) if axis == 0 else (self.rows, self.n, self.m)
        u, inv, cnt = np.unique(idx, return_inverse=True, return_counts=True)
        s = np.full(u.size, -np.inf if is_max else np.inf)
        (np.maximum if is_max else np.minimum).at(s, inv, d)
        part = cnt < length  # an implicit zero takes part
        s[part] = np.maximum(s[part], 0) if is_max else np.minimum(s[part], 0)
        z = np.zeros(u.size, dtype=np.int64)
        if self.dtype == np.bool_:
            s = s != 0
        if axis == 0:
            return Store(1, n, z, u, s, dtype=s.dtype)
        return Store(n, 1, u, z, s, dtype=s.dtype)

    # --- indexing ----------------------------------------------------------------
    def get_linear(self, k) -> np.ndarray:
        """Values at 0-based linear positions k (any shape) -> dense values array."""
        k = np.asarray(k, dtype=np.int64)
        keys = self.keys
        pos = np.searchsorted(keys, k.reshape(-1))
        pos_c = np.minimum(pos, max(keys.size - 1, 0))
        hit = (keys.size > 0) & (keys[pos_c] == k.reshape(-1)) if keys.size else np.zeros(k.size, bool)
        out = np.zeros(k.size, dtype=self.dtype)
        out[hit] = self.data[pos_c[hit]]
        return out

    def take_linear(self, k, m, n) -> "Store":
        """Sparse result of shape m x n holding self at 0-based linear positions k (column-major)."""
        k = np.asarray(k, dtype=np.int64).reshape(-1)
        keys = self.keys
        if keys.size == 0 or k.size == 0:
            return Store.zeros(m, n, self.dtype)
        pos = np.searchsorted(keys, k)
        pos_c = np.minimum(pos, keys.size - 1)
        hit = np.nonzero(keys[pos_c] == k)[0]
        cols, rows = np.divmod(hit, m) if m else (hit, hit)
        return Store(m, n, rows, cols, self.data[pos_c[hit]], canonical=True, dtype=self.dtype)

    def submatrix(self, I, J) -> "Store":
        """S(I, J) for 0-based index vectors (repeats allowed)."""
        I = np.asarray(I, dtype=np.int64).reshape(-1)
        J = np.asarray(J, dtype=np.int64).reshape(-1)
        ptr = self.indptr
        counts = ptr[J + 1] - ptr[J]
        total = int(counts.sum())
        if total == 0 or I.size == 0:
            return Store.zeros(I.size, J.size, self.dtype)
        newcol = np.repeat(np.arange(J.size), counts)
        pos = np.repeat(ptr[J] - np.cumsum(counts) + counts, counts) + np.arange(total)
        r = self.rows[pos]
        # map each source row to every position p with I[p] == r
        order = np.argsort(I, kind="stable")
        sI = I[order]
        lo = np.searchsorted(sI, r, "left")
        hi = np.searchsorted(sI, r, "right")
        mult = hi - lo
        tot2 = int(mult.sum())
        if tot2 == 0:
            return Store.zeros(I.size, J.size, self.dtype)
        src = np.repeat(np.arange(r.size), mult)
        within = np.arange(tot2) - np.repeat(np.cumsum(mult) - mult, mult)
        newrow = order[np.repeat(lo, mult) + within]
        return Store(I.size, J.size, newrow, newcol[src], self.data[pos][src], dtype=self.dtype)

    def assign_block(self, I, J, vals, m, n) -> "Store":
        """Return S grown to m x n with S(I,J) = vals (dense block |I| x |J| or scalar)."""
        I = np.asarray(I, dtype=np.int64).reshape(-1)
        J = np.asarray(J, dtype=np.int64).reshape(-1)
        vals = np.asarray(vals)
        if vals.size == 1:
            vals = np.broadcast_to(vals.reshape(1, 1), (I.size, J.size))
        vals = vals.reshape(I.size, J.size)
        # last assignment wins for repeated subscripts (MATLAB)
        RR = np.repeat(I[:, None], J.size, 1).reshape(-1, order="F")
        CC = np.repeat(J[None, :], I.size, 0).reshape(-1, order="F")
        VV = vals.reshape(-1, order="F")
        newkeys = CC * m + RR
        _, last = np.unique(newkeys[::-1], return_index=True)
        last = newkeys.size - 1 - last
        RR, CC, VV = RR[last], CC[last], VV[last]
        oldkeys = self.cols * m + self.rows
        keep = ~np.isin(oldkeys, CC * m + RR)
        dt = np.bool_ if self.dtype == np.bool_ else np.result_type(self.data, VV, np.float64)
        nz = VV != 0
        return Store(m, n, np.concatenate([self.rows[keep], RR[nz]]), np.concatenate([self.cols[keep], CC[nz]]),
                     np.concatenate([self.data[keep].astype(dt), VV[nz].astype(dt)]), dtype=dt)

    def assign_linear(self, k, vals, m, n) -> "Store":
        k = np.asarray(k, dtype=np.int64).reshape(-1)
        vals = np.asarray(vals).reshape(-1, order="F")
        if vals.size == 1:
            vals = np.broadcast_to(vals, k.shape)
        _, last = np.unique(k[::-1], return_index=True)
        last = k.size - 1 - last
        k, vals = k[last], vals[last]
        cols, rows = np.divmod(k, m) if m else (k, k)
        oldkeys = self.cols * m + self.rows
        keep = ~np.isin(oldkeys, k)
        dt = self.dtype if self.dtype == np.bool_ else np.result_type(self.data, vals, np.float64)
        nz = vals != 0
        return Store(m, n, np.concatenate([self.rows[keep], rows[nz]]), np.concatenate([self.cols[keep], cols[nz]]),
                     np.concatenate([self.data[keep].astype(dt), vals[nz].astype(dt)]), dtype=dt)

    def delete_rows(self, I) -> "Store":
        drop = np.zeros(self.m, bool)
        drop[np.asarray(I, dtype=np.int64)] = True
        newidx = np.cumsum(~drop) - 1
        keep = ~drop[self.rows]
        return Store(self.m - int(drop.sum()), self.n, newidx[self.rows[keep]], self.cols[keep], self.data[keep],
                     canonical=True, dtype=self.dtype)

    def delete_cols(self, J) -> "Store":
        return self.transpose().delete_rows(J).transpose()


def _coalesce(m, rows, cols, data):
    if data.size == 0:
        return rows, cols, data
    keys = cols * max(m, 1) + rows
    u, inv = np.unique(keys, return_inverse=True)
    if u.size != keys.size:
        if data.dtype == np.bool_:
            acc = np.zeros(u.size, bool)
            np.logical_or.at(acc, inv, data)
        else:
            acc = np.zeros(u.size, dtype=data.dtype)
            np.add.at(acc, inv, data)
        data = acc
    else:
        order = np.argsort(keys, kind="stable")
        data = data[order]
    keep = data != 0
    u = u[keep]
    data = data[keep]
    c, r = np.divmod(u, max(m, 1))
    return r.astype(np.int64), c.astype(np.int64), data


def concat(blocks) -> Store:
    """[B11 B12; B21 B22] from a list of rows of Stores (dims already checked)."""
    rows_all, cols_all, vals_all = [], [], []
    r0 = 0
    total_n = 0
    dts = []
    for row in blocks:
        c0 = 0
        h = 0
        for b in row:
            rows_all.append(b.rows + r0)
            cols_all.append(b.cols + c0)
            vals_all.append(b.data)
            dts.append(b.dtype)
            c0 += b.n
            h = max(h, b.m)
        total_n = max(total_n, c0)
        r0 += h
    dt = np.bool_ if all(d == np.bool_ for d in dts) else np.result_type(*[np.float64 if d == np.bool_ else d for d in dts])
    vals = [v.astype(dt) for v in vals_all]
    return Store(r0, total_n, np.concatenate(rows_all) if rows_all else [], np.concatenate(cols_all) if cols_all else [],
                 np.concatenate(vals) if vals else np.zeros(0, dt), dtype=dt)
