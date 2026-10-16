"""MATLAB ``categorical`` (M10 T-E2, Epic #692).

Stored as an integer code array (0 = ``<undefined>``, k = ``cats[k-1]``) plus the
ordered category list and the ``Ordinal``/``Protected`` flags. A value type: every
operation returns a new ``CategoricalValue``.
"""

from __future__ import annotations

from typing import List, Sequence

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.table_value import _cv, _err, cellstr_col, is_text, text, texts

UNDEF = "<undefined>"


class CategoricalValue:
    is_object = True
    is_categorical = True

    def __init__(self, codes, cats: Sequence[str], ordinal: bool = False, protected: bool = False):
        a = np.asarray(codes, dtype=np.int64)
        self.codes = a.reshape(1, 1) if a.ndim == 0 else (a.reshape(1, -1) if a.ndim == 1 else a)
        self.cats: List[str] = list(cats)
        self.ordinal = bool(ordinal)
        self.protected = bool(protected) or self.ordinal

    def like(self, codes, cats=None) -> "CategoricalValue":
        return CategoricalValue(codes, self.cats if cats is None else cats, self.ordinal, self.protected)

    # -- value protocol -------------------------------------------------------
    def matlab_class(self) -> str:
        return "categorical"

    @property
    def shape(self):
        return self.codes.shape

    def numel(self) -> int:
        return int(self.codes.size)

    def is_scalar(self) -> bool:
        return self.codes.size == 1

    def labels(self) -> List[str]:
        return [self.cats[k - 1] if k else UNDEF for k in self.codes.reshape(-1, order="F")]

    def transpose_value(self) -> "CategoricalValue":
        return self.like(self.codes.T)

    def get_prop(self, name):
        raise _err(f"Unrecognized method, property, or field '{name}' for class 'categorical'.",
                   "MATLAB:noSuchMethodOrField")

    # -- conversion of other values to codes in this category set -------------
    def codes_for(self, v, *, grow: bool = False):
        """Return (codes, cats) for ``v`` (categorical/text) in this value's categories."""
        cats = list(self.cats)
        if isinstance(v, CategoricalValue):
            labels, shape = v.labels(), v.shape
        else:
            labels = texts(v)
            if labels is None:
                if getattr(v, "is_missing_value", False):
                    return np.zeros((1, 1), dtype=np.int64), cats
                raise _err("Invalid comparison or assignment: values must be categorical, text, or a cell array of "
                           "character vectors.", "MATLAB:categorical:InvalidComparisonTypes")
            shape = (1, 1) if is_text(v) else _text_shape(v)
        out = []
        for s in labels:
            if s == UNDEF or s == "":
                out.append(0)
            elif s in cats:
                out.append(cats.index(s) + 1)
            elif grow and not self.protected:
                cats.append(s)
                out.append(len(cats))
            elif grow:
                raise _err(f"Cannot add a new category '{s}' to this categorical array because its categories are "
                           "protected.", "MATLAB:categorical:ProtectedForAssign")
            else:
                out.append(-1)  # not a category: never equal
        return np.array(out, dtype=np.int64).reshape(shape, order="F"), cats

    # -- indexing -------------------------------------------------------------
    def _subs(self, args):
        idx = []
        for k, a in enumerate(args):
            if is_text(a) and text(a) == ":":
                idx.append(None)
                continue
            b = np.asarray(a.backend_buffer())
            if b.dtype == np.bool_:
                idx.append(np.flatnonzero(b.reshape(-1, order="F")))
            else:
                f = b.reshape(-1, order="F")
                if np.any(f != np.floor(f)) or np.any(f < 1):
                    raise _err("Array indices must be positive integers or logical values.", "MATLAB:badsubscript")
                idx.append(f.astype(int) - 1)
        return idx

    def index(self, args):
        idx = self._subs(args)
        if len(idx) == 1:
            flat = self.codes.reshape(-1, order="F")
            i = np.arange(flat.size) if idx[0] is None else idx[0]
            if i.size and i.max() >= flat.size:
                raise _err(f"Index exceeds the number of array elements. Index must not exceed {flat.size}.",
                           "MATLAB:badsubscript")
            a = args[0]
            if idx[0] is None:
                out = flat.reshape(-1, 1)
            elif hasattr(a, "shape") and not is_text(a) and len(a.shape) == 2 and min(a.shape) != 1 and \
                    np.asarray(a.backend_buffer()).dtype != np.bool_:
                out = flat[i].reshape(a.shape, order="F")
            elif self.codes.shape[0] == 1:
                out = flat[i].reshape(1, -1)
            else:
                out = flat[i].reshape(-1, 1)
            return self.like(out)
        codes = self.codes
        if len(idx) > 2:
            idx = idx[:2] + [x for x in idx[2:] if not (x is not None and np.all(x == 0))]
        sel = []
        for k, i in enumerate(idx[:2]):
            n = codes.shape[k]
            i = np.arange(n) if i is None else i
            if i.size and i.max() >= n:
                raise _err("Index in position %d exceeds array bounds. Index must not exceed %d." % (k + 1, n),
                           "MATLAB:badsubscript")
            sel.append(i)
        return self.like(codes[np.ix_(*sel)])

    def assign(self, args, value):
        if getattr(value, "backend_buffer", None) and not is_text(value) and not isinstance(value, CategoricalValue) \
                and np.asarray(value.backend_buffer()).size == 0:
            return self._delete(args)
        codes_v, cats = self.codes_for(value, grow=True)
        idx = self._subs(args)
        if len(idx) == 1:
            flat = self.codes.reshape(-1, order="F").copy()
            i = np.arange(flat.size) if idx[0] is None else idx[0]
            if i.size and i.max() >= flat.size:
                grow = np.zeros(i.max() + 1 - flat.size, dtype=np.int64)
                flat = np.concatenate([flat, grow])
                shape = (1, flat.size) if self.codes.shape[0] <= 1 else (flat.size, 1)
            else:
                shape = self.codes.shape
            src = codes_v.reshape(-1, order="F")
            if src.size not in (1, i.size):
                raise _err("Unable to perform assignment because the left and right sides have a different number "
                           "of elements.", "MATLAB:matrix:assignmentDimMismatch")
            flat[i] = src
            return self.like(flat.reshape(shape, order="F"), cats)
        codes = self.codes.copy()
        sel = []
        for k, i in enumerate(idx[:2]):
            i = np.arange(codes.shape[k]) if i is None else i
            sel.append(i)
        need = [max(codes.shape[k], (sel[k].max() + 1) if sel[k].size else 0) for k in range(2)]
        if need != list(codes.shape):
            g = np.zeros(need, dtype=np.int64)
            g[: codes.shape[0], : codes.shape[1]] = codes
            codes = g
        block = codes_v if codes_v.size != 1 else np.full((sel[0].size, sel[1].size), codes_v.reshape(-1)[0])
        if block.size != sel[0].size * sel[1].size:
            raise _err("Unable to perform assignment because the size of the left side does not match the right side.",
                       "MATLAB:subsassigndimmismatch")
        codes[np.ix_(*sel)] = block.reshape(sel[0].size, sel[1].size, order="F")
        return self.like(codes, cats)

    def _delete(self, args):
        idx = self._subs(args)
        if len(idx) == 1:
            flat = self.codes.reshape(-1, order="F")
            keep = np.ones(flat.size, bool)
            keep[np.arange(flat.size) if idx[0] is None else idx[0]] = False
            out = flat[keep]
            return self.like(out.reshape(-1, 1) if self.codes.shape[1] == 1 and self.codes.shape[0] != 1
                             else out.reshape(1, -1))
        r, c = idx[:2]
        if r is None:
            keep = np.ones(self.codes.shape[1], bool)
            keep[c] = False
            return self.like(self.codes[:, keep])
        keep = np.ones(self.codes.shape[0], bool)
        keep[r] = False
        return self.like(self.codes[keep, :])

    # -- operators ------------------------------------------------------------
    def binop(self, op, other, reflected):
        if op not in ("==", "~=", "<", ">", "<=", ">="):
            raise _err(f"Operator '{op}' is not supported for operands of type 'categorical'.",
                       "MATLAB:categorical:InvalidOperator")
        if isinstance(other, CategoricalValue):
            if op in ("<", ">", "<=", ">=") and not (self.ordinal and other.ordinal and self.cats == other.cats):
                raise _err("Relational comparisons are not allowed for categorical arrays that are not ordinal, "
                           "or ordinal with different categories.", "MATLAB:categorical:NotOrdinal")
            if self.ordinal and other.ordinal and self.cats != other.cats:
                raise _err("Ordinal categorical arrays must have the same sets of categories, in the same order.",
                           "MATLAB:categorical:OrdinalCategoriesMismatch")
        elif op in ("<", ">", "<=", ">=") and not self.ordinal:
            raise _err("Relational comparisons are not allowed for categorical arrays that are not ordinal.",
                       "MATLAB:categorical:NotOrdinal")
        o, _ = self.codes_for(other)
        if op in ("<", ">", "<=", ">=") and np.any(o < 0):
            raise _err("Invalid comparison: value is not a category of the ordinal categorical array.",
                       "MATLAB:categorical:InvalidOrdinalComparison")
        a, b = (o, self.codes) if reflected else (self.codes, o)
        if a.size != 1 and b.size != 1 and a.shape != b.shape:
            raise _err("Arrays have incompatible sizes for this operation.", "MATLAB:sizeDimensionsMustMatch")
        defined = (a > 0) & (b > 0)
        res = {"==": a == b, "~=": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
        res = (res & defined) if op != "~=" else (res | ~defined)
        return NDArrayValue(np.asarray(res, dtype=bool))

    # -- display --------------------------------------------------------------
    def body_text(self) -> str:
        if self.codes.size == 0:
            return ""
        labs = np.array(self.labels(), dtype=object).reshape(self.codes.shape, order="F")
        w = max(len(s) for s in labs.reshape(-1))
        return "\n".join("     " + "      ".join(s.ljust(w) for s in row) + " " for row in labs) + "\n"

    def display_text(self) -> str:
        from openmatlab.host.display import _dims

        if self.codes.size == 0:
            return f"  {_dims(self.shape)} empty categorical array"
        if self.codes.size == 1:
            return "     " + self.labels()[0] + " "
        return f"  {_dims(self.shape)} categorical array\n\n" + self.body_text()


def _text_shape(v):
    from openmatlab.runtime.cell_value import CellValue

    if isinstance(v, CellValue):
        return tuple(v.shape)
    return tuple(v.shape)


def categories_value(c: CategoricalValue):
    return cellstr_col(c.cats)


def concat(rows):
    """[a b; c d] where some element is categorical: union of categories in order of appearance."""
    flat = [v for r in rows for v in r]
    first = next(v for v in flat if isinstance(v, CategoricalValue))
    cats = list(first.cats)
    ordinal = first.ordinal
    for v in flat:
        if isinstance(v, CategoricalValue):
            if ordinal and (not v.ordinal or v.cats != cats):
                raise _err("Cannot concatenate an ordinal categorical array with a categorical array that has "
                           "different categories.", "MATLAB:categorical:OrdinalCategoriesMismatch")
            for s in v.cats:
                if s not in cats:
                    cats.append(s)
    base = CategoricalValue(np.zeros((0, 0), np.int64), cats, ordinal)
    base.protected = first.protected and ordinal

    def codes(v):
        if not isinstance(v, CategoricalValue) and hasattr(v, "backend_buffer") and not is_text(v) \
                and np.asarray(v.backend_buffer()).size == 0:
            return None
        c, newcats = base.codes_for(v, grow=True)
        base.cats = newcats
        return c

    try:
        hs = []
        for r in rows:
            parts = [x for x in (codes(v) for v in r) if x is not None]
            if parts:
                if len({p.shape[0] for p in parts}) > 1:
                    raise _err("Dimensions of arrays being concatenated are not consistent.", "MATLAB:catenate:dimensionMismatch")
                hs.append(np.concatenate(parts, axis=1))
        if hs and len({h.shape[1] for h in hs}) > 1:
            raise _err("Dimensions of arrays being concatenated are not consistent.", "MATLAB:catenate:dimensionMismatch")
        out = np.concatenate(hs, axis=0) if hs else np.zeros((0, 0), np.int64)
    except ValueError:
        raise _err("Dimensions of arrays being concatenated are not consistent.", "MATLAB:catenate:dimensionMismatch") from None
    return CategoricalValue(out, base.cats, ordinal, first.protected)
