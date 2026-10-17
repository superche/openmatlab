"""gallery: classic test-matrix families (C-E5 #765 T2 burn-down).

Clean-room implementations from the published definitions (MATLAB ``gallery`` documentation and
N. J. Higham, "Accuracy and Stability of Numerical Algorithms", Appendix on test matrices). Families
that MATLAB returns as sparse are returned full (no sparse type yet). Random families draw from the
global ``rand``/``randn`` stream, or from a private stream when MATLAB documents a seed argument.
No MATLAB or Octave source was consulted.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

from .burndown_builtins import _err, _is_text, _num

EPS = 2.220446049250313e-16


def _o(a):
    a = np.asarray(a)
    if np.iscomplexobj(a) and not np.any(a.imag):
        a = a.real
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(-1, 1)
    return NDArrayValue(np.ascontiguousarray(a, dtype=a.dtype if a.dtype.kind in "fc" else float))


def _vec(a):
    return np.asarray(a, dtype=float if not np.iscomplexobj(a) else complex).reshape(-1)


def _n(a, fn="gallery"):
    a = np.asarray(a).reshape(-1)
    if a.size != 1:
        raise _err(f"gallery: {fn}: N must be a scalar.", "MATLAB:gallery:invalidN")
    return max(0, int(a[0]))


def _mn(a):
    a = np.asarray(a).reshape(-1)
    return (int(a[0]), int(a[0])) if a.size == 1 else (int(a[0]), int(a[1]))


def _seq(a):
    """Scalar n -> 1:n, vector -> itself."""
    a = np.asarray(a)
    return np.arange(1.0, _n(a) + 1) if a.size == 1 else _vec(a)


def _rs():
    from .math_builtins import _RNG

    return _RNG.rs


def _opt(args, i, default):
    if len(args) > i and np.asarray(args[i]).size:
        return float(np.asarray(args[i]).reshape(-1)[0])
    return default


def _tri(n, sub, d, sup):
    a = np.zeros((n, n))
    if n:
        a[np.arange(n), np.arange(n)] = d
        a[np.arange(1, n), np.arange(n - 1)] = sub
        a[np.arange(n - 1), np.arange(1, n)] = sup
    return a


def _hilb(n):
    i = np.arange(1, n + 1)
    return 1.0 / (i[:, None] + i[None, :] - 1)


def _orth_random(n):
    q, r = np.linalg.qr(_rs().standard_normal((n, n)))
    return q * np.sign(np.where(np.diag(r) == 0, 1, np.diag(r)))


# ---- families -------------------------------------------------------------------------

def cauchy(a):
    x = _seq(a[0])
    y = _seq(a[1]) if len(a) > 1 else x
    if x.size != y.size:
        raise _err("gallery: cauchy: X and Y must be vectors of the same length.", "MATLAB:gallery:cauchy")
    return [1.0 / (x[:, None] + y[None, :])]


def chebspec(a):
    n, k = _n(a[0]), int(_opt(a, 1, 0))
    m = n + 1 if k == 1 else n
    if m <= 1:
        return [np.zeros((n, n))]
    i = np.arange(m)
    x = np.cos(np.pi * i / (m - 1))
    c = np.where((i == 0) | (i == m - 1), 2.0, 1.0) * (-1.0) ** i
    dx = x[:, None] - x[None, :] + np.eye(m)
    d = (c[:, None] / c[None, :]) / dx
    d -= np.diag(d.sum(axis=1))
    return [d[1:, 1:] if k == 1 else d]


def chebvand(a):
    if len(a) > 1:
        m, p = _n(a[0]), a[1]
    else:
        m, p = None, a[0]
    p = np.asarray(p)
    p = np.linspace(0, 1, _n(p)) if p.size == 1 else _vec(p)
    m = p.size if m is None else m
    c = np.ones((m, p.size))
    if m > 1:
        c[1] = p
    for i in range(2, m):
        c[i] = 2 * p * c[i - 1] - c[i - 2]
    return [c]


def chow(a):
    n, alpha, delta = _n(a[0]), _opt(a, 1, 1.0), _opt(a, 2, 0.0)
    i, j = np.indices((n, n))
    h = np.where(j <= i + 1, alpha ** (i - j + 1.0), 0.0)
    return [h + delta * np.eye(n)]


def circul(a):
    v = _seq(a[0])
    n = v.size
    i, j = np.indices((n, n))
    return [v[(j - i) % n]]


def clement(a):
    n, k = _n(a[0]), int(_opt(a, 1, 0))
    z = np.arange(1.0, n)
    sup, sub = z, z[::-1].copy()
    if k == 1:
        sup = sub = np.sqrt(z * z[::-1])
    return [_tri(n, sub, 0.0, sup)]


def compar(a):
    x = np.asarray(a[0], dtype=float)
    k = int(_opt(a, 1, 0))
    c = -np.abs(x)
    if k == 1:
        off = np.abs(x) - np.diag(np.diag(np.abs(x))) if x.shape[0] == x.shape[1] else np.abs(x)
        c = -np.repeat(off.max(axis=1, keepdims=True), x.shape[1], axis=1)
    n = min(x.shape)
    c[np.arange(n), np.arange(n)] = np.abs(np.diag(x))
    return [c]


def cycol(a):
    m, n = _mn(a[0])
    k = int(_opt(a, 1, max(round(n / 4), 1)))
    b = _rs().standard_normal((m, k))
    return [np.tile(b, (1, -(-n // k)))[:, :n]]


def fiedler(a):
    c = _seq(a[0])
    return [np.abs(c[:, None] - c[None, :])]


def forsythe(a):
    n, alpha, lam = _n(a[0]), _opt(a, 1, math.sqrt(EPS)), _opt(a, 2, 0.0)
    j = jordbloc([n, lam])[0]
    if n:
        j[n - 1, 0] = alpha
    return [j]


def frank(a):
    n, k = _n(a[0]), int(_opt(a, 1, 0))
    i, j = np.indices((n, n))
    f = np.where(j >= i - 1, n - np.maximum(i, j), 0).astype(float)
    if k == 1:
        f = f[::-1, ::-1].T.copy()
    return [f]


def gcdmat(a):
    n = _n(a[0])
    i = np.arange(1, n + 1)
    return [np.gcd(i[:, None], i[None, :]).astype(float)]


def gearmat(a):
    n = _n(a[0])
    i, j = int(_opt(a, 1, n)), int(_opt(a, 2, -n))
    if not (1 <= abs(i) <= n and 1 <= abs(j) <= n):
        raise _err("gallery: gearmat: I and J must be in the range [-N, N] excluding 0.", "MATLAB:gallery:gearmat")
    g = _tri(n, 1.0, 0.0, 1.0)
    g[0, abs(i) - 1] = math.copysign(1, i)
    g[n - 1, n - abs(j)] = math.copysign(1, j)
    return [g]


def grcar(a):
    n, k = _n(a[0]), int(_opt(a, 1, 3))
    i, j = np.indices((n, n))
    return [np.where(j == i - 1, -1.0, np.where((j >= i) & (j <= i + k), 1.0, 0.0))]


def hanowa(a):
    n, d = _n(a[0]), _opt(a, 1, -1.0)
    if n % 2:
        raise _err("gallery: hanowa: N must be even.", "MATLAB:gallery:hanowa")
    m = n // 2
    e, g = d * np.eye(m), np.diag(np.arange(1.0, m + 1))
    return [np.block([[e, -g], [g, e]])]


def house(a):
    x = _vec(a[0]).astype(complex if np.iscomplexobj(a[0]) else float)
    nx = np.linalg.norm(x)
    if nx == 0:
        return [np.zeros((x.size, 1)), np.zeros((1, 1)), np.zeros((1, 1))]
    s = x[0] / abs(x[0]) if x[0] != 0 else 1.0
    v = x.copy()
    v[0] += s * nx
    beta = 1.0 / (np.conj(s) * nx * v[0]).real
    return [v.reshape(-1, 1), np.array([[beta]]), np.array([[-s * nx]])]


def invhess(a):
    x = _seq(a[0])
    n = x.size
    y = _vec(a[1]) if len(a) > 1 else -x[:n - 1]
    i, j = np.indices((n, n))
    yy = np.append(y, 0.0)
    return [np.where(i >= j, x[j], yy[np.minimum(i, n - 1)])]


def invol(a):
    n = _n(a[0])
    h = _hilb(n)
    d = -float(n)
    h[:, 0] *= d
    for i in range(n - 1):
        d = -(n + i + 1) * (n - i - 1) * d / ((i + 1) ** 2)
        h[i + 1, :] *= d
    return [h]


def ipjfact(a):
    n, k = _n(a[0]), int(_opt(a, 1, 0))
    i = np.arange(1, n + 1)
    f = np.array([[float(math.factorial(int(p + q))) for q in i] for p in i]).reshape(n, n)
    return [1.0 / f if k == 1 else f]


def jordbloc(a):
    n, lam = _n(a[0]), _opt(a, 1, 1.0)
    return [_tri(n, 0.0, lam, 1.0)]


def kahan(a):
    m, n = _mn(a[0])
    theta, pert = _opt(a, 1, 1.2), _opt(a, 2, 25.0)
    r = min(m, n)
    s, c = math.sin(theta), math.cos(theta)
    u = np.eye(m, n) - c * np.triu(np.ones((m, n)), 1)
    u = np.diag(s ** np.arange(m)) @ u
    u[np.arange(r), np.arange(r)] += pert * EPS * np.arange(r, 0, -1)
    return [u]


def kms(a):
    n = _n(a[0])
    rho = complex(np.asarray(a[1]).reshape(-1)[0]) if len(a) > 1 else 0.5
    i, j = np.indices((n, n))
    k = rho ** np.abs(i - j).astype(float)
    if rho.imag:
        k = np.where(i > j, np.conj(k), k)
    return [k]


def krylov(a):
    x0 = np.asarray(a[0])
    A = _rs().standard_normal((_n(x0), _n(x0))) if x0.size == 1 else np.asarray(x0, dtype=float)
    n = A.shape[0]
    x = _vec(a[1]) if len(a) > 1 and np.asarray(a[1]).size else np.ones(n)
    k = int(_opt(a, 2, n))
    out = np.zeros((n, k), dtype=np.result_type(A, x))
    for c in range(k):
        out[:, c] = x
        x = A @ x
    return [out]


def lauchli(a):
    n, mu = _n(a[0]), _opt(a, 1, math.sqrt(EPS))
    return [np.vstack([np.ones((1, n)), mu * np.eye(n)])]


def lehmer(a):
    n = _n(a[0])
    i, j = np.indices((n, n)) + 1
    return [np.minimum(i, j) / np.maximum(i, j)]


def lesp(a):
    n = _n(a[0])
    return [_tri(n, np.arange(2.0, n + 1), -(2 * np.arange(1.0, n + 1) + 3), 1.0 / np.arange(2.0, n + 1))]


def lotkin(a):
    h = _hilb(_n(a[0]))
    if h.size:
        h[0, :] = 1
    return [h]


def minij(a):
    n = _n(a[0])
    i, j = np.indices((n, n)) + 1
    return [np.minimum(i, j).astype(float)]


def moler(a):
    n, alpha = _n(a[0]), _opt(a, 1, -1.0)
    u = np.eye(n) + alpha * np.triu(np.ones((n, n)), 1)
    return [u.T @ u]


def neumann(a):
    n = _n(a[0])
    m = int(round(math.sqrt(n)))
    if m * m != n:
        raise _err("gallery: neumann: N must be a perfect square.", "MATLAB:gallery:neumann")
    t = _tri(m, -1.0, 2.0, -1.0)
    if m > 1:
        t[0, 1] = t[m - 1, m - 2] = -2.0
    return [np.kron(t, np.eye(m)) + np.kron(np.eye(m), t)]


def orthog(a):
    n, k = _n(a[0]), int(_opt(a, 1, 1))
    i, j = np.indices((n, n)) + 1.0
    if k == 1:
        q = math.sqrt(2 / (n + 1)) * np.sin(i * j * np.pi / (n + 1))
    elif k == 2:
        q = 2 / math.sqrt(2 * n + 1) * np.sin(2 * i * j * np.pi / (2 * n + 1))
    elif k == 3:
        q = np.exp(2j * np.pi * (i - 1) * (j - 1) / n) / math.sqrt(n)
    elif k == 4:  # Helmert
        q = np.tril(np.ones((n, n)), -1) + np.diag(-np.arange(0.0, n))
        q[0] = 1.0
        q = q / np.sqrt((q * q).sum(axis=1, keepdims=True))
    elif k == 5:
        q = (np.sin(2 * np.pi * (i - 1) * (j - 1) / n) + np.cos(2 * np.pi * (i - 1) * (j - 1) / n)) / math.sqrt(n)
    elif k == -1:
        q = np.cos((i - 1) * (j - 1) * np.pi / (n - 1)) if n > 1 else np.ones((n, n))
    elif k == -2:
        q = np.cos((i - 1) * (j - 0.5) * np.pi / n)
    else:
        raise _err(f"gallery: orthog: unknown K = {k}.", "MATLAB:gallery:orthog")
    return [q]


def parter(a):
    n = _n(a[0])
    i, j = np.indices((n, n))
    return [1.0 / (i - j + 0.5)]


def pei(a):
    n, alpha = _n(a[0]), _opt(a, 1, 1.0)
    return [alpha * np.eye(n) + np.ones((n, n))]


def poisson(a):
    n = _n(a[0])
    t = _tri(n, -1.0, 2.0, -1.0)
    return [np.kron(np.eye(n), t) + np.kron(t, np.eye(n))]


def prolate(a):
    n, w = _n(a[0]), _opt(a, 1, 0.25)
    k = np.arange(1.0, n)
    col = np.concatenate([[2 * w], np.sin(2 * np.pi * w * k) / (np.pi * k)])
    i, j = np.indices((n, n))
    return [col[np.abs(i - j)]]


def randhess(a):
    x0 = np.asarray(a[0])
    if x0.size == 1:
        n = _n(x0)
        th = 2 * np.pi * _rs().random_sample(max(n - 1, 0))
    else:
        th = _vec(x0)
        n = th.size
        th = th[: n - 1]
    h = np.eye(n)
    h[n - 1, n - 1] = 1.0
    for i in range(n - 2, -1, -1):  # H <- G(i, i+1) * H
        c, s = math.cos(th[i]), math.sin(th[i])
        r1, r2 = h[i].copy(), h[i + 1].copy()
        h[i], h[i + 1] = c * r1 + s * r2, -s * r1 + c * r2
    return [h]


def rando(a):
    m, n = _mn(a[0])
    k = int(_opt(a, 1, 1))
    u = _rs().random_sample(m * n).reshape((m, n), order="F")
    if k == 1:
        r = np.floor(u + 0.5)
    elif k == 2:
        r = 2 * np.floor(u + 0.5) - 1
    elif k == 3:
        r = np.round(3 * u - 1.5)
    else:
        raise _err("gallery: rando: K must be 1, 2 or 3.", "MATLAB:gallery:rando")
    return [r]


def randsvd(a):
    m, n = _mn(a[0])
    kappa, mode = _opt(a, 1, math.sqrt(1 / EPS)), int(_opt(a, 2, 3))
    p = min(m, n)
    if p == 0:
        return [np.zeros((m, n))]
    am = abs(mode)
    if am == 1:
        s = np.full(p, 1 / kappa)
        s[0] = 1
    elif am == 2:
        s = np.ones(p)
        s[-1] = 1 / kappa
    elif am == 3:
        s = kappa ** (-np.arange(p) / max(p - 1, 1))
    elif am == 4:
        s = 1 - np.arange(p) / max(p - 1, 1) * (1 - 1 / kappa)
    elif am == 5:
        s = np.exp(-_rs().random_sample(p) * math.log(kappa))
    else:
        raise _err("gallery: randsvd: MODE must be one of 1..5 or their negatives.", "MATLAB:gallery:randsvd")
    if mode < 0:
        s = s[::-1]
    d = np.zeros((m, n))
    d[np.arange(p), np.arange(p)] = s
    return [_orth_random(m) @ d @ _orth_random(n).T]


def redheff(a):
    n = _n(a[0])
    i, j = np.indices((n, n)) + 1
    return [((j % i == 0) | (j == 1)).astype(float)]


def riemann(a):
    n = _n(a[0])
    i, j = np.indices((n, n)) + 2
    return [np.where(j % i == 0, i - 1.0, -1.0)]


def ris(a):
    n = _n(a[0])
    i, j = np.indices((n, n)) + 1
    return [0.5 / (n - i - j + 1.5)]


def smoke(a):
    n, k = _n(a[0]), int(_opt(a, 1, 0))
    w = np.exp(2j * np.pi / n) if n else 1
    s = np.diag(w ** np.arange(1, n + 1)) + np.diag(np.ones(max(n - 1, 0)), 1)
    if k == 0 and n:
        s[n - 1, 0] = 1
    return [s]


def toeppd(a):
    n = _n(a[0])
    m = int(_opt(a, 1, n))
    w = _vec(a[2]) if len(a) > 2 else _rs().random_sample(m)
    th = _vec(a[3]) if len(a) > 3 else _rs().random_sample(m)
    i, j = np.indices((n, n))
    d = np.abs(i - j)
    return [sum(w[k] * np.cos(2 * np.pi * th[k] * d) for k in range(m)) if m else np.zeros((n, n))]


def toeppen(a):
    n = _n(a[0])
    coef = [_opt(a, 1, 1.0), _opt(a, 2, -10.0), _opt(a, 3, 0.0), _opt(a, 4, 10.0), _opt(a, 5, 1.0)]
    i, j = np.indices((n, n))
    out = np.zeros((n, n))
    for off, c in zip(range(-2, 3), coef):
        out[j - i == off] = c
    return [out]


def tridiag(a):
    if len(a) == 3:
        x, y, z = _vec(a[0]), _vec(a[1]), _vec(a[2])
        n = y.size
        if x.size != n - 1 or z.size != n - 1:
            raise _err("gallery: tridiag: X and Z must have one element fewer than Y.", "MATLAB:gallery:tridiag")
        return [_tri(n, x, y, z)]
    n = _n(a[0])
    c, d, e = (_opt(a, 1, -1.0), _opt(a, 2, 2.0), _opt(a, 3, -1.0)) if len(a) > 1 else (-1.0, 2.0, -1.0)
    return [_tri(n, c, d, e)]


def triw(a):
    m, n = _mn(a[0])
    alpha, k = _opt(a, 1, -1.0), int(_opt(a, 2, n - 1))
    i, j = np.indices((m, n))
    return [np.where(i == j, 1.0, np.where((j > i) & (j - i <= k), alpha, 0.0))]


def wilk(a):
    n = _n(a[0])
    if n == 3:
        A = np.array([[1e-10, 0.9, -0.4], [0, 0.9, -0.4], [0, 0, 1e-10]])
        return [A, np.array([[0.0], [0.0], [1.0]])]
    if n == 4:
        A = np.array([[0.9143e-4, 0, 0, 0], [0.8762, 0.7156e-4, 0, 0],
                      [0.7943, 0.8143, 0.9504e-4, 0], [0.8017, 0.6123, 0.7165, 0.7123e-4]])
        return [A, np.array([[0.6524], [0.3127], [0.4186], [0.7853]])]
    if n == 5:
        return [_hilb(6)[:5, 1:6] * 1.8144]
    if n == 21:
        return [np.diag(np.abs(np.arange(-10.0, 11))) + np.diag(np.ones(20), 1) + np.diag(np.ones(20), -1)]
    raise _err("gallery: wilk: N must be 3, 4, 5, or 21.", "MATLAB:gallery:wilk")


def _seeded(a, fn, gen):
    shp = tuple(int(v) for v in _vec(a[0]) if True) if np.asarray(a[0]).size > 1 else (_n(a[0]), _n(a[0]))
    if len(a) < 2:
        raise _err(f"gallery: {fn}: a seed J is required.", "MATLAB:minrhs")
    rs = np.random.RandomState(int(_opt(a, 1, 0)) % (2 ** 32))
    return [gen(rs, shp)]


def integerdata(a):
    if len(a) < 3:
        raise _err("gallery: integerdata: IMAX, size and seed J are required.", "MATLAB:minrhs")
    lim = _vec(a[0])
    lo, hi = (1, int(lim[0])) if lim.size == 1 else (int(lim[0]), int(lim[1]))
    return _seeded(a[1:], "integerdata",
                   lambda rs, shp: rs.randint(lo, hi + 1, size=int(np.prod(shp))).reshape(shp, order="F").astype(float))


FAMILIES: Dict[str, Callable[[List[np.ndarray]], list]] = {
    "cauchy": cauchy, "chebspec": chebspec, "chebvand": chebvand, "chow": chow, "circul": circul,
    "clement": clement, "compar": compar, "cycol": cycol, "fiedler": fiedler, "forsythe": forsythe,
    "frank": frank, "gcdmat": gcdmat, "gearmat": gearmat, "grcar": grcar, "hanowa": hanowa, "house": house,
    "invhess": invhess, "invol": invol, "ipjfact": ipjfact, "jordbloc": jordbloc, "kahan": kahan, "kms": kms,
    "krylov": krylov, "lauchli": lauchli, "lehmer": lehmer, "lesp": lesp, "lotkin": lotkin, "minij": minij,
    "moler": moler, "neumann": neumann, "orthog": orthog, "parter": parter, "pei": pei, "poisson": poisson,
    "prolate": prolate, "randhess": randhess, "rando": rando, "randsvd": randsvd, "redheff": redheff,
    "riemann": riemann, "ris": ris, "smoke": smoke, "toeppd": toeppd, "toeppen": toeppen, "tridiag": tridiag,
    "triw": triw, "wilk": wilk, "integerdata": integerdata,
    "uniformdata": lambda a: _seeded(a, "uniformdata", lambda rs, shp: rs.random_sample(shp[::-1]).T
                                      if len(shp) == 2 else rs.random_sample(int(np.prod(shp))).reshape(shp, order="F")),
    "normaldata": lambda a: _seeded(a, "normaldata", lambda rs, shp:
                                     rs.standard_normal(int(np.prod(shp))).reshape(shp, order="F")),
}


def _gallery(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if not _is_text(args[0]):
        raise _err("gallery: NAME must be a string.", "MATLAB:gallery:invalidName")
    name = args[0].text.lower()
    fam = FAMILIES.get(name)
    if fam is None:
        raise _err(f"gallery: unknown matrix with NAME {args[0].text}", "MATLAB:gallery:unknownName")
    rest = [args[i].text if _is_text(args[i]) else _num(args[i], "gallery") for i in range(1, len(args))]
    if not rest:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if any(isinstance(r, str) for r in rest):
        rest = [r for r in rest if not isinstance(r, str)]  # class name ('double'/'single') is accepted, ignored
    outs = fam(rest)
    if nargout > len(outs):
        raise _err("Too many output arguments.", "MATLAB:maxlhs")
    return tuple(_o(o) for o in outs[:max(1, nargout)])


def register(builtins: Dict[str, Callable]) -> None:
    builtins.setdefault("gallery", _gallery)
