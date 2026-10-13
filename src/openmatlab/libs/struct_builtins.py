"""struct / fieldnames / isfield / rmfield / setfield / getfield / isstruct / orderfields (Epic #506)."""

from __future__ import annotations

from typing import Callable, Dict, List

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.struct_value import StructValue, is_struct
from openmatlab.runtime.value import Value


def _err(msg: str):
    from openmatlab.libs.numeric_builtins import BuiltinError

    return BuiltinError(msg)


def _text(v: Value, what: str = "Field names") -> str:
    if getattr(v, "is_string", False) and v.numel() == 1:
        g = v.data.flat[0] if hasattr(v, "data") else v.text
        if g is not None:
            return g
    if isinstance(v, CharValue) and len(v.rows) <= 1:
        return v.text
    raise _err(f"{what} must be character vectors or string scalars.")


def _names(v: Value, what: str = "Field names") -> List[str]:
    """Char/string scalar, string array, or cellstr → list of names."""
    if isinstance(v, CellValue):
        return [_text(x, what) for x in v.to_obj().reshape(-1, order="F")]
    if getattr(v, "is_string", False) and hasattr(v, "data"):
        return [str(x) for x in v.data.reshape(-1, order="F")]
    return [_text(v, what)]


def _valid(name: str) -> str:
    from openmatlab.runtime.struct_eval import valid_field

    try:
        return valid_field(name)
    except Exception as exc:
        raise _err(str(exc)) from None


def _need_struct(name: str, v: Value) -> StructValue:
    if not is_struct(v):
        raise _err(f"{name}: input must be a structure.")
    return v


def _cellstr_col(names) -> CellValue:
    return CellValue(rows=tuple((CharValue(n),) for n in names)) if names else CellValue.from_obj(
        np.empty((0, 1), dtype=object))


def _struct(args, *, nargout=1):
    if not args:
        return (StructValue.scalar(),)
    if len(args) == 1 and is_struct(args[0]):
        return (args[0],)
    if len(args) % 2:
        raise _err("struct: field and value input arguments must come in pairs.")
    pairs = [(_valid(_text(args[k])), args[k + 1]) for k in range(0, len(args), 2)]
    shape = None
    for _, v in pairs:  # every non-1x1 cell must have the same size (MATLAB)
        if isinstance(v, CellValue) and v.numel() != 1:
            s = tuple(v.full_shape)
            if shape is not None and s != shape:
                raise _err("struct: dimensions of cell array values must match.")
            shape = s
    if shape is None:
        shape = (1, 1)
    if len(shape) > 2:
        raise _err("struct: N-D struct arrays are not supported.")
    n = int(np.prod(shape))
    fields, elems = [], [dict() for _ in range(n)]
    for f, v in pairs:
        if f not in fields:
            fields.append(f)
        if isinstance(v, CellValue):
            flat = v.to_obj().reshape(-1, order="F")
            for k in range(n):
                elems[k][f] = flat[0] if v.numel() == 1 else flat[k]
        else:
            for k in range(n):
                elems[k][f] = v
    return (StructValue.build(shape, fields, elems),)


def _fieldnames(args, *, nargout=1):
    if len(args) != 1:
        raise _err("fieldnames: expected 1 argument")
    return (_cellstr_col(_need_struct("fieldnames", args[0]).fields),)


def _isfield(args, *, nargout=1):
    if len(args) != 2:
        raise _err("isfield: expected 2 arguments")
    s, f = args
    if isinstance(f, CellValue):
        obj = f.to_obj()
        out = np.zeros(obj.shape, dtype=bool)
        for ix in np.ndindex(*obj.shape):
            x = obj[ix]
            ok = isinstance(x, CharValue) and len(x.rows) <= 1
            out[ix] = bool(is_struct(s) and ok and x.text in s.fields)
        return (NDArrayValue(out),)
    try:
        name = _text(f)
    except Exception:
        return (NDArrayValue(np.array([[False]])),)
    return (NDArrayValue(np.array([[bool(is_struct(s) and name in s.fields)]])),)


def _rmfield(args, *, nargout=1):
    if len(args) != 2:
        raise _err("rmfield: expected 2 arguments")
    s = _need_struct("rmfield", args[0])
    names = _names(args[1])
    for n in names:
        if n not in s.fields:
            raise _err(f"A field named '{n}' doesn't exist.")
    return (s.without(set(names)),)


def _setfield(args, *, nargout=1):
    if len(args) < 3:
        raise _err("setfield: usage setfield(s, field, ..., value)")
    s, path, value = args[0], [_valid(_text(a)) for a in args[1:-1]], args[-1]

    def put(cur, names):
        if not names:
            return value
        if cur is None or not is_struct(cur):
            cur = StructValue.scalar()
        if cur.numel() != 1:
            raise _err("setfield: scalar structure required.")
        child = cur.get(names[0]) if cur.has(names[0]) else None
        return cur.with_field(names[0], put(child, names[1:]))

    return (put(s if is_struct(s) else None, path),)


def _getfield(args, *, nargout=1):
    if len(args) < 2:
        raise _err("getfield: usage getfield(s, field, ...)")
    cur = args[0]
    for a in args[1:]:
        name = _text(a)
        if not is_struct(cur):
            raise _err("Dot indexing is not supported for variables of this type.")
        if not cur.has(name):
            raise _err(f'Unrecognized field name "{name}".')
        if cur.numel() < 1:
            raise _err("getfield: structure is empty.")
        cur = cur.get(name)  # first element, as MATLAB's getfield(s, f) does
    return (cur,)


def _isstruct(args, *, nargout=1):
    if len(args) != 1:
        raise _err("isstruct: expected 1 argument")
    return (NDArrayValue(np.array([[is_struct(args[0])]])),)


def _orderfields(args, *, nargout=1):
    if len(args) not in (1, 2):
        raise _err("orderfields: usage orderfields(s[, order])")
    s = _need_struct("orderfields", args[0])
    if len(args) == 1:
        order = sorted(s.fields)
    elif is_struct(args[1]):
        order = list(args[1].fields)
    elif isinstance(args[1], CellValue) or getattr(args[1], "is_string", False):
        order = _names(args[1])
    else:
        p = np.asarray(args[1].backend_buffer()).reshape(-1)
        if sorted(int(x) for x in p) != list(range(1, len(s.fields) + 1)):
            raise _err("orderfields: the permutation vector must be a permutation of 1:numel(fieldnames(s)).")
        order = [s.fields[int(x) - 1] for x in p]
    if sorted(order) != sorted(s.fields):
        raise _err("orderfields: the new field names must be the same as the existing field names.")
    out = [s.reorder(order)]
    if nargout > 1:
        out.append(NDArrayValue(np.array([[float(s.fields.index(f) + 1)] for f in order]).reshape(-1, 1)))
    return tuple(out)


def register(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        struct=_struct, fieldnames=_fieldnames, isfield=_isfield, rmfield=_rmfield,
        setfield=_setfield, getfield=_getfield, isstruct=_isstruct, orderfields=_orderfields,
    )
