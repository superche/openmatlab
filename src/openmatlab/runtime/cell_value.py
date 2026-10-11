"""Cell array value (2-D container of Value)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from openmatlab.runtime.value import Value


@dataclass(frozen=True)
class CellValue:
    """MATLAB-like cell array — rectangular 2-D grid of Values."""

    rows: Tuple[Tuple[Value, ...], ...]

    def matlab_class(self) -> str:
        return "cell"

    @property
    def shape(self) -> Tuple[int, int]:
        if not self.rows:
            return (0, 0)
        return (len(self.rows), len(self.rows[0]) if self.rows[0] else 0)

    @property
    def ndim(self) -> int:
        return 2

    def numel(self) -> int:
        r, c = self.shape
        return r * c

    def is_scalar(self) -> bool:
        return self.numel() == 1

    def get(self, i: int, j: int) -> Value:
        """0-based access."""
        return self.rows[i][j]

    def with_set(self, i: int, j: int, value: Value) -> "CellValue":
        """Return a new cell with rows[i][j] replaced (0-based)."""
        rows = [list(r) for r in self.rows]
        rows[i][j] = value
        return CellValue(rows=tuple(tuple(r) for r in rows))

    @staticmethod
    def empty(m: int, n: int) -> "CellValue":
        """m×n cell of empty 0×0 double arrays (filled by caller/libs)."""
        from openmatlab.numerics.ndarray_value import NDArrayValue
        import numpy as np

        blank = NDArrayValue(np.zeros((0, 0), dtype=np.float64))
        rows = tuple(tuple(blank for _ in range(n)) for _ in range(m))
        return CellValue(rows=rows)

    def __repr__(self) -> str:
        r, c = self.shape
        return f"CellValue(shape=({r}, {c}))"
