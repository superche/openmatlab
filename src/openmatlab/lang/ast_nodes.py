"""AST node shapes — current stubs + reserved matrix-first forms.

Concrete evaluation is out of scope at the architecture stage. Node types
exist so parser, runtime, and display can agree on seams.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union


class AstNode:
    """Marker base for all AST nodes."""


# ----- expression forms (minimal + reserved) -----


@dataclass(frozen=True)
class NumberLiteral(AstNode):
    value: float  # parse-time literal; runtime promotes to Array 1x1


@dataclass(frozen=True)
class StringLiteral(AstNode):
    value: str  # double-quoted MVP string


@dataclass(frozen=True)
class Name(AstNode):
    id: str


@dataclass(frozen=True)
class EndExpr(AstNode):
    """end — last index in a subscript context."""

    pass


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
class CellLiteral(AstNode):
    rows: Tuple[Tuple["Expr", ...], ...]


@dataclass(frozen=True)
class MatrixLiteral(AstNode):
    """Reserved: [ row ; row ] — rows are sequences of expressions."""

    rows: Sequence[Sequence["Expr"]]


@dataclass(frozen=True)
class CellIndexExpr(AstNode):
    """Content indexing: target{i} or target{i,j}."""

    target: "Expr"
    indices: Sequence["Expr"]


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
    StringLiteral,
    Name,
    EndExpr,
    BinOp,
    UnaryOp,
    MatrixLiteral,
    CellLiteral,
    IndexExpr,
    CellIndexExpr,
    ColonExpr,
    TransposeExpr,
    CallExpr,
]


# ----- statements -----


@dataclass(frozen=True)
class ArrayAssign(AstNode):
    """A(i) = expr — indexed assignment into an Array."""

    target: IndexExpr
    value: Expr
    suppress: bool = False


@dataclass(frozen=True)
class CellAssign(AstNode):
    """c{i} = expr — content assignment into a cell."""

    target: CellIndexExpr
    value: Expr
    suppress: bool = False


@dataclass(frozen=True)
class Assign(AstNode):
    name: str
    value: Expr
    suppress: bool = False  # True if statement ended with ';'


@dataclass(frozen=True)
class MultiAssign(AstNode):
    """[a, b] = f(...) — multiple outputs from a call."""

    names: Sequence[str]
    value: Expr
    suppress: bool = False


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


@dataclass(frozen=True)
class IfBranch(AstNode):
    """One if/elseif branch: condition + body."""

    condition: Expr
    body: Sequence["Stmt"]


@dataclass(frozen=True)
class IfStmt(AstNode):
    branches: Sequence[IfBranch]  # if + elseif
    else_body: Optional[Sequence["Stmt"]] = None


@dataclass(frozen=True)
class ForStmt(AstNode):
    var: str
    iterable: Expr
    body: Sequence["Stmt"]


@dataclass(frozen=True)
class WhileStmt(AstNode):
    condition: Expr
    body: Sequence["Stmt"]


@dataclass(frozen=True)
class BreakStmt(AstNode):
    """break — exits innermost while/for."""

    pass


@dataclass(frozen=True)
class ContinueStmt(AstNode):
    """continue — next iteration of innermost while/for."""

    pass


@dataclass(frozen=True)
class ReturnStmt(AstNode):
    """return — exit current function or script early."""

    pass


@dataclass(frozen=True)
class SwitchCase(AstNode):
    """One case arm: one or more match values + body."""

    values: Sequence["Expr"]
    body: Sequence["Stmt"]


@dataclass(frozen=True)
class SwitchStmt(AstNode):
    """switch expr … case … otherwise … end (no fall-through)."""

    expr: "Expr"
    cases: Sequence[SwitchCase]
    otherwise: Optional[Sequence["Stmt"]] = None


Stmt = Union[
    Assign,
    CellAssign,
    ArrayAssign,
    MultiAssign,
    ExprStmt,
    FunctionDef,
    IfStmt,
    ForStmt,
    WhileStmt,
    BreakStmt,
    ContinueStmt,
    ReturnStmt,
    SwitchStmt,
]
Program = List[Stmt]
