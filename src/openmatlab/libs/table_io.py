"""readtable / writetable / readcell / writecell for delimited text (M10 T-E4, Epic #694).

Fields are split with Python's ``csv`` module (quoted fields, embedded delimiters).
Each column is typed from its non-placeholder fields: all numeric -> double (empty
-> NaN), all dates in one supported form -> datetime (empty -> NaT), all
``hh:mm:ss`` or ``dd:hh:mm:ss`` duration text -> duration (empty -> NaN),
otherwise text (cellstr, or string with ``'TextType','string'``). Logical and
categorical text stay text until ``'Format'`` or ``VariableTypes`` says otherwise.

``'TreatAsMissing'`` (M17 CSV slice of #721) adds placeholder texts. A field whose
stripped text is one of those tokens is left out of typing and stored as the
standard missing value: NaN, NaT, ``''`` (cellstr), or ``<missing>`` (string).
The match is exact and case-sensitive. Spreadsheet files still raise.

``detectImportOptions`` / ``setvaropts`` (#1040) build a ``DelimitedTextImportOptions``
object and ``readtable(file, opts)`` imports with it. See ``libs/import_options.py``.

``'Range'`` (#1041) selects rows and columns of a delimited text file. The same
name-value is accepted by ``detectImportOptions``. Named ranges and spreadsheet
files are not. See ``docs/design/ISSUE-1041-readtable-range.md``.

``'Format'`` (#1042) is ``'auto'`` or a textscan column format on ``readtable``
for delimited text. See ``docs/design/ISSUE-1042-readtable-format.md``.

``'DatetimeType'`` (#1043) is ``'datetime'`` (default) or ``'text'`` on
``readtable`` and ``detectImportOptions`` for delimited text. ``'text'`` stores
a detected datetime column as char or string, following ``TextType``.
``'exceldatenum'`` is rejected for text. See
``docs/design/ISSUE-1043-readtable-datetimetype.md``.

``'VariableNamingRule'`` (#1044) is ``'modify'`` (default) or ``'preserve'``
on ``readtable`` and ``detectImportOptions`` for delimited text. ``'preserve'``
keeps the header text, including names that are not valid identifiers. See
``docs/design/ISSUE-1044-readtable-variablenamingrule.md``.

When that rewrite changes a header (#1045), the original column headers are
stored as ``Properties.VariableDescriptions``, a 1-by-N cell of the file text,
including headers that were already valid identifiers. No rewrite leaves the
property empty. See ``docs/design/ISSUE-1045-readtable-variabledescriptions.md``.

``'DurationType'`` (#1046) is ``'duration'`` (default) or ``'text'`` on
``readtable`` and ``detectImportOptions``. Duration text is
``hh:mm:ss`` or ``dd:hh:mm:ss`` (optional fraction, optional leading minus).
``setvaropts`` ``Type`` also accepts ``duration``, ``categorical``, and
``logical``. ``%T`` / ``%{fmt}T`` and ``%C`` are the textscan specifiers for
duration and categorical. See ``docs/design/ISSUE-1046-readtable-column-types.md``.

``'QuoteStrings'`` (#1047) on delimited-text ``writetable`` and ``writecell``
is ``'minimal'`` (default), ``'all'``, or ``'none'``. See
``docs/design/ISSUE-1047-writetable-quotestrings.md``.
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
# One family per pattern. Longer clock forms are listed before the shorter ones
# so ``HH:mm:ss`` is not read as ``HH:mm``.
_FIXED_DATES = [
    (re.compile(r"^\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}:\d{2}:\d{2}$"), "%Y-%m-%d %H:%M:%S", "yyyy-MM-dd HH:mm:ss"),
    (re.compile(r"^\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}:\d{2}$"), "%Y-%m-%d %H:%M", "yyyy-MM-dd HH:mm"),
    (re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"), "%Y-%m-%d", "yyyy-MM-dd"),
    (re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{4} \d{1,2}:\d{2}:\d{2}$"), "%d-%b-%Y %H:%M:%S", "dd-MMM-yyyy HH:mm:ss"),
    (re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{4} \d{1,2}:\d{2}$"), "%d-%b-%Y %H:%M", "dd-MMM-yyyy HH:mm"),
    (re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{4}$"), "%d-%b-%Y", "dd-MMM-yyyy"),
    (re.compile(r"^\d{4}/\d{1,2}/\d{1,2} \d{1,2}:\d{2}:\d{2}$"), "%Y/%m/%d %H:%M:%S", "yyyy/MM/dd HH:mm:ss"),
    (re.compile(r"^\d{4}/\d{1,2}/\d{1,2} \d{1,2}:\d{2}$"), "%Y/%m/%d %H:%M", "yyyy/MM/dd HH:mm"),
    (re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"), "%Y/%m/%d", "yyyy/MM/dd"),
]
_SLASH_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})(?: (\d{1,2}):(\d{2})(?::(\d{2}))?)?$")
# duration(TimeStrings): hh:mm:ss or dd:hh:mm:ss. A leading '+' is not a duration.
_DUR_AUTO = re.compile(r"^(-)?(\d+):(\d+):(\d+)(?::(\d+))?(?:\.(\d+))?$")
_TRUE_SYMBOLS = frozenset({"true", "t"})
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


def _delim_text(s):
    return _DELIMS.get(s.lower(), s.replace("\\t", "\t"))


def _delim(v):
    return _delim_text(text(v))


def _split_fields(lines, delim):
    if not lines:
        return []
    if delim == " ":
        return [ln.split() for ln in lines]
    return [list(r) for r in csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)]


_NAMING_RULES = ("modify", "preserve")


def _naming_rule_value(v):
    """``'modify'`` or ``'preserve'``. Any other value is an ``EvalError``."""
    if not is_text(v) or text(v).lower() not in _NAMING_RULES:
        raise _err("VariableNamingRule must be 'modify' or 'preserve'.",
                   "MATLAB:readtable:InvalidVariableNamingRule")
    return text(v).lower()


def _naming_rule(o):
    if "variablenamingrule" not in o:
        return "modify"
    return _naming_rule_value(o["variablenamingrule"])


def _naming_rule_for(name, fn, o):
    """Extension check first, so a spreadsheet still raises before the value is judged."""
    if "variablenamingrule" not in o:
        return "modify"
    _check_text_file(name, fn)
    return _naming_rule_value(o["variablenamingrule"])


def _preserved_name(s, k):
    """Header text as the variable name. A blank header cannot be a table name."""
    return s if s else f"Var{k + 1}"


def _names_from_header(header, ncol, rule="modify"):
    """Headers as variable names, with ``_1`` suffixes for duplicates.

    ``'modify'`` (the default) is the existing makeValidName path. ``'preserve'``
    keeps the header text, including names that are not valid identifiers.
    ``changed`` is true when that step differs from the file, before the suffix.
    The third value is the header text for each variable, before that step.
    """
    header = (list(header) + [""] * (ncol - len(header)))[:ncol]
    names, seen, changed = [], set(), False
    pick = _valid_name if rule != "preserve" else _preserved_name
    for k, h in enumerate(header):
        n = pick(h, k)
        changed = changed or n != h
        base, j = n, 1
        while n in seen:
            n = f"{base}_{j}"
            j += 1
        seen.add(n)
        names.append(n)
    return names, changed, header


def _headers_when_modified(changed, originals):
    """Original headers when a name was rewritten, and the warning that says so."""
    if not changed:
        return None
    _warn_modified_names()
    return list(originals)


def _warn_modified_names():
    from openmatlab.runtime import warnings as _w

    _w.emit("Column headers from the file were modified to make them valid MATLAB identifiers before "
            "creating variable names for the table. The original column headers are saved in the "
            "VariableDescriptions property.", "MATLAB:table:ModifiedAndSavedVarnames")


def _check_text_file(name, fn):
    ext = Path(name).suffix.lower()
    if ext in (".xls", ".xlsx", ".xlsm", ".xlsb", ".ods"):
        raise _err(f"{fn}: spreadsheet files are not supported; only delimited text files can be read or written.",
                   f"MATLAB:{fn}:UnsupportedFileType")


def _text_lines(name, fn):
    _check_text_file(name, fn)
    p = Path(name).expanduser()
    if not p.is_file():
        raise _err(f"Unable to find or open '{name}'. Check the path and filename or file permissions.",
                   "MATLAB:textio:textio:FileNotFound")
    return p, p.read_text(encoding=ENC).splitlines()


def _read_rows(name, fn, delim, header_lines):
    p, lines = _text_lines(name, fn)
    lines = [ln for ln in lines[header_lines:] if ln.strip()]
    if delim is None:
        delim = "," if p.suffix.lower() == ".csv" else _sniff(lines)
    return _split_fields(lines, delim)


def _sniff(lines):
    head = lines[:5]
    for d in (",", "\t", ";", "|"):
        counts = {ln.count(d) for ln in head}
        if head and len(counts) == 1 and counts != {0}:
            return d
    return " "


class _TextRange:
    """One ``Range`` window. Rows and columns are 1-based; a None end reads through the data."""

    def __init__(self, r1, r2, c1, c2, trim_leading, columns_only):
        self.r1 = r1
        self.r2 = r2
        self.c1 = c1
        self.c2 = c2
        self.trim_leading = trim_leading
        self.columns_only = columns_only


_RANGE_FORMS = ("Range must be of the form 'A1' (cell), 'A:B' (column-select), '1:5' (row-select), "
                "'A1:B5' (rectangle-select), [row col], or [r1 c1 r2 c2]. "
                "Named ranges are spreadsheet-only.")
_CELL_RE = re.compile(r"^([A-Za-z]+)(\d+)$")
_RECT_RE = re.compile(r"^([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)$")
_COLS_RE = re.compile(r"^([A-Za-z]+):([A-Za-z]+)$")
_ROWS_RE = re.compile(r"^(\d+):(\d+)$")


def _range_err(msg=None):
    raise _err(msg or _RANGE_FORMS, "MATLAB:textio:textio:InvalidRange")


def _col_number(letters):
    n = 0
    for ch in letters:
        if not ch.isalpha():
            return None
        n = n * 26 + (ord(ch.upper()) - 64)
    return n or None


def _ordered(a, b):
    return (a, b) if a <= b else (b, a)


def _parse_range_text(s):
    m = _RECT_RE.match(s)
    if m:
        c1, r1 = _col_number(m.group(1)), int(m.group(2))
        c2, r2 = _col_number(m.group(3)), int(m.group(4))
        if not c1 or not c2 or r1 < 1 or r2 < 1:
            _range_err()
        r1, r2 = _ordered(r1, r2)
        c1, c2 = _ordered(c1, c2)
        return _TextRange(r1, r2, c1, c2, False, False)
    m = _CELL_RE.match(s)
    if m:
        c, r = _col_number(m.group(1)), int(m.group(2))
        if not c or r < 1:
            _range_err()
        return _TextRange(r, None, c, None, False, False)
    m = _COLS_RE.match(s)
    if m:
        c1, c2 = _col_number(m.group(1)), _col_number(m.group(2))
        if not c1 or not c2:
            _range_err()
        c1, c2 = _ordered(c1, c2)
        return _TextRange(None, None, c1, c2, False, True)
    m = _ROWS_RE.match(s)
    if m:
        r1, r2 = int(m.group(1)), int(m.group(2))
        if r1 < 1 or r2 < 1:
            _range_err()
        r1, r2 = _ordered(r1, r2)
        return _TextRange(r1, r2, 1, None, True, False)
    _range_err()


def _parse_range(v):
    """``None`` is an empty range, the same as omitting ``Range``."""
    if is_text(v):
        s = text(v).strip()
        return None if s == "" else _parse_range_text(s)
    if hasattr(v, "backend_buffer") and not getattr(v, "is_object", False):
        a = np.asarray(v.backend_buffer()).reshape(-1)
        if a.dtype == np.bool_ or np.iscomplexobj(a) or a.size not in (2, 4):
            _range_err()
        try:
            a = np.asarray(a, dtype=float)
        except (TypeError, ValueError):
            _range_err()
        if not np.all(np.isfinite(a)) or np.any(a != np.trunc(a)) or np.any(a < 1):
            _range_err()
        nums = [int(x) for x in a]
        if len(nums) == 2:
            return _TextRange(nums[0], None, nums[1], None, False, False)
        r1, c1, r2, c2 = nums
        return _TextRange(*_ordered(r1, r2), *_ordered(c1, c2), False, False)
    _range_err()


def _col_has(rows, col):
    return any(col < len(r) and r[col].strip() != "" for r in rows)


def _resolve_cols(rows, rng):
    width = max((len(r) for r in rows), default=0)
    if rng.c2 is not None:
        return rng.c1, rng.c2
    if rng.trim_leading:
        start = rng.c1 - 1
        while start < width and not _col_has(rows, start):
            start += 1
        if start >= width:
            return None
        end = width - 1
        while end > start and not _col_has(rows, end):
            end -= 1
        return start + 1, end + 1
    end = width - 1
    while end >= rng.c1 - 1 and not _col_has(rows, end):
        end -= 1
    if end < rng.c1 - 1:
        return None
    return rng.c1, end + 1


def _slice_fields(row, c1, c2):
    part = list(row[c1 - 1:c2])
    need = c2 - c1 + 1
    if len(part) < need:
        part.extend([""] * (need - len(part)))
    return part


def _row_indexes(lines, rng, nheader, fn):
    if rng.columns_only:
        idxs = [i for i in range(max(nheader, 0), len(lines)) if lines[i].strip()]
    else:
        if nheader:
            _range_err("Supplying 'NumHeaderLines' with 'Range' is only supported when the range "
                       "value is of the form 'A:B' (column-select).")
        if rng.r1 > len(lines):
            _range_err(f"{fn}: range starts past the end of the file.")
        last = len(lines) if rng.r2 is None else min(rng.r2, len(lines))
        idxs = [i for i in range(rng.r1 - 1, last) if lines[i].strip()]
    if not idxs:
        _range_err(f"{fn}: the specified range contains no data.")
    return idxs


def _ranged_rows(name, fn, delim, nheader, rng):
    """Content rows inside ``rng``. Blank lines are skipped, then columns are sliced.

    Returns ``(rows, line_numbers, delim, c1, c2, data_end)``. Line numbers are
    1-based. ``data_end`` is the last physical line of a bounded window, or None
    to read through the end of the file.
    """
    p, lines = _text_lines(name, fn)
    idxs = _row_indexes(lines, rng, nheader, fn)
    kept = [lines[i] for i in idxs]
    if delim is None:
        delim = "," if p.suffix.lower() == ".csv" else _sniff(kept)
    rows = _split_fields(kept, delim)
    bounds = _resolve_cols(rows, rng)
    if bounds is None:
        _range_err(f"{fn}: the specified range contains no data.")
    c1, c2 = bounds
    return [_slice_fields(r, c1, c2) for r in rows], [i + 1 for i in idxs], delim, c1, c2, rng.r2


def _ymd_dn(y, mo, d, h=0, mi=0, s=0):
    from openmatlab.runtime.objects import datenum_from_parts
    import datetime as _dt

    try:
        _dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s))
    except ValueError:
        return None
    return datenum_from_parts(int(y), int(mo), int(d), int(h), int(mi), float(s))


def _date_hit(s):
    """One field as a fixed format, or as both slash readings.

    A slash hit is ``('slash', suffix, month_first, day_first)``. Either reading
    is ``None`` when that month/day pair is not a real date. ``suffix`` is the
    clock part of the format, shared by both readings.
    """
    from openmatlab.runtime.objects import datenum_from_parts
    import datetime as _dt

    for rx, pyfmt, mfmt in _FIXED_DATES:
        if not rx.match(s):
            continue
        raw = s.replace("T", " ", 1) if pyfmt.startswith("%Y-%m-%d") else s
        try:
            t = _dt.datetime.strptime(raw, pyfmt)
        except ValueError:
            return None
        dn = datenum_from_parts(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)
        return ("fixed", mfmt, dn)
    m = _SLASH_DATE.match(s)
    if not m:
        return None
    a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if m.group(4) is None:
        h = mi = sec = 0
        suffix = ""
    else:
        h, mi = int(m.group(4)), int(m.group(5))
        sec = 0 if m.group(6) is None else int(m.group(6))
        if not (0 <= h <= 23 and 0 <= mi <= 59 and 0 <= sec <= 59):
            return None
        suffix = " HH:mm" if m.group(6) is None else " HH:mm:ss"
    month_first, day_first = _ymd_dn(y, a, b, h, mi, sec), _ymd_dn(y, b, a, h, mi, sec)
    if month_first is None and day_first is None:
        return None
    return ("slash", suffix, month_first, day_first)


def _dates_one_format(hits):
    """True when every hit is the same fixed format, or one slash order."""
    if not hits or len({h[0] for h in hits}) != 1:
        return False
    if hits[0][0] == "fixed":
        return len({h[1] for h in hits}) == 1
    if len({h[1] for h in hits}) != 1:
        return False
    month_only = any(h[2] is not None and h[3] is None for h in hits)
    day_only = any(h[3] is not None and h[2] is None for h in hits)
    return not (month_only and day_only)


def _prefer_day_first(hits):
    month_only = any(h[2] is not None and h[3] is None for h in hits)
    day_only = any(h[3] is not None and h[2] is None for h in hits)
    return day_only and not month_only


def _hit_value(hit, day_first):
    if hit[0] == "fixed":
        return hit[2], hit[1]
    suffix = hit[1]
    if day_first:
        return hit[3], "dd/MM/yyyy" + suffix
    return hit[2], "MM/dd/yyyy" + suffix


def _date(s):
    """``(datenum, format)`` for one field. An ambiguous slash date is month-first."""
    hit = _date_hit(s)
    if hit is None:
        return None
    return _hit_value(hit, hit[0] == "slash" and hit[2] is None)


def _is_one_date(values):
    hits = [_date_hit(v) for v in values]
    return bool(hits) and all(h is not None for h in hits) and _dates_one_format(hits)


def _datetime_column_values(vals, tokens):
    """Datenums for a column, using one slash order when the column agrees."""
    hits, present, failed = [], [], False
    for v in vals:
        if v == "" or v in tokens:
            hits.append(None)
            continue
        hit = _date_hit(v)
        hits.append(hit)
        if hit is None:
            failed = True
        else:
            present.append(hit)
    agree = bool(present) and not failed and _dates_one_format(present)
    day_first = _prefer_day_first(present) if agree and present[0][0] == "slash" else False
    dns, fmt = [], None
    for v, hit in zip(vals, hits):
        if v == "" or v in tokens or hit is None:
            dns.append(np.nan)
            continue
        if agree:
            dn, fmt = _hit_value(hit, day_first)
        else:
            dn, one = _hit_value(hit, hit[0] == "slash" and hit[2] is None)
            fmt = fmt or one
        dns.append(dn)
    return dns, fmt or "yyyy-MM-dd"


def _duration_days_auto(s):
    """Days for ``hh:mm:ss`` or ``dd:hh:mm:ss``, or None.

    ``duration(TimeStrings)`` accepts those two forms, an optional fractional
    second, and a leading minus. A leading ``+`` is not accepted. Two-part
    text (``hh:mm`` or ``mm:ss``) needs an input format.
    """
    if not s or s[0] == "+":
        return None
    m = _DUR_AUTO.fullmatch(s)
    if not m:
        return None
    sign = -1.0 if m.group(1) else 1.0
    first, second, third = (int(m.group(i)) for i in (2, 3, 4))
    extra = float(f"0.{m.group(6)}") if m.group(6) else 0.0
    if m.group(5) is None:
        days, hour, minute, sec = 0, first, second, third + extra
    else:
        days, hour, minute, sec = first, second, third, int(m.group(5)) + extra
    return sign * (days + hour / 24.0 + minute / 1440.0 + sec / 86400.0)


def _split_duration_format(fmt):
    """``(base, fractional digits)`` for a duration ``InputFormat``, or None."""
    if fmt == "hh:mm":
        return "hh:mm", 0
    matched = re.fullmatch(r"(dd:hh:mm:ss|hh:mm:ss|mm:ss)\.(S{1,9})", fmt)
    if matched:
        return matched.group(1), len(matched.group(2))
    if fmt in ("dd:hh:mm:ss", "hh:mm:ss", "mm:ss"):
        return fmt, 0
    return None


def _parse_formatted_duration(s, base, frac_n):
    if not s or s[0] == "+":
        return None
    sign = -1.0 if s[0] == "-" else 1.0
    body = s[1:] if s[0] == "-" else s
    if frac_n:
        matched = re.fullmatch(r"(\d+(?::\d+)*)\.(\d+)", body)
        if not matched or not (1 <= len(matched.group(2)) <= frac_n):
            return None
        bits = matched.group(1).split(":")
        extra = float("0." + matched.group(2))
    else:
        if "." in body or not re.fullmatch(r"\d+(?::\d+)+", body):
            return None
        bits = body.split(":")
        extra = 0.0
    need = {"dd:hh:mm:ss": 4, "hh:mm:ss": 3, "mm:ss": 2, "hh:mm": 2}[base]
    if len(bits) != need:
        return None
    nums = [int(p) for p in bits]
    if base == "dd:hh:mm:ss":
        days, hour, minute, sec = nums[0], nums[1], nums[2], nums[3] + extra
    elif base == "hh:mm:ss":
        days, hour, minute, sec = 0, nums[0], nums[1], nums[2] + extra
    elif base == "mm:ss":
        days, hour, minute, sec = 0, 0, nums[0], nums[1] + extra
    else:
        days, hour, minute, sec = 0, nums[0], nums[1], extra
    return sign * (days + hour / 24.0 + minute / 1440.0 + sec / 86400.0)


def _valid_name(s, k):
    n = re.sub(r"\s+(\w)", lambda m: m.group(1).upper(), s.strip())  # matlab.lang.makeValidName
    n = re.sub(r"\W", "_", n)
    if not n:
        return f"Var{k + 1}"
    if not n[0].isalpha():
        n = "x" + n
    return n[:63]


def _placeholders(v):
    """``'TreatAsMissing'`` tokens. Exact match after stripping; case-sensitive."""
    from openmatlab.runtime import string_array as sa
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    def bad():
        raise _err("TreatAsMissing must be a character vector, a string array, or a cell array of "
                   "character vectors.", "MATLAB:readtable:InvalidTreatAsMissing")

    def piece(e):
        if isinstance(e, CharValue) and not getattr(e, "is_string", False):
            if len(e.rows) > 1:
                bad()
            return e.text.strip()
        if getattr(e, "is_string", False):
            if e.numel() != 1:
                bad()
            g = sa.to_grid(e).reshape(-1)[0]
            if g is None:
                bad()
            return str(g).strip()
        bad()

    if isinstance(v, CharValue) and not getattr(v, "is_string", False):
        if len(v.rows) > 1:
            bad()
        return frozenset({v.text.strip()})
    if getattr(v, "is_string", False):
        out = []
        for g in sa.to_grid(v).reshape(-1, order="F"):
            if g is None:
                bad()
            out.append(str(g).strip())
        return frozenset(out)
    if isinstance(v, CellValue):
        return frozenset(piece(v.rows[r][c]) for c in range(v.shape[1]) for r in range(v.shape[0]))
    bad()


def _kind(fields, tokens, text_type):
    """Column type ``readtable`` would pick.

    double, datetime, duration, char, or string. Logical words and repeated
    labels stay text; those types are selected with ``Type`` or ``Format``.
    """
    vals = [f.strip() for f in fields]
    present = [v for v in vals if v != "" and v not in tokens]
    if present and all(_NUM.match(v) for v in present):
        return "double"
    if present and _is_one_date(present):
        return "datetime"
    if present and all(_duration_days_auto(v) is not None for v in present):
        return "duration"
    if not present and vals:
        return "double"
    return "string" if text_type == "string" else "char"


_DATETIME_TYPES = ("datetime", "text", "exceldatenum")


def _datetime_type(o):
    """``'datetime'`` or ``'text'``. ``'exceldatenum'`` is not valid for text files.

    Call :func:`_check_text_file` first when the name is present, so a spreadsheet
    extension still raises ``UnsupportedFileType`` before this check.
    """
    if "datetimetype" not in o:
        return "datetime"
    v = o["datetimetype"]
    if not is_text(v) or text(v).lower() not in _DATETIME_TYPES:
        raise _err("DatetimeType must be 'datetime', 'text', or 'exceldatenum'.",
                   "MATLAB:readtable:InvalidDatetimeType")
    if text(v).lower() == "exceldatenum":
        raise _err("DatetimeType 'exceldatenum' is valid only for spreadsheet files.",
                   "MATLAB:readtable:ExcelDateNumText")
    return text(v).lower()


def _datetime_type_for(name, fn, o):
    if "datetimetype" not in o:
        return "datetime"
    _check_text_file(name, fn)
    return _datetime_type(o)


def _dated_kind(kind, datetime_type, text_type, duration_type="duration"):
    """Datetime or duration becomes text when that name-value is ``'text'``."""
    text_kind = "string" if text_type == "string" else "char"
    if kind == "datetime" and datetime_type == "text":
        return text_kind
    if kind == "duration" and duration_type == "text":
        return text_kind
    return kind


_DURATION_TYPES = ("duration", "text")


def _duration_type(o):
    """``'duration'`` or ``'text'``.

    Call :func:`_check_text_file` first when the name is present, so a spreadsheet
    extension still raises ``UnsupportedFileType`` before this check.
    """
    if "durationtype" not in o:
        return "duration"
    v = o["durationtype"]
    if not is_text(v) or text(v).lower() not in _DURATION_TYPES:
        raise _err("DurationType must be 'duration' or 'text'.",
                   "MATLAB:readtable:InvalidDurationType")
    return text(v).lower()


def _duration_type_for(name, fn, o):
    if "durationtype" not in o:
        return "duration"
    _check_text_file(name, fn)
    return _duration_type(o)


def _column_as(fields, kind, tokens):
    """Import one column as ``kind``. Tokens and blank numeric/datetime fields are standard missing.

    A forced ``double`` or ``datetime`` stores NaN or NaT when a field does not convert.
    A forced ``duration`` stores NaN. A forced ``logical`` stores false for a blank,
    a placeholder, or any text that is not a true symbol. A forced ``categorical``
    stores ``<undefined>`` for a blank or a placeholder. Text keeps the original
    field unless its stripped text is a token.
    """
    from openmatlab.runtime.cell_value import CellValue

    tokens = frozenset() if tokens is None else tokens
    vals = [f.strip() for f in fields]
    if kind == "double":
        out = [np.nan if (v == "" or v in tokens or not _NUM.match(v)) else float(v) for v in vals]
        return NDArrayValue(np.array(out, dtype=float).reshape(-1, 1))
    if kind == "datetime":
        from openmatlab.runtime.objects import DatetimeValue

        dn, fmt = _datetime_column_values(vals, tokens)
        return DatetimeValue(np.array(dn, dtype=float).reshape(-1, 1), fmt)
    if kind == "duration":
        return _duration_value(vals, tokens, None)
    if kind == "logical":
        bits = [v.lower() in _TRUE_SYMBOLS and v != "" and v not in tokens for v in vals]
        return NDArrayValue(np.array(bits, dtype=bool).reshape(-1, 1))
    if kind == "categorical":
        return _categorical_value(fields, tokens)
    hit = [f.strip() in tokens for f in fields]
    if kind == "string":
        from openmatlab.runtime import string_array as sa

        data = [None if h else f for h, f in zip(hit, fields)]
        return sa.make(np.array(data, dtype=object).reshape(-1, 1))
    if not fields:
        return CellValue(rows=())
    return CellValue(rows=tuple((_cv(""),) if h else (_cv(f),) for h, f in zip(hit, fields)))


def _duration_value(vals, tokens, fmt):
    from openmatlab.runtime.objects import DurationValue

    spec = None if not fmt else _split_duration_format(fmt)
    days = []
    for v in vals:
        if v == "" or v in tokens:
            days.append(np.nan)
            continue
        got = _duration_days_auto(v) if spec is None else _parse_formatted_duration(v, spec[0], spec[1])
        days.append(np.nan if got is None else got)
    return DurationValue(np.array(days, dtype=float).reshape(-1, 1), "hh:mm:ss")


def _categorical_value(fields, tokens):
    """Categories are the sorted nonempty labels, the same order ``categorical`` uses."""
    from openmatlab.runtime.categorical_value import CategoricalValue

    labels = []
    for f in fields:
        v = f.strip()
        if v == "" or v in tokens or v == "<undefined>":
            labels.append(None)
        else:
            labels.append(v)
    cats = sorted({x for x in labels if x is not None})
    index = {c: i + 1 for i, c in enumerate(cats)}
    codes = [0 if x is None else index[x] for x in labels]
    return CategoricalValue(np.array(codes, dtype=np.int64).reshape(-1, 1), cats)


def _column(fields, text_type, tokens=None, datetime_type="datetime", duration_type="duration"):
    tokens = frozenset() if tokens is None else tokens
    kind = _dated_kind(_kind(fields, tokens, text_type), datetime_type, text_type, duration_type)
    return _column_as(fields, kind, tokens)


# ----------------------------------------------------------------- Format (#1042)
class _Conv:
    """One textscan conversion in a ``readtable`` ``Format`` string."""

    def __init__(self, skip=False, width=None, prec=None, kind="double", fmt=None, unquote=False, base=10):
        self.skip = skip
        self.width = width
        self.prec = prec
        self.kind = kind
        self.fmt = fmt
        self.unquote = unquote
        self.base = base


_FLOAT_SPEC = {"f": "double", "f32": "single", "f64": "double", "n": "double"}
_INT_SPEC = {
    "d": ("int32", 10), "d8": ("int8", 10), "d16": ("int16", 10), "d32": ("int32", 10), "d64": ("int64", 10),
    "u": ("uint32", 10), "u8": ("uint8", 10), "u16": ("uint16", 10), "u32": ("uint32", 10), "u64": ("uint64", 10),
    "x": ("uint64", 16), "xu8": ("uint8", 16), "xu16": ("uint16", 16), "xu32": ("uint32", 16), "xu64": ("uint64", 16),
    "xs8": ("int8", 16), "xs16": ("int16", 16), "xs32": ("int32", 16), "xs64": ("int64", 16),
    "b": ("uint64", 2), "bu8": ("uint8", 2), "bu16": ("uint16", 2), "bu32": ("uint32", 2), "bu64": ("uint64", 2),
    "bs8": ("int8", 2), "bs16": ("int16", 2), "bs32": ("int32", 2), "bs64": ("int64", 2),
}
_TEXT_SPEC = {"s": False, "q": True}
_REJECT_SPEC = {"c": "%c"}
_CONV_KEYS = sorted([*_FLOAT_SPEC, *_INT_SPEC, *_TEXT_SPEC, *_REJECT_SPEC, "D", "T", "C"], key=len, reverse=True)


def _bad_format(detail):
    raise _err(f"Invalid 'Format' value. {detail}", "MATLAB:readtable:InvalidFormat")


def _format_value(v):
    if not is_text(v):
        _bad_format("Format must be 'auto' or a character vector or string scalar of textscan conversion specifiers.")
    s = text(v).strip()
    if s.lower() == "auto":
        return "auto"
    return _parse_format(s)


def _parse_format(s):
    """Whitespace-separated textscan conversions. Literal text between them is rejected."""
    out, i, n = [], 0, len(s)
    while i < n:
        if s[i].isspace():
            i += 1
            continue
        if s[i] != "%":
            _bad_format(f"unrecognized text at '{s[i:i + 12]}'.")
        i += 1
        skip = False
        if i < n and s[i] == "*":
            skip = True
            i += 1
        width = None
        if i < n and s[i].isdigit():
            j = i
            while j < n and s[j].isdigit():
                j += 1
            width = int(s[i:j])
            if width < 1:
                _bad_format("a field width must be a positive integer.")
            i = j
        prec = None
        if i < n and s[i] == ".":
            j = i + 1
            if j >= n or not s[j].isdigit():
                _bad_format("a precision must be digits after the decimal point.")
            while j < n and s[j].isdigit():
                j += 1
            prec = int(s[i + 1:j])
            i = j
        conv, i = _match_conv(s, i)
        conv.skip, conv.width, conv.prec = skip, width, prec
        if prec is not None and conv.kind not in ("double", "single"):
            _bad_format("precision is only valid on a floating-point conversion.")
        out.append(conv)
    if not out:
        _bad_format("Format has no conversion specifiers.")
    if all(c.skip for c in out):
        _bad_format("Format has no output columns.")
    return out


def _match_conv(s, i):
    if i >= len(s):
        _bad_format("Format ends at a '%'.")
    if s[i] == "{":
        j = s.find("}", i + 1)
        if j < 0 or j + 1 >= len(s) or s[j + 1] not in "DT":
            _bad_format("a %{...} conversion must end with D or T.")
        body = s[i + 1:j]
        if s[j + 1] == "T":
            if _split_duration_format(body) is None:
                _bad_format(f"duration format '{body}' is not a duration InputFormat.")
            return _Conv(kind="duration", fmt=body, unquote=True), j + 2
        return _Conv(kind="datetime", fmt=body, unquote=True), j + 2
    if s[i] == "[":
        _bad_format("Format scansets are not supported for delimited text.")
    for key in _CONV_KEYS:
        if s.startswith(key, i):
            if key in _REJECT_SPEC:
                _bad_format(f"Format specifier '%{key}' is not supported for delimited text.")
            if key == "D":
                return _Conv(kind="datetime", unquote=True), i + 1
            if key == "T":
                return _Conv(kind="duration", unquote=True), i + 1
            if key == "C":
                return _Conv(kind="categorical", unquote=True), i + 1
            if key in _FLOAT_SPEC:
                return _Conv(kind=_FLOAT_SPEC[key]), i + len(key)
            if key in _TEXT_SPEC:
                return _Conv(kind="char", unquote=_TEXT_SPEC[key]), i + len(key)
            kind, base = _INT_SPEC[key]
            return _Conv(kind=kind, base=base), i + len(key)
    _bad_format(f"unrecognized conversion at '{s[i:i + 8]}'.")


def _limit_decimals(raw, prec):
    m = re.match(r"^(\s*[+-]?)(\d*)(?:\.(\d*))?(.*)$", raw)
    if not m or m.group(3) is None:
        return raw
    sign, whole, frac, rest = m.group(1), m.group(2), m.group(3), m.group(4)
    kept = frac[:prec]
    exp = ""
    if len(frac) <= prec:
        em = re.match(r"\s*([eE][+-]?\d+)", rest)
        if em:
            exp = em.group(1)
    if prec == 0:
        return f"{sign}{whole}{exp}"
    return f"{sign}{whole}.{kept}{exp}"


def _unquote(s):
    """``%q`` / ``%D``: drop a wrapping quote pair and turn ``""`` into ``"``."""
    if not s.startswith('"'):
        return s
    out, i = [], 1
    while i < len(s):
        if s[i] == '"':
            if i + 1 < len(s) and s[i + 1] == '"':
                out.append('"')
                i += 2
                continue
            return "".join(out) + s[i + 1:].replace('"', "")
        out.append(s[i])
        i += 1
    return "".join(out)


def _field_text(raw, conv):
    if conv.width is not None:
        raw = raw[:conv.width]
    if conv.prec is not None:
        raw = _limit_decimals(raw, conv.prec)
    if conv.unquote:
        raw = _unquote(raw)
    return raw


def _int_literal(s, base):
    t = s.strip()
    sign = -1.0 if t[:1] == "-" else 1.0
    if t[:1] in "+-":
        t = t[1:]
    pref = "0x" if base == 16 else "0b"
    if base != 10 and t.lower().startswith(pref):
        t = t[2:]
    digits = "0123456789abcdef" if base == 16 else "01"
    if not t or any(c not in digits for c in t.lower()):
        return np.nan
    return sign * int(t, base)


def _single_column(fields, tokens):
    out = []
    for f in fields:
        v = f.strip()
        out.append(np.nan if (v == "" or v in tokens or not _NUM.match(v)) else float(v))
    return NDArrayValue(np.array(out, dtype=np.float32).reshape(-1, 1))


def _int_column(fields, conv, tokens):
    from openmatlab.numerics.intclass import INT_CLASSES, saturate

    vals = []
    for f in fields:
        v = f.strip()
        if v == "" or v in tokens:
            vals.append(np.nan)
        elif conv.base == 10:
            vals.append(float(v) if _NUM.match(v) else np.nan)
        else:
            vals.append(_int_literal(v, conv.base))
    arr = saturate(np.array(vals, dtype=float), INT_CLASSES[conv.kind]).reshape(-1, 1)
    return NDArrayValue(arr)


def _format_datetime(fields, fmt, tokens):
    from openmatlab.libs.datetime_arrays import java_to_strptime
    from openmatlab.runtime.objects import DatetimeValue, datenum_from_parts
    import datetime as _dt

    if not fmt:
        vals = []
        for f in fields:
            v = f.strip()
            vals.append("" if v.lower() == "nat" else v)
        dn, used = _datetime_column_values(vals, tokens)
        return DatetimeValue(np.array(dn, dtype=float).reshape(-1, 1), used)
    dn, used = [], fmt
    py = java_to_strptime(fmt)
    for f in fields:
        v = f.strip()
        if v == "" or v.lower() == "nat" or v in tokens:
            dn.append(np.nan)
            continue
        try:
            t = _dt.datetime.strptime(v, py)
        except ValueError:
            dn.append(np.nan)
            continue
        dn.append(datenum_from_parts(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6))
    return DatetimeValue(np.array(dn, dtype=float).reshape(-1, 1), used or "yyyy-MM-dd")


def _convert_fields(fields, conv, tokens, text_type, datetime_type="datetime", duration_type="duration"):
    if conv.kind == "char":
        return _column_as(fields, "string" if text_type == "string" else "char", tokens)
    if conv.kind == "single":
        return _single_column(fields, tokens)
    if conv.kind == "datetime":
        if datetime_type == "text":
            return _column_as(fields, "string" if text_type == "string" else "char", tokens)
        return _format_datetime(fields, conv.fmt, tokens)
    if conv.kind == "duration":
        if duration_type == "text":
            return _column_as(fields, "string" if text_type == "string" else "char", tokens)
        return _duration_value([f.strip() for f in fields], tokens, conv.fmt)
    if conv.kind == "categorical":
        return _categorical_value(fields, tokens)
    if conv.base != 10 or conv.kind != "double":
        return _int_column(fields, conv, tokens)
    return _column_as(fields, "double", tokens)


def _names_for(header, n, supplied, rule="modify"):
    """Variable names, and original headers when a name was rewritten."""
    if supplied is not None:
        names = texts(supplied)
        if names is None or len(names) != n:
            raise _err("The VariableNames property must contain one name for each variable in the table.",
                       "MATLAB:table:IncorrectNumberOfVarNames")
        return names, None
    if header:
        names, changed, originals = _names_from_header(header, n, rule)
        return names, _headers_when_modified(changed, originals)
    return [f"Var{k + 1}" for k in range(n)], None


def _kept_lines(name, fn, delim, hdr, rng):
    p, lines = _text_lines(name, fn)
    if rng is None:
        kept = [ln for ln in lines[hdr:] if ln.strip()]
    else:
        kept = [lines[i] for i in _row_indexes(lines, rng, hdr, fn)]
    if delim is None:
        delim = "," if p.suffix.lower() == ".csv" else _sniff(kept)
    return kept, delim


def _quote_flags(line, delim):
    """True when a csv field starts with a quote. Length matches ``csv.reader`` for ordinary lines."""
    flags, i, n = [], 0, len(line)
    if n == 0:
        return [False]
    while i <= n:
        if i == n:
            flags.append(False)
            break
        if line[i] == '"':
            flags.append(True)
            i += 1
            while i < n:
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            while i < n and line[i] != delim:
                i += 1
            if i >= n:
                break
            i += 1
            continue
        flags.append(False)
        j = line.find(delim, i)
        if j < 0:
            break
        i = j + 1
        if i == n:
            flags.append(False)
            break
    return flags


def _split_detailed(lines, delim):
    """Field text plus whether that field was quoted. Text matches the ordinary splitter."""
    if not lines:
        return []
    if delim == " ":
        out = []
        for ln in lines:
            row = []
            for tok in ln.split():
                row.append((tok, len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"'))
            out.append(row)
        return out
    values = _split_fields(lines, delim)
    out = []
    for ln, vals in zip(lines, values):
        flags = _quote_flags(ln, delim)
        if len(flags) != len(vals):
            flags = [False] * len(vals)
        out.append(list(zip(vals, flags)))
    return out


def _slice_pairs(rows, c1, c2):
    need = c2 - c1 + 1
    out = []
    for r in rows:
        part = list(r[c1 - 1:c2])
        if len(part) < need:
            part.extend([("", False)] * (need - len(part)))
        out.append(part)
    return out


def _auto_kind(pairs, tokens, text_type):
    """Previous ``readtable`` rule: a blank or a quoted field makes the column text."""
    text_kind = "string" if text_type == "string" else "char"
    if not pairs:
        return text_kind  # no data rows: same empty column as readtable without Format
    present, saw_blank, saw_quote = [], False, False
    for f, q in pairs:
        v = f.strip()
        if q:
            saw_quote = True
        if v in tokens:
            continue
        if v == "":
            saw_blank = True
            continue
        present.append(v)
    if saw_quote or saw_blank:
        return text_kind
    if present and all(_NUM.match(v) for v in present):
        return "double"
    if present and _is_one_date(present):
        return "datetime"
    if not present:
        return "double"
    return text_kind


def _read_opts(o):
    delim = _delim(o["delimiter"]) if "delimiter" in o else None
    hdr = int(np.asarray(o.get("numheaderlines", o.get("headerlines")).backend_buffer()).reshape(-1)[0]) \
        if ("numheaderlines" in o or "headerlines" in o) else 0
    readnames = _flag(o["readvariablenames"]) if "readvariablenames" in o else True
    tt = text(o["texttype"]).lower() if "texttype" in o else "char"
    if tt not in ("char", "string"):
        raise _err("TextType must be 'char' or 'string'.", "MATLAB:readtable:InvalidTextType")
    tokens = _placeholders(o["treatasmissing"]) if "treatasmissing" in o else frozenset()
    rng = _parse_range(o["range"]) if "range" in o else None
    supplied = o["variablenames"] if "variablenames" in o else None
    return delim, hdr, readnames, tt, tokens, rng, supplied


def _window_rows(rows, rng):
    if rng is None:
        return rows
    bounds = _resolve_cols(rows, rng)
    if bounds is None:
        _range_err("readtable: the specified range contains no data.")
    return [_slice_fields(r, *bounds) for r in rows]


def _read_spec(kept, delim, rng, spec, readnames, tt, tokens, supplied, dt, rule="modify", du="duration"):
    rows = _window_rows(_split_fields(kept, delim), rng)
    header = rows.pop(0) if (readnames and rows) else None
    nspec = len(spec)
    data = [(list(r) + [""] * (nspec - len(r)))[:nspec] for r in rows]
    out_idx = [i for i, conv in enumerate(spec) if not conv.skip]
    cols = [_convert_fields([_field_text(r[i], spec[i]) for r in data], spec[i], tokens, tt, dt, du)
            for i in out_idx]
    picked = None if header is None else [header[i] if i < len(header) else "" for i in out_idx]
    names, descs = _names_for(picked, len(out_idx), supplied, rule)
    return (TableValue(names, cols, len(data), variable_descriptions=descs),)


def _read_auto(kept, delim, rng, readnames, tt, tokens, supplied, dt, rule="modify"):
    """``'Format','auto'``. A blank or a quoted field forces text. Unequal field counts are an error.

    ``12abc`` stays one field. Splitting the numeric prefix off the trailing text would insert a
    column the header row cannot name; the R2020a note's split is not reproduced.
    """
    detailed = _split_detailed(kept, delim)
    if rng is not None:
        bounds = _resolve_cols([[t for t, _q in r] for r in detailed], rng)
        if bounds is None:
            _range_err("readtable: the specified range contains no data.")
        detailed = _slice_pairs(detailed, *bounds)
    if not detailed:
        raise _err("readtable: the file has no data to import with 'Format','auto'.", "MATLAB:readtable:NoData")
    width = len(detailed[0])
    if any(len(r) != width for r in detailed):
        raise _err("readtable: lines do not have the same number of delimiters.",
                   "MATLAB:readtable:UnequalDelimiters")
    header = [t for t, _q in detailed.pop(0)] if readnames else None
    cols = [_column_as([r[k][0] for r in detailed],
                       _dated_kind(_auto_kind([r[k] for r in detailed], tokens, tt), dt, tt), tokens)
            for k in range(width)]
    names, descs = _names_for(header, width, supplied, rule)
    return (TableValue(names, cols, len(detailed), variable_descriptions=descs),)


def _read_formatted(name, o):
    """``readtable(file, 'Format', ...)`` for delimited text. The file is not opened for a spreadsheet extension."""
    _check_text_file(name, "readtable")
    rule = _naming_rule(o)
    spec = _format_value(o["format"])
    delim, hdr, readnames, tt, tokens, rng, supplied = _read_opts(o)
    dt = _datetime_type(o)
    du = _duration_type(o)
    kept, delim = _kept_lines(name, "readtable", delim, hdr, rng)
    if spec == "auto":
        return _read_auto(kept, delim, rng, readnames, tt, tokens, supplied, dt, rule)
    return _read_spec(kept, delim, rng, spec, readnames, tt, tokens, supplied, dt, rule, du)


def _readtable(args, *, nargout=1):
    if len(args) >= 2 and getattr(args[1], "is_import_options", False):
        from openmatlab.libs.import_options import read_with_options

        return read_with_options(args)
    name, o = _opts(args, "readtable", ("delimiter", "readvariablenames", "variablenames", "numheaderlines",
                                         "texttype", "filetype", "headerlines", "treatasmissing", "range", "format",
                                         "datetimetype", "durationtype", "variablenamingrule"))
    if "filetype" in o and text(o["filetype"]).lower() not in ("text", "delimitedtext"):
        raise _err("readtable: only 'FileType','text' is supported.", "MATLAB:readtable:UnsupportedFileType")
    if "format" in o:
        return _read_formatted(name, o)
    rule = _naming_rule_for(name, "readtable", o)
    delim = _delim(o["delimiter"]) if "delimiter" in o else None
    hdr = int(np.asarray(o.get("numheaderlines", o.get("headerlines")).backend_buffer()).reshape(-1)[0]) \
        if ("numheaderlines" in o or "headerlines" in o) else 0
    readnames = _flag(o["readvariablenames"]) if "readvariablenames" in o else True
    tt = text(o["texttype"]).lower() if "texttype" in o else "char"
    if tt not in ("char", "string"):
        raise _err("TextType must be 'char' or 'string'.", "MATLAB:readtable:InvalidTextType")
    dt = _datetime_type_for(name, "readtable", o)
    du = _duration_type_for(name, "readtable", o)
    tokens = _placeholders(o["treatasmissing"]) if "treatasmissing" in o else frozenset()
    rng = None
    if "range" in o:
        _check_text_file(name, "readtable")
        rng = _parse_range(o["range"])
    if rng is None:
        rows = _read_rows(name, "readtable", delim, hdr)
    else:
        rows = _ranged_rows(name, "readtable", delim, hdr, rng)[0]
    header = rows.pop(0) if (readnames and rows) else None
    ncol = max([len(r) for r in rows] + [len(header) if header else 0])
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    names, descs = _names_for(header, ncol, o.get("variablenames"), rule)
    cols = [_column([r[k] for r in rows], tt, tokens, dt, du) for k in range(ncol)]
    return (TableValue(names, cols, len(rows), variable_descriptions=descs),)


# ----------------------------------------------------------------- writing
_QUOTE_MODES = ("minimal", "all", "none")
# 'all' encloses these and no others. 'minimal' looks at the characters instead.
_QUOTED_KINDS = frozenset({"text", "categorical", "datetime", "duration"})


def _quote_mode(name, fn, o):
    """``minimal`` (default), ``all``, or ``none``. A spreadsheet extension is rejected first."""
    _check_text_file(name, fn)
    if "quotestrings" not in o:
        return "minimal"
    v = o["quotestrings"]
    if not is_text(v) or text(v).lower() not in _QUOTE_MODES:
        raise _err("QuoteStrings must be 'minimal', 'all', or 'none'.", f"MATLAB:{fn}:InvalidQuoteStrings")
    return text(v).lower()


def _enclose(s):
    """Wrap a field. An embedded double quote is doubled, which ``readtable`` already reads."""
    return '"' + s.replace('"', '""') + '"'


class _Quoter:
    def __init__(self, delim, mode):
        self.delim = delim
        self.mode = mode

    def __call__(self, s, kind="text"):
        if self.mode == "none" or kind == "missing":
            return s
        if self.mode == "all":
            return _enclose(s) if kind in _QUOTED_KINDS else s
        if any(ch in s for ch in (self.delim, '"', "\n", "\r")):
            return _enclose(s)
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


def _cells_of(v, n, q):
    """A table variable -> n rows of field strings (one per column of the variable)."""
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue, _java_to_datestr, datestr_format

    if isinstance(v, CellValue):
        return [[_scalar_field(e, q) for e in row] for row in v.rows]
    if getattr(v, "is_string", False):
        from openmatlab.runtime import string_array as sa

        g = np.asarray(sa.to_grid(v), dtype=object).reshape(n, -1)
        return [[q("", "missing") if x is None else q(str(x), "text") for x in row] for row in g]
    if getattr(v, "is_categorical", False):
        def one(s):
            if s == "<undefined>":
                return q("", "missing")
            return q(s, "categorical")

        labs = np.array([one(s) for s in v.labels()], dtype=object)
        return [list(row) for row in labs.reshape(v.shape, order="F")]
    if isinstance(v, DatetimeValue):
        fmt = _java_to_datestr(v.fmt) if v.fmt else None

        def one(x):
            if np.isnan(x):
                return q("", "missing")
            if fmt:
                raw = datestr_format(x, fmt)
            else:
                raw = datestr_format(x, "dd-mmm-yyyy HH:MM:SS" if x != int(x) else "dd-mmm-yyyy")
            return q(raw, "datetime")
        return [[one(x) for x in row] for row in v.v.reshape(n, -1)]
    if isinstance(v, DurationValue):
        return [[q(v._like(v, np.array([[x]])).display_text().strip(), "duration") for x in row]
                for row in v.v.reshape(n, -1)]
    if isinstance(v, CharValue):
        rows = list(v.rows) if v.rows else [""]
        return [[q(r, "text")] for r in rows]
    if hasattr(v, "backend_buffer") and not getattr(v, "is_object", False):
        a = np.asarray(v.backend_buffer())
        if np.iscomplexobj(a):
            return [[q(_num_text(z.real) + ("+" if z.imag >= 0 else "-") + _num_text(abs(z.imag)) + "i", "other")
                     for z in row] for row in a.reshape(n, -1)]
        return [[q(_num_text(x), "other") for x in row] for row in a.reshape(n, -1)]
    raise _err(f"writetable: variables of class '{v.matlab_class()}' cannot be written to a text file.",
               "MATLAB:table:write:UnsupportedVarType")


def _scalar_field(e, q):
    from openmatlab.runtime.char_value import CharValue

    if getattr(e, "is_missing_value", False):
        return q("", "missing")
    if getattr(e, "is_string", False):
        from openmatlab.runtime import string_array as sa

        g = np.asarray(sa.to_grid(e), dtype=object).reshape(-1)
        if g.size == 1 and g[0] is not None:
            return q(str(g[0]), "text")
        return q("", "missing")
    if isinstance(e, CharValue):
        return q(e.text, "text")
    if hasattr(e, "backend_buffer") and not getattr(e, "is_object", False):
        a = np.asarray(e.backend_buffer()).reshape(-1)
        if a.size == 0:
            return q("", "other")
        if a.size == 1:
            return q(_num_text(a[0]), "other")
    if getattr(e, "is_object", False) and getattr(e, "numel", lambda: 0)() == 1:
        return _cells_of(e, 1, q)[0][0]
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
    mode = _quote_mode(name, "writetable", o)
    delim = _delim(o["delimiter"]) if "delimiter" in o else ("\t" if Path(name).suffix.lower() == ".tsv" else ",")
    q = _Quoter(delim, mode)
    hdr = _flag(o["writevariablenames"]) if "writevariablenames" in o else True
    rown = (_flag(o["writerownames"]) if "writerownames" in o else False) and bool(t.rownames)
    body = [[] for _ in range(t.nrows)]
    head = ["Row"] if rown else []
    if rown:
        for r in range(t.nrows):
            body[r].append(q(t.rownames[r], "text"))
    for nm, v in zip(t.names, t.cols):
        if getattr(v, "is_table", False):
            raise _err("writetable: nested tables cannot be written to a text file.",
                       "MATLAB:table:write:NestedTableNotSupported")
        cells = _cells_of(v, t.nrows, q)
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
    mode = _quote_mode(name, "writecell", o)
    delim = _delim(o["delimiter"]) if "delimiter" in o else ","
    q = _Quoter(delim, mode)
    if getattr(c, "nd", False):
        raise _err("writecell: only 2-D cell arrays can be written.", "MATLAB:writecell:NDCell")
    _write(name, "writecell", [[_scalar_field(e, q) for e in row] for row in c.rows], delim)
    return ()


def register(builtins) -> None:
    builtins.update(readtable=_readtable, writetable=_writetable, readcell=_readcell, writecell=_writecell)
    from openmatlab.libs.import_options import register as _register_import_options

    _register_import_options(builtins)
