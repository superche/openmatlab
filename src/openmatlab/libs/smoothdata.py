"""smoothdata for the FD001 story (M14 V-E2, Epic #995).

Call shapes this slice accepts:

- ``smoothdata(A, method, window)``
- ``smoothdata(A, dim, method, window)``
- optional ``'omitnan'`` / ``'includenan'`` (also the ``*missing`` names)
- optional ``'SamplePoints', t`` for a numeric sample-point vector

``method`` is ``'movmean'`` (default) or ``'gaussian'``. ``window`` is a positive
scalar or ``[b f]``, the same lengths ``movmean`` uses. The window is required:
the public reference only says that an omitted window comes from a heuristic
that attenuates about ``100*SmoothingFactor`` percent of the energy, and it
does not specify the estimator.

``'movmean'`` is ``movmean`` on that window, dimension, and sample points.
``smoothdata`` defaults to ``'omitnan'``; ``movmean`` defaults to ``'includenan'``.
With no NaNs the two agree, and with NaNs ``smoothdata(...,'movmean',k)`` agrees
with ``movmean(...,k,'omitnan')``.

``'gaussian'`` is a weighted mean on that same window. The standard deviation
is one fifth of the window width (MathWorks staff, MATLAB Central answers
406563 and 471173): scalar ``k`` uses ``sigma = k/5``, and ``[b f]`` uses
``sigma = (b+f+1)/5``. Distance is in samples, or in sample-point units when
``SamplePoints`` is set. Weights are ``exp(-0.5*(d/sigma)^2)`` and are rescaled
to sum to 1 over the samples left after endpoint truncation and NaN omission.

Out of slice: automatic windows, ``SmoothingFactor``, ``movmedian``, lowess /
loess / sgolay, tables and timetables, duration windows, GPU.
"""

from __future__ import annotations

import numpy as np

from openmatlab.libs.stats import _arr, _dim, _err, _first_dim, _moving, _nd, _pad, _text, _window

_MOVMEAN = _moving("movmean")

_METHODS = ("movmean", "gaussian")
_UNSUPPORTED = ("movmedian", "lowess", "loess", "rlowess", "rloess", "sgolay")
_NAN = {"omitnan": True, "omitmissing": True, "includenan": False, "includemissing": False}
_OUTSIDE = ("smoothingfactor", "datavariables", "replacevalues", "degree")


def _spans(n, kb, kf, sp, kraw):
    """Window index pairs. Same membership as ``movmean`` (scalar half-open, ``[b f]`` closed)."""
    if sp is None:
        return [(i - kb, i + kf) for i in range(n)]
    if kraw.size == 1:
        half = float(kraw[0]) / 2.0
        return [
            (int(np.searchsorted(sp, sp[i] - half, "left")), int(np.searchsorted(sp, sp[i] + half, "left")) - 1)
            for i in range(n)
        ]
    b, f = float(kraw[0]), float(kraw[1])
    return [
        (int(np.searchsorted(sp, sp[i] - b, "left")), int(np.searchsorted(sp, sp[i] + f, "right")) - 1)
        for i in range(n)
    ]


def _gauss_row(row, spans, sigma, omit, sp):
    n = row.shape[0]
    out = np.empty(n, dtype=float)
    for i, (lo, hi) in enumerate(spans):
        a, b = max(lo, 0), min(hi, n - 1)
        if b < a:
            out[i] = np.nan
            continue
        sl = row[a : b + 1]
        d = (sp[a : b + 1] - sp[i]) if sp is not None else (np.arange(a, b + 1) - i)
        w = np.exp(-0.5 * (d / sigma) ** 2)
        if omit:
            ok = ~np.isnan(sl)
            if not np.any(ok):
                out[i] = np.nan
                continue
            w, sl = w[ok], sl[ok]
        elif np.any(np.isnan(sl)):
            out[i] = np.nan
            continue
        sw = float(w.sum())
        if not sw:
            out[i] = np.nan
            continue
        # Shift by the first sample so a constant window stays that constant.
        c0 = float(sl[0])
        out[i] = c0 + float(np.dot(w, sl - c0)) / sw
    return out


def _sample_points(v, n):
    sp = np.asarray(v.backend_buffer(), dtype=float).reshape(-1)
    if sp.size != n:
        raise _err(
            "Sample points must have the same length as the operating dimension.",
            "MATLAB:smoothdata:SamplePointsLength",
        )
    if sp.size > 1 and np.any(np.diff(sp) <= 0):
        raise _err(
            "Sample points must be sorted and contain unique elements.",
            "MATLAB:smoothdata:SamplePointsNotSorted",
        )
    return sp


def _sigma(kraw):
    if kraw.size == 1:
        return float(kraw[0]) / 5.0
    return (float(kraw[0]) + float(kraw[1]) + 1.0) / 5.0


def _gaussian(data, dim, window, omit, sp_value):
    a = _arr(data, "smoothdata")
    ax = _dim(dim, "smoothdata") if dim is not None else _first_dim(a)
    kb, kf = _window(window, "smoothdata")
    kraw = np.asarray(window.backend_buffer(), dtype=float).reshape(-1)
    a = _pad(a, ax)
    moved = np.moveaxis(a, ax, -1)
    n = moved.shape[-1]
    sp = _sample_points(sp_value, n) if sp_value is not None else None
    spans = _spans(n, kb, kf, sp, kraw)
    sigma = _sigma(kraw)
    out = np.empty(moved.shape, dtype=float)
    for idx in np.ndindex(moved.shape[:-1]):
        out[idx] = _gauss_row(moved[idx], spans, sigma, omit, sp)
    return _nd(np.moveaxis(out, -1, ax))


def _movmean(data, window, dim, omit, sp_value):
    from openmatlab.runtime.char_value import CharValue

    args = [data, window]
    if dim is not None:
        args.append(dim)
    args.append(CharValue("omitnan" if omit else "includenan"))
    if sp_value is not None:
        args.extend([CharValue("SamplePoints"), sp_value])
    return _MOVMEAN(args, nargout=1)[0]


def _parse(args):
    """Return ``(dim, method, window, omit, sample_points)`` from the arguments after ``A``."""
    dim = None
    method = "movmean"
    window = None
    omit = True
    sp = None
    seen_method = False
    i, n = 0, len(args)
    while i < n:
        t = _text(args[i])
        if t is None:
            if seen_method and window is None:
                window = args[i]
            elif not seen_method and dim is None:
                dim = args[i]
            else:
                raise _err("Unexpected numeric argument.", "OpenMATLAB:smoothdata:InvalidInput")
            i += 1
            continue
        tl = t.lower()
        if tl in _NAN:
            omit = _NAN[tl]
            i += 1
            continue
        if tl in _METHODS:
            if seen_method:
                raise _err("Specify the smoothing method once.", "OpenMATLAB:smoothdata:InvalidInput")
            method, seen_method = tl, True
            i += 1
            continue
        if tl in _UNSUPPORTED:
            raise _err(
                f"Smoothing method '{t}' is outside this slice. Use 'movmean' or 'gaussian'.",
                "OpenMATLAB:smoothdata:UnsupportedMethod",
            )
        if tl == "samplepoints":
            if i + 1 >= n:
                raise _err("SamplePoints requires a following value.", "OpenMATLAB:smoothdata:InvalidInput")
            sp = args[i + 1]
            i += 2
            continue
        if tl in _OUTSIDE:
            raise _err(
                f"'{t}' is outside this slice. Pass numeric data and an explicit window.",
                "OpenMATLAB:smoothdata:UnsupportedOption",
            )
        raise _err(f"Invalid option '{t}'.", "OpenMATLAB:smoothdata:invalidOption")
    if window is None:
        raise _err(
            "This slice requires a window, for example smoothdata(A,'movmean',15). "
            "Automatic window size is not implemented.",
            "OpenMATLAB:smoothdata:WindowRequired",
        )
    _window(window, "smoothdata")
    return dim, method, window, omit, sp


def _smoothdata(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if getattr(args[0], "is_table", False):
        raise _err(
            "smoothdata of a table or timetable is outside this slice. Pass the numeric columns.",
            "OpenMATLAB:smoothdata:Table",
        )
    _arr(args[0], "smoothdata")
    dim, method, window, omit, sp = _parse(list(args[1:]))
    if method == "movmean":
        result = _movmean(args[0], window, dim, omit, sp)
    else:
        result = _gaussian(args[0], dim, window, omit, sp)
    if nargout > 1:
        return [result, _nd(np.asarray(window.backend_buffer(), dtype=float))]
    return [result]


def register(builtins) -> None:
    builtins["smoothdata"] = _smoothdata
