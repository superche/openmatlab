"""Recursive-descent parser for a minimal MATLAB-like subset.

Grammar (public-spec / clean-room):

  program     := { statement }
  statement   := assignment | expression  [ ';' ]
  assignment  := IDENT '=' expression
  expression  := term { ('+' | '-') term }
  term        := factor { ('*' | '/') factor }
  factor      := ('+' | '-') factor | primary
  primary     := NUMBER | IDENT | '(' expression ')'

Statements are separated by newlines and/or semicolons.
"""

from __future__ import annotations

from typing import List, Optional

from openmatlab.ast_nodes import Assign, BinOp, Expr, ExprStmt, Name, Number, Stmt, UnaryOp
from openmatlab.lexer import Token, TokenType, tokenize


class ParseError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        loc = f" at line {line}, column {column}" if line else ""
        super().__init__(f"{message}{loc}")
        self.line = line
        self.column = column


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

    def skip_separators(self) -> None:
        while self.match(TokenType.NEWLINE, TokenType.SEMICOLON):
            pass

    def parse(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        self.skip_separators()
        while self.current().type != TokenType.EOF:
            stmts.append(self.parse_statement())
            # Optional trailing separators
            saw = False
            while self.match(TokenType.NEWLINE, TokenType.SEMICOLON):
                saw = True
            if not saw and self.current().type != TokenType.EOF:
                tok = self.current()
                raise ParseError(
                    "Expected newline or ';' between statements",
                    tok.line,
                    tok.column,
                )
        return stmts

    def parse_statement(self) -> Stmt:
        # Lookahead: IDENT '=' → assignment
        if (
            self.current().type == TokenType.IDENT
            and self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].type == TokenType.ASSIGN
        ):
            name = self.advance().value
            self.expect(TokenType.ASSIGN)
            value = self.parse_expression()
            return Assign(name=name, value=value)
        return ExprStmt(expr=self.parse_expression())

    def parse_expression(self) -> Expr:
        left = self.parse_term()
        while True:
            op = self.match(TokenType.PLUS, TokenType.MINUS)
            if not op:
                break
            right = self.parse_term()
            left = BinOp(op=op.value, left=left, right=right)
        return left

    def parse_term(self) -> Expr:
        left = self.parse_factor()
        while True:
            op = self.match(TokenType.STAR, TokenType.SLASH)
            if not op:
                break
            right = self.parse_factor()
            left = BinOp(op=op.value, left=left, right=right)
        return left

    def parse_factor(self) -> Expr:
        op = self.match(TokenType.PLUS, TokenType.MINUS)
        if op:
            return UnaryOp(op=op.value, operand=self.parse_factor())
        return self.parse_primary()

    def parse_primary(self) -> Expr:
        tok = self.current()
        if tok.type == TokenType.NUMBER:
            self.advance()
            return Number(value=float(tok.value))
        if tok.type == TokenType.IDENT:
            self.advance()
            return Name(id=tok.value)
        if tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        raise ParseError(
            f"Unexpected token {tok.type.name}",
            tok.line,
            tok.column,
        )


def parse(source: str) -> List[Stmt]:
    """Parse source text into a list of statements."""
    return Parser(tokenize(source)).parse()
