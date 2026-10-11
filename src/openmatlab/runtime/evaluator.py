"""AST evaluator — Array-first on Session numerics (+ optional plot surface)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Sequence

from openmatlab.lang import ast_nodes as ast
from openmatlab.lang.parser import parse
from openmatlab.numerics.backend import ArrayBackend
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.value import Array, Value
from openmatlab.runtime.workspace import Workspace

if TYPE_CHECKING:
    from openmatlab.host.plot_surface import PlotSurface


class EvalError(Exception):
    pass


class _BreakSignal(Exception):
    """Internal: break leaves the innermost for/while."""


class Evaluator:
    """Walk AST against Workspace + ArrayBackend (+ optional PlotSurface)."""

    def __init__(
        self,
        workspace: Optional[Workspace] = None,
        functions: Optional[FunctionResolver] = None,
        numerics: Optional[ArrayBackend] = None,
        plots: Optional[Any] = None,
    ) -> None:
        self.workspace = workspace if workspace is not None else Workspace()
        self.functions = functions if functions is not None else FunctionResolver()
        if numerics is None:
            raise EvalError("Evaluator requires an ArrayBackend (Session.numerics)")
        self.numerics = numerics
        self.plots = plots

    def eval_source(self, source: str) -> Optional[Value]:
        stmts = parse(source)
        return self.eval_program(stmts)

    def eval_program(self, stmts: Sequence[ast.Stmt]) -> Optional[Value]:
        last: Optional[Value] = None
        for stmt in stmts:
            last = self.eval_stmt(stmt)
        return last

    def eval_stmt(self, stmt: ast.Stmt) -> Value:
        if isinstance(stmt, ast.Assign):
            value = self.eval_expr(stmt.value)
            self.workspace.set(stmt.name, value)
            return value
        if isinstance(stmt, ast.CellAssign):
            return self._eval_cell_assign(stmt)
        if isinstance(stmt, ast.ArrayAssign):
            return self._eval_array_assign(stmt)
        if isinstance(stmt, ast.MultiAssign):
            return self._eval_multi_assign(stmt)
        if isinstance(stmt, ast.IfStmt):
            return self._eval_if(stmt)
        if isinstance(stmt, ast.ForStmt):
            return self._eval_for(stmt)
        if isinstance(stmt, ast.WhileStmt):
            return self._eval_while(stmt)
        if isinstance(stmt, ast.BreakStmt):
            raise _BreakSignal()
        if isinstance(stmt, ast.ExprStmt):
            return self.eval_expr(stmt.expr)
        if isinstance(stmt, ast.FunctionDef):
            raise EvalError(
                "function definitions are only valid in .m files on the path"
            )
        raise EvalError(f"Unknown statement: {type(stmt)!r}")

    def eval_expr(self, expr: ast.Expr) -> Value:
        if isinstance(expr, ast.NumberLiteral):
            return self.numerics.from_scalar(expr.value)
        if isinstance(expr, ast.StringLiteral):
            from openmatlab.runtime.char_value import CharValue

            return CharValue(expr.value)
        if isinstance(expr, ast.Name):
            try:
                return self.workspace.get(expr.id)
            except KeyError as exc:
                raise EvalError(f"Undefined variable: {expr.id}") from exc
        if isinstance(expr, ast.UnaryOp):
            v = self._require_array(self.eval_expr(expr.operand), "unary")
            if expr.op == "+":
                return v
            if expr.op == "-":
                z = self.numerics.from_scalar(0.0)
                return self.numerics.sub(z, v)
            raise EvalError(f"Unknown unary op: {expr.op}")
        if isinstance(expr, ast.BinOp):
            return self._eval_binop(expr)
        if isinstance(expr, ast.CellLiteral):
            return self._eval_cell_literal(expr)
        if isinstance(expr, ast.MatrixLiteral):
            return self._eval_matrix(expr)
        if isinstance(expr, ast.ColonExpr):
            return self._eval_colon(expr)
        if isinstance(expr, ast.TransposeExpr):
            return self.numerics.transpose(
                self._require_array(self.eval_expr(expr.operand), "transpose"),
                conjugate=expr.conjugate,
            )
        if isinstance(expr, ast.CellIndexExpr):
            return self._eval_cell_index(expr)
        if isinstance(expr, ast.IndexExpr):
            return self._eval_call_or_index(expr.target, list(expr.indices))
        if isinstance(expr, ast.CallExpr):
            return self._eval_call_or_index(expr.func, list(expr.args))
        raise EvalError(f"Unknown expression: {type(expr)!r}")


    def _eval_cell_literal(self, expr: "ast.CellLiteral") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        if not expr.rows:
            return CellValue(rows=tuple())
        rows = []
        width = None
        for row in expr.rows:
            vals = [self.eval_expr(cell) for cell in row]
            if width is None:
                width = len(vals)
            elif len(vals) != width:
                raise EvalError("Cell literal rows must have equal length")
            rows.append(tuple(vals))
        return CellValue(rows=tuple(rows))



    def _eval_cell_index(self, expr: "ast.CellIndexExpr") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        target = self.eval_expr(expr.target)
        if not isinstance(target, CellValue):
            raise EvalError(
                f"cell index: expected cell, got {type(target).__name__}"
            )
        i0, j0 = self._cell_subscripts(target, list(expr.indices), "cell index")
        return target.get(i0, j0)


    def _eval_array_assign(self, stmt: "ast.ArrayAssign") -> Value:
        target_expr = stmt.target.target
        if not isinstance(target_expr, ast.Name):
            raise EvalError("array assign: LHS must be name(...) in this MVP")
        name = target_expr.id
        try:
            arr = self.workspace.get(name)
        except KeyError as exc:
            raise EvalError(f"Undefined variable: {name}") from exc
        arr_a = self._require_array(arr, "array assign")
        idxs = [
            self._require_array(self.eval_expr(a), "array assign")
            for a in stmt.target.indices
        ]
        rhs = self._require_array(self.eval_expr(stmt.value), "array assign")
        try:
            new_arr = self.numerics.set_index(arr_a, idxs, rhs)
        except Exception as exc:  # NumericsError
            raise EvalError(f"array assign: {exc}") from exc
        self.workspace.set(name, new_arr)
        return rhs

    def _eval_cell_assign(self, stmt: "ast.CellAssign") -> Value:
        from openmatlab.runtime.cell_value import CellValue

        target_expr = stmt.target.target
        if not isinstance(target_expr, ast.Name):
            raise EvalError("cell assign: LHS must be name{...} in this MVP")
        name = target_expr.id
        try:
            cell = self.workspace.get(name)
        except KeyError as exc:
            raise EvalError(f"Undefined variable: {name}") from exc
        if not isinstance(cell, CellValue):
            raise EvalError(
                f"cell assign: expected cell, got {type(cell).__name__}"
            )
        i0, j0 = self._cell_subscripts(
            cell, list(stmt.target.indices), "cell assign"
        )
        value = self.eval_expr(stmt.value)
        self.workspace.set(name, cell.with_set(i0, j0, value))
        return value

    def _cell_subscripts(
        self, cell: "object", idx_exprs: list, label: str
    ) -> tuple:
        """Return 0-based (i, j) for 1-based linear or (i,j) indices."""
        from openmatlab.runtime.cell_value import CellValue

        assert isinstance(cell, CellValue)
        idxs = [self.eval_expr(i) for i in idx_exprs]
        if not idxs:
            raise EvalError(f"{label}: missing indices")
        rows, cols = cell.shape
        if rows == 0 and cols == 0:
            raise EvalError(f"{label}: empty cell")

        def _as_int(v: Value, what: str) -> int:
            arr = self._require_array(v, what)
            if not arr.is_scalar():
                raise EvalError(f"{what}: expected scalar index")
            x = float(arr.backend_buffer().reshape(-1)[0])
            if x != int(x) or x < 1:
                raise EvalError(f"{what}: indices must be positive integers")
            return int(x)

        if len(idxs) == 1:
            k = _as_int(idxs[0], label)
            n = cell.numel()
            if k > n:
                raise EvalError(
                    f"{label}: linear index {k} exceeds numel ({n})"
                )
            return (k - 1) % rows, (k - 1) // rows
        if len(idxs) == 2:
            i = _as_int(idxs[0], label)
            j = _as_int(idxs[1], label)
            if i > rows or j > cols:
                raise EvalError(
                    f"{label}: ({i},{j}) out of bounds for {rows}x{cols} cell"
                )
            return i - 1, j - 1
        raise EvalError(f"{label}: only 1 or 2 subscripts supported")


    def _require_array(self, val: Value, ctx: str) -> Array:
        if not isinstance(val, Array):
            raise EvalError(f"{ctx}: expected Array, got {type(val).__name__}")
        return val

    def _eval_multi_assign(self, stmt: ast.MultiAssign) -> Value:
        nargout = len(stmt.names)
        if nargout < 1:
            raise EvalError("multi-assign: empty output list")
        expr = stmt.value
        if isinstance(expr, ast.IndexExpr):
            target_expr, arg_exprs = expr.target, list(expr.indices)
        elif isinstance(expr, ast.CallExpr):
            target_expr, arg_exprs = expr.func, list(expr.args)
        else:
            raise EvalError("multi-assign RHS must be a function call")
        results = self._invoke_call(target_expr, arg_exprs, nargout=nargout)
        if len(results) < nargout:
            raise EvalError(
                f"multi-assign: expected {nargout} outputs, got {len(results)}"
            )
        for name, val in zip(stmt.names, results):
            self.workspace.set(name, val)
        return results[0]

    def _eval_call_or_index(self, target_expr: ast.Expr, arg_exprs: List[ast.Expr]) -> Value:
        results = self._invoke_call(target_expr, arg_exprs, nargout=1)
        if results is None:
            target = self.eval_expr(target_expr)
            from openmatlab.runtime.cell_value import CellValue

            if isinstance(target, CellValue):
                return self._eval_cell_paren_index(target, arg_exprs)
            target_a = self._require_array(target, "index")
            idxs = [
                self._require_array(self.eval_expr(a), "index") for a in arg_exprs
            ]
            return self.numerics.index(target_a, idxs)
        if not results:
            return self.numerics.from_nested([])
        return results[0]

    def _eval_cell_paren_index(
        self, cell: "object", arg_exprs: List[ast.Expr]
    ) -> Value:
        """c(i) / c(i,j) → 1×1 CellValue holding the content (slice, not content)."""
        from openmatlab.runtime.cell_value import CellValue

        assert isinstance(cell, CellValue)
        i0, j0 = self._cell_subscripts(cell, list(arg_exprs), "cell () index")
        return CellValue(rows=((cell.get(i0, j0),),))

    def _invoke_call(
        self,
        target_expr: ast.Expr,
        arg_exprs: List[ast.Expr],
        *,
        nargout: int,
    ):
        """Return output sequence for a function call, or None if indexing."""
        if not (
            isinstance(target_expr, ast.Name)
            and not self._name_bound(target_expr.id)
        ):
            if nargout != 1:
                raise EvalError("multi-assign RHS must be a function call")
            return None
        n = target_expr.id
        key = n.lower()
        if key == "plot":
            if nargout != 1:
                raise EvalError("plot: only one output supported")
            return (self._builtin_plot(arg_exprs),)
        if key == "addpath":
            if nargout != 1:
                raise EvalError("addpath: only one output supported")
            return (self._builtin_addpath(arg_exprs),)
        if key == "which":
            if nargout != 1:
                raise EvalError("which: only one output supported")
            return (self._builtin_which(arg_exprs),)
        if key in ("show", "drawnow"):
            if nargout != 1:
                raise EvalError(f"{key}: only one output supported")
            return (self._builtin_show(arg_exprs),)
        if key == "run":
            if nargout != 1:
                raise EvalError("run: only one output supported")
            return (self._builtin_run(arg_exprs),)
        try:
            fn = self.functions.resolve(n)
        except LookupError as exc:
            raise EvalError(str(exc)) from exc
        args = [self.eval_expr(a) for a in arg_exprs]
        try:
            results = list(fn(args, nargout=nargout))
        except ValueError as exc:  # builtin argument errors (e.g. BuiltinError)
            msg = str(exc)
            raise EvalError(msg if msg.startswith(f"{n}:") else f"{n}: {msg}") from exc
        for i, out in enumerate(results):
            if not isinstance(out, Value):
                raise EvalError(f"{n}: output {i} is not a Value")
        return results

    def _string_arg(self, expr: ast.Expr, fname: str) -> str:
        from openmatlab.runtime.char_value import CharValue

        val = self.eval_expr(expr)
        if isinstance(val, CharValue):
            return val.text
        raise EvalError(f"{fname}: expected char/string argument")

    def _name_bound(self, name: str) -> bool:
        try:
            self.workspace.get(name)
            return True
        except KeyError:
            return False

    def _builtin_plot(self, arg_exprs: List[ast.Expr]) -> Array:
        if self.plots is None:
            raise EvalError("plot: no PlotSurface on this Session")
        args = [
            self._require_array(self.eval_expr(a), "plot") for a in arg_exprs
        ]
        handle = self.plots.plot(*args)
        try:
            return self.numerics.from_scalar(float(handle))
        except (TypeError, ValueError):
            return self.numerics.from_scalar(1.0)

    def _builtin_addpath(self, arg_exprs: List[ast.Expr]) -> Value:
        from openmatlab.runtime.char_value import CharValue

        if not arg_exprs:
            raise EvalError("addpath: expected at least one directory")
        if self.functions.path is None:
            raise EvalError("addpath: no ToolboxPath on FunctionResolver")
        last = ""
        for a in arg_exprs:
            last = self._string_arg(a, "addpath")
            self.functions.path.addpath(last)
        return CharValue(last)

    def _builtin_which(self, arg_exprs: List[ast.Expr]) -> Value:
        from openmatlab.runtime.char_value import CharValue

        if len(arg_exprs) != 1:
            raise EvalError("which: expected one name string")
        name = self._string_arg(arg_exprs[0], "which")
        return CharValue(self.functions.which(name))

    def _builtin_show(self, arg_exprs: List[ast.Expr]) -> Array:
        if arg_exprs:
            raise EvalError("show/drawnow: expected no arguments")
        if self.plots is None:
            raise EvalError("show: no PlotSurface on this Session")
        show = getattr(self.plots, "show", None)
        if callable(show):
            show()
        return self.numerics.from_scalar(1.0)

    def _builtin_run(self, arg_exprs: List[ast.Expr]) -> Array:
        from pathlib import Path

        from openmatlab.lang.ast_nodes import FunctionDef
        from openmatlab.runtime.functions import Script, eval_script, load_mfile

        if len(arg_exprs) != 1:
            raise EvalError("run: expected one string path")
        name = self._string_arg(arg_exprs[0], "run")
        path = Path(name).expanduser()
        if not path.is_file():
            # try ToolboxPath by stem / name
            hit = None
            if self.functions.path is not None:
                hit = self.functions.path.find_mfile(name)
            if hit is None:
                raise EvalError(f"run: file not found: {name}")
            path = hit
        try:
            loaded = load_mfile(path)
        except ValueError as exc:
            raise EvalError(str(exc)) from exc
        if isinstance(loaded, FunctionDef):
            raise EvalError(
                f"run: {path} is a function file; call it as a function instead"
            )
        assert isinstance(loaded, Script)
        eval_script(loaded, self)
        return self.numerics.from_scalar(1.0)

    def _eval_binop(self, expr: ast.BinOp) -> Array:
        left = self._require_array(self.eval_expr(expr.left), "binop")
        right = self._require_array(self.eval_expr(expr.right), "binop")
        op = expr.op
        n = self.numerics
        if op == "+":
            return n.add(left, right)
        if op == "-":
            return n.sub(left, right)
        if op == "*":
            return n.matmul(left, right)
        if op == "/":
            return n.elem_div(left, right)
        if op == ".*":
            return n.elem_mul(left, right)
        if op == "./":
            return n.elem_div(left, right)
        if op == ".^":
            return n.power(left, right, elementwise=True)
        if op == "^":
            return n.power(left, right, elementwise=False)
        if op in ("<", "<=", ">", ">=", "==", "~="):
            return self._eval_relational(op, left, right)
        raise EvalError(f"Unknown binary op: {op}")

    def _eval_matrix(self, expr: ast.MatrixLiteral) -> Array:
        if not expr.rows:
            return self.numerics.from_nested([])
        rows_f: List[List[float]] = []
        for row in expr.rows:
            out_row: List[float] = []
            for cell in row:
                val = self._require_array(self.eval_expr(cell), "matrix")
                if not val.is_scalar():
                    raise EvalError(
                        "Matrix literal cells must be scalar in this MVP"
                    )
                out_row.append(float(val.backend_buffer().reshape(-1)[0]))
            rows_f.append(out_row)
        return self.numerics.from_nested(rows_f)

    def _eval_colon(self, expr: ast.ColonExpr) -> Array:
        if expr.start is None or expr.stop is None:
            raise EvalError("Colon requires start and stop")
        start = self._as_float(
            self._require_array(self.eval_expr(expr.start), "colon")
        )
        stop = self._as_float(
            self._require_array(self.eval_expr(expr.stop), "colon")
        )
        step = 1.0
        if expr.step is not None:
            step = self._as_float(
                self._require_array(self.eval_expr(expr.step), "colon")
            )
        return self.numerics.colon(start, stop, step)

    def _as_float(self, val: Array) -> float:
        if not val.is_scalar():
            raise EvalError("Expected scalar")
        return float(val.backend_buffer().reshape(-1)[0])

    def _eval_relational(self, op: str, left: Array, right: Array) -> Array:
        import numpy as np

        a = np.asarray(left.backend_buffer(), dtype=float)
        b = np.asarray(right.backend_buffer(), dtype=float)
        if op == "<":
            r = a < b
        elif op == "<=":
            r = a <= b
        elif op == ">":
            r = a > b
        elif op == ">=":
            r = a >= b
        elif op == "==":
            r = a == b
        elif op == "~=":
            r = a != b
        else:
            raise EvalError(f"Unknown relational op: {op}")
        r = np.asarray(r, dtype=float)
        if r.shape == ():
            return self.numerics.from_scalar(float(r))
        if r.ndim == 1:
            return self.numerics.from_nested([list(map(float, r.tolist()))])
        return self.numerics.from_nested(
            [list(map(float, row)) for row in r.tolist()]
        )

    def _truthy(self, val: Value) -> bool:
        arr = self._require_array(val, "condition")
        if arr.numel() == 0:
            return False
        import numpy as np

        buf = np.asarray(arr.backend_buffer(), dtype=float).reshape(-1)
        return bool(np.all(buf != 0))

    def _eval_if(self, stmt: ast.IfStmt) -> Value:
        last: Value = self.numerics.from_scalar(0.0)
        for branch in stmt.branches:
            if self._truthy(self.eval_expr(branch.condition)):
                for s in branch.body:
                    last = self.eval_stmt(s)
                return last
        if stmt.else_body is not None:
            for s in stmt.else_body:
                last = self.eval_stmt(s)
        return last

    def _eval_for(self, stmt: ast.ForStmt) -> Value:
        iterable = self._require_array(self.eval_expr(stmt.iterable), "for")
        import numpy as np

        vals = np.asarray(iterable.backend_buffer(), dtype=float).reshape(-1)
        last: Value = self.numerics.from_scalar(0.0)
        for x in vals:
            self.workspace.set(stmt.var, self.numerics.from_scalar(float(x)))
            try:
                for s in stmt.body:
                    last = self.eval_stmt(s)
            except _BreakSignal:
                break
        return last

    def _eval_while(self, stmt: ast.WhileStmt) -> Value:
        last: Value = self.numerics.from_scalar(0.0)
        # Cap iterations to avoid hard hangs from user error in MVP
        for _ in range(1_000_000):
            if not self._truthy(self.eval_expr(stmt.condition)):
                return last
            try:
                for s in stmt.body:
                    last = self.eval_stmt(s)
            except _BreakSignal:
                return last
        raise EvalError("while: exceeded 1000000 iterations")

