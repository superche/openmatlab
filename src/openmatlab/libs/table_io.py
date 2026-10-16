"""readtable / writetable / readcell / writecell for delimited text (M10 T-E4, Epic #694).

Fields are split with Python's ``csv`` module (quoted fields, embedded delimiters).
Each column is typed from its non-empty fields: all numeric -> double (empty -> NaN),
all dates -> datetime (empty -> NaT), otherwise text (cellstr, or string with
``'TextType','string'``).
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import numpy as np

from openmatlab.libs.file_builtins import ENC
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.table_value import TableValue, _cv, _err, is_text, text, texts

_NUM = re.compile(r"^[+-]?((\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?|Inf|NaN)$", re.I)
_DATE_FORMS = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "%Y-%m-%d", "yyyy-MM-dd"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}$"), None, "yyyy-MM-dd HH:mm:ss"),
    (re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$"), "%d-%b-%Y", "dd-MMM-yyyy"),
    (re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4} \d{2}:\d{2}:\d{2}$"), "%d-%b-%Y %H:%M:%S", "dd-MMM-yyyy HH:mm:ss"),
]
_DELIMS = {"comma": ",", "tab": "\t", "\\t": "\t", "semi": ";", "semicolon": ";", "bar": "|", "space": " "}


def _opts(args, fn, allowed):
    if not args or not is_text(args[0]):
        raise _err(f"{fn}: the file name must be a character vector or string scalar.", f"MATLAB:{fn}:InvalidFileName")
    rest = list(args[1:])
    if len(rest) % 2:
        raise _err(f"{fn}: name-value arguments must come in pairs.", "MATLAB:InputParser:ParamMissingValue")
    out = {}
    for k in range(0, len(rest), 2):
        if not is_text(rest[k]) or text(rest[k]).lower() not in allowed:
            nm = text(rest[k]) if is_text(rest[k]) else "?"
            raise _err(f"'{nm}' is not a recognized parameter. For a list of valid name-value pair arguments, see "
                       f"the documentation for {fn}.", "MATLAB:textio:textio:UnknownParameter")
        out[text(rest[k]).lower()] = rest[k + 1]
    return text(args[0]), out


def _flag(v):
    return bool(np.asarray(v.backend_buffer()).reshape(-1)[0]) if hasattr(v, "backend_buffer") else bool(v)


def _delim(v):
    d = text(v)
    return _DELIMS.get(d.lower(), d.replace("\\t", "\t"))


def _check_text_file(name, fn):
    ext = Path(name).suffix.lower()
    if ext in (".xls", ".xlsx", ".xlsm", ".xlsb", ".ods"):
        raise _err(f"{fn}: spreadsheet files are not supported; only delimited text files can be read or written.",
                   f"MATLAB:{fn}:UnsupportedFileType")


def _read_rows(name, fn, delim, header_lines):
    _check_text_file(name, fn)
    p = Path(name).expanduser()
    if not p.is_file():
        raise _err(f"Unable to find or open '{name}'. Check the path and filename or file permissions.",
                   "MATLAB:textio:textio:FileNotFound")
    raw = p.read_text(encoding=ENC)
    lines = raw.splitlines()[header_lines:]
    lines = [ln for ln in lines if ln.strip()]
    if delim is None:
        delim = "," if p.suffix.lower() == ".csv" else _sniff(lines)
    if delim == " ":
        return [ln.split() for ln in lines]
    return [list(r) for r in csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)]


def _sniff(lines):
    head = lines[:5]
    for d in (",", "\t", ";", "|"):
        counts = {ln.count(d) for ln in head}
        if head and len(counts) == 1 and counts != {0}:
            return d
    return " "


def _date(s):
    from openmatlab.runtime.objects import datenum_from_parts
    import datetime as _dt

    for rx, pyfmt, mfmt in _DATE_FORMS:
        if rx.match(s):
            try:
                t = _dt.datetime.strptime(s.replace("T", " "), pyfmt or "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
            return datenum_from_parts(t.year, t.month, t.day, t.hour, t.minute, t.second), mfmt
    return None


def _valid_name(s, k):
    n = re.sub(r"\s+(\w)", lambda m: m.group(1).upper(), s.strip())  # matlab.lang.makeValidName
    n = re.sub(r"\W", "_", n)
    if not n:
        return f"Var{k + 1}"
    if not n[0].isalpha():
        n = "x" + n
    return n[:63]


def _column(fields, text_type):
    from openmatlab.runtime.cell_value import CellValue

    vals = [f.strip() for f in fields]
    present = [v for v in vals if v != ""]
    if present and all(_NUM.match(v) for v in present):
        return NDArrayValue(np.array([float(v) if v else np.nan for v in vals], dtype=float).reshape(-1, 1))
    if present:
        dates = [_date(v) for v in present]
        if all(d is not None for d in dates) and len({d[1] for d in dates}) == 1:
            from openmatlab.runtime.objects import DatetimeValue

            dn = [(_date(v)[0] if v else np.nan) for v in vals]
            return DatetimeValue(np.array(dn, dtype=float).reshape(-1, 1), dates[0][1])
    if not present and vals:
        return NDArrayValue(np.full((len(vals), 1), np.nan))
    if text_type == "string":
        from openmatlab.runtime import string_array as sa

        return sa.make(np.array(list(fields), dtype=object).reshape(-1, 1))
    return CellValue(rows=tuple((_cv(f),) for f in fields)) if fields else CellValue(rows=())


def _readtable(args, *, nargout=1):
    name, o = _opts(args, "readtable", ("delimiter", "readvariablenames", "variablenames", "numheaderlines",
                                         "texttype", "filetype", "headerlines"))
    if "filetype" in o and text(o["filetype"]).lower() not in ("text", "delimitedtext"):
        raise _err("readtable: only 'FileType','text' is supported.", "MATLAB:readtable:UnsupportedFileType")
    delim = _delim(o["delimiter"]) if "delimiter" in o else None
    hdr = int(np.asarray(o.get("numheaderlines", o.get("headerlines")).backend_buffer()).reshape(-1)[0]) \
        if ("numheaderlines" in o or "headerlines" in o) else 0
    readnames = _flag(o["readvariablenames"]) if "readvariablenames" in o else True
    tt = text(o["texttype"]).lower() if "texttype" in o else "char"
    if tt not in ("char", "string"):
        raise _err("TextType must be 'char' or 'string'.", "MATLAB:readtable:InvalidTextType")
    rows = _read_rows(name, "readtable", delim, hdr)
    header = rows.pop(0) if (readnames and rows) else None
    ncol = max([len(r) for r in rows] + [len(header) if header else 0])
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    if "variablenames" in o:
        names = texts(o["variablenames"])
        if names is None or len(names) != ncol:
            raise _err("The VariableNames property must contain one name for each variable in the table.",
                       "MATLAB:table:IncorrectNumberOfVarNames")
    elif header:
        header = header + [""] * (ncol - len(header))
        names, seen = [], set()
        changed = False
        for k, h in enumerate(header):
            n = _valid_name(h, k)
            changed = changed or n != h
            base, j = n, 1
            while n in seen:
                n = f"{base}_{j}"
                j += 1
            seen.add(n)
            names.append(n)
        if changed:
            from openmatlab.runtime import warnings as _w

            _w.emit("Column headers from the file were modified to make them valid MATLAB identifiers before "
                    "creating variable names for the table. The original column headers are saved in the "
                    "VariableDescriptions property.", "MATLAB:table:ModifiedAndSavedVarnames")
    else:
        names = [f"Var{k + 1}" for k in range(ncol)]
    cols = [_column([r[k] for r in rows], tt) for k in range(ncol)]
    return (TableValue(names, cols, len(rows)),)


# ----------------------------------------------------------------- writing
def _quote(s, delim):
    if any(ch in s for ch in (delim, '"', "\n", "\r")):
        return '"' + s.replace('"', '""') + '"'
    return s


def _num_text(x):
    if isinstance(x, (bool, np.bool_)):
        return "1" if x else "0"
    x = float(x)
    if np.isnan(x):
        return ""
    if np.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    return "%.15g" % x


def _cells_of(v, n, delim):
    """A table variable -> n rows of field strings (one per column of the variable)."""
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue, _java_to_datestr, datestr_format

    if isinstance(v, CellValue):
        return [[_scalar_field(e, delim) for e in row] for row in v.rows]
    if getattr(v, "is_string", False):
        from openmatlab.runtime import string_array as sa

        g = np.asarray(sa.to_grid(v), dtype=object).reshape(n, -1)
        return [["" if x is None else _quote(str(x), delim) for x in row] for row in g]
    if getattr(v, "is_categorical", False):
        labs = np.array(["" if s == "<undefined>" else s for s in v.labels()], dtype=object)
        return [[_quote(x, delim) for x in row] for row in labs.reshape(v.shape, order="F")]
    if isinstance(v, DatetimeValue):
        fmt = _java_to_datestr(v.fmt) if v.fmt else None

        def one(x):
            if np.isnan(x):
                return ""
            if fmt:
                return datestr_format(x, fmt)
            return datestr_format(x, "dd-mmm-yyyy HH:MM:SS" if x != int(x) else "dd-mmm-yyyy")
        return [[one(x) for x in row] for row in v.v.reshape(n, -1)]
    if isinstance(v, DurationValue):
        return [[_quote(v._like(v, np.array([[x]])).display_text().strip(), delim) for x in row]
                for row in v.v.reshape(n, -1)]
    if isinstance(v, CharValue):
        rows = v.text.split("\n") if v.shape[0] > 1 else [v.text]
        return [[_quote(r, delim)] for r in rows]
    if hasattr(v, "backend_buffer") and not getattr(v, "is_object", False):
        a = np.asarray(v.backend_buffer())
        if np.iscomplexobj(a):
            return [[_num_text(z.real) + ("+" if z.imag >= 0 else "-") + _num_text(abs(z.imag)) + "i" for z in row]
                    for row in a.reshape(n, -1)]
        return [[_num_text(x) for x in row] for row in a.reshape(n, -1)]
    raise _err(f"writetable: variables of class '{v.matlab_class()}' cannot be written to a text file.",
               "MATLAB:table:write:UnsupportedVarType")


def _scalar_field(e, delim):
    from openmatlab.runtime.char_value import CharValue

    if getattr(e, "is_missing_value", False):
        return ""
    if isinstance(e, CharValue) or getattr(e, "is_string", False):
        return _quote(text(e) if is_text(e) else "", delim)
    if hasattr(e, "backend_buffer") and not getattr(e, "is_object", False):
        a = np.asarray(e.backend_buffer()).reshape(-1)
        if a.size == 0:
            return ""
        if a.size == 1:
            return _num_text(a[0])
    if getattr(e, "is_object", False) and getattr(e, "numel", lambda: 0)() == 1:
        return _cells_of(e, 1, delim)[0][0]
    raise _err("Cell elements must be scalars or text to be written to a text file.",
               "MATLAB:table:write:NestedCellNotSupported")


def _write(name, fn, lines, delim):
    _check_text_file(name, fn)
    try:
        Path(name).expanduser().write_text("".join(delim.join(r) + "\n" for r in lines), encoding=ENC)
    except OSError:
        raise _err(f"Unable to open file '{name}' for writing.", f"MATLAB:{fn}:FileOpenError") from None


def _writetable(args, *, nargout=1):
    if not args or not getattr(args[0], "is_table", False):
        raise _err("First input must be a table.", "MATLAB:writetable:FirstArgNotTable")
    t = args[0]
    rest = list(args[1:])
    name = "table.txt"
    if rest and is_text(rest[0]) and (len(rest) % 2 == 1):
        name = text(rest.pop(0))
    _n, o = _opts([_cv(name)] + rest, "writetable", ("delimiter", "writevariablenames", "writerownames",
                                                       "filetype", "quotestrings"))
    delim = _delim(o["delimiter"]) if "delimiter" in o else ("\t" if Path(name).suffix.lower() == ".tsv" else ",")
    hdr = _flag(o["writevariablenames"]) if "writevariablenames" in o else True
    rown = (_flag(o["writerownames"]) if "writerownames" in o else False) and bool(t.rownames)
    body = [[] for _ in range(t.nrows)]
    head = ["Row"] if rown else []
    if rown:
        for r in range(t.nrows):
            body[r].append(_quote(t.rownames[r], delim))
    for nm, v in zip(t.names, t.cols):
        if getattr(v, "is_table", False):
            raise _err("writetable: nested tables cannot be written to a text file.",
                       "MATLAB:table:write:NestedTableNotSupported")
        cells = _cells_of(v, t.nrows, delim)
        w = len(cells[0]) if cells else 1
        head += [nm] if w == 1 else [f"{nm}_{k + 1}" for k in range(w)]
        for r in range(t.nrows):
            body[r] += cells[r]
    _write(name, "writetable", ([head] if hdr else []) + body, delim)
    return ()


def _readcell(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.missing_value import MissingValue

    name, o = _opts(args, "readcell", ("delimiter", "numheaderlines", "filetype"))
    delim = _delim(o["delimiter"]) if "delimiter" in o else None
    hdr = int(np.asarray(o["numheaderlines"].backend_buffer()).reshape(-1)[0]) if "numheaderlines" in o else 0
    rows = _read_rows(name, "readcell", delim, hdr)
    ncol = max((len(r) for r in rows), default=0)

    def cell(f):
        s = f.strip()
        if s == "":
            return MissingValue()
        if _NUM.match(s):
            return NDArrayValue(np.array([[float(s)]]))
        d = _date(s)
        if d is not None:
            from openmatlab.runtime.objects import DatetimeValue

            return DatetimeValue(np.array([[d[0]]]), d[1])
        return _cv(f)

    return (CellValue(rows=tuple(tuple(cell(r[k]) if k < len(r) else MissingValue() for k in range(ncol))
                                 for r in rows)),)


def _writecell(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    if not args or not isinstance(args[0], CellValue):
        raise _err("First input must be a cell array.", "MATLAB:writecell:FirstArgNotCell")
    c = args[0]
    rest = list(args[1:])
    name = text(rest.pop(0)) if rest and is_text(rest[0]) and len(rest) % 2 == 1 else "cell.txt"
    _n, o = _opts([_cv(name)] + rest, "writecell", ("delimiter", "filetype", "quotestrings"))
    delim = _delim(o["delimiter"]) if "delimiter" in o else ","
    if getattr(c, "nd", False):
        raise _err("writecell: only 2-D cell arrays can be written.", "MATLAB:writecell:NDCell")
    _write(name, "writecell", [[_scalar_field(e, delim) for e in row] for row in c.rows], delim)
    return ()


def register(builtins) -> None:
    builtins.update(readtable=_readtable, writetable=_writetable, readcell=_readcell, writecell=_writecell)
