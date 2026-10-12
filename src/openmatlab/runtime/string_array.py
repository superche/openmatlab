"""MATLAB string arrays (Epic #482: #459, #460).

A 1x1 non-missing string stays a ``StringValue`` (so every text consumer keeps
working); any other shape is a ``StringArray`` over a 2-D NumPy object grid of
``str`` with ``None`` for ``<missing>``. ``to_grid`` / ``make`` are the only
conversion points, so every string operation is "grid in, grid out".
"""

from __future__ import annotations

from typing import Optional

import numpy as np


class StringArray:
    """Non-scalar (or missing) MATLAB string array; class ``string``."""

    __slots__ = ("data",)
    is_string = True

    def __init__(self, data) -> None:
        a = np.empty(np.shape(data), dtype=object)
        a[...] = data
        if a.ndim != 2:
            a = a.reshape(1, -1) if a.ndim < 2 else a
        object.__setattr__(self, "data", a)

    def __setattr__(self, name, value):
        raise AttributeError("StringArray is immutable")

    @property
    def shape(self):
        return tuple(int(d) for d in self.data.shape)

    def numel(self) -> int:
        return int(self.data.size)

    def matlab_class(self) -> str:
        return "string"

    @property
    def text(self) -> str:
        if self.data.size == 1 and self.data.flat[0] is not None:
            return self.data.flat[0]
        raise ValueError("string array used where a single text value is required")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, StringArray)
            and other.data.shape == self.data.shape
            and all(a == b and a is not None for a, b in zip(self.data.flat, other.data.flat))
        )

    def __hash__(self) -> int:
        return hash(tuple(self.data.flat))

    def __repr__(self) -> str:
        return f"StringArray(shape={self.shape})"


def num_text(x) -> Optional[str]:
    """MATLAB string(x) text for one real number / logical; None if complex."""
    if np.iscomplexobj(x):
        return None
    if isinstance(x, (bool, np.bool_)):
        return "true" if x else "false"
    if np.issubdtype(np.asarray(x).dtype, np.integer):
        return str(int(x))
    x = float(x)
    if x != x:
        return "NaN"
    if x in (float("inf"), float("-inf")):
        return "Inf" if x > 0 else "-Inf"
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    return f"{x:.4f}".rstrip("0")  # MVP: 4 significant decimals


def to_grid(v, *, numbers: bool = True, cells: bool = False) -> Optional[np.ndarray]:
    """2-D object grid of str/None for a string, char row/matrix (one element per
    row), number array (``numbers``) or cellstr (``cells``); None if not convertible."""
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.value import Array

    if isinstance(v, StringArray):
        return v.data.copy()
    if isinstance(v, CharValue):
        if getattr(v, "is_string", False):
            return _grid([[v.text]])
        if len(v.rows) > 1:
            return _grid([[r] for r in v.rows])
        return _grid([[v.text]])
    if cells and isinstance(v, CellValue):
        r, c = v.shape
        out = np.empty((r, c), dtype=object)
        for i in range(r):
            for j in range(c):
                e = v.get(i, j)
                if not isinstance(e, CharValue) or len(e.rows) > 1:
                    return None
                out[i, j] = e.text
        return out
    if numbers and isinstance(v, Array):
        b = np.asarray(v.backend_buffer())
        b = b.reshape(1, 1) if b.ndim == 0 else b
        if b.ndim != 2:
            return None
        out = np.empty(b.shape, dtype=object)
        for idx in np.ndindex(*b.shape):
            t = num_text(b[idx])
            if t is None:
                return None
            out[idx] = t
        return out
    return None


def _grid(rows) -> np.ndarray:
    r, c = len(rows), len(rows[0]) if rows else 0
    out = np.empty((r, c), dtype=object)
    for i, row in enumerate(rows):
        for j, x in enumerate(row):
            out[i, j] = x
    return out


def make(grid: np.ndarray):
    """StringValue for a 1x1 non-missing grid, else StringArray."""
    from openmatlab.runtime.char_value import StringValue

    g = np.asarray(grid, dtype=object)
    if g.size == 1 and g.ndim <= 2 and g.reshape(-1)[0] is not None:
        return StringValue(g.reshape(-1)[0])
    return StringArray(g.reshape(g.shape if g.ndim == 2 else (1, -1)))


def is_string(v) -> bool:
    return bool(getattr(v, "is_string", False))
