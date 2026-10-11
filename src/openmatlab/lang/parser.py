"""Recursive-descent parser — matrix-first subset (no evaluator)."""

from __future__ import annotations

from typing import List, Optional, Sequence

from openmatlab.lang.ast_nodes import (
    Assign,
    BinOp,
    ColonExpr,
    Expr,
    ExprStmt,
    FunctionDef,
    IndexExpr,
    MultiAssign,
    MatrixLiteral,
    Name,
    NumberLiteral,
    Program,
    StringLiteral,
    Stmt,
    TransposeExpr,
    UnaryOp,
)
from openmatlab.lang.lexer import Token, TokenType, tokenize


class ParseError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        loc = f" at line {line}, column {column}" if line else ""
        super().__init__(f"{message}{loc}")
        self.line = line
        self.column = column


# New matrix row element via juxtaposition (not binary +/- which bind inside expr)
_JUXTAPOSE_START = frozenset(
    {
        TokenType.NUMBER,
        TokenType.IDENT,
        TokenType.LPAREN,
        TokenType.LBRACKET,
    }
)


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.current()
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def match(self, *types: TokenType) -> Optional[Token]:
        if self.current().type in types:
            return self.advance()
        return None

    def expect(self, typ: TokenType) -> Token:
        tok = self.current()
        if tok.type != typ:
            raise ParseError(
                f"Expected {typ.name}, got {tok.type.name}",
                tok.line,
                tok.column,
            )
        return self.advance()

    def skip_newlines(self) -> None:
        while self.match(TokenType.NEWLINE):
            pass

    def parse(self) -> Program:
        stmts: List[Stmt] = []
        self.skip_newlines()
        while self.current().type != TokenType.EOF:
            stmts.append(self.parse_statement())
            # optional separators; suppress already applied from trailing ';'
            while self.match(TokenType.NEWLINE, TokenType.SEMICOLON):
                pass
        return stmts

    def parse_statement(self) -> Stmt:
        if self.current().type == TokenType.KW_FUNCTION:
            return self.parse_function_def()
        if (
            self.current().type == TokenType.IDENT
            and self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].type == TokenType.ASSIGN
        ):
            name = self.advance().value
            self.expect(TokenType.ASSIGN)
            value = self.parse_expression()
            suppress = self._trailing_suppress()
            return Assign(name=name, value=value, suppress=suppress)
        multi = self._try_parse_multi_assign()
        if multi is not None:
            return multi
        expr = self.parse_expression()
        suppress = self._trailing_suppress()
        return ExprStmt(expr=expr, suppress=suppress)

    def _try_parse_multi_assign(self) -> Optional[MultiAssign]:
        """Parse [a, b] = expr; rewind if not that pattern (matrix / other)."""
        if self.current().type != TokenType.LBRACKET:
            return None
        saved = self.pos
        self.advance()  # [
        if self.current().type != TokenType.IDENT:
            self.pos = saved
            return None
        try:
            names = self._parse_name_list()
            if self.current().type != TokenType.RBRACKET:
                self.pos = saved
                return None
            self.advance()
            if self.match(TokenType.ASSIGN) is None:
                self.pos = saved
                return None
        except ParseError:
            self.pos = saved
            return None
        value = self.parse_expression()
        suppress = self._trailing_suppress()
        return MultiAssign(names=tuple(names), value=value, suppress=suppress)

    def parse_function_def(self) -> FunctionDef:
        self.expect(TokenType.KW_FUNCTION)
        outputs: List[str] = []
        # function name(args)
        # function out = name(args)
        # function [a,b] = name(args)
        if self.match(TokenType.LBRACKET):
            outputs = self._parse_name_list()
            self.expect(TokenType.RBRACKET)
            self.expect(TokenType.ASSIGN)
            name = self.expect(TokenType.IDENT).value
        elif self.current().type == TokenType.IDENT:
            first = self.advance().value
            if self.match(TokenType.ASSIGN):
                outputs = [first]
                name = self.expect(TokenType.IDENT).value
            else:
                name = first
        else:
            tok = self.current()
            raise ParseError("Expected function name", tok.line, tok.column)
        self.expect(TokenType.LPAREN)
        inputs: List[str] = []
        if self.current().type != TokenType.RPAREN:
            inputs = self._parse_name_list()
        self.expect(TokenType.RPAREN)
        while self.match(TokenType.NEWLINE, TokenType.SEMICOLON):
            pass
        body: List[Stmt] = []
        while self.current().type not in (TokenType.KW_END, TokenType.EOF):
            body.append(self.parse_statement())
            while self.match(TokenType.NEWLINE, TokenType.SEMICOLON):
                pass
        if self.current().type != TokenType.KW_END:
            tok = self.current()
            raise ParseError("Expected end to close function", tok.line, tok.column)
        self.advance()  # KW_END
        return FunctionDef(
            name=name,
            outputs=tuple(outputs),
            inputs=tuple(inputs),
            body=tuple(body),
        )

    def _parse_name_list(self) -> List[str]:
        names: List[str] = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.COMMA):
            names.append(self.expect(TokenType.IDENT).value)
        return names

    def _trailing_suppress(self) -> bool:
        """True if statement ends with ';' before newline/EOF (not inside matrix)."""
        return self.match(TokenType.SEMICOLON) is not None

    def parse_expression(self) -> Expr:
        return self.parse_colon()

    def parse_colon(self) -> Expr:
        first = self.parse_add()
        if not self.match(TokenType.COLON):
            return first
        second = self.parse_add()
        if self.match(TokenType.COLON):
            third = self.parse_add()
            return ColonExpr(start=first, step=second, stop=third)
        return ColonExpr(start=first, stop=second, step=None)

    def parse_add(self) -> Expr:
        left = self.parse_mul()
        while True:
            op = self.match(TokenType.PLUS, TokenType.MINUS)
            if not op:
                break
            right = self.parse_mul()
            left = BinOp(op=op.value, left=left, right=right)
        return left

    def parse_mul(self) -> Expr:
        left = self.parse_unary()
        while True:
            op = self.match(
                TokenType.STAR,
                TokenType.SLASH,
                TokenType.DOT_STAR,
                TokenType.DOT_SLASH,
                TokenType.BACKSLASH,
                TokenType.DOT_BACKSLASH,
            )
            if not op:
                break
            right = self.parse_unary()
            left = BinOp(op=op.value, left=left, right=right)
        return left

    def parse_unary(self) -> Expr:
        op = self.match(TokenType.PLUS, TokenType.MINUS)
        if op:
            return UnaryOp(op=op.value, operand=self.parse_unary())
        return self.parse_power()

    def parse_power(self) -> Expr:
        # right-associative ^ .^
        base = self.parse_postfix()
        op = self.match(TokenType.HAT, TokenType.DOT_HAT)
        if not op:
            return base
        exp = self.parse_unary()
        return BinOp(op=op.value, left=base, right=exp)

    def parse_postfix(self) -> Expr:
        expr = self.parse_primary()
        while True:
            if self.match(TokenType.TRANSPOSE):
                expr = TransposeExpr(operand=expr, conjugate=True)
                continue
            if self.match(TokenType.CTC_TRANSPOSE):
                expr = TransposeExpr(operand=expr, conjugate=False)
                continue
            if self.match(TokenType.LPAREN):
                args = self._parse_arg_list(TokenType.RPAREN)
                self.expect(TokenType.RPAREN)
                expr = IndexExpr(target=expr, indices=args)
                continue
            break
        return expr

    def parse_primary(self) -> Expr:
        tok = self.current()
        if tok.type == TokenType.NUMBER:
            self.advance()
            return NumberLiteral(value=float(tok.value))
        if tok.type == TokenType.STRING:
            self.advance()
            return StringLiteral(value=tok.value)
        if tok.type == TokenType.IDENT:
            self.advance()
            return Name(id=tok.value)
        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        if tok.type == TokenType.LBRACKET:
            return self.parse_matrix()
        raise ParseError(
            f"Unexpected token {tok.type.name}",
            tok.line,
            tok.column,
        )

    def parse_matrix(self) -> MatrixLiteral:
        self.expect(TokenType.LBRACKET)
        rows: List[Sequence[Expr]] = []
        # empty []
        if self.match(TokenType.RBRACKET):
            return MatrixLiteral(rows=())
        while True:
            while self.match(TokenType.SEMICOLON):
                pass
            if self.current().type == TokenType.RBRACKET:
                break
            row = self._parse_matrix_row()
            rows.append(tuple(row))
            if self.match(TokenType.SEMICOLON):
                continue
            if self.current().type == TokenType.RBRACKET:
                break
            tok = self.current()
            raise ParseError(
                "Expected ';' or ']' in matrix",
                tok.line,
                tok.column,
            )
        self.expect(TokenType.RBRACKET)
        return MatrixLiteral(rows=tuple(rows))

    def _parse_matrix_row(self) -> List[Expr]:
        elems: List[Expr] = []
        elems.append(self.parse_expression())
        while True:
            if self.match(TokenType.COMMA):
                elems.append(self.parse_expression())
                continue
            # whitespace juxtaposition: next primary starts a new element
            if self.current().type in _JUXTAPOSE_START:
                elems.append(self.parse_expression())
                continue
            break
        return elems

    def _parse_arg_list(self, closer: TokenType) -> List[Expr]:
        args: List[Expr] = []
        if self.current().type == closer:
            return args
        args.append(self.parse_expression())
        while self.match(TokenType.COMMA):
            args.append(self.parse_expression())
        return args


def parse(source: str) -> Program:
    return Parser(tokenize(source)).parse()
