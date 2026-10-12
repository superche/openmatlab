"""MATLAB integer classes int8…uint64 (Epic #457, #72).

Integers are NDArrayValue buffers with a NumPy integer dtype. Arithmetic is
computed in double, then rounded half away from zero and saturated to the
class range (NaN → 0), as in MATLAB.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

INT_CLASSES = {
    "int8": np.int8, "uint8": np.uint8, "int16": np.int16, "uint16": np.uint16,
    "int32": np.int32, "uint32": np.uint32, "int64": np.int64, "uint64": np.uint64,
}

MIX_ERR = "Integers can only be combined with integers of the same class, or scalar doubles."


class IntClassError(ValueError):
    pass


def is_int(buf) -> bool:
    return np.issubdtype(np.asarray(buf).dtype, np.integer)


def class_name(dtype) -> Optional[str]:
    dt = np.dtype(dtype)
    for name, t in INT_CLASSES.items():
        if np.dtype(t) == dt:
            return name
    return None


def saturate(vals, dtype) -> np.ndarray:
    """Round half away from zero, NaN → 0, clip to the class range."""
    v = np.asarray(vals)
    if np.iscomplexobj(v):
        raise IntClassError("Complex values cannot be converted to integer classes.")
    if is_int(v):
        v = v.astype(np.float64) if np.dtype(v.dtype) != np.dtype(dtype) else v
        if np.dtype(v.dtype) == np.dtype(dtype):
            return v.copy()
    v = np.asarray(v, dtype=np.float64)
    info = np.iinfo(dtype)
    with np.errstate(invalid="ignore"):
        r = np.sign(v) * np.floor(np.abs(v) + 0.5)
        r = np.where(np.isnan(r), 0.0, r)
        r = np.clip(r, float(info.min), float(info.max))
    with np.errstate(invalid="ignore"):
        out = r.astype(dtype)
    # float(info.max) for int64/uint64 rounds up to 2^63 / 2^64; pin the edges
    out = np.where(r >= float(info.max), info.max, out).astype(dtype)
    return out


def result_dtype(*bufs):
    """Integer class of a mixed operation, or None if no integer operand."""
    ints = []
    for b in bufs:
        b = np.asarray(b)
        if is_int(b):
            ints.append(np.dtype(b.dtype))
    if not ints:
        return None
    if len(set(ints)) > 1:
        raise IntClassError(MIX_ERR)
    if any(np.iscomplexobj(np.asarray(b)) for b in bufs):
        raise IntClassError("Complex integer arithmetic is not supported.")
    return ints[0]


def _as_pyint(buf):
    """Object array of Python ints, or None if a value is not integer-valued."""
    b = np.asarray(buf)
    if b.dtype == np.bool_ or is_int(b):
        return b.astype(object)
    if np.iscomplexobj(b) or not np.all(np.isfinite(b)) or np.any(b != np.floor(b)):
        return None
    return np.vectorize(int, otypes=[object])(b) if b.size else b.astype(object)


def _div_round(n: int, d: int, info) -> int:
    if d == 0:
        return 0 if n == 0 else (info.max if n > 0 else info.min)
    q, r = divmod(abs(n), abs(d))
    q += 2 * r >= abs(d)  # round half away from zero
    return q if (n >= 0) == (d > 0) else -q


def exact_wide(op: str, x, y, dtype):
    """Exact int64/uint64 add/subtract/multiply/divide via Python ints (#463).

    Returns None when an operand is not integer-valued (falls back to double).
    """
    if np.dtype(dtype) not in (np.dtype(np.int64), np.dtype(np.uint64)):
        return None
    px, py = _as_pyint(x), _as_pyint(y)
    if px is None or py is None:
        return None
    info = np.iinfo(dtype)
    px, py = np.broadcast_arrays(px, py)
    if op == "add":
        r = px + py
    elif op == "subtract":
        r = px - py
    elif op == "multiply":
        r = px * py
    elif op == "true_divide":
        r = np.frompyfunc(lambda n, d: _div_round(int(n), int(d), info), 2, 1)(px, py)
    else:
        return None
    r = np.asarray(r, dtype=object)
    clip = np.frompyfunc(lambda v: min(max(int(v), int(info.min)), int(info.max)), 1, 1)
    return np.asarray(clip(r) if r.size else r, dtype=object).astype(dtype)
