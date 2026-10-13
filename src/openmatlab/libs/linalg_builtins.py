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
    n = a.shape[0]
    if n == 0:
        return (_out(a),)
    x, singular = la._lu_solve(a, np.eye(n, dtype=a.dtype))
    if singular:
        mw.emit("Matrix is singular to working precision.")
        return (_out(np.full((n, n), np.inf)),)  # MATLAB inv of a singular matrix is all Inf
    rc = la.rcond(a)
    if rc < la.EPS:
        mw.emit(f"Matrix is close to singular or badly scaled. Results may be inaccurate. RCOND = {rc:e}.")
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


def _warning(args, *, nargout=1):
    from openmatlab.libs.text_builtins import _flat_args, _format
    from openmatlab.libs.string_builtins import _scalar_text

    if not args:
        raise _err("warning: not enough input arguments")
    first = _scalar_text("warning", args[0], "message")
    if first.lower() in ("off", "on") and (len(args) == 1 or _scalar_text("warning", args[1], "id").lower() == "all"):
        mw.set_enabled(first.lower() == "on")
        return ()
    if first.lower() in ("off", "on"):
        return ()  # per-identifier control is a non-goal; accepted silently
    mw.emit(_format(first, _flat_args(args[1:])) if len(args) > 1 else first)
    return ()


def _lastwarn(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.libs.string_builtins import _scalar_text

    prev = mw.last()
    if args:
        mw.set_last(_scalar_text("lastwarn", args[0], "message"))
    return (CharValue(prev),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        mldivide=_mldivide, mrdivide=_mrdivide, inv=_inv, det=_det, rank=_rank, pinv=_pinv,
        warning=_warning, lastwarn=_lastwarn,
    )
