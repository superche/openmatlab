"""Small base-MATLAB functions left in GAP-ANALYSIS p0 rows (M7 close-out).

colon, cputime, display, rmpath, path, print (figure export via saveas).
"""

from __future__ import annotations

import time
from typing import Callable, Dict

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _scalar(v, fn):
    if not hasattr(v, "backend_buffer"):
        raise _err(f"{fn}: arguments must be numeric scalars.", f"MATLAB:{fn}:InvalidInput")
    return float(np.asarray(v.backend_buffer()).reshape(-1)[0])


def _colon(ev, args, nargout):
    from openmatlab.lang.parser import parse

    if len(args) not in (2, 3):
        raise _err("colon: expected colon(j, k) or colon(j, i, k).", "MATLAB:colon:InvalidInput")
    vals = [_scalar(a, "colon") for a in args]
    j, k = vals[0], vals[-1]
    i = vals[1] if len(vals) == 3 else 1.0
    return (ev.numerics.colon(j, k, i) if hasattr(ev.numerics, "colon") and len(vals) == 2 else
            ev.eval_expr(parse(f"({j!r}):({i!r}):({k!r})")[0].expr),)


def _cputime(ev, args, nargout):
    return (NDArrayValue(np.array([[time.process_time()]])),)


def _display(ev, args, nargout):
    if len(args) != 1:
        raise _err("display: expected one argument.", "MATLAB:display:InvalidInput")
    ev.display.show(args[0], name=None)
    return ()


def _paths(ev):
    p = getattr(ev.functions, "path", None)
    if p is None:
        raise _err("path: no search path on this session.", "MATLAB:path:NoPath")
    return p


def _rmpath(ev, args, nargout):
    import os

    p = _paths(ev)
    for a in args:
        for d in a.text.split(os.pathsep):
            if d:
                p.rmpath(d)
    return ()


def _path(ev, args, nargout):
    import os

    from openmatlab.runtime.char_value import CharValue

    p = _paths(ev)
    if args:
        p.entries = []
        for a in reversed(args):
            for d in reversed(a.text.split(os.pathsep)):
                if d:
                    p.addpath(d)
    text = os.pathsep.join(str(e) for e in p.list())
    if nargout == 0 and not args:
        print("\n\t\tMATLABPATH\n")
        for e in p.list():
            print(f"\t{e}")
        return ()
    return (CharValue(text),) if nargout else ()


def _print(ev, args, nargout):
    """print(fig, '-dpng', filename) / print('-dpng', filename) / print(filename)."""
    from openmatlab.libs import graphics_builtins as gb
    from openmatlab.runtime.char_value import CharValue

    m = gb.model(ev)
    fig = None
    fmt = None
    fname = None
    for a in args:
        if isinstance(a, CharValue):
            t = a.text
            if t.startswith("-d"):
                fmt = t[2:].lower()
            elif t.startswith("-"):
                continue  # -r300 etc.: resolution flags are accepted and ignored
            else:
                fname = t
        else:
            fig = a
    if fname is None:
        raise _err("print: printing to a printer is not supported; give a file name.", "MATLAB:print:NoPrinter")
    if fmt is None and "." not in fname.rsplit("/", 1)[-1]:
        fmt = "png"  # print(filename) defaults to PNG for figures
    fmt = {"jpeg": "jpg", "epsc": "eps", "svg": "svg"}.get(fmt, fmt)
    target = fig if fig is not None else gb._h(m.gcf().id)
    sargs = [target, CharValue(fname)] + ([CharValue(fmt)] if fmt else [])
    return gb.INTRINSICS["saveas"](ev, sargs, 0)


INTRINSICS: Dict[str, Callable] = {"colon": _colon, "cputime": _cputime, "display": _display,
                                   "rmpath": _rmpath, "path": _path, "print": _print}
STATEMENT_ZERO = {"display", "rmpath", "path", "print"}
