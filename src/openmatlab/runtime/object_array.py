"""General object arrays (#766, residual of #669).

An ``ObjectArray`` is an N-d grid of ``ClassInstance`` elements of one class. It is
itself an instance of that class for method dispatch (``is_class_instance``), so
``numel(f)``, ``f(k)``, ``f(k) = g``, ``f(k) = []``, ``[f g]`` and ``f(k).p`` work
with the builtin semantics that class methods see. A 1-by-1 result is always the
plain element, so scalar objects never change representation.
"""

from __future__ import annotations

from typing import List

import numpy as np

from openmatlab.runtime import classdef as cd
from openmatlab.runtime.struct_value import CsList


def _err(msg, ident=""):
    return cd._err(msg, ident)


def _is_colon(a) -> bool:
    return getattr(a, "is_colon", False) or getattr(a, "text", None) == ":"


def grid_of(v) -> np.ndarray:
    if isinstance(v, ObjectArray):
        return v.grid
    g = np.empty((1, 1), dtype=object)
    g[0, 0] = v
    return g


def wrap(info, grid):
    g = np.asarray(grid, dtype=object)
    if g.size == 1:
        return g.reshape(-1)[0]
    if g.ndim < 2:
        g = g.reshape(1, -1)
    return ObjectArray(info, g)


def empty(info, shape=(0, 0)):
    return ObjectArray(info, np.empty(shape, dtype=object))


def _subs(args, shape, *, grow: bool):
    """MATLAB subscripts -> list of 0-based integer index vectors (one per dim or one linear)."""
    out = []
    n = len(args)
    for k, a in enumerate(args):
        if _is_colon(a):
            if n == 1:
                ext = int(np.prod(shape))
            elif k < n - 1:
                ext = shape[k] if k < len(shape) else 1
            else:
                ext = int(np.prod(shape[k:])) if k < len(shape) else 1
            out.append(np.arange(ext))
            continue
        v = np.asarray(a.backend_buffer())
        if v.dtype == bool:
            out.append(np.flatnonzero(v.reshape(-1, order="F")))
            continue
        f = v.reshape(-1, order="F").astype(float)
        if f.size and (np.any(f < 1) or np.any(f != np.floor(f))):
            raise _err("Array indices must be positive integers or logical values.", "MATLAB:badsubscript")
        out.append(f.astype(int) - 1)
    return out


class ObjectArray:
    is_object = True
    is_class_instance = True
    is_object_array = True

    def __init__(self, info, grid):
        self.info = info
        self.grid = np.asarray(grid, dtype=object)

    # Value protocol
    def matlab_class(self) -> str:
        return self.info.name

    @property
    def shape(self):
        return tuple(int(d) for d in self.grid.shape)

    @property
    def ndim(self):
        return self.grid.ndim

    @property
    def alive(self):
        return True

    @property
    def props(self):  # element-wise state lives on the elements
        raise _err("Expected one output from a curly brace or dot indexing expression.")

    def numel(self):
        return int(self.grid.size)

    def is_scalar(self):
        return self.grid.size == 1

    def isa(self, name):
        return self.info.isa(name)

    def flat(self) -> List:
        return list(self.grid.reshape(-1, order="F"))

    # indexing
    def index(self, args):
        return index(self.info, self.grid, args)

    def assign(self, args, value):
        return assign(self.info, self.grid, args, value)

    def get_prop(self, name):
        vals = [e.get_prop(name) for e in self.flat()]
        return vals[0] if len(vals) == 1 else CsList(vals)

    def set_prop(self, name, value):
        if self.grid.size != 1:
            raise _err("Scalar object required for this assignment.", "MATLAB:class:ScalarObjectRequired")
        return self.flat()[0].set_prop(name, value)

    def binop(self, op, other, reflected):
        return NotImplemented

    def display_text(self) -> str:
        dims = "×".join(str(d) for d in self.shape)
        if self.grid.size == 0:
            return f"  {dims} empty {self.info.name} array"
        return f"  {dims} {self.info.name} array"


def index(info, grid, args):
    if not args:
        return wrap(info, grid)
    idx = _subs(args, grid.shape, grow=False)
    try:
        if len(idx) == 1:
            flat = grid.reshape(-1, order="F")
            sel = flat[idx[0]]
            a0 = args[0]
            if _is_colon(a0):
                shape = (-1, 1)
            elif not hasattr(a0, "shape") or grid.ndim == 2 and min(grid.shape) == 1 and max(grid.shape) >= 1 \
                    and sum(d > 1 for d in a0.shape) <= 1:
                shape = (1, -1) if grid.shape[0] == 1 and grid.size else (-1, 1) if grid.size else tuple(a0.shape)
            else:
                shape = tuple(a0.shape)
            g = np.asarray(sel, dtype=object).reshape(shape, order="F") if sel.size else np.empty(
                (0, 0) if not hasattr(a0, "shape") else ((1, 0) if a0.shape[0] == 1 else (0, 1)), dtype=object)
        else:
            g = _nd(grid, len(idx))[np.ix_(*idx)]
    except IndexError:
        raise _err("Index exceeds the number of array elements.", "MATLAB:index:outOfBounds") from None
    return wrap(info, g) if g.size else ObjectArray(info, g)


def _nd(grid, n):
    """View grid with exactly n dims (trailing dims folded / singleton dims added)."""
    s = list(grid.shape)
    if n >= len(s):
        return grid.reshape(s + [1] * (n - len(s)), order="F")
    return grid.reshape(s[:n - 1] + [int(np.prod(s[n - 1:]))], order="F")


def _filler(info):
    try:
        return cd.construct(info, [])
    except Exception:
        return info.new_instance()


def _is_empty_value(v) -> bool:
    return not cd.is_instance(v) and getattr(v, "numel", None) is not None and v.numel() == 0


def assign(info, grid, args, value):
    grid = np.array(grid, dtype=object)
    if _is_empty_value(value):  # x(k) = [] deletes
        return _delete(info, grid, args)
    if not cd.is_instance(value):
        raise _err(f"Unable to perform assignment because value of type '{value.matlab_class()}' is not "
                   f"convertible to '{info.name}'.", "MATLAB:invalidConversion")
    vg = grid_of(value)
    idx = _subs(args, grid.shape, grow=True)
    if len(idx) == 1:
        need = (int(idx[0].max()) + 1) if idx[0].size else 0
        if need > grid.size:
            if grid.size == 0:
                newshape = (1, need)
            elif grid.ndim == 2 and grid.shape[0] == 1:
                newshape = (1, need)
            elif grid.ndim == 2 and grid.shape[1] == 1:
                newshape = (need, 1)
            else:
                raise _err("Attempt to grow array along ambiguous dimension.", "MATLAB:indexed:ambiguousGrow")
            grid = _grow(info, grid, newshape)
        flat = grid.reshape(-1, order="F").copy()
        _put(flat, (idx[0],), vg)
        return wrap(info, flat.reshape(grid.shape, order="F"))
    g = _nd(grid, len(idx))
    need = [max(g.shape[k], (int(i.max()) + 1) if i.size else 0) for k, i in enumerate(idx)]
    if tuple(need) != g.shape:
        g = _grow(info, g, tuple(need))
    g = g.copy()
    _put(g, np.ix_(*idx), vg)
    while g.ndim > 2 and g.shape[-1] == 1:
        g = g.reshape(g.shape[:-1])
    return wrap(info, g)


def _put(target, where, vg):
    sel = target[where]
    if vg.size == 1:
        target[where] = vg.reshape(-1)[0] if sel.ndim == 0 else np.full(sel.shape, vg.reshape(-1)[0], dtype=object)
        return
    if vg.size != sel.size:
        raise _err("Unable to perform assignment because the indices on the left side are not compatible with "
                   "the size of the right side.", "MATLAB:subsassigndimmismatch")
    target[where] = vg.reshape(-1, order="F").reshape(sel.shape, order="F")


def _grow(info, grid, newshape):
    out = np.empty(newshape, dtype=object)
    for pos in np.ndindex(*newshape):
        out[pos] = None
    src = _nd(grid, len(newshape)) if grid.size else grid.reshape((0,) * len(newshape))
    if src.size:
        out[tuple(slice(0, d) for d in src.shape)] = src
    fill = None
    for pos in np.ndindex(*newshape):
        if out[pos] is None:
            fill = fill or _filler(info)
            out[pos] = fill
    return out


def _delete(info, grid, args):
    idx = _subs(args, grid.shape, grow=False)
    if len(idx) == 1:
        keep = np.ones(grid.size, dtype=bool)
        keep[idx[0]] = False
        flat = grid.reshape(-1, order="F")[keep]
        shape = (-1, 1) if grid.ndim == 2 and grid.shape[1] == 1 and grid.shape[0] != 1 else (1, -1)
        return wrap(info, flat.reshape(shape)) if flat.size else empty(info, (1, 0) if shape == (1, -1) else (0, 1))
    g = _nd(grid, len(idx))
    full = [k for k, i in enumerate(idx) if not (len(np.unique(i)) == g.shape[k] and _is_colonish(i, g.shape[k]))]
    if len(full) > 1:
        raise _err("A null assignment can have only one non-colon index.", "MATLAB:subsdeldimmismatch")
    if not full:
        return empty(info, tuple(0 if k == 0 else d for k, d in enumerate(g.shape)))
    k = full[0]
    out = np.delete(g, idx[k], axis=k)
    return wrap(info, out) if out.size else ObjectArray(info, out)


def _is_colonish(i, n):
    return np.array_equal(np.sort(np.unique(i)), np.arange(n))


def concat(name, parts):
    """[a b] / [a; b] of instances of one class with no horzcat/vertcat overload, else NotImplemented."""
    if not parts or not all(cd.is_instance(p) for p in parts):
        return NotImplemented
    infos = {p.info.name for p in parts}
    if len(infos) != 1:
        return NotImplemented
    info = parts[0].info
    grids = [grid_of(p) for p in parts]
    grids = [g for g in grids if g.size] or grids[:1]
    try:
        g = np.concatenate(grids, axis=1 if name == "horzcat" else 0)
    except ValueError:
        raise _err("Dimensions of arrays being concatenated are not consistent.",
                   "MATLAB:catenate:dimensionMismatch") from None
    return wrap(info, g)
