"""Lexer for a minimal MATLAB-like expression/statement subset.

Based on publicly documented MATLAB-like syntax ideas (identifiers, numbers,
arithmetic operators, parentheses, assignment, statement separators).
Clean-room: no proprietary binary analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, List


class TokenType(Enum):
    NUMBER = auto()
    IDENT = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    LPAREN = auto()
    RPAREN = auto()
    ASSIGN = auto()
    SEMICOLON = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


def tokenize(source: str) -> List[Token]:
    """Tokenize source into a list of tokens, ending with EOF."""
    return list(_iter_tokens(source))


def _iter_tokens(source: str) -> Iterator[Token]:
    i = 0
    line = 1
    col = 1
    n = len(source)

    def peek(offset: int = 0) -> str:
        j = i + offset
        return source[j] if j < n else ""

    while i < n:
        ch = source[i]

        # Whitespace (space, tab) — skip
        if ch in " \t\r":
            i += 1
            col += 1
            continue

        # Newline
        if ch == "\n":
            yield Token(TokenType.NEWLINE, "\n", line, col)
            i += 1
            line += 1
            col = 1
            continue

        # Line comment: % ... end of line (MATLAB-style public syntax)
        if ch == "%":
            while i < n and source[i] != "\n":
                i += 1
                col += 1
            continue

        start_line, start_col = line, col

        # Number: digit sequence with optional fractional part
        if ch.isdigit() or (ch == "." and peek(1).isdigit()):
            start = i
            if ch == ".":
                i += 1
                col += 1
            while i < n and source[i].isdigit():
                i += 1
                col += 1
            if i < n and source[i] == ".":
                i += 1
                col += 1
                while i < n and source[i].isdigit():
                    i += 1
                    col += 1
            # Optional scientific exponent: e/E [+-]? digits
            if i < n and source[i] in "eE":
                i += 1
                col += 1
                if i < n and source[i] in "+-":
                    i += 1
                    col += 1
                if i >= n or not source[i].isdigit():
                    raise LexerError("Invalid number exponent", start_line, start_col)
                while i < n and source[i].isdigit():
                    i += 1
                    col += 1
            yield Token(TokenType.NUMBER, source[start:i], start_line, start_col)
            continue

        # Identifier: letter/_ then letter/digit/_
        if ch.isalpha() or ch == "_":
            start = i
            i += 1
            col += 1
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
                col += 1
            yield Token(TokenType.IDENT, source[start:i], start_line, start_col)
            continue

        single = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "=": TokenType.ASSIGN,
            ";": TokenType.SEMICOLON,
        }
        if ch in single:
            yield Token(single[ch], ch, start_line, start_col)
            i += 1
            col += 1
            continue

        raise LexerError(f"Unexpected character {ch!r}", start_line, start_col)

    yield Token(TokenType.EOF, "", line, col)
