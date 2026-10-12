"""Char value: a 2-D char matrix stored as equal-length rows (#427).

Most of the runtime still consumes single-row text through ``.text``; a
multi-row matrix raises there instead of silently dropping rows.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple


class CharValue:
    """MATLAB char array (not an Array). ``''`` is 0x0; ``'abc'`` is 1x3."""

    __slots__ = ("rows",)

    def __init__(self, text: str = "", rows: Optional[Sequence[str]] = None) -> None:
        if rows is None:
            rows = (text,) if text else ()
        rows = tuple(rows)
        if len({len(r) for r in rows}) > 1:
            raise ValueError("char rows must have equal length")
        if rows and not rows[0] and len(rows) == 1:
            rows = ()
        object.__setattr__(self, "rows", rows)

    def __setattr__(self, name, value):  # immutable like the old frozen dataclass
        raise AttributeError("CharValue is immutable")

    @property
    def text(self) -> str:
        if len(self.rows) > 1:
            raise ValueError(
                "multi-row char matrix used where a char row vector is required"
            )
        return self.rows[0] if self.rows else ""

    @property
    def shape(self) -> Tuple[int, int]:
        if not self.rows:
            return (0, 0)
        return (len(self.rows), len(self.rows[0]))

    def numel(self) -> int:
        r, c = self.shape
        return r * c

    def matlab_class(self) -> str:
        return "char"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CharValue) and other.rows == self.rows

    def __hash__(self) -> int:
        return hash(self.rows)

    def __repr__(self) -> str:
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
