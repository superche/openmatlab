"""``import pkg.name`` / ``import pkg.*`` (M8 O-E5).

An import list belongs to one evaluator (the base workspace, a script run in
it, or one function call). ``import`` wraps that evaluator's resolver in an
``ImportResolver``, which tries the imported names before the normal lookup.
Builtins stay ahead of wildcard imports so ordinary calls never touch the disk;
an exact ``import pkg.f`` still shadows them (MATLAB gives imports precedence
over everything except variables and local functions).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ImportResolver:
    def __init__(self, inner: Any, entries: List[str]) -> None:
        self._inner = inner
        self.entries = entries
        self._hits: Dict[str, Optional[str]] = {}

    def _full(self, name: str) -> Optional[str]:
        if "." in name:
            return None
        if name in self._hits:
            return self._hits[name]
        hit = None
        for e in self.entries:
            if not e.endswith(".*") and e.rsplit(".", 1)[-1] == name:
                hit = e
                break
        if hit is None and name.lower() not in getattr(self._inner, "builtins", {}):
            for e in self.entries:
                if e.endswith(".*"):
                    cand = e[:-1] + name
                    try:
                        self._inner.resolve(cand)
                    except Exception:
                        continue
                    hit = cand
                    break
        self._hits[name] = hit
        return hit

    def resolve(self, name: str):
        full = self._full(name)
        return self._inner.resolve(full if full else name)

    def which(self, name: str) -> str:
        full = self._full(name)
        return self._inner.which(full if full else name)

    def __getattr__(self, attr: str):
        return getattr(self._inner, attr)


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def import_intrinsic(ev, args, nargout):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.char_value import CharValue

    cur = ev.functions if isinstance(ev.functions, ImportResolver) else None
    if not args:
        lst = cur.entries if cur else []
        if nargout or not lst:
            return (CellValue.from_obj([[CharValue(e)] for e in lst]) if lst else CellValue(rows=()),) if nargout else ()
        return ()
    names = []
    for a in args:
        t = getattr(a, "text", None)
        if not t or not all(p.isidentifier() for p in (t[:-2] if t.endswith(".*") else t).split(".")):
            raise _err(f"Invalid import name '{t}'.", "MATLAB:import:InvalidName")
        if "." not in t:
            raise _err(f"Import argument '{t}' must be a fully qualified name or end in '.*'.",
                       "MATLAB:import:NotQualified")
        names.append(t)
    if cur is None:
        cur = ImportResolver(ev.functions, [])
        ev.functions = cur
    for n in names:
        if n not in cur.entries:
            cur.entries.append(n)
    cur._hits.clear()
    return ()


def clear_imports(ev) -> None:
    if isinstance(ev.functions, ImportResolver):
        ev.functions = ev.functions._inner
