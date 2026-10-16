"""timetable builtins (M10 T-E7, #697): timetable, table2timetable, timetable2table, istimetable,
timerange, withtol, retime, synchronize, lag.

``retime``/``synchronize`` build a new time vector, then fill each variable per method:
aggregation methods ('mean', 'sum', 'min', 'max', 'count', 'firstvalue', 'lastvalue') reduce the
rows in each bin ``[t_k, t_{k+1})`` (numeric/logical variables); fill methods ('previous',
'next', 'nearest', 'linear', 'fillwithmissing', 'fillwithconstant') read the row at or around each
new time. Missing results use each type's missing value (NaN, NaT, '', <missing>, <undefined>).
"""

from __future__ import annotations

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.table_value import TableValue, _err, height_of, is_text, text, texts
from openmatlab.runtime.timetable_value import (
    TimeRangeValue, TimetableValue, WithTolValue, coerce_time, days, is_time, like_times,
)

_AGG = ("mean", "sum", "min", "max", "count", "firstvalue", "lastvalue", "median", "prod")
_FILL = ("previous", "next", "nearest", "linear", "fillwithmissing", "fillwithconstant", "spline", "pchip")
_STEPS = {"yearly": None, "quarterly": None, "monthly": None, "weekly": 7.0, "daily": 1.0, "hourly": 1 / 24,
          "minutely": 1 / 1440, "secondly": 1 / 86400}


def _bool(b):
    return NDArrayValue(np.array([[bool(b)]]))


def _is_tt(v):
    return getattr(v, "is_timetable", False)


def _need_tt(v, fn):
    if not _is_tt(v):
        raise _err(f"{fn}: the first input must be a timetable.", "MATLAB:timetable:NotATimetable")
    return v


def _col_vec_times(t, fn):
    if not is_time(t):
        raise _err(f"{fn}: row times must be a datetime or duration vector.", "MATLAB:timetable:InvalidRowTimes")
    return like_times(t, days(t))


def _make_tt(cols, names, rowtimes, timename="Time"):
    n = rowtimes.numel()
    for c in cols:
        if height_of(c) != n:
            raise _err("All timetable variables must have the same number of rows as the row times.",
                       "MATLAB:timetable:IncorrectNumberOfRows")
    return TimetableValue(names, cols, n, rowtimes, [timename, "Variables"])


# =====================================================================
# construction / conversion
# =====================================================================
def _timetable(args, *, nargout=1):
    from openmatlab.libs.table_builtins import _caller_arg_names, _names_opt, _split_opts

    data, opts = _split_opts(args, ("variablenames", "rowtimes", "timestep", "samplerate", "starttime",
                                    "dimensionnames"))
    given = _caller_arg_names(len(data))
    if "rowtimes" in opts:
        rt, tname = opts["rowtimes"], "Time"
    elif "timestep" in opts or "samplerate" in opts:
        n = height_of(data[0]) if data else 0
        start = opts.get("starttime")
        if "timestep" in opts:
            step = float(days(opts["timestep"])[0])
        else:
            step = 1.0 / 86400 / float(np.asarray(opts["samplerate"].backend_buffer()).reshape(-1)[0])
        from openmatlab.runtime.objects import DurationValue

        base = start if start is not None else DurationValue(np.zeros((1, 1)))
        rt = like_times(base, float(days(base)[0]) + step * np.arange(n))
        tname = "Time"
    else:
        if not data or not is_time(data[0]):
            raise _err("timetable: the first input must be a datetime or duration vector of row times, or "
                       "specify 'RowTimes'.", "MATLAB:timetable:NoTimeVector")
        # a workspace variable passed as row times names the time dimension (MATLAB)
        rt, tname = data[0], (given[0] if given and given[0] else "Time")
        data, given = data[1:], given[1:]
    rt = _col_vec_times(rt, "timetable")
    default = [g if g else f"Var{k + 1}" for k, g in enumerate(given)]
    seen = set()
    for k, g in enumerate(default):
        if g in seen or g == tname:
            default[k] = f"Var{k + 1}"
        seen.add(default[k])
    names = _names_opt(opts, len(data), default)
    if "dimensionnames" in opts:
        dn = texts(opts["dimensionnames"])
        if dn and len(dn) == 2:
            tname = dn[0]
    return (_make_tt(list(data), names, rt, tname),)


def _table2timetable(args, *, nargout=1):
    from openmatlab.libs.table_builtins import _split_opts

    data, opts = _split_opts(args, ("rowtimes",))
    if len(data) != 1 or not getattr(data[0], "is_table", False) or _is_tt(data[0]):
        raise _err("table2timetable: input must be a table.", "MATLAB:table2timetable:NotATable")
    T = data[0]
    if "rowtimes" in opts:
        rt = opts["rowtimes"]
        if is_text(rt):
            k = T.var_index(text(rt))
            return (_make_tt([c for i, c in enumerate(T.cols) if i != k], [n for i, n in enumerate(T.names) if i != k],
                             _col_vec_times(T.cols[k], "table2timetable"), T.names[k]),)
        return (_make_tt(list(T.cols), list(T.names), _col_vec_times(rt, "table2timetable")),)
    for k, c in enumerate(T.cols):
        if is_time(c):
            return (_make_tt([c2 for i, c2 in enumerate(T.cols) if i != k], [n for i, n in enumerate(T.names) if i != k],
                             _col_vec_times(c, "table2timetable"), T.names[k]),)
    raise _err("table2timetable: the table has no datetime or duration variable to use as row times.",
               "MATLAB:table2timetable:NoTimeVarFound")


def _timetable2table(args, *, nargout=1):
    if len(args) < 1:
        raise _err("timetable2table: expected a timetable.", "MATLAB:minrhs")
    return (_need_tt(args[0], "timetable2table").as_table(),)


def _istimetable(args, *, nargout=1):
    if len(args) != 1:
        raise _err("istimetable: expected one input.", "MATLAB:minrhs")
    return (_bool(_is_tt(args[0])),)


def _istable_fix(orig):
    def f(args, *, nargout=1):
        if len(args) == 1 and _is_tt(args[0]):
            return (_bool(False),)  # MATLAB: istable(timetable) is false
        return orig(args, nargout=nargout)
    return f


def _timerange(args, *, nargout=1):
    if len(args) not in (2, 3):
        raise _err("timerange: expected timerange(startTime, endTime[, intervalType]).", "MATLAB:narginchk")
    kind = "openright"
    if len(args) == 3:
        if not is_text(args[2]):
            raise _err("timerange: intervalType must be text.", "MATLAB:timerange:InvalidIntervalType")
        kind = text(args[2]).lower()
        if kind not in ("open", "closed", "openleft", "openright", "closedleft", "closedright"):
            raise _err(f"timerange: unknown interval type '{text(args[2])}'.", "MATLAB:timerange:InvalidIntervalType")
    for a in args[:2]:
        if not (is_time(a) or is_text(a)):
            raise _err("timerange: start and end must be datetime, duration, or date text.",
                       "MATLAB:timerange:InvalidTimes")
    return (TimeRangeValue(args[0], args[1], kind),)


def _withtol(args, *, nargout=1):
    from openmatlab.runtime.objects import DurationValue

    if len(args) != 2:
        raise _err("withtol: expected withtol(rowTimes, tol).", "MATLAB:narginchk")
    if not isinstance(args[1], DurationValue):
        raise _err("withtol: the tolerance must be a duration.", "MATLAB:withtol:InvalidTolerance")
    if float(days(args[1])[0]) < 0:
        raise _err("withtol: the tolerance must be nonnegative.", "MATLAB:withtol:InvalidTolerance")
    return (WithTolValue(args[0], args[1]),)


# =====================================================================
# retime / synchronize
# =====================================================================
def _num_of(c, fn, method):
    if getattr(c, "is_object", False) or not hasattr(c, "backend_buffer"):
        raise _err(f"{fn}: method '{method}' needs numeric or logical variables; '{c.matlab_class()}' "
                   "is not supported.", "MATLAB:timetable:retime:NonNumericVar")
    a = np.asarray(c.backend_buffer())
    return a.reshape(a.shape[0], -1).astype(float)


def _fill_rows(c, n, rows):
    from openmatlab.libs.table_join_group import take_filled

    return take_filled(c, n, rows)


def _index_for(t, nt, method):
    """For each new time, the source row to read (-1 = missing) for a fill method."""
    out = np.full(len(nt), -1, dtype=int)
    order = np.argsort(t, kind="stable")
    ts = t[order]
    for k, x in enumerate(nt):
        exact = np.flatnonzero(np.abs(ts - x) <= 1e-9)
        if exact.size:
            out[k] = order[exact[0]]
            continue
        if method == "previous":
            j = np.searchsorted(ts, x, side="right") - 1
            out[k] = order[j] if j >= 0 else -1
        elif method == "next":
            j = np.searchsorted(ts, x, side="left")
            out[k] = order[j] if j < len(ts) else -1
        elif method == "nearest" and len(ts):
            out[k] = order[int(np.argmin(np.abs(ts - x)))]
    return out


def _retime_col(c, n, t, nt, method, edges, const, fn):
    if method in _AGG:
        a = _num_of(c, fn, method)
        res = np.full((len(nt), a.shape[1]), np.nan)
        for k in range(len(nt)):
            lo, hi = edges[k], edges[k + 1]
            m = (t >= lo - 1e-9) & ((t < hi - 1e-9) if k + 1 < len(nt) else (t <= hi + 1e-9))
            blk = a[m]
            if method == "count":
                res[k] = blk.shape[0]
            elif not blk.shape[0]:
                res[k] = 0 if method in ("sum",) else np.nan
            else:
                res[k] = {"mean": np.mean, "sum": np.sum, "min": np.min, "max": np.max, "median": np.median,
                          "prod": np.prod, "firstvalue": lambda b, axis: b[0], "lastvalue": lambda b, axis: b[-1]
                          }[method](blk, axis=0)
        return NDArrayValue(res)
    if method == "linear" or method in ("spline", "pchip"):
        a = _num_of(c, fn, method)
        o = np.argsort(t)
        res = np.column_stack([np.interp(nt, t[o], a[o, j], left=np.nan, right=np.nan) for j in range(a.shape[1])]) \
            if len(t) else np.full((len(nt), a.shape[1]), np.nan)
        return NDArrayValue(res.reshape(len(nt), -1))
    if method == "fillwithconstant":
        a = _num_of(c, fn, method)
        idx = _index_for(t, nt, "exact")
        res = np.where(idx[:, None] >= 0, a[np.maximum(idx, 0)] if len(a) else 0.0, const)
        return NDArrayValue(res.reshape(len(nt), -1))
    return _fill_rows(c, n, _index_for(t, nt, method))


def _regular_times(t, step, fn):
    if step is None or step <= 0:
        raise _err(f"{fn}: 'regular' needs a positive 'TimeStep' or 'SampleRate'.", "MATLAB:timetable:retime:NoTimeStep")
    if not len(t):
        return np.zeros(0)
    a, b = np.nanmin(t), np.nanmax(t)
    a = np.floor(a / step + 1e-9) * step if step in _STEPS.values() else a
    k = int(np.floor((b - a) / step + 1e-9))
    return a + step * np.arange(k + 1)


def _parse_basis(arg, opts, t_all, fn):
    """New time vector (days) from a basis argument: text keyword or a time vector."""
    step = None
    if "timestep" in opts:
        step = float(days(opts["timestep"])[0])
    elif "samplerate" in opts:
        step = 1.0 / 86400 / float(np.asarray(opts["samplerate"].backend_buffer()).reshape(-1)[0])
    if is_time(arg):
        return np.sort(days(arg)), arg
    if not is_text(arg):
        raise _err(f"{fn}: the new time basis must be a time vector or a keyword such as 'regular' or 'hourly'.",
                   "MATLAB:timetable:retime:InvalidTimeBasis")
    kw = text(arg).lower()
    if kw == "regular":
        return _regular_times(np.concatenate(t_all), step, fn), None
    if kw in _STEPS:
        if _STEPS[kw] is None:
            raise _err(f"{fn}: '{kw}' time steps are not supported yet; use 'regular' with a 'TimeStep'.",
                       "MATLAB:timetable:retime:Unsupported")
        return _regular_times(np.concatenate(t_all), _STEPS[kw], fn), None
    allt = np.concatenate(t_all) if t_all else np.zeros(0)
    if kw == "union":
        return _unique(allt), None
    if kw == "intersection":
        s = _unique(t_all[0])
        for o in t_all[1:]:
            s = np.array([x for x in s if np.any(np.abs(o - x) <= 1e-9)])
        return s, None
    if kw == "first":
        return _unique(t_all[0]), None
    if kw == "last":
        return _unique(t_all[-1]), None
    if kw == "commonrange":
        lo, hi = max(np.min(x) for x in t_all), min(np.max(x) for x in t_all)
        u = _unique(allt)
        return u[(u >= lo - 1e-9) & (u <= hi + 1e-9)], None
    raise _err(f"{fn}: unknown time basis '{text(arg)}'.", "MATLAB:timetable:retime:InvalidTimeBasis")


def _unique(t):
    s = np.sort(t[~np.isnan(t)])
    if not len(s):
        return s
    keep = np.concatenate([[True], np.diff(s) > 1e-9])
    return s[keep]


def _method(arg, fn):
    if not is_text(arg):
        raise _err(f"{fn}: the method must be text such as 'mean' or 'previous'.", "MATLAB:timetable:retime:InvalidMethod")
    m = text(arg).lower()
    if m not in _AGG + _FILL + ("default",):
        raise _err(f"{fn}: unknown method '{text(arg)}'.", "MATLAB:timetable:retime:InvalidMethod")
    return "fillwithmissing" if m == "default" else m


def _edges(nt, t):
    if len(nt) >= 2:
        return np.concatenate([nt, [nt[-1] + (nt[-1] - nt[-2])]])
    return np.concatenate([nt, [max(np.nanmax(t) if len(t) else nt[0], nt[0] if len(nt) else 0) + 1e-9]])


def _retime_one(TT, nt, method, const, fn):
    t = days(TT.rowtimes)
    edges = _edges(nt, t)
    return [_retime_col(c, TT.nrows, t, nt, method, edges, const, fn) for c in TT.cols]


def _split(args, fn):
    from openmatlab.libs.table_utils import _opts

    return _opts(args, ("timestep", "samplerate", "constant", "endvalues", "includededgee"), fn)


def _retime(args, *, nargout=1):
    data, opts = _split(args, "retime")
    if len(data) < 2:
        raise _err("retime: expected retime(TT, newTimes, method).", "MATLAB:minrhs")
    TT = _need_tt(data[0], "retime")
    method = _method(data[2], "retime") if len(data) > 2 else "fillwithmissing"
    nt, _src = _parse_basis(data[1], opts, [days(TT.rowtimes)], "retime")
    const = float(np.asarray(opts["constant"].backend_buffer()).reshape(-1)[0]) if "constant" in opts else 0.0
    cols = _retime_one(TT, nt, method, const, "retime")
    return (TT.copy(cols=cols, nrows=len(nt), rowtimes=like_times(TT.rowtimes, nt)),)


def _synchronize(args, *, nargout=1):
    from openmatlab.libs.table_builtins import _caller_arg_names

    data, opts = _split(args, "synchronize")
    k = 0
    while k < len(data) and _is_tt(data[k]):
        k += 1
    tts, rest = data[:k], data[k:]
    if not tts:
        raise _err("synchronize: expected timetables.", "MATLAB:timetable:NotATimetable")
    first = type(tts[0].rowtimes)
    if any(type(T.rowtimes) is not first for T in tts):
        raise _err("synchronize: all timetables must use the same kind of row times (datetime or duration).",
                   "MATLAB:timetable:synchronize:MixedTimeTypes")
    basis = rest[0] if rest else NDArrayValue(np.zeros((0, 0)))
    if not rest:
        from openmatlab.runtime.char_value import CharValue

        basis = CharValue("union")
    method = _method(rest[1], "synchronize") if len(rest) > 1 else "fillwithmissing"
    nt, _ = _parse_basis(basis, opts, [days(T.rowtimes) for T in tts], "synchronize")
    const = float(np.asarray(opts["constant"].backend_buffer()).reshape(-1)[0]) if "constant" in opts else 0.0
    given = _caller_arg_names(len(tts))
    counts = {}
    for T in tts:
        for n in T.names:
            counts[n] = counts.get(n, 0) + 1
    names, cols = [], []
    for i, T in enumerate(tts):
        tag = given[i] or f"{i + 1}"
        for n, c in zip(T.names, _retime_one(T, nt, method, const, "synchronize")):
            names.append(f"{n}_{tag}" if counts[n] > 1 else n)
            cols.append(c)
    return (TimetableValue(names, cols, len(nt), like_times(tts[0].rowtimes, nt), tts[0].dimnames),)


def _lag(args, *, nargout=1):
    if not args:
        raise _err("lag: expected lag(TT, n).", "MATLAB:minrhs")
    TT = _need_tt(args[0], "lag")
    n = 1
    if len(args) > 1:
        if is_time(args[1]):
            t = days(TT.rowtimes)
            step = np.diff(t)
            if len(step) == 0 or np.any(np.abs(step - step[0]) > 1e-9):
                raise _err("lag: a duration lag needs a regular timetable.", "MATLAB:timetable:lag:IrregularTimes")
            n = int(round(float(days(args[1])[0]) / step[0]))
        else:
            n = float(np.asarray(args[1].backend_buffer()).reshape(-1)[0])
            if n != int(n):
                raise _err("lag: the lag must be an integer number of time steps.", "MATLAB:timetable:lag:NonIntegerLag")
            n = int(n)
    rows = np.arange(TT.nrows) - n
    rows[(rows < 0) | (rows >= TT.nrows)] = -1
    from openmatlab.runtime import frames  # noqa: F401  (evaluator context for take_filled)

    cols = [_fill_rows(c, TT.nrows, rows) for c in TT.cols]
    return (TT.copy(cols=cols),)


def register(builtins) -> None:
    builtins.update(timetable=_timetable, table2timetable=_table2timetable, timetable2table=_timetable2table,
                    istimetable=_istimetable, timerange=_timerange, withtol=_withtol, retime=_retime,
                    synchronize=_synchronize, lag=_lag)
    if "istable" in builtins:
        builtins["istable"] = _istable_fix(builtins["istable"])
