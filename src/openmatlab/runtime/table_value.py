"""MATLAB ``table``: native column store (M10 T-E1, Epic #691).

A table is an ordered list of named variables (columns). Each variable is an
ordinary MATLAB ``Value`` whose first dimension is the table height (numeric
matrix, cell, string, char matrix, datetime, ...). No pandas: rows are selected
and concatenated through the evaluator's own indexing, so every value type keeps
its MATLAB semantics.

Indexing goes through ``classdef_subs`` (``native_subs``): the evaluator hands the
whole chain (``T.x(i)``, ``T{r,c}``, ``T(r,c)``, ``T.Properties.VariableNames``) to
``subsref``/``subsasgn`` here as substruct levels.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _cv(s):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(s)


def is_text(v) -> bool:
    from openmatlab.runtime.char_value import CharValue

    return isinstance(v, CharValue) or (getattr(v, "is_string", False) and v.numel() == 1)


def text(v) -> str:
    if getattr(v, "is_string", False):
        from openmatlab.runtime import string_array as sa

        return str(np.asarray(sa.to_grid(v), dtype=object).flat[0])
    return v.text


def texts(v) -> Optional[List[str]]:
    """char / string / cellstr -> list of str; None if not text."""
    from openmatlab.runtime.cell_value import CellValue

    if is_text(v):
        return [text(v)]
    if getattr(v, "is_string", False):
        from openmatlab.runtime import string_array as sa

        return [str(x) for x in np.asarray(sa.to_grid(v), dtype=object).reshape(-1, order="F")]
    if isinstance(v, CellValue):
        out = []
        for c in range(v.shape[1]):
            for r in range(v.shape[0]):
                e = v.rows[r][c]
                if not is_text(e):
                    return None
                out.append(text(e))
        return out
    return None


def cellstr_row(names: Sequence[str]):
    from openmatlab.runtime.cell_value import CellValue

    return CellValue(rows=(tuple(_cv(n) for n in names),)) if names else CellValue(rows=())


def cellstr_col(names: Sequence[str]):
    from openmatlab.runtime.cell_value import CellValue

    return CellValue(rows=tuple((_cv(n),) for n in names)) if names else CellValue(rows=())


def _shape(v):
    if getattr(v, "is_table", False):
        return tuple(v.shape)
    from openmatlab.libs.numeric_builtins import BUILTINS

    sz = BUILTINS["size"]([v], nargout=1)[0]
    return tuple(int(d) for d in np.asarray(sz.backend_buffer()).reshape(-1))


def height_of(v) -> int:
    return _shape(v)[0]


def _idx_value(rows: np.ndarray):
    return NDArrayValue(np.asarray(rows, dtype=float).reshape(-1, 1) + 1.0)


_VALID = re.compile(r"^[A-Za-z]\w*$")


class TableValue:
    is_object = True
    is_table = True
    native_subs = True

    def __init__(self, names: Sequence[str], cols: Sequence, nrows: int, rownames: Optional[Sequence[str]] = None,
                 description: str = ""):
        self.names = list(names)
        self.cols = list(cols)
        self.nrows = int(nrows)
        self.rownames = list(rownames) if rownames else None
        self.description = description
        check_names(self.names)

    # -- value protocol -------------------------------------------------------
    def matlab_class(self) -> str:
        return "table"

    @property
    def shape(self):
        return (self.nrows, len(self.names))

    def numel(self) -> int:
        return self.nrows * len(self.names)

    def is_scalar(self) -> bool:
        return self.numel() == 1

    def copy(self, **kw) -> "TableValue":
        d = dict(names=self.names, cols=self.cols, nrows=self.nrows, rownames=self.rownames,
                 description=self.description)
        d.update(kw)
        return TableValue(**d)

    def var_index(self, name: str) -> int:
        try:
            return self.names.index(name)
        except ValueError:
            raise _err(f"Unrecognized table variable name '{name}'.", "MATLAB:table:UnrecognizedVarName") from None

    def get_prop(self, name):  # T.x when the evaluator reads a bare field
        if name == "Properties":
            return self.properties()
        return self.cols[self.var_index(name)]

    def binop(self, op, other, reflected):
        return NotImplemented

    # -- Properties -----------------------------------------------------------
    def properties(self):
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.runtime.struct_value import StructValue

        return StructValue.scalar([
            ("Description", _cv(self.description)),
            ("DimensionNames", cellstr_row(["Row", "Variables"])),
            ("VariableNames", cellstr_row(self.names)),
            ("VariableDescriptions", CellValue(rows=())),
            ("VariableUnits", CellValue(rows=())),
            ("RowNames", cellstr_col(self.rownames) if self.rownames else CellValue(rows=())),
        ])

    def with_properties(self, p) -> "TableValue":
        names = texts(p.get("VariableNames")) if p.has("VariableNames") else self.names
        if names is None or len(names) != len(self.names):
            raise _err("The VariableNames property must contain one name for each variable in the table.",
                       "MATLAB:table:IncorrectNumberOfVarNames")
        rn = texts(p.get("RowNames")) if p.has("RowNames") else self.rownames
        if rn is not None and len(rn) == 0:
            rn = None
        if rn is not None and len(rn) != self.nrows:
            raise _err("The RowNames property must contain one name for each row in the table.",
                       "MATLAB:table:IncorrectNumberOfRowNames")
        desc = text(p.get("Description")) if p.has("Description") and is_text(p.get("Description")) else self.description
        return self.copy(names=names, rownames=rn, description=desc)

    # -- selectors ------------------------------------------------------------
    def var_sel(self, v) -> List[int]:
        n = len(self.names)
        if v is None or (is_text(v) and text(v) == ":"):
            return list(range(n))
        names = texts(v)
        if names is not None:
            return [self.var_index(s) for s in names]
        a = np.asarray(v.backend_buffer()).reshape(-1)
        if a.dtype == np.bool_:
            if a.size > n:
                raise _err("Variable index exceeds table dimensions.", "MATLAB:table:VarIndexOutOfRange")
            return [int(i) for i in np.flatnonzero(a)]
        out = []
        for x in a:
            if x != int(x) or x < 1:
                raise _err("Subscript indices must be real positive integers.", "MATLAB:badsubscript")
            if x > n:
                raise _err(f"Variable index exceeds table dimensions. Index must not exceed {n}.",
                           "MATLAB:table:VarIndexOutOfRange")
            out.append(int(x) - 1)
        return out

    def row_sel(self, v, *, grow: bool = False) -> np.ndarray:
        if v is None or (is_text(v) and text(v) == ":"):
            return np.arange(self.nrows)
        names = texts(v)
        if names is not None:
            if not self.rownames:
                raise _err("Table row names are not defined; index rows by number or logical value.",
                           "MATLAB:table:RowNamesNotDefined")
            out = []
            for s in names:
                if s not in self.rownames:
                    raise _err(f"Unrecognized row name '{s}'.", "MATLAB:table:UnrecognizedRowName")
                out.append(self.rownames.index(s))
            return np.array(out, dtype=int)
        a = np.asarray(v.backend_buffer()).reshape(-1)
        if a.dtype == np.bool_:
            if a.size > self.nrows and np.any(a[self.nrows:]):
                raise _err("Row index exceeds table dimensions.", "MATLAB:table:RowIndexOutOfRange")
            return np.flatnonzero(a[: self.nrows]) if a.size >= self.nrows else np.flatnonzero(a)
        if np.any(a != np.floor(a)) or np.any(a < 1):
            raise _err("Subscript indices must be real positive integers.", "MATLAB:badsubscript")
        if not grow and np.any(a > self.nrows):
            raise _err(f"Row index exceeds table dimensions. Index must not exceed {self.nrows}.",
                       "MATLAB:table:RowIndexOutOfRange")
        return a.astype(int) - 1

    # -- row operations (through the evaluator: every value type keeps MATLAB indexing)
    def take_rows(self, ev, rows: np.ndarray) -> "TableValue":
        from openmatlab.runtime.table_subs import ix

        if len(rows) == self.nrows and np.array_equal(rows, np.arange(self.nrows)):
            return self
        iv = _idx_value(rows)
        cols = [ix(ev, c, [iv, None]) for c in self.cols]
        rn = [self.rownames[i] for i in rows] if self.rownames else None
        return self.copy(cols=cols, nrows=len(rows), rownames=rn)

    def take_vars(self, idx: List[int]) -> "TableValue":
        if len(set(idx)) != len(idx):
            raise _err("Duplicate table variable name.", "MATLAB:table:DuplicateVarNames")
        return self.copy(names=[self.names[i] for i in idx], cols=[self.cols[i] for i in idx])

    def delete_rows(self, ev, rows: np.ndarray) -> "TableValue":
        keep = np.setdiff1d(np.arange(self.nrows), rows)
        out = self.take_rows(ev, keep)
        return out if out is not self else self.copy()

    # -- display --------------------------------------------------------------
    def body_text(self) -> str:
        if not self.names:
            return ""
        cols = []
        if self.rownames:
            cols.append(("", list(self.rownames), "left"))
        for n, c in zip(self.names, self.cols):
            cells, align = _format_column(c, self.nrows)
            cols.append((n, cells, align))
        widths = [max([len(h)] + [len(x) for x in cells]) for h, cells, _a in cols]
        def row(items):
            return "    " + "    ".join(items).rstrip()
        head = row([h.center(w) for (h, _c, _a), w in zip(cols, widths)])
        unders = row([("_" * len(h)).center(w) if h else " " * w for (h, _c, _a), w in zip(cols, widths)])
        lines = [head, unders, ""]
        for r in range(self.nrows):
            items = []
            for (h, cells, a), w in zip(cols, widths):
                items.append(cells[r].ljust(w) if a == "left" else cells[r].rjust(w))
            lines.append(row(items))
        return "\n".join(lines)

    def display_text(self) -> str:
        from openmatlab.host.display import _dims

        head = f"  {_dims(self.shape)} empty table" if self.numel() == 0 else f"  {_dims(self.shape)} table"
        body = self.body_text()
        return head + ("\n\n" + body if body and self.nrows else "")


def check_names(names) -> None:
    seen = set()
    for n in names:
        if not isinstance(n, str) or not n:
            raise _err("Table variable names must be nonempty character vectors.", "MATLAB:table:InvalidVarNames")
        if n in seen:
            raise _err(f"Duplicate table variable name: '{n}'.", "MATLAB:table:DuplicateVarNames")
        if n in ("Properties", "RowNames", "VariableNames", ":"):
            raise _err(f"'{n}' is a reserved table name and cannot be used as a variable name.",
                       "MATLAB:table:ReservedVarName")
        seen.add(n)


def _fmt_num(x, is_int_class=False) -> str:
    if isinstance(x, (bool, np.bool_)):
        return "true" if x else "false"
    if np.iscomplexobj(x):
        return f"{_fmt_num(x.real)}{'+' if x.imag >= 0 else '-'}{_fmt_num(abs(x.imag))}i"
    x = float(x)
    if np.isnan(x):
        return "NaN"
    if np.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    return f"{x:.5g}"


def _format_column(c, n):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    if isinstance(c, CellValue):
        out = []
        for r in range(n):
            items = []
            for e in c.rows[r]:
                if isinstance(e, CharValue) and e.shape[0] <= 1:
                    items.append("{'" + e.text + "'}")
                elif hasattr(e, "backend_buffer") and np.asarray(e.backend_buffer()).size == 1:
                    items.append("{[" + _fmt_num(np.asarray(e.backend_buffer()).reshape(-1)[0]) + "]}")
                else:
                    from openmatlab.host.display import _field_summary

                    items.append("{" + _field_summary(e) + "}")
            out.append("    ".join(items))
        return out, "left"
    if getattr(c, "is_string", False):
        from openmatlab.runtime import string_array as sa

        a = np.asarray(sa.to_grid(c), dtype=object).reshape(n, -1)
        return ["    ".join("<missing>" if x is None else f'"{x}"' for x in a[r]) for r in range(n)], "left"
    if isinstance(c, CharValue):
        rows = c.text.split("\n") if c.shape[0] > 1 else [c.text]
        return [rows[r] if r < len(rows) else "" for r in range(n)], "left"
    if getattr(c, "is_table", False):
        return ["[1×" + str(len(c.names)) + " table]"] * n, "left"
    if hasattr(c, "backend_buffer") and not getattr(c, "is_object", False):
        a = np.asarray(c.backend_buffer())
        a = a.reshape(n, -1) if a.size else np.zeros((n, 0))
        return ["    ".join(_fmt_num(x) for x in a[r]) for r in range(n)], "right"
    if hasattr(c, "display_text") and hasattr(c, "index"):
        out = []
        for r in range(n):
            try:
                t = c.index([NDArrayValue(np.array([[float(r + 1)]]))]).display_text().strip()
            except Exception:
                t = c.matlab_class()
            out.append(t)
        return out, "left"
    return [f"[1×1 {c.matlab_class()}]"] * n, "left"
