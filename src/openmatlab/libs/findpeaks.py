"""``findpeaks`` for the ECG story (M15 B-E3, #1010).

Clean-room, from the public local-maximum rule. Not a copy of Octave Forge.

A sample is a peak when it starts a run that is strictly higher than both
neighbors. ``MinPeakHeight`` drops shorter peaks. ``MinPeakDistance`` then
keeps the tallest peak and drops anything closer than that distance; ties
keep the earlier sample. Locations are 1-based indices, or seconds from 0
when a sample rate is given.

The story subset is those two name-value pairs. Prominence, width, and
``NPeaks`` are out of scope. This is not a Pan-Tompkins detector.
"""

from __future__ import annotations

import bisect
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
    return NDArrayValue(np.asarray(a, dtype=np.float64))


def _scalar(v, name: str) -> float:
    a = _matlab2d(v, name).reshape(-1)
    if a.size != 1 or not np.isfinite(a[0]):
        raise _err(f"{name}: expected a finite scalar.", f"signal:{name}:invalidScalar")
    return float(a[0])


def local_max_indices(y: np.ndarray) -> np.ndarray:
    """0-based index of the first sample of each strict local-maximum run."""
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    if y.size < 3:
        return np.zeros(0, dtype=int)
    change = np.flatnonzero(y[1:] != y[:-1]) + 1
    starts = np.concatenate((np.array([0], dtype=int), change))
    ends = np.concatenate((change, np.array([y.size], dtype=int)))
    s = starts[1:-1]
    e = ends[1:-1]
    if s.size == 0:
        return s
    vals = y[s]
    keep = (vals > y[s - 1]) & (vals > y[e])
    return s[keep]


def _thin_samples(idx: np.ndarray, values: np.ndarray, min_dist: float, n: int) -> np.ndarray:
    """Keep tallest peaks whose sample indices are at least ``min_dist`` apart."""
    if min_dist <= 0 or idx.size <= 1:
        return idx
    order = np.lexsort((idx, -values))
    taken = np.zeros(n, dtype=bool)
    keep = []
    for k in order:
        i = int(idx[k])
        if taken[i]:
            continue
        keep.append(i)
        lo = max(0, int(np.floor(i - min_dist)) + 1)
        hi = min(n - 1, int(np.ceil(i + min_dist)) - 1)
        taken[lo : hi + 1] = True
    return np.asarray(sorted(keep), dtype=int)


def _thin_locations(loc: np.ndarray, values: np.ndarray, min_dist: float) -> np.ndarray:
    """Same rule when locations are not uniform sample indices."""
    if min_dist <= 0 or loc.size <= 1:
        return np.arange(loc.size)
    order = np.lexsort((loc, -values))
    kept: list[float] = []
    chosen: list[int] = []
    for k in order:
        x = float(loc[k])
        pos = bisect.bisect_left(kept, x)
        if pos < len(kept) and kept[pos] - x < min_dist:
            continue
        if pos > 0 and x - kept[pos - 1] < min_dist:
            continue
        kept.insert(pos, x)
        chosen.append(int(k))
    chosen.sort(key=lambda k: float(loc[k]))
    return np.asarray(chosen, dtype=int)


def findpeaks_array(y: np.ndarray, height: float, min_dist: float) -> tuple[np.ndarray, np.ndarray]:
    """Peak values and 0-based sample indices. ``min_dist`` is in samples."""
    idx = local_max_indices(y)
    if idx.size and np.isfinite(height):
        idx = idx[y[idx] >= height]
    idx = _thin_samples(idx, y[idx] if idx.size else np.zeros(0), min_dist, y.size)
    return y[idx], idx


def _orient(vals: np.ndarray, row: bool) -> np.ndarray:
    vals = np.asarray(vals, dtype=np.float64).reshape(-1)
    if vals.size == 0:
        return np.zeros((1, 0) if row else (0, 1), dtype=np.float64)
    return vals.reshape(1, -1) if row else vals.reshape(-1, 1)


def _findpeaks(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "signal:findpeaks:notEnoughInputs")
    y = _matlab2d(args[0], "findpeaks")
    if min(y.shape) != 1:
        raise _err("Y must be a vector.", "signal:findpeaks:expectedVector")
    row = y.shape[0] == 1
    data = y.reshape(-1)
    rest = list(args[1:])
    fs = None
    locations = None
    if rest and _text(rest[0]) is None:
        second = _matlab2d(rest.pop(0), "findpeaks").reshape(-1)
        if second.size == 1:
            if not np.isfinite(second[0]) or second[0] <= 0:
                raise _err("Sample rate must be a positive scalar.", "signal:findpeaks:invalidFs")
            fs = float(second[0])
        elif second.size == data.size:
            locations = second
        else:
            raise _err(
                "The location vector must have one element per sample, or be a positive sample rate.",
                "signal:findpeaks:invalidLocations",
            )
    if len(rest) % 2:
        raise _err("Name-value arguments must come in pairs.", "signal:findpeaks:invalidNameValue")
    height = -np.inf
    min_dist = 0.0
    for i in range(0, len(rest), 2):
        key = _text(rest[i])
        if key is None:
            raise _err("Parameter name must be text.", "signal:findpeaks:invalidNameValue")
        name = key.lower()
        if name == "minpeakheight":
            height = _scalar(rest[i + 1], "findpeaks")
        elif name == "minpeakdistance":
            min_dist = _scalar(rest[i + 1], "findpeaks")
            if min_dist < 0:
                raise _err("MinPeakDistance must be nonnegative.", "signal:findpeaks:invalidDistance")
        else:
            raise _err(
                f"'{key}' is not a supported findpeaks parameter. This slice has MinPeakHeight and MinPeakDistance.",
                "signal:findpeaks:unknownParameter",
            )
    if fs is not None:
        sample_dist = min_dist * fs
        pks, idx = findpeaks_array(data, height, sample_dist)
        locs = idx / fs
    elif locations is not None:
        idx = local_max_indices(data)
        if idx.size and np.isfinite(height):
            idx = idx[data[idx] >= height]
        pick = _thin_locations(locations[idx] if idx.size else np.zeros(0), data[idx] if idx.size else np.zeros(0), min_dist)
        idx = idx[pick] if idx.size else idx
        pks = data[idx]
        locs = locations[idx] if idx.size else np.zeros(0)
    else:
        pks, idx = findpeaks_array(data, height, min_dist)
        locs = idx.astype(np.float64) + 1.0
    pair = (_out(_orient(pks, row)), _out(_orient(locs, row)))
    if nargout <= 0:
        return ()
    return pair if nargout > 1 else pair[:1]


def register(builtins: Dict[str, Callable]) -> None:
    builtins["findpeaks"] = _findpeaks
