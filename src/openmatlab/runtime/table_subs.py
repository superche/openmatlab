"""Table indexing, assignment and concatenation (M10 T-E1, Epic #691).

Called from ``classdef_subs.try_ref/try_asgn`` with the whole indexing chain as
substruct levels, and from the evaluator's ``[...]`` for concatenation.
"""

from __future__ import annotations

from typing import List

import numpy as np

from openmatlab.lang import ast_nodes as ast
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime import classdef_subs as cs
from openmatlab.runtime.table_value import TableValue, _cv, _err, _idx_value, _shape, height_of, is_text, text

_TWO_SUBS = ("Subscripting a table using linear indexing (one subscript) or multidimensional indexing "
             "(three or more subscripts) is not supported. Use a row subscript and a variable subscript.")


_COLON = ast.ColonExpr(start=None, stop=None)


def ix(ev, value, subs, kind="()"):
    """value(subs...) where a ``None`` subscript is a bare colon."""
    names = [cs._tmp(ev, value)] + [cs._tmp(ev, v) for v in subs if v is not None]
    try:
        it = iter(names[1:])
        idx = tuple(_COLON if v is None else ast.Name(next(it)) for v in subs)
        node = (ast.IndexExpr(target=ast.Name(names[0]), indices=idx) if kind == "()"
                else ast.CellIndexExpr(target=ast.Name(names[0]), indices=idx))
        return ev.eval_expr(node)
    finally:
        for n in names:
            ev.workspace.clear(n)


def ix_asgn(ev, base, subs, val, kind="()"):
    """base(subs...) = val / base{subs...} = val (``None`` subscript = colon); returns the new base."""
    if base is None:
        base = NDArrayValue(np.zeros((0, 0))) if kind == "()" else __import__(
            "openmatlab.runtime.cell_value", fromlist=["CellValue"]).CellValue(rows=())
    names = [cs._tmp(ev, base), cs._tmp(ev, val)] + [cs._tmp(ev, v) for v in subs if v is not None]
    try:
        it = iter(names[2:])
        idx = tuple(_COLON if v is None else ast.Name(next(it)) for v in subs)
        if kind == "()":
            st = ast.ArrayAssign(target=ast.IndexExpr(target=ast.Name(names[0]), indices=idx),
                                 value=ast.Name(names[1]), suppress=True)
        else:
            st = ast.CellAssign(target=ast.CellIndexExpr(target=ast.Name(names[0]), indices=idx),
                                value=ast.Name(names[1]), suppress=True)
        ev._exec_stmt(st)
        return ev.workspace.get(names[0])
    finally:
        for n in names:
            ev.workspace.clear(n)


def _end_of(cur, k, n) -> float:
    if cur is None:
        return 1.0
    if getattr(cur, "is_table", False):
        sh = cur.shape
    else:
        try:
            sh = _shape(cur)
        except Exception:
            return 1.0
    if n == 1:
        return float(np.prod(sh))
    if k < n - 1:
        return float(sh[k]) if k < len(sh) else 1.0
    return float(np.prod(sh[k:])) if k < len(sh) else 1.0


def dref(ev, cur, lv):
    """Default indexing chain on any value; tables recurse into ``ref``."""
    for i, (kind, sub) in enumerate(lv):
        if getattr(cur, "is_table", False):
            return ref(ev, cur, lv[i:])
        cur = cs._field(cur, sub) if kind == "." else ix(ev, cur, sub, kind)
    return cur


def dasgn(ev, base, lv, val):
    """Default assignment chain on any value; tables recurse into ``asgn``."""
    if not lv:
        return val
    if getattr(base, "is_table", False):
        return asgn(ev, base, lv, val)
    (kind, sub), rest = lv[0], lv[1:]
    if kind == ".":
        cur = None
        if rest and base is not None:
            try:
                cur = cs._field(base, sub)
            except Exception:
                cur = None
        return cs.default_asgn(ev, base, [(".", sub)], dasgn(ev, cur, rest, val))
    if rest:
        cur = None
        if base is not None:
            try:
                cur = ix(ev, base, sub, kind)
            except Exception:
                cur = None
        val = dasgn(ev, cur, rest, val)
    return ix_asgn(ev, base, sub, val, kind)


def _ref1(ev, cur, level):
    return dref(ev, cur, [level])


def levels(ev, obj, steps) -> list:
    """AST steps -> levels; ``end`` in each subscript refers to the value indexed at that level."""
    out = []
    cur = obj
    for i, (kind, node) in enumerate(steps):
        if kind == ".":
            name = node.name
            if name is None:
                name = getattr(ev.eval_expr(node.name_expr), "text", "")
            lv = (".", name)
        else:
            idx = list(getattr(node, "indices", None) or getattr(node, "args", None) or [])
            vals = []
            for k, e in enumerate(idx):
                if ev._is_bare_colon(e):
                    vals.append(None)  # bare colon
                    continue
                ev._end_stack.append(_end_of(cur, k, len(idx)))
                try:
                    vals.append(ev.eval_expr(e))
                finally:
                    ev._end_stack.pop()
            lv = (kind, vals)
        out.append(lv)
        if i + 1 < len(steps):
            try:
                cur = _ref1(ev, cur, lv) if cur is not None else None
            except Exception:
                cur = None  # assignment may create it
    return out


def _rc(sub):
    if len(sub) != 2:
        raise _err(_TWO_SUBS, "MATLAB:table:LinearSubscript")
    return sub


def _cat(ev, values, vertical: bool):
    if len(values) == 1:
        return values[0]
    names = [cs._tmp(ev, v) for v in values]
    try:
        exprs = [ast.Name(n) for n in names]
        rows = tuple((e,) for e in exprs) if vertical else (tuple(exprs),)
        return ev.eval_expr(ast.MatrixLiteral(rows=rows))
    finally:
        for n in names:
            ev.workspace.clear(n)


def ref(ev, T: TableValue, lv: list):
    (kind, sub), rest = lv[0], lv[1:]
    if kind == ".":
        v = T.get_prop(sub)
    else:
        r, c = _rc(sub)
        part = T.take_rows(ev, T.row_sel(r)).take_vars(T.var_sel(c))
        if kind == "()":
            v = part
        else:
            if not part.cols:
                v = NDArrayValue(np.zeros((part.nrows, 0)))
            else:
                v = _cat(ev, part.cols, vertical=False)
    if not rest:
        return v
    return dref(ev, v, rest)


def _is_empty_double(v) -> bool:
    return (not getattr(v, "is_object", False) and hasattr(v, "backend_buffer") and v.matlab_class() == "double"
            and _shape(v) == (0, 0))


def _expand(ev, v, n):
    """Scalar expansion to n rows (MATLAB allows a scalar for a new or whole variable)."""
    return ix(ev, v, [NDArrayValue(np.ones((n, 1))), None])


def set_var(ev, T: TableValue, name: str, v) -> TableValue:
    if getattr(v, "is_table", False):
        raise _err("Table variables cannot be assigned a table with dot assignment in this release.",
                   "MATLAB:table:NestedTable")
    names, cols, n = list(T.names), list(T.cols), T.nrows
    if not names and n == 0:
        n = height_of(v)
    h = height_of(v)
    if h != n:
        if np.prod(_shape(v)) == 1 and n > 0:
            v = _expand(ev, v, n)
        else:
            raise _err("To assign to or create a variable in a table, the number of rows must match the height of "
                       "the table.", "MATLAB:table:RowDimensionMismatch")
    if name in names:
        cols[names.index(name)] = v
    else:
        from openmatlab.runtime.table_value import check_names

        check_names(names + [name])
        names.append(name)
        cols.append(v)
    return T.copy(names=names, cols=cols, nrows=n)


def _regrow(ev, T, cols, rows_hit):
    """After row assignment: new height and consistent columns."""
    n = max([T.nrows] + [int(r) + 1 for r in rows_hit])
    hs = {height_of(c) for c in cols}
    if hs - {n}:
        raise _err("To grow a table by assignment, assign values to all of its variables.",
                   "MATLAB:table:RowDimensionMismatch")
    rn = T.rownames
    if rn is not None and n > len(rn):
        rn = rn + [f"Row{k + 1}" for k in range(len(rn), n)]
    return T.copy(cols=cols, nrows=n, rownames=rn)


def _put_rows(ev, col, rows, v):
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(col, CellValue):
        if not isinstance(v, CellValue):
            v = CellValue(rows=((v,),))
        need = int(max(rows)) + 1 if len(rows) else 0
        if need > col.shape[0] and col.shape[1]:  # grow a cell column with [] rows first
            empty = NDArrayValue(np.zeros((0, 0)))
            col = CellValue(rows=col.rows + tuple((empty,) * col.shape[1] for _ in range(need - col.shape[0])))
    return ix_asgn(ev, col, [_idx_value(rows), None], v)


def _split_cols(ev, v, k):
    """A value spanning k variables -> k column values (numeric matrices split by column)."""
    from openmatlab.runtime.cell_value import CellValue

    if k == 1:
        return [v]
    if isinstance(v, CellValue):
        if v.numel() != k and v.shape[1] != k:
            raise _err("The number of values on the right does not match the number of table variables.",
                       "MATLAB:table:RHSDimensionMismatch")
        if v.shape[0] == 1:
            return list(v.rows[0])
        return [CellValue(rows=tuple((r[j],) for r in v.rows)) for j in range(k)]
    sh = _shape(v)
    if np.prod(sh) == 1:
        return [v] * k
    if sh[1] != k:
        raise _err("The number of values on the right does not match the number of table variables.",
                   "MATLAB:table:RHSDimensionMismatch")
    return [ix(ev, v, [None, NDArrayValue(np.array([[float(j + 1)]]))]) for j in range(k)]


def asgn(ev, T: TableValue, lv: list, val) -> TableValue:
    from openmatlab.runtime.cell_value import CellValue

    (kind, sub), rest = lv[0], lv[1:]
    if kind == ".":
        if sub == "Properties":
            p = dasgn(ev, T.properties(), rest, val) if rest else val
            if not getattr(p, "is_struct", False):
                raise _err("Table Properties must be assigned a struct.", "MATLAB:table:InvalidProperties")
            return T.with_properties(p)
        if rest:
            cur = T.cols[T.names.index(sub)] if sub in T.names else None
            return set_var(ev, T, sub, dasgn(ev, cur, rest, val))
        if _is_empty_double(val) and sub in T.names:
            k = T.names.index(sub)
            return T.copy(names=T.names[:k] + T.names[k + 1:], cols=T.cols[:k] + T.cols[k + 1:])
        return set_var(ev, T, sub, val)
    r, c = _rc(sub)
    if rest:
        cur = ref(ev, T, [(kind, sub)])
        val = dasgn(ev, cur, rest, val)
    if kind == "()" and _is_empty_double(val):
        if c is None:
            return T.delete_rows(ev, T.row_sel(r))
        if r is None:
            keep = [i for i in range(len(T.names)) if i not in set(T.var_sel(c))]
            return T.take_vars(keep)
        raise _err("Deleting table elements requires a colon for either the rows or the variables.",
                   "MATLAB:table:InvalidDeletion")
    rows = T.row_sel(r, grow=True)
    vars_ = T.var_sel(c)
    cols = list(T.cols)
    names = list(T.names)
    if kind == "()" and getattr(val, "is_table", False):
        if len(val.names) != len(vars_):
            raise _err("The number of variables on the right does not match the assignment.",
                       "MATLAB:table:RHSDimensionMismatch")
        parts = val.cols
    elif kind == "()" and isinstance(val, CellValue):  # T(r, vars) = {v1, v2, ...}: contents per variable
        if val.numel() != len(vars_) and not (val.numel() == 1):
            raise _err("The number of values on the right does not match the number of table variables.",
                       "MATLAB:table:RHSDimensionMismatch")
        flat = [x for row in val.rows for x in row]
        parts = flat if len(flat) == len(vars_) else flat * len(vars_)
    else:
        parts = _split_cols(ev, val, len(vars_))
    for j, part in zip(vars_, parts):
        if j >= len(cols):
            raise _err("To add a variable by indexing, assign to all of the table's rows.",
                       "MATLAB:table:UnrecognizedVarName")
        cols[j] = _put_rows(ev, cols[j], rows, part)
    return _regrow(ev, T.copy(names=names), cols, rows)


def concat(ev, rows) -> TableValue:
    """[T1 T2; T3 T4]: horizontal within each row, then vertical."""
    hrows = [_hcat(ev, r) for r in rows if r]
    return hrows[0] if len(hrows) == 1 else _vcat(ev, hrows)


def _as_table(v, like=None):
    if getattr(v, "is_table", False):
        return v
    raise _err("All input arguments must be tables.", "MATLAB:table:cat:InvalidInput")


def _hcat(ev, items) -> TableValue:
    items = [v for v in items if not _is_empty_double(v)]
    ts = [_as_table(v) for v in items]
    out = ts[0]
    for t in ts[1:]:
        if t.nrows != out.nrows:
            raise _err("All tables being horizontally concatenated must have the same number of rows.",
                       "MATLAB:table:horzcat:SizeMismatch")
        dup = [n for n in t.names if n in out.names]
        if dup:
            raise _err(f"Duplicate table variable name: '{dup[0]}'.", "MATLAB:table:DuplicateVarNames")
        out = out.copy(names=out.names + t.names, cols=out.cols + t.cols)
    return out


def _vcat(ev, items) -> TableValue:
    items = [v for v in items if not _is_empty_double(v)]
    ts = [_as_table(v) for v in items]
    first = ts[0]
    for t in ts[1:]:
        if sorted(t.names) != sorted(first.names):
            raise _err("All tables being vertically concatenated must have the same variable names.",
                       "MATLAB:table:vertcat:UnequalVarNames")
    cols = [_cat(ev, [t.cols[t.names.index(n)] for t in ts], vertical=True) for n in first.names]
    rn = None
    if all(t.rownames for t in ts):
        rn = [x for t in ts for x in t.rownames]
        if len(set(rn)) != len(rn):
            raise _err("Duplicate row name.", "MATLAB:table:DuplicateRowNames")
    return first.copy(cols=cols, nrows=sum(t.nrows for t in ts), rownames=rn)
