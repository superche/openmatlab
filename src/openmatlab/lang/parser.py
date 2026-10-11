"""Parser stub — produces Program AST; matrix productions reserved on AstNode."""

from __future__ import annotations

from openmatlab.lang.ast_nodes import Program


class ParseError(Exception):
    pass


def parse(source: str) -> Program:
    """Parse source into a statement list. Architecture stage: not implemented."""
    raise NotImplementedError(
        "lang.parser.parse: will emit MatrixLiteral, IndexExpr, ColonExpr, "
        "TransposeExpr, Assign(suppress=...), FunctionDef; deferred"
    )
