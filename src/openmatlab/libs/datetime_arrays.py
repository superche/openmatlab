"""datetime/duration array completion (M10 T-E5, #695).

NaT, InputFormat parsing, text arrays, calendarDuration (caldays/calmonths/..., between, split),
dateshift, char/string/cellstr of datetime and duration, and concatenation of time arrays.
"""

from __future__ import annotations

import calendar
import datetime as _dt
import re

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime import calendar_duration as _cd
from openmatlab.runtime.calendar_duration import CalendarDurationValue
from openmatlab.runtime.objects import (DatetimeValue, DurationValue, _err, _is_text, _num, _text, datenum_from_parts,
                                        parts_from_datenum)


def _is_texty(v):
    return _is_text(v) or getattr(v, "is_string", False)


def _texts(v):
    """List of strings and the result shape for char / string array / cellstr input, else None."""
    from openmatlab.runtime.cell_value import CellValue

    if getattr(v, "is_string", False) and hasattr(v, "data"):
        a = np.asarray(v.data, dtype=object)
        a = a.reshape(1, 1) if a.ndim == 0 else a
        return [str(x) for x in a.reshape(-1, order="F")], a.shape
    if isinstance(v, CellValue) and not getattr(v, "nd", None):
        rows = v.rows
        if all(_is_text(x) for r in rows for x in r):
            shape = (len(rows), len(rows[0]) if rows else 0)
            return [_text(rows[i][j]) for j in range(shape[1]) for i in range(shape[0])], shape
    if _is_text(v):
        return [_text(v)], (1, 1)
    return None


# ------------------------------------------------------------------ InputFormat
_JAVA_TOKENS = [("yyyy", "%Y"), ("uuuu", "%Y"), ("yy", "%y"), ("MMMM", "%B"), ("MMM", "%b"), ("MM", "%m"), ("M", "%m"),
                ("dd", "%d"), ("d", "%d"), ("HH", "%H"), ("H", "%H"), ("hh", "%I"), ("h", "%I"), ("mm", "%M"),
                ("m", "%M"), ("ss", "%S"), ("s", "%S"), ("SSSSSS", "%f"), ("SSS", "%f"), ("SS", "%f"), ("S", "%f"),
                ("a", "%p"), ("EEEE", "%A"), ("eeee", "%A"), ("EEE", "%a"), ("eee", "%a")]


def java_to_strptime(f):
    out, i = "", 0
    while i < len(f):
        if f[i] == "'":  # quoted literal, e.g. 'T'
            j = f.find("'", i + 1)
            j = len(f) if j < 0 else j
            out += f[i + 1:j].replace("%", "%%")
            i = j + 1
            continue
        for tok, rep in _JAVA_TOKENS:
            if f.startswith(tok, i):
                out += rep
                i += len(tok)
                break
        else:
            out += "%%" if f[i] == "%" else f[i]
            i += 1
    return out


def parse_with_format(s, fmt):
    s = s.strip()
    if s == "" or s.lower() == "nat":
        return np.nan
    try:
        t = _dt.datetime.strptime(s, java_to_strptime(fmt))
    except ValueError:
        raise _err(f"Unable to convert the text '{s}' to datetime using the format '{fmt}'.",
                   "MATLAB:datetime:ParseErrWithFormat") from None
    return datenum_from_parts(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)


def _wrap_datetime(orig):
    def f(args, *, nargout=1):
        args = list(args)
        infmt = fmt = None
        rest = []
        i = 0
        while i < len(args):
            a = args[i]
            if _is_texty(a) and i + 1 < len(args) and _text(a).lower() in ("inputformat", "format", "locale", "pivotyear", "timezone"):
                key = _text(a).lower()
                if key == "inputformat":
                    infmt = _text(args[i + 1])
                elif key == "format":
                    fmt = _text(args[i + 1])
                elif key == "timezone" and _text(args[i + 1]):
                    raise _err("Time zones are not supported; omit 'TimeZone' to create an unzoned datetime.",
                               "MATLAB:datetime:TimeZoneUnsupported")
                i += 2
                continue
            rest.append(a)
            i += 1
        if len(rest) == 1 and (infmt is not None or not _is_text(rest[0])):
            tx = _texts(rest[0])
            if tx is not None:
                strs, shape = tx
                if infmt is not None:
                    dns = [parse_with_format(s, infmt) for s in strs]
                else:
                    from openmatlab.runtime.objects import parse_date_text

                    dns = [np.nan if s.strip() in ("", "NaT") else parse_date_text(s) for s in strs]
                v = np.array(dns, float).reshape(shape, order="F")
                return (DatetimeValue(v, fmt if fmt is not None else infmt),)
        if infmt is not None:
            raise _err("'InputFormat' requires text input.", "MATLAB:datetime:InputFormatNeedsText")
        call = rest + (["Format", fmt] if fmt is not None else [])
        from openmatlab.runtime.char_value import CharValue

        call = [CharValue(x) if isinstance(x, str) else x for x in call]
        return orig(call, nargout=nargout)
    return f


# ------------------------------------------------------------------ NaT
def _dims(args, name):
    nums = [a for a in args if not _is_texty(a)]
    if not nums:
        return (1, 1)
    d = [int(x) for a in nums for x in np.asarray(a.backend_buffer(), float).reshape(-1)]
    if len(d) == 1:
        return (max(d[0], 0), max(d[0], 0))
    return tuple(max(x, 0) for x in d[:2])


def _nat(args, *, nargout=1):
    fmt = None
    a = list(args)
    if len(a) >= 2 and _is_texty(a[-2]) and _text(a[-2]).lower() == "format":
        fmt = _text(a[-1])
        a = a[:-2]
    return (DatetimeValue(np.full(_dims(a, "NaT"), np.nan), fmt),)


# ------------------------------------------------------------------ calendarDuration constructors
def _arr(v, name):
    if v is None or _is_texty(v) or not hasattr(v, "backend_buffer"):
        raise _err(f"{name}: input must be numeric.", f"MATLAB:{name}:InvalidInput")
    return np.asarray(v.backend_buffer(), float)


def _int_check(a, name):
    if np.any(np.isfinite(a) & (a != np.round(a))):
        raise _err(f"{name}: input must contain integer values.", f"MATLAB:{name}:NonInteger")
    return a


def _calunit(name, months=0, days=0):
    def f(args, *, nargout=1):
        if args and isinstance(args[0], CalendarDurationValue):
            return tuple(_cd.split(args[0], [{"calyears": "years", "calquarters": "quarters", "calmonths": "months",
                                               "calweeks": "weeks", "caldays": "days"}[name]]))
        a = _int_check(_arr(args[0], name), name) if args else np.array([[1.0]])
        return (CalendarDurationValue(a * months, a * days, 0.0),)
    return f


def _calendarduration(args, *, nargout=1):
    nums = [a for a in args if not _is_texty(a)]
    if len(nums) == 1:
        a = _arr(nums[0], "calendarDuration")
        if a.ndim == 2 and a.shape[1] in (3, 6):
            cols = [a[:, k:k + 1] for k in range(a.shape[1])]
            nums_a = cols
        else:
            raise _err("calendarDuration: expected calendarDuration(y,mo,d) or (y,mo,d,h,mi,s).", "MATLAB:calendarDuration:InvalidInput")
    elif len(nums) in (3, 4, 6):
        nums_a = [_arr(x, "calendarDuration") for x in nums]
    else:
        raise _err("calendarDuration: expected calendarDuration(y,mo,d) or (y,mo,d,h,mi,s).", "MATLAB:calendarDuration:InvalidInput")
    y, mo, d = (_int_check(x, "calendarDuration") for x in nums_a[:3])
    if len(nums_a) == 4:
        t = nums_a[3].v if isinstance(nums[3], DurationValue) else nums_a[3]
    elif len(nums_a) == 6:
        t = nums_a[3] / 24 + nums_a[4] / 1440 + nums_a[5] / 86400
    else:
        t = 0.0
    return (CalendarDurationValue(y * 12 + mo, d, t),)


def _between(args, *, nargout=1):
    if len(args) < 2 or not all(isinstance(a, DatetimeValue) for a in args[:2]):
        raise _err("between: the first two inputs must be datetime arrays.", "MATLAB:datetime:between:InvalidInput")
    comps = _cd.parse_components(args[2] if len(args) > 2 else None)
    try:
        return (_cd.between(args[0], args[1], comps),)
    except ValueError:
        raise _err("between: the datetime arrays must be the same size or one must be scalar.", "MATLAB:sizeDimensionsMustMatch") from None


def _wrap_split(orig):
    def f(args, *, nargout=1):
        if args and isinstance(args[0], CalendarDurationValue):
            if len(args) < 2:
                raise _err("split: specify the date and time units.", "MATLAB:calendarDuration:split:MissingUnits")
            units = _cd.parse_components(args[1])
            out = _cd.split(args[0], units)
            return tuple(out[:max(1, nargout)])
        if args and isinstance(args[0], DurationValue):
            if len(args) < 2:
                raise _err("split: specify the time units.", "MATLAB:duration:split:MissingUnits")
            tx = _texts(args[1])
            units = [s.lower() for s in (tx[0] if tx else [])]
            k = {"years": 365.2425, "days": 1.0, "hours": 1 / 24, "minutes": 1 / 1440, "seconds": 1 / 86400}
            rest = args[0].v.copy()
            res = []
            for i, u in enumerate(units):
                if u not in k:
                    raise _err(f"'{u}' is not a valid time unit.", "MATLAB:duration:split:InvalidUnit")
                if i == len(units) - 1:
                    part = np.round(rest / k[u], 9)
                else:
                    part = np.fix(rest / k[u] + np.sign(rest) * 1e-9)
                    rest = rest - part * k[u]
                res.append(_num(part))
            return tuple(res[:max(1, nargout)])
        return orig(args, nargout=nargout)
    return f


# ------------------------------------------------------------------ dateshift
_UNITS = ("year", "quarter", "month", "week", "day", "hour", "minute", "second")


def _start(dn, unit):
    y, mo, d, h, mi, s = parts_from_datenum(dn)
    if unit == "year":
        return datenum_from_parts(y, 1, 1)
    if unit == "quarter":
        return datenum_from_parts(y, 3 * ((mo - 1) // 3) + 1, 1)
    if unit == "month":
        return datenum_from_parts(y, mo, 1)
    if unit == "week":  # weeks start on Sunday
        day = np.floor(dn)
        return day - ((day - 2) % 7)
    if unit == "day":
        return datenum_from_parts(y, mo, d)
    if unit == "hour":
        return datenum_from_parts(y, mo, d, h)
    if unit == "minute":
        return datenum_from_parts(y, mo, d, h, mi)
    return datenum_from_parts(y, mo, d, h, mi, np.floor(s + 1e-9))


def _add(dn, unit, n):
    if n == 0:
        return dn
    if unit in ("year", "quarter", "month"):
        mult = {"year": 12, "quarter": 3, "month": 1}[unit]
        return _cd._add_months(dn, n * mult)
    step = {"week": 7.0, "day": 1.0, "hour": 1 / 24, "minute": 1 / 1440, "second": 1 / 86400}[unit]
    return dn + n * step


def _end(dn, unit):
    """End of a calendar unit: the start of its last day (year, quarter, month, week)."""
    y, mo, d = parts_from_datenum(dn)[:3]
    if unit == "year":
        return datenum_from_parts(y, 12, 31)
    if unit == "quarter":
        qm = 3 * ((mo - 1) // 3) + 3
        return datenum_from_parts(y, qm, calendar.monthrange(y, qm)[1])
    if unit == "month":
        return datenum_from_parts(y, mo, calendar.monthrange(y, mo)[1])
    return _start(dn, "week") + 6


def _dateshift(args, *, nargout=1):
    if len(args) < 3 or not isinstance(args[0], DatetimeValue) or not _is_texty(args[1]) or not _is_texty(args[2]):
        raise _err("dateshift: expected dateshift(t, 'start'|'end', unit).", "MATLAB:datetime:dateshift:InvalidInput")
    t, where, unit = args[0], _text(args[1]).lower(), _text(args[2]).lower()
    if unit.endswith("s"):
        unit = unit[:-1]
    if where not in ("start", "end"):
        raise _err("dateshift: the second input must be 'start' or 'end'.", "MATLAB:datetime:dateshift:InvalidWhere")
    if unit not in _UNITS:
        raise _err(f"dateshift: '{unit}' is not a valid unit. Use 'year', 'quarter', 'month', 'week', 'day', 'hour', "
                   "'minute' or 'second'.", "MATLAB:datetime:dateshift:InvalidUnit")
    if where == "end" and unit not in ("year", "quarter", "month", "week"):
        raise _err(f"dateshift: 'end' with unit '{unit}' is not supported yet; use 'start' with the next unit.",
                   "MATLAB:datetime:dateshift:Unsupported")
    rule = np.zeros((1, 1))
    if len(args) > 3:
        r = args[3]
        if _is_texty(r):
            rule = np.array([[{"current": 0, "next": 1, "previous": -1}.get(_text(r).lower(), np.nan)]])
            if np.isnan(rule).any():
                raise _err("dateshift: rule must be 'current', 'next', 'previous' or an integer.", "MATLAB:datetime:dateshift:InvalidRule")
        else:
            rule = _int_check(_arr(r, "dateshift"), "dateshift")
    v, rr = np.broadcast_arrays(t.v, rule)
    out = np.empty(v.shape)
    for k in np.ndindex(v.shape):
        x = v[k]
        if np.isnan(x):
            out[k] = np.nan
            continue
        base = _add(_start(x, unit), unit, int(rr[k]))
        out[k] = _end(base, unit) if where == "end" else base
    return (DatetimeValue(out, t.fmt),)


# ------------------------------------------------------------------ text conversions
def _text_grid(v):
    return v.text_grid()


def _wrap_text(name, orig):
    def f(args, *, nargout=1):
        if args and isinstance(args[0], (DatetimeValue, DurationValue, CalendarDurationValue)):
            v = args[0]
            if len(args) > 1 and isinstance(v, DatetimeValue) and _is_texty(args[1]):
                v = DatetimeValue(v.v, _text(args[1]))
            grid = _text_grid(v)
            from openmatlab.runtime.char_value import CharValue

            if name == "char":
                if not grid or not grid[0]:
                    return (CharValue(""),)
                w = max(len(t) for r in grid for t in r)
                order = [grid[i][j] for j in range(len(grid[0])) for i in range(len(grid))]
                if len(order) == 1:
                    return (CharValue(order[0]),)
                return (CharValue(rows=tuple(t.ljust(w) for t in order)),)
            if name == "string":
                from openmatlab.runtime import string_array as sa

                a = np.array([list(r) for r in grid], dtype=object)
                return (sa.make(a),)
            from openmatlab.runtime.cell_value import CellValue

            return (CellValue(rows=tuple(tuple(CharValue(t) for t in r) for r in grid)),)
        return orig(args, nargout=nargout)
    return f


def _wrap_len(name, orig):
    def f(args, *, nargout=1):
        if args and isinstance(args[0], CalendarDurationValue):
            sh = args[0].shape
            if name == "numel":
                return (_num(int(np.prod(sh))),)
            if name == "length":
                return (_num(max(sh) if np.prod(sh) else 0),)
            if name == "isempty":
                return (NDArrayValue(np.array([[np.prod(sh) == 0]])),)
            if name == "size":
                return (_num([list(sh)]),) if nargout <= 1 else tuple(_num(d) for d in sh)[:nargout]
        if args and isinstance(args[0], (DatetimeValue, DurationValue, CalendarDurationValue)) and name in (
                "isrow", "iscolumn", "isvector", "isscalar", "ndims"):
            r, c = args[0].shape
            val = {"isrow": r == 1, "iscolumn": c == 1, "isvector": r == 1 or c == 1, "isscalar": r == 1 and c == 1,
                   "ndims": 2}[name]
            return ((_num(val),) if name == "ndims" else (NDArrayValue(np.array([[bool(val)]])),))
        return orig(args, nargout=nargout)
    return f


# ------------------------------------------------------------------ concatenation
def concat(rows):
    """[a b; c d] where some element is a datetime, duration or calendarDuration."""
    flat = [v for r in rows for v in r]
    kinds = {type(v) for v in flat if isinstance(v, (DatetimeValue, DurationValue, CalendarDurationValue))}
    if kinds == {CalendarDurationValue, DurationValue}:  # durations promote to calendarDuration
        kinds = {CalendarDurationValue}
    if len(kinds) > 1:
        names = sorted(k().matlab_class() if k is CalendarDurationValue else k(0).matlab_class() for k in kinds)
        raise _err(f"Cannot concatenate {' and '.join(names)} values.", "MATLAB:datetime:InvalidConcatenation")
    kind = kinds.pop()

    def conv(v):
        if isinstance(v, kind):
            return v
        if hasattr(v, "numel") and v.numel() == 0 and not _is_texty(v):
            return None
        if kind is DatetimeValue:
            tx = _texts(v)
            if tx is not None:
                from openmatlab.runtime.objects import parse_date_text

                strs, shape = tx
                return DatetimeValue(np.array([np.nan if s.strip() in ("", "NaT") else parse_date_text(s) for s in strs],
                                              float).reshape(shape, order="F"))
            raise _err("Only datetime values or date text can be concatenated with datetime values.",
                       "MATLAB:datetime:InvalidConcatenation")
        if kind is DurationValue:
            raise _err("Only durations can be concatenated with durations.", "MATLAB:duration:InvalidConcatenation")
        if isinstance(v, DurationValue):
            return CalendarDurationValue(0, 0, v.v)
        raise _err("Only calendar durations can be concatenated with calendar durations.",
                   "MATLAB:calendarDuration:InvalidConcatenation")

    first = next(v for v in flat if isinstance(v, kind))
    built = []
    for r in rows:
        items = [x for x in (conv(v) for v in r) if x is not None]
        if not items:
            continue
        hs = {x.shape[0] for x in items}
        if len(hs) > 1:
            raise _err("Dimensions of arrays being concatenated are not consistent.", "MATLAB:catenate:dimensionMismatch")
        built.append(items)
    if not built:
        return first
    widths = {sum(x.shape[1] for x in r) for r in built}
    if len(widths) > 1:
        raise _err("Dimensions of arrays being concatenated are not consistent.", "MATLAB:catenate:dimensionMismatch")
    if kind is CalendarDurationValue:
        parts = [np.vstack([np.hstack([getattr(x, a) for x in r]) for r in built]) for a in ("m", "d", "t")]
        return CalendarDurationValue(*parts)
    v = np.vstack([np.hstack([x.v for x in r]) for r in built])
    return kind._like(first, v)


def is_time(v):
    return isinstance(v, (DatetimeValue, DurationValue, CalendarDurationValue))


def register(builtins) -> None:
    builtins["datetime"] = _wrap_datetime(builtins["datetime"])
    builtins.update({
        "nat": _nat, "caldays": _calunit("caldays", days=1), "calweeks": _calunit("calweeks", days=7),
        "calmonths": _calunit("calmonths", months=1), "calquarters": _calunit("calquarters", months=3),
        "calyears": _calunit("calyears", months=12), "calendarduration": _calendarduration, "between": _between,
        "dateshift": _dateshift,
        "iscalendarduration": lambda a, *, nargout=1: (NDArrayValue(np.array([[isinstance(a[0], CalendarDurationValue)]])),),
    })
    if "split" in builtins:
        builtins["split"] = _wrap_split(builtins["split"])
    for n in ("char", "string", "cellstr"):
        if n in builtins:
            builtins[n] = _wrap_text(n, builtins[n])
    for n in ("numel", "length", "isempty", "size", "isrow", "iscolumn", "isvector", "isscalar", "ndims"):
        if n in builtins:
            builtins[n] = _wrap_len(n, builtins[n])
