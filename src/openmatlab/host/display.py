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
            buf = value.backend_buffer()
            if value.is_scalar():
                v = float(buf.reshape(-1)[0])
                import math

                if math.isnan(v):
                    return "NaN"
                if math.isinf(v):
                    return "-Inf" if v < 0 else "Inf"
                if v == int(v) and abs(v) < 1e15:
                    return str(int(v))
                return repr(v)
            try:
                import numpy as np

                return str(np.asarray(buf))
            except Exception:
                return str(buf)
    except Exception:
        pass
    return str(value)
