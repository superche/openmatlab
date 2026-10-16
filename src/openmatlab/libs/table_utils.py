"""Table utilities, sorting and sets (M10 T-E3, #693).

Conversions (table2array/table2cell/table2struct), head/tail, varfun/rowfun, variable management
(removevars/renamevars/movevars/addvars), summary, and sortrows/issortedrows/unique/ismember on
tables, plus sort/ismember on categorical arrays.

Row operations go through the calling evaluator (``frames``), so every variable type keeps its own
MATLAB indexing and concatenation rules. Ordering uses per-variable *rank keys*: each variable
becomes float rank columns (NaN, NaT, <missing> and <undefined> rank last), which makes multi-key
stable sorting and row equality type-independent.
"""

from __future__ import annotations

import sys

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.table_value import TableValue, _cv, _err, cellstr_row, height_of, is_text, text, texts


def _ev():
    from openmatlab.runtime import frames

    st = frames._STACK.get()
    if not st:
        raise _err("Internal error: no active evaluator.", "MATLAB:table:NoEvaluator")
    return st[-1]


def _num(x):
    a = np.asarray(x, dtype=float)
    return NDArrayValue(a.reshape(1, 1) if a.ndim == 0 else (a.reshape(-1, 1) if a.ndim == 1 else a))


def _bool(b):
    return NDArrayValue(np.asarray(b, dtype=bool).reshape(1, 1) if np.ndim(b) == 0 else np.asarray(b, dtype=bool))


def _is_table(v):
    return getattr(v, "is_table", False)


def _need_table(v, fn, pos="first"):
    if not _is_table(v):
        cls = v.matlab_class() if hasattr(v, "matlab_class") else "double"
        raise _err(f"Undefined function '{fn}' for input arguments of type '{cls}'.", "MATLAB:UndefinedFunction")
    return v


def _rows(T, rows):
    return T.take_rows(_ev(), np.asarray(rows, dtype=int)).copy() if len(rows) == T.nrows else T.take_rows(
        _ev(), np.asarray(rows, dtype=int))


def _col_rows(c, rows):
    from openmatlab.runtime.table_subs import ix
    from openmatlab.runtime.table_value import _idx_value

    return ix(_ev(), c, [_idx_value(np.asarray(rows, dtype=int)), None])


def _opts(args, allowed, fn):
    """Split trailing Name,Value pairs (case-insensitive names from ``allowed``)."""
    data, opts = [], {}
    i = 0
    args = list(args)
    while i < len(args):
        a = args[i]
        if is_text(a) and text(a).lower() in allowed:
            if i + 1 >= len(args):
                raise _err(f"{fn}: missing value for '{text(a)}'.", "MATLAB:table:MissingNVValue")
            opts[text(a).lower()] = args[i + 1]
            i += 2
            continue
        if opts:
            raise _err(f"{fn}: unrecognized parameter name '{text(a) if is_text(a) else '?'}'.",
                       "MATLAB:table:UnrecognizedParameter")
        data.append(a)
        i += 1
    return data, opts


# =====================================================================
# conversions
# =====================================================================
def _table2array(args, *, nargout=1):
    if len(args) != 1:
        raise _err("table2array: expected one input.", "MATLAB:narginchk:notEnoughInputs")
    T = _need_table(args[0], "table2array")
    if not T.cols:
        return (NDArrayValue(np.zeros((T.nrows, 0))),)
    if any(_is_table(c) for c in T.cols):
        raise _err("table2array: nested tables are not supported.", "MATLAB:table2array:NestedTable")
    try:
        return (_ev().concat_values([list(T.cols)]),)
    except Exception as e:
        if type(e).__name__ == "EvalError":
            raise _err("Unable to concatenate the table variables in a single array: the variables have "
                       "incompatible types.", "MATLAB:table2array:CatError") from None
        raise


def _cell_entries(c, n):
    """Per-row values of a variable as table2cell gives them: a cell variable contributes its contents."""
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(c, CellValue) and c.shape[1] == 1:
        return [c.rows[r][0] for r in range(n)]
    return [_col_rows(c, [r]) for r in range(n)]


def _table2cell(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    if len(args) != 1:
        raise _err("table2cell: expected one input.", "MATLAB:narginchk:notEnoughInputs")
    T = _need_table(args[0], "table2cell")
    cols = [_cell_entries(c, T.nrows) for c in T.cols]
    if not cols or T.nrows == 0:
        return (CellValue.empty(T.nrows, len(T.cols)) if hasattr(CellValue, "empty") else CellValue(rows=()),)
    return (CellValue(rows=tuple(tuple(col[r] for col in cols) for r in range(T.nrows))),)


def _table2struct(args, *, nargout=1):
    from openmatlab.runtime.struct_value import StructValue

    data, opts = _opts(args, ("toscalar",), "table2struct")
    if len(data) != 1:
        raise _err("table2struct: expected one table input.", "MATLAB:narginchk:notEnoughInputs")
    T = _need_table(data[0], "table2struct")
    to_scalar = "toscalar" in opts and bool(np.asarray(opts["toscalar"].backend_buffer()).reshape(-1)[0])
    if to_scalar:
        return (StructValue.scalar(zip(T.names, T.cols)),)
    cols = [_cell_entries(c, T.nrows) for c in T.cols]
    elems = [{n: col[r] for n, col in zip(T.names, cols)} for r in range(T.nrows)]
    return (StructValue.build((T.nrows, 1), T.names, elems),)


# =====================================================================
# head / tail
# =====================================================================
def _headtail(which):
    def f(args, *, nargout=1):
        if not args or len(args) > 2:
            raise _err(f"{which}: expected {which}(A) or {which}(A, k).", "MATLAB:narginchk:notEnoughInputs")
        A = args[0]
        k = 8
        if len(args) == 2:
            kk = np.asarray(args[1].backend_buffer(), float).reshape(-1) if hasattr(args[1], "backend_buffer") and not is_text(args[1]) else None
            if kk is None or kk.size != 1 or kk[0] < 0 or kk[0] != int(kk[0]):
                raise _err(f"{which}: the number of rows must be a nonnegative integer scalar.", f"MATLAB:{which}:InvalidK")
            k = int(kk[0])
        n = A.nrows if _is_table(A) else height_of(A)
        k = min(k, n)
        rows = np.arange(k) if which == "head" else np.arange(n - k, n)
        if _is_table(A):
            return (A.take_rows(_ev(), rows),)
        return (_col_rows(A, rows),)
    return f


# =====================================================================
# varfun / rowfun
# =====================================================================
def _fh(v, fn):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if not isinstance(v, FunctionHandleValue):
        raise _err(f"{fn}: the first input must be a function handle.", f"MATLAB:table:{fn}:InvalidFunction")
    return v


def _fname(fh):
    n = getattr(fh, "name", "") or ""
    return "Fun" if n.startswith("@") or not n else n.split(".")[-1]


def _bool_opt(v):
    return bool(np.asarray(v.backend_buffer()).reshape(-1)[0])


def _outfmt(opts, fn):
    if "outputformat" not in opts:
        return "table"
    f = text(opts["outputformat"]).lower() if is_text(opts["outputformat"]) else ""
    if f not in ("table", "uniform", "cell"):
        raise _err(f"{fn}: 'OutputFormat' must be 'table', 'uniform' or 'cell'.", f"MATLAB:table:{fn}:InvalidOutputFormat")
    return f


def _call1(fh, args, fn):
    r = fh.call(list(args), nargout=1)
    if not r:
        raise _err(f"{fn}: the function did not return a value.", f"MATLAB:table:{fn}:NoOutput")
    return r[0]


def _uniform_scalar(v, fn):
    if getattr(v, "is_object", False) or is_text(v) or not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: with 'OutputFormat','uniform' the function must return a numeric or logical scalar.",
                   f"MATLAB:table:{fn}:NotAScalarOutput")
    a = np.asarray(v.backend_buffer())
    if a.size != 1:
        raise _err(f"{fn}: with 'OutputFormat','uniform' the function must return a numeric or logical scalar.",
                   f"MATLAB:table:{fn}:NotAScalarOutput")
    return a.reshape(-1)[0]


def _varfun(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    data, opts = _opts(args, ("inputvariables", "outputformat", "groupingvariables"), "varfun")
    if len(data) != 2:
        raise _err("varfun: expected varfun(func, T, ...).", "MATLAB:narginchk:notEnoughInputs")
    fh = _fh(data[0], "varfun")
    T = _need_table(data[1], "varfun")
    if "groupingvariables" in opts:
        raise _err("varfun: 'GroupingVariables' is not supported yet; use groupsummary or splitapply.",
                   "MATLAB:table:varfun:Unsupported")
    idx = T.var_sel(opts["inputvariables"]) if "inputvariables" in opts else list(range(len(T.names)))
    fmt = _outfmt(opts, "varfun")
    res = [_call1(fh, [T.cols[i]], "varfun") for i in idx]
    if fmt == "uniform":
        return (NDArrayValue(np.array([[_uniform_scalar(v, "varfun") for v in res]], dtype=float)),)
    if fmt == "cell":
        return (CellValue(rows=(tuple(res),)) if res else CellValue(rows=()),)
    names = [f"{_fname(fh)}_{T.names[i]}" for i in idx]
    hs = {height_of(v) for v in res}
    if len(hs) > 1:
        raise _err("varfun: the function returned outputs with different numbers of rows for different variables.",
                   "MATLAB:table:varfun:OutputRowsMismatch")
    n = hs.pop() if hs else 0
    rn = T.rownames if (T.rownames and n == T.nrows) else None
    return (TableValue(names, res, n, rn),)


def _row_args(T, idx, r):
    from openmatlab.runtime.cell_value import CellValue

    out = []
    for i in idx:
        c = T.cols[i]
        out.append(_col_rows(c, [r]))
    return out


def _rowfun(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    data, opts = _opts(args, ("inputvariables", "outputformat", "outputvariablenames", "numoutputs",
                              "groupingvariables", "separateinputs"), "rowfun")
    if len(data) != 2:
        raise _err("rowfun: expected rowfun(func, T, ...).", "MATLAB:narginchk:notEnoughInputs")
    fh = _fh(data[0], "rowfun")
    T = _need_table(data[1], "rowfun")
    if "groupingvariables" in opts:
        raise _err("rowfun: 'GroupingVariables' is not supported yet; use splitapply.", "MATLAB:table:rowfun:Unsupported")
    idx = T.var_sel(opts["inputvariables"]) if "inputvariables" in opts else list(range(len(T.names)))
    fmt = _outfmt(opts, "rowfun")
    outnames = texts(opts["outputvariablenames"]) if "outputvariablenames" in opts else None
    if "outputvariablenames" in opts and outnames is None:
        raise _err("rowfun: 'OutputVariableNames' must be text.", "MATLAB:table:rowfun:InvalidVarNames")
    nout = int(np.asarray(opts["numoutputs"].backend_buffer()).reshape(-1)[0]) if "numoutputs" in opts else (
        len(outnames) if outnames else 1)
    separate = _bool_opt(opts["separateinputs"]) if "separateinputs" in opts else True
    results = []
    for r in range(T.nrows):
        a = _row_args(T, idx, r)
        if not separate:
            a = [_ev().concat_values([a])]
        out = fh.call(a, nargout=nout) if nout else fh.call(a, nargout=0)
        if len(out) < nout:
            raise _err("rowfun: the function returned fewer outputs than 'NumOutputs'.", "MATLAB:table:rowfun:TooFewOutputs")
        results.append(list(out[:nout]))
    if fmt == "cell":
        return (CellValue(rows=tuple(tuple(r) for r in results)) if results else CellValue(rows=()),)
    if fmt == "uniform":
        outs = [NDArrayValue(np.array([[_uniform_scalar(results[r][k], "rowfun")] for r in range(T.nrows)], dtype=float)
                             .reshape(T.nrows, 1)) for k in range(nout)]
        return tuple(outs[:max(1, nargout)])
    cols = []
    for k in range(nout):
        vals = [results[r][k] for r in range(T.nrows)]
        cols.append(_ev().concat_values([[v] for v in vals]) if vals else NDArrayValue(np.zeros((0, 1))))
    names = outnames or [f"Var{k + 1}" for k in range(nout)]
    if len(names) != nout:
        raise _err("rowfun: 'OutputVariableNames' must have one name per output.", "MATLAB:table:rowfun:InvalidVarNames")
    for c in cols:
        if height_of(c) != T.nrows:
            raise _err("rowfun: each function output must have one row per table row.", "MATLAB:table:rowfun:OutputRowsMismatch")
    return (TableValue(names, cols, T.nrows, T.rownames),)


# =====================================================================
# variable management
# =====================================================================
def _removevars(args, *, nargout=1):
    if len(args) != 2:
        raise _err("removevars: expected removevars(T, vars).", "MATLAB:narginchk:notEnoughInputs")
    T = _need_table(args[0], "removevars")
    drop = set(T.var_sel(args[1]))
    keep = [i for i in range(len(T.names)) if i not in drop]
    return (T.copy(names=[T.names[i] for i in keep], cols=[T.cols[i] for i in keep]),)


def _renamevars(args, *, nargout=1):
    if len(args) != 3:
        raise _err("renamevars: expected renamevars(T, vars, newNames).", "MATLAB:narginchk:notEnoughInputs")
    T = _need_table(args[0], "renamevars")
    idx = T.var_sel(args[1])
    new = texts(args[2])
    if new is None or len(new) != len(idx):
        raise _err("renamevars: the number of new names must match the number of variables to rename.",
                   "MATLAB:table:renamevars:NumNamesMismatch")
    names = list(T.names)
    for i, n in zip(idx, new):
        names[i] = n
    return (T.copy(names=names),)


def _location(T, opts, fn):
    if "before" in opts and "after" in opts:
        raise _err(f"{fn}: specify either 'Before' or 'After', not both.", f"MATLAB:table:{fn}:BeforeAndAfter")
    if "before" in opts:
        sel = T.var_sel(opts["before"])
        return ("before", sel[0]) if len(sel) == 1 else _bad_loc(fn)
    if "after" in opts:
        sel = T.var_sel(opts["after"])
        return ("after", sel[0]) if len(sel) == 1 else _bad_loc(fn)
    return ("end", None)


def _bad_loc(fn):
    raise _err(f"{fn}: the location must specify exactly one variable.", f"MATLAB:table:{fn}:InvalidLocation")


def _movevars(args, *, nargout=1):
    data, opts = _opts(args, ("before", "after"), "movevars")
    if len(data) != 2:
        raise _err("movevars: expected movevars(T, vars, 'Before'|'After', location).", "MATLAB:narginchk:notEnoughInputs")
    T = _need_table(data[0], "movevars")
    moving = T.var_sel(data[1])
    where, at = _location(T, opts, "movevars")
    rest = [i for i in range(len(T.names)) if i not in moving]
    if where == "end":
        order = rest + moving
    else:
        if at in moving:
            # anchor is one of the moved variables: place relative to its original neighbours
            rest_pos = sum(1 for i in rest if i < at) if where == "before" else sum(1 for i in rest if i <= at)
        else:
            rest_pos = rest.index(at) + (0 if where == "before" else 1)
        order = rest[:rest_pos] + moving + rest[rest_pos:]
    return (T.copy(names=[T.names[i] for i in order], cols=[T.cols[i] for i in order]),)


def _addvars(args, *, nargout=1):
    data, opts = _opts(args, ("before", "after", "newvariablenames"), "addvars")
    if len(data) < 2:
        raise _err("addvars: expected addvars(T, var1, ..., varN).", "MATLAB:narginchk:notEnoughInputs")
    T = _need_table(data[0], "addvars")
    new = list(data[1:])
    if "newvariablenames" in opts:
        names = texts(opts["newvariablenames"])
        if names is None or len(names) != len(new):
            raise _err("addvars: 'NewVariableNames' must have one name per new variable.",
                       "MATLAB:table:addvars:NumNamesMismatch")
    else:
        from openmatlab.libs.table_builtins import _caller_arg_names

        given = _caller_arg_names(len(data))[1:]
        names = [g if g else f"Var{len(T.names) + k + 1}" for k, g in enumerate(given)]
    for v in new:
        if height_of(v) != T.nrows:
            raise _err("addvars: the new variables must have the same number of rows as the table.",
                       "MATLAB:table:addvars:RowMismatch")
    where, at = _location(T, opts, "addvars")
    pos = len(T.names) if where == "end" else (at if where == "before" else at + 1)
    return (T.copy(names=T.names[:pos] + names + T.names[pos:], cols=T.cols[:pos] + new + T.cols[pos:]),)


# =====================================================================
# rank keys
# =====================================================================
def _ranks_of_strings(vals):
    """vals: list of str or None (missing) -> float ranks, missing = NaN."""
    present = sorted({v for v in vals if v is not None})
    pos = {v: k for k, v in enumerate(present)}
    return np.array([np.nan if v is None else float(pos[v]) for v in vals])


def rank_columns(c, n):
    """A table variable -> list of float rank arrays (length n); NaN marks missing values."""
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    if getattr(c, "is_categorical", False):
        codes = c.codes.reshape(n, -1, order="F").astype(float)
        codes[codes == 0] = np.nan
        return [codes[:, j] for j in range(codes.shape[1])]
    if isinstance(c, (DatetimeValue, DurationValue)):
        v = c.v.reshape(n, -1, order="F")
        return [v[:, j] for j in range(v.shape[1])]
    if getattr(c, "is_string", False):
        from openmatlab.runtime import string_array as sa

        a = np.asarray(sa.to_grid(c), dtype=object).reshape(n, -1)
        return [_ranks_of_strings([None if x is None else str(x) for x in a[:, j]]) for j in range(a.shape[1])]
    if isinstance(c, CellValue):
        if c.shape[1] != 1 or any(not (isinstance(c.rows[r][0], CharValue) and c.rows[r][0].shape[0] <= 1)
                                  for r in range(n)):
            raise _err("Sorting and set operations on a cell variable require a cell array of character vectors.",
                       "MATLAB:table:sortrows:CellVarNotCellstr")
        return [_ranks_of_strings([c.rows[r][0].text for r in range(n)])]
    if isinstance(c, CharValue):
        rows = c.text.split("\n") if c.shape[0] > 1 else [c.text]
        return [_ranks_of_strings(rows[:n])]
    if hasattr(c, "backend_buffer") and not getattr(c, "is_object", False):
        a = np.asarray(c.backend_buffer())
        if np.iscomplexobj(a):
            a = np.abs(a)
        a = a.astype(float).reshape(n, -1) if a.size else np.zeros((n, 0))
        return [a[:, j] for j in range(a.shape[1])]
    raise _err(f"Sorting and set operations are not supported for table variables of class '{c.matlab_class()}'.",
               "MATLAB:table:sortrows:UnsupportedVarType")


def _sort_order(keys, dirs):
    """Stable multi-key argsort; NaN last ascending, first descending (MATLAB)."""
    n = len(keys[0]) if keys else 0
    order = np.arange(n)
    for k, d in reversed(list(zip(keys, dirs))):
        v = k[order]
        if d == "descend":
            v = np.where(np.isnan(v), -np.inf, -v)
        else:
            v = np.where(np.isnan(v), np.inf, v)
        order = order[np.argsort(v, kind="stable")]
    return order


def _var_dir_spec(T, args, fn):
    """(var indices or 'rownames', directions) from sortrows/issortedrows trailing inputs."""
    rest = list(args)
    opts = {}
    while len(rest) >= 2 and is_text(rest[-2]) and text(rest[-2]).lower() in ("missingplacement", "comparisonmethod"):
        opts[text(rest[-2]).lower()] = rest[-1]
        rest = rest[:-2]
    if opts:
        raise _err(f"{fn}: 'MissingPlacement' and 'ComparisonMethod' are not supported yet.", f"MATLAB:table:{fn}:Unsupported")
    vars_ = None
    dirs = None
    if rest:
        first = rest[0]
        t = texts(first)
        if t is not None and all(s.lower() in ("ascend", "descend") for s in t) and len(rest) == 1:
            dirs = [s.lower() for s in t]
        else:
            if t is not None and t == ["RowNames"] or (t is not None and T.rownames is None and t == ["Row"]):
                vars_ = "rownames"
            elif hasattr(first, "backend_buffer") and not is_text(first) and not getattr(first, "is_string", False) \
                    and np.asarray(first.backend_buffer()).dtype != np.bool_:
                a = np.asarray(first.backend_buffer(), float).reshape(-1)
                vars_ = T.var_sel(_num(np.abs(a)).__class__(np.abs(a).reshape(1, -1)))
                dirs = ["descend" if x < 0 else "ascend" for x in a]
            else:
                vars_ = T.var_sel(first)
            if len(rest) > 1:
                d = texts(rest[1])
                if d is None or not all(s.lower() in ("ascend", "descend") for s in d):
                    raise _err(f"{fn}: sorting direction must be 'ascend' or 'descend'.", f"MATLAB:table:{fn}:InvalidDirection")
                dirs = [s.lower() for s in d]
            if len(rest) > 2:
                raise _err(f"{fn}: too many input arguments.", "MATLAB:TooManyInputs")
    if vars_ is None:
        vars_ = list(range(len(T.names)))
    nk = 1 if vars_ == "rownames" else len(vars_)
    if dirs is None:
        dirs = ["ascend"] * nk
    if len(dirs) == 1 and nk > 1:
        dirs = dirs * nk
    if len(dirs) != nk:
        raise _err(f"{fn}: the number of sorting directions must match the number of sorting variables.",
                   f"MATLAB:table:{fn}:DirectionsMismatch")
    return vars_, dirs


def _keys_dirs(T, vars_, dirs):
    if vars_ == "rownames":
        if not T.rownames:
            raise _err("The table has no row names to sort by.", "MATLAB:table:sortrows:NoRowNames")
        return [_ranks_of_strings(list(T.rownames))], dirs
    keys, kd = [], []
    for i, d in zip(vars_, dirs):
        for k in rank_columns(T.cols[i], T.nrows):
            keys.append(k)
            kd.append(d)
    return keys, kd


def _wrap_sortrows(orig):
    def f(args, *, nargout=1):
        if args and _is_table(args[0]):
            T = args[0]
            vars_, dirs = _var_dir_spec(T, args[1:], "sortrows")
            keys, kd = _keys_dirs(T, vars_, dirs)
            order = _sort_order(keys, kd) if keys else np.arange(T.nrows)
            out = T.take_rows(_ev(), order)
            return (out, _num((order + 1).astype(float)))[:max(1, nargout)]
        return orig(args, nargout=nargout)
    return f


def _issortedrows(args, *, nargout=1):
    if not args:
        raise _err("issortedrows: not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    if not _is_table(args[0]):
        from openmatlab.libs.numeric_builtins import BUILTINS

        S = BUILTINS["sortrows"](list(args), nargout=2)
        idx = np.asarray(S[1].backend_buffer()).reshape(-1)
        return (_bool(np.array_equal(idx, np.arange(1, idx.size + 1)) or _equal_values(S[0], args[0])),)
    T = args[0]
    vars_, dirs = _var_dir_spec(T, args[1:], "issortedrows")
    keys, kd = _keys_dirs(T, vars_, dirs)
    if not keys or T.nrows < 2:
        return (_bool(True),)
    order = _sort_order(keys, kd)
    K = np.column_stack([np.where(np.isnan(k), np.inf, k) for k in keys])
    return (_bool(np.array_equal(K[order], K)),)


def _equal_values(a, b):
    try:
        return np.array_equal(np.asarray(a.backend_buffer()), np.asarray(b.backend_buffer()), equal_nan=True)
    except Exception:
        return False


# =====================================================================
# unique / ismember on tables
# =====================================================================
def _row_keys(T):
    """Hashable per-row keys, comparable across tables with the same variables."""
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    per_col = []
    for c in T.cols:
        n = T.nrows
        if getattr(c, "is_categorical", False):
            labs = c.labels()
            per_col.append([("c", labs[r]) for r in range(n)])
        elif isinstance(c, (DatetimeValue, DurationValue)):
            v = c.v.reshape(n, -1, order="F")
            per_col.append([("t", tuple(v[r])) for r in range(n)])
        elif getattr(c, "is_string", False):
            from openmatlab.runtime import string_array as sa

            a = np.asarray(sa.to_grid(c), dtype=object).reshape(n, -1)
            per_col.append([("s", tuple(a[r])) for r in range(n)])
        elif isinstance(c, CellValue):
            rank_columns(c, n)  # validates cellstr
            per_col.append([("s", (c.rows[r][0].text,)) for r in range(n)])
        elif isinstance(c, CharValue):
            rows = c.text.split("\n") if c.shape[0] > 1 else [c.text]
            per_col.append([("s", (rows[r],)) for r in range(n)])
        else:
            rank_columns(c, n)  # validates type
            a = np.asarray(c.backend_buffer()).astype(float).reshape(n, -1)
            per_col.append([("n", tuple(a[r])) for r in range(n)])
    return [tuple(col[r] for col in per_col) for r in range(T.nrows)]


def _table_unique(T, nargout):
    keys, kd = _keys_dirs(T, list(range(len(T.names))), ["ascend"] * len(T.names))
    order = _sort_order(keys, kd) if keys else np.arange(T.nrows)
    rk = _row_keys(T)
    first = {}
    for i in order:
        first.setdefault(rk[i], i)
    ia = []
    seen = set()
    for i in order:
        if rk[i] not in seen:
            seen.add(rk[i])
            ia.append(first[rk[i]])
    pos = {rk[i]: k for k, i in enumerate(ia)}
    ic = [pos[rk[i]] + 1 for i in range(T.nrows)]
    C = T.take_rows(_ev(), np.array(ia, dtype=int))
    return (C, _num(np.array(ia, float) + 1), _num(np.array(ic, float)))[:max(1, nargout)]


def _wrap_unique(orig):
    def f(args, *, nargout=1):
        if args and _is_table(args[0]):
            extra = [text(a).lower() for a in args[1:] if is_text(a)]
            if any(e not in ("sorted", "rows") for e in extra) or len(extra) != len(args) - 1:
                raise _err("unique: only the 'sorted' and 'rows' options are supported for tables.",
                           "MATLAB:table:unique:UnsupportedOption")
            return _table_unique(args[0], nargout)
        return orig(args, nargout=nargout)
    return f


def _wrap_ismember(orig):
    def f(args, *, nargout=1):
        if len(args) >= 2 and (_is_table(args[0]) or _is_table(args[1])):
            A, B = args[0], args[1]
            if not (_is_table(A) and _is_table(B)):
                raise _err("ismember: a table can only be compared with another table.", "MATLAB:table:setmembership:TypeMismatch")
            if sorted(A.names) != sorted(B.names):
                raise _err("ismember: the tables must have the same variable names.", "MATLAB:table:setmembership:DisjointVars")
            B2 = B.take_vars([B.names.index(n) for n in A.names])
            kb = _row_keys(B2)
            first = {}
            for i, k in enumerate(kb):
                first.setdefault(k, i)
            ka = _row_keys(A)
            tf = np.array([k in first for k in ka]).reshape(-1, 1)
            loc = np.array([first.get(k, -1) + 1 for k in ka], float).reshape(-1, 1)
            return (NDArrayValue(tf), NDArrayValue(loc))[:max(1, nargout)]
        if args and getattr(args[0], "is_categorical", False):
            return _cat_ismember(args, nargout)
        return orig(args, nargout=nargout)
    return f


# =====================================================================
# categorical sort / ismember
# =====================================================================
def _cat_ismember(args, nargout):
    a = args[0]
    b = args[1]
    if getattr(b, "is_categorical", False):
        labels_b = [s for s in b.labels()]
    else:
        labels_b = texts(b)
        if labels_b is None:
            raise _err("ismember: a categorical array can only be compared with categorical arrays or text.",
                       "MATLAB:categorical:ismember:TypeMismatch")
    from openmatlab.runtime.categorical_value import UNDEF

    first = {}
    for i, s in enumerate(labels_b):
        if s != UNDEF:
            first.setdefault(s, i)
    labs = a.labels()
    tf = np.array([s in first for s in labs]).reshape(a.shape, order="F")
    loc = np.array([first.get(s, -1) + 1 for s in labs], float).reshape(a.shape, order="F")
    return (NDArrayValue(tf), NDArrayValue(loc))[:max(1, nargout)]


def _wrap_sort(orig):
    def f(args, *, nargout=1):
        if args and getattr(args[0], "is_categorical", False):
            c = args[0]
            direction = "ascend"
            dim = None
            for a in args[1:]:
                if is_text(a):
                    d = text(a).lower()
                    if d not in ("ascend", "descend"):
                        raise _err("sort: direction must be 'ascend' or 'descend'.", "MATLAB:sort:InvalidDirection")
                    direction = d
                else:
                    dim = int(np.asarray(a.backend_buffer()).reshape(-1)[0])
            codes = c.codes.astype(float)
            codes[codes == 0] = np.nan
            if dim is None:
                dim = 1 if codes.shape[0] != 1 else 2
            ax = dim - 1
            if ax > 1:
                return (c, _num(np.ones(c.shape)))[:max(1, nargout)]
            v = np.where(np.isnan(codes), -np.inf, -codes) if direction == "descend" else \
                np.where(np.isnan(codes), np.inf, codes)
            idx = np.argsort(v, axis=ax, kind="stable")
            out = np.take_along_axis(c.codes, idx, axis=ax)
            return (c.like(out), NDArrayValue((idx + 1).astype(float)))[:max(1, nargout)]
        return orig(args, nargout=nargout)
    return f


# =====================================================================
# summary
# =====================================================================
def _dims(shape):
    return "×".join(str(int(d)) for d in shape)


def _var_class_desc(c):
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(c, CellValue):
        try:
            if all(is_text(c.rows[r][0]) for r in range(c.shape[0])) and c.shape[1] == 1:
                return "cell array of character vectors"
        except Exception:
            pass
        return "cell"
    return c.matlab_class()


def _summary_lines(name, c, n):
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    shape = (n, int(np.prod(c.shape)) // n if n else 0) if hasattr(c, "shape") else (n, 1)
    lines = [f"    {name}: {_dims(shape)} {_var_class_desc(c)}"]
    stats = None
    if getattr(c, "is_categorical", False):
        counts = [(s, int(np.sum(c.codes == i + 1))) for i, s in enumerate(c.cats)]
        und = int(np.sum(c.codes == 0))
        if und:
            counts.append(("<undefined>", und))
        w = max([len(s) for s, _ in counts] + [1])
        lines += ["", "        Values:", ""] + [f"            {s.ljust(w)}    {k}" for s, k in counts]
    elif isinstance(c, (DatetimeValue, DurationValue)):
        v = c.v.reshape(-1)
        ok = v[~np.isnan(v)]
        if ok.size:
            def fmt(x):
                return type(c)._like(c, np.array([[x]])).display_text().strip()
            stats = [("Min", fmt(ok.min())), ("Median", fmt(np.median(ok))), ("Max", fmt(ok.max()))]
            miss = int(np.isnan(v).sum())
            if miss:
                stats.append(("NumMissing", str(miss)))
    elif hasattr(c, "backend_buffer") and not getattr(c, "is_object", False) and not is_text(c) \
            and not getattr(c, "is_string", False):
        a = np.asarray(c.backend_buffer())
        if a.dtype == np.bool_:
            stats = [("True", str(int(a.sum()))), ("False", str(int(a.size - a.sum())))]
        elif a.size and not np.iscomplexobj(a):
            a = a.astype(float).reshape(n, -1)
            from openmatlab.runtime.table_value import _fmt_num

            cols = []
            for j in range(a.shape[1]):
                col = a[:, j]
                ok = col[~np.isnan(col)]
                cols.append([_fmt_num(ok.min()) if ok.size else "NaN", _fmt_num(np.median(ok)) if ok.size else "NaN",
                             _fmt_num(ok.max()) if ok.size else "NaN", str(int(np.isnan(col).sum()))])
            labels = ["Min", "Median", "Max"] + (["NumMissing"] if any(int(cc[3]) for cc in cols) else [])
            stats = [(lab, "    ".join(cc[k] for cc in cols)) for k, lab in enumerate(labels)]
    if stats:
        w = max(len(s) for s, _ in stats)
        vw = max(len(v) for _, v in stats)
        lines += ["", "        Values:", ""] + [f"            {s.ljust(w)}    {v.rjust(vw)}" for s, v in stats]
    return lines + [""]


def _wrap_summary(orig):
    def f(args, *, nargout=1):
        if args and _is_table(args[0]):
            T = args[0]
            out = []
            if T.description:
                out += ["Description:  " + T.description, ""]
            out += ["Variables:", ""]
            for nme, c in zip(T.names, T.cols):
                out += _summary_lines(nme, c, T.nrows)
            sys.stdout.write("\n".join(out) + "\n")
            return ()
        return orig(args, nargout=nargout)
    return f


def register(builtins) -> None:
    builtins.update(table2array=_table2array, table2cell=_table2cell, table2struct=_table2struct,
                    head=_headtail("head"), tail=_headtail("tail"), varfun=_varfun, rowfun=_rowfun,
                    removevars=_removevars, renamevars=_renamevars, movevars=_movevars, addvars=_addvars,
                    issortedrows=_issortedrows)
    for name, w in (("sortrows", _wrap_sortrows), ("unique", _wrap_unique), ("ismember", _wrap_ismember),
                    ("sort", _wrap_sort), ("summary", _wrap_summary)):
        if name in builtins:
            builtins[name] = w(builtins[name])
