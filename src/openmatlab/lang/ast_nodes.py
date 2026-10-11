"""AST node shapes — current stubs + reserved matrix-first forms.

Concrete evaluation is out of scope at the architecture stage. Node types
exist so parser, runtime, and display can agree on seams.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Union


class AstNode:
    """Marker base for all AST nodes."""


# ----- expression forms (minimal + reserved) -----


@dataclass(frozen=True)
class NumberLiteral(AstNode):
    value: float  # parse-time literal; runtime promotes to Array 1x1


@dataclass(frozen=True)
class Name(AstNode):
    id: str


@dataclass(frozen=True)
class BinOp(AstNode):
    op: str
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class UnaryOp(AstNode):
    op: str
    operand: "Expr"


@dataclass(frozen=True)
class MatrixLiteral(AstNode):
    """Reserved: [ row ; row ] — rows are sequences of expressions."""

    rows: Sequence[Sequence["Expr"]]


@dataclass(frozen=True)
class IndexExpr(AstNode):
    """Reserved: target(i, j, ...)"""

    target: "Expr"
    indices: Sequence["Expr"]


@dataclass(frozen=True)
class ColonExpr(AstNode):
    """Reserved: start:stop or start:step:stop (None = default)."""

    start: Optional["Expr"]
    stop: Optional["Expr"]
    step: Optional["Expr"] = None


@dataclass(frozen=True)
class TransposeExpr(AstNode):
    """Reserved: A' or A.'"""

    operand: "Expr"
    conjugate: bool = True


@dataclass(frozen=True)
class CallExpr(AstNode):
    """Reserved: f(args) — also overlaps indexing until name resolution."""

    func: "Expr"
    args: Sequence["Expr"]


Expr = Union[
    NumberLiteral,
    Name,
    BinOp,
    UnaryOp,
    MatrixLiteral,
    IndexExpr,
    ColonExpr,
    TransposeExpr,
    CallExpr,
]


# ----- statements -----


@dataclass(frozen=True)
class Assign(AstNode):
    name: str
    value: Expr
    suppress: bool = False  # True if statement ended with ';'


@dataclass(frozen=True)
class ExprStmt(AstNode):
    expr: Expr
    suppress: bool = False


@dataclass(frozen=True)
class FunctionDef(AstNode):
    """Reserved: function [outs] = name(ins) ... end"""

    name: str
    outputs: Sequence[str]
    inputs: Sequence[str]
    body: Sequence["Stmt"]


Stmt = Union[Assign, ExprStmt, FunctionDef]
Program = List[Stmt]
