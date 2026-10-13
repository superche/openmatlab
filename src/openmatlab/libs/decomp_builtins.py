"""Dense matrix decompositions (Epic #538), NumPy only.

eig svd lu qr chol null orth trace cross dot, plus sqrtm and linsolve.
Shapes, output counts, ordering and error identifiers follow MATLAB.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _is_text(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue)


def _mat(v, fn, square=False):
    if not hasattr(v, "backend_buffer") or _is_text(v):
        raise _err(f"{fn}: input must be a numeric matrix.", f"MATLAB:{fn}:inputType")
    if hasattr(v, "is_sparse") and getattr(v, "is_sparse", False):
        raise _err(f"{fn}: sparse input is not supported; use full().", f"MATLAB:{fn}:sparse")
    b = np.asarray(v.backend_buffer())
    b = b.reshape(1, 1) if b.ndim == 0 else (b.reshape(1, -1) if b.ndim == 1 else b)
    if b.ndim != 2:
        raise _err(f"{fn}: input must be 2-D.", f"MATLAB:{fn}:inputMustBe2D")
    if np.issubdtype(b.dtype, np.integer) or b.dtype == np.bool_:
        raise _err(f"Invalid data type. Input matrix must be double or single.", f"MATLAB:{fn}:integerNotSupported" if fn != "eig" else "MATLAB:eig:integerNotSupported")
    if square and b.shape[0] != b.shape[1]:
        raise _err("Matrix must be square.", "MATLAB:square")
    if not np.all(np.isfinite(b)) and fn in ("eig", "svd", "chol", "null", "orth", "sqrtm"):
        raise _err("Input to " + fn.upper() + " must not contain NaN or Inf.", f"MATLAB:{fn}:matrixWithNaNInf")
    return b.astype(np.complex128 if np.iscomplexobj(b) else np.float64)


def _out(a):
    a = np.asarray(a)
    if np.iscomplexobj(a) and np.all(a.imag == 0):
        a = a.real
    return NDArrayValue(np.ascontiguousarray(a))


def _flags(args):
    return [a.text.lower() for a in args if _is_text(a)]


def _is_hermitian(a):
    return a.shape[0] == a.shape[1] and np.allclose(a, a.conj().T, rtol=0, atol=0)


# ------------------------------------------------------------------ eig
def _eig(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    a = _mat(args[0], "eig", square=True)
    nums = [x for x in args[1:] if not _is_text(x)]
    flags = _flags(args[1:])
    if nums:
        b = _mat(nums[0], "eig", square=True)
        if b.shape != a.shape:
            raise _err("Inputs must be the same size.", "MATLAB:eig:sizeMismatch")
        try:
            a = np.linalg.solve(b, a)
        except np.linalg.LinAlgError:
            raise _err("eig(A,B): B is singular; the QZ algorithm is not supported.", "MATLAB:eig:singularB") from None
    if a.size == 0:
        z = np.zeros((0, 1))
        return (_out(z), _out(np.zeros((0, 0))), _out(np.zeros((0, 0))))[: max(nargout, 1)]
    if not nums and _is_hermitian(a):
        w, v = np.linalg.eigh(a)  # ascending, real (MATLAB)
    else:
        w, v = np.linalg.eig(a)
    w_out = w.reshape(-1, 1)
    if "vector" in flags and nargout > 1:
        d = w_out
    else:
        d = np.diag(w)
    if nargout <= 1:
        return (_out(w_out),)
    v = v / np.linalg.norm(v, axis=0, keepdims=True)
    if nargout == 2:
        return (_out(v), _out(d))
    wl, vl = np.linalg.eig(a.conj().T)
    # match left vectors to the eigenvalue order of w
    order = [int(np.argmin(np.abs(wl.conj() - x))) for x in w]
    W = vl[:, order]
    W = W / np.linalg.norm(W, axis=0, keepdims=True)
    return (_out(v), _out(d), _out(W))


# ------------------------------------------------------------------ svd
def _svd(args, *, nargout=1):
    a = _mat(args[0], "svd")
    flags = _flags(args[1:])
    econ = "econ" in flags or any(not _is_text(x) and np.asarray(x.backend_buffer()).size == 1 and float(np.asarray(x.backend_buffer()).reshape(-1)[0]) == 0 for x in args[1:])
    m, n = a.shape
    if nargout <= 1:
        s = np.linalg.svd(a, compute_uv=False) if a.size else np.zeros(0)
        return (_out(s.reshape(-1, 1)),)
    if a.size == 0:
        return (_out(np.eye(m)), _out(np.zeros((m, n))), _out(np.eye(n)))
    u, s, vh = np.linalg.svd(a, full_matrices=not econ)
    if econ:
        S = np.diag(s)
    else:
        S = np.zeros((m, n))
        S[: s.size, : s.size] = np.diag(s)
    if "vector" in flags:
        S = s.reshape(-1, 1)
    return (_out(u), _out(S), _out(vh.conj().T))


# ------------------------------------------------------------------ lu
def _lu_factor(a):
    m, n = a.shape
    U = a.copy()
    L = np.eye(m, dtype=a.dtype)
    perm = np.arange(m)
    k_max = min(m, n)
    for k in range(k_max):
        p = k + int(np.argmax(np.abs(U[k:, k])))
        if p != k:
            U[[k, p], :] = U[[p, k], :]
            L[[k, p], :k] = L[[p, k], :k]
            perm[[k, p]] = perm[[p, k]]
        if U[k, k] != 0:
            f = U[k + 1:, k] / U[k, k]
            L[k + 1:, k] = f
            U[k + 1:, :] -= np.outer(f, U[k, :])
    L = L[:, :k_max]
    U = np.triu(U[:k_max, :])
    return L, U, perm


def _lu(args, *, nargout=1):
    a = _mat(args[0], "lu")
    vector = "vector" in _flags(args[1:])
    m, n = a.shape
    L, U, perm = _lu_factor(a)
    P = np.eye(m)[perm, :]
    if nargout <= 1:
        k = min(m, n)
        Y = np.triu(U) if m <= n else np.vstack([U, np.zeros((m - k, n))])
        Lfull = np.zeros((m, n))
        Lfull[:, :k] = L
        return (_out(np.triu(np.vstack([U, np.zeros((m - U.shape[0], n))])) + np.tril(Lfull, -1)),)
    if nargout == 2:
        return (_out(P.T @ L), _out(U))
    return (_out(L), _out(U), _out((perm + 1.0).reshape(1, -1) if vector else P))


# ------------------------------------------------------------------ qr
def _qr(args, *, nargout=1):
    a = _mat(args[0], "qr")
    flags = _flags(args[1:])
    econ = "econ" in flags or any(not _is_text(x) and float(np.asarray(x.backend_buffer()).reshape(-1)[0]) == 0 for x in args[1:])
    m, n = a.shape
    if nargout == 3:
        # column pivoting: greedy by remaining column norm (Businger-Golub)
        A = a.copy()
        perm = np.arange(n)
        for k in range(min(m, n)):
            norms = np.linalg.norm(A[k:, k:], axis=0)
            j = k + int(np.argmax(norms))
            A[:, [k, j]] = A[:, [j, k]]
            perm[[k, j]] = perm[[j, k]]
            q, r = np.linalg.qr(A[k:, k:], mode="complete")
            A[k:, k:] = r
            if k == 0:
                Qacc = q
            else:
                Qacc[:, k:] = Qacc[:, k:] @ q
        if min(m, n) == 0:
            Qacc = np.eye(m)
        Q, R = Qacc, np.triu(A)
        if econ:
            Q, R = Q[:, : min(m, n)], R[: min(m, n), :]
        E = (perm + 1.0).reshape(1, -1) if econ or "vector" in flags else np.eye(n)[:, perm]
        return (_out(Q), _out(R), _out(E))
    q, r = np.linalg.qr(a, mode="reduced" if econ else "complete")
    if nargout <= 1:
        return (_out(np.triu(r)),)
    return (_out(q), _out(r))


# ------------------------------------------------------------------ chol
def _chol(args, *, nargout=1):
    a = _mat(args[0], "chol", square=True)
    lower = "lower" in _flags(args[1:])
    n = a.shape[0]
    # Cholesky of the upper triangle (MATLAB uses only triu(A)) with failure column p
    au = np.triu(a) + np.triu(a, 1).conj().T
    R = np.zeros_like(au)
    p = 0
    for j in range(n):
        s = au[j, j] - np.vdot(R[:j, j], R[:j, j])
        if np.iscomplexobj(s):
            s = s.real
        if not s > 0:
            p = j + 1
            break
        R[j, j] = np.sqrt(s)
        if j + 1 < n:
            R[j, j + 1:] = (au[j, j + 1:] - R[:j, j].conj() @ R[:j, j + 1:]) / R[j, j]
    if p:
        if nargout < 2:
            raise _err("Matrix must be positive definite.", "MATLAB:posdef")
        R = R[: p - 1, : p - 1]
    out = R.conj().T if lower else R
    if nargout >= 2:
        return (_out(out), _out(np.array([[float(p)]])))
    return (_out(out),)


# ------------------------------------------------------------------ subspaces
def _tol(s, shape):
    return max(shape) * np.spacing(s.max()) if s.size else 0.0


def _null(args, *, nargout=1):
    a = _mat(args[0], "null")
    m, n = a.shape
    if a.size == 0:
        return (_out(np.eye(n)),)
    u, s, vh = np.linalg.svd(a)
    tol = float(np.asarray(args[1].backend_buffer()).reshape(-1)[0]) if len(args) > 1 and not _is_text(args[1]) else _tol(s, a.shape)
    r = int(np.sum(s > tol))
    return (_out(vh[r:, :].conj().T),)


def _orth(args, *, nargout=1):
    a = _mat(args[0], "orth")
    if a.size == 0:
        return (_out(np.zeros((a.shape[0], 0))),)
    u, s, vh = np.linalg.svd(a)
    tol = float(np.asarray(args[1].backend_buffer()).reshape(-1)[0]) if len(args) > 1 else _tol(s, a.shape)
    r = int(np.sum(s > tol))
    return (_out(u[:, :r]),)


def _trace(args, *, nargout=1):
    a = _mat(args[0], "trace")
    if a.shape[0] != a.shape[1]:
        raise _err("Matrix must be square.", "MATLAB:square")
    return (_out(np.array([[np.trace(a)]])),)


def _cross(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    a, b = _mat(args[0], "cross"), _mat(args[1], "cross")
    if a.shape != b.shape:
        raise _err("A and B must be of the same size.", "MATLAB:cross:InputSizeMismatch")
    if len(args) > 2:
        dim = int(np.asarray(args[2].backend_buffer()).reshape(-1)[0]) - 1
    else:
        dims = [d for d, k in enumerate(a.shape) if k == 3]
        if not dims:
            raise _err("A and B must have at least one dimension of length 3.", "MATLAB:cross:InvalidDimAorB")
        dim = dims[0]
    if a.shape[dim] != 3:
        raise _err("A and B must be of length 3 in the dimension in which the cross product is taken.", "MATLAB:cross:InvalidDimAorBForCrossProd")
    return (_out(np.cross(a, b, axis=dim)),)


def _dot(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    a, b = _mat(args[0], "dot"), _mat(args[1], "dot")
    if 1 in a.shape and 1 in b.shape and a.size == b.size and len(args) == 2:
        return (_out(np.array([[np.vdot(a.reshape(-1), b.reshape(-1))]])),)
    if a.shape != b.shape:
        raise _err("A and B must be same size.", "MATLAB:dot:InputSizeMismatch")
    dim = int(np.asarray(args[2].backend_buffer()).reshape(-1)[0]) - 1 if len(args) > 2 else (0 if a.shape[0] != 1 else 1)
    r = np.sum(a.conj() * b, axis=dim, keepdims=True)
    return (_out(r),)


def _sqrtm(args, *, nargout=1):
    a = _mat(args[0], "sqrtm", square=True)
    if _is_hermitian(a):
        w, v = np.linalg.eigh(a)
        w = w.astype(complex)
        r = (v * np.sqrt(w)) @ v.conj().T
    else:
        w, v = np.linalg.eig(a)
        r = v @ np.diag(np.sqrt(w.astype(complex))) @ np.linalg.inv(v)
    if np.allclose(r.imag, 0, atol=1e-12 * max(1.0, np.abs(r).max())):
        r = r.real
    return (_out(r),)


def register(builtins: Dict[str, Callable]) -> None:
    table = {"eig": _eig, "svd": _svd, "lu": _lu, "qr": _qr, "chol": _chol, "null": _null,
             "orth": _orth, "trace": _trace, "cross": _cross, "dot": _dot, "sqrtm": _sqrtm}
    for k, v in table.items():
        builtins.setdefault(k, v)
