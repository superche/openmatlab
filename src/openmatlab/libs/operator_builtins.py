"""Functional forms of MATLAB operators: plus(a,b) == a+b, etc. (Epic #531).

Each one evaluates the real operator expression through the evaluator, so its
semantics (broadcasting, class rules, sparse, strings, errors) are those of
the operator itself, with no second implementation to drift from it.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable, Dict

_BINARY = {
    "plus": "a + b", "minus": "a - b", "times": "a .* b", "mtimes": "a * b",
    "rdivide": "a ./ b", "ldivide": "a .\\ b", "power": "a .^ b", "mpower": "a ^ b",
    "eq": "a == b", "ne": "a ~= b", "lt": "a < b", "gt": "a > b", "le": "a <= b", "ge": "a >= b",
}
_UNARY = {"uminus": "-a", "uplus": "+a", "transpose": "a.'", "ctranspose": "a'"}


@lru_cache(maxsize=None)
def _expr(src: str):
    from openmatlab.lang.parser import parse

    return parse(src)[0].expr


def _backend():
    from openmatlab.numerics.numpy_backend import NumPyArrayBackend

    global _BK
    try:
        return _BK
    except NameError:
        _BK = NumPyArrayBackend()
        return _BK


def _make(name: str, src: str, arity: int) -> Callable:
    def fn(args, *, nargout=1):
        from openmatlab.runtime.evaluator import EvalError, Evaluator
        from openmatlab.runtime.workspace import Workspace

        if len(args) != arity:
            raise EvalError("Not enough input arguments." if len(args) < arity else "Too many input arguments.",
                            "MATLAB:minrhs" if len(args) < arity else "MATLAB:TooManyInputs")
        ws = Workspace()
        for n, v in zip("ab", args):
            ws.set(n, v)
        return (Evaluator(workspace=ws, numerics=_backend()).eval_expr(_expr(src)),)

    fn.__name__ = name
    return fn


def _cat(axis_src: str):
    def fn(args, *, nargout=1):
        from openmatlab.runtime.evaluator import Evaluator
        from openmatlab.runtime.workspace import Workspace
        from openmatlab.lang.parser import parse

        ws = Workspace()
        names = [f"v{i}" for i in range(len(args))]
        for n, v in zip(names, args):
            ws.set(n, v)
        src = "[" + axis_src.join(names) + "]"
        return (Evaluator(workspace=ws, numerics=_backend()).eval_expr(parse(src)[0].expr),)

    return fn


def register(builtins: Dict[str, Callable]) -> None:
    for name, src in _BINARY.items():
        builtins.setdefault(name, _make(name, src, 2))
    for name, src in _UNARY.items():
        builtins.setdefault(name, _make(name, src, 1))
    builtins.setdefault("horzcat", _cat(", "))
    builtins.setdefault("vertcat", _cat("; "))
