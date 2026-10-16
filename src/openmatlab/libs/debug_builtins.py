"""dbstack and mfilename from the MATLAB call stack (M11 D-E1, Epic #698)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from openmatlab.runtime import callstack, errors as er


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _dbstack(args, *, nargout=1):
    """dbstack, dbstack(n), dbstack('-completenames'), [ST, I] = dbstack(...)."""
    from openmatlab.runtime.char_value import CharValue

    omit, complete = 0, False
    for a in args:
        if isinstance(a, CharValue) or getattr(a, "is_string", False):
            t = a.text if hasattr(a, "text") else str(a)
            if t == "-completenames":
                complete = True
                continue
            try:
                a_n = float(t)  # command syntax: dbstack 1
            except ValueError:
                raise _err(f"dbstack: unknown option '{t}'", "MATLAB:dbstack:InvalidInput") from None
        elif hasattr(a, "backend_buffer"):
            b = np.asarray(a.backend_buffer()).ravel()
            if b.size != 1:
                raise _err("dbstack: N must be a nonnegative integer scalar", "MATLAB:dbstack:InvalidInput")
            a_n = float(b[0])
        else:
            raise _err("dbstack: invalid argument", "MATLAB:dbstack:InvalidInput")
        if a_n < 0 or a_n != int(a_n):
            raise _err("dbstack: N must be a nonnegative integer scalar", "MATLAB:dbstack:InvalidInput")
        omit = int(a_n)
    frames = callstack.snapshot()[omit:]
    if nargout == 0:
        for f, name, line in frames:
            sys.stdout.write(f"> In {f + '>' + name if complete and f else name} (line {line})\n")
        return ()
    if not complete:
        frames = tuple((Path(f).name if f else "", n, ln) for f, n, ln in frames)
    out = [er.stack_struct(frames)]
    if nargout > 1:
        from openmatlab.numerics.ndarray_value import NDArrayValue

        out.append(NDArrayValue(np.array([[1.0]])))  # current workspace index (always the top)
    return tuple(out)


def _mfilename(args, *, nargout=1):
    """mfilename, mfilename('fullpath'), mfilename('class')."""
    from openmatlab.runtime.char_value import CharValue

    fr = callstack.top()
    path = Path(fr.file) if fr is not None and fr.file else None
    opt = ""
    if args:
        a = args[0]
        if not (isinstance(a, CharValue) or getattr(a, "is_string", False)):
            raise _err("mfilename: option must be 'fullpath' or 'class'", "MATLAB:mfilename:InvalidInput")
        opt = (a.text if hasattr(a, "text") else str(a)).lower()
        if opt not in ("fullpath", "class"):
            raise _err(f"mfilename: unknown option '{opt}'", "MATLAB:mfilename:InvalidInput")
    if path is None:
        return (CharValue(""),)
    if opt == "fullpath":
        return (CharValue(str(path.with_suffix(""))),)
    if opt == "class":
        return (CharValue(fr.name.split(".")[0] if "." in fr.name else ""),)
    return (CharValue(path.stem),)


def register(builtins) -> None:
    builtins.update(dbstack=_dbstack, mfilename=_mfilename)
