"""Function resolution — builtins → path → .m load/eval."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Sequence, Tuple

from openmatlab.lang.ast_nodes import FunctionDef, Stmt
from openmatlab.lang.parser import parse
from openmatlab.runtime.value import Array, Value

if TYPE_CHECKING:
    from openmatlab.libs.path import ToolboxPath
    from openmatlab.numerics.backend import ArrayBackend


class CallableFunction(Protocol):
    def __call__(
        self,
        args: Sequence[Value],
        *,
        nargout: int = 1,
    ) -> Sequence[Value]:
        ...


@dataclass(frozen=True)
class Script:
    """Statement-only .m file (no function header)."""

    body: Sequence[Stmt]
    source_path: Optional[Path] = None


def load_mfile(path: Path) -> FunctionDef | Script:
    """Load a .m file as a function or a script."""
    text = path.read_text(encoding="utf-8")
    stmts = parse(text)
    funcs = [s for s in stmts if isinstance(s, FunctionDef)]
    if funcs:
        if len(funcs) != 1 or any(not isinstance(s, FunctionDef) for s in stmts):
            raise ValueError(
                f"Mixed function/script or multiple functions not supported: {path}"
            )
        return funcs[0]
    return Script(body=tuple(stmts), source_path=path.resolve())


def parse_mfile(path: Path) -> FunctionDef:
    """Parse a .m file; require a top-level function definition."""
    loaded = load_mfile(path)
    if not isinstance(loaded, FunctionDef):
        raise ValueError(f"No function definition in {path}")
    return loaded


def eval_script(script: Script, evaluator: Any) -> Optional[Value]:
    """Evaluate a script in the given evaluator's workspace (shared base WS)."""
    return evaluator.eval_program(list(script.body))


@dataclass
class MFileCallable:
    """Callable wrapper for a parsed FunctionDef."""

    defn: FunctionDef
    numerics: Any
    plots: Any
    resolver: "FunctionResolver"
    source_path: Optional[Path] = None

    def __call__(
        self,
        args: Sequence[Value],
        *,
        nargout: int = 1,
    ) -> Sequence[Value]:
        from openmatlab.runtime.evaluator import (
    EvalError,
    Evaluator,
    _BreakSignal,
    _ContinueSignal,
    _ReturnSignal,
)
        from openmatlab.runtime.workspace import Workspace

        if len(args) != len(self.defn.inputs):
            raise EvalError(
                f"{self.defn.name}: expected {len(self.defn.inputs)} args, "
                f"got {len(args)}"
            )
        ws = Workspace()
        for name, val in zip(self.defn.inputs, args):
            if not isinstance(val, Array):
                raise EvalError(f"{self.defn.name}: args must be Arrays")
            ws.set(name, val)
        ev = Evaluator(
            workspace=ws,
            functions=self.resolver,
            numerics=self.numerics,
            plots=self.plots,
        )
        ev._return_ok += 1
        try:
            try:
                for stmt in self.defn.body:
                    if isinstance(stmt, FunctionDef):
                        continue  # nested not supported
                    ev.eval_stmt(stmt)
            except _ReturnSignal:
                pass  # early exit; collect assigned outputs below
            except _BreakSignal:
                raise EvalError("break outside of a for or while loop") from None
            except _ContinueSignal:
                raise EvalError("continue outside of a for or while loop") from None
        finally:
            ev._return_ok -= 1
        if not self.defn.outputs:
            return ()
        outs: List[Value] = []
        for o in self.defn.outputs:
            try:
                outs.append(ws.get(o))
            except KeyError as exc:
                raise EvalError(
                    f"{self.defn.name}: output {o!r} was not assigned"
                ) from exc
        if nargout <= 0:
            return tuple(outs)
        return tuple(outs[:nargout])


@dataclass
class FunctionResolver:
    """Resolve a name to a callable: builtins → ToolboxPath .m files."""

    builtins: Dict[str, CallableFunction] = field(default_factory=dict)
    path: Optional["ToolboxPath"] = None
    _cache: Dict[str, MFileCallable] = field(default_factory=dict)
    _numerics: Any = None
    _plots: Any = None

    def bind_runtime(self, numerics: Any, plots: Any = None) -> None:
        """Attach ArrayBackend / PlotSurface for loaded .m callables."""
        self._numerics = numerics
        self._plots = plots
        # refresh cached callables' runtime refs
        for fn in self._cache.values():
            fn.numerics = numerics
            fn.plots = plots

    def register_builtin(self, name: str, fn: CallableFunction) -> None:
        self.builtins[name.lower()] = fn

    def resolve(self, name: str) -> CallableFunction:
        key = name.lower()
        if key in self.builtins:
            return self.builtins[key]
        mfile = self._find(name)
        if mfile is not None:
            return self._load(mfile)
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

    def _load(self, mfile: Path) -> MFileCallable:
        key = str(mfile.resolve())
        if key in self._cache:
            return self._cache[key]
        if self._numerics is None:
            raise RuntimeError(
                "FunctionResolver.bind_runtime(numerics) required before loading .m"
            )
        defn = parse_mfile(mfile)
        fn = MFileCallable(
            defn=defn,
            numerics=self._numerics,
            plots=self._plots,
            resolver=self,
            source_path=mfile,
        )
        self._cache[key] = fn
        return fn
