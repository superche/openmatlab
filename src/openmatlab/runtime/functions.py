"""Function resolution — builtins → path → .m files (stub)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional, Protocol, Sequence

from openmatlab.runtime.value import Value

if TYPE_CHECKING:
    from openmatlab.libs.path import ToolboxPath


class CallableFunction(Protocol):
    def __call__(
        self,
        args: Sequence[Value],
        *,
        nargout: int = 1,
    ) -> Sequence[Value]:
        ...


@dataclass
class FunctionResolver:
    """Resolve a name to a callable.

    Search order (calibrated architecture):
      1. builtins registered here
      2. user path (ToolboxPath)
      3. .m function files (lang parse + runtime) — later
    """

    builtins: Dict[str, CallableFunction] = field(default_factory=dict)
    path: Optional["ToolboxPath"] = None

    def register_builtin(self, name: str, fn: CallableFunction) -> None:
        self.builtins[name.lower()] = fn

    def resolve(self, name: str) -> CallableFunction:
        key = name.lower()
        if key in self.builtins:
            return self.builtins[key]
        raise NotImplementedError(
            f"FunctionResolver.resolve({name!r}): path/.m loading not wired "
            "(architecture stage); builtins only"
        )

    def which(self, name: str) -> str:
        key = name.lower()
        if key in self.builtins:
            return f"builtin/{key}"
        return ""
