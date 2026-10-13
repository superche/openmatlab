"""MATLAB struct arrays (Epic #506).

``StructValue`` is an immutable 2-D array of records that all share one ordered
field list. Elements are stored column-major as dicts. A 1x1 struct is the
common "scalar struct". Indexing and growth work through a position map in
the evaluator, so the numeric index rules (``end``, ranges, logical masks,
deletion) are reused unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from openmatlab.runtime.value import Value


def _empty() -> Value:
    import numpy as np

    from openmatlab.numerics.ndarray_value import NDArrayValue

    return NDArrayValue(np.zeros((0, 0)))


@dataclass(frozen=True)
class StructValue:
    shape: Tuple[int, ...]  # 2-D or N-D (#508)
    fields: Tuple[str, ...]
    elems: Tuple[Dict[str, Value], ...]  # column-major, len == prod(shape)

    is_struct = True

    # --- Value protocol -------------------------------------------------
    def matlab_class(self) -> str:
        return "struct"

    @property
    def ndim(self) -> int:
        return len(self.shape)

    def numel(self) -> int:
        n = 1
        for d in self.shape:
            n *= int(d)
        return n

    def is_scalar(self) -> bool:
        return self.numel() == 1

    # --- construction -----------------------------------------------------
    @staticmethod
    def scalar(pairs: Iterable[Tuple[str, Value]] = ()) -> "StructValue":
        d = dict(pairs)
        return StructValue((1, 1), tuple(d), (d,))

    @staticmethod
    def build(shape, fields, elems) -> "StructValue":
        fields = tuple(fields)
        elems = tuple({f: e.get(f, _empty()) for f in fields} for e in elems)
        shape = [int(d) for d in shape] or [1, 1]
        if len(shape) == 1:
            shape = [1, shape[0]]
        while len(shape) > 2 and shape[-1] == 1:  # trailing singleton dims drop
            shape.pop()
        return StructValue(tuple(shape), fields, elems)

    # --- field operations ---------------------------------------------------
    def has(self, name: str) -> bool:
        return name in self.fields

    def get(self, name: str, k: int = 0) -> Value:
        if name not in self.fields:
            raise KeyError(name)
        return self.elems[k][name]

    def with_field(self, name: str, value: Value, k: int = 0) -> "StructValue":
        """Set field ``name`` of element ``k``; a new field is [] in other elements."""
        fields = self.fields if name in self.fields else self.fields + (name,)
        elems = []
        for i, e in enumerate(self.elems):
            e = dict(e)
            if i == k:
                e[name] = value
            else:
                e.setdefault(name, _empty())
            elems.append(e)
        return StructValue(self.shape, fields, tuple(elems))

    def without(self, names) -> "StructValue":
        keep = tuple(f for f in self.fields if f not in names)
        return StructValue(self.shape, keep, tuple({f: e[f] for f in keep} for e in self.elems))

    def reorder(self, fields) -> "StructValue":
        return StructValue(self.shape, tuple(fields), self.elems)

    def element(self, k: int) -> "StructValue":
        return StructValue((1, 1), self.fields, (self.elems[k],))

    def __repr__(self) -> str:
        return f"StructValue(shape={self.shape}, fields={self.fields})"


def is_struct(v) -> bool:
    return bool(getattr(v, "is_struct", False))


class CsList:
    """A comma-separated list produced by ``s.f`` on a struct array, or by ``c{:}``.

    Only the evaluator sees this type. List contexts ([...], {...}, call
    arguments) expand it; other contexts take the first value.
    """

    __slots__ = ("values",)

    def __init__(self, values):
        self.values = list(values)

    def matlab_class(self) -> str:  # pragma: no cover - never user-visible
        return "cs-list"
