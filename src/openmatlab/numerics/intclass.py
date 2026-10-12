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
