"""AST node types for the OpenMATLAB subset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Number:
    value: float


@dataclass(frozen=True)
class Name:
    id: str


@dataclass(frozen=True)
class BinOp:
    op: str  # +, -, *, /
    left: Expr
    right: Expr


@dataclass(frozen=True)
class UnaryOp:
    op: str  # +, -
    operand: Expr


@dataclass(frozen=True)
class Assign:
    name: str
    value: Expr


@dataclass(frozen=True)
class ExprStmt:
    expr: Expr


Expr = Union[Number, Name, BinOp, UnaryOp]
Stmt = Union[Assign, ExprStmt]
