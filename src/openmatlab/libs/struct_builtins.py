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


# ----- #508 residuals: disp, is*, deal, struct2cell/cell2struct, structfun/arrayfun -----

def _disp(args, *, nargout=1):
    import sys

    from openmatlab.host.display import _format_value
    from openmatlab.runtime.value import Array

    if len(args) != 1:
        raise _err("disp: expected 1 argument")
    v = args[0]
    if isinstance(v, Array) and not is_struct(v) and v.numel() == 0:
        return ()
    if getattr(v, "is_string", False) and v.numel() == 1:
        g = v.data.flat[0] if hasattr(v, "data") else v.text
        text = "<missing>" if g is None else g
    elif is_struct(v) and v.numel() == 1:
        lines = _format_value(v).split("\n")
        text = "\n".join(lines[2:]) if v.fields else ""
    else:
        text = _format_value(v)
    if getattr(v, "is_string", False) and hasattr(v, "data") and v.numel() != 1 and "\n\n" in text:
        text = text.split("\n\n", 1)[1]  # body only, no "RxC string array" header
    sys.stdout.write(text + "\n")
    sys.stdout.flush()
    return ()


def _shape(v):
    from openmatlab.libs.numeric_builtins import _shape_of

    return tuple(_shape_of(v))


def _shape_pred(name, test):
    def _fn(args, *, nargout=1):
        if len(args) != 1:
            raise _err(f"{name}: expected 1 argument")
        return (NDArrayValue(np.array([[bool(test(_shape(args[0])))]])),)

    return _fn


def _deal(args, *, nargout=1):
    n = max(1, nargout)
    if len(args) == 1:
        return tuple(args[0] for _ in range(n))
    if len(args) != n:
        raise _err("deal: The number of outputs should match the number of inputs.")
    return tuple(args)


def _struct2cell(args, *, nargout=1):
    if len(args) != 1:
        raise _err("struct2cell: expected 1 argument")
    s = _need_struct("struct2cell", args[0])
    nf = len(s.fields)
    shape = (nf,) + tuple(s.shape)
    obj = np.empty(shape if s.numel() != 1 else (nf, 1), dtype=object)
    for k, e in enumerate(s.elems):
        idx = np.unravel_index(k, s.shape, order="F")
        for i, f in enumerate(s.fields):
            if s.numel() == 1:
                obj[i, 0] = e[f]
            else:
                obj[(i,) + tuple(idx)] = e[f]
    if nf == 0:
        obj = np.empty((0, 1), dtype=object)
    return (CellValue.from_obj(obj),)


def _cell2struct(args, *, nargout=1):
    if len(args) not in (2, 3):
        raise _err("cell2struct: usage cell2struct(c, fields[, dim])")
    c = args[0]
    if not isinstance(c, CellValue):
        raise _err("cell2struct: argument must be a cell array.")
    fields = [_valid(n) for n in _names(args[1])]
    dim = int(np.asarray(args[2].backend_buffer()).reshape(-1)[0]) if len(args) == 3 else 1
    obj = c.to_obj()
    if obj.ndim != 2 or dim not in (1, 2):
        raise _err("cell2struct: only 2-D cells with dim 1 or 2 are supported.")
    if obj.shape[dim - 1] != len(fields):
        raise _err("cell2struct: Number of field names must match number of fields in new structure.")
    if dim == 2:
        obj = obj.T
    elems = [{f: obj[i, k] for i, f in enumerate(fields)} for k in range(obj.shape[1])]
    return (StructValue.build((len(elems), 1), fields, elems),)


def _uniform_opt(name, rest):
    uniform, err = True, None
    i = 0
    while i < len(rest):
        key = rest[i]
        if isinstance(key, CharValue) and i + 1 < len(rest):
            k = key.text.lower()
            if k == "uniformoutput":
                uniform = bool(np.asarray(rest[i + 1].backend_buffer()).reshape(-1)[0])
            elif k == "errorhandler":
                err = rest[i + 1]
            else:
                raise _err(f"{name}: unsupported option '{key.text}'")
            i += 2
        else:
            raise _err(f"{name}: invalid option arguments")
    return uniform, err


def _handle(name, v, resolver=None):
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if not isinstance(v, FunctionHandleValue):
        raise _err(f"{name}: first argument must be a function handle")
    return v


def _collect(name, results_per_item, shape, uniform, nout):
    """Uniform: numeric arrays of `shape` per output; else cell arrays."""
    from openmatlab.runtime.value import Array

    outs = []
    for o in range(nout):
        vals = [r[o] for r in results_per_item]
        if uniform:
            arr = np.zeros(len(vals), dtype=np.float64)
            kinds = set()
            for k, v in enumerate(vals):
                if isinstance(v, CharValue) and not getattr(v, "is_string", False) and v.numel() == 1:
                    arr[k] = ord(v.text)
                    kinds.add("char")
                    continue
                if not isinstance(v, Array) or is_struct(v) or v.numel() != 1:
                    raise _err(f"{name}: Non-scalar in Uniform output, at index {k + 1}, output {o + 1}. "
                               "Set 'UniformOutput' to false.")
                b = np.asarray(v.backend_buffer())
                kinds.add("logical" if b.dtype == np.bool_ else "num")
                if np.iscomplexobj(b):
                    arr = arr.astype(complex)
                arr[k] = b.reshape(-1)[0]
            out = arr.reshape(shape, order="F") if len(vals) else np.zeros(shape)
            if kinds == {"logical"}:
                out = out.astype(bool)
            outs.append(NDArrayValue(out))
        else:
            obj = np.empty(len(vals), dtype=object)
            for k, v in enumerate(vals):
                obj[k] = v
            outs.append(CellValue.from_obj(obj.reshape(shape, order="F")))
    return tuple(outs)


def _elements(v):
    """Per-element values of an array argument (column-major) and its shape."""
    from openmatlab.runtime.value import Array

    if is_struct(v):
        return [v.element(k) for k in range(v.numel())], tuple(v.shape)
    if getattr(v, "is_graphics_handle", False):  # arrayfun over graphics handles (#768)
        return [v.rewrap(NDArrayValue(np.array([[i]]))) for i in v.ids], tuple(v.shape)
    if isinstance(v, CellValue):
        obj = v.to_obj()
        return ([CellValue.from_obj(np.array([[x]], dtype=object)) for x in obj.reshape(-1, order="F")],
                tuple(obj.shape))
    if getattr(v, "is_string", False) and hasattr(v, "data"):
        from openmatlab.runtime import string_array as sa

        return [sa.make(np.array([[x]], dtype=object)) for x in v.data.reshape(-1, order="F")], tuple(v.shape)
    if isinstance(v, CharValue):
        codes = [ch for row in v.rows for ch in row]
        r, c = v.shape
        flat = [v.rows[i][j] for j in range(c) for i in range(r)]
        return [CharValue(ch) for ch in flat], (r, c)
    if isinstance(v, Array):
        b = np.asarray(v.backend_buffer())
        b = b.reshape(1, 1) if b.ndim == 0 else b
        return [NDArrayValue(np.array([[x]], dtype=b.dtype)) for x in b.reshape(-1, order="F")], tuple(b.shape)
    return [v], (1, 1)


def _arrayfun(args, *, nargout=1):
    if len(args) < 2:
        raise _err("arrayfun: not enough input arguments")
    fh = _handle("arrayfun", args[0])
    k = 1
    arrays = []
    while k < len(args) and not (isinstance(args[k], CharValue) and args[k].text.lower() in
                                 ("uniformoutput", "errorhandler") and k >= 2):
        arrays.append(args[k])
        k += 1
    uniform, _ = _uniform_opt("arrayfun", list(args[k:]))
    items = [_elements(a) for a in arrays]
    shape = items[0][1]
    for el, sh in items[1:]:
        if sh != shape:
            raise _err("arrayfun: All of the input arguments must be of the same size and shape.")
    nout = max(1, nargout)
    results = []
    for i in range(len(items[0][0])):
        r = fh.call([el[i] for el, _ in items], nargout=nout)
        if len(r) < nout:
            raise _err("arrayfun: function returned too few outputs")
        results.append(list(r))
    return _collect("arrayfun", results, shape, uniform, nout)


def _structfun(args, *, nargout=1):
    if len(args) < 2:
        raise _err("structfun: not enough input arguments")
    fh = _handle("structfun", args[0])
    s = _need_struct("structfun", args[1])
    if s.numel() != 1:
        raise _err("structfun: Inputs to STRUCTFUN must be scalar structures.")
    uniform, _ = _uniform_opt("structfun", list(args[2:]))
    nout = max(1, nargout)
    results = [list(fh.call([s.get(f)], nargout=nout)) for f in s.fields]
    if uniform:
        return _collect("structfun", results, (len(s.fields), 1), True, nout)
    return tuple(StructValue.build((1, 1), s.fields, [{f: r[o] for f, r in zip(s.fields, results)}])
                 for o in range(nout))


def register_residuals(builtins: Dict[str, Callable]) -> None:
    builtins.update(
        disp=_disp, deal=_deal, struct2cell=_struct2cell, cell2struct=_cell2struct,
        structfun=_structfun, arrayfun=_arrayfun,
        isrow=_shape_pred("isrow", lambda s: len(s) == 2 and s[0] == 1),
        iscolumn=_shape_pred("iscolumn", lambda s: len(s) == 2 and s[1] == 1),
        isvector=_shape_pred("isvector", lambda s: len(s) == 2 and 1 in s and (s[0] * s[1]) >= 1),
        isscalar=_shape_pred("isscalar", lambda s: all(d == 1 for d in s)),
        ismatrix=_shape_pred("ismatrix", lambda s: len(s) == 2),
    )
