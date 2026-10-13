"""Cell array value (2-D container of Value)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from openmatlab.runtime.value import Value


@dataclass(frozen=True)
class CellValue:
    """MATLAB-like cell array — rectangular 2-D grid of Values."""

    rows: Tuple[Tuple[Value, ...], ...]
    # N-D cells (#444): full MATLAB size when ndims > 2; ``rows`` then holds the
    # folded m x (n*p*...) view c(:,:), column-major over trailing dims.
    nd: Tuple[int, ...] = ()

    @property
    def full_shape(self) -> Tuple[int, ...]:
        return self.nd or self.shape

    def matlab_class(self) -> str:
        return "cell"

    @property
    def shape(self) -> Tuple[int, int]:
        if not self.rows:
            return (0, 0)
        return (len(self.rows), len(self.rows[0]) if self.rows[0] else 0)

    @property
    def ndim(self) -> int:
        return len(self.full_shape)

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
        return CellValue(rows=tuple(tuple(r) for r in rows), nd=self.nd)

    def page(self, off: int) -> "CellValue":
        """2-D page ``off`` (0-based, column-major over trailing dims) of an N-D cell."""
        n = self.full_shape[1]
        return CellValue(rows=tuple(r[off * n:(off + 1) * n] for r in self.rows))

    def to_obj(self):
        """NumPy object array of the full (N-D) shape, column-major over trailing dims (#479)."""
        import numpy as np

        r, c = self.shape
        folded = np.empty((r, c), dtype=object)
        for i in range(r):
            for j in range(c):
                folded[i, j] = self.rows[i][j]
        return folded.reshape(self.full_shape, order="F")

    @staticmethod
    def from_obj(a) -> "CellValue":
        """CellValue from an object array; trailing singleton dims beyond 2 drop (#479)."""
        import numpy as np

        a = np.asarray(a, dtype=object)
        shape = list(a.shape) if a.ndim >= 2 else [1, a.size]
        while len(shape) > 2 and shape[-1] == 1:
            shape.pop()
        folded = a.reshape(shape[0], int(np.prod(shape[1:])), order="F")
        rows = tuple(tuple(folded[i, j] for j in range(folded.shape[1])) for i in range(folded.shape[0]))
        return CellValue(rows=rows, nd=tuple(shape) if len(shape) > 2 else ())

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
