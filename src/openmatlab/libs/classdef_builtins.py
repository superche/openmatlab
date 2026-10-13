"""Builtins that understand classdef instances (M8).

These wrap existing builtins at registration time so the old behaviour stays
the same for non-objects.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime import classdef as cd


def _b(x):
    return NDArrayValue(np.array([[bool(x)]]))


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def instances_equal(a, b, eq) -> bool:
    if cd.is_instance(a) or cd.is_instance(b):
        if not (cd.is_instance(a) and cd.is_instance(b)) or a.info is not b.info:
            return False
        if a.info.is_handle:
            return a is b or a.props is b.props or all(eq(a.props[k], b.props[k]) for k in a.props)
        return a.props.keys() == b.props.keys() and all(eq(a.props[k], b.props[k]) for k in a.props)
    return eq(a, b)


def _wrap_isequal(orig):
    def _eq(x, y):
        if cd.is_instance(x) or cd.is_instance(y):
            return instances_equal(x, y, _eq)
        return bool(np.asarray(orig([x, y], nargout=1)[0].backend_buffer()).reshape(-1)[0])

    def f(args, *, nargout=1):
        if any(cd.is_instance(a) for a in args):
            if len(args) < 2:
                raise _err("Not enough input arguments.", "MATLAB:minrhs")
            return (_b(all(_eq(args[0], b) for b in args[1:])),)
        return orig(args, nargout=nargout)

    return f


def _wrap_isa(orig):
    def f(args, *, nargout=1):
        if len(args) == 2 and cd.is_instance(args[0]):
            from openmatlab.runtime.char_value import CharValue

            want = args[1].text if isinstance(args[1], CharValue) else None
            if want is None:
                raise _err("isa: usage isa(obj, 'classname')")
            return (_b(args[0].info.isa(want)),)
        return orig(args, nargout=nargout)

    return f


def _wrap_isvalid(orig):
    def f(args, *, nargout=1):
        if len(args) == 1 and cd.is_instance(args[0]):
            if not args[0].info.is_handle:
                raise _err(f"Undefined function 'isvalid' for input arguments of type '{args[0].info.name}'.",
                           "MATLAB:UndefinedFunction")
            return (_b(args[0].alive),)
        if orig is None:
            raise _err("isvalid: expected a handle object.", "MATLAB:UndefinedFunction")
        return orig(args, nargout=nargout)

    return f


def _wrap_delete(orig):
    def f(args, *, nargout=1):
        if args and all(cd.is_instance(a) for a in args):
            for a in args:
                if not a.info.is_handle:
                    raise _err(f"Undefined function 'delete' for input arguments of type '{a.info.name}'.",
                               "MATLAB:UndefinedFunction")
                if a.alive:
                    m = a.info.find_method("delete")
                    if m is not None:  # user destructor (O-E7 extends this)
                        m([a], nargout=0)
                    a.alive = False
            return ()
        return orig(args, nargout=nargout)

    return f


def _superclasses_names(info):
    out = []
    for s in info.supers:
        out.append(s.name)
        out.extend(n for n in _superclasses_names(s) if n not in out)
    for b in info.builtin_bases:
        if b not in out:
            out.append(b)
    if info.is_handle and "handle" not in out:
        out.append("handle")
    return out


def _superclasses(ev_resolver):
    def f(args, *, nargout=1):
        from openmatlab.runtime.cell_value import CellValue
        from openmatlab.runtime.char_value import CharValue

        if len(args) != 1:
            raise _err("Not enough input arguments." if not args else "Too many input arguments.",
                       "MATLAB:minrhs" if not args else "MATLAB:TooManyInputs")
        a = args[0]
        info = a.info if cd.is_instance(a) else None
        if info is None and isinstance(a, CharValue):
            info = cd.lookup(ev_resolver(), a.text)
        if info is None:
            return (CellValue(rows=()),)
        names = _superclasses_names(info)
        if not names:
            return (CellValue(rows=()),)
        return (CellValue(rows=tuple((CharValue(n),) for n in names)),)

    return f


def metaclass_for(ev, name: str):
    raise _err(f"metaclass for '{name}' is not available yet.", "MATLAB:class:metaclassUnavailable")


def register_late(builtins: Dict[str, Callable]) -> None:
    if "isequal" in builtins:
        builtins["isequal"] = _wrap_isequal(builtins["isequal"])
    if "isa" in builtins:
        builtins["isa"] = _wrap_isa(builtins["isa"])
    builtins["isvalid"] = _wrap_isvalid(builtins.get("isvalid"))
    if "delete" in builtins:
        builtins["delete"] = _wrap_delete(builtins["delete"])
    builtins["superclasses"] = _superclasses(_current_resolver)


def _current_resolver():
    from openmatlab.runtime import frames as _frames

    ev = _frames.caller(None) if hasattr(_frames, "caller") else None
    return getattr(ev, "functions", None)
