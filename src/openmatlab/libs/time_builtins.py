"""containers.Map functions and date/time basics (Epic #539).

containers.Map, keys, values, isKey, remove (+ length/isempty/numel on maps);
datetime, year/month/day/hour/minute/second, days/hours/minutes/seconds/
years/duration, datenum, datestr, now, clock, date, weekday, etime,
isdatetime/isduration/isobject.
"""

from __future__ import annotations

import datetime as _dt
import math
import time
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.objects import (DatetimeValue, DurationValue, MapValue, datenum_from_parts,
                                        datestr_format, map_new, parse_date_text, parts_from_datenum)


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _is_text(v):
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue)


def _text(v):
    if getattr(v, "is_string", False) and hasattr(v, "data"):
        return str(v.data.flat[0])
    return v.text


def _cv(s):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(s)


def _arr(v, fn):
    if _is_text(v) or not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: expected a numeric argument.", f"MATLAB:{fn}:InvalidInput")
    return np.asarray(v.backend_buffer(), dtype=float)


def _num(x):
    a = np.asarray(x, dtype=float)
    return NDArrayValue(a.reshape(1, 1) if a.ndim == 0 else (a.reshape(1, -1) if a.ndim == 1 else a))


def _row_cell(items):
    from openmatlab.runtime.cell_value import CellValue

    if not items:
        return CellValue(rows=())
    return CellValue(rows=(tuple(items),))


def _need_map(v, fn):
    if not isinstance(v, MapValue):
        raise _err(f"Undefined function '{fn}' for input arguments of type '{v.matlab_class()}'.", "MATLAB:UndefinedFunction")
    return v


# ------------------------------------------------------------------ Map
def _map(args, *, nargout=1):
    return (map_new(args),)


def _keys(args, *, nargout=1):
    m = _need_map(args[0], "keys")
    return (_row_cell([m._key_value(k) for k in m.sorted_keys()]),)


def _values(args, *, nargout=1):
    m = _need_map(args[0], "values")
    if len(args) > 1:
        from openmatlab.runtime.cell_value import CellValue

        ks = args[1]
        if not isinstance(ks, CellValue):
            raise _err("values: keySet must be a cell array.", "MATLAB:Containers:Map:KeySetNotCell")
        r, c = ks.shape
        return (_row_cell([m.index([ks.get(i, j)]) for j in range(c) for i in range(r)]),)
    return (_row_cell([m.data[k] for k in m.sorted_keys()]),)


def _iskey(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    m = _need_map(args[0], "isKey")
    k = args[1]
    if isinstance(k, CellValue):
        r, c = k.shape
        out = np.array([[_has(m, k.get(i, j)) for j in range(c)] for i in range(r)], dtype=bool)
        return (NDArrayValue(out),)
    return (NDArrayValue(np.array([[_has(m, k)]])),)


def _has(m, k):
    try:
        return m._key(k) in m.data
    except Exception:
        return False


def _remove(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    m = _need_map(args[0], "remove")
    ks = args[1]
    items = [ks.get(i, j) for j in range(ks.shape[1]) for i in range(ks.shape[0])] if isinstance(ks, CellValue) else [ks]
    for k in items:
        kk = m._key(k)
        if kk not in m.data:
            raise _err("The specified key is not present in this container.", "MATLAB:Containers:Map:NoKey")
        del m.data[kk]
    return (m,)


def _wrap_len(name, orig):
    def f(args, *, nargout=1):
        if args and isinstance(args[0], MapValue):
            n = len(args[0].data)
            if name == "length":
                return (_num(n),)
            if name == "isempty":
                return (NDArrayValue(np.array([[n == 0]])),)
            if name == "numel":
                return (_num(1),)
            if name == "size":
                return (_num([[1, 1]]),) if nargout <= 1 else (_num(1), _num(1))[:nargout]
        if args and isinstance(args[0], (DatetimeValue, DurationValue)):
            v = args[0].v
            if name == "length":
                return (_num(max(v.shape) if v.size else 0),)
            if name == "isempty":
                return (NDArrayValue(np.array([[v.size == 0]])),)
            if name == "numel":
                return (_num(v.size),)
            if name == "size":
                return (_num([list(v.shape)]),) if nargout <= 1 else tuple(_num(d) for d in v.shape)[:nargout]
        return orig(args, nargout=nargout)
    return f


# ------------------------------------------------------------------ datetime
def _datetime(args, *, nargout=1):
    args = list(args)
    fmt = None
    if len(args) >= 2 and _is_text(args[-2]) and _text(args[-2]).lower() in ("format", "inputformat"):
        if _text(args[-2]).lower() == "format":
            fmt = _text(args[-1])
        args = args[:-2]
    if not args:
        t = _dt.datetime.now()
        return (DatetimeValue(datenum_from_parts(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6), fmt),)
    if len(args) == 1 and _is_text(args[0]):
        s = _text(args[0]).lower()
        today = _dt.date.today()
        if s == "now":
            return _datetime([], nargout=1) if fmt is None else (DatetimeValue(_datetime([])[0].v, fmt),)
        if s in ("today", "tomorrow", "yesterday"):
            off = {"today": 0, "tomorrow": 1, "yesterday": -1}[s]
            return (DatetimeValue(datenum_from_parts(today.year, today.month, today.day) + off, fmt),)
        return (DatetimeValue(parse_date_text(_text(args[0])), fmt),)
    if len(args) == 1:
        # datetime(DateVectors) or datetime(X, 'ConvertFrom', ...) not supported; a [y m d ...] row works
        a = _arr(args[0], "datetime")
        if a.ndim == 2 and a.shape[1] in (3, 6):
            dns = [datenum_from_parts(*row) for row in a]
            return (DatetimeValue(np.array(dns).reshape(-1, 1) if len(dns) > 1 else dns[0], fmt),)
        raise _err("datetime: numeric input must be a date vector [y m d] or [y m d h mi s].", "MATLAB:datetime:InvalidNumericData")
    if len(args) not in (3, 6, 7):
        raise _err("datetime: expected datetime(y, mo, d) or datetime(y, mo, d, h, mi, s).", "MATLAB:datetime:InvalidNumericData")
    parts = [_arr(a, "datetime") for a in args[:6]]
    if len(args) == 7:
        parts[5] = parts[5] + _arr(args[6], "datetime") / 1000.0
    b = np.broadcast_arrays(*parts)
    dn = np.vectorize(lambda *p: datenum_from_parts(*p))(*b) if b[0].size != 1 else datenum_from_parts(*[float(x.reshape(-1)[0]) for x in b])
    return (DatetimeValue(dn, fmt),)


def _part(idx, name):
    def f(args, *, nargout=1):
        v = args[0] if args else None
        if isinstance(v, DatetimeValue):
            out = np.array([parts_from_datenum(x)[idx] if not np.isnan(x) else np.nan for x in v.v.reshape(-1)], float)
            return (_num(out.reshape(v.v.shape)),)
        if v is not None and not _is_text(v) and hasattr(v, "backend_buffer") and name in ("year", "month", "day", "hour", "minute", "second"):
            # numeric datenum input (Financial-toolbox style), MATLAB accepts for year/month/day
            a = np.asarray(v.backend_buffer(), float)
            out = np.array([parts_from_datenum(x)[idx] for x in a.reshape(-1)], float)
            return (_num(out.reshape(a.shape)),)
        raise _err(f"{name}: input must be a datetime.", f"MATLAB:{name}:InvalidInput")
    return f


_UNIT = {"years": 365.2425, "days": 1.0, "hours": 1 / 24, "minutes": 1 / 1440, "seconds": 1 / 86400, "milliseconds": 1 / 86400000}
_FMT = {"years": "y", "days": "d", "hours": "h", "minutes": "m", "seconds": "s", "milliseconds": "s"}


def _unit(name):
    k = _UNIT[name]

    def f(args, *, nargout=1):
        if not args:
            return (DurationValue(np.array([[1.0 * k]]), _FMT[name]),)
        v = args[0]
        if isinstance(v, DurationValue):
            return (_num(v.v / k),)
        if isinstance(v, DatetimeValue):
            raise _err(f"{name}: input must be numeric or a duration.", f"MATLAB:{name}:InvalidInput")
        return (DurationValue(_arr(v, name) * k, _FMT[name]),)
    return f


def _duration(args, *, nargout=1):
    nums = [a for a in args if not _is_text(a)]
    if len(nums) < 3:
        raise _err("duration: expected duration(h, mi, s).", "MATLAB:duration:InvalidInput")
    h, mi, s = (_arr(a, "duration") for a in nums[:3])
    ms = _arr(nums[3], "duration") if len(nums) > 3 else 0.0
    return (DurationValue(h / 24 + mi / 1440 + (s + ms / 1000) / 86400),)


def _datenum(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    if len(args) == 1:
        v = args[0]
        if isinstance(v, DatetimeValue):
            return (_num(v.v),)
        if _is_text(v):
            return (_num(parse_date_text(_text(v))),)
        a = _arr(v, "datenum")
        if a.ndim == 2 and a.shape[1] in (3, 6) and a.shape[0] >= 1 and a.reshape(-1)[0] > 31:
            return (_num(np.array([datenum_from_parts(*row) for row in a]).reshape(-1, 1)),)
        return (_num(a),)
    if len(args) == 2 and _is_text(args[0]):
        return (_num(parse_date_text(_text(args[0]))),)
    parts = [_arr(a, "datenum") for a in args[:6]]
    b = np.broadcast_arrays(*parts)
    if b[0].size == 1:
        return (_num(datenum_from_parts(*[float(x.reshape(-1)[0]) for x in b])),)
    return (_num(np.vectorize(lambda *p: datenum_from_parts(*p))(*b)),)


_FREE = {0: "dd-mmm-yyyy HH:MM:SS", 1: "dd-mmm-yyyy", 2: "mm/dd/yy", 3: "mmm", 4: "m", 5: "mm", 6: "mm/dd",
         7: "dd", 8: "ddd", 9: "d", 10: "yyyy", 11: "yy", 12: "mmmyy", 13: "HH:MM:SS", 14: "HH:MM:SS PM",
         15: "HH:MM", 16: "HH:MM PM", 17: "QQ-YY", 18: "QQ", 19: "dd/mm", 20: "dd/mm/yy", 21: "mmm.dd,yyyy HH:MM:SS",
         22: "mmm.dd,yyyy", 23: "mm/dd/yyyy", 24: "dd/mm/yyyy", 25: "yy/mm/dd", 26: "yyyy/mm/dd", 27: "QQ-YYYY",
         28: "mmmyyyy", 29: "yyyy-mm-dd", 30: "yyyymmddTHHMMSS", 31: "yyyy-mm-dd HH:MM:SS"}  # documented table


def _datestr(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    v = args[0]
    if isinstance(v, DatetimeValue):
        dns = v.v.reshape(-1)
    elif _is_text(v):
        dns = np.array([parse_date_text(_text(v))])
    else:
        a = _arr(v, "datestr")
        if a.ndim == 2 and a.shape[1] in (3, 6) and a.reshape(-1)[0] > 31:
            dns = np.array([datenum_from_parts(*row) for row in a])
        else:
            dns = a.reshape(-1)
    fmt = None
    if len(args) > 1:
        f = args[1]
        if _is_text(f):
            fmt = _text(f)
        else:
            code = int(_arr(f, "datestr").reshape(-1)[0])
            if code not in _FREE:
                raise _err(f"datestr: unsupported numeric format {code}.", "MATLAB:datestr:InvalidFormat")
            fmt = _FREE[code]
    if fmt is None:
        any_time = any(parts_from_datenum(x)[3:] != (0, 0, 0) for x in dns)
        fmt = "dd-mmm-yyyy HH:MM:SS" if any_time else "dd-mmm-yyyy"
    rows = [datestr_format(x, fmt) for x in dns]
    if len(rows) == 1:
        return (_cv(rows[0]),)
    from openmatlab.runtime.char_value import CharValue

    w = max(len(r) for r in rows)
    return (CharValue(rows=tuple(r.ljust(w) for r in rows)),)


def _now(args, *, nargout=1):
    t = _dt.datetime.now()
    return (_num(datenum_from_parts(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)),)


def _clock(args, *, nargout=1):
    t = _dt.datetime.now()
    return (_num([[t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6]]),)


def _date(args, *, nargout=1):
    t = _dt.date.today()
    return (_cv(datestr_format(datenum_from_parts(t.year, t.month, t.day), "dd-mmm-yyyy")),)


def _weekday(args, *, nargout=1):
    v = args[0]
    dn = v.v if isinstance(v, DatetimeValue) else (np.array([[parse_date_text(_text(v))]]) if _is_text(v) else _arr(v, "weekday"))
    n = np.mod(np.floor(dn) - 2, 7) + 1
    if nargout > 1:
        from openmatlab.runtime.char_value import CharValue

        names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        rows = tuple(names[int(k) - 1] for k in n.reshape(-1))
        return (_num(n), CharValue(rows=rows) if len(rows) > 1 else _cv(rows[0]))
    return (_num(n),)


def _etime(args, *, nargout=1):
    a, b = _arr(args[0], "etime").reshape(-1), _arr(args[1], "etime").reshape(-1)
    if a.size != 6 or b.size != 6:
        raise _err("etime: inputs must be 6-element clock vectors.", "MATLAB:etime:InvalidInput")
    return (_num((datenum_from_parts(*b) - datenum_from_parts(*a)) * 86400),)


def _isa(cls):
    def f(args, *, nargout=1):
        return (NDArrayValue(np.array([[isinstance(args[0], cls)]])),)
    return f


def _isnat(args, *, nargout=1):
    if not args or not isinstance(args[0], DatetimeValue):
        cls = args[0].matlab_class() if args else "double"
        raise _err(f"Undefined function 'isnat' for input arguments of type '{cls}'.", "MATLAB:UndefinedFunction")
    return (NDArrayValue(np.isnan(args[0].v)),)


def _isobject(args, *, nargout=1):
    v = args[0]
    return (NDArrayValue(np.array([[bool(getattr(v, "is_object", False) or getattr(v, "is_graphics_handle", False))]])),)


def register(builtins: Dict[str, Callable]) -> None:
    table = {
        "containers.Map": _map, "keys": _keys, "values": _values, "isKey": _iskey, "remove": _remove,
        "datetime": _datetime, "year": _part(0, "year"), "month": _part(1, "month"), "day": _part(2, "day"),
        "hour": _part(3, "hour"), "minute": _part(4, "minute"), "second": _part(5, "second"),
        "years": _unit("years"), "days": _unit("days"), "hours": _unit("hours"), "minutes": _unit("minutes"),
        "seconds": _unit("seconds"), "milliseconds": _unit("milliseconds"), "duration": _duration,
        "datenum": _datenum, "datestr": _datestr, "now": _now, "clock": _clock, "date": _date,
        "weekday": _weekday, "etime": _etime, "isdatetime": _isa(DatetimeValue), "isduration": _isa(DurationValue),
        "isobject": _isobject, "isnat": _isnat,
    }
    for k, v in table.items():
        builtins.setdefault(k.lower(), v)  # the resolver looks names up lower-cased
    for n in ("length", "isempty", "numel", "size"):
        if n in builtins:
            builtins[n] = _wrap_len(n, builtins[n])
