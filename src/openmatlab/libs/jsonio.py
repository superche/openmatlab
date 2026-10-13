"""jsonencode / jsondecode (M3-E5, #629).

Encoding: numeric/logical scalars become numbers/booleans (NaN and Inf become
null unless 'ConvertInfAndNaN' is false), vectors flat arrays, matrices and N-D
arrays row-major nested arrays, char rows and string scalars JSON strings,
scalar structs objects, struct arrays arrays of objects, cells arrays. Decoding
follows MATLAB's consolidation rules: null is [], numeric/boolean arrays become
column vectors (rectangular nested arrays become matrices, null inside numeric
arrays becomes NaN), arrays of objects with identical field names become an
Nx1 struct array, anything heterogeneous becomes an Nx1 cell. Object keys are
made valid with makeValidName rules.
"""

from __future__ import annotations

import json
import math
import re
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _text(v):
    t = getattr(v, "text", None)
    if t is None and getattr(v, "is_string", False) and getattr(v, "data", None) is not None and v.data.size == 1:
        t = v.data.flat[0]
    return t


# -- encode ------------------------------------------------------------------------------
def _num(x, nan_null):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    x = float(x)
    if math.isnan(x) or math.isinf(x):
        if nan_null:
            return None
        return _Raw("NaN" if math.isnan(x) else ("Infinity" if x > 0 else "-Infinity"))
    return int(x) if x == int(x) and abs(x) < 1e15 else x


class _Raw(str):
    pass


def _nest(a, nan_null):
    """Row-major nested lists for an array with ndim >= 2 (vectors already flattened)."""
    if a.ndim == 1:
        return [_num(x, nan_null) for x in a]
    return [_nest(a[i], nan_null) for i in range(a.shape[0])]


def _to_py(v, nan_null):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    if getattr(v, "is_object", False) or hasattr(v, "call"):
        raise _err(f"Unable to encode value of class {v.matlab_class()} as JSON.", "MATLAB:json:UnsupportedClass")
    if getattr(v, "is_struct", False):
        objs = [{f: _to_py(e[f], nan_null) for f in v.fields} for e in v.elems]
        return objs[0] if v.numel() == 1 else objs
    if isinstance(v, CellValue):
        return [_to_py(x, nan_null) for x in v.to_obj().reshape(-1, order="F")]
    if getattr(v, "is_string", False) and not isinstance(v, CharValue):
        items = [None if s is None else str(s) for s in v.data.reshape(-1, order="F")]
        return items[0] if len(items) == 1 else items
    if isinstance(v, CharValue):
        if getattr(v, "is_string", False) or len(v.rows) <= 1:
            return v.rows[0] if v.rows else ""
        return list(v.rows)
    a = np.asarray(v.backend_buffer())
    if np.iscomplexobj(a):
        raise _err("Complex values cannot be encoded as JSON.", "MATLAB:json:ComplexNotSupported")
    if a.dtype != bool:
        a = a.astype(float)
    if a.size == 1:
        return _num(a.reshape(-1)[0], nan_null)
    if a.ndim == 2 and (a.shape[0] == 1 or a.shape[1] == 1):
        return [_num(x, nan_null) for x in a.reshape(-1)]
    if a.size == 0:
        return []
    return _nest(a, nan_null)


def _dump(o, pretty, level=0):
    ind = "  " if pretty else ""
    nl = "\n" if pretty else ""
    sep = ": " if pretty else ":"
    pad, pad1 = ind * level, ind * (level + 1)
    if isinstance(o, _Raw):
        return str(o)
    if isinstance(o, dict):
        if not o:
            return "{}"
        body = ("," + nl).join(pad1 + json.dumps(k, ensure_ascii=False) + sep + _dump(x, pretty, level + 1) for k, x in o.items())
        return "{" + nl + body + nl + pad + "}"
    if isinstance(o, list):
        if not o:
            return "[]"
        body = ("," + nl).join(pad1 + _dump(x, pretty, level + 1) for x in o)
        return "[" + nl + body + nl + pad + "]"
    if isinstance(o, float):
        return repr(o)
    return json.dumps(o, ensure_ascii=False)


def _jsonencode(args, *, nargout=1):
    from openmatlab.runtime.char_value import CharValue

    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    nan_null, pretty = True, False
    rest = list(args[1:])
    if len(rest) % 2:
        raise _err("Name-value arguments must come in pairs.", "MATLAB:json:NameValuePairs")
    for k in range(0, len(rest), 2):
        name = (_text(rest[k]) or "").lower()
        val = bool(np.asarray(rest[k + 1].backend_buffer()).reshape(-1)[0])
        if name == "convertinfandnan":
            nan_null = val
        elif name == "prettyprint":
            pretty = val
        else:
            raise _err(f"Invalid option '{_text(rest[k])}'.", "MATLAB:json:InvalidOption")
    return [CharValue(_dump(_to_py(args[0], nan_null), pretty))]


# -- decode ------------------------------------------------------------------------------
def _valid_name(k):
    from keyword import iskeyword  # noqa: F401 (MATLAB keywords handled below)

    s = re.sub(r"[^A-Za-z0-9_]", "_", k)
    if not s or not s[0].isalpha():
        s = "x" + s
    if s in _MATLAB_KEYWORDS:
        s = "x" + s[0].upper() + s[1:]
    return s[:63]


_MATLAB_KEYWORDS = {"break", "case", "catch", "classdef", "continue", "else", "elseif", "end", "for", "function",
                    "global", "if", "otherwise", "parfor", "persistent", "return", "spmd", "switch", "try", "while"}


def _is_num(x):
    return x is None or (isinstance(x, (int, float)) and not isinstance(x, bool))


def _rect(o):
    """Shape of a rectangular nested list of non-list leaves, or None."""
    if not isinstance(o, list):
        return ()
    if not o:
        return None
    shapes = {_rect(x) for x in o}
    if len(shapes) != 1 or None in shapes:
        return None
    return (len(o),) + shapes.pop()


def _leaves(o):
    if isinstance(o, list):
        for x in o:
            yield from _leaves(x)
    else:
        yield o


def _from_py(o):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue

    if o is None:
        return NDArrayValue(np.zeros((0, 0)))
    if isinstance(o, bool):
        return NDArrayValue(np.array([[o]]))
    if isinstance(o, (int, float)):
        return NDArrayValue(np.array([[float(o)]]))
    if isinstance(o, str):
        return CharValue(o)
    if isinstance(o, dict):
        return StructValue.scalar(_fields(o))
    if not o:
        return NDArrayValue(np.zeros((0, 0)))
    shape = _rect(o)
    if shape is not None:
        leaves = list(_leaves(o))
        if all(_is_num(x) for x in leaves) and any(x is not None for x in leaves):
            a = np.array([np.nan if x is None else float(x) for x in leaves]).reshape(shape)
            return NDArrayValue(a.reshape(-1, 1) if a.ndim == 1 else a)
        if all(isinstance(x, bool) for x in leaves):
            a = np.array(leaves, dtype=bool).reshape(shape)
            return NDArrayValue(a.reshape(-1, 1) if a.ndim == 1 else a)
    if all(isinstance(x, dict) for x in o):
        keys = [tuple(_valid_name(k) for k in x) for x in o]
        if len(set(keys)) == 1:
            elems = [dict(_fields(x)) for x in o]
            return StructValue.build((len(o), 1), keys[0], elems)
    return CellValue.from_obj(np.array([_from_py(x) for x in o] + [None], dtype=object)[:-1].reshape(-1, 1))


def _fields(d):
    out, seen = [], set()
    for k, x in d.items():
        name = _valid_name(k)
        base, i = name, 1
        while name in seen:
            name = f"{base}_{i}"
            i += 1
        seen.add(name)
        out.append((name, _from_py(x)))
    return out


def _jsondecode(args, *, nargout=1):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:narginchk:notEnoughInputs")
    t = _text(args[0])
    if t is None:
        raise _err("Input must be a character vector or string scalar.", "MATLAB:json:ExpectedStringInput")
    try:
        o = json.loads(t, parse_constant=lambda c: {"NaN": float("nan"), "Infinity": float("inf"), "-Infinity": float("-inf")}[c])
    except json.JSONDecodeError as e:
        raise _err(f"JSON syntax error at line {e.lineno}, column {e.colno}: {e.msg}.", "MATLAB:json:SyntaxError") from None
    return [_from_py(o)]


def register(builtins: Dict[str, Callable]) -> None:
    builtins["jsonencode"] = _jsonencode
    builtins["jsondecode"] = _jsondecode
