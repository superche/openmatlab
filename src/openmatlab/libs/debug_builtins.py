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


# -- debug engine commands (M11 D-E2, Epic #699) ------------------------------------
def _words(args, fn):
    from openmatlab.runtime.char_value import CharValue

    out = []
    for a in args:
        if isinstance(a, CharValue) or getattr(a, "is_string", False):
            out.append(a.text if hasattr(a, "text") else str(a))
        elif hasattr(a, "backend_buffer") and np.asarray(a.backend_buffer()).size == 1:
            v = float(np.asarray(a.backend_buffer()).reshape(-1)[0])
            out.append(str(int(v)) if v == int(v) else str(v))
        else:
            raise _err(f"{fn}: arguments must be character vectors.", f"MATLAB:{fn}:InvalidInput")
    return out


def _dbg():
    from openmatlab.runtime import debugger

    d = debugger.active()
    if d is None:
        raise _err("The debugger is not available in this context.", "MATLAB:debugger:NotAvailable")
    return d


def _resolve_file(ev, name):
    """Function / script name (or path, or file>local) -> (resolved path, display name)."""
    base = name.split(">")[0].split("/")[0]
    p = Path(base)
    if p.suffix == ".m" and p.is_file():
        return str(p.resolve()), p.stem
    path = getattr(ev.functions, "path", None)
    hit = path.find_mfile(base) if path is not None else None
    if hit is None:
        try:
            fn = ev.functions.resolve(base)
        except Exception:
            fn = None
        sp = getattr(fn, "source_path", None) or getattr(getattr(fn, "info", None), "path", None)
        hit = Path(sp) if sp else None
    if hit is None:
        raise _err(f"Cannot find function '{base}'.", "MATLAB:dbstop:FileNotFound")
    return str(Path(hit).resolve()), Path(hit).stem


def _exec_lines(path):
    from openmatlab.runtime import debugger
    from openmatlab.runtime.functions import load_mfile

    try:
        loaded = load_mfile(Path(path))
    except Exception as exc:
        raise _err(f"Unable to set a breakpoint: {exc}", "MATLAB:dbstop:ParseError") from None
    body = getattr(loaded, "body", None)
    first = None
    for st in body or ():
        if type(st).__name__ not in ("FunctionDef", "LocalFunction") and getattr(st, "_line", None):
            first = st._line
            break
    return debugger.statement_lines([loaded]), first


def _dbstop(ev, args, nargout):
    w = _words(args, "dbstop")
    if not w:
        raise _err("dbstop: specify a location, e.g. dbstop in f at 3", "MATLAB:dbstop:NoLocation")
    if w[0] == "if":
        return _cond_stop(w[1:])
    name, line, cond = None, None, None
    i = 0
    while i < len(w):
        t = w[i]
        if t == "in" and i + 1 < len(w):
            name = w[i + 1]
            i += 2
        elif t == "at" and i + 1 < len(w):
            try:
                line = int(float(w[i + 1]))
            except ValueError:
                raise _err(f"dbstop: invalid line '{w[i + 1]}'", "MATLAB:dbstop:InvalidLine") from None
            i += 2
        elif t == "if":
            cond = " ".join(w[i + 1:])
            break
        elif name is None and i == 0:
            name = t  # dbstop f
            i += 1
        else:
            raise _err(f"dbstop: unexpected '{t}'", "MATLAB:dbstop:InvalidInput")
    if name is None:
        raise _err("dbstop: specify a file with 'in'.", "MATLAB:dbstop:NoLocation")
    path, stem = _resolve_file(ev, name)
    lines, first = _exec_lines(path)
    if line is None:
        if first is None:
            raise _err(f"dbstop: '{name}' has no executable lines.", "MATLAB:dbstop:NoExecutableLines")
        line = first
    else:
        after = [x for x in lines if x >= line]
        if not after:
            raise _err(f"Breakpoint cannot be set at line {line}: no executable line at or after it in {stem}.",
                       "MATLAB:dbstop:InvalidLine")
        line = after[0]
    _dbg().set_bp(path, stem, line, cond)
    return ()


def _cond_stop(w):
    from openmatlab.runtime import debugger

    kinds = ("caught error", "error", "warning", "naninf", "infnan")
    text_ = " ".join(w)
    for k in kinds:
        if text_ == k or text_.startswith(k + " "):
            ident = text_[len(k):].strip()
            k = "naninf" if k == "infnan" else k
            ids = _dbg().cond_stops.setdefault(k, [])
            ids.append(ident)
            debugger._recompute_on()
            return ()
    raise _err(f"dbstop: unknown condition 'if {text_}'", "MATLAB:dbstop:InvalidCondition")


def _dbclear(ev, args, nargout):
    from openmatlab.runtime import debugger

    w = _words(args, "dbclear")
    d = _dbg()
    if not w or w == ["all"]:
        d.clear()
        d.cond_stops.clear()
        debugger._recompute_on()
        return ()
    if w[0] == "if":
        k = " ".join(w[1:]).split(" ")[0] if w[1:2] != ["caught"] else "caught error"
        d.cond_stops.pop(k, None)
        debugger._recompute_on()
        return ()
    name, line = None, None
    i = 0
    while i < len(w):
        if w[i] == "in" and i + 1 < len(w):
            name, i = w[i + 1], i + 2
        elif w[i] == "at" and i + 1 < len(w):
            line, i = int(float(w[i + 1])), i + 2
        elif name is None:
            name, i = w[i], i + 1
        else:
            raise _err(f"dbclear: unexpected '{w[i]}'", "MATLAB:dbclear:InvalidInput")
    path, _stem = _resolve_file(ev, name)
    if line is not None:
        lines, _f = _exec_lines(path)
        after = [x for x in lines if x >= line]
        line = after[0] if after else line
    d.clear(path, line)
    return ()


def _dbstatus(ev, args, nargout):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue
    from openmatlab.numerics.ndarray_value import NDArrayValue

    w = [x for x in _words(args, "dbstatus") if x != "-completenames"]
    d = _dbg()
    files = list(d.bps)
    if w:
        path, _s = _resolve_file(ev, w[0])
        files = [f for f in files if f == path]
    elems = []
    for f in files:
        lines = sorted(d.bps[f])
        exprs = [d.bps[f][ln] or "" for ln in lines]
        elems.append({
            "name": CharValue(d.names.get(f, Path(f).stem)), "file": CharValue(f),
            "line": NDArrayValue(np.array([[float(x) for x in lines]])),
            "anonymous": NDArrayValue(np.zeros((1, len(lines)))),
            "expression": CellValue(rows=(tuple(CharValue(e) for e in exprs),)),
            "cond": CharValue(""), "identifier": CellValue(rows=()),
        })
    if not w:
        for k, ids in d.cond_stops.items():
            elems.append({"name": CharValue(""), "file": CharValue(""), "line": NDArrayValue(np.zeros((0, 0))),
                          "anonymous": NDArrayValue(np.zeros((0, 0))), "expression": CellValue(rows=()),
                          "cond": CharValue(k),
                          "identifier": CellValue(rows=(tuple(CharValue(i) for i in ids if i),)) if any(ids)
                          else CellValue(rows=())})
    fields = ("name", "file", "line", "anonymous", "expression", "cond", "identifier")
    if nargout == 0:
        for e in elems:
            if e["cond"].text:
                sys.stdout.write(f"Stop if {e['cond'].text}.\n")
                continue
            ls = [str(int(x)) for x in np.asarray(e["line"].backend_buffer()).reshape(-1)]
            if len(ls) == 1:
                sys.stdout.write(f"Breakpoint for {e['name'].text} is on line {ls[0]}.\n")
            else:
                sys.stdout.write(f"Breakpoints for {e['name'].text} are on lines {', '.join(ls)}.\n")
        return ()
    return (StructValue((len(elems), 1), fields, tuple(elems)),)


def _paused(fn):
    d = _dbg()
    if not d.paused:
        raise _err(f"{fn}: only valid when stopped at a breakpoint (K>> prompt).", "MATLAB:debugger:NotInDebugMode")
    return d, d.paused[-1]


def _dbcont(ev, args, nargout):
    _d, st = _paused("dbcont")
    st.resume = "cont"
    return ()


def _dbstep(ev, args, nargout):
    d, st = _paused("dbstep")
    w = _words(args, "dbstep")
    mode, n = "step", 1
    if w:
        if w[0] in ("in", "out"):
            mode = w[0]
        else:
            try:
                n = int(float(w[0]))
            except ValueError:
                raise _err(f"dbstep: invalid argument '{w[0]}'", "MATLAB:dbstep:InvalidInput") from None
            if n < 1:
                raise _err("dbstep: N must be a positive integer.", "MATLAB:dbstep:InvalidInput")
    d.request_step(mode, n)
    st.resume = "step"
    return ()


def _dbquit(ev, args, nargout):
    _d, st = _paused("dbquit")
    st.resume = "quit"
    return ()


def _dbup(ev, args, nargout):
    _d, st = _paused("dbup")
    n = int(_words(args, "dbup")[0]) if args else 1
    st.idx = max(-1, st.idx - n)
    sys.stdout.write("In base workspace.\n" if st.idx < 0 else
                     f"In workspace belonging to {st.frames[st.idx].name}.\n")
    return ()


def _dbdown(ev, args, nargout):
    _d, st = _paused("dbdown")
    n = int(_words(args, "dbdown")[0]) if args else 1
    if st.idx >= len(st.frames) - 1:
        raise _err("In the workspace of the function where execution stopped; cannot go down further.",
                   "MATLAB:dbdown:BottomOfStack")
    st.idx = min(len(st.frames) - 1, st.idx + n)
    sys.stdout.write(f"In workspace belonging to {st.frames[st.idx].name}.\n")
    return ()


INTRINSICS = {"dbstop": _dbstop, "dbclear": _dbclear, "dbstatus": _dbstatus, "dbcont": _dbcont, "dbstep": _dbstep,
              "dbquit": _dbquit, "dbup": _dbup, "dbdown": _dbdown}
