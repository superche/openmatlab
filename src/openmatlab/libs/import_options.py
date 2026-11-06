"""Delimited-text import options (#1040).

Public ``detectImportOptions`` / ``setvaropts`` / ``readtable(file, opts)`` for
delimited text only. The object is the same type later issues extend
(``VariableImportOptions`` for per-column fields, ``DelimitedTextImportOptions``
for file-level fields). This slice honors delimiter, names, types, a variable
subset, the names line, and per-variable ``TreatAsMissing``.

Detection uses the same strict column rule as ``readtable`` (see ``_kind``),
so ``readtable(file, detectImportOptions(file))`` matches ``readtable(file)``.
``setvaropts`` accepts ``Type`` (double, char, string, datetime, duration,
categorical, logical) and ``TreatAsMissing``. Any other variable option is
an error.

``Range`` (#1041) is a name-value of ``detectImportOptions`` and ``readtable``.
The window is stored as internal line and column bounds, not as a ``Range`` or
``DataLines`` property. ``readtable(file, opts)`` honors those bounds.
``readtable`` ``'Format'`` is #1042 and is not a property of this object.
``detectImportOptions`` accepts ``DatetimeType`` (#1043) and stores the result
in ``VariableTypes``: ``'text'`` makes a detected datetime column ``char`` or
``string``. There is no ``DatetimeType`` property. ``readtable(file, opts)``
still rejects ``Format`` and ``DatetimeType``. ``setvaropts`` does not accept
``DatetimeType``.

``VariableNamingRule`` (#1044) is a property. ``detectImportOptions`` records
``'modify'`` or ``'preserve'`` and detects names under that rule.
``readtable(file, opts)`` imports those names. Changing the property does not
rewrite them. ``readtable(file, opts, 'VariableNamingRule', ...)`` is still an
unknown parameter.

When detection rewrites a header (#1045), the original header text is kept
internally and ``readtable(file, opts)`` stores it on
``Properties.VariableDescriptions``. It is not a property of this object, and
the read does not emit the modified-name warning again. See
``docs/design/ISSUE-1045-readtable-variabledescriptions.md``.

``detectImportOptions`` accepts ``DurationType`` (#1046). ``'text'`` records
a detected duration column as ``char`` or ``string``. There is no
``DurationType`` property. Logical and categorical columns stay text until
``Type`` is set. See ``docs/design/ISSUE-1046-readtable-column-types.md``.
"""

from __future__ import annotations

import re

import numpy as np

from openmatlab.libs.table_io import (
    _check_text_file,
    _column_as,
    _delim_text,
    _flag,
    _dated_kind,
    _datetime_type_for,
    _duration_type_for,
    _kind,
    _headers_when_modified,
    _names_from_header,
    _naming_rule_for,
    _naming_rule_value,
    _opts,
    _parse_range,
    _placeholders,
    _ranged_rows,
    _slice_fields,
    _sniff,
    _split_fields,
    _text_lines,
)
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.table_value import TableValue, _err, cellstr_row, check_names, is_text, text, texts


_PARAM_NAMES = {
    "type", "fillvalue", "treatasmissing", "quoterule", "emptyfieldrule", "prefixes", "suffixes",
    "whitespacerule", "exponentcharacter", "decimalseparator", "thousandsseparator", "trimnonnumeric",
    "numbersystem", "truesymbols", "falsesymbols", "casesensitive", "datetimetype", "datetimeformat", "inputformat",
    "datetimelocale", "timezone", "categories", "protected", "ordinal", "durationformat", "fieldseparator",
    "durationtype",
}
_TYPES = ("double", "char", "string", "datetime", "duration", "categorical", "logical")
_IDENT = re.compile(r"[A-Za-z]\w{0,62}\Z")


class VariableImportOptions:
    """One column. Add fields here when a later issue grows ``setvaropts``."""

    def __init__(self, name, typ, tokens):
        self.name = name
        self.type = typ
        self.tokens = frozenset(tokens)

    def copy(self):
        return VariableImportOptions(self.name, self.type, self.tokens)


class DelimitedTextImportOptions:
    """File-level options. Add fields here when a later issue grows detection."""

    is_object = True
    is_import_options = True

    def __init__(self, delimiter, variables, selected_idx, variable_names_line, data_line,
                 col_start=1, col_end=None, data_end=None, variable_naming_rule="modify",
                 variable_descriptions=None):
        self.delimiter = delimiter
        self.variables = list(variables)
        self.selected_idx = list(selected_idx)
        self.variable_names_line = int(variable_names_line)
        self.data_line = int(data_line)
        # Internal window from a Range name-value. Not properties: col_end None
        # means every field, data_end None means through the end of the file.
        self.col_start = int(col_start)
        self.col_end = None if col_end is None else int(col_end)
        self.data_end = None if data_end is None else int(data_end)
        self.variable_naming_rule = variable_naming_rule
        # Original headers when detection rewrote a name. Not a public property.
        self.variable_descriptions = None if variable_descriptions is None else list(variable_descriptions)

    def matlab_class(self):
        return "DelimitedTextImportOptions"

    @property
    def shape(self):
        return (1, 1)

    def numel(self):
        return 1

    def is_scalar(self):
        return True

    def binop(self, op, other, reflected):
        return NotImplemented

    def copy(self):
        return DelimitedTextImportOptions(
            self.delimiter, [v.copy() for v in self.variables], self.selected_idx,
            self.variable_names_line, self.data_line, self.col_start, self.col_end, self.data_end,
            self.variable_naming_rule, self.variable_descriptions)

    @property
    def names(self):
        return [v.name for v in self.variables]

    def _selected_names(self):
        return [self.variables[i].name for i in self.selected_idx]

    def get_prop(self, name):
        k = name.lower()
        if k == "delimiter":
            return cellstr_row([self.delimiter])
        if k == "variablenames":
            return cellstr_row(self.names)
        if k == "variabletypes":
            return cellstr_row([v.type for v in self.variables])
        if k == "selectedvariablenames":
            return cellstr_row(self._selected_names())
        if k == "variablenamesline":
            return NDArrayValue(np.array([[float(self.variable_names_line)]]))
        if k == "variablenamingrule":
            return CharValue(self.variable_naming_rule)
        raise _err(f"Unrecognized property '{name}' for class 'DelimitedTextImportOptions'.",
                   "MATLAB:noPublicFieldForClass")

    def set_prop(self, name, value):
        k = name.lower()
        if k == "delimiter":
            self.delimiter = _one_delim(value)
        elif k == "variablenames":
            self._set_names(value)
        elif k == "variabletypes":
            self._set_types(value)
        elif k == "selectedvariablenames":
            self.selected_idx = _selection(self, value)
        elif k == "variablenamesline":
            n = _nonneg_int(value, "VariableNamesLine")
            self.variable_names_line = n
            self.data_line = 1 if n == 0 else n + 1
        elif k == "variablenamingrule":
            # Public delimitedTextImportOptions: names are not refreshed when the
            # rule changes from modify to preserve. This object does not keep the
            # original header text, so neither direction rewrites VariableNames.
            self.variable_naming_rule = _naming_rule_value(value)
        else:
            raise _err(f"Unrecognized property '{name}' for class 'DelimitedTextImportOptions'.",
                       "MATLAB:noPublicFieldForClass")
        return self

    def _set_names(self, value):
        names = texts(value)
        if names is None or len(names) != len(self.variables):
            raise _err("The VariableNames property must contain one name for each variable.",
                       "MATLAB:table:IncorrectNumberOfVarNames")
        check_names(names)
        if self.variable_naming_rule != "preserve":
            for n in names:
                if not _IDENT.fullmatch(n):
                    raise _err(f"'{n}' is not a valid MATLAB identifier.", "MATLAB:table:InvalidVarNames")
        for var, n in zip(self.variables, names):
            var.name = n

    def _set_types(self, value):
        got = texts(value)
        if got is None or len(got) != len(self.variables):
            raise _err("VariableTypes must contain one type for each variable.",
                       "MATLAB:setvaropts:InvalidType")
        types = [_type_name(t) for t in got]
        for var, t in zip(self.variables, types):
            var.type = t

    def display_text(self):
        def brace(xs):
            shown = ["'\\t'" if x == "\t" else f"'{x}'" for x in xs]
            return "{" + "  ".join(shown) + "}" if shown else "{}"

        rows = [
            ("Delimiter", brace([self.delimiter])),
            ("VariableNames", brace(self.names)),
            ("VariableTypes", brace([v.type for v in self.variables])),
            ("SelectedVariableNames", brace(self._selected_names())),
            ("VariableNamesLine", str(self.variable_names_line)),
            ("VariableNamingRule", f"'{self.variable_naming_rule}'"),
        ]
        w = max(len(k) for k, _ in rows)
        body = [f"    {k.rjust(w)}: {v}" for k, v in rows]
        return "\n".join(["  DelimitedTextImportOptions with properties:", ""] + body)


def _nonneg_int(v, what):
    if not hasattr(v, "backend_buffer"):
        raise _err(f"{what} must be a nonnegative integer.", "MATLAB:detectImportOptions:InvalidOption")
    a = np.asarray(v.backend_buffer()).reshape(-1)
    if a.size != 1 or not np.isfinite(a[0]) or int(a[0]) != a[0] or int(a[0]) < 0:
        raise _err(f"{what} must be a nonnegative integer.", "MATLAB:detectImportOptions:InvalidOption")
    return int(a[0])


def _one_delim(v):
    names = texts(v)
    if not names or len(names) != 1:
        raise _err("Delimiter must be one character or a delimiter name such as 'comma', 'tab', or 'semi'.",
                   "MATLAB:detectImportOptions:InvalidDelimiter")
    d = _delim_text(names[0])
    if len(d) != 1:
        raise _err("Delimiter must be one character or a delimiter name such as 'comma', 'tab', or 'semi'.",
                   "MATLAB:detectImportOptions:InvalidDelimiter")
    return d


def _type_name(s):
    t = s.lower()
    if t not in _TYPES:
        raise _err("Variable type '{0}' is not supported. Supported types are double, char, string, "
                   "datetime, duration, categorical, and logical.".format(s),
                   "MATLAB:setvaropts:InvalidType")
    return t


def _one_type(v):
    if not is_text(v):
        raise _err("Type must be a character vector or string scalar.", "MATLAB:setvaropts:InvalidType")
    return _type_name(text(v))


def _selection(opts, v):
    n = len(opts.variables)
    names = opts.names
    if hasattr(v, "backend_buffer") and not is_text(v) and not getattr(v, "is_string", False):
        a = np.asarray(v.backend_buffer())
        if a.dtype == np.bool_ or np.issubdtype(a.dtype, np.bool_):
            flat = a.reshape(-1, order="F")
            if flat.size != n:
                raise _err(f"Logical selection must have one element for each variable ({n}).",
                           "MATLAB:setvaropts:InvalidSelection")
            idxs = [i for i, b in enumerate(flat) if b]
        else:
            idxs = []
            for x in a.reshape(-1, order="F"):
                if not np.isfinite(x) or int(x) != x or not (1 <= int(x) <= n):
                    raise _err("Variable index is out of range.", "MATLAB:setvaropts:InvalidSelection")
                idxs.append(int(x) - 1)
    else:
        got = texts(v)
        if got is None:
            raise _err("Variable selection must be names, indices, or a logical array.",
                       "MATLAB:setvaropts:InvalidSelection")
        idxs = []
        for name in got:
            if name not in names:
                raise _err(f"Unrecognized variable name '{name}'.", "MATLAB:setvaropts:UnknownVariable")
            idxs.append(names.index(name))
    if len(idxs) != len(set(idxs)):
        raise _err("Variable selection contains duplicates.", "MATLAB:setvaropts:InvalidSelection")
    return idxs


def _locate(o, lines):
    """Names line and first data line, as 1-based physical line numbers.

    ``VariableNamesLine`` 0 means there is no names line. With the default
    ``ReadVariableNames``, the names line is the first non-blank line after
    ``NumHeaderLines``, which is how ``readtable`` drops blank lines before typing.
    """
    nheader = 0
    if "numheaderlines" in o or "headerlines" in o:
        nheader = _nonneg_int(o.get("numheaderlines", o.get("headerlines")), "NumHeaderLines")
    readnames = _flag(o["readvariablenames"]) if "readvariablenames" in o else True
    if "variablenamesline" in o:
        vline = _nonneg_int(o["variablenamesline"], "VariableNamesLine")
        if "readvariablenames" in o and not readnames and vline > 0:
            raise _err("ReadVariableNames false cannot be combined with a positive VariableNamesLine.",
                       "MATLAB:detectImportOptions:InconsistentOptions")
        if vline == 0:
            return 0, nheader + 1
        if vline <= nheader:
            raise _err("VariableNamesLine must point at a line after NumHeaderLines.",
                       "MATLAB:detectImportOptions:InconsistentOptions")
        if vline > len(lines):
            raise _err(f"VariableNamesLine {vline} is past the end of the file.",
                       "MATLAB:detectImportOptions:InvalidOption")
        return vline, vline + 1
    if not readnames:
        return 0, nheader + 1
    for i in range(nheader, len(lines)):
        if lines[i].strip():
            return i + 1, i + 2
    raise _err("The file contains no variables.", "MATLAB:detectImportOptions:NoData")


def _detect_ranged(name, o, tt, rng, dt, rule, du):
    if "variablenamesline" in o:
        raise _err("Range cannot be combined with VariableNamesLine.",
                   "MATLAB:detectImportOptions:InconsistentOptions")
    nheader = 0
    if "numheaderlines" in o or "headerlines" in o:
        nheader = _nonneg_int(o.get("numheaderlines", o.get("headerlines")), "NumHeaderLines")
    readnames = _flag(o["readvariablenames"]) if "readvariablenames" in o else True
    tokens = _placeholders(o["treatasmissing"]) if "treatasmissing" in o else frozenset()
    delim = _one_delim(o["delimiter"]) if "delimiter" in o else None
    rows, line_nos, delim, c1, c2, data_end = _ranged_rows(
        name, "detectImportOptions", delim, nheader, rng)
    if readnames:
        vline = line_nos[0]
        data_line = vline + 1
        header, body = rows[0], rows[1:]
    else:
        vline, data_line = 0, line_nos[0]
        header, body = None, rows
    ncol = c2 - c1 + 1
    descriptions = None
    if header is not None:
        names, changed, originals = _names_from_header(header, ncol, rule)
        descriptions = _headers_when_modified(changed, originals)
    else:
        names = [f"Var{k + 1}" for k in range(ncol)]
    variables = [VariableImportOptions(nm, _dated_kind(_kind([r[k] for r in body], tokens, tt), dt, tt, du), tokens)
                 for k, nm in enumerate(names)]
    return (DelimitedTextImportOptions(
        delim, variables, list(range(ncol)), vline, data_line, c1, c2, data_end, rule, descriptions),)


def _detect(args, *, nargout=1):
    name, o = _opts(args, "detectImportOptions", (
        "delimiter", "readvariablenames", "numheaderlines", "headerlines",
        "texttype", "filetype", "variablenamesline", "treatasmissing", "range",
        "datetimetype", "durationtype", "variablenamingrule"))
    if "filetype" in o and text(o["filetype"]).lower() not in ("text", "delimitedtext"):
        raise _err("detectImportOptions: only delimited text files are supported.",
                   "MATLAB:detectImportOptions:UnsupportedFileType")
    tt = text(o["texttype"]).lower() if "texttype" in o else "char"
    if tt not in ("char", "string"):
        raise _err("TextType must be 'char' or 'string'.", "MATLAB:readtable:InvalidTextType")
    dt = _datetime_type_for(name, "detectImportOptions", o)
    du = _duration_type_for(name, "detectImportOptions", o)
    rule = _naming_rule_for(name, "detectImportOptions", o)
    rng = None
    if "range" in o:
        _check_text_file(name, "detectImportOptions")
        rng = _parse_range(o["range"])
    if rng is not None:
        return _detect_ranged(name, o, tt, rng, dt, rule, du)
    p, lines = _text_lines(name, "detectImportOptions")
    vline, data_line = _locate(o, lines)
    tokens = _placeholders(o["treatasmissing"]) if "treatasmissing" in o else frozenset()
    if "delimiter" in o:
        delim = _one_delim(o["delimiter"])
    else:
        start = (vline - 1) if vline else (data_line - 1)
        sample = [ln for ln in lines[max(start, 0):] if ln.strip()]
        delim = "," if p.suffix.lower() == ".csv" else _sniff(sample)
    header = None
    if vline:
        header_rows = _split_fields([lines[vline - 1]], delim)
        header = header_rows[0] if header_rows else []
        if not any(c.strip() for c in header):
            raise _err("The variable-names line is empty.", "MATLAB:detectImportOptions:InvalidOption")
    body = [ln for ln in lines[data_line - 1:] if ln.strip()]
    rows = _split_fields(body, delim)
    ncol = max([len(r) for r in rows] + [len(header) if header else 0])
    if ncol == 0:
        raise _err("The file contains no variables.", "MATLAB:detectImportOptions:NoData")
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    descriptions = None
    if header is not None:
        names, changed, originals = _names_from_header(header, ncol, rule)
        descriptions = _headers_when_modified(changed, originals)
    else:
        names = [f"Var{k + 1}" for k in range(ncol)]
    variables = [VariableImportOptions(nm, _dated_kind(_kind([r[k] for r in rows], tokens, tt), dt, tt, du), tokens)
                 for k, nm in enumerate(names)]
    return (DelimitedTextImportOptions(delim, variables, list(range(ncol)), vline, data_line,
                                       variable_naming_rule=rule, variable_descriptions=descriptions),)


def _apply(opts, indices, shown, value):
    key = shown.lower()
    if key == "type":
        typ = _one_type(value)
        for i in indices:
            opts.variables[i].type = typ
    elif key == "treatasmissing":
        tokens = _placeholders(value)
        for i in indices:
            opts.variables[i].tokens = tokens
    else:
        raise _err(f"'{shown}' is not a supported variable import option. "
                   "Supported options are Type and TreatAsMissing.",
                   "MATLAB:setvaropts:UnknownParameter")


def _setvaropts(args, *, nargout=1):
    if not args or not getattr(args[0], "is_import_options", False):
        raise _err("First argument must be a DelimitedTextImportOptions object.",
                   "MATLAB:setvaropts:InvalidOpts")
    if len(args) < 3:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    opts = args[0].copy()
    rest = list(args[1:])
    if is_text(rest[0]) and text(rest[0]).lower() in _PARAM_NAMES and len(rest) % 2 == 0:
        indices, pairs = list(range(len(opts.variables))), rest
    else:
        indices = _selection(opts, rest[0])
        pairs = rest[1:]
        if len(pairs) % 2:
            raise _err("Name-value arguments must come in pairs.", "MATLAB:InputParser:ParamMissingValue")
    if not pairs:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    for k in range(0, len(pairs), 2):
        if not is_text(pairs[k]):
            raise _err("Variable import option names must be text.",
                       "MATLAB:setvaropts:UnknownParameter")
        _apply(opts, indices, text(pairs[k]), pairs[k + 1])
    return (opts,)


def _import(name, opts, data_line):
    _p, lines = _text_lines(name, "readtable")
    end = len(lines) if opts.data_end is None else opts.data_end
    body = [ln for ln in lines[max(data_line, 1) - 1:end] if ln.strip()]
    rows = _split_fields(body, opts.delimiter)
    if opts.col_end is not None:
        rows = [_slice_fields(r, opts.col_start, opts.col_end) for r in rows]
    nvars = len(opts.variables)
    width = max((len(r) for r in rows), default=0)
    if width > nvars:
        raise _err("A row has more fields than the import options have variables.",
                   "MATLAB:readtable:ExtraColumns")
    rows = [r + [""] * (nvars - len(r)) for r in rows]
    names = [opts.variables[i].name for i in opts.selected_idx]
    cols = [_column_as([r[i] for r in rows], opts.variables[i].type, opts.variables[i].tokens)
            for i in opts.selected_idx]
    descs = opts.variable_descriptions
    if descs is not None:
        descs = [descs[i] for i in opts.selected_idx]
    return TableValue(names, cols, len(rows), variable_descriptions=descs)


def read_with_options(args):
    """``readtable(file, opts)`` and ``readtable(file, opts, 'ReadVariableNames', tf)``."""
    name, o = _opts([args[0], *args[2:]], "readtable", ("readvariablenames",))
    opts = args[1]
    start = opts.data_line
    if "readvariablenames" in o and not _flag(o["readvariablenames"]) and opts.variable_names_line > 0:
        start = opts.variable_names_line
    return (_import(name, opts, start),)


def register(builtins) -> None:
    builtins.update(detectimportoptions=_detect, setvaropts=_setvaropts)
