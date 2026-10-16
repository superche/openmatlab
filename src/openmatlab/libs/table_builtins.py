"""table construction and size builtins (M10 T-E1, Epic #691)."""

from __future__ import annotations

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.table_value import TableValue, _cv, _err, height_of, is_text, text, texts


def _num(x):
    return NDArrayValue(np.array([[float(x)]]))


def _bool(b):
    return NDArrayValue(np.array([[bool(b)]]))


def _split_opts(args, allowed):
    """Trailing Name,Value pairs (names from ``allowed``) -> (data args, {lower name: value})."""
    args = list(args)
    opts = {}
    i = 0
    data = []
    while i < len(args):
        a = args[i]
        if is_text(a) and text(a).lower() in allowed and i + 1 < len(args):
            opts[text(a).lower()] = args[i + 1]
            i += 2
            continue
        if opts:
            raise _err("Name-value arguments must come after all table variables.", "MATLAB:table:NVArgsAfterData")
        data.append(a)
        i += 1
    return data, opts


def _caller_arg_names(n):
    from openmatlab.lang import ast_nodes as ast
    from openmatlab.runtime import frames

    st = frames._STACK.get()
    exprs = getattr(st[-1], "_call_arg_exprs", None) or () if st else ()
    return [e.id if k < len(exprs) and isinstance(e, ast.Name) else "" for k, e in
            enumerate(list(exprs)[:n] + [None] * max(0, n - len(exprs)))]


def _names_opt(opts, n, default):
    if "variablenames" not in opts:
        return default
    names = texts(opts["variablenames"])
    if names is None or len(names) != n:
        raise _err("The VariableNames property must contain one name for each variable in the table.",
                   "MATLAB:table:IncorrectNumberOfVarNames")
    return names


def _rownames_opt(opts, n):
    if "rownames" not in opts:
        return None
    rn = texts(opts["rownames"])
    if rn is not None and len(rn) == 0:
        return None
    if rn is None or len(rn) != n:
        raise _err("The RowNames property must contain one name for each row in the table.",
                   "MATLAB:table:IncorrectNumberOfRowNames")
    if len(set(rn)) != len(rn):
        raise _err("Duplicate row names.", "MATLAB:table:DuplicateRowNames")
    return rn


def _make(cols, names, rownames=None):
    n = height_of(cols[0]) if cols else (len(rownames) if rownames else 0)
    for c in cols:
        if height_of(c) != n:
            raise _err("All table variables must have the same number of rows.", "MATLAB:table:UnequalVarLengths")
    return TableValue(names, cols, n, rownames)


def _table(args, *, nargout=1):
    data, opts = _split_opts(args, ("variablenames", "rownames", "size", "variabletypes", "dimensionnames"))
    if "size" in opts:
        raise _err("table: 'Size' / 'VariableTypes' preallocation is not supported yet.", "MATLAB:table:Unsupported")
    given = _caller_arg_names(len(data))
    default = [g if g else f"Var{k + 1}" for k, g in enumerate(given)]
    # a duplicate inferred name falls back to VarN (MATLAB)
    seen = set()
    for k, g in enumerate(default):
        if g in seen:
            default[k] = f"Var{k + 1}"
        seen.add(default[k])
    names = _names_opt(opts, len(data), default)
    n = height_of(data[0]) if data else 0
    rn = _rownames_opt(opts, n if data else len(texts(opts["rownames"]) or []) if "rownames" in opts else 0)
    return (_make(list(data), names, rn),)


def _array2table(args, *, nargout=1):
    data, opts = _split_opts(args, ("variablenames", "rownames"))
    if len(data) != 1 or not hasattr(data[0], "backend_buffer") or getattr(data[0], "is_object", False):
        raise _err("array2table: input must be a matrix.", "MATLAB:array2table:NDArray")
    a = np.asarray(data[0].backend_buffer())
    if a.ndim > 2:
        raise _err("array2table: input must be a 2-D matrix.", "MATLAB:array2table:NDArray")
    a = a.reshape(a.shape[0] if a.ndim else 1, -1)
    base = _caller_arg_names(1)[0] or "Var"
    default = [f"{base}{j + 1}" if base != "Var" else f"Var{j + 1}" for j in range(a.shape[1])]
    names = _names_opt(opts, a.shape[1], default)
    cols = [NDArrayValue(a[:, j:j + 1].copy()) for j in range(a.shape[1])]
    return (TableValue(names, cols, a.shape[0], _rownames_opt(opts, a.shape[0])),)


def _column_from_cells(cells):
    """cell2table / struct2table column rule: uniform numeric/logical scalars -> numeric column, else cell."""
    from openmatlab.runtime.cell_value import CellValue

    def scalar_num(v):
        return (hasattr(v, "backend_buffer") and not getattr(v, "is_object", False) and not is_text(v)
                and not getattr(v, "is_string", False) and np.asarray(v.backend_buffer()).size == 1)

    if cells and all(scalar_num(v) for v in cells):
        vals = [np.asarray(v.backend_buffer()).reshape(-1)[0] for v in cells]
        arr = np.array(vals).reshape(-1, 1)
        if arr.dtype != np.bool_:
            arr = arr.astype(np.float64)
        return NDArrayValue(arr)
    if cells and all(getattr(v, "is_string", False) and v.numel() == 1 for v in cells):
        from openmatlab.runtime import string_array as sa

        return sa.make(np.array([[str(v.data.flat[0])] for v in cells], dtype=object))
    return CellValue(rows=tuple((v,) for v in cells))


def _cell2table(args, *, nargout=1):
    from openmatlab.runtime.cell_value import CellValue

    data, opts = _split_opts(args, ("variablenames", "rownames"))
    if len(data) != 1 or not isinstance(data[0], CellValue):
        raise _err("cell2table: input must be a cell array.", "MATLAB:cell2table:NotCell")
    c = data[0]
    m, n = c.shape
    base = _caller_arg_names(1)[0] or "Var"
    default = [f"{base}{j + 1}" for j in range(n)]
    names = _names_opt(opts, n, default)
    cols = [_column_from_cells([c.rows[i][j] for i in range(m)]) for j in range(n)]
    return (TableValue(names, cols, m, _rownames_opt(opts, m)),)


def _struct2table(args, *, nargout=1):
    data, opts = _split_opts(args, ("rownames", "asarray"))
    if len(data) != 1 or not getattr(data[0], "is_struct", False):
        raise _err("struct2table: input must be a struct.", "MATLAB:struct2table:NotStruct")
    s = data[0]
    names = list(s.fields)
    if s.numel() == 1:
        cols = [s.get(f) for f in names]
        return (_make(cols, names, _rownames_opt(opts, height_of(cols[0]) if cols else 0)),)
    cols = [_column_from_cells([s.get(f, k) for k in range(s.numel())]) for f in names]
    return (TableValue(names, cols, s.numel(), _rownames_opt(opts, s.numel())),)


def _need_table(args, fn):
    if len(args) != 1:
        raise _err(f"{fn}: expected one input.", "MATLAB:minrhs" if not args else "MATLAB:TooManyInputs")
    if not getattr(args[0], "is_table", False):
        # height/width work on any array in MATLAB: rows / columns
        from openmatlab.libs.numeric_builtins import _shape_of

        return None, _shape_of(args[0])
    return args[0], args[0].shape


def _height(args, *, nargout=1):
    _t, sh = _need_table(args, "height")
    return (_num(sh[0]),)


def _width(args, *, nargout=1):
    _t, sh = _need_table(args, "width")
    return (_num(sh[1] if len(sh) > 1 else 1),)


def _istable(args, *, nargout=1):
    if len(args) != 1:
        raise _err("istable: expected one input.", "MATLAB:minrhs")
    return (_bool(getattr(args[0], "is_table", False)),)


def _isempty_fix(orig):
    def _wrapped(args, *, nargout=1):
        if len(args) == 1 and getattr(args[0], "is_table", False):
            return (_bool(args[0].numel() == 0),)
        return orig(args, nargout=nargout)

    return _wrapped


def _disp_fix(orig):
    def _wrapped(args, *, nargout=1):
        if len(args) == 1 and getattr(args[0], "is_table", False):
            import sys

            body = args[0].body_text()
            if body and args[0].nrows:
                sys.stdout.write(body + "\n\n")
            return ()
        return orig(args, nargout=nargout)

    return _wrapped


def register(builtins) -> None:
    builtins.update(table=_table, array2table=_array2table, cell2table=_cell2table, struct2table=_struct2table,
                    height=_height, width=_width, istable=_istable)
    for name, fix in (("isempty", _isempty_fix), ("disp", _disp_fix)):
        if name in builtins:
            builtins[name] = fix(builtins[name])
