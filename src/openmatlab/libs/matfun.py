"""funm, logm and the complex Schur form they share (C-E5 #765 T2 burn-down).

Clean-room, NumPy only, against the MATLAB documentation, which cites the algorithms:

* complex Schur form: Householder reduction to Hessenberg form, then the shifted QR iteration with Wilkinson
  shifts and deflation (Golub & Van Loan, Matrix Computations, 4th ed., 7.4-7.5);
* ``funm``: the Schur-Parlett algorithm of Davies & Higham (SIAM J. Matrix Anal. Appl. 25(2), 2003):
  eigenvalues within ``TolBlk`` are clustered, the clusters are made contiguous by swapping adjacent diagonal
  entries, each diagonal block is evaluated by a Taylor series about its mean eigenvalue and the off-diagonal
  blocks by the block Parlett recurrence (triangular Sylvester equations);
* ``logm``: inverse scaling and squaring on the triangular factor (repeated triangular square roots, then a
  Gauss-Legendre quadrature form of the diagonal Pade approximant of log(I + X), Higham, Functions of
  Matrices, 2008, 11.3-11.5).
"""

from __future__ import annotations

import math
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

from .burndown_builtins import _err, _is_text

_EPS = np.finfo(float).eps


# --- complex Schur form ----------------------------------------------------------------------------------

def _hessenberg(a: np.ndarray):
    n = a.shape[0]
    h = a.astype(complex).copy()
    q = np.eye(n, dtype=complex)
    for k in range(n - 2):
        x = h[k + 1:, k].copy()
        nx = np.linalg.norm(x)
        if nx == 0:
            continue
        alpha = -np.exp(1j * np.angle(x[0])) * nx if x[0] != 0 else -nx
        v = x
        v[0] -= alpha
        nv = np.linalg.norm(v)
        if nv == 0:
            continue
        v /= nv
        h[k + 1:, :] -= 2.0 * np.outer(v, v.conj() @ h[k + 1:, :])
        h[:, k + 1:] -= 2.0 * np.outer(h[:, k + 1:] @ v, v.conj())
        q[:, k + 1:] -= 2.0 * np.outer(q[:, k + 1:] @ v, v.conj())
        h[k + 2:, k] = 0
    return h, q


def _givens(a: complex, b: complex):
    """c (real), s with [c s; -conj(s) c] @ [a; b] = [r; 0]."""
    if b == 0:
        return 1.0, 0j
    if a == 0:
        return 0.0, np.conj(b) / abs(b)
    na = abs(a)
    nr = math.hypot(na, abs(b))
    c = na / nr
    s = (a / na) * np.conj(b) / nr
    return c, s


def _rot_rows(m, i, c, s, cols=slice(None)):
    r1, r2 = m[i, cols].copy(), m[i + 1, cols].copy()
    m[i, cols] = c * r1 + s * r2
    m[i + 1, cols] = -np.conj(s) * r1 + c * r2


def _rot_cols(m, i, c, s, rows=slice(None)):
    """m <- m G' on columns i, i+1 (G as in _rot_rows)."""
    c1, c2 = m[rows, i].copy(), m[rows, i + 1].copy()
    m[rows, i] = c * c1 + np.conj(s) * c2
    m[rows, i + 1] = -s * c1 + c * c2


def schur_complex(a: np.ndarray):
    """(U, T) with A = U T U', U unitary and T upper triangular."""
    n = a.shape[0]
    if n == 0:
        return np.zeros((0, 0), complex), np.zeros((0, 0), complex)
    h, q = _hessenberg(a)
    hi, its = n - 1, 0
    scale = max(np.abs(h).max(), np.finfo(float).tiny)
    while hi > 0:
        lo = hi
        while lo > 0 and abs(h[lo, lo - 1]) > _EPS * (abs(h[lo, lo]) + abs(h[lo - 1, lo - 1]) or _EPS * scale):
            lo -= 1
        if lo > 0:
            h[lo, lo - 1] = 0
        if lo == hi:
            hi, its = hi - 1, 0
            continue
        its += 1
        if its > 30 * n + 100:
            raise _err("The QR iteration did not converge.", "MATLAB:schur:noConvergence")
        # Wilkinson shift from the trailing 2x2 of the active window (exceptional shift now and then)
        a11, a12, a21, a22 = h[hi - 1, hi - 1], h[hi - 1, hi], h[hi, hi - 1], h[hi, hi]
        tr, det = a11 + a22, a11 * a22 - a12 * a21
        disc = np.sqrt(tr * tr / 4 - det)
        m1, m2 = tr / 2 + disc, tr / 2 - disc
        mu = m1 if abs(m1 - a22) < abs(m2 - a22) else m2
        if its % 11 == 0:
            mu = a22 + abs(h[hi, hi - 1]) * (1 + 1j)
        # explicit-shift QR sweep on rows/cols lo..hi, accumulated over the full matrix
        h[lo:hi + 1, lo:hi + 1] -= mu * np.eye(hi - lo + 1)
        rots = []
        for k in range(lo, hi):
            c, s = _givens(h[k, k], h[k + 1, k])
            _rot_rows(h, k, c, s, slice(k, n))
            h[k + 1, k] = 0
            rots.append((k, c, s))
        for k, c, s in rots:
            _rot_cols(h, k, c, s, slice(0, min(k + 2, hi) + 1))
            _rot_cols(q, k, c, s)
        h[lo:hi + 1, lo:hi + 1] += mu * np.eye(hi - lo + 1)
    return q, np.triu(h)


def swap_adjacent(t: np.ndarray, u: np.ndarray, k: int) -> None:
    """Exchange diagonal entries k and k+1 of the triangular T (in place, A = U T U' kept)."""
    a, b, c = t[k, k], t[k, k + 1], t[k + 1, k + 1]
    if a == c:
        return
    cg, sg = _givens(b, c - a)  # G [b; c-a] = [r; 0]: the eigenvector of c goes to e1
    _rot_rows(t, k, cg, sg)
    _rot_cols(t, k, cg, sg)
    _rot_cols(u, k, cg, sg)
    t[k + 1, k] = 0
    t[k, k], t[k + 1, k + 1] = c, a


# --- function derivatives --------------------------------------------------------------------------------

def _known_derivative(name: str):
    def f_exp(x, k):
        return np.exp(x)

    def f_sin(x, k):
        return [np.sin, np.cos, lambda z: -np.sin(z), lambda z: -np.cos(z)][k % 4](x)

    def f_cos(x, k):
        return [np.cos, lambda z: -np.sin(z), lambda z: -np.cos(z), np.sin][k % 4](x)

    def f_sinh(x, k):
        return np.sinh(x) if k % 2 == 0 else np.cosh(x)

    def f_cosh(x, k):
        return np.cosh(x) if k % 2 == 0 else np.sinh(x)

    def f_log(x, k):
        if k == 0:
            return np.log(x.astype(complex)) if np.any(np.real(x) < 0) or np.iscomplexobj(x) else np.log(x)
        return (-1.0) ** (k - 1) * math.factorial(k - 1) / x ** k

    return {"exp": f_exp, "sin": f_sin, "cos": f_cos, "sinh": f_sinh, "cosh": f_cosh, "log": f_log}.get(name)


def _deriv_fn(fun) -> Callable:
    name = getattr(fun, "name", None) if hasattr(fun, "call") else None
    if _is_text(fun):
        name = fun.text if hasattr(fun, "text") else str(fun.data.flat[0])
    if name:
        known = _known_derivative(name.lstrip("@"))
        if known is not None:
            return known
    if not hasattr(fun, "call"):
        raise _err("funm: FUN must be a function handle or function name.", "MATLAB:funm:invalidFun")

    def user(x, k):
        out = fun.call([NDArrayValue(x.reshape(-1, 1)), NDArrayValue(np.array([[float(k)]]))], nargout=1)
        return np.asarray(out[0].backend_buffer()).reshape(-1)

    return user


# --- Schur-Parlett ----------------------------------------------------------------------------------------

def _blocking(ev: np.ndarray, delta: float):
    """Davies-Higham clustering: a set index per diagonal position, sets numbered by first appearance."""
    n = ev.size
    m = [0] * n
    nxt = 1
    for i in range(n):
        if m[i] == 0:
            m[i], nxt = nxt, nxt + 1
        for j in range(i + 1, n):
            if m[j] != m[i] and abs(ev[i] - ev[j]) <= delta:
                if m[j] == 0:
                    m[j] = m[i]
                else:
                    old, new = max(m[i], m[j]), min(m[i], m[j])
                    m = [new if v == old else v for v in m]
    # renumber consecutively by first appearance
    seen: Dict[int, int] = {}
    return [seen.setdefault(v, len(seen) + 1) for v in m]


def _reorder(t, u, ord_):
    """Make the sets contiguous, ordered by their mean position (stable); returns the index blocks."""
    n = len(ord_)
    sets = sorted(set(ord_), key=lambda s: (np.mean([i for i, v in enumerate(ord_) if v == s]), s))
    target = [sets.index(v) for v in ord_]
    cur = list(target)
    for i in range(n):  # bubble sort by target rank via adjacent swaps
        for k in range(n - 1 - i):
            if cur[k] > cur[k + 1]:
                swap_adjacent(t, u, k)
                cur[k], cur[k + 1] = cur[k + 1], cur[k]
    blocks, start = [], 0
    for r in range(len(sets)):
        size = cur.count(r)
        blocks.append(list(range(start, start + size)))
        start += size
    return blocks


def _taylor_block(tb, f, tol, maxterms):
    n = tb.shape[0]
    if n == 1:
        return np.array([[f(np.array([tb[0, 0]]), 0)[0]]], dtype=complex), 1, True
    sigma = np.mean(np.diag(tb))
    m = tb - sigma * np.eye(n)
    p = np.eye(n, dtype=complex)
    fs = np.array([sigma])
    F = f(fs, 0)[0] * np.eye(n, dtype=complex)
    mk = np.eye(n, dtype=complex)
    for k in range(1, maxterms + 1):
        p = p @ m / k
        mk = mk @ m
        term = f(fs, k)[0] * p
        F = F + term
        fn = np.abs(F).sum(axis=0).max()
        if np.abs(term).sum(axis=0).max() <= tol * fn:
            # the next derivatives cannot revive the series (truncation bound with ||M^(k+1)||)
            nxt = max(abs(f(fs, k + r)[0]) / math.factorial(k + r) for r in range(1, n + 1))
            if nxt * np.abs(mk @ m).sum(axis=0).max() <= tol * fn:
                return F, k + 1, True
    return F, maxterms, False


def _sylvester_tri(a, b, c):
    """Solve A X - X B = C for upper-triangular A, B (column by column)."""
    x = np.zeros(c.shape, dtype=complex)
    na = a.shape[0]
    for j in range(b.shape[0]):
        rhs = c[:, j] + x[:, :j] @ b[:j, j]
        x[:, j] = np.linalg.solve(np.triu(a) - b[j, j] * np.eye(na), rhs)
    return x


def schur_parlett(a, f, tol_blk=0.1, tol_tay=_EPS, max_terms=250, ord_=None):
    u, t = schur_complex(a)
    n = t.shape[0]
    ev = np.diag(t).copy()
    ord_ = list(ord_) if ord_ is not None else _blocking(ev, tol_blk)
    blocks = _reorder(t, u, ord_)
    F = np.zeros((n, n), dtype=complex)
    terms, ok = [], True
    for blk in blocks:
        s = slice(blk[0], blk[-1] + 1)
        fb, nt, conv = _taylor_block(t[s, s], f, tol_tay, max_terms)
        F[s, s] = fb
        terms.append(nt)
        ok = ok and conv
    nb = len(blocks)
    for d in range(1, nb):
        for i in range(nb - d):
            j = i + d
            si = slice(blocks[i][0], blocks[i][-1] + 1)
            sj = slice(blocks[j][0], blocks[j][-1] + 1)
            c = F[si, si] @ t[si, sj] - t[si, sj] @ F[sj, sj]
            for k in range(i + 1, j):
                sk = slice(blocks[k][0], blocks[k][-1] + 1)
                c = c + F[si, sk] @ t[sk, sj] - t[si, sk] @ F[sk, sj]
            F[si, sj] = _sylvester_tri(t[si, si], t[sj, sj], c)
    return u @ F @ u.conj().T, t, u, ord_, blocks, terms, ok


# --- builtins ---------------------------------------------------------------------------------------------

def _square(v, fn):
    buf = getattr(v, "backend_buffer", None)
    if buf is None or _is_text(v):
        raise _err(f"{fn}: A must be a numeric square matrix.", f"MATLAB:{fn}:inputMustBeSquare")
    a = np.asarray(buf())
    a = a.reshape(1, 1) if a.ndim == 0 else a
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise _err(f"{fn}: A must be a numeric square matrix.", "MATLAB:square")
    single = a.dtype == np.float32 or a.dtype == np.complex64
    return a.astype(complex if np.iscomplexobj(a) else float), single


def _cast(r, single, real_input):
    r = np.asarray(r)
    if np.iscomplexobj(r) and real_input:
        if np.abs(r.imag).sum() <= 10 * max(r.shape[0], 1) * _EPS * max(np.abs(r).sum(), np.finfo(float).tiny):
            r = r.real
    if single:
        r = r.astype(np.complex64 if np.iscomplexobj(r) else np.float32)
    return NDArrayValue(r)


def _opt(opts, name):
    if opts is None or not opts.has(name):
        return None
    return np.asarray(opts.get(name).backend_buffer())


def _funm(args, *, nargout=1):
    from openmatlab.runtime.struct_value import StructValue, is_struct

    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    a, single = _square(args[0], "funm")
    f = _deriv_fn(args[1])
    opts = None
    if len(args) > 2:
        if not is_struct(args[2]) or not args[2].is_scalar():
            raise _err("funm: OPTIONS must be a scalar struct.", "MATLAB:funm:invalidOptions")
        opts = args[2]
    tol_blk = _opt(opts, "TolBlk")
    tol_tay = _opt(opts, "TolTay")
    max_terms = _opt(opts, "MaxTerms")
    ord_ = _opt(opts, "Ord")
    tol_blk = 0.1 if tol_blk is None else float(tol_blk.reshape(-1)[0])
    tol_tay = _EPS if tol_tay is None else float(tol_tay.reshape(-1)[0])
    max_terms = 250 if max_terms is None else int(max_terms.reshape(-1)[0])
    n = a.shape[0]
    if n == 0:
        F, t, ord_l, blocks, terms, ok = np.zeros((0, 0)), np.zeros((0, 0)), [], [], [], True
    else:
        if ord_ is not None:
            ord_ = [int(v) for v in ord_.reshape(-1)]
        F, t, _u, ord_l, blocks, terms, ok = schur_parlett(a, f, tol_blk, tol_tay, max_terms, ord_)
    real_input = not np.iscomplexobj(a)
    out = [_cast(F, single, real_input)]
    if nargout > 1:
        out.append(NDArrayValue(np.array([[0.0 if ok else 1.0]])))
    if nargout > 2:
        ind = _cell_row([NDArrayValue(np.array([[float(i + 1) for i in b]])) for b in blocks])
        tt = np.asarray(t)
        out.append(StructValue.scalar([
            ("terms", NDArrayValue(np.array([[float(x) for x in terms]]).reshape(1, -1))),
            ("ind", ind),
            ("ord", NDArrayValue(np.array([[float(x) for x in ord_l]]).reshape(1, -1))),
            ("T", _cast(tt, single, False)),
        ]))
    return tuple(out)


def _cell_row(items):
    from .burndown_builtins import _cell

    return _cell(items, (1, len(items)))


def _sqrt_tri(t):
    """Principal square root of an upper-triangular matrix (Bjorck-Hammarling recurrence)."""
    n = t.shape[0]
    r = np.zeros_like(t, dtype=complex)
    for j in range(n):
        r[j, j] = np.sqrt(t[j, j])
        for i in range(j - 1, -1, -1):
            s = t[i, j] - r[i, i + 1:j] @ r[i + 1:j, j]
            d = r[i, i] + r[j, j]
            r[i, j] = s / d if d != 0 else (0 if s == 0 else np.inf)
    return r


def _logm_tri(t):
    n = t.shape[0]
    eye = np.eye(n)
    r, s = t.astype(complex), 0
    while np.abs(r - eye).sum(axis=0).max() > 0.25 and s < 100:
        r, s = _sqrt_tri(r), s + 1
    x = r - eye
    nodes, weights = np.polynomial.legendre.leggauss(12)
    nodes, weights = (nodes + 1) / 2, weights / 2
    lg = np.zeros((n, n), dtype=complex)
    for xj, wj in zip(nodes, weights):
        lg += wj * np.linalg.solve(eye + xj * x, x)
    return (2.0 ** s) * lg


def _logm(args, *, nargout=1):
    from .quadrature import _warn

    if len(args) != 1:
        raise _err("Not enough input arguments." if not args else "Too many input arguments.",
                   "MATLAB:minrhs" if not args else "MATLAB:TooManyInputs")
    a, single = _square(args[0], "logm")
    n = a.shape[0]
    if n == 0:
        return (NDArrayValue(np.zeros((0, 0))),)
    u, t = schur_complex(a)
    ev = np.diag(t)
    if np.any(ev == 0):
        _warn("Principal matrix logarithm is not defined for A with nonpositive real eigenvalues. "
              "A non-principal matrix logarithm is returned.", "MATLAB:logm:nonPosRealEig")
    elif np.any((np.abs(ev.imag) <= _EPS * np.abs(ev)) & (ev.real < 0)):
        _warn("Principal matrix logarithm is not defined for A with nonpositive real eigenvalues. "
              "A non-principal matrix logarithm is returned.", "MATLAB:logm:nonPosRealEig")
    if np.allclose(t, np.diag(ev), atol=0, rtol=0):
        lt = np.diag(np.log(ev.astype(complex)))
    else:
        with np.errstate(all="ignore"):
            lt = _logm_tri(t)
    r = u @ lt @ u.conj().T
    real_input = not np.iscomplexobj(a)
    if real_input and np.any((np.abs(ev.imag) <= _EPS * np.abs(ev)) & (ev.real < 0)):
        real_input = False
    return (_cast(r, single, real_input),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.setdefault("funm", _funm)
    builtins.setdefault("logm", _logm)
