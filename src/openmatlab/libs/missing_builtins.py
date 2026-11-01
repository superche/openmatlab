"""``ismissing``, ``rmmissing``, and ``fillmissing`` for the analyst path (M17, #1033).

``fillmissing`` accepts exactly three methods:

- ``'constant'`` — replace missing entries with a scalar (or, for a numeric array,
  one value per slice of the non-operating dimensions; for a table, a scalar or a
  cell array with one value per filled variable)
- ``'previous'`` — the previous non-missing entry; a leading gap stays missing
- ``'next'`` — the next non-missing entry; a trailing gap stays missing

Standard missing values follow the public definitions used by the rest of this
tree: NaN (double, single, duration), NaT (datetime), ``<missing>`` (string),
``<undefined>`` (categorical), a blank (char), and ``{''}`` (cell of character
vectors). Integer and logical arrays have none. Tables and timetables are
handled one variable at a time, down the rows, including a table with one row.
A char result stays char. Empty inputs keep their size.

Out of this issue: every other fill method (including ``movmean``), ``EndValues``,
``SamplePoints``, custom missing indicators, and ``standardizeMissing``.
"""

from __future__ import annotations

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue

_METHODS = ("constant", "previous", "next")
_UNSUPPORTED_METHODS = frozenset({
    "nearest", "linear", "spline", "pchip", "makima", "movmean", "movmedian", "knn",
})
_UNSUPPORTED_OPTIONS = frozenset({
    "endvalues", "samplepoints", "maxgap", "missinglocations", "replacevalues", "smoothingfactor",
})


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _class_name(v) -> str:
    return v.matlab_class() if hasattr(v, "matlab_class") else type(v).__name__


def _is_missing_scalar(v) -> bool:
    return bool(getattr(v, "is_missing_value", False))


def _keyword(v):
    """Scalar char or string, or None when ``v`` is not a keyword."""
    from openmatlab.runtime import string_array as sa
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue) and not getattr(v, "is_string", False):
        return v.text
    if getattr(v, "is_string", False) and v.numel() == 1:
        g = sa.to_grid(v).reshape(-1)[0]
        return None if g is None else str(g)
    return None


def _element_missing(e) -> bool:
    """One cell element. Empty char and ``missing`` count; a double NaN in a cell does not."""
    from openmatlab.runtime import string_array as sa
    from openmatlab.runtime.char_value import CharValue

    if _is_missing_scalar(e):
        return True
    if getattr(e, "is_string", False):
        if e.numel() != 1:
            return False
        return sa.to_grid(e).reshape(-1)[0] is None
    if isinstance(e, CharValue):
        return e.shape[0] == 0 and e.text == ""
    return False


def _none_mask(data: np.ndarray) -> np.ndarray:
    return np.array([x is None for x in data.reshape(-1)], dtype=bool).reshape(data.shape)


_CHAR_MISSING = ord(" ")


def _char_codes(v) -> np.ndarray:
    """Character codes for a char array. A blank (``' '``) is the standard missing value."""
    r, c = v.shape
    if r == 0 or c == 0:
        return np.zeros((r, c), dtype=np.int32)
    return np.array([[ord(ch) for ch in row] for row in v.rows], dtype=np.int32)


def _flat_width(shape) -> int:
    """Trailing-dimension product. Explicit, so a 0 leading size does not ask NumPy to infer it."""
    return int(np.prod(shape[1:], dtype=int))


def _logical(mask: np.ndarray) -> NDArrayValue:
    a = np.asarray(mask, dtype=bool)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(-1, 1)
    return NDArrayValue(a)


def _default_axis(shape) -> int:
    for i, n in enumerate(shape):
        if n != 1:
            return i
    return 0


def _row_any(mask: np.ndarray, nrows: int) -> np.ndarray:
    if mask.shape[:1] == (nrows,):
        return np.any(mask.reshape(nrows, _flat_width(mask.shape)), axis=1)
    if mask.size == nrows:
        return np.asarray(mask, dtype=bool).reshape(nrows)
    raise _err("A table variable must have one row for each row of the table.",
               "OpenMATLAB:ismissing:TableVariable")


def missing_mask(v) -> np.ndarray:
    """Boolean mask of standard missing entries. A table yields one column per variable."""
    from openmatlab.runtime import string_array as sa
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    if getattr(v, "is_table", False):
        out = np.zeros((v.nrows, len(v.names)), dtype=bool)
        for j, col in enumerate(v.cols):
            out[:, j] = _row_any(missing_mask(col), v.nrows)
        return out
    if _is_missing_scalar(v):
        return np.ones((1, 1), dtype=bool)
    if sa.is_string(v):
        return _none_mask(sa.to_grid(v))
    if getattr(v, "is_categorical", False):
        return np.equal(v.codes, 0)
    if isinstance(v, (DatetimeValue, DurationValue)):
        return np.isnan(v.v)
    if isinstance(v, CellValue):
        r, c = v.shape
        out = np.zeros((r, c), dtype=bool)
        for i in range(r):
            for j in range(c):
                out[i, j] = _element_missing(v.rows[i][j])
        return out
    if isinstance(v, CharValue) and not getattr(v, "is_string", False):
        return np.equal(_char_codes(v), _CHAR_MISSING)
    if hasattr(v, "backend_buffer") and not getattr(v, "is_object", False):
        a = np.asarray(v.backend_buffer())
        if a.dtype == np.bool_ or np.issubdtype(a.dtype, np.integer):
            return np.zeros(a.shape, dtype=bool)
        return np.isnan(a)
    return np.zeros(getattr(v, "shape", (1, 1)), dtype=bool)


class _Buf:
    __slots__ = ("data", "missing", "kind", "rebuild", "accept", "sparse")

    def __init__(self, data, missing, kind, rebuild, accept, sparse=False):
        self.data = data
        self.missing = missing
        self.kind = kind
        self.rebuild = rebuild
        self.accept = accept
        self.sparse = sparse


def _bad_const(const, what: str):
    raise _err(f"Cannot fill {what} with a value of class '{_class_name(const)}'.",
               "OpenMATLAB:fillmissing:ConstantType")


def _char_from_codes(data: np.ndarray):
    from openmatlab.runtime.char_value import CharValue

    a = np.asarray(data)
    if a.shape[0] == 0:
        return CharValue("")
    return CharValue(rows=["".join(chr(int(ch)) for ch in row) for row in a])


def _accept_char(const):
    from openmatlab.runtime.char_value import CharValue

    if isinstance(const, CharValue) and not getattr(const, "is_string", False):
        if const.numel() != 1:
            raise _err("The fill constant must be a scalar.", "OpenMATLAB:fillmissing:ConstantSize")
        return ord(const.text)
    _bad_const(const, "char data")


def _buffer(v):
    """Element buffer the three fill methods share. None when the value has no standard missing entries to write."""
    from openmatlab.runtime import string_array as sa
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.objects import DatetimeValue, DurationValue

    if _is_missing_scalar(v):
        data = np.array([[np.nan]])

        def accept(const, _data=data):
            return _accept_float(const, _data.dtype)

        return _Buf(data, np.ones((1, 1), dtype=bool), "float", lambda d: NDArrayValue(d), accept)
    if sa.is_string(v):
        data = sa.to_grid(v)

        def accept(const):
            if _is_missing_scalar(const):
                return None
            if getattr(const, "is_string", False) and const.numel() == 1:
                return sa.to_grid(const).reshape(-1)[0]
            if isinstance(const, CharValue) and const.shape[0] <= 1:
                return const.text
            _bad_const(const, "string data")

        return _Buf(data, _none_mask(data), "string", lambda d: sa.make(d), accept)
    if getattr(v, "is_categorical", False):
        holder = {"cats": list(v.cats)}

        def accept(const, _v=v, _holder=holder):
            if _is_missing_scalar(const):
                return 0
            codes, cats = _v.codes_for(const, grow=not _v.protected)
            if codes.size != 1:
                raise _err("The fill constant must be a scalar.", "OpenMATLAB:fillmissing:ConstantSize")
            code = int(codes.reshape(-1)[0])
            if code < 0:
                raise _err("Fill constant is not a category of this array.",
                           "OpenMATLAB:fillmissing:ConstantType")
            _holder["cats"] = cats
            return code

        return _Buf(v.codes.copy(), np.equal(v.codes, 0), "codes",
                    lambda d, _v=v, _holder=holder: _v.like(d, _holder["cats"]), accept)
    if isinstance(v, (DatetimeValue, DurationValue)):
        data = np.array(v.v, dtype=float, copy=True)

        def accept(const, _v=v):
            if _is_missing_scalar(const):
                return np.array(np.nan, dtype=float)
            if type(const) is type(_v):
                if const.numel() != 1:
                    raise _err("The fill constant must be a scalar.", "OpenMATLAB:fillmissing:ConstantSize")
                return np.array(float(const.v.reshape(-1)[0]), dtype=float)
            _bad_const(const, f"{_v.matlab_class()} data")

        return _Buf(data, np.isnan(data), "float", lambda d, _v=v: type(_v)._like(_v, d), accept)
    if isinstance(v, CellValue):
        r, c = v.shape
        data = np.empty((r, c), dtype=object)
        missing = np.zeros((r, c), dtype=bool)
        for i in range(r):
            for j in range(c):
                data[i, j] = v.rows[i][j]
                missing[i, j] = _element_missing(v.rows[i][j])

        def accept(const):
            if _is_missing_scalar(const):
                return CharValue("")
            if getattr(const, "is_string", False) and const.numel() == 1:
                g = sa.to_grid(const).reshape(-1)[0]
                return CharValue("" if g is None else str(g))
            if isinstance(const, CharValue) and const.shape[0] <= 1:
                return CharValue(const.text)
            if hasattr(const, "backend_buffer") and not getattr(const, "is_object", False) \
                    and np.asarray(const.backend_buffer()).size == 1:
                return const
            _bad_const(const, "cell data")

        def rebuild(d, _v=v):
            rows = tuple(tuple(d[i, j] for j in range(d.shape[1])) for i in range(d.shape[0]))
            return CellValue(rows=rows, nd=_v.nd)

        return _Buf(data, missing, "cell", rebuild, accept)
    if isinstance(v, CharValue) and not getattr(v, "is_string", False):
        data = _char_codes(v)
        return _Buf(data, np.equal(data, _CHAR_MISSING), "char", _char_from_codes, _accept_char)
    if hasattr(v, "backend_buffer") and not getattr(v, "is_object", False):
        a = np.asarray(v.backend_buffer())
        sparse = bool(getattr(v, "issparse", False))
        if a.dtype == np.bool_ or np.issubdtype(a.dtype, np.integer):
            return _Buf(a, np.zeros(a.shape, dtype=bool), "float", lambda _d, _v=v: _v, lambda _c: None, sparse)
        data = np.array(a, copy=True)

        def accept(const, _dtype=data.dtype):
            return _accept_float(const, _dtype)

        return _Buf(data, np.isnan(data), "float", lambda d: NDArrayValue(d), accept, sparse)
    return None


def _accept_float(const, dtype):
    if _is_missing_scalar(const):
        if not (np.issubdtype(dtype, np.floating) or np.issubdtype(dtype, np.complexfloating)):
            _bad_const(const, "numeric data")
        return np.array(np.nan, dtype=dtype)
    if not hasattr(const, "backend_buffer") or getattr(const, "is_object", False) or getattr(const, "issparse", False):
        _bad_const(const, "numeric data")
    vec = np.asarray(const.backend_buffer()).reshape(-1)
    if vec.size == 1:
        return np.array(vec[0], dtype=dtype)
    return np.asarray(vec, dtype=dtype)


def _mask_of(kind: str, data: np.ndarray) -> np.ndarray:
    if kind == "string":
        return _none_mask(data)
    if kind == "codes":
        return np.equal(data, 0)
    if kind == "cell":
        return np.array([_element_missing(x) for x in data.reshape(-1)], dtype=bool).reshape(data.shape)
    if kind == "char":
        return np.equal(data, _CHAR_MISSING)
    if data.dtype == np.bool_ or np.issubdtype(data.dtype, np.integer):
        return np.zeros(data.shape, dtype=bool)
    return np.isnan(data)


def _assign_missing(col: np.ndarray, miss: np.ndarray, scalar) -> None:
    if not np.any(miss):
        return
    if col.dtype == object:
        for i in np.flatnonzero(miss):
            col[i] = scalar
    else:
        col[miss] = scalar


def _propagate(col: np.ndarray, miss: np.ndarray, method: str) -> np.ndarray:
    """1-D previous/next. Index 0 is the sentinel for 'no previous valid entry yet'."""
    if method == "next":
        return _propagate(col[::-1], miss[::-1], "previous")[::-1].copy()
    if col.size == 0:
        return col.copy()
    idx = np.where(miss, 0, np.arange(col.shape[0]))
    np.maximum.accumulate(idx, out=idx)
    return col[idx]


def _fill_moved(data: np.ndarray, miss: np.ndarray, method: str, value) -> np.ndarray:
    n = data.shape[0]
    rest = _flat_width(data.shape)
    flat = data.reshape(n, rest).copy()
    m = miss.reshape(n, rest)
    vector = isinstance(value, np.ndarray) and value.ndim == 1 and value.size > 1
    if method == "constant" and vector and value.size != rest:
        raise _err(
            f"The fill constant must be a scalar or a vector of length {rest} "
            "(one value for each slice of the non-operating dimensions).",
            "OpenMATLAB:fillmissing:ConstantSize",
        )
    scalar = None
    if method == "constant" and not vector:
        scalar = value.reshape(-1)[0] if isinstance(value, np.ndarray) else value
    for j in range(rest):
        if method == "constant":
            _assign_missing(flat[:, j], m[:, j], value[j] if vector else scalar)
        else:
            flat[:, j] = _propagate(flat[:, j], m[:, j], method)
    return flat.reshape(data.shape)


def _operate(data, missing, method, value, axis: int):
    work_d, work_m = data, missing
    while work_d.ndim <= axis:
        work_d = work_d.reshape(work_d.shape + (1,))
        work_m = work_m.reshape(work_m.shape + (1,))
    filled = _fill_moved(np.moveaxis(work_d, axis, 0), np.moveaxis(work_m, axis, 0), method, value)
    back = np.moveaxis(filled, 0, axis)
    return back.reshape(data.shape) if back.ndim != data.ndim else back


def _fill_one(v, method: str, const, axis):
    buf = _buffer(v)
    shape = getattr(v, "shape", (1, 1))
    if buf is None:
        return v, np.zeros(shape, dtype=bool)
    if not np.any(buf.missing):
        return v, buf.missing
    if buf.sparse:
        raise _err("Sparse matrices are not supported.", "OpenMATLAB:fillmissing:Sparse")
    value = buf.accept(const) if method == "constant" else None
    if method == "constant" and isinstance(value, np.ndarray) and value.ndim == 1 and value.size > 1 \
            and buf.kind != "float":
        raise _err("The fill constant must be a scalar.", "OpenMATLAB:fillmissing:ConstantSize")
    ax = _default_axis(buf.data.shape) if axis is None else axis
    filled = _operate(buf.data, buf.missing, method, value, ax)
    tf = buf.missing & ~_mask_of(buf.kind, filled)
    if not np.any(tf):
        return v, tf
    return buf.rebuild(filled), tf


def _constants_for(const, n: int):
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(const, CellValue):
        elems = [const.rows[i][j] for j in range(const.shape[1]) for i in range(const.shape[0])]
        if len(elems) != n:
            raise _err(f"The fill constant cell must contain one value for each variable ({n}).",
                       "OpenMATLAB:fillmissing:ConstantSize")
        return elems
    if n != 1 and hasattr(const, "backend_buffer") and not getattr(const, "is_object", False) \
            and np.asarray(const.backend_buffer()).size > 1:
        raise _err("For a table, the fill constant must be a scalar or a cell array with one value per variable.",
                   "OpenMATLAB:fillmissing:ConstantSize")
    return [const] * n


def _fill_table(v, method: str, const, indices):
    from openmatlab.runtime.evaluator import EvalError

    consts = _constants_for(const, len(indices)) if method == "constant" else [None] * len(indices)
    cols = list(v.cols)
    tf = np.zeros((v.nrows, len(v.names)), dtype=bool)
    for k, j in enumerate(indices):
        try:
            # Dimension 1 of the variable. A one-row table must not fill across its columns.
            filled, mask = _fill_one(v.cols[j], method, consts[k], 0)
        except EvalError as exc:
            if exc.identifier == "OpenMATLAB:fillmissing:ConstantType":
                raise _err(f"{exc} (variable '{v.names[j]}').", exc.identifier) from exc
            raise
        cols[j] = filled
        tf[:, j] = _row_any(mask, v.nrows)
    return v.copy(cols=cols), tf


def _var_indices(v, spec, fn: str):
    if type(spec).__name__ == "FunctionHandleValue":
        raise _err(f"{fn}: DataVariables as a function handle is not supported. Pass variable names or indices.",
                   f"OpenMATLAB:{fn}:DataVariables")
    return v.var_sel(spec)


def _split(args, fn: str, ok: frozenset):
    positional, opts = [], {}
    known = ok | _UNSUPPORTED_OPTIONS | frozenset({"datavariables", "minnummissing"})
    i = 0
    while i < len(args):
        key = _keyword(args[i])
        if key is not None and key.lower() in known:
            if i + 1 >= len(args):
                raise _err(f"{fn}: missing value for '{key}'.", f"OpenMATLAB:{fn}:MissingOption")
            low = key.lower()
            if low not in ok:
                raise _err(f"'{key}' is not supported by {fn}.", f"OpenMATLAB:{fn}:UnsupportedOption")
            opts[low] = args[i + 1]
            i += 2
            continue
        if opts:
            raise _err(f"{fn}: name-value arguments must come at the end.", f"OpenMATLAB:{fn}:InvalidOption")
        positional.append(args[i])
        i += 1
    return positional, opts


def _dim(v, fn: str) -> int:
    if _keyword(v) is not None or not hasattr(v, "backend_buffer") or getattr(v, "is_object", False):
        raise _err(f"{fn}: dimension must be a positive integer scalar.", f"OpenMATLAB:{fn}:InvalidDimension")
    a = np.asarray(v.backend_buffer(), dtype=float).reshape(-1)
    if a.size != 1 or not np.isfinite(a[0]) or a[0] < 1 or a[0] != int(a[0]):
        raise _err(f"{fn}: dimension must be a positive integer scalar.", f"OpenMATLAB:{fn}:InvalidDimension")
    return int(a[0]) - 1


def _positive_int(v, name: str, fn: str) -> int:
    if not hasattr(v, "backend_buffer") or getattr(v, "is_object", False):
        raise _err(f"{fn}: '{name}' must be a positive integer.", f"OpenMATLAB:{fn}:InvalidOption")
    a = np.asarray(v.backend_buffer(), dtype=float).reshape(-1)
    if a.size != 1 or not np.isfinite(a[0]) or a[0] < 1 or a[0] != int(a[0]):
        raise _err(f"{fn}: '{name}' must be a positive integer.", f"OpenMATLAB:{fn}:InvalidOption")
    return int(a[0])


def _method_of(v) -> str:
    if type(v).__name__ == "FunctionHandleValue":
        raise _err("Function handles are not a supported fill method. Use 'constant', 'previous', or 'next'.",
                   "OpenMATLAB:fillmissing:UnsupportedMethod")
    key = _keyword(v)
    if key is None:
        raise _err("The fill method must be 'constant', 'previous', or 'next'.",
                   "OpenMATLAB:fillmissing:InvalidMethod")
    low = key.lower()
    if low in _UNSUPPORTED_METHODS:
        raise _err(f"Fill method '{key}' is not supported. Use 'constant', 'previous', or 'next'.",
                   "OpenMATLAB:fillmissing:UnsupportedMethod")
    if low not in _METHODS:
        raise _err(f"Invalid fill method '{key}'. Use 'constant', 'previous', or 'next'.",
                   "OpenMATLAB:fillmissing:InvalidMethod")
    return low


def _ismissing(args, *, nargout=1):
    if len(args) != 1:
        if not args:
            raise _err("Not enough input arguments.", "MATLAB:minrhs")
        raise _err("A missing-value indicator is not supported. Call ismissing(A) for standard missing values.",
                   "OpenMATLAB:ismissing:Indicator")
    return (_logical(missing_mask(args[0])),)


def _fillmissing(args, *, nargout=1):
    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    positional, opts = _split(args[1:], "fillmissing", frozenset({"datavariables"}))
    if not positional:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    method = _method_of(positional[0])
    rest = positional[1:]
    const = None
    if method == "constant":
        if not rest:
            raise _err("fillmissing: 'constant' requires a fill value, as in fillmissing(A,'constant',0).",
                       "OpenMATLAB:fillmissing:ConstantValueRequired")
        const = rest[0]
        rest = rest[1:]
    dim = None
    if rest:
        if len(rest) > 1 or _keyword(rest[0]) is not None:
            key = _keyword(rest[0])
            if key:
                raise _err(f"Unrecognized parameter name '{key}'.", "OpenMATLAB:fillmissing:InvalidOption")
            raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
        dim = _dim(rest[0], "fillmissing")
    src = args[0]
    if getattr(src, "is_table", False):
        if dim is not None:
            raise _err("fillmissing: a dimension is not supported for tables. Each variable is filled along its rows.",
                       "OpenMATLAB:fillmissing:TableDimension")
        indices = _var_indices(src, opts["datavariables"], "fillmissing") if "datavariables" in opts \
            else list(range(len(src.names)))
        filled, tf = _fill_table(src, method, const, indices)
    else:
        if "datavariables" in opts:
            raise _err("fillmissing: 'DataVariables' is only supported for tables.",
                       "OpenMATLAB:fillmissing:DataVariables")
        filled, tf = _fill_one(src, method, const, dim)
    if nargout > 1:
        return (filled, _logical(tf))
    return (filled,)


def _counts_along(mask: np.ndarray, axis: int) -> np.ndarray:
    work = mask
    while work.ndim <= axis:
        work = work.reshape(work.shape + (1,))
    moved = np.moveaxis(work, axis, 0)
    return np.sum(moved.reshape(moved.shape[0], _flat_width(moved.shape)), axis=1)


def _take_axis(data: np.ndarray, keep: np.ndarray, axis: int) -> np.ndarray:
    work = data
    while work.ndim <= axis:
        work = work.reshape(work.shape + (1,))
    taken = np.take(np.moveaxis(work, axis, 0), keep, axis=0)
    back = np.moveaxis(taken, 0, axis)
    return back.reshape(back.shape[:data.ndim]) if back.ndim != data.ndim else back


def _rm_array(v, axis: int, min_num: int):
    mask = missing_mask(v)
    if getattr(v, "issparse", False) and np.any(mask):
        raise _err("Sparse matrices are not supported.", "OpenMATLAB:rmmissing:Sparse")
    counts = _counts_along(mask, axis)
    drop = counts >= min_num
    keep = np.flatnonzero(~drop)
    if keep.size == counts.size:
        return v, drop
    buf = _buffer(v)
    if buf is None:
        raise _err(f"rmmissing does not support values of class '{_class_name(v)}'.",
                   "OpenMATLAB:rmmissing:UnsupportedType")
    return buf.rebuild(_take_axis(buf.data, keep, axis)), drop


def _tf_along(drop: np.ndarray, axis: int) -> np.ndarray:
    """Removed positions. Dimension 2 yields a row; every other dimension yields a column."""
    if axis == 1:
        return drop.reshape(1, -1)
    return drop.reshape(-1, 1)


def _rmmissing(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    positional, opts = _split(args[1:], "rmmissing", frozenset({"datavariables", "minnummissing"}))
    if len(positional) > 1:
        raise _err("Too many input arguments.", "MATLAB:TooManyInputs")
    if positional and _keyword(positional[0]) is not None:
        raise _err(f"Unrecognized parameter name '{_keyword(positional[0])}'.",
                   "OpenMATLAB:rmmissing:InvalidOption")
    src = args[0]
    dim = _dim(positional[0], "rmmissing") if positional else None
    min_num = _positive_int(opts["minnummissing"], "MinNumMissing", "rmmissing") if "minnummissing" in opts else 1
    if getattr(src, "is_table", False):
        if dim not in (None, 0):
            raise _err("rmmissing: removing table variables (dimension 2) is not supported. "
                       "Omit the dimension to remove rows.",
                       "OpenMATLAB:rmmissing:TableDimension")
        indices = _var_indices(src, opts["datavariables"], "rmmissing") if "datavariables" in opts \
            else list(range(len(src.names)))
        counts = np.zeros(src.nrows, dtype=int)
        for j in indices:
            counts += _row_any(missing_mask(src.cols[j]), src.nrows).astype(int)
        drop = counts >= min_num
        keep = np.flatnonzero(~drop)
        if keep.size != src.nrows:
            from openmatlab.libs.table_utils import _ev

            src = src.take_rows(_ev(), keep)
        tf = drop.reshape(-1, 1)
    else:
        if "datavariables" in opts:
            raise _err("rmmissing: 'DataVariables' is only supported for tables.",
                       "OpenMATLAB:rmmissing:DataVariables")
        shape = getattr(src, "shape", (1, 1))
        axis = _default_axis(shape) if dim is None else dim
        src, drop = _rm_array(src, axis, min_num)
        tf = _tf_along(drop, axis)
    if nargout > 1:
        return (src, _logical(tf))
    return (src,)


def register(builtins) -> None:
    builtins.update(ismissing=_ismissing, rmmissing=_rmmissing, fillmissing=_fillmissing)
