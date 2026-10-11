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
        if isinstance(stmt, ast.MultiAssign):
            return self._eval_multi_assign(stmt)
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
        if isinstance(expr, ast.MatrixLiteral):
            return self._eval_matrix(expr)
        if isinstance(expr, ast.ColonExpr):
            return self._eval_colon(expr)
        if isinstance(expr, ast.TransposeExpr):
            return self.numerics.transpose(
                self._require_array(self.eval_expr(expr.operand), "transpose"),
                conjugate=expr.conjugate,
            )
        if isinstance(expr, ast.IndexExpr):
            return self._eval_call_or_index(expr.target, list(expr.indices))
        if isinstance(expr, ast.CallExpr):
            return self._eval_call_or_index(expr.func, list(expr.args))
        raise EvalError(f"Unknown expression: {type(expr)!r}")

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
            # indexed array path
            target = self._require_array(self.eval_expr(target_expr), "index")
            idxs = [
                self._require_array(self.eval_expr(a), "index") for a in arg_exprs
            ]
            return self.numerics.index(target, idxs)
        if not results:
            return self.numerics.from_nested([])
        return results[0]

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
        try:
            fn = self.functions.resolve(n)
        except LookupError as exc:
            raise EvalError(str(exc)) from exc
        args = [self.eval_expr(a) for a in arg_exprs]
        results = list(fn(args, nargout=nargout))
        for i, out in enumerate(results):
            if not isinstance(out, Array):
                raise EvalError(f"{n}: output {i} is not an Array")
        return results

    def _string_arg(self, expr: ast.Expr, fname: str) -> str:
        from openmatlab.runtime.char_value import CharValue

        val = self.eval_expr(expr)
        if isinstance(val, CharValue):
            return val.text
        raise EvalError(f"{fname}: expected string literal (double quotes)")

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
