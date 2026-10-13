"""Evaluator hooks for classdef objects (M8). These keep evaluator.py free of class logic.

``call(ev, target_expr, arg_exprs, nargout)`` handles a dotted or ``@``
target and returns the output list, or ``None`` when the expression is not
class-related (structs, containers.Map, ...). In that case the caller falls back
to its old path and nothing has been evaluated twice.
"""

from __future__ import annotations

from typing import List, Optional

from openmatlab.lang import ast_nodes as ast
from openmatlab.runtime import classdef as cd


def _chain(expr):
    """FieldExpr chain of static names rooted at a Name: ['a', 'b', 'c'], or None."""
    names: List[str] = []
    node = expr
    while isinstance(node, ast.FieldExpr):
        if node.name is None:
            return None
        names.append(node.name)
        node = node.target
    if not isinstance(node, ast.Name):
        return None
    names.append(node.id)
    return names[::-1]


def _root(expr):
    node = expr
    while isinstance(node, (ast.FieldExpr, ast.IndexExpr, ast.CellIndexExpr)):
        node = node.target
    return node


def call(ev, target_expr, arg_exprs: Optional[list], nargout: int = 1):
    if isinstance(target_expr, ast.SuperRef):
        return cd.super_call(ev, target_expr, ev._eval_call_args(arg_exprs or []), nargout)
    if isinstance(target_expr, ast.MetaClassExpr):
        from openmatlab.libs import classdef_builtins as _cb

        return [_cb.metaclass_for(ev, target_expr.name)]
    if not isinstance(target_expr, ast.FieldExpr) or target_expr.name is None:
        return None
    root = _root(target_expr)
    if not isinstance(root, ast.Name):
        return None
    bound = ev._name_bound(root.id)
    if bound:
        base_val = ev.workspace.get(root.id)
        if not cd.is_instance(base_val):
            return None
        inner = target_expr.target
        base = base_val if inner is root else _eval_inner(ev, inner)
        if base is None:
            return None
        if not cd.is_instance(base):
            return None
        return cd.dot_access(ev, base, target_expr.name, arg_exprs, nargout)
    if root.id == "containers":
        return None
    names = _chain(target_expr)
    if names is None:
        # e.g. Cls.member(2).prop: evaluate the inner part only if it is class-rooted
        inner_names = _chain(_root_chain(target_expr.target))
        if inner_names is None or not _class_rooted(ev, inner_names):
            return None
        base = ev.eval_expr(target_expr.target)
        if cd.is_instance(base):
            return cd.dot_access(ev, base, target_expr.name, arg_exprs, nargout)
        return [ev._index_with_exprs(_field_of(ev, base, target_expr.name), arg_exprs) if arg_exprs is not None
                else _field_of(ev, base, target_expr.name)]
    return _static_chain(ev, names, arg_exprs, nargout)


def _root_chain(expr):
    node = expr
    while isinstance(node, (ast.IndexExpr, ast.CellIndexExpr)):
        node = node.target
    return node


def _class_rooted(ev, names) -> bool:
    for k in range(len(names), 0, -1):
        if cd.lookup(ev.functions, ".".join(names[:k])) is not None:
            return True
    return False


def _field_of(ev, base, name):
    if cd.is_instance(base):
        return base.get_prop(name)
    from openmatlab.runtime import struct_eval as _se

    if _se.is_struct(base) and base.numel() == 1 and base.has(name):
        return base.get(name)
    raise cd._err("Dot indexing is not supported for variables of this type.", "MATLAB:dotRefNotAllowed")


def _eval_inner(ev, inner):
    """Value of the inner chain below an instance-rooted dotted expression."""
    if isinstance(inner, ast.FieldExpr):
        r = call(ev, inner, None, 1)
        if r is not None:
            return r[0] if r else None
    return ev.eval_expr(inner)


def _static_chain(ev, names, arg_exprs, nargout):
    """Unbound dotted names: pkg.fn(...), pkg.Cls(...), Cls.static(...), Cls.Const, Cls.Enum.prop ..."""
    res = ev.functions
    full = ".".join(names)
    # whole chain is a package function or class constructor
    if len(names) > 1 and _has_package(ev, names[0]):
        try:
            fn = res.resolve(full)
        except Exception:
            fn = None
        if fn is not None:
            from openmatlab.runtime import frames as _frames

            args = ev._eval_call_args(arg_exprs or [])
            with _frames.calling(ev):
                return list(fn(args, nargout=nargout))
    for k in range(len(names) - 1, 0, -1):
        info = cd.lookup(res, ".".join(names[:k]))
        if info is None:
            continue
        rest = names[k:]
        out = cd.class_ref_access(ev, info, rest[0], arg_exprs if len(rest) == 1 else None,
                                  nargout if len(rest) == 1 else 1)
        val = out[0] if out else None
        for i, nm in enumerate(rest[1:], start=2):
            last = i == len(rest)
            if cd.is_instance(val):
                out = cd.dot_access(ev, val, nm, arg_exprs if last else None, nargout if last else 1)
            else:
                v = _field_of(ev, val, nm)
                out = [ev._index_with_exprs(v, arg_exprs) if (last and arg_exprs is not None) else v]
            val = out[0] if out else None
        return out
    return None


def _has_package(ev, name: str) -> bool:
    path = getattr(ev.functions, "path", None)
    if path is None:
        return False
    for e in path.list():
        if (e / ("+" + name)).is_dir():
            return True
    return False
