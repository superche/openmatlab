"""Evaluator stub — Array-first; no float-dict eval guts."""

from __future__ import annotations

from typing import Optional

from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.value import Value
from openmatlab.runtime.workspace import Workspace


class EvalError(Exception):
    pass


class Evaluator:
    """Walk AST against Workspace. Architecture stage: not implemented."""

    def __init__(
        self,
        workspace: Optional[Workspace] = None,
        functions: Optional[FunctionResolver] = None,
    ) -> None:
        self.workspace = workspace if workspace is not None else Workspace()
        self.functions = functions if functions is not None else FunctionResolver()

    def eval_source(self, source: str) -> Optional[Value]:
        raise NotImplementedError(
            "runtime.Evaluator.eval_source: deferred until lang parser + "
            "Array Value are implemented"
        )
