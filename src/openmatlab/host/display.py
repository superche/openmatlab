"""Interactive display policy — semicolon suppress, ans, pretty-print.

In MATLAB-like REPLs, a trailing ';' suppresses printing; otherwise the
host shows the result (and may bind ans). This seam must exist before
plots and matrix pretty-print land.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from openmatlab.runtime.value import Value


@runtime_checkable
class DisplayPolicy(Protocol):
    """Host-facing display contract."""

    def should_print(self, suppress: bool) -> bool:
        """Return False when statement semicolon requested suppression."""
        ...

    def show(self, value: Value, *, name: Optional[str] = None) -> None:
        """Pretty-print a runtime value (matrices, scalars-as-1x1, …)."""
        ...

    def bind_ans(self, value: Value) -> None:
        """Optionally bind ans in the base workspace after a displayed expr."""
        ...


class NullDisplay:
    """Architecture stub: no-op display (used until REPL pretty-print lands)."""

    def should_print(self, suppress: bool) -> bool:
        return not suppress

    def show(self, value: object, *, name: Optional[str] = None) -> None:
        return None

    def bind_ans(self, value: object) -> None:
        return None
