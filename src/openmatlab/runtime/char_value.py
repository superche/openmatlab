"""Char value: a 2-D char matrix stored as equal-length rows (#427, #1058).

``''`` is 0×0. A 1×0 row (``'abc'(:,[])``, ``blanks(0)``) and a 0×N matrix
keep their shape: with no rows, the width lives in ``ncols``. Most of the
runtime still consumes single-row text through ``.text``; a multi-row matrix
raises there instead of silently dropping rows.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple


class CharValue:
    """MATLAB char array (not an Array). ``''`` is 0×0; ``'abc'`` is 1×3."""

    __slots__ = ("rows", "ncols")

    def __init__(self, text: str = "", rows: Optional[Sequence[str]] = None, *, ncols: Optional[int] = None) -> None:
        if rows is None:
            rows = (text,) if text else ()
        rows = tuple(rows)
        if len({len(r) for r in rows}) > 1:
            raise ValueError("char rows must have equal length")
        if rows:
            width = len(rows[0])
            if ncols is not None and int(ncols) != width:
                raise ValueError("char ncols does not match the rows")
        elif ncols is None:
            width = 0
        else:
            width = int(ncols)
            if width < 0:
                raise ValueError("char ncols must be non-negative")
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "ncols", width)

    def __setattr__(self, name, value):  # immutable like the old frozen dataclass
        raise AttributeError("CharValue is immutable")

    @classmethod
    def from_codes(cls, data) -> "CharValue":
        """Code matrix → char. Empty inputs keep their size (1×0, 0×N, M×0, 0×0)."""
        import numpy as np

        a = np.asarray(data)
        if a.ndim == 0:
            a = a.reshape(1, 1)
        elif a.ndim == 1:
            a = a.reshape(1, -1)
        elif a.ndim != 2:
            raise ValueError("N-D char arrays are not supported")
        nrows, width = int(a.shape[0]), int(a.shape[1])
        if nrows == 0:
            return cls(rows=(), ncols=width)
        return cls(rows=tuple("".join(chr(int(ch)) for ch in row) for row in a))

    @property
    def text(self) -> str:
        if len(self.rows) > 1:
            raise ValueError(
                "multi-row char matrix used where a char row vector is required"
            )
        return self.rows[0] if self.rows else ""

    @property
    def shape(self) -> Tuple[int, int]:
        return (len(self.rows), self.ncols)

    def numel(self) -> int:
        r, c = self.shape
        return r * c

    def matlab_class(self) -> str:
        return "char"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CharValue) and other.rows == self.rows and other.ncols == self.ncols

    def __hash__(self) -> int:
        return hash((self.rows, self.ncols))

    def __repr__(self) -> str:
        if not self.rows and self.ncols:
            return f"CharValue(rows=(), ncols={self.ncols})"
        return f"CharValue(rows={self.rows!r})"

    def __str__(self) -> str:
        return "\n".join(self.rows)


class StringValue(CharValue):
    """MATLAB ``string`` scalar (double-quoted literal, #78).

    Subclasses CharValue so text-consuming builtins (flags, which, run …) keep
    working; MATLAB-visible differences: class ``string``, size 1x1, ``+``
    concatenates, display ``"abc"``. String arrays are out of scope.
    """

    __slots__ = ()
    is_string = True

    def __init__(self, text: str = "") -> None:
        super().__init__(text)

    @property
    def shape(self):
        return (1, 1)

    def numel(self) -> int:
        return 1

    def matlab_class(self) -> str:
        return "string"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StringValue) and other.rows == self.rows

    def __hash__(self) -> int:
        return hash(("string", self.rows))

    def __repr__(self) -> str:
        return f"StringValue({self.text!r})"
