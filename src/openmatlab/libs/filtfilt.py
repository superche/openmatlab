"""Zero-phase ``filtfilt`` and a thin Butterworth ``bandpass`` (M15 B-E2, #1009).

Clean-room, from the public filter formulas. Not a copy of GPL Octave Forge.

``filtfilt`` is Gustafsson's steady-state initial condition: odd reflection of
``3*(nfilt-1)`` samples, then forward and reverse ``filter``. Vectors keep
their orientation. Matrices are filtered down the columns.

``butter`` keeps the lowpass and highpass cases (analog poles, prewarp
``tan(pi*Wn/2)``, bilinear map) and adds the two-edge bandpass: order ``2n``,
zeros split between ``z = +1`` and ``z = -1``, gain 1 at the prewarped
geometric center. ``bandpass(x,[f1 f2],fs)`` is that design at order 2,
applied with ``filtfilt``. It is not a ``designfilt`` object.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg: str, ident: str = ""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _matlab2d(v, name: str) -> np.ndarray:
    if not hasattr(v, "backend_buffer"):
        raise _err(f"{name}: expected a numeric argument", "MATLAB:invalidType")
    a = np.asarray(v.backend_buffer())
    if np.iscomplexobj(a):
        raise _err(f"{name}: complex data is not supported.", f"signal:{name}:complex")
    if a.dtype == bool:
        a = a.astype(np.float64)
    else:
        a = np.asarray(a, dtype=np.float64)
    if a.ndim == 0:
        return a.reshape(1, 1)
    if a.ndim == 1:
        return a.reshape(1, -1)
    if a.ndim != 2:
        raise _err(f"{name}: N-D arrays are not supported.", f"signal:{name}:invalidDimensions")
    return a


def _text(v) -> str | None:
    t = getattr(v, "text", None)
    return t if isinstance(t, str) else None


def _out(a: np.ndarray) -> NDArrayValue:
    a = np.asarray(a, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    return NDArrayValue(a)


def _normalize(b: np.ndarray, a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    if a.size == 0 or a[0] == 0:
        raise _err(
            "First denominator filter coefficient must be non-zero.",
            "signal:filtfilt:invalidA",
        )
    b = b / a[0]
    a = a / a[0]
    nf = max(int(b.size), int(a.size))
    if b.size < nf:
        b = np.pad(b, (0, nf - b.size))
    if a.size < nf:
        a = np.pad(a, (0, nf - a.size))
    return b, a


def _steady_zi(b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Gustafsson IC: ``zi = (I - A) \\ (b[1:] - b[0]*a[1:])``."""
    n = b.size - 1
    if n <= 0:
        return np.zeros(0, dtype=np.float64)
    comp = np.zeros((n, n), dtype=np.float64)
    comp[:, 0] = -a[1:]
    if n > 1:
        comp[:-1, 1:] = np.eye(n - 1)
    rhs = b[1:] - b[0] * a[1:]
    return np.linalg.solve(np.eye(n) - comp, rhs)


def _df2t(b: np.ndarray, a: np.ndarray, x: np.ndarray, zi: np.ndarray) -> np.ndarray:
    """Direct-form II transposed, the same recurrence as ``filter``."""
    n = b.size
    y = np.empty(x.shape[0], dtype=np.float64)
    z = np.zeros(n, dtype=np.float64)
    if zi.size:
        z[: zi.size] = zi
    b0 = b[0]
    for k in range(x.shape[0]):
        xk = x[k]
        yk = b0 * xk + z[0]
        y[k] = yk
        for j in range(1, n):
            z[j - 1] = b[j] * xk + z[j] - a[j] * yk
    return y


def _extend(x: np.ndarray, nfact: int) -> np.ndarray:
    if nfact == 0:
        return x
    left = 2.0 * x[0] - x[nfact:0:-1]
    right = 2.0 * x[-1] - x[-2 : -(nfact + 2) : -1]
    return np.concatenate((left, x, right))


def filtfilt_array(b: np.ndarray, a: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Zero-phase filter. ``x`` is 2-D; a 1-by-N row is restored."""
    b, a = _normalize(b, a)
    nfact = 3 * (b.size - 1)
    row = x.shape[0] == 1
    work = x.reshape(-1, 1) if row else x
    if work.shape[0] <= nfact:
        raise _err(
            "Data must have length more than 3 times filter order.",
            "signal:filtfilt:InvalidDimensions",
        )
    zi = _steady_zi(b, a)
    cols = []
    for c in range(work.shape[1]):
        xc = np.ascontiguousarray(work[:, c])
        ext = _extend(xc, nfact)
        v = _df2t(b, a, ext, zi * ext[0])
        v = _df2t(b, a, v[::-1], zi * v[-1])
        v = v[::-1]
        cols.append(v[nfact : v.size - nfact] if nfact else v)
    y = np.column_stack(cols)
    return y.reshape(1, -1) if row else y


def butter_ba(n: int, wn: np.ndarray, ftype: str) -> tuple[np.ndarray, np.ndarray]:
    """Digital Butterworth numerator and denominator, each a 1-D real vector."""
    wn = np.asarray(wn, dtype=np.float64).reshape(-1)
    ftype = ftype.lower()
    if ftype not in ("low", "high", "bandpass"):
        raise _err("Filter type must be 'low', 'high', or 'bandpass'.", "signal:butter:invalidType")
    if n < 1:
        raise _err("Filter order must be a positive integer.", "signal:butter:invalidOrder")
    k = np.arange(1, n + 1)
    proto = np.exp(1j * np.pi * (2 * k + n - 1) / (2 * n))
    if ftype in ("low", "high"):
        if wn.size != 1 or not (0.0 < wn[0] < 1.0):
            raise _err(
                "The cutoff frequency Wn must be a scalar with 0 < Wn < 1.",
                "signal:butter:invalidCutoff",
            )
        omega = np.tan(np.pi * wn[0] / 2.0)
        if ftype == "low":
            s = omega * proto
            zeros = -np.ones(n)
            zref = 1.0
        else:
            s = omega / proto
            zeros = np.ones(n)
            zref = -1.0
        poles = (1.0 + s) / (1.0 - s)
        a = np.real(np.poly(poles))
        b = np.real(np.poly(zeros))
        b = b * (np.polyval(a, zref) / np.polyval(b, zref))
        return b, a
    if wn.size != 2 or not (0.0 < wn[0] < wn[1] < 1.0):
        raise _err(
            "Bandpass Wn must be a two-element vector with 0 < Wn1 < Wn2 < 1.",
            "signal:butter:invalidCutoff",
        )
    w1 = np.tan(np.pi * float(wn[0]) / 2.0)
    w2 = np.tan(np.pi * float(wn[1]) / 2.0)
    bw = w2 - w1
    w0sq = w1 * w2
    poles_s = []
    for pk in proto:
        disc = np.sqrt((pk * bw) ** 2 - 4.0 * w0sq)
        poles_s.append(0.5 * (pk * bw + disc))
        poles_s.append(0.5 * (pk * bw - disc))
    s = np.asarray(poles_s)
    poles = (1.0 + s) / (1.0 - s)
    zeros = np.concatenate((np.ones(n), -np.ones(n)))
    a = np.real(np.poly(poles))
    b = np.real(np.poly(zeros))
    a = a / a[0]
    wc = 2.0 * np.arctan(np.sqrt(w0sq))
    h = np.polyval(b, np.exp(1j * wc)) / np.polyval(a, np.exp(1j * wc))
    b = np.real(b / h)
    return b, a


def _butter(args, *, nargout=1):
    if not 2 <= len(args) <= 3:
        raise _err("Not enough input arguments." if len(args) < 2 else "Too many input arguments.", "signal:butter:nargin")
    n_arr = _matlab2d(args[0], "butter").reshape(-1)
    if n_arr.size != 1 or n_arr[0] != np.floor(n_arr[0]) or n_arr[0] < 1:
        raise _err("Filter order must be a positive integer.", "signal:butter:invalidOrder")
    wn = _matlab2d(args[1], "butter").reshape(-1)
    if len(args) == 3:
        label = _text(args[2])
        if label is None:
            raise _err("Filter type must be 'low', 'high', or 'bandpass'.", "signal:butter:invalidType")
        ftype = label
    else:
        ftype = "bandpass" if wn.size == 2 else "low"
    b, a = butter_ba(int(n_arr[0]), wn, ftype)
    pair = (_out(b), _out(a))
    return pair if nargout > 1 else pair[:1]


def _filtfilt(args, *, nargout=1):
    if len(args) < 3:
        raise _err("Not enough input arguments.", "signal:filtfilt:notEnoughInputs")
    if len(args) > 3:
        raise _err("Too many input arguments.", "signal:filtfilt:tooManyInputs")
    b = _matlab2d(args[0], "filtfilt")
    a = _matlab2d(args[1], "filtfilt")
    x = _matlab2d(args[2], "filtfilt")
    return (_out(filtfilt_array(b, a, x)),)


def _bandpass(args, *, nargout=1):
    if len(args) < 3:
        raise _err("Not enough input arguments.", "signal:bandpass:notEnoughInputs")
    if len(args) > 4:
        raise _err("Too many input arguments.", "signal:bandpass:tooManyInputs")
    x = _matlab2d(args[0], "bandpass")
    fpass = _matlab2d(args[1], "bandpass").reshape(-1)
    fs_arr = _matlab2d(args[2], "bandpass").reshape(-1)
    if fs_arr.size != 1 or not np.isfinite(fs_arr[0]) or fs_arr[0] <= 0:
        raise _err("Sampling frequency must be a positive scalar.", "signal:bandpass:invalidFs")
    order = 2
    if len(args) == 4:
        n_arr = _matlab2d(args[3], "bandpass").reshape(-1)
        if n_arr.size != 1 or n_arr[0] != np.floor(n_arr[0]) or n_arr[0] < 1:
            raise _err("Filter order must be a positive integer.", "signal:bandpass:invalidOrder")
        order = int(n_arr[0])
    fs = float(fs_arr[0])
    if fpass.size != 2 or not np.all(np.isfinite(fpass)) or not (0.0 < fpass[0] < fpass[1] < fs / 2.0):
        raise _err(
            "Passband must be [f1 f2] in Hz with 0 < f1 < f2 < fs/2.",
            "signal:bandpass:invalidFpass",
        )
    b, a = butter_ba(order, fpass / (fs / 2.0), "bandpass")
    return (_out(filtfilt_array(b, a, x)),)


def register(builtins: Dict[str, Callable]) -> None:
    builtins["butter"] = _butter
    builtins["filtfilt"] = _filtfilt
    builtins["bandpass"] = _bandpass
