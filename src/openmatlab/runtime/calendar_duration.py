"""calendarDuration (M10 T-E5, #695): lengths of time in variable-length calendar units.

Stored as three same-shaped float arrays: whole months, whole days and a time part (in days, like
``duration``). Adding to a datetime applies months first (clamping the day to the month's end, so
31-Jan + 1 month is the last day of February), then days, then the time part.
"""

from __future__ import annotations

import calendar
import math

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.objects import (DatetimeValue, DurationValue, _err, _is_text, _num, _text, datenum_from_parts,
                                        parts_from_datenum, _grid_text)


def _shape2(a):
    a = np.asarray(a, float)
    return a.reshape(1, 1) if a.ndim == 0 else (a.reshape(1, -1) if a.ndim == 1 else a)


class CalendarDurationValue:
    is_object = True
    is_calendar_duration = True

    def __init__(self, months=0.0, days=0.0, time=0.0):
        m, d, t = np.broadcast_arrays(_shape2(months), _shape2(days), _shape2(time))
        self.m, self.d, self.t = m.astype(float).copy(), d.astype(float).copy(), t.astype(float).copy()

    @property
    def shape(self):
        return self.m.shape

    def numel(self):
        return int(self.m.size)

    def is_scalar(self):
        return self.m.size == 1

    def matlab_class(self):
        return "calendarDuration"

    def _map(self, fn):
        return CalendarDurationValue(fn(self.m), fn(self.d), fn(self.t))

    def transpose_value(self):
        return self._map(lambda a: a.T)

    def index(self, args):
        idx = []
        for a in args:
            if _is_text(a) and _text(a) == ":":
                idx.append(slice(None))
            else:
                b = np.asarray(a.backend_buffer())
                idx.append(np.flatnonzero(b.reshape(-1)) if b.dtype == bool else b.reshape(-1).astype(int) - 1)
        if len(idx) == 1:
            row = self.m.shape[0] == 1

            def one(a):
                f = a.reshape(-1, order="F")[idx[0]]
                return f.reshape(1, -1) if row else f.reshape(-1, 1)
            return self._map(one)
        return self._map(lambda a: a[np.ix_(*[np.atleast_1d(np.arange(a.shape[k])[i]) for k, i in enumerate(idx)])])

    def get_prop(self, name):
        if name.lower() == "format":
            from openmatlab.runtime.objects import _cv

            return _cv("ymdt")
        raise _err(f"Unrecognized property '{name}' for class 'calendarDuration'.", "MATLAB:noSuchMethodOrField")

    def binop(self, op, other, reflected):
        o = other
        if isinstance(o, DatetimeValue):
            return datetime_binop(o, op, self, not reflected)
        if op in ("+", "-"):
            if isinstance(o, DurationValue):
                o = CalendarDurationValue(0, 0, o.v)
            elif not isinstance(o, CalendarDurationValue):
                if hasattr(o, "backend_buffer") and not _is_text(o):  # numbers are days
                    o = CalendarDurationValue(0, np.asarray(o.backend_buffer(), float), 0)
                else:
                    return NotImplemented
            a, b = (o, self) if reflected else (self, o)
            sg = 1.0 if op == "+" else -1.0
            return CalendarDurationValue(a.m + sg * b.m, a.d + sg * b.d, a.t + sg * b.t)
        if op in ("*", ".*") and not isinstance(o, (CalendarDurationValue, DurationValue)) and hasattr(o, "backend_buffer"):
            k = np.asarray(o.backend_buffer(), float)
            if np.any(k != np.round(k)):
                raise _err("Calendar durations can only be multiplied by integer values.", "MATLAB:calendarDuration:NonIntegerMultiplier")
            return CalendarDurationValue(self.m * k, self.d * k, self.t * k)
        if op in ("==", "~="):
            if not isinstance(o, CalendarDurationValue):
                raise _err("Comparison is not defined between calendarDuration and non-calendarDuration values.",
                           "MATLAB:calendarDuration:InvalidComparison")
            eq = (self.m == o.m) & (self.d == o.d) & (np.abs(self.t - o.t) < 1e-12)
            return NDArrayValue(eq if op == "==" else ~eq)
        if op in ("<", ">", "<=", ">="):
            raise _err("Relational comparisons are not defined for calendar durations, because their lengths vary.",
                       "MATLAB:calendarDuration:RelationalComparison")
        return NotImplemented

    def text_grid(self):
        def one(m, d, t):
            if np.isnan(m) or np.isnan(d) or np.isnan(t):
                return "NaN"
            out = []
            y, mo = int(math.trunc(m / 12)), int(m - 12 * math.trunc(m / 12))
            if y:
                out.append(f"{y}y")
            if mo:
                out.append(f"{mo}mo")
            if d:
                out.append(f"{int(d)}d")
            if abs(t) > 1e-12:
                secs = round(t * 86400, 4)
                sg = -1 if secs < 0 else 1
                a = abs(secs)
                hh, mm, ss = int(a // 3600), int(a % 3600 // 60), a % 60
                for val, u in ((hh, "h"), (mm, "m"), (ss, "s")):
                    if val:
                        out.append(f"{sg * val:g}{u}")
            return " ".join(out) if out else "0d"
        return [[one(*z) for z in zip(rm, rd, rt)] for rm, rd, rt in zip(self.m, self.d, self.t)]

    def display_text(self):
        return _grid_text(self.text_grid())


# ------------------------------------------------------------------ arithmetic with datetime
def _add_months(dn, months):
    y, mo, d, h, mi, s = parts_from_datenum(dn)
    total = (y * 12 + (mo - 1)) + int(months)
    ny, nm = divmod(total, 12)
    nd = min(d, calendar.monthrange(ny, nm + 1)[1])
    return datenum_from_parts(ny, nm + 1, nd, h, mi, s)


def shift(dn_arr, cd, sign=1.0):
    dn, m, d, t = np.broadcast_arrays(np.asarray(dn_arr, float), cd.m, cd.d, cd.t)
    out = np.empty(dn.shape)
    for k in np.ndindex(dn.shape):
        x = dn[k]
        if np.isnan(x) or np.isnan(m[k]):
            out[k] = np.nan
            continue
        if m[k]:
            x = _add_months(x, sign * m[k])
        out[k] = x + sign * d[k] + sign * t[k]
    return out


def datetime_binop(dt, op, cd, reflected):
    if op == "+":
        return DatetimeValue(shift(dt.v, cd), dt.fmt)
    if op == "-" and not reflected:
        return DatetimeValue(shift(dt.v, cd, -1.0), dt.fmt)
    if op == "-":
        raise _err("Subtraction of a datetime from a calendar duration is not defined.", "MATLAB:datetime:DurationMinusDatetime")
    return NotImplemented


# ------------------------------------------------------------------ between
_COMPONENTS = ("years", "quarters", "months", "weeks", "days", "time")


def parse_components(v):
    if v is None:
        return ["years", "months", "days", "time"]
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(v, CellValue):
        items = [_text(x) for r in v.rows for x in r]
    elif getattr(v, "is_string", False):
        items = [str(x) for x in np.asarray(v.data).reshape(-1)]
    else:
        items = [_text(v)]
    out = []
    for s in items:
        s = s.lower()
        if s not in _COMPONENTS:
            raise _err(f"'{s}' is not a valid date or time component. Valid components are 'years', 'quarters', "
                       "'months', 'weeks', 'days', and 'time'.", "MATLAB:datetime:InvalidComponents")
        out.append(s)
    return out


def _between1(a, b, comps):
    """calendarDuration parts (months, days, time) from a to b using only ``comps``."""
    if np.isnan(a) or np.isnan(b):
        return np.nan, np.nan, np.nan
    neg = b < a
    if neg:
        a, b = b, a
    months = 0
    mstep = 1 if "months" in comps else (3 if "quarters" in comps else 12)
    if any(c in comps for c in ("years", "quarters", "months")):
        ya, ma = parts_from_datenum(a)[:2]
        yb, mb = parts_from_datenum(b)[:2]
        months = ((yb - ya) * 12 + (mb - ma)) // mstep * mstep
        while months > 0 and _add_months(a, months) > b + 1e-9:
            months -= mstep
    base = _add_months(a, months) if months else a
    rest = b - base
    days = 0.0
    if "days" in comps or "weeks" in comps:
        days = math.floor(rest + 1e-9)
        if "days" not in comps:
            days -= days % 7
        rest -= days
    t = rest if "time" in comps else 0.0
    sg = -1.0 if neg else 1.0
    return sg * months, sg * days, sg * t


def between(t1, t2, comps):
    a, b = np.broadcast_arrays(t1.v, t2.v)
    m = np.empty(a.shape)
    d = np.empty(a.shape)
    t = np.empty(a.shape)
    for k in np.ndindex(a.shape):
        m[k], d[k], t[k] = _between1(a[k], b[k], comps)
    return CalendarDurationValue(m, d, t)


def split(cd, units):
    """[u1,...] = split(calD, units): integer parts, largest unit first; 'time' returns a duration."""
    m, d, t = cd.m.copy(), cd.d.copy(), cd.t.copy()
    out = {}
    if "years" in units:
        out["years"] = np.trunc(m / 12)
        m = m - 12 * out["years"]
    if "quarters" in units:
        out["quarters"] = np.trunc(m / 3)
        m = m - 3 * out["quarters"]
    if "months" in units:
        out["months"] = m
    if "weeks" in units:
        out["weeks"] = np.trunc(d / 7)
        d = d - 7 * out["weeks"]
    if "days" in units:
        out["days"] = d
    res = []
    for u in units:
        if u == "time":
            res.append(DurationValue(t))
        else:
            res.append(_num(out[u]))
    return res
