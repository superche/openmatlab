"""mldivide/mrdivide/inv/det/rank/pinv and warning/lastwarn (Epic #496)."""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics import linalg as la
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime import warnings as mw
from openmatlab.runtime.value import Array, Value


def _err(msg: str):
    from openmatlab.libs.numeric_builtins import BuiltinError

    return BuiltinError(msg)


def _mat(name: str, v: Value, *, square: bool = False) -> np.ndarray:
    if not isinstance(v, Array):
        raise _err(f"{name}: input must be numeric")
    b = np.asarray(v.backend_buffer())
    if np.issubdtype(b.dtype, np.integer):
        raise _err(f"{name}: integer matrices are not supported; convert with double() first")
    b = b.reshape(1, 1) if b.ndim == 0 else b
    if b.ndim > 2:
        raise _err(f"{name}: input must be 2-D")
    if square and b.shape[0] != b.shape[1]:
        raise _err("Matrix must be square.")
    return la._f(b)


def _out(x) -> NDArrayValue:
    x = np.asarray(x)
    if np.iscomplexobj(x) and not np.any(x.imag):
        x = x.real.copy()
    return NDArrayValue(x.reshape(1, 1) if x.ndim == 0 else x)


def solve(kind: str, a: Value, b: Value) -> NDArrayValue:
    """Shared by the operators and the mldivide/mrdivide builtins."""
    for v in (a, b):
        if isinstance(v, Array) and np.issubdtype(np.asarray(v.backend_buffer()).dtype, np.integer) \
                and v.numel() != 1:
            raise _err("Integer data types are not supported for matrix division; at least one input must be scalar.")
    try:
        fa, fb = np.asarray(a.backend_buffer()), np.asarray(b.backend_buffer())
        x = la.mldivide(fa, fb) if kind == "mldivide" else la.mrdivide(fa, fb)
    except la.LinalgError as exc:
        raise _err(str(exc)) from None
    out = _out(x)
    if getattr(a, "issparse", False) and getattr(b, "issparse", False):
        from openmatlab.numerics.sparse import to_sparse

        return to_sparse(out.backend_buffer())  # S\\S and S/S are sparse (#488)
    if any(isinstance(v, Array) and np.asarray(v.backend_buffer()).dtype in (np.float32, np.complex64) for v in (a, b)):
        buf = np.asarray(out.backend_buffer())
        out = NDArrayValue(buf.astype(np.complex64 if np.iscomplexobj(buf) else np.float32))
    return out


def _mldivide(args, *, nargout=1):
    if len(args) != 2:
        raise _err("mldivide: requires two inputs")
    return (solve("mldivide", *args),)


def _mrdivide(args, *, nargout=1):
    if len(args) != 2:
        raise _err("mrdivide: requires two inputs")
    return (solve("mrdivide", *args),)


def _inv(args, *, nargout=1):
    if len(args) != 1:
        raise _err("inv: expected 1 argument")
    a = _mat("inv", args[0], square=True)
    if getattr(args[0], "issparse", False):  # inv(S) is sparse (#488)
        from openmatlab.numerics.sparse import to_sparse

        args = list(args)
        r = _inv([NDArrayValue(a)], nargout=nargout)[0]
        return (to_sparse(r.backend_buffer()),)
    n = a.shape[0]
    if n == 0:
        return (_out(a),)
    x, singular = la._lu_solve(a, np.eye(n, dtype=a.dtype))
    if singular:
        mw.emit("Matrix is singular to working precision.", "MATLAB:singularMatrix")
        return (_out(np.full((n, n), np.inf)),)  # MATLAB inv of a singular matrix is all Inf
    rc = la.rcond(a)
    if rc < la.EPS:
        mw.emit(f"Matrix is close to singular or badly scaled. Results may be inaccurate. RCOND = {rc:e}.", "MATLAB:nearlySingularMatrix")
    return (_out(x),)


def _det(args, *, nargout=1):
    if len(args) != 1:
        raise _err("det: expected 1 argument")
    a = _mat("det", args[0], square=True)
    return (_out(np.array([[np.linalg.det(a) if a.size else 1.0]])),)


def _sv_tol(name, a, args):
    s = np.linalg.svd(a, compute_uv=False) if a.size else np.zeros(0)
    if len(args) == 2:
        tol = float(np.asarray(args[1].backend_buffer()).reshape(-1)[0])
    else:
        tol = max(a.shape) * (np.spacing(s.max()) if s.size else 0.0)
    return s, tol


def _rank(args, *, nargout=1):
    if len(args) not in (1, 2):
        raise _err("rank: usage rank(A[, tol])")
    a = _mat("rank", args[0])
    s, tol = _sv_tol("rank", a, args)
    return (_out(np.array([[float(np.sum(s > tol))]])),)


def _pinv(args, *, nargout=1):
    if len(args) not in (1, 2):
        raise _err("pinv: usage pinv(A[, tol])")
    a = _mat("pinv", args[0])
    if not a.size:
        return (_out(np.zeros((a.shape[1], a.shape[0]))),)
    u, s, vh = np.linalg.svd(a, full_matrices=False)
    _, tol = _sv_tol("pinv", a, args)
    sinv = np.where(s > tol, 1.0 / np.where(s > tol, s, 1.0), 0.0)
    return (_out((vh.conj().T * sinv) @ u.conj().T),)


_ID = __import__("re").compile(r"^[A-Za-z][\w-]*(:[\w-]+)+$")


def _warning(args, *, nargout=1):
    from openmatlab.libs.text_builtins import _flat_args, _format
    from openmatlab.libs.string_builtins import _scalar_text

    if not args:
        raise _err("warning: not enough input arguments")
    first = _scalar_text("warning", args[0], "message")
    state = first.lower()
    if state in ("off", "on", "query") and len(args) <= 2:
        target = _scalar_text("warning", args[1], "id") if len(args) == 2 else "all"
        if state == "query":
            from openmatlab.runtime.char_value import CharValue

            return (CharValue("on" if (mw.is_on(target) if target != "all" else mw.is_on("")) else "off"),)
        if target.lower() == "all":
            mw.set_enabled(state == "on")
        else:
            mw.set_id(target, state == "on")
        return ()
    ident = ""
    if len(args) > 1 and _ID.match(first):  # warning(id, fmt, ...) (#498)
        ident, args = first, args[1:]
        first = _scalar_text("warning", args[0], "message")
    mw.emit(_format(first, _flat_args(args[1:])) if len(args) > 1 or ident else first, ident)
    return ()


def _lastwarn(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.libs.string_builtins import _scalar_text

    prev, prev_id = mw.last(), mw.last_id()
    if args:
        mw.set_last(_scalar_text("lastwarn", args[0], "message"),
                    _scalar_text("lastwarn", args[1], "id") if len(args) > 1 else "")
    return (CharValue(prev), CharValue(prev_id)) if nargout > 1 else (CharValue(prev),)


def _magic(args, *, nargout=1):
    if len(args) != 1:
        raise _err("magic: expected 1 argument")
    n = int(np.asarray(args[0].backend_buffer()).reshape(-1)[0].real)
    return (_out(magic_square(n)),)


def magic_square(n: int) -> np.ndarray:
    """MATLAB's magic(n) construction (odd: siamese; 4k: complement pattern; 4k+2: LUX quadrants)."""
    if n < 1:
        return np.zeros((0, 0))
    if n == 1:
        return np.array([[1.0]])
    if n == 2:
        return np.array([[4.0, 3.0], [1.0, 2.0]])
    if n % 2 == 1:
        j, i = np.meshgrid(np.arange(1, n + 1), np.arange(1, n + 1))
        a = np.mod(i + j - (n + 3) // 2, n)
        b = np.mod(i + 2 * j - 2, n)
        return (n * a + b + 1).astype(float)
    if n % 4 == 0:
        j, i = np.meshgrid(np.arange(1, n + 1), np.arange(1, n + 1))
        k = np.fix(np.mod(i, 4) / 2) == np.fix(np.mod(j, 4) / 2)
        m = np.arange(1, n * n + 1, dtype=float).reshape(n, n)  # row-major 1..n^2
        m[k] = n * n + 1 - m[k]
        return m
    p = n // 2
    a = magic_square(p)
    m = np.block([[a, a + 2 * p * p], [a + 3 * p * p, a + p * p]])
    k = (n - 2) // 4
    cols = list(range(k)) + list(range(n - k + 1, n))
    for c in cols:
        m[[*range(p), *range(p, n)], c] = m[[*range(p, n), *range(p)], c]
    for c in (0, k):
        m[[k, k + p], c] = m[[k + p, k], c]
    return m


def _norm(args, *, nargout=1):
    if len(args) not in (1, 2):
        raise _err("norm: usage norm(X[, p])")
    a = _mat("norm", args[0])
    p = 2.0
    if len(args) == 2:
        from openmatlab.runtime.char_value import CharValue

        if isinstance(args[1], CharValue):
            if args[1].text.lower() not in ("fro", "inf"):
                raise _err("norm: the only matrix norms available are 1, 2, inf, and 'fro'.")
            p = "fro" if args[1].text.lower() == "fro" else np.inf
        else:
            p = float(np.asarray(args[1].backend_buffer()).reshape(-1)[0].real)
    if a.size == 0:
        return (_out(np.array([[0.0]])),)
    vec = 1 in a.shape
    v = a.reshape(-1)
    if vec:
        if p == "fro":
            r = np.sqrt(np.sum(np.abs(v) ** 2))
        elif p == np.inf:
            r = np.max(np.abs(v))
        elif p == -np.inf:
            r = np.min(np.abs(v))
        else:
            r = np.sum(np.abs(v) ** p) ** (1.0 / p)
    else:
        if p == "fro":
            r = np.linalg.norm(a, "fro")
        elif p in (1.0, 2.0, np.inf):
            r = np.linalg.norm(a, {1.0: 1, 2.0: 2, np.inf: np.inf}[p])
        else:
            raise _err("norm: the only matrix norms available are 1, 2, inf, and 'fro'.")
    return (_out(np.array([[float(r)]])),)


def _cond(args, *, nargout=1):
    if len(args) not in (1, 2):
        raise _err("cond: usage cond(A[, p])")
    a = _mat("cond", args[0])
    if len(args) == 1 or float(np.asarray(args[1].backend_buffer()).reshape(-1)[0].real) == 2 \
            if not hasattr(args[1] if len(args) == 2 else None, "text") else False:
        if a.size == 0:
            return (_out(np.array([[0.0]])),)
        s = np.linalg.svd(a, compute_uv=False)
        r = np.inf if s[-1] == 0 else s[0] / s[-1]
        return (_out(np.array([[float(r)]])),)
    if a.shape[0] != a.shape[1]:
        raise _err("cond: A must be square for p ~= 2.")
    try:
        inv = np.linalg.inv(a)
    except np.linalg.LinAlgError:
        return (_out(np.array([[np.inf]])),)
    na = _norm([NDArrayValue(a), args[1]])[0].backend_buffer().item()
    ni = _norm([NDArrayValue(inv), args[1]])[0].backend_buffer().item()
    return (_out(np.array([[na * ni]])),)


def _rcond(args, *, nargout=1):
    if len(args) != 1:
        raise _err("rcond: expected 1 argument")
    a = _mat("rcond", args[0], square=True)
    if a.size == 0:
        return (_out(np.array([[np.inf]])),)
    return (_out(np.array([[la.rcond(a)]])),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        mldivide=_mldivide, mrdivide=_mrdivide, inv=_inv, det=_det, rank=_rank, pinv=_pinv,
        warning=_warning, lastwarn=_lastwarn, magic=_magic, norm=_norm, cond=_cond, rcond=_rcond,
    )
