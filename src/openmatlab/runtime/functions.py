"""Function resolution — builtins → path → .m files."""

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

    Search order: builtins → ToolboxPath .m files (load TBD).
    """

    builtins: Dict[str, CallableFunction] = field(default_factory=dict)
    path: Optional["ToolboxPath"] = None

    def register_builtin(self, name: str, fn: CallableFunction) -> None:
        self.builtins[name.lower()] = fn

    def resolve(self, name: str) -> CallableFunction:
        key = name.lower()
        if key in self.builtins:
            return self.builtins[key]
        mfile = self._find(name)
        if mfile is not None:
            raise NotImplementedError(
                f"FunctionResolver.resolve({name!r}): found {mfile}, "
                "but .m loading/eval is not implemented yet"
            )
        raise LookupError(f"Undefined function or variable: {name}")

    def which(self, name: str) -> str:
        key = name.lower()
        if key in self.builtins:
            return f"builtin/{key}"
        mfile = self._find(name)
        if mfile is not None:
            return str(mfile)
        return ""

    def _find(self, name: str):
        if self.path is None:
            return None
        return self.path.find_mfile(name)
