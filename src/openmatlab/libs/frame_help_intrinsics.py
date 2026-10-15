"""evalin, assignin, doc, lookfor, what (M7 C11, Epic #610).

evalin/assignin reach the caller or base workspace through runtime.frames.
doc/lookfor/what follow MATLAB's text behaviour in a terminal: doc shows the
help text (there is no documentation browser), lookfor searches H1 lines,
and what lists the MATLAB files in a folder or returns them as a struct.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import numpy as np

from openmatlab.numerics.ndarray_value import NDArrayValue


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _texts(args, fn):
    from openmatlab.runtime.char_value import CharValue

    out = []
    for a in args:
        if not isinstance(a, CharValue):
            raise _err(f"{fn}: arguments must be character vectors or string scalars.", f"MATLAB:{fn}:InvalidInput")
        out.append(a.text if not (getattr(a, "is_string", False) and hasattr(a, "data")) else str(a.data.flat[0]))
    return out


def _target(ev, where, fn):
    from openmatlab.runtime import frames

    w = where.lower()
    if w == "base":
        return frames.base(ev)
    if w == "caller":
        return frames.caller(ev)
    raise _err(f"{fn}: first argument must be 'base' or 'caller'.", f"MATLAB:{fn}:invalidContext" if fn == "evalin" else "MATLAB:assignin:invalidContext")


def _evalin(ev, args, nargout):
    from openmatlab.libs.function_intrinsics import _eval
    from openmatlab.runtime import frames

    if len(args) < 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    where = _texts(args[:1], "evalin")[0]
    tgt = _target(ev, where, "evalin")
    # inside the target frame, its own caller/base are what they were when it was running:
    # evaluate with the stack trimmed to the frames below the target
    from openmatlab.runtime.frames import _STACK

    st = _STACK.get()
    below = st[: st.index(tgt)] if tgt in st else ()
    token = _STACK.set(below)
    try:
        return _eval(tgt, list(args[1:]), nargout)
    finally:
        _STACK.reset(token)


def _assignin(ev, args, nargout):
    if len(args) != 3:
        raise _err("assignin: expected assignin(ws, 'name', value).", "MATLAB:narginchk:notEnoughInputs" if len(args) < 3 else "MATLAB:TooManyInputs")
    where, name = _texts(args[:2], "assignin")

    if not re.fullmatch(r"[A-Za-z]\w{0,62}", name) or name in _keywords():
        raise _err(f"Invalid variable name \"{name}\" in ASSIGNIN.", "MATLAB:assignin:invalidVariableName")
    tgt = _target(ev, where, "assignin")
    tgt.workspace.set(name, args[2])
    return ()


def _keywords():
    return {"break", "case", "catch", "classdef", "continue", "else", "elseif", "end", "for", "function",
            "global", "if", "otherwise", "parfor", "persistent", "return", "spmd", "switch", "try", "while"}


# ------------------------------------------------------------------ help browsing
def _h1(path: Path) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    for ln in lines:
        st = ln.strip()
        if not st or st.startswith("function") or st.startswith("classdef"):
            continue
        if st.startswith("%"):
            return st.lstrip("%").strip()
        break
    return ""


def _search_dirs(ev):
    dirs = [Path.cwd()]
    p = getattr(ev.functions, "path", None)
    if p is not None:
        dirs += [Path(d) for d in p.list()]
    seen, out = set(), []
    for d in dirs:
        r = d.resolve()
        if r not in seen and r.is_dir():
            seen.add(r)
            out.append(r)
    return out


def _doc(ev, args, nargout):
    from openmatlab.libs.workspace_commands import _help
    from openmatlab.runtime.char_value import CharValue

    names = _texts(args, "doc")
    if not names:
        sys.stdout.write("The documentation browser is not available in OpenMATLAB. Use help NAME, or see https://www.mathworks.com/help/matlab/.\n")
        return ()
    out = _help(ev, [CharValue(names[0])], 1)[0].text
    if out.strip().endswith("not found."):
        sys.stdout.write(f"No documentation found for \"{names[0]}\".\n")
        return ()
    sys.stdout.write(out)
    return ()


_BUILTIN_H1 = {}


def _builtin_h1(name, fn):
    doc = (getattr(fn, "__doc__", None) or "").strip().splitlines()
    return doc[0].strip() if doc else ""


def _lookfor(ev, args, nargout):
    words = _texts(args, "lookfor")
    if not words:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    flags = [w for w in words[1:] if w.startswith("-")]
    key = words[0].lower()
    full = "-all" in flags
    hits = []
    for d in _search_dirs(ev):
        for f in sorted(d.glob("*.m")):
            h1 = _h1(f)
            body = f.read_text(errors="replace").lower() if full else ""
            if key in f.stem.lower() or key in h1.lower() or (full and key in body):
                hits.append((f.stem, h1))
    for name, fn in sorted(getattr(ev.functions, "builtins", {}).items()):
        h1 = _builtin_h1(name, fn)
        if key in name.lower():
            hits.append((name, h1 or "built-in function"))
    seen, rows = set(), []
    for n, h in hits:
        if n not in seen:
            seen.add(n)
            rows.append((n, h))
    w = max([len(n) for n, _ in rows] + [0])
    text = "".join(f"{n.ljust(w)} - {h}\n" for n, h in rows)
    if nargout:
        from openmatlab.runtime.char_value import CharValue

        return (CharValue(text.rstrip("\n")),)
    sys.stdout.write(text)
    return ()


def _what(ev, args, nargout):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue
    from openmatlab.runtime.struct_value import StructValue

    names = _texts(args, "what")
    d = Path(names[0]).expanduser() if names else Path.cwd()
    if not d.is_absolute():
        cand = Path.cwd() / d
        if not cand.is_dir():
            cand = next((p / d for p in _search_dirs(ev) if (p / d).is_dir()), cand)
        d = cand
    if not d.is_dir():
        if nargout:
            return (StructValue((0, 1), ("path", "m", "mlapp", "mlx", "mat", "mex", "p", "classes", "packages"), ()),)
        sys.stdout.write(f"Folder {names[0] if names else d} not found.\n")
        return ()
    d = d.resolve()
    groups = {
        "m": sorted(f.name for f in d.glob("*.m")),
        "mlapp": sorted(f.name for f in d.glob("*.mlapp")),
        "mlx": sorted(f.name for f in d.glob("*.mlx")),
        "mat": sorted(f.name for f in d.glob("*.mat")),
        "mex": sorted(f.name for f in d.iterdir() if f.suffix.startswith(".mex")),
        "p": sorted(f.name for f in d.glob("*.p")),
        "classes": sorted(f.name[1:] for f in d.iterdir() if f.is_dir() and f.name.startswith("@")),
        "packages": sorted(f.name[1:] for f in d.iterdir() if f.is_dir() and f.name.startswith("+")),
    }
    if nargout:
        def col(items):
            if not items:
                return CellValue(rows=())
            return CellValue(rows=tuple((CharValue(x),) for x in items))

        rec = {"path": CharValue(str(d))}
        rec.update({k: col(v) for k, v in groups.items()})
        return (StructValue((1, 1), tuple(rec), (rec,)),)
    labels = [("m", "MATLAB Code files"), ("mlx", "MATLAB Live Code files"), ("mat", "MAT-files"),
              ("mlapp", "MATLAB App files"), ("p", "P-files"), ("classes", "Classes"), ("packages", "Packages")]
    out = []
    for k, title in labels:
        items = [os.path.splitext(x)[0] if k in ("m", "mlx", "p", "mlapp") else x for x in groups[k]]
        if items:
            out.append(f"\n{title} in folder {d}:\n\n" + "".join(f"{x}\n" for x in items))
    sys.stdout.write("".join(out) if out else f"\nNo MATLAB files in folder {d}.\n")
    return ()


def _inputname(ev, args, nargout):
    """inputname(k): the caller's variable name for argument k, or '' for an expression (#569/#640).

    Indexed and field arguments (``v(1)``, ``s.f``) return ''. A second argument
    is rejected (MATLAB takes one argument only).
    """
    from openmatlab.lang import ast_nodes as ast
    from openmatlab.runtime.char_value import CharValue

    if len(args) != 1:
        raise _err("Not enough input arguments." if not args else "Too many input arguments.",
                   "MATLAB:minrhs" if not args else "MATLAB:TooManyInputs")
    from openmatlab.runtime import frames

    st = frames._STACK.get()
    if not st or st[-1] is ev:
        raise _err("inputname can only be called from within a MATLAB function.", "MATLAB:inputname:notInFunction")
    k = int(np.asarray(args[0].backend_buffer()).reshape(-1)[0])
    exprs = getattr(st[-1], "_call_arg_exprs", None) or ()
    if k < 1 or k > max(len(exprs), getattr(ev, "_nargs", (0, 0))[0]):
        raise _err("Argument number is not valid.", "MATLAB:inputname:argNumberNotValid")
    e = exprs[k - 1] if k <= len(exprs) else None
    # Only a bare Name is a "variable name"; IndexExpr / FieldExpr / calls → ''
    return (CharValue(e.id if isinstance(e, ast.Name) else ""),)


INTRINSICS = {"inputname": _inputname, "evalin": _evalin, "assignin": _assignin, "doc": _doc, "lookfor": _lookfor, "what": _what}
STATEMENT_ZERO = {"evalin", "assignin", "doc", "lookfor", "what"}
