"""AST evaluator — Array-first on Session numerics backend."""

from __future__ import annotations

from typing import List, Optional, Sequence

from openmatlab.lang import ast_nodes as ast
from openmatlab.lang.parser import parse
from openmatlab.numerics.backend import ArrayBackend
from openmatlab.runtime.functions import FunctionResolver
from openmatlab.runtime.value import Array, Value
from openmatlab.runtime.workspace import Workspace


class EvalError(Exception):
    pass


class Evaluator:
    """Walk AST against Workspace + ArrayBackend."""

    def __init__(
        self,
        workspace: Optional[Workspace] = None,
        functions: Optional[FunctionResolver] = None,
        numerics: Optional[ArrayBackend] = None,
    ) -> None:
        self.workspace = workspace if workspace is not None else Workspace()
        self.functions = functions if functions is not None else FunctionResolver()
        if numerics is None:
            raise EvalError("Evaluator requires an ArrayBackend (Session.numerics)")
        self.numerics = numerics

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
        if isinstance(stmt, ast.ExprStmt):
            return self.eval_expr(stmt.expr)
        raise EvalError(f"Unknown statement: {type(stmt)!r}")

    def eval_expr(self, expr: ast.Expr) -> Array:
        if isinstance(expr, ast.NumberLiteral):
            return self.numerics.from_scalar(expr.value)
        if isinstance(expr, ast.Name):
            try:
                val = self.workspace.get(expr.id)
            except KeyError as exc:
                raise EvalError(f"Undefined variable: {expr.id}") from exc
            if not isinstance(val, Array):
                raise EvalError(f"Variable {expr.id!r} is not an Array")
            return val
        if isinstance(expr, ast.UnaryOp):
            v = self.eval_expr(expr.operand)
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
                self.eval_expr(expr.operand), conjugate=expr.conjugate
            )
        if isinstance(expr, ast.IndexExpr):
            target = self.eval_expr(expr.target)
            idxs = [self.eval_expr(i) for i in expr.indices]
            return self.numerics.index(target, idxs)
        if isinstance(expr, ast.CallExpr):
            # Same surface as indexing for now
            target = self.eval_expr(expr.func)
            idxs = [self.eval_expr(a) for a in expr.args]
            return self.numerics.index(target, idxs)
        raise EvalError(f"Unknown expression: {type(expr)!r}")

    def _eval_binop(self, expr: ast.BinOp) -> Array:
        left = self.eval_expr(expr.left)
        right = self.eval_expr(expr.right)
        op = expr.op
        n = self.numerics
        if op == "+":
            return n.add(left, right)
        if op == "-":
            return n.sub(left, right)
        if op == "*":
            return n.matmul(left, right)
        if op == "/":
            # matrix right-divide approx: element-wise for MVP scalars/arrays
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
                val = self.eval_expr(cell)
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
        start = self._as_float(self.eval_expr(expr.start))
        stop = self._as_float(self.eval_expr(expr.stop))
        step = 1.0
        if expr.step is not None:
            step = self._as_float(self.eval_expr(expr.step))
        return self.numerics.colon(start, stop, step)

    def _as_float(self, val: Array) -> float:
        if not val.is_scalar():
            raise EvalError("Expected scalar")
        return float(val.backend_buffer().reshape(-1)[0])
