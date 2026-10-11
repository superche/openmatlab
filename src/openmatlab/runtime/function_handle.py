"""Function handle values (@name)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

from openmatlab.runtime.value import Value

if TYPE_CHECKING:
    from openmatlab.runtime.functions import CallableFunction


@dataclass(frozen=True)
class FunctionHandleValue:
    """Resolved named function handle."""

    name: str
    fn: "CallableFunction"

    def matlab_class(self) -> str:
        return "function_handle"

    def call(self, args: Sequence[Value], *, nargout: int = 1) -> Sequence[Value]:
        return self.fn(args, nargout=nargout)
