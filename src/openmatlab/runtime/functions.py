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
    # Local functions defined after the script code (MATLAB R2016b+, #529).
    local_functions: Tuple[FunctionDef, ...] = ()


@dataclass(frozen=True)
class ClassFile:
    """Marker returned by load_mfile for a classdef file (M8); the resolver loads it as a class."""

    path: Path


def load_mfile(path: Path) -> FunctionDef | Script:
    """Load a .m file as a function or a script."""
    text = path.read_text(encoding="utf-8")
    from openmatlab.lang.classdef_parser import is_classdef_source

    if is_classdef_source(text):  # a class file is neither a script nor a function (M8)
        return ClassFile(path.resolve())
    stmts = parse(text)
    funcs = [s for s in stmts if isinstance(s, FunctionDef)]
    if funcs and not isinstance(stmts[0], FunctionDef):
        # Script with local functions: all function blocks must come last (MATLAB).
        first = next(i for i, s in enumerate(stmts) if isinstance(s, FunctionDef))
        if any(not isinstance(s, FunctionDef) for s in stmts[first:]):
            raise ValueError(
                f"Mixed function/script in {path.name}: local functions in a script must be defined at the end of the file"
            )
        return Script(body=tuple(stmts[:first]), source_path=path.resolve(), local_functions=tuple(funcs))
    if funcs:
        if any(not isinstance(s, FunctionDef) for s in stmts):
            raise ValueError(f"Mixed function/script in {path.name}: statements after function definitions are not allowed")
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

    def bind_ref(self, name, store, default) -> None:
        self._ws(name).bind_ref(name, store, default)

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

    def global_store(self):
        return self._inner.global_store()

    def persistent_store(self, key):
        return self._inner.persistent_store(key)

    def __getattr__(self, attr: str):
        return getattr(self._inner, attr)


def parse_mfile(path: Path) -> FunctionDef:
    """Parse a .m file; require a top-level function definition."""
    loaded = load_mfile(path)
    if not isinstance(loaded, FunctionDef):
        raise ValueError(f"No function definition in {path}")
    return loaded


def eval_script(script: Script, evaluator: Any) -> Optional[Value]:
    """Evaluate a script in the given evaluator's workspace (shared base WS).

    Local functions (#529) are visible to the script body, to each other and as
    handles (``@name``) for the duration of the run. The script gets its own
    call-stack frame (dbstack / MException.stack, #698)."""
    from openmatlab.runtime import callstack as _cs

    path = script.source_path
    saved = evaluator._frame
    with _cs.entering(_cs.Frame(str(Path(path).resolve()) if path else "", Path(path).stem if path else "")) as fr:
        evaluator._frame = fr
        fr.ev = evaluator
        try:
            return _eval_script_body(script, evaluator)
        finally:
            evaluator._frame = saved


def _eval_script_body(script: Script, evaluator: Any) -> Optional[Value]:
    if not script.local_functions:
        return evaluator.eval_program(list(script.body))
    outer = evaluator.functions
    local: Dict[str, Any] = {}
    for f in script.local_functions:
        local[f.name.lower()] = MFileCallable(
            defn=f, numerics=evaluator.numerics, plots=evaluator.plots,
            resolver=outer, source_path=script.source_path,
        )
    scope = _ScopedResolver(outer, local)
    for fn in local.values():
        fn.scope = scope
    evaluator.functions = scope
    try:
        return evaluator.eval_program(list(script.body))
    finally:
        evaluator.functions = outer


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
    # MATLAB stack name override, e.g. "Class.method" for classdef methods (#698).
    qualname: Optional[str] = None

    def __call__(
        self,
        args: Sequence[Value],
        *,
        nargout: int = 1,
        prebind: Optional[Dict[str, Value]] = None,
    ) -> Sequence[Value]:
        from openmatlab.runtime.evaluator import (
    EvalError,
    Evaluator,
    _BreakSignal,
    _ContinueSignal,
    _ReturnSignal,
)
        from openmatlab.runtime.workspace import Workspace

        inputs = list(self.defn.inputs)
        variadic_in = bool(inputs) and inputs[-1] == "varargin"
        fixed_in = inputs[:-1] if variadic_in else inputs
        if not variadic_in and len(args) > len(inputs):
            raise EvalError("Too many input arguments.", "MATLAB:TooManyInputs")
        outputs = list(self.defn.outputs)
        variadic_out = bool(outputs) and outputs[-1] == "varargout"
        if not variadic_out and nargout > max(len(outputs), 1):
            raise EvalError("Too many output arguments.", "MATLAB:TooManyOutputs")
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
        for name, val in (prebind or {}).items():  # constructor output pre-set to the default object (M8)
            ws.set(name, val)
        for name, val in zip(fixed_in, args):
            ws.set(name, val)  # any MATLAB value (cell, struct, handle, ...) (#531)
        if variadic_in:
            from openmatlab.runtime.cell_value import CellValue

            extra = list(args[len(fixed_in):])
            ws.set("varargin", CellValue(rows=(tuple(extra),)) if extra else CellValue(rows=()))
        ev = Evaluator(
            workspace=ws,
            functions=scope,
            numerics=self.numerics,
            plots=self.plots,
        )
        ev._return_ok += 1
        ev._nargs = (len(args), nargout)
        ev._persist_key = (str(self.source_path), self.defn.name)
        from openmatlab.runtime import callstack as _cs

        frame = _cs.Frame(str(self.source_path) if self.source_path else "",
                          _cs.frame_name(self.source_path, self.defn.name, self.qualname),
                          getattr(self.defn, "_line", 0))
        ev._frame = frame
        frame.ev = ev
        try:
            try:
                with _cs.entering(frame):
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
        if not outputs:
            return ()
        want = max(nargout, 1)
        fixed_out = outputs[:-1] if variadic_out else outputs
        outs: List[Value] = []
        for o in fixed_out:
            try:
                outs.append(ws.get(o))
            except KeyError:
                if len(outs) < want and (nargout >= 1 and len(outs) < nargout):
                    raise EvalError(
                        f'Output argument "{o}" (and possibly others) not assigned a value '
                        f'in the execution with "{self.defn.name}" function.',
                        "MATLAB:unassignedOutputs",
                    ) from None
                break
        if variadic_out and len(outs) == len(fixed_out):
            try:
                vo = ws.get("varargout")
            except KeyError:
                vo = None
            if vo is not None:
                rows, cols = vo.shape
                outs.extend(vo.get(i, j) for j in range(cols) for i in range(rows))
            if nargout > len(outs):
                raise EvalError(
                    f'Output argument "varargout{{{len(outs) + 1}}}" not assigned a value '
                    f'in the execution with "{self.defn.name}" function.',
                    "MATLAB:unassignedOutputs",
                )
        return tuple(outs[:want])


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
            return self._load(mfile, name)
        raise LookupError(f"Undefined function or variable: {name}")

    def which(self, name: str) -> str:
        key = name.lower()
        if key in self.builtins:
            return f"builtin/{key}"
        mfile = self._find(name)
        if mfile is not None:
            return str(mfile)
        return ""

    def global_store(self) -> Dict[str, Any]:
        if not hasattr(self, "_globals"):
            self._globals = {}
        return self._globals

    def persistent_store(self, key) -> Dict[str, Any]:
        if not hasattr(self, "_persist"):
            self._persist = {}
        return self._persist.setdefault(key, {})

    def _find(self, name: str):
        if self.path is None:
            return None
        return self.path.find_mfile(name)

    def _load(self, mfile: Path, name: str = "") -> MFileCallable:
        key = str(mfile.resolve())
        if key in self._cache:
            return self._cache[key]
        if self._numerics is None:
            raise RuntimeError(
                "FunctionResolver.bind_runtime(numerics) required before loading .m"
            )
        from openmatlab.lang.classdef_parser import is_classdef_source

        text = mfile.read_text(encoding="utf-8")
        if is_classdef_source(text):  # classdef file (M8)
            from openmatlab.lang.classdef_parser import parse_classdef
            from openmatlab.lang.parser import ParseError
            from openmatlab.runtime import classdef as _cd

            try:
                node = parse_classdef(text)
            except ParseError as exc:
                raise ValueError(f"Error in class file {mfile.name}: {exc}") from None
            full = name if name and name.rsplit(".", 1)[-1] == node.name else node.name
            if node.name != mfile.stem:
                raise ValueError(f"The class name '{node.name}' must match the file name '{mfile.stem}'.")
            ctor = _cd.ClassConstructor(None)
            self._cache[key] = ctor  # registered before members load (self-references in defaults)
            try:
                ctor.info = _cd.ClassInfo(node, self, mfile, full)
            except BaseException:
                self._cache.pop(key, None)
                raise
            _cd.register_class(ctor.info)
            return ctor
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
