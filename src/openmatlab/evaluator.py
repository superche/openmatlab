"""Simple AST evaluator with a variable environment (scalars first)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from openmatlab.ast_nodes import Assign, BinOp, Expr, ExprStmt, Name, Number, Stmt, UnaryOp


class EvalError(Exception):
    pass


Env = Dict[str, float]


class Evaluator:
    def __init__(self, env: Optional[Env] = None) -> None:
        self.env: Env = {} if env is None else env

    def eval_program(self, stmts: List[Stmt]) -> Optional[float]:
        """Evaluate statements; return the last non-assignment expression value."""
        last: Optional[float] = None
        for stmt in stmts:
            result = self.eval_stmt(stmt)
            if isinstance(stmt, ExprStmt):
                last = result
            elif isinstance(stmt, Assign):
                last = result
        return last

    def eval_stmt(self, stmt: Stmt) -> float:
        if isinstance(stmt, Assign):
            value = self.eval_expr(stmt.value)
            self.env[stmt.name] = value
            return value
        if isinstance(stmt, ExprStmt):
            return self.eval_expr(stmt.expr)
        raise EvalError(f"Unknown statement type: {type(stmt)!r}")

    def eval_expr(self, expr: Expr) -> float:
        if isinstance(expr, Number):
            return expr.value
        if isinstance(expr, Name):
            if expr.id not in self.env:
                raise EvalError(f"Undefined variable: {expr.id}")
            return self.env[expr.id]
        if isinstance(expr, UnaryOp):
            v = self.eval_expr(expr.operand)
            if expr.op == "+":
                return +v
            if expr.op == "-":
                return -v
            raise EvalError(f"Unknown unary operator: {expr.op}")
        if isinstance(expr, BinOp):
            left = self.eval_expr(expr.left)
            right = self.eval_expr(expr.right)
            if expr.op == "+":
                return left + right
            if expr.op == "-":
                return left - right
            if expr.op == "*":
                return left * right
            if expr.op == "/":
                if right == 0:
                    raise EvalError("Division by zero")
                return left / right
            raise EvalError(f"Unknown binary operator: {expr.op}")
        raise EvalError(f"Unknown expression type: {type(expr)!r}")


def run(source: str, env: Optional[Env] = None) -> tuple[Optional[float], Env]:
    """Parse and evaluate source; return (last_value, environment)."""
    from openmatlab.parser import parse

    evaluator = Evaluator(env)
    stmts = parse(source)
    result = evaluator.eval_program(stmts)
    return result, evaluator.env


def format_number(value: float) -> str:
    """Format a float in a MATLAB-ish friendly way for display."""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return repr(value)
