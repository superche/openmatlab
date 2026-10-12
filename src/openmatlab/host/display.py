"""Interactive display policy — semicolon suppress, ans, pretty-print."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, TextIO, runtime_checkable

if TYPE_CHECKING:
    from openmatlab.runtime.value import Value
    from openmatlab.runtime.workspace import Workspace


@runtime_checkable
class DisplayPolicy(Protocol):
    def should_print(self, suppress: bool) -> bool: ...

    def show(self, value: Value, *, name: Optional[str] = None) -> None: ...

    def bind_ans(self, value: Value) -> None: ...


class NullDisplay:
    def should_print(self, suppress: bool) -> bool:
        return not suppress

    def show(self, value: object, *, name: Optional[str] = None) -> None:
        return None

    def bind_ans(self, value: object) -> None:
        return None


class ConsoleDisplay:
    """Pretty-print Arrays; optionally bind ans into a workspace."""

    def __init__(
        self,
        workspace: Optional["Workspace"] = None,
        stream: Optional[TextIO] = None,
    ) -> None:
        import sys

        self.workspace = workspace
        self.stream = stream or sys.stdout

    def should_print(self, suppress: bool) -> bool:
        return not suppress

    def bind_ans(self, value: object) -> None:
        if self.workspace is not None:
            self.workspace.set("ans", value)  # type: ignore[arg-type]

    def show(self, value: object, *, name: Optional[str] = None) -> None:
        label = name if name is not None else "ans"
        text = _format_value(value)
        self.stream.write(f"{label} =\n\n{text}\n\n")
        self.stream.flush()


def _format_value(value: object) -> str:
    try:
        from openmatlab.runtime.cell_value import CellValue

        if isinstance(value, CellValue):
            r, c = value.shape
            if r == 0 and c == 0:
                return "{}  (empty cell)"
            lines = [f"{{{r}x{c} cell}}"]
            for i in range(r):
                for j in range(c):
                    inner = _format_value(value.get(i, j))
                    # indent multi-line
                    inner_lines = inner.splitlines() or [inner]
                    lines.append(f"  ({i+1},{j+1}) = {inner_lines[0]}")
                    for extra in inner_lines[1:]:
                        lines.append(f"           {extra}")
            return "\n".join(lines)
    except Exception:
        pass
    try:
        from openmatlab.runtime.char_value import CharValue

        if isinstance(value, CharValue):
            return value.text
    except Exception:
        pass
    try:
        from openmatlab.numerics.ndarray_value import NDArrayValue
        from openmatlab.runtime.value import Array

        if isinstance(value, Array):
            return format_array(value.backend_buffer())
    except Exception:
        pass
    return str(value)


def _fmt_real(v: float, integer: bool) -> str:
    if v != v:
        return "NaN"
    if v in (float("inf"), float("-inf")):
        return "Inf" if v > 0 else "-Inf"
    if integer:
        return str(int(v))
    return f"{v:.4f}"


def format_array(buf: object) -> str:
    """MATLAB/Octave ``format short`` text for a 2-D array (no NumPy repr).

    Integer-valued (and logical) data prints as integers; otherwise 4 decimals,
    switching to ``%.4e`` when magnitudes leave [1e-4, 1e5). Columns are
    right-aligned to a shared width with a 3-space gutter; scalars are bare.
    Empty arrays print ``[](RxC)``.
    """
    import numpy as np

    a = np.asarray(buf)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    if a.size == 0:
        return f"[]({a.shape[0]}x{a.shape[1]})"
    if np.iscomplexobj(a):
        return str(a)
    a = a.astype(np.float64)
    finite = a[np.isfinite(a)]
    integer = bool(np.all(finite == np.floor(finite))) and (
        finite.size == 0 or float(np.max(np.abs(finite))) < 1e15
    )
    if integer:
        cells = [[_fmt_real(v, True) for v in row] for row in a]
    else:
        nz = np.abs(finite[finite != 0])
        sci = nz.size > 0 and (float(nz.max()) >= 1e5 or float(nz.min()) < 1e-4)
        def one(v: float) -> str:
            if sci and np.isfinite(v):
                return f"{v:.4e}"
            return _fmt_real(v, False)
        cells = [[one(v) for v in row] for row in a]
    if a.size == 1:
        return cells[0][0]
    width = max(len(c) for row in cells for c in row) + 3
    return "\n".join("".join(c.rjust(width) for c in row) for row in cells)
