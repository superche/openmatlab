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
    return _split_signed_matrix_elements(source, list(_iter_tokens(source)))


_VALUE_END = {
    TokenType.NUMBER,
    TokenType.IDENT,
    TokenType.STRING,
    TokenType.CHAR,
    TokenType.RPAREN,
    TokenType.RBRACKET,
    TokenType.RBRACE,
    TokenType.TRANSPOSE,
    TokenType.CTC_TRANSPOSE,
    TokenType.KW_END,
}


def _split_signed_matrix_elements(source: str, toks: List[Token]) -> List[Token]:
    """Inside [ ] (not nested in parens), `a -b` starts a new element.

    MATLAB rule: a +/- with whitespace before and none after, following a
    value, separates matrix elements. Implemented by inserting a COMMA.
    """
    line_starts = [0]
    for idx, ch in enumerate(source):
        if ch == "\n":
            line_starts.append(idx + 1)

    def offset(tok: Token) -> int:
        return line_starts[tok.line - 1] + tok.column - 1

    out: List[Token] = []
    stack: List[TokenType] = []
    for tok in toks:
        if (
            tok.type in (TokenType.LPAREN, TokenType.LBRACE)
            and stack
            and stack[-1] in (TokenType.LBRACKET, TokenType.LBRACE)
            and out
            and out[-1].type in _VALUE_END
            and source[offset(tok) - 1 : offset(tok)] in (" ", "\t")
        ):
            # `[c {2}]` / `[a (1)]`: whitespace before ( or { starts a new element
            out.append(Token(TokenType.COMMA, ",", tok.line, tok.column))
        if tok.type in (TokenType.LBRACKET, TokenType.LPAREN, TokenType.LBRACE):
            stack.append(tok.type)
        elif tok.type in (TokenType.RBRACKET, TokenType.RPAREN, TokenType.RBRACE) and stack:
            stack.pop()
        elif (
            tok.type in (TokenType.PLUS, TokenType.MINUS)
            and stack
            and stack[-1] in (TokenType.LBRACKET, TokenType.LBRACE)
            and out
            and out[-1].type in _VALUE_END
        ):
            off = offset(tok)
            before = source[off - 1] if off > 0 else ""
            after = source[off + 1] if off + 1 < len(source) else ""
            if before in " \t" and after not in " \t":
                out.append(Token(TokenType.COMMA, ",", tok.line, tok.column))
        elif (
            tok.type == TokenType.TILDE
            and stack
            and stack[-1] in (TokenType.LBRACKET, TokenType.LBRACE)
            and out
            and out[-1].type in _VALUE_END
        ):
            # `[a ~b]`: unary not after a value always starts a new element
            out.append(Token(TokenType.COMMA, ",", tok.line, tok.column))
        out.append(tok)
    return out


def _iter_tokens(source: str) -> Iterator[Token]:
    i = 0
    line = 1
    col = 1
    n = len(source)
    bracket_depth = 0
    brace_depth = 0
    last_sig: TokenType | None = None

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
            if bracket_depth > 0 or brace_depth > 0:
                tok = Token(TokenType.SEMICOLON, ";", line, col)
            else:
                tok = Token(TokenType.NEWLINE, "\n", line, col)
            yield tok
            # NEWLINE / row-sep does not update last_sig (transpose can follow across NL)
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
            # MATLAB: no backslash escapes in "..."; a doubled "" is one quote (#483)
            while i < n and (source[i] != '"' or source[i + 1:i + 2] == '"'):
                if source[i] == '"':
                    chars.append('"')
                    i += 2
                    col += 2
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
            tok = Token(TokenType.STRING, "".join(chars), start_line, start_col)
            yield tok
            last_sig = tok.type
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
            tok = Token(mapping[nxt], "." + nxt, start_line, start_col)
            yield tok
            last_sig = tok.type
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
            # imaginary literal suffix 3i / 2.5j / 4I (#71); not 3if / 2jx
            if (
                i < n and source[i] in "ijIJ"
                and (i + 1 >= n or not (source[i + 1].isalnum() or source[i + 1] == "_"))
            ):
                i += 1
                col += 1
            tok = Token(TokenType.NUMBER, source[start:i], start_line, start_col)
            yield tok
            last_sig = tok.type
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
                "while": TokenType.KW_WHILE,
                "break": TokenType.KW_BREAK,
                "continue": TokenType.KW_CONTINUE,
                "return": TokenType.KW_RETURN,
                "switch": TokenType.KW_SWITCH,
                "case": TokenType.KW_CASE,
                "otherwise": TokenType.KW_OTHERWISE,
            }
            typ = keywords.get(word.lower(), TokenType.IDENT)
            tok = Token(typ, word, start_line, start_col)
            yield tok
            last_sig = tok.type
            continue

        # Relational / multi-char before '=' / '<' / '>' / '~'
        two = ch + peek(1)
        two_map = {
            "==": TokenType.REL_EQ,
            "~=": TokenType.REL_NE,
            "<=": TokenType.REL_LE,
            ">=": TokenType.REL_GE,
            "&&": TokenType.AND_AND,
            "||": TokenType.OR_OR,
        }
        if two in two_map:
            tok = Token(two_map[two], two, start_line, start_col)
            yield tok
            last_sig = tok.type
            i += 2
            col += 2
            continue
        one_map = {"&": TokenType.AMP, "|": TokenType.PIPE, "~": TokenType.TILDE}
        if ch in one_map:
            tok = Token(one_map[ch], ch, start_line, start_col)
            yield tok
            last_sig = tok.type
            i += 1
            col += 1
            continue
        if ch == "<":
            tok = Token(TokenType.REL_LT, ch, start_line, start_col)
            yield tok
            last_sig = tok.type
            i += 1
            col += 1
            continue
        if ch == ">":
            tok = Token(TokenType.REL_GT, ch, start_line, start_col)
            yield tok
            last_sig = tok.type
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
            "@": TokenType.AT,
        }
        # Context-sensitive single quote: transpose vs char literal
        if ch == "'":
            # inside [ ] / { }, whitespace before ' starts a char literal: ['ab' 'cd']
            spaced_elem = (bracket_depth > 0 or brace_depth > 0) and i > 0 and source[i - 1] in " \t"
            if last_sig is not None and last_sig in _VALUE_END and not spaced_elem:
                tok = Token(TokenType.TRANSPOSE, "'", start_line, start_col)
                yield tok
                last_sig = tok.type
                i += 1
                col += 1
                continue
            # Char literal '…' with '' escape
            i += 1
            col += 1
            chars: List[str] = []
            while i < n:
                if source[i] == "'":
                    if i + 1 < n and source[i + 1] == "'":
                        chars.append("'")
                        i += 2
                        col += 2
                        continue
                    i += 1
                    col += 1
                    tok = Token(TokenType.CHAR, "".join(chars), start_line, start_col)
                    yield tok
                    last_sig = tok.type
                    break
                if source[i] == chr(10):
                    raise LexerError("Unterminated char literal", start_line, start_col)
                chars.append(source[i])
                i += 1
                col += 1
            else:
                raise LexerError("Unterminated char literal", start_line, start_col)
            continue
        if ch in singles:
            typ = singles[ch]
            if ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth = max(0, bracket_depth - 1)
            elif ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth = max(0, brace_depth - 1)
            tok = Token(typ, ch, start_line, start_col)
            yield tok
            last_sig = tok.type
            i += 1
            col += 1
            continue

        raise LexerError(f"Unexpected character {ch!r}", start_line, start_col)

    yield Token(TokenType.EOF, "", line, col)
