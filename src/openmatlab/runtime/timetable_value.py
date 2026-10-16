"""timetable, timerange and withtol values (M10 T-E7, #697).

A ``TimetableValue`` is a ``TableValue`` whose rows are labelled by a column vector of row times
(``datetime`` or ``duration``) instead of row names. Row subscripts accept numbers, logicals, a
datetime/duration (rows at exactly that time), date text, a ``timerange`` or a ``withtol``.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from openmatlab.runtime.table_value import TableValue, _cv, _err, cellstr_row, is_text, text

_EPS = 1e-9  # days (~86 µs): row-time equality tolerance for floating datetime arithmetic


def is_time(v) -> bool:
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    return isinstance(v, (DatetimeValue, DurationValue))


def days(v) -> np.ndarray:
    return np.asarray(v.v, dtype=float).reshape(-1, order="F")


def like_times(src, d) -> object:
    """A column of row times of ``src``'s class/format holding ``d`` (days)."""
    return type(src)._like(src, np.asarray(d, dtype=float).reshape(-1, 1))


def coerce_time(v, like, fn="timetable"):
    """datetime/duration ``v``, or date text parsed against a datetime ``like``."""
    from openmatlab.runtime.objects import DatetimeValue, parse_date_text

    if is_time(v):
        if like is not None and type(v) is not type(like):
            raise _err(f"{fn}: row times are {like.matlab_class()}, not {v.matlab_class()}.",
                       "MATLAB:timetable:InvalidRowTimes")
        return v
    if is_text(v) and (like is None or isinstance(like, DatetimeValue)):
        try:
            return DatetimeValue(parse_date_text(text(v)))
        except Exception:
            raise _err(f"{fn}: could not recognize the date/time text '{text(v)}'.",
                       "MATLAB:datetime:ParseErr") from None
    raise _err(f"{fn}: expected a datetime or duration value.", "MATLAB:timetable:InvalidRowTimes")


class TimeRangeValue:
    """``timerange(start, end, intervalType)``; default interval is 'openright' (MATLAB)."""

    is_object = True
    native_subs = False

    def __init__(self, start, end, kind="openright"):
        self.start, self.end, self.kind = start, end, kind

    def matlab_class(self):
        return "timerange"

    @property
    def shape(self):
        return (1, 1)

    def numel(self):
        return 1

    def is_scalar(self):
        return True

    def mask(self, rt) -> np.ndarray:
        t = days(rt)
        a = float(days(coerce_time(self.start, rt, "timerange"))[0])
        b = float(days(coerce_time(self.end, rt, "timerange"))[0])
        lo = t >= a - _EPS if self.kind in ("closed", "openright", "closedleft") else t > a + _EPS
        hi = t <= b + _EPS if self.kind in ("closed", "openleft", "closedright") else t < b - _EPS
        return lo & hi

    def display_text(self):
        br = {"openright": "[ )", "closedleft": "[ )", "openleft": "( ]", "closedright": "( ]",
              "closed": "[ ]", "open": "( )"}[self.kind]

        def s(v):
            return v.display_text().strip() if hasattr(v, "display_text") else text(v)
        return f"  timetable timerange subscript:\n\n    Select timetable rows with times in the {br} interval:\n      Starting at, including:   {s(self.start)}\n      Ending at, excluding:     {s(self.end)}"


class WithTolValue:
    """``withtol(rowTimes, tol)``: rows within ``tol`` of any of ``rowTimes``."""

    is_object = True
    native_subs = False

    def __init__(self, times, tol):
        self.times, self.tol = times, tol

    def matlab_class(self):
        return "withtol"

    @property
    def shape(self):
        return (1, 1)

    def numel(self):
        return 1

    def is_scalar(self):
        return True

    def mask(self, rt) -> np.ndarray:
        t = days(rt)
        want = days(coerce_time(self.times, rt, "withtol"))
        tol = float(days(self.tol)[0])
        return np.any(np.abs(t[:, None] - want[None, :]) <= tol + _EPS, axis=1)

    def display_text(self):
        return f"  timetable withtol subscript:\n\n    Select timetable rows matching the specified times within tolerance {self.tol.display_text().strip()}"


class TimetableValue(TableValue):
    is_timetable = True

    def __init__(self, names: Sequence[str], cols: Sequence, nrows: int, rowtimes=None,
                 dimnames: Optional[Sequence[str]] = None, description: str = "", rownames=None):
        super().__init__(names, cols, nrows, None, description)
        self.rowtimes = rowtimes
        self.dimnames = list(dimnames) if dimnames else ["Time", "Variables"]
        if self.dimnames[0] in self.names:
            raise _err(f"Duplicate variable name '{self.dimnames[0]}': it is the row times name.",
                       "MATLAB:table:DuplicateDimnamesVarnames")

    def matlab_class(self) -> str:
        return "timetable"

    def copy(self, **kw) -> "TimetableValue":
        kw.pop("rownames", None)
        d = dict(names=self.names, cols=self.cols, nrows=self.nrows, rowtimes=self.rowtimes,
                 dimnames=self.dimnames, description=self.description)
        d.update(kw)
        if d["nrows"] != self.nrows and "rowtimes" not in kw:
            raise _err("Assignment that changes the number of timetable rows needs row times.",
                       "MATLAB:timetable:RowTimesRequired")
        return TimetableValue(**d)

    @property
    def time_name(self) -> str:
        return self.dimnames[0]

    def get_prop(self, name):
        if name == self.time_name:
            return self.rowtimes
        return super().get_prop(name)

    def properties(self):
        from openmatlab.runtime.struct_value import StructValue

        base = super().properties()
        items = [(f, base.get(f)) for f in base.fields if f != "RowNames"]
        items = [(f, cellstr_row(self.dimnames) if f == "DimensionNames" else v) for f, v in items]
        return StructValue.scalar(items + [("RowTimes", self.rowtimes)])

    def with_properties(self, p) -> "TimetableValue":
        out = self
        if p.has("RowTimes"):
            rt = p.get("RowTimes")
            if not is_time(rt) or rt.numel() != self.nrows:
                raise _err("The RowTimes property must be a datetime or duration vector with one time per row.",
                           "MATLAB:timetable:InvalidRowTimes")
            out = out.copy(rowtimes=like_times(rt, days(rt)))
        from openmatlab.runtime.table_value import texts

        if p.has("DimensionNames"):
            dn = texts(p.get("DimensionNames"))
            if not dn or len(dn) != 2:
                raise _err("The DimensionNames property must contain two names.", "MATLAB:table:IncorrectNumberOfDimNames")
            out = out.copy(dimnames=dn)
        names = texts(p.get("VariableNames")) if p.has("VariableNames") else out.names
        if names is None or len(names) != len(out.names):
            raise _err("The VariableNames property must contain one name for each variable in the table.",
                       "MATLAB:table:IncorrectNumberOfVarNames")
        desc = text(p.get("Description")) if p.has("Description") and is_text(p.get("Description")) else out.description
        return out.copy(names=names, description=desc)

    def row_sel(self, v, *, grow: bool = False) -> np.ndarray:
        if isinstance(v, (TimeRangeValue, WithTolValue)):
            return np.flatnonzero(v.mask(self.rowtimes))
        if is_time(v) or (is_text(v) and text(v) != ":"):
            want = days(coerce_time(v, self.rowtimes))
            t = days(self.rowtimes)
            out = [i for w in want for i in np.flatnonzero(np.abs(t - w) <= _EPS)]
            return np.array(out, dtype=int)
        return super().row_sel(v, grow=grow)

    def take_rows(self, ev, rows: np.ndarray) -> "TimetableValue":
        rows = np.asarray(rows, dtype=int)
        if len(rows) == self.nrows and np.array_equal(rows, np.arange(self.nrows)):
            return self
        from openmatlab.runtime.table_subs import ix
        from openmatlab.runtime.table_value import _idx_value

        iv = _idx_value(rows)
        cols = [ix(ev, c, [iv, None]) for c in self.cols]
        return self.copy(cols=cols, nrows=len(rows), rowtimes=like_times(self.rowtimes, days(self.rowtimes)[rows]))

    def as_table(self) -> TableValue:
        return TableValue([self.time_name] + self.names, [self.rowtimes] + self.cols, self.nrows,
                          description=self.description)

    def body_text(self) -> str:
        return self.as_table().body_text()

    def display_text(self) -> str:
        from openmatlab.host.display import _dims

        head = f"  {_dims(self.shape)} empty timetable" if self.numel() == 0 else f"  {_dims(self.shape)} timetable"
        body = self.body_text()
        return head + ("\n\n" + body if body and self.nrows else "")
