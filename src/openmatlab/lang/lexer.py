"""Lexer for matrix-first OpenMATLAB subset (public-spec / clean-room)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List

from openmatlab.lang.tokens import TokenType


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
    return list(_iter_tokens(source))


def _iter_tokens(source: str) -> Iterator[Token]:
    i = 0
    line = 1
    col = 1
    n = len(source)
    bracket_depth = 0

    def peek(offset: int = 0) -> str:
        j = i + offset
        return source[j] if j < n else ""

    while i < n:
        ch = source[i]

        if ch in " \t\r":
            i += 1
            col += 1
            continue

        if ch == "\n":
            if bracket_depth > 0:
                yield Token(TokenType.SEMICOLON, ";", line, col)
            else:
                yield Token(TokenType.NEWLINE, "\n", line, col)
            i += 1
            line += 1
            col = 1
            continue

        if ch == "%":
            while i < n and source[i] != "\n":
                i += 1
                col += 1
            continue

        start_line, start_col = line, col

        # Double-quoted string MVP ("..."); single quote stays transpose
        if ch == '"':
            i += 1
            col += 1
            chars: List[str] = []
            while i < n and source[i] != '"':
                if source[i] == "\\":
                    i += 1
                    col += 1
                    if i >= n:
                        raise LexerError(
                            "Unterminated string escape", start_line, start_col
                        )
                    esc = source[i]
                    if esc == "n":
                        chars.append("\n")
                    elif esc == "t":
                        chars.append("\t")
                    elif esc == '"':
                        chars.append('"')
                    elif esc == "\\":
                        chars.append("\\")
                    else:
                        chars.append(esc)
                    i += 1
                    col += 1
                    continue
                if source[i] == "\n":
                    raise LexerError("Unterminated string", start_line, start_col)
                chars.append(source[i])
                i += 1
                col += 1
            if i >= n or source[i] != '"':
                raise LexerError("Unterminated string", start_line, start_col)
            i += 1
            col += 1
            yield Token(TokenType.STRING, "".join(chars), start_line, start_col)
            continue

        # Dot-operators: .* ./ .\ .^ .'
        if ch == "." and peek(1) in "*/\\^'":
            nxt = peek(1)
            mapping = {
                "*": TokenType.DOT_STAR,
                "/": TokenType.DOT_SLASH,
                "\\": TokenType.DOT_BACKSLASH,
                "^": TokenType.DOT_HAT,
                "'": TokenType.CTC_TRANSPOSE,
            }
            yield Token(mapping[nxt], "." + nxt, start_line, start_col)
            i += 2
            col += 2
            continue

        # Number: digit… or .digit…
        if ch.isdigit() or (ch == "." and peek(1).isdigit()):
            start = i
            if ch == ".":
                i += 1
                col += 1
            while i < n and source[i].isdigit():
                i += 1
                col += 1
            if i < n and source[i] == "." and (i + 1 >= n or source[i + 1] != "."):
                # fractional part (not ..)
                if i + 1 < n and source[i + 1].isdigit():
                    i += 1
                    col += 1
                    while i < n and source[i].isdigit():
                        i += 1
                        col += 1
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

        if ch.isalpha() or ch == "_":
            start = i
            i += 1
            col += 1
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
                col += 1
            word = source[start:i]
            keywords = {
                "function": TokenType.KW_FUNCTION,
                "end": TokenType.KW_END,
                "if": TokenType.KW_IF,
                "else": TokenType.KW_ELSE,
                "elseif": TokenType.KW_ELSEIF,
                "for": TokenType.KW_FOR,
            }
            typ = keywords.get(word.lower(), TokenType.IDENT)
            yield Token(typ, word, start_line, start_col)
            continue

        # Relational / multi-char before '=' / '<' / '>' / '~'
        two = ch + peek(1)
        two_map = {
            "==": TokenType.REL_EQ,
            "~=": TokenType.REL_NE,
            "<=": TokenType.REL_LE,
            ">=": TokenType.REL_GE,
        }
        if two in two_map:
            yield Token(two_map[two], two, start_line, start_col)
            i += 2
            col += 2
            continue
        if ch == "<":
            yield Token(TokenType.REL_LT, ch, start_line, start_col)
            i += 1
            col += 1
            continue
        if ch == ">":
            yield Token(TokenType.REL_GT, ch, start_line, start_col)
            i += 1
            col += 1
            continue

        singles = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "^": TokenType.HAT,
            "\\": TokenType.BACKSLASH,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "=": TokenType.ASSIGN,
            ";": TokenType.SEMICOLON,
            ",": TokenType.COMMA,
            ":": TokenType.COLON,
            "'": TokenType.TRANSPOSE,
        }
        if ch in singles:
            typ = singles[ch]
            if ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth = max(0, bracket_depth - 1)
            yield Token(typ, ch, start_line, start_col)
            i += 1
            col += 1
            continue

        raise LexerError(f"Unexpected character {ch!r}", start_line, start_col)

    yield Token(TokenType.EOF, "", line, col)
