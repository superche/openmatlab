"""Enumeration classes (M8 O-E5).

Each member is built once per class, in declaration order, and cached on the
ClassInfo: ``ClassName.Member`` always returns the same ``EnumMember``. A member
is an ordinary instance (its properties come from the constructor called with
the declared arguments) plus its name and, for a class derived from a numeric
builtin (``classdef L < int32``), its underlying value. Equality is identity of
the member; a numeric-derived member behaves as its value in relational and
arithmetic operators and in conversions. ``[A.x A.y]`` makes an ``EnumArray``
(enumeration object arrays only; general object arrays are a separate residual).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from openmatlab.runtime import classdef as cd

_NUMERIC = {"double", "single", "logical", "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64"}
_REL = {"==", "~=", "<", "<=", ">", ">="}


def _err(msg, ident=""):
    return cd._err(msg, ident)


class EnumMember(cd.ClassInstance):
    is_enum = True

    def __init__(self, info, props, name: str, index: int, value=None):
        super().__init__(info, props)
        self.enum_name, self.enum_index, self.builtin_value = name, index, value

    def with_raw(self, name, value):
        raise _err(f"Cannot set property '{name}' of enumeration member '{self.info.name}.{self.enum_name}'.",
                   "MATLAB:class:SetProhibited")

    def binop(self, op, other, reflected):
        return _binop(self, op, other, reflected)

    def display_text(self) -> str:
        return f"    {self.enum_name}"


def is_enum(v) -> bool:
    return bool(getattr(v, "is_enum", False)) or isinstance(v, EnumArray)


def numeric_base(info) -> Optional[str]:
    for c in info.mro():
        for b in c.builtin_bases:
            if b in _NUMERIC:
                return b
    return None


def members(info) -> Dict[str, EnumMember]:
    if info._enum_members is None:
        decls = _decls(info)
        if not decls:
            info._enum_members = {}
            return info._enum_members
        out: Dict[str, EnumMember] = {}
        info._enum_members = out  # members may refer to each other while building
        base = numeric_base(info)
        for i, d in enumerate(decls):
            args = [info._eval(a) for a in d.args]
            value = None
            if base is not None and info.constructor() is None:
                if len(args) != 1:
                    raise _err(f"Enumeration member '{d.name}' of class '{info.name}' needs exactly one value.",
                               "MATLAB:class:EnumerationArgs")
                value = info.resolver.resolve(base)([args[0]], nargout=1)[0]
                obj = info.new_instance()
            else:
                obj = cd.construct(info, args)
            out[d.name] = EnumMember(info, dict(obj.props), d.name, i, value)
    return info._enum_members


def _decls(info):
    for c in info.mro():
        if getattr(c.node, "enums", None):
            return c.node.enums
    return []


def member(info, name: str):
    return members(info).get(name)


# -- arrays ------------------------------------------------------------------------------
class EnumArray:
    """An N-by-M array of members of one enumeration class."""

    is_object = True
    is_enum_array = True

    def __init__(self, info, grid):
        self.info = info
        self.grid = np.asarray(grid, dtype=object)
        if self.grid.ndim != 2:
            self.grid = self.grid.reshape(1, -1)

    def matlab_class(self) -> str:
        return self.info.name

    @property
    def shape(self):
        return tuple(int(d) for d in self.grid.shape)

    @property
    def ndim(self):
        return 2

    def numel(self):
        return int(self.grid.size)

    def is_scalar(self):
        return self.grid.size == 1

    def flat(self) -> List[EnumMember]:
        return list(self.grid.reshape(-1, order="F"))

    def index(self, args):
        idx = []
        for a in args:
            if getattr(a, "is_colon", False) or getattr(a, "text", None) == ":":
                idx.append(slice(None))
                continue
            v = np.asarray(a.backend_buffer())
            idx.append(v.reshape(-1).astype(bool) if v.dtype == bool else v.reshape(-1).astype(int) - 1)
        try:
            if len(idx) == 1:
                flat = self.grid.reshape(-1, order="F")
                sel = flat[idx[0]]
                shape = (1, -1) if self.grid.shape[0] == 1 else (-1, 1)
                g = np.asarray(sel, dtype=object).reshape(shape)
            else:
                g = self.grid[np.ix_(*[np.arange(self.grid.shape[k])[i] for k, i in enumerate(idx[:2])])]
        except IndexError:
            raise _err("Index exceeds the number of array elements.", "MATLAB:index:outOfBounds") from None
        return wrap(self.info, g)

    def assign(self, args, value):
        raise _err("Indexed assignment into enumeration arrays is not supported.", "MATLAB:class:IndexedAssign")

    def binop(self, op, other, reflected):
        return _binop(self, op, other, reflected)

    def display_text(self) -> str:
        r, c = self.shape
        if r * c == 0:
            return f"  {r}×{c} empty {self.info.name} enumeration array"
        w = max(len(m.enum_name) for m in self.flat())
        lines = [f"  {r}×{c} {self.info.name} enumeration array", ""]
        for i in range(r):
            lines.append("    " + "    ".join(self.grid[i, j].enum_name.ljust(w) for j in range(c)).rstrip())
        return "\n".join(lines)


def wrap(info, grid):
    g = np.asarray(grid, dtype=object)
    if g.size == 1:
        return g.reshape(-1)[0]
    return EnumArray(info, g)


def as_grid(v):
    if isinstance(v, EnumArray):
        return v.grid
    g = np.empty((1, 1), dtype=object)
    g[0, 0] = v
    return g


def concat(name, parts):
    """horzcat/vertcat of enumeration members/arrays of one class, else NotImplemented."""
    infos = {p.info for p in parts if is_enum(p)}
    if len(infos) != 1 or not all(is_enum(p) or _is_text(p) for p in parts):
        return NotImplemented
    info = infos.pop()
    grids = [as_grid(p) if is_enum(p) else as_grid(_from_text(info, p)) for p in parts]
    try:
        g = np.hstack(grids) if name == "horzcat" else np.vstack(grids)
    except ValueError:
        raise _err("Dimensions of arrays being concatenated are not consistent.", "MATLAB:catenate:dimensionMismatch") from None
    return wrap(info, g)


def _is_text(v):
    return getattr(v, "text", None) is not None and not cd.is_instance(v)


def _from_text(info, v):
    m = member(info, v.text)
    if m is None:
        raise _err(f"'{v.text}' is not a member of enumeration '{info.name}'.", "MATLAB:class:InvalidEnum")
    return m


# -- operators -----------------------------------------------------------------------------
def _values(v):
    """Underlying numeric array of a numeric-derived member/array, or None."""
    if not is_enum(v):
        return None
    ms = [v] if not isinstance(v, EnumArray) else v.flat()
    if any(m.builtin_value is None for m in ms):
        return None
    if not isinstance(v, EnumArray):
        return v.builtin_value
    arr = np.array([np.asarray(m.builtin_value.backend_buffer()).reshape(-1)[0] for m in ms])
    return type(ms[0].builtin_value)(arr.reshape(v.shape, order="F")) if hasattr(ms[0].builtin_value, "backend_buffer") else None


def _identity_eq(a, b):
    info = a.info if is_enum(a) else b.info
    if _is_text(a):
        a = _from_text(info, a)
    if _is_text(b):
        b = _from_text(info, b)
    if not (is_enum(a) and is_enum(b)) or a.info is not b.info:
        return None
    ga, gb = as_grid(a), as_grid(b)
    if ga.size == 1:
        ga = np.full(gb.shape, ga.reshape(-1)[0], dtype=object)
    if gb.size == 1:
        gb = np.full(ga.shape, gb.reshape(-1)[0], dtype=object)
    if ga.shape != gb.shape:
        raise _err("Arrays have incompatible sizes for this operation.", "MATLAB:sizeDimensionsMustMatch")
    return np.vectorize(lambda x, y: x is y, otypes=[bool])(ga, gb)


def _binop(self, op, other, reflected):
    from openmatlab.numerics.ndarray_value import NDArrayValue
    from openmatlab.runtime.evaluator import Evaluator

    a, b = (other, self) if reflected else (self, other)
    if op in ("==", "~="):
        eq = _identity_eq(a, b)
        if eq is not None:
            return NDArrayValue(eq if op == "==" else ~eq)
    va, vb = _values(a), _values(b)
    if va is not None or vb is not None:
        name = Evaluator._OP_METHODS.get(op)
        if name is None:
            return NotImplemented
        xa = va if va is not None else a
        xb = vb if vb is not None else b
        if is_enum(xa) or is_enum(xb):
            return NotImplemented
        return self.info.resolver.resolve(name)([xa, xb], nargout=1)[0]
    if op in _REL and not (is_enum(a) and is_enum(b)):
        return NotImplemented
    return NotImplemented


def values_equal(a, b) -> Optional[bool]:
    """switch/case matching for enumerations; None when neither side is an enumeration."""
    if not (is_enum(a) or is_enum(b)):
        return None
    try:
        eq = _identity_eq(a, b)
    except Exception:
        return False
    return bool(eq is not None and eq.size == 1 and eq.reshape(-1)[0])
