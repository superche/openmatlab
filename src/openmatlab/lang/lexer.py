"""Lexer stub — matrix grammar reserved in TokenType; tokenize not wired."""

from __future__ import annotations

from typing import List

from openmatlab.lang.tokens import TokenType


class LexerError(Exception):
    pass


def tokenize(source: str) -> List[object]:
    """Return a token list. Architecture stage: not implemented."""
    raise NotImplementedError(
        "lang.lexer.tokenize: reserved TokenType includes matrix forms "
        f"(e.g. {TokenType.LBRACKET.name}, {TokenType.DOT_STAR.name}, "
        f"{TokenType.COLON.name}); implementation deferred"
    )
