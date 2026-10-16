"""subsref/subsasgn overloads, builtin(), substruct (M8 O-E4, #621).

Outside its own class's methods, indexing an object whose class defines
``subsref``/``subsasgn`` calls the overload with the MATLAB substruct array
``s`` (fields ``type`` and ``subs``). Inside the class's methods built-in
indexing is used, so overloads never recurse (MATLAB rule). ``builtin('subsref',
obj, s)`` / ``builtin('subsasgn', obj, s, v)`` run the default indexing.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from openmatlab.lang import ast_nodes as ast
from openmatlab.runtime import classdef as cd

Level = Tuple[str, object]  # ('.', name) | ('()', [values]) | ('{}', [values])


def _err(msg, ident=""):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg, ident)


def _cv(s):
    from openmatlab.runtime.char_value import CharValue

    return CharValue(s)


def _in_own_class(obj) -> bool:
    return any(obj.info.isa(c.name) or c.isa(obj.info.name) for c in cd._CTX.get())


def overloaded(obj, name: str):
    if not cd.is_instance(obj):
        return None
    m = obj.info.find_method(name)
    if m is None or m.static or _in_own_class(obj):
        return None
    return m


def _steps(expr) -> Optional[Tuple[str, list]]:
    """Outer-to-inner AST chain -> (root name, inner-to-outer list of AST steps)."""
    steps = []
    node = expr
    while True:
        if isinstance(node, ast.FieldExpr):
            steps.append((".", node))
            node = node.target
        elif isinstance(node, ast.IndexExpr):
            steps.append(("()", node))
            node = node.target
        elif isinstance(node, ast.CallExpr):
            steps.append(("()", node))
            node = node.func
        elif isinstance(node, ast.CellIndexExpr):
            steps.append(("{}", node))
            node = node.target
        else:
            break
    if not isinstance(node, ast.Name) or not steps:
        return None
    return node.id, steps[::-1]


def _subs_values(ev, obj, idx_exprs) -> list:
    out = []
    n = len(idx_exprs)
    for k, e in enumerate(idx_exprs):
        if ev._is_bare_colon(e):
            out.append(_cv(":"))
            continue
        endm = obj.info.find_method("end") if cd.is_instance(obj) else None
        if endm is not None:
            num = lambda x: ev.numerics.from_scalar(float(x))
            endv = float(endm([obj, num(k + 1), num(n)], nargout=1)[0].backend_buffer().reshape(-1)[0])
        else:
            endv = 1.0
        ev._end_stack.append(endv)
        try:
            out.append(ev.eval_expr(e))
        finally:
            ev._end_stack.pop()
    return out


def levels_of(ev, obj, steps) -> List[Level]:
    lv: List[Level] = []
    for kind, node in steps:
        if kind == ".":
            name = node.name
            if name is None:
                name = getattr(ev.eval_expr(node.name_expr), "text", "")
            lv.append((".", name))
        else:
            idx = list(getattr(node, "indices", None) or getattr(node, "args", None) or [])
            lv.append((kind, _subs_values(ev, obj, idx)))
    return lv


def make_s(levels: List[Level]):
    from openmatlab.runtime.cell_value import CellValue
    from openmatlab.runtime.struct_value import StructValue

    elems = []
    for kind, sub in levels:
        subs = _cv(sub) if kind == "." else CellValue(rows=(tuple(sub),)) if sub else CellValue(rows=())
        elems.append({"type": _cv(kind), "subs": subs})
    return StructValue.build((1, len(elems)), ("type", "subs"), elems)


def parse_s(s) -> List[Level]:
    if not getattr(s, "is_struct", False) or not (s.has("type") and s.has("subs")):
        raise _err("Subscript argument must be a structure with fields 'type' and 'subs'.", "MATLAB:subsArgNotStruct")
    out: List[Level] = []
    for k in range(s.numel()):
        t = s.get("type", k).text
        sub = s.get("subs", k)
        if t == ".":
            out.append((".", sub.text))
        else:
            vals = [x for r in getattr(sub, "rows", ()) for x in r]
            if hasattr(sub, "rows") and sub.rows and len(sub.rows) > 1:  # column cell
                vals = [r[0] for r in sub.rows]
            out.append((t, vals))
    return out


# -- default (built-in) indexing ---------------------------------------------------
def _tmp(ev, value):
    from openmatlab.runtime.evaluator import Evaluator

    Evaluator._tmp_seq += 1
    t = f"__om_sr{Evaluator._tmp_seq}"
    ev.workspace.set(t, value)
    return t


def _index(ev, value, kind, vals):
    names = [_tmp(ev, value)] + [_tmp(ev, v) for v in vals]
    try:
        idx = tuple(ast.Name(n) for n in names[1:])
        node = (ast.IndexExpr(target=ast.Name(names[0]), indices=idx) if kind == "()"
                else ast.CellIndexExpr(target=ast.Name(names[0]), indices=idx))
        return ev.eval_expr(node)
    finally:
        for n in names:
            ev.workspace.clear(n)


def _field(value, name):
    if cd.is_instance(value) or ((getattr(value, "is_object", False) or getattr(value, "is_graphics_handle", False))
                                 and hasattr(value, "get_prop")):
        return value.get_prop(name)
    if getattr(value, "is_struct", False) and value.numel() == 1 and value.has(name):
        return value.get(name)
    if getattr(value, "is_struct", False):
        raise _err(f"Unrecognized field name \"{name}\".", "MATLAB:nonExistentField")
    raise _err("Dot indexing is not supported for variables of this type.", "MATLAB:dotRefNotAllowed")


def default_ref(ev, value, levels: List[Level]):
    for kind, sub in levels:
        value = _field(value, sub) if kind == "." else _index(ev, value, kind, sub)
    return value


def default_asgn(ev, base, levels: List[Level], val):
    if not levels:
        return val
    (kind, sub), rest = levels[0], levels[1:]
    if kind == ".":
        if cd.is_instance(base):
            cur = base.get_prop(sub) if rest else None
            return base.set_prop(sub, default_asgn(ev, cur, rest, val))
        from openmatlab.runtime.struct_value import StructValue

        if base is None or (getattr(base, "numel", None) and not getattr(base, "is_struct", False) and base.numel() == 0):
            base = StructValue.scalar()
        if not getattr(base, "is_struct", False):
            raise _err("Unable to perform assignment because dot indexing is not supported for variables of this type.",
                       "MATLAB:dotRefNotAllowed")
        cur = base.get(sub) if (rest and base.has(sub)) else None
        return base.with_field(sub, default_asgn(ev, cur, rest, val))
    if rest:
        cur = _index(ev, base, kind, sub)
        val = default_asgn(ev, cur, rest, val)
    names = [_tmp(ev, base if base is not None else ev.numerics.from_nested([])), _tmp(ev, val)] + [_tmp(ev, v) for v in sub]
    try:
        idx = tuple(ast.Name(n) for n in names[2:])
        if kind == "()":
            st = ast.ArrayAssign(target=ast.IndexExpr(target=ast.Name(names[0]), indices=idx), value=ast.Name(names[1]),
                                 suppress=True)
        else:
            st = ast.CellAssign(target=ast.CellIndexExpr(target=ast.Name(names[0]), indices=idx), value=ast.Name(names[1]),
                                suppress=True)
        ev._exec_stmt(st)
        return ev.workspace.get(names[0])
    finally:
        for n in names:
            ev.workspace.clear(n)


# -- evaluator hooks -----------------------------------------------------------------
def try_ref(ev, expr, nargout=1):
    """Overloaded subsref for an object-rooted indexing expression, or None."""
    st = _steps(expr)
    if st is None or not ev._name_bound(st[0]):
        return None
    obj = ev.workspace.get(st[0])
    if getattr(obj, "native_subs", False):  # table (M10): Python-level indexing of the whole chain
        from openmatlab.runtime import table_subs as ts

        return [ts.ref(ev, obj, ts.levels(ev, obj, st[1]))]
    m = overloaded(obj, "subsref")
    if m is None:
        return None
    from openmatlab.runtime import frames

    s = make_s(levels_of(ev, obj, st[1]))
    with frames.calling(ev):
        return list(m([obj, s], nargout=nargout))


def try_asgn(ev, target, value_expr) -> Optional[object]:
    st = _steps(target)
    if st is None or not ev._name_bound(st[0]):
        return None
    obj = ev.workspace.get(st[0])
    if getattr(obj, "native_subs", False):
        from openmatlab.runtime import table_subs as ts

        val = ev.eval_expr(value_expr)
        out = ts.asgn(ev, obj, ts.levels(ev, obj, st[1]), val)
        ev.workspace.set(st[0], out)
        return out
    m = overloaded(obj, "subsasgn")
    if m is None:
        return None
    from openmatlab.runtime import frames

    val = ev.eval_expr(value_expr)
    s = make_s(levels_of(ev, obj, st[1]))
    with frames.calling(ev):
        outs = list(m([obj, s, val], nargout=1))
    if not outs:
        if obj.info.is_handle:
            return obj
        raise _err("subsasgn must return the modified object.", "MATLAB:class:subsasgnOutput")
    ev.workspace.set(st[0], outs[0])
    return outs[0]


# -- intrinsics -----------------------------------------------------------------------
def _subsref(ev, args, nargout):
    m = overloaded(args[0], "subsref")
    if m is not None:
        return list(m(list(args), nargout=max(1, nargout)))
    return [default_ref(ev, args[0], parse_s(args[1]))]


def _subsasgn(ev, args, nargout):
    m = overloaded(args[0], "subsasgn")
    if m is not None:
        return list(m(list(args), nargout=1))
    return [default_asgn(ev, args[0], parse_s(args[1]), args[2])]


def _substruct(ev, args, nargout):
    if len(args) % 2:
        raise _err("Not enough input arguments.", "MATLAB:minrhs")
    lv: List[Level] = []
    for k in range(0, len(args), 2):
        t = args[k].text
        sub = args[k + 1]
        if t == ".":
            lv.append((".", sub.text))
        elif t in ("()", "{}"):
            lv.append((t, [x for r in getattr(sub, "rows", ()) for x in r]))
        else:
            raise _err("Invalid subscript type.", "MATLAB:substruct:invalidType")
    return [make_s(lv)]


def _builtin(ev, args, nargout):
    if not args or getattr(args[0], "text", None) is None:
        raise _err("Function name must be a character vector.", "MATLAB:builtin:nameMustBeText")
    name, rest = args[0].text, list(args[1:])
    if name == "subsref":
        return [default_ref(ev, rest[0], parse_s(rest[1]))]
    if name == "subsasgn":
        return [default_asgn(ev, rest[0], parse_s(rest[1]), rest[2])]
    table = getattr(ev.functions, "builtins", {}) or {}
    fn = table.get(name) or table.get(name.lower())
    if fn is None:
        from openmatlab.libs import function_intrinsics as _fi

        if name.lower() in _fi.INTRINSICS:
            return list(_fi.INTRINSICS[name.lower()](ev, rest, nargout))
        raise _err(f"Cannot find builtin function '{name}'.", "MATLAB:builtin:NotBuiltin")
    return list(fn(rest, nargout=nargout))


INTRINSICS = {"subsref": _subsref, "subsasgn": _subsasgn, "substruct": _substruct, "builtin": _builtin}
