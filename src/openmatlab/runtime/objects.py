"""Object values: containers.Map, datetime, duration (Epic #539).

Objects set ``is_object = True`` and implement a small protocol that the
evaluator dispatches to:

- ``index(args)``          -> Value            obj(args)
- ``assign(args, value)``  -> object            obj(args) = value
- ``get_prop(name)``       -> Value            obj.Name
- ``binop(op, other, reflected)`` -> Value or NotImplemented
- ``display_text()``       -> str

containers.Map is a handle: assignment copies the reference, so ``m2 = m``
then ``m2(k) = v`` is visible through ``m`` (MATLAB). datetime/duration are
value types backed by float64 arrays (datetime: days on MATLAB's datenum
axis; duration: days).
"""

from __future__ import annotations

import datetime as _dt
import math
from typing import Any, List, Tuple

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


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


def _scalar(v):
    return float(np.asarray(v.backend_buffer()).reshape(-1)[0])


def _num(x):
    a = np.asarray(x, dtype=float)
    return NDArrayValue(a.reshape(1, 1) if a.ndim == 0 else (a.reshape(1, -1) if a.ndim == 1 else a))


def _row_cell(items):
    from openmatlab.runtime.cell_value import CellValue

    if not items:
        return CellValue(rows=((),)) if False else _empty_row_cell()
    return CellValue(rows=(tuple(items),))


def _empty_row_cell():
    from openmatlab.runtime.cell_value import CellValue

    return CellValue(rows=())


# =====================================================================
# containers.Map
# =====================================================================
_NUMERIC_KEYS = ("double", "single", "int32", "uint32", "int64", "uint64")


class MapValue:
    is_object = True
    is_handle = True

    def __init__(self, key_type: str = "char", value_type: str = "any", uniform: bool = True):
        self.key_type = key_type
        self.value_type = value_type
        self.uniform = uniform
        self.data: dict = {}

    def matlab_class(self) -> str:
        return "containers.Map"

    # --- shape protocol (a Map is 1x1 in MATLAB's size(); length is Count)
    @property
    def shape(self):
        return (1, 1)

    def numel(self):
        return 1

    # --- keys
    def _key(self, v):
        if self.key_type == "char":
            if not _is_text(v):
                raise _err("Specified key type does not match the type expected for this container.", "MATLAB:Containers:TypeMismatch")
            return _text(v)
        if _is_text(v) or not hasattr(v, "backend_buffer"):
            raise _err("Specified key type does not match the type expected for this container.", "MATLAB:Containers:TypeMismatch")
        a = np.asarray(v.backend_buffer()).reshape(-1)
        if a.size != 1:
            raise _err("Only one key may be specified.", "MATLAB:Containers:Map:NonScalarKey")
        return float(a[0])

    def _key_value(self, k):
        return _cv(k) if isinstance(k, str) else _num(k)

    def sorted_keys(self):
        return sorted(self.data)

    def _check_value(self, v):
        vt = self.value_type
        if vt == "any":
            return v
        if vt == "char":
            if not _is_text(v):
                raise _err("Specified value type does not match the type expected for this container.", "MATLAB:Containers:TypeMismatch")
            return v
        if vt in ("double", "single", "logical") or vt.startswith(("int", "uint")):
            if _is_text(v) or not hasattr(v, "backend_buffer") or np.asarray(v.backend_buffer()).size != 1:
                raise _err("Specified value type does not match the type expected for this container.", "MATLAB:Containers:TypeMismatch")
        return v

    # --- object protocol
    def index(self, args):
        if len(args) != 1:
            raise _err("Only one level of indexing is supported by a containers.Map.", "MATLAB:Containers:Map:OneLevel")
        k = self._key(args[0])
        if k not in self.data:
            shown = k if isinstance(k, str) else (str(int(k)) if float(k).is_integer() else repr(k))
            raise _err(f"The specified key is not present in this container.", "MATLAB:Containers:Map:NoKey")
        return self.data[k]

    def assign(self, args, value):
        if len(args) != 1:
            raise _err("Only one level of indexing is supported by a containers.Map.", "MATLAB:Containers:Map:OneLevel")
        self.data[self._key(args[0])] = self._check_value(value)
        return self

    def get_prop(self, name):
        n = name.lower()
        if n == "count":
            return _num(float(len(self.data)))
        if n == "keytype":
            return _cv(self.key_type)
        if n == "valuetype":
            return _cv(self.value_type)
        raise _err(f"Unrecognized method, property, or field '{name}' for class 'containers.Map'.", "MATLAB:noSuchMethodOrField")

    def binop(self, op, other, reflected):
        if op in ("==", "~="):
            same = other is self
            return _bool(same if op == "==" else not same)
        return NotImplemented

    def display_text(self):
        return (f"  containers.Map with properties:\n\n"
                f"        Count: {len(self.data)}\n      KeyType: {self.key_type}\n    ValueType: {self.value_type}")


def _bool(b):
    return NDArrayValue(np.array([[bool(b)]]))


def _cell_items(v):
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(v, CellValue):
        r, c = v.shape
        return [v.get(i, j) for j in range(c) for i in range(r)]
    return None


def map_new(args):
    """containers.Map constructor (all documented forms used by core code)."""
    args = list(args)
    kt, vt, uniform = None, None, True
    opts = {}
    # trailing name-value pairs
    while len(args) >= 2 and _is_text(args[-2]) and _text(args[-2]).lower() in ("keytype", "valuetype", "uniformvalues"):
        opts[_text(args[-2]).lower()] = args[-1]
        args = args[:-2]
    if "keytype" in opts:
        kt = _text(opts["keytype"]).lower()
        if kt not in ("char",) + _NUMERIC_KEYS:
            raise _err(f"Unsupported KeyType '{kt}'.", "MATLAB:Containers:Map:UnsupportedKeyType")
    if "valuetype" in opts:
        vt = _text(opts["valuetype"]).lower()
    if "uniformvalues" in opts:
        uniform = bool(_scalar(opts["uniformvalues"]))
    keys, vals = [], []
    if args:
        if len(args) != 2:
            raise _err("containers.Map: expected (keys, values) or name-value options.", "MATLAB:Containers:Map:InvalidInput")
        ks = _cell_items(args[0])
        if ks is None:
            if _is_text(args[0]):
                ks = [args[0]]
            else:
                a = np.asarray(args[0].backend_buffer()).reshape(-1)
                ks = [_num(x) for x in a]
        vs = _cell_items(args[1])
        if vs is None:
            if len(ks) == 1:
                vs = [args[1]]
            else:
                b = np.asarray(args[1].backend_buffer()).reshape(-1)
                vs = [_num(x) for x in b]
        if len(ks) != len(vs):
            raise _err("The number of keys and values must be the same.", "MATLAB:Containers:Map:KeyValueNumberMismatch")
        keys, vals = ks, vs
        if kt is None:
            kt = "char" if all(_is_text(k) for k in ks) else "double"
        if vt is None:
            if all(_is_text(v) for v in vs):
                vt = "char"
            elif all(hasattr(v, "backend_buffer") and not _is_text(v) and np.asarray(v.backend_buffer()).size == 1 for v in vs):
                vt = "double"
            else:
                vt = "any"
    m = MapValue(kt or "char", vt or "any", uniform)
    for k, v in zip(keys, vals):
        m.assign([k], v)
    return m


# =====================================================================
# datetime / duration
# =====================================================================
_EPOCH_DN = 719529.0  # datenum of 1970-01-01


def datenum_from_parts(y, mo=1, d=1, h=0, mi=0, s=0):
    """MATLAB datenum from (possibly non-normalised) components."""
    y = float(y)
    mo = float(mo)
    # normalise months (MATLAB carries month overflow into years)
    yy = y + math.floor((mo - 1) / 12)
    mm = int((mo - 1) % 12) + 1
    base = _dt.date(int(yy), mm, 1).toordinal() + 366  # datenum of yy-mm-01
    return base + (float(d) - 1) + float(h) / 24 + float(mi) / 1440 + float(s) / 86400


def parts_from_datenum(dn):
    """(y, mo, d, h, mi, s) from a datenum, with seconds rounded to 0.1 ms."""
    day = math.floor(dn)
    frac = dn - day
    secs = round(frac * 86400, 4)  # datenum resolution near 7e5 is ~1e-5 s
    if secs >= 86400:
        day += 1
        secs -= 86400
    date = _dt.date.fromordinal(int(day) - 366)
    h = int(secs // 3600)
    mi = int((secs - h * 3600) // 60)
    s = secs - h * 3600 - mi * 60
    return date.year, date.month, date.day, h, mi, s


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def datestr_format(dn, fmt=None):
    y, mo, d, h, mi, s = parts_from_datenum(dn)
    if fmt is None:
        fmt = "dd-mmm-yyyy HH:MM:SS" if (h or mi or s) else "dd-mmm-yyyy"
    pm = "PM" in fmt or "AM" in fmt
    hh = (h % 12 or 12) if pm else h
    wd = int((math.floor(dn) - 2) % 7)
    toks = [("yyyy", f"{y:04d}"), ("yy", f"{y % 100:02d}"), ("mmmm", _dt.date(2000, mo, 1).strftime("%B")),
            ("mmm", _MONTHS[mo - 1]), ("mm", f"{mo:02d}"), ("dddd", _dt.date(2000, 1, 2 + wd).strftime("%A")),
            ("ddd", _DAYS[wd]), ("dd", f"{d:02d}"), ("HH", f"{hh:02d}"), ("MM", f"{mi:02d}"), ("SS", f"{int(s):02d}"),
            ("FFF", f"{int(round((s - int(s)) * 1000)):03d}"), ("AM", "AM" if h < 12 else "PM"), ("PM", "AM" if h < 12 else "PM")]
    out = ""
    i = 0
    while i < len(fmt):
        for t, rep in toks:
            if fmt.startswith(t, i):
                out += rep
                i += len(t)
                break
        else:
            out += fmt[i]
            i += 1
    return out


def _isostr(dn):
    return datestr_format(dn, "yyyy-mm-dd HH:MM:SS")


def parse_date_text(s: str) -> float:
    s = s.strip()
    fmts = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d-%b-%Y %H:%M:%S", "%d-%b-%Y",
            "%m/%d/%Y", "%Y/%m/%d", "%d-%b-%Y %H:%M", "%Y-%m-%dT%H:%M:%S"]
    for f in fmts:
        try:
            t = _dt.datetime.strptime(s, f)
            return datenum_from_parts(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)
        except ValueError:
            continue
    raise _err(f"Could not recognize the date/time text '{s}'. Use a format such as 'yyyy-MM-dd HH:mm:ss'.", "MATLAB:datetime:UnrecognizedDateStringSuggestLocale")


class _TimeBase:
    is_object = True

    def __init__(self, days):
        a = np.asarray(days, dtype=float)
        self.v = a.reshape(1, 1) if a.ndim == 0 else (a.reshape(1, -1) if a.ndim == 1 else a)

    @property
    def shape(self):
        return self.v.shape

    def numel(self):
        return int(self.v.size)

    def is_scalar(self):
        return self.v.size == 1

    def index(self, args):
        idx = []
        for a in args:
            if _is_text(a) and _text(a) == ":":
                idx.append(slice(None))
            else:
                b = np.asarray(a.backend_buffer())
                idx.append(np.flatnonzero(b.reshape(-1)) if b.dtype == bool else b.reshape(-1).astype(int) - 1)
        if len(idx) == 1:
            flat = self.v.reshape(-1, order="F")
            return type(self)._like(self, flat[idx[0]].reshape(1, -1) if self.v.shape[0] == 1 else flat[idx[0]].reshape(-1, 1))
        return type(self)._like(self, self.v[np.ix_(*[np.atleast_1d(np.arange(self.v.shape[k])[i]) for k, i in enumerate(idx)])])

    def assign(self, args, value):
        other = self._coerce(value)
        flat = self.v.reshape(-1, order="F").copy()
        b = np.asarray(args[0].backend_buffer()).reshape(-1).astype(int) - 1
        if b.max(initial=-1) >= flat.size:
            flat = np.concatenate([flat, np.full(b.max() + 1 - flat.size, np.nan)])
        flat[b] = other.v.reshape(-1)
        return type(self)._like(self, flat.reshape(1, -1))


class DatetimeValue(_TimeBase):
    def __init__(self, dn, fmt=None):
        super().__init__(dn)
        self.fmt = fmt

    @staticmethod
    def _like(src, v):
        return DatetimeValue(v, src.fmt)

    def matlab_class(self):
        return "datetime"

    def _coerce(self, v):
        if isinstance(v, DatetimeValue):
            return v
        if _is_text(v):
            return DatetimeValue(parse_date_text(_text(v)))
        raise _err("Value must be a datetime or date text.", "MATLAB:datetime:InvalidAssignment")

    def get_prop(self, name):
        n = name.lower()
        parts = [parts_from_datenum(x) for x in self.v.reshape(-1)]
        idx = {"year": 0, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5}
        if n in idx:
            return _num(np.array([p[idx[n]] for p in parts], float).reshape(self.v.shape))
        if n == "format":
            return _cv(self.fmt or "dd-MMM-yyyy")
        raise _err(f"Unrecognized property '{name}' for class 'datetime'.", "MATLAB:noSuchMethodOrField")

    def binop(self, op, other, reflected):
        o = other
        if op in ("+", "-"):
            if isinstance(o, DurationValue) or (not isinstance(o, _TimeBase) and hasattr(o, "backend_buffer") and not _is_text(o)):
                dv = o.v if isinstance(o, DurationValue) else np.asarray(o.backend_buffer(), float)
                if op == "-" and reflected:
                    raise _err("Subtraction of a datetime from a duration is not defined.", "MATLAB:datetime:DurationMinusDatetime")
                return DatetimeValue(self.v + dv if op == "+" else self.v - dv, self.fmt)
            if isinstance(o, DatetimeValue) and op == "-":
                return DurationValue(o.v - self.v if reflected else self.v - o.v)
            if isinstance(o, DatetimeValue):
                raise _err("Addition of two datetime values is not defined.", "MATLAB:datetime:DatetimeAddition")
        if op in ("<", ">", "<=", ">=", "==", "~="):
            ov = self._coerce(o).v
            a, b = (ov, self.v) if reflected else (self.v, ov)
            return NDArrayValue(_cmp(op, a, b))
        return NotImplemented

    def display_text(self):
        f = self.fmt
        def one(x):
            if np.isnan(x):
                return "NaT"
            if f:
                return datestr_format(x, _java_to_datestr(f))
            y, mo, d, h, mi, s = parts_from_datenum(x)
            return datestr_format(x, "dd-mmm-yyyy HH:MM:SS" if (h or mi or s) else "dd-mmm-yyyy")
        vals = [one(x) for x in self.v.reshape(-1)]
        if len(vals) == 1:
            return f"   {vals[0]}"
        return "   " + "   ".join(vals)


def _java_to_datestr(f):
    """datetime Format ('yyyy-MM-dd HH:mm:ss') -> datestr tokens."""
    rep = [("yyyy", "yyyy"), ("MMMM", "mmmm"), ("MMM", "mmm"), ("MM", "mm"), ("dd", "dd"), ("HH", "HH"), ("mm", "MM"), ("ss", "SS"), ("SSS", "FFF"), ("eeee", "dddd"), ("eee", "ddd")]
    out = ""
    i = 0
    while i < len(f):
        for a, b in rep:
            if f.startswith(a, i):
                out += b
                i += len(a)
                break
        else:
            out += f[i]
            i += 1
    return out


def _cmp(op, a, b):
    return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b, "==": a == b, "~=": a != b}[op]


class DurationValue(_TimeBase):
    """Elapsed time; stored in days."""

    def __init__(self, days, fmt="hh:mm:ss"):
        super().__init__(days)
        self.fmt = fmt

    @staticmethod
    def _like(src, v):
        return DurationValue(v, src.fmt)

    def matlab_class(self):
        return "duration"

    def _coerce(self, v):
        if isinstance(v, DurationValue):
            return v
        raise _err("Comparison is not defined between duration and non-duration values.", "MATLAB:duration:InvalidComparison")

    def get_prop(self, name):
        if name.lower() == "format":
            return _cv(self.fmt)
        raise _err(f"Unrecognized property '{name}' for class 'duration'.", "MATLAB:noSuchMethodOrField")

    def binop(self, op, other, reflected):
        o = other
        if isinstance(o, DatetimeValue):
            return o.binop(op, self, not reflected)
        if op in ("+", "-"):
            if not isinstance(o, DurationValue):
                if hasattr(o, "backend_buffer") and not _is_text(o):  # numbers are days (MATLAB)
                    o = DurationValue(np.asarray(o.backend_buffer(), float))
                else:
                    return NotImplemented
            a, b = (o.v, self.v) if reflected else (self.v, o.v)
            return DurationValue(a + b if op == "+" else a - b, self.fmt)
        if op in ("*", ".*") and not isinstance(o, DurationValue) and hasattr(o, "backend_buffer"):
            return DurationValue(self.v * np.asarray(o.backend_buffer(), float), self.fmt)
        if op in ("/", "./"):
            if isinstance(o, DurationValue) and not reflected:
                return _num(self.v / o.v)
            if not reflected and hasattr(o, "backend_buffer"):
                return DurationValue(self.v / np.asarray(o.backend_buffer(), float), self.fmt)
        if op in ("<", ">", "<=", ">=", "==", "~="):
            ov = self._coerce(o).v
            a, b = (ov, self.v) if reflected else (self.v, ov)
            return NDArrayValue(_cmp(op, a, b))
        return NotImplemented

    def display_text(self):
        def one(x):
            if np.isnan(x):
                return "NaN"
            f = self.fmt
            unit = {"d": (1, "days"), "h": (24, "hr"), "m": (1440, "min"), "s": (86400, "sec"), "y": (1 / 365.2425, "yrs")}
            if f in unit:
                k, u = unit[f]
                val = x * k
                txt = f"{val:.4g}" if not float(val).is_integer() else str(int(val))
                return f"{txt} {u}"
            secs = round(x * 86400, 3)
            sign = "-" if secs < 0 else ""
            secs = abs(secs)
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            s = secs % 60
            return f"{sign}{h:02d}:{m:02d}:{int(s):02d}"
        vals = [one(x) for x in self.v.reshape(-1)]
        return "   " + "   ".join(vals)
