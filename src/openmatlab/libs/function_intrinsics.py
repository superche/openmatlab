"""Function-frame intrinsics (Epic #531).

These need the calling evaluator (its workspace, nargin/nargout, resolver), so
they are dispatched from ``Evaluator._invoke_call`` instead of ``BUILTINS``:
nargin, nargout, narginchk, nargoutchk, eval, evalc-free ``eval(try, catch)``,
feval, exist, str2func, func2str, and the global/persistent declarations.
"""

from __future__ import annotations

import re
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _num(x) -> NDArrayValue:
    return NDArrayValue(np.array([[float(x)]]))


def _text(v, fn):
    from openmatlab.runtime.char_value import CharValue

    if isinstance(v, CharValue):
        return v.text
    raise _err(f"{fn}: expected a character vector or string scalar")


def _scalar_int(v, fn) -> int:
    b = np.asarray(v.backend_buffer()).reshape(-1)
    if b.size != 1:
        raise _err(f"{fn}: expected a scalar")
    return int(b[0]) if np.isfinite(b[0]) else (10**12 if b[0] > 0 else -(10**12))


def _empty():
    return NDArrayValue(np.zeros((0, 0)))


def declare(ev, stmt):
    if stmt.kind == "global":
        store = ev.functions.global_store()
    else:
        if ev._persist_key is None:
            raise _err("A PERSISTENT declaration is only allowed in a function.")
        store = ev.functions.persistent_store(ev._persist_key)
    for n in stmt.names:
        if stmt.kind == "global" and n in ev.workspace and n not in store:
            store[n] = ev.workspace.get(n)  # MATLAB warns and keeps the global value; adopt local if new
        ev.workspace.bind_ref(n, store, _empty())
    return ev.numerics.from_scalar(0.0)


def _frame(ev, fn):
    if ev._nargs is None:
        raise _err(f"You can only call nargin/nargout from within a MATLAB function.", "MATLAB:nargin:isScript")
    return ev._nargs


def _nargin(ev, args, nargout):
    if args:
        return (_num(_declared_count(ev, args[0], "nargin")),)
    return (_num(_frame(ev, "nargin")[0]),)


def _nargout(ev, args, nargout):
    if args:
        return (_num(_declared_count(ev, args[0], "nargout")),)
    return (_num(_frame(ev, "nargout")[1]),)


def _declared_count(ev, f, which):
    """nargin('f') / nargout(@f): declared count, negative when variadic (MATLAB)."""
    fn = _resolve_callable(ev, f)
    defn = getattr(fn, "defn", None)
    if defn is None:
        raise _err(f"{which}: '{getattr(f, 'name', f)}' is not a MATLAB function file", "MATLAB:narginout:notValidMfile")
    names = list(defn.inputs if which == "nargin" else defn.outputs)
    var = "varargin" if which == "nargin" else "varargout"
    return -len(names) if names and names[-1] == var else len(names)


def _chk(ev, args, which):
    if len(args) != 2:
        raise _err(f"{which}chk: expected (minArgs, maxArgs)")
    lo, hi = _scalar_int(args[0], which), _scalar_int(args[1], which)
    n = _frame(ev, which)[0 if which == "nargin" else 1]
    kind = "Inputs" if which == "nargin" else "Outputs"
    word = "input" if which == "nargin" else "output"
    if n < lo:
        raise _err(f"Not enough {word} arguments.", f"MATLAB:{which}chk:notEnough{kind}")
    if n > hi:
        raise _err(f"Too many {word} arguments.", f"MATLAB:{which}chk:tooMany{kind}")
    return ()


def _eval(ev, args, nargout):
    from openmatlab.lang.parser import parse
    from openmatlab.runtime.evaluator import EvalError
    from openmatlab.lang import ast_nodes as ast

    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    code = _text(args[0], "eval")
    catch_code = _text(args[1], "eval") if len(args) > 1 else None

    def run(src):
        stmts = parse(src)
        if nargout >= 1 and len(stmts) == 1 and isinstance(stmts[0], ast.ExprStmt):
            return (ev.eval_expr(stmts[0].expr),)  # v = eval('expr'): value, no display
        for st in stmts:  # statement form: the code runs (and displays) in the caller
            ev.eval_stmt(st)
        return ()

    try:
        try:
            return run(code)
        except EvalError:
            raise
        except Exception as exc:  # parse errors are MATLAB errors
            raise _err(str(exc), "MATLAB:m_invalid_expression" if "Parse" in type(exc).__name__ else "") from None
    except (Exception) as exc:
        from openmatlab.runtime.evaluator import _BreakSignal, _ContinueSignal, _ReturnSignal

        if isinstance(exc, (_BreakSignal, _ContinueSignal, _ReturnSignal)) or catch_code is None:
            raise
        from openmatlab.runtime import errors as er

        er.record(str(exc), getattr(exc, "identifier", "") or er.infer_identifier(str(exc)))
        return run(catch_code)


def _resolve_callable(ev, f):
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if isinstance(f, FunctionHandleValue):
        return f.fn
    if isinstance(f, CharValue):
        try:
            return ev.functions.resolve(f.text)
        except LookupError:
            raise _err(f"Undefined function '{f.text}'.", "MATLAB:UndefinedFunction") from None
    raise _err("feval: first argument must be a function handle or name")


def _feval(ev, args, nargout):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    fn = _resolve_callable(ev, args[0])
    try:
        return tuple(fn(list(args[1:]), nargout=nargout))
    except ValueError as exc:
        raise _err(str(exc)) from exc


def _exist(ev, args, nargout):
    if not args:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    name = _text(args[0], "exist")
    kind = _text(args[1], "exist") if len(args) > 1 else ""
    from pathlib import Path

    if kind in ("", "var") and name in ev.workspace:
        return (_num(1),)
    if kind == "var":
        return (_num(0),)
    if kind in ("", "builtin") and name.lower() in getattr(ev.functions, "builtins", {}):
        return (_num(5),)
    if kind in ("", "file"):
        try:
            if ev.functions._find(name) is not None:
                return (_num(2),)
        except Exception:
            pass
        if Path(name).is_file():
            return (_num(2),)
    if kind in ("", "dir") and name and Path(name).is_dir():
        return (_num(7),)
    if kind in ("", "intrinsic") and name.lower() in INTRINSICS:
        return (_num(5),)
    return (_num(0),)


def _str2func(ev, args, nargout):
    from openmatlab.lang.parser import parse
    from openmatlab.lang import ast_nodes as ast
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if len(args) != 1:
        raise _err("str2func: expected one argument")
    text = _text(args[0], "str2func").strip()
    if text.startswith("@"):
        stmts = parse(text)
        expr = stmts[0].expr if stmts and isinstance(stmts[0], ast.ExprStmt) else None
        if not isinstance(expr, ast.AnonFuncExpr):
            raise _err(f"str2func: invalid anonymous function '{text}'")
        return (ev._make_anon(expr),)
    name = text
    try:
        fn = ev.functions.resolve(name)
    except LookupError:
        # MATLAB defers resolution: calling the handle errors later
        def fn(a, *, nargout=1, _n=name):
            raise _err(f"Undefined function '{_n}'.", "MATLAB:UndefinedFunction")
    return (FunctionHandleValue(name=name, fn=fn),)


def _canonical(text: str) -> str:
    """MATLAB func2str prints anonymous bodies without blanks (outside quotes)."""
    out, q = [], None
    for i, ch in enumerate(text):
        if q:
            out.append(ch)
            if ch == q:
                q = None
            continue
        if ch == '"' or (ch == "'" and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] in ")]}'_."))):
            q = ch
            out.append(ch)
            continue
        if ch in " \t":
            continue
        out.append(ch)
    return "".join(out)


def _func2str(ev, args, nargout):
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.function_handle import FunctionHandleValue

    if len(args) != 1 or not isinstance(args[0], FunctionHandleValue):
        raise _err("func2str: argument must be a function handle", "MATLAB:func2str:InputNotFunctionHandle")
    name = args[0].name
    return (CharValue(_canonical(name) if name.startswith("@") else name),)


INTRINSICS: Dict[str, Callable] = {
    "nargin": _nargin,
    "nargout": _nargout,
    "narginchk": lambda ev, a, n: _chk(ev, a, "nargin"),
    "nargoutchk": lambda ev, a, n: _chk(ev, a, "nargout"),
    "eval": _eval,
    "feval": _feval,
    "exist": _exist,
    "str2func": _str2func,
    "func2str": _func2str,
}

from openmatlab.libs import workspace_commands as _wc  # noqa: E402

INTRINSICS.update(_wc.INTRINSICS)

from openmatlab.libs import file_builtins as _fb  # noqa: E402

INTRINSICS.update(_fb.INTRINSICS)

from openmatlab.libs import graphics_builtins as _gb  # noqa: E402

INTRINSICS.update(_gb.INTRINSICS)

from openmatlab.libs import gap_leftovers as _gl  # noqa: E402

INTRINSICS.update(_gl.INTRINSICS)
