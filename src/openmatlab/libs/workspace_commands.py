"""Workspace / session commands (Epic #532).

clear, clearvars, who, whos, format, clc, help, pwd, cd, dir, ls, evalc and
the command form of which. They need the calling evaluator, so they are frame
intrinsics. Each one returns values when outputs are requested, and prints
the MATLAB listing when called as a statement (``nargout == 0``).
"""

from __future__ import annotations

import contextlib
import fnmatch
import io
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
        if isinstance(a, CharValue):
            out.append(a.text)
        elif getattr(a, "is_string", False):
            out.append(str(a.data.flat[0]))
        else:
            raise _err(f"{fn}: arguments must be character vectors")
    return out


def _char(t):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(t)


def _visible(ev):
    return sorted(ev.workspace.names(), key=str.lower)


def _clear(ev, args, nargout):
    names = _texts(args, "clear")
    flags = {n.lower() for n in names if n.startswith("-") or n.lower() in ("all", "variables", "functions", "global", "classes", "mex", "import")}
    pats = [n for n in names if n not in flags and n.lower() not in flags]
    if flags & {"all", "-all", "import"}:  # clear import / clear all drop the import list (O-E5)
        from openmatlab.runtime.imports import clear_imports

        clear_imports(ev)
    if flags & {"all", "-all"}:  # MATLAB: clear all also clears globals (#640)
        store = ev.functions.global_store()
        for k in list(store):
            store.pop(k, None)
            ev.workspace.clear(k)
    if not names or flags & {"all", "-all", "variables", "-variables", "-v"} and not pats:
        ev.workspace.clear()
        return ()
    if "global" in flags or "-global" in flags:
        store = ev.functions.global_store()
        targets = [k for k in list(store) if not pats or any(fnmatch.fnmatchcase(k, p) for p in pats)]
        for k in targets:
            store.pop(k, None)
            ev.workspace.clear(k)
        return ()
    if flags & {"functions", "-functions", "classes", "mex", "import"} and not pats:
        return ()
    if "-regexp" in flags:
        hit = [n for n in _visible(ev) if any(re.match(p, n) for p in pats)]
    else:
        hit = [n for n in _visible(ev) if any(fnmatch.fnmatchcase(n, p) for p in pats)]
    if hit:
        ev.workspace.clear(*hit)
    return ()


def _clearvars(ev, args, nargout):
    names = _texts(args, "clearvars")
    # clearvars -global [names] clears the global store (#640); without -global,
    # only the local binding of a global name is removed (MATLAB).
    if "-global" in names:
        names = [n for n in names if n != "-global"]
        store = ev.functions.global_store()
        if "-except" in names:
            k = names.index("-except")
            keep, pats = names[k + 1:], names[:k] or ["*"]
        else:
            keep, pats = [], names or ["*"]
        targets = [k for k in list(store)
                   if any(fnmatch.fnmatchcase(k, p) for p in pats)
                   and not any(fnmatch.fnmatchcase(k, p) for p in keep)]
        for k in targets:
            store.pop(k, None)
            ev.workspace.clear(k)
        return ()
    if "-except" in names:
        k = names.index("-except")
        keep, pats = names[k + 1:], names[:k] or ["*"]
    else:
        keep, pats = [], names or ["*"]
    hit = [n for n in _visible(ev) if any(fnmatch.fnmatchcase(n, p) for p in pats)
           and not any(fnmatch.fnmatchcase(n, p) for p in keep)]
    if hit:
        ev.workspace.clear(*hit)
    return ()


def _who(ev, args, nargout):
    from openmatlab.runtime.cell_value import CellValue

    names = _visible(ev)
    if args:
        pats = _texts(args, "who")
        names = [n for n in names if any(fnmatch.fnmatchcase(n, p) for p in pats)]
    if nargout >= 1:
        return (CellValue(rows=tuple((_char(n),) for n in names)) if names else CellValue(rows=()),)
    if names:
        sys.stdout.write("Your variables are:\n\n" + "  ".join(names) + "\n\n")
    return ()


def _size_of(v):
    shp = getattr(v, "shape", (1, 1))
    try:
        shp = tuple(shp)
    except TypeError:
        shp = (1, 1)
    return shp if len(shp) >= 2 else (1, *shp)


def _bytes_of(v):
    buf = None
    try:
        buf = np.asarray(v.backend_buffer())
    except Exception:
        pass
    if buf is not None and buf.dtype != object:
        return int(buf.nbytes)
    if hasattr(v, "text"):
        return 2 * len(v.text)
    return 0


def _whos(ev, args, nargout):
    from openmatlab.runtime.struct_value import StructValue

    names = _visible(ev)
    if args:
        pats = _texts(args, "whos")
        names = [n for n in names if any(fnmatch.fnmatchcase(n, p) for p in pats)]
    gl = ev.functions.global_store()
    rows = []
    for n in names:
        v = ev.workspace.get(n)
        cls = v.matlab_class() if hasattr(v, "matlab_class") else type(v).__name__
        cplx = False
        try:
            cplx = bool(np.iscomplexobj(v.backend_buffer()))
        except Exception:
            pass
        rows.append((n, _size_of(v), _bytes_of(v), cls, n in gl and n in getattr(ev.workspace, "_refs", [{}])[-1], bool(getattr(v, "issparse", False)), cplx))
    if nargout >= 1:
        fields = ("name", "size", "bytes", "class", "global", "sparse", "complex", "nesting", "persistent")
        elems = tuple({
            "name": _char(n), "size": NDArrayValue(np.array([list(map(float, sz))])),
            "bytes": NDArrayValue(np.array([[float(b)]])), "class": _char(c),
            "global": NDArrayValue(np.array([[g]])), "sparse": NDArrayValue(np.array([[sp]])),
            "complex": NDArrayValue(np.array([[cx]])),
            "nesting": StructValue((1, 1), ("function", "level"), ({"function": _char(""), "level": NDArrayValue(np.array([[1.0]]))},)),
            "persistent": NDArrayValue(np.array([[False]])),
        } for n, sz, b, c, g, sp, cx in rows)
        return (StructValue((len(elems), 1), fields, elems),)
    if rows:
        w = max(4, *(len(r[0]) for r in rows))
        out = [f"  {'Name'.ljust(w)}      Size            Bytes  Class     Attributes", ""]
        for n, sz, b, c, g, sp, cx in rows:
            attrs = " ".join(a for a, on in (("global", g), ("sparse", sp), ("complex", cx)) if on)
            out.append(f"  {n.ljust(w)}      {'x'.join(map(str, sz)).ljust(14)}{str(b).rjust(7)}  {c.ljust(10)}{attrs}".rstrip())
        sys.stdout.write("\n".join(out) + "\n\n")
    return ()


def _format(ev, args, nargout):
    from openmatlab.host import display

    words = [w.lower() for w in _texts(args, "format")]
    if nargout >= 1:
        return (_char("long" if display.FORMAT["mode"] == "long" else "short"),)
    mode = "short"
    for w in words:
        if w.startswith("long"):
            mode = "long"
        elif w.startswith("short") or w == "default":
            mode = "short"
        elif w in ("compact", "loose", "rat", "hex", "bank", "+"):
            continue  # accepted; layout-only modes are not modelled (residual)
        else:
            raise _err(f"format: unknown format '{w}'", "MATLAB:format:unknownFormat")
    display.FORMAT["mode"] = mode
    return ()


def _clc(ev, args, nargout):
    return ()  # command window clear: nothing to clear on a plain stdout


def _help(ev, args, nargout):
    names = _texts(args, "help")
    if not names:
        text = "help NAME displays help for the function NAME.\n"
    else:
        name = names[0]
        text = ""
        mfile = None
        try:
            mfile = ev.functions._find(name)
        except Exception:
            mfile = None
        if mfile is not None:
            lines = Path(mfile).read_text().splitlines()
            block, started = [], False
            for ln in lines:
                st = ln.strip()
                if st.startswith("%"):
                    block.append(st.lstrip("%").rstrip())
                    started = True
                elif started or (st and not st.startswith("function")):
                    break
            text = "\n".join(" " + b for b in block) + "\n" if block else f" No help found for {name}.\n"
        elif name.lower() in getattr(ev.functions, "builtins", {}) or name.lower() in _intrinsic_names():
            text = f" {name} is a built-in function.\n"
        else:
            text = f"{name} not found.\n"
    if nargout >= 1:
        return (_char(text),)
    sys.stdout.write(text)
    return ()


def _intrinsic_names():
    from openmatlab.libs import function_intrinsics as fi

    return set(fi.INTRINSICS)


def _pwd(ev, args, nargout):
    return (_char(os.getcwd()),)


def _cd(ev, args, nargout):
    if not args:
        if nargout >= 1:
            return (_char(os.getcwd()),)
        sys.stdout.write(os.getcwd() + "\n")
        return ()
    old = os.getcwd()
    target = os.path.expanduser(_texts(args, "cd")[0])
    try:
        os.chdir(target)
    except OSError:
        raise _err(f"Cannot CD to {target} (Name is nonexistent or not a folder).", "MATLAB:cd:NonExistentFolder") from None
    return (_char(old),) if nargout >= 1 else ()


def _listing(path_arg):
    p = Path(path_arg) if path_arg else Path(".")
    if any(ch in str(p) for ch in "*?"):
        base = p.parent
        entries = sorted(base.glob(p.name), key=lambda q: q.name.lower())
        return base, entries, False
    if not p.exists():
        return p, [], False
    if p.is_file():
        return p.parent, [p], False
    return p, sorted(p.iterdir(), key=lambda q: q.name.lower()), True


def _dir(ev, args, nargout):
    from openmatlab.runtime.struct_value import StructValue
    import datetime as _dt

    base, entries, isdir = _listing(_texts(args, "dir")[0] if args else "")
    if isdir:
        entries = [base / "."] + ([base / ".."]) + entries
    if nargout >= 1:
        fields = ("name", "folder", "date", "bytes", "isdir", "datenum")
        elems = []
        for e in entries:
            try:
                st = e.stat()
                mt = _dt.datetime.fromtimestamp(st.st_mtime)
                size = 0 if e.is_dir() else st.st_size
            except OSError:
                mt, size = _dt.datetime.now(), 0
            dn = mt.toordinal() + 366 + (mt.hour * 3600 + mt.minute * 60 + mt.second) / 86400.0
            elems.append({
                "name": _char(e.name if e.name not in ("",) else str(e)),
                "folder": _char(str(e.parent.resolve())),
                "date": _char(mt.strftime("%d-%b-%Y %H:%M:%S")),
                "bytes": NDArrayValue(np.array([[float(size)]])),
                "isdir": NDArrayValue(np.array([[e.is_dir()]])),
                "datenum": NDArrayValue(np.array([[dn]])),
            })
        for e, n in zip(elems, [x.name for x in entries]):
            pass
        # Path('.')/'.' has name '' in pathlib: restore MATLAB's '.' / '..'
        if isdir and len(elems) >= 2:
            elems[0]["name"], elems[1]["name"] = _char("."), _char("..")
        return (StructValue((len(elems), 1), fields, tuple(elems)),)
    names = [e.name for e in entries]
    if isdir:
        names = [".", ".."] + names[2:]
    if names:
        sys.stdout.write("\n" + "  ".join(names) + "\n\n")
    return ()


def _ls(ev, args, nargout):
    base, entries, isdir = _listing(_texts(args, "ls")[0] if args else "")
    names = [e.name for e in entries]
    if nargout >= 1:
        return (_char("  ".join(names)),)
    if names:
        sys.stdout.write("  ".join(names) + "\n")
    return ()


def _which_cmd(ev, args, nargout):
    names = _texts(args, "which")
    if not names:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    name = names[0]
    if name in ev.workspace:
        text = f"{name} is a variable."
    else:
        w = ev.functions.which(name) if hasattr(ev.functions, "which") else ""
        if w.startswith("builtin/") or name.lower() in _intrinsic_names():
            text = f"built-in ({w or 'builtin/' + name.lower()})"
        elif w:
            text = w
        else:
            text = f"'{name}' not found."
    if nargout >= 1:
        return (_char(text if not text.endswith("not found.") else ""),)
    sys.stdout.write(text + "\n")
    return ()


def _evalc(ev, args, nargout):
    from openmatlab.libs import function_intrinsics as fi

    from openmatlab.host.display import ConsoleDisplay

    buf = io.StringIO()
    saved = ev.display
    ev.display = ConsoleDisplay(workspace=ev.workspace, stream=buf)  # capture display too
    try:
        with contextlib.redirect_stdout(buf):
            fi._eval(ev, list(args), 0)
    finally:
        ev.display = saved
    return (_char(buf.getvalue()),)


_KEYWORDS = {"break", "case", "catch", "classdef", "continue", "else", "elseif", "end", "for", "function",
             "global", "if", "otherwise", "parfor", "persistent", "return", "spmd", "switch", "try", "while"}


def _isvarname(ev, args, nargout):
    from openmatlab.runtime.char_value import CharValue

    ok = False
    if len(args) == 1 and isinstance(args[0], CharValue) and len(args[0].rows) <= 1:
        t = args[0].text
        ok = bool(re.fullmatch(r"[A-Za-z]\w{0,62}", t)) and t not in _KEYWORDS
    return (NDArrayValue(np.array([[ok]])),)


def _iskeyword(ev, args, nargout):
    from openmatlab.runtime.cell_value import CellValue

    if not args:
        return (CellValue(rows=tuple((_char(k),) for k in sorted(_KEYWORDS))),)
    return (NDArrayValue(np.array([[_texts(args, "iskeyword")[0] in _KEYWORDS]])),)


INTRINSICS = {
    "isvarname": _isvarname, "iskeyword": _iskeyword,
    "clear": _clear, "clearvars": _clearvars, "who": _who, "whos": _whos, "format": _format,
    "clc": _clc, "help": _help, "pwd": _pwd, "cd": _cd, "dir": _dir, "ls": _ls, "evalc": _evalc,
}
# statement forms that print instead of binding ans (MATLAB)
STATEMENT_ZERO = {"clear", "clearvars", "who", "whos", "format", "clc", "help", "cd", "dir", "ls", "eval", "save", "load", "fprintf"}
STATEMENT_ZERO |= {"dbstop", "dbclear", "dbstatus", "dbcont", "dbstep", "dbquit", "dbup", "dbdown"}  # M11 D-E2
COMMAND_ONLY = {"which": _which_cmd}

# graphics calls as statements: no display, no ans (Epic #537)
STATEMENT_ZERO |= {"figure", "close", "clf", "cla", "hold", "subplot", "plot", "bar", "scatter", "histogram",
                   "title", "xlabel", "ylabel", "legend", "grid", "xlim", "ylim", "axis", "text", "set",
                   "saveas", "delete", "display", "rmpath", "path", "print",
                   "evalin", "assignin", "doc", "lookfor", "what"}
# 2-D charts and annotations (Epic #772)
STATEMENT_ZERO |= {"line", "loglog", "semilogx", "semilogy", "errorbar", "area", "stairs", "stem", "barh", "pie",
                   "hist", "patch", "fill", "rectangle", "imagesc", "image", "pcolor", "contour", "contourf",
                   "quiver", "spy", "polar", "polarplot", "rose", "compass", "plotyy", "colormap", "caxis",
                   "clim", "colorbar", "zlabel", "box", "drawnow", "annotation", "axes"}
# 3-D, colour and axes helpers (Epic #771); sphere/cylinder/ellipsoid with no outputs plot
STATEMENT_ZERO |= {"plot3", "scatter3", "surf", "surfc", "mesh", "meshc", "waterfall", "surface", "contour3",
                   "bar3", "sphere", "cylinder", "ellipsoid", "view", "zlim", "shading", "light", "camlight",
                   "lighting", "material", "imshow", "daspect", "pbaspect", "clabel", "uistack", "xticks",
                   "yticks", "zticks", "xticklabels", "yticklabels", "zticklabels"}
# layout (Epic #770)
STATEMENT_ZERO |= {"tiledlayout", "nexttile", "yyaxis"}
