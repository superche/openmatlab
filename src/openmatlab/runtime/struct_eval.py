"""Evaluator support for structs (Epic #506): field reads, cs-lists, struct
indexing, and chained assignment (s.a.b(2) = v, s(3).x = v, c{2}.f = v).

Paren indexing on struct arrays uses a *position map*: a double array holding
1..numel in the struct's shape goes through the existing numeric index and
assign paths, so ``end``, ranges, masks, growth and deletion follow the same
MATLAB rules as numeric arrays. Chained assignment recurses one step at a time.
Paren and brace steps on non-struct values run the existing ArrayAssign and
CellAssign code against a temporary variable.
"""

from __future__ import annotations

import re
from typing import List, Optional

import numpy as np

from openmatlab.lang import ast_nodes as ast
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.struct_value import CsList, StructValue, is_struct

_VALID = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _err(msg: str):
    from openmatlab.runtime.evaluator import EvalError

    return EvalError(msg)


def valid_field(name: str) -> str:
    if not _VALID.match(name) or len(name) > 63:
        raise _err(f"Invalid field name: '{name}'.")
    return name


def field_name(ev, expr: ast.FieldExpr) -> str:
    if expr.name is not None:
        return expr.name
    v = ev.eval_expr(expr.name_expr)
    from openmatlab.runtime.char_value import CharValue

    if getattr(v, "is_string", False) and v.numel() == 1:
        txt = v.text if not hasattr(v, "data") else v.data.flat[0]
    elif isinstance(v, CharValue) and len(v.rows) <= 1:
        txt = v.text
    else:
        raise _err("Dynamic structure field names must be strings or character vectors.")
    return valid_field(txt)


def positions(sv: StructValue) -> NDArrayValue:
    n = sv.numel()
    return NDArrayValue(np.arange(1, n + 1, dtype=np.float64).reshape(sv.shape, order="F"))


def _as_2d(shape):
    shape = tuple(int(d) for d in shape)
    if len(shape) == 0:
        return (1, 1)
    if len(shape) == 1:
        return (1, shape[0])
    return shape  # N-D struct arrays are allowed (#508)


def from_positions(sv: StructValue, grid, extra=()) -> StructValue:
    """Struct from a position grid: k>0 picks sv element k (or extra[k-n-1]); 0 is a new empty element."""
    g = np.asarray(grid)
    shape = _as_2d(g.shape if g.ndim else (1, 1))
    flat = g.reshape(-1, order="F")
    n = sv.numel()
    elems = []
    for p in flat:
        k = int(p)
        if k == 0:
            elems.append({})
        elif k <= n:
            elems.append(sv.elems[k - 1])
        else:
            elems.append(extra[k - n - 1])
    return StructValue.build(shape, sv.fields, elems)


def struct_index(ev, sv: StructValue, arg_exprs) -> StructValue:
    pos = positions(sv)
    idxs = ev._eval_subscripts(pos, list(arg_exprs), label="index")
    out = np.asarray(ev.numerics.index(pos, idxs).backend_buffer())
    if len(arg_exprs) == 1 and ev._is_bare_colon(arg_exprs[0]):
        out = out.reshape(-1, 1)
    return from_positions(sv, out)


def _elements_equal_fields(a: StructValue, b: StructValue) -> bool:
    return set(a.fields) == set(b.fields)


def struct_paren_assign(ev, cur: Optional[StructValue], arg_exprs, rhs) -> StructValue:
    """s(idx) = t (struct) or s(idx) = [] (delete)."""
    if cur is None:
        cur = StructValue.build((0, 0), rhs.fields if is_struct(rhs) else (), ())
    pos = positions(cur)
    n = cur.numel()
    idxs = ev._eval_subscripts(pos, list(arg_exprs), label="array assign")
    if is_struct(rhs):
        if cur.numel() and cur.fields and not _elements_equal_fields(cur, rhs):
            raise _err("Subscripted assignment between dissimilar structures.")
        fields = cur.fields if (cur.numel() or cur.fields) else rhs.fields
        for f in rhs.fields:
            if f not in fields:
                fields = fields + (f,)
        cur = StructValue.build(cur.shape, fields, cur.elems)
        rhs_s = StructValue.build(rhs.shape, fields, rhs.elems)
        markers = NDArrayValue(
            np.arange(n + 1, n + rhs_s.numel() + 1, dtype=np.float64).reshape(rhs_s.shape, order="F")
        )
        new = ev.numerics.set_index(pos, idxs, markers)
        return from_positions(cur, new.backend_buffer(), rhs_s.elems)
    from openmatlab.runtime.value import Array

    if isinstance(rhs, Array) and rhs.numel() == 0:  # deletion
        new = ev.numerics.set_index(pos, idxs, rhs)
        if len(arg_exprs) == 1 and ev._is_bare_colon(arg_exprs[0]):
            return StructValue.build((0, 0), cur.fields, ())
        return from_positions(cur, new.backend_buffer())
    raise _err("Conversion to struct from " + rhs.matlab_class() + " is not possible.")


def read_field(ev, expr: ast.FieldExpr):
    """Value of s.f; a CsList when s has more or less than one element."""
    base = ev.eval_expr(expr.target)
    if isinstance(base, CsList):
        if len(base.values) != 1:
            raise _err("Expected one output from a curly brace or dot indexing expression, but there were "
                       f"{len(base.values)} results.")
        base = base.values[0]
    if getattr(base, "is_class_instance", False):  # s.obj.prop (M8)
        return base.get_prop(field_name(ev, expr))
    if not is_struct(base):
        raise _err("Dot indexing is not supported for variables of this type.")
    name = field_name(ev, expr)
    if not base.has(name):
        raise _err(f'Unrecognized field name "{name}".')
    if base.numel() == 1:
        return base.get(name)
    return CsList(e[name] for e in base.elems)


# --- chained assignment -------------------------------------------------------

def _steps(expr) -> tuple:
    steps = []
    node = expr
    while not isinstance(node, ast.Name):
        if isinstance(node, ast.FieldExpr):
            steps.append(("field", node))
        elif isinstance(node, ast.IndexExpr):
            steps.append(("paren", list(node.indices)))
        elif isinstance(node, ast.CellIndexExpr):
            steps.append(("brace", list(node.indices)))
        else:
            raise _err("Invalid assignment target.")
        node = node.target
    return node.id, steps[::-1]


def _is_empty_double(v) -> bool:
    from openmatlab.runtime.value import Array

    return isinstance(v, Array) and not is_struct(v) and v.numel() == 0 and \
        np.asarray(v.backend_buffer()).dtype == np.float64


def chain_assign(ev, stmt: ast.ChainAssign):
    name, steps = _steps(stmt.target)
    try:
        cur = ev.workspace.get(name)
    except KeyError:
        cur = None
    rhs = ev.eval_expr(stmt.value)
    if isinstance(rhs, CsList):
        if not rhs.values:
            raise _err("Insufficient number of outputs from right hand side of equal sign to satisfy assignment.")
        rhs = rhs.values[0]
    new = _assign(ev, cur, steps, rhs, 0)
    ev.workspace.set(name, new)
    return rhs


def _temp_assign(ev, cur, kind: str, args, rhs, depth: int):
    """Run ArrayAssign / CellAssign for one step against a temporary variable."""
    from openmatlab.runtime.cell_value import CellValue

    t, r = f"__om_lv{depth}", f"__om_rv{depth}"
    if cur is None:
        cur = CellValue(rows=()) if (kind == "brace" or isinstance(rhs, CellValue)) else NDArrayValue(np.zeros((0, 0)))
    ev.workspace.set(t, cur)
    ev.workspace.set(r, rhs)
    try:
        if kind == "paren":
            ev._eval_array_assign(ast.ArrayAssign(target=ast.IndexExpr(target=ast.Name(t), indices=args),
                                                  value=ast.Name(r)))
        else:
            ev._eval_cell_assign(ast.CellAssign(target=ast.CellIndexExpr(target=ast.Name(t), indices=args),
                                                value=ast.Name(r)))
        return ev.workspace.get(t)
    finally:
        ev.workspace.clear(t, r)


def _temp_read(ev, cur, kind: str, args, depth: int):
    """Current value at cur(args) / cur{args}; None if out of range (growth)."""
    t = f"__om_lv{depth}"
    ev.workspace.set(t, cur)
    try:
        node = ast.IndexExpr(target=ast.Name(t), indices=args) if kind == "paren" else \
            ast.CellIndexExpr(target=ast.Name(t), indices=args)
        try:
            return ev.eval_expr(node)
        except Exception:
            return None
    finally:
        ev.workspace.clear(t)


def _assign(ev, cur, steps, rhs, depth):
    if not steps:
        return rhs
    kind, arg = steps[0]
    rest = steps[1:]
    if kind == "field" and getattr(cur, "is_class_instance", False):  # obj.prop = v (M8)
        name = field_name(ev, arg)
        child = cur.get_prop(name) if rest else None
        return cur.set_prop(name, _assign(ev, child, rest, rhs, depth + 1))
    if kind == "field":
        if cur is None or _is_empty_double(cur):
            cur = StructValue.scalar()
        if not is_struct(cur):
            raise _err("Unable to perform assignment because dot indexing is not supported for variables of this type.")
        if cur.numel() == 0:
            cur = StructValue.build((1, 1), cur.fields, ({},))
        if cur.numel() != 1:
            raise _err("Scalar structure required for this assignment.")
        name = field_name(ev, arg)
        valid_field(name)
        child = cur.get(name) if cur.has(name) else None
        return cur.with_field(name, _assign(ev, child, rest, rhs, depth + 1))
    if kind == "paren":
        if is_struct(cur) or ((cur is None or _is_empty_double(cur)) and (rest or is_struct(rhs))):
            if not rest:
                return struct_paren_assign(ev, cur if is_struct(cur) else None, arg, rhs)
            return _struct_element_assign(ev, cur if is_struct(cur) else None, arg, rest, rhs, depth)
        if rest:
            raise _err("Unable to perform assignment because dot indexing is not supported for variables of this type."
                       if rest[0][0] == "field" else "Invalid use of () before further indexing in assignment.")
        if is_struct(rhs):
            raise _err("Conversion to " + cur.matlab_class() + " from struct is not possible.")
        return _temp_assign(ev, cur, "paren", arg, rhs, depth)
    # brace
    from openmatlab.runtime.cell_value import CellValue

    if cur is not None and not isinstance(cur, CellValue) and not _is_empty_double(cur) and \
            not getattr(cur, "is_string", False):
        raise _err("Brace indexing is not supported for variables of this type.")
    if _is_empty_double(cur):
        cur = None
    if not rest:
        return _temp_assign(ev, cur, "brace", arg, rhs, depth)
    old = _temp_read(ev, cur, "brace", arg, depth) if cur is not None else None
    if isinstance(old, CsList):
        old = None
    return _temp_assign(ev, cur, "brace", arg, _assign(ev, old, rest, rhs, depth + 1), depth)


def _struct_element_assign(ev, cur, args, rest, rhs, depth):
    """s(idx).rest = rhs for a single element idx (grows as needed)."""
    if cur is None:
        cur = StructValue.build((0, 0), (), ())
    pos = positions(cur)
    n = cur.numel()
    idxs = ev._eval_subscripts(pos, list(args), label="array assign")
    try:
        got = np.asarray(ev.numerics.index(pos, idxs).backend_buffer()).reshape(-1)
    except Exception:
        got = None
    if got is not None and got.size != 1:
        raise _err("Expected one output from a curly brace or dot indexing expression, but there were "
                   f"{got.size} results.")
    if got is not None:
        k = int(got[0]) - 1
        new_el = _assign(ev, cur.element(k), rest, rhs, depth + 1)
        grid = pos.backend_buffer()
        extra = ()
    else:
        new_el = _assign(ev, StructValue.build((1, 1), cur.fields, ({},)), rest, rhs, depth + 1)
        grid = ev.numerics.set_index(pos, idxs, NDArrayValue(np.array([[float(n + 1)]]))).backend_buffer()
        k = None
    if not is_struct(new_el):
        raise _err("Invalid struct element assignment.")
    fields = cur.fields + tuple(f for f in new_el.fields if f not in cur.fields)
    base = StructValue.build(cur.shape, fields, cur.elems)
    elems = list(base.elems)
    if k is not None:
        elems[k] = dict(new_el.elems[0])
        return StructValue.build(base.shape, fields, elems)
    return from_positions(base, grid, (dict(new_el.elems[0]),))


# --- list contexts --------------------------------------------------------------

def expand(ev, expr) -> List:
    """Values of one element in a list context ([...], {...}, call args)."""
    if isinstance(expr, ast.FieldExpr):
        v = read_field(ev, expr)
        return list(v.values) if isinstance(v, CsList) else [v]
    v = ev.eval_expr(expr)
    return list(v.values) if isinstance(v, CsList) else [v]


def single(v):
    """Non-list context: a cs-list yields its first value (MATLAB assignment rule)."""
    if isinstance(v, CsList):
        if not v.values:
            raise _err("Insufficient number of outputs from right hand side of equal sign to satisfy assignment.")
        return v.values[0]
    return v


def concat_structs(rows) -> StructValue:
    """[s1 s2; s3 s4]: struct arrays with the same field set."""
    from openmatlab.runtime.value import Array

    fields = None
    out_rows = []
    for r in rows:
        parts = []
        for v in r:
            if isinstance(v, Array) and not is_struct(v) and v.numel() == 0:
                continue
            if not is_struct(v):
                raise _err("Concatenation of struct with non-struct values is not supported.")
            if fields is None:
                fields = v.fields
            elif set(v.fields) != set(fields):
                raise _err("Concatenation of structures requires the same field names.")
            if v.numel():
                parts.append(v)
        if parts:
            out_rows.append(parts)
    fields = fields or ()

    def grid(v):
        g = np.empty(v.shape, dtype=object)
        for k, e in enumerate(v.elems):
            g[np.unravel_index(k, v.shape, order="F")] = e
        return g

    try:
        big = np.concatenate([np.concatenate([grid(v) for v in r], axis=1) for r in out_rows], axis=0) \
            if out_rows else np.empty((0, 0), dtype=object)
    except ValueError:
        raise _err("Dimensions of arrays being concatenated are not consistent.") from None
    return StructValue.build(big.shape, fields, list(big.reshape(-1, order="F")))


def transpose(sv: StructValue) -> StructValue:
    if len(sv.shape) > 2:
        raise _err("Transpose on ND array is not defined. Use PERMUTE instead.")
    g = np.arange(sv.numel()).reshape(sv.shape, order="F").T
    return StructValue.build(g.shape, sv.fields, [sv.elems[k] for k in g.reshape(-1, order="F")])




# --- #508: cs-lists on both sides of multi-assignment -------------------------------

def expand_rhs(ev, expr) -> List:
    """All values of s.f / c{...} on the right of [a, b] = ..."""
    if isinstance(expr, ast.FieldExpr):
        return expand(ev, expr)
    from openmatlab.runtime.cell_value import CellValue

    target = ev.eval_expr(expr.target)
    if isinstance(target, CellValue):
        t = "__om_rhs"
        ev.workspace.set(t, target)
        try:
            sub = ev._eval_cell_paren_index(target, list(expr.indices))
        finally:
            ev.workspace.clear(t)
        obj = sub.to_obj()
        return list(obj.reshape(-1, order="F"))
    return [ev.eval_expr(expr)]


def _target_count(ev, t) -> int:
    """How many outputs a target takes: s.f on an n-element struct takes n; c{idx} takes numel(idx)."""
    if isinstance(t, ast.FieldExpr):
        try:
            base = ev.eval_expr(t.target)
        except Exception:
            return 1
        return base.numel() if is_struct(base) and base.numel() > 1 else 1
    if isinstance(t, ast.CellIndexExpr) and isinstance(t.target, ast.Name) and t.target.id in ev.workspace:
        cur = ev.workspace.get(t.target.id)
        from openmatlab.runtime.cell_value import CellValue

        if isinstance(cur, CellValue):
            try:
                return max(1, ev._eval_cell_paren_index(cur, list(t.indices)).numel())
            except Exception:
                return 1
    return 1


def _assign_one(ev, target, value) -> None:
    if isinstance(target, ast.Name):
        ev.workspace.set(target.id, value)
        return
    t = "__om_mv"
    ev.workspace.set(t, value)
    try:
        if isinstance(target, ast.IndexExpr) and isinstance(target.target, ast.Name):
            ev._eval_array_assign(ast.ArrayAssign(target=target, value=ast.Name(t)))
        elif isinstance(target, ast.CellIndexExpr) and isinstance(target.target, ast.Name):
            ev._eval_cell_assign(ast.CellAssign(target=target, value=ast.Name(t)))
        else:
            chain_assign(ev, ast.ChainAssign(target=target, value=ast.Name(t)))
    finally:
        ev.workspace.clear(t)


def multi_assign_targets(ev, stmt):
    counts = [_target_count(ev, t) for t in stmt.targets]
    total = sum(counts)
    expr = stmt.value
    if isinstance(expr, (ast.FieldExpr, ast.CellIndexExpr)):
        vals = expand_rhs(ev, expr)
    else:
        if isinstance(expr, ast.IndexExpr):
            target_expr, arg_exprs = expr.target, list(expr.indices)
        elif isinstance(expr, ast.Name):
            target_expr, arg_exprs = expr, []
        else:
            raise _err("multi-assign RHS must be a function call")
        vals = list(ev._invoke_call(target_expr, arg_exprs, nargout=total) or [])
    if len(vals) < total:
        raise _err("Insufficient number of outputs from right hand side of equal sign to satisfy assignment.")
    k = 0
    for t, n in zip(stmt.targets, counts):
        if n == 1 or not isinstance(t, (ast.FieldExpr, ast.CellIndexExpr)):
            _assign_one(ev, t, vals[k])
        elif isinstance(t, ast.FieldExpr):  # [s.f] = ...: element by element
            for j in range(n):
                idx = ast.IndexExpr(target=t.target, indices=[ast.NumberLiteral(float(j + 1))])
                _assign_one(ev, ast.FieldExpr(target=idx, name=t.name, name_expr=t.name_expr), vals[k + j])
        else:  # [c{1:2}] = ...: linear positions of the selection
            from openmatlab.runtime.cell_value import CellValue

            cur = ev.workspace.get(t.target.id)
            pos = NDArrayValue(np.arange(1, cur.numel() + 1, dtype=float).reshape(cur.full_shape, order="F"))
            sel = np.asarray(ev.numerics.index(pos, ev._eval_subscripts(pos, list(t.indices), label="index"))
                             .backend_buffer()).reshape(-1, order="F")
            for j, p in enumerate(sel):
                _assign_one(ev, ast.CellIndexExpr(target=t.target, indices=[ast.NumberLiteral(float(p))]), vals[k + j])
        k += n
    return vals[0]
