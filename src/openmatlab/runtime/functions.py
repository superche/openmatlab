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
        if any(not isinstance(s, FunctionDef) for s in stmts):
            raise ValueError(f"Mixed function/script not supported: {path}")
        main = funcs[0]
        if len(funcs) > 1:
            # Local functions: carry them as trailing FunctionDefs of main.
            main = FunctionDef(
                name=main.name,
                outputs=main.outputs,
                inputs=main.inputs,
                body=tuple(main.body) + tuple(LocalFunction(f) for f in funcs[1:]),
            )
        return main
    return Script(body=tuple(stmts), source_path=path.resolve())


@dataclass(frozen=True)
class LocalFunction:
    """Marker: a file-level local function (no shared scope), vs. nested."""

    defn: FunctionDef


def _names_in(node: Any, out: set) -> set:
    """Collect identifiers used/assigned in a body, not descending into
    nested FunctionDefs (their scope is separate)."""
    from dataclasses import fields, is_dataclass

    if isinstance(node, (FunctionDef, LocalFunction)):
        return out
    if isinstance(node, (list, tuple)):
        for x in node:
            _names_in(x, out)
        return out
    if is_dataclass(node):
        for f in fields(node):
            v = getattr(node, f.name)
            if f.name in ("id", "name") and isinstance(v, str):
                out.add(v)
            elif f.name in ("names", "targets", "var") and isinstance(v, (str, tuple, list)):
                for n in ([v] if isinstance(v, str) else v):
                    if isinstance(n, str):
                        out.add(n)
                    else:
                        _names_in(n, out)
            else:
                _names_in(v, out)
    return out


class _SharedWorkspace:
    """Nested-function workspace: names shared with the parent (MATLAB:
    textually used in both) read/write the parent frame; the rest are local."""

    def __init__(self, parent: Any, shared: set) -> None:
        from openmatlab.runtime.workspace import Workspace

        self._own = Workspace()
        self._parent = parent
        self._shared = shared

    def _ws(self, name: str):
        return self._parent if name in self._shared else self._own

    def get(self, name: str):
        return self._ws(name).get(name)

    def set(self, name: str, value: Any) -> None:
        self._ws(name).set(name, value)

    def __contains__(self, name: object) -> bool:
        return name in self._ws(name)  # type: ignore[arg-type]

    def clear(self, *names: str) -> None:
        if not names:
            self._own.clear()
        for n in names:
            self._ws(n).clear(n)

    def names(self):
        seen = set(self._own.names())
        yield from seen
        for n in self._shared:
            if n not in seen and n in self._parent:
                yield n

    def depth(self) -> int:
        return self._own.depth()

    def push(self) -> None:
        self._own.push()

    def pop(self) -> None:
        self._own.pop()

    @property
    def base(self):
        return self._own.base


class _ScopedResolver:
    """Resolver view that sees a function's nested/local functions first."""

    def __init__(self, inner: Any, local: Dict[str, Any]) -> None:
        self._inner = inner
        self._local = local

    def resolve(self, name: str):
        fn = self._local.get(name.lower())
        return fn if fn is not None else self._inner.resolve(name)

    def which(self, name: str) -> str:
        if name.lower() in self._local:
            return f"{name} is a local function"
        return self._inner.which(name)

    def __getattr__(self, attr: str):
        return getattr(self._inner, attr)


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
    # Resolver used inside the body (sees sibling local functions).
    scope: Any = None
    # For nested functions: (parent workspace getter, shared names).
    parent_ws: Any = None
    shared: Any = None

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
        ws = (
            _SharedWorkspace(self.parent_ws, self.shared)
            if self.parent_ws is not None
            else Workspace()
        )
        base_scope = self.scope if self.scope is not None else self.resolver
        local: Dict[str, Any] = {}
        mine = _names_in(list(self.defn.body), set()) | set(self.defn.inputs) | set(self.defn.outputs)
        if self.shared:
            mine |= set(self.shared)
        for stmt in self.defn.body:
            if isinstance(stmt, LocalFunction):
                local[stmt.defn.name.lower()] = MFileCallable(
                    defn=stmt.defn, numerics=self.numerics, plots=self.plots,
                    resolver=self.resolver, source_path=self.source_path,
                )
            elif isinstance(stmt, FunctionDef):
                inner = _names_in(list(stmt.body), set())
                shared = (inner & mine) - set(stmt.inputs) - set(stmt.outputs)
                local[stmt.name.lower()] = MFileCallable(
                    defn=stmt, numerics=self.numerics, plots=self.plots,
                    resolver=self.resolver, source_path=self.source_path,
                    parent_ws=ws, shared=shared,
                )
        scope = _ScopedResolver(base_scope, local) if local else base_scope
        for fn in local.values():
            # nested/local functions see each other and the enclosing scope
            fn.scope = scope
        for name, val in zip(self.defn.inputs, args):
            if not isinstance(val, Array):
                raise EvalError(f"{self.defn.name}: args must be Arrays")
            ws.set(name, val)
        ev = Evaluator(
            workspace=ws,
            functions=scope,
            numerics=self.numerics,
            plots=self.plots,
        )
        ev._return_ok += 1
        try:
            try:
                for stmt in self.defn.body:
                    if isinstance(stmt, (FunctionDef, LocalFunction)):
                        continue  # bound above as nested/local functions
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
