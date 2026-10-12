"""Token vocabulary — scalar subset + reserved matrix / MATLAB-like forms.

Reserved names document grammar the lexer/parser MUST grow into for a
matrix-first workbench. Implementations may still be stubs.
"""

from __future__ import annotations

from enum import Enum, auto


class TokenType(Enum):
    # --- implemented / planned soon ---
    NUMBER = auto()
    STRING = auto()  # double-quoted "..." (MVP)
    CHAR = auto()  # single-quoted '...' (context-sensitive vs transpose)
    IDENT = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()  # matrix multiply (*) in MATLAB-like public semantics
    SLASH = auto()  # matrix right-divide (/) — semantics TBD with arrays
    LPAREN = auto()
    RPAREN = auto()
    ASSIGN = auto()
    SEMICOLON = auto()  # statement sep OR suppress-display OR row sep in [...] 
    NEWLINE = auto()
    EOF = auto()

    # --- reserved: matrix-first language (not yet lexed) ---
    DOT_STAR = auto()  # .*
    DOT_SLASH = auto()  # ./
    DOT_BACKSLASH = auto()  # .\
    DOT_HAT = auto()  # .^
    BACKSLASH = auto()  # \
    HAT = auto()  # ^
    TRANSPOSE = auto()  # '  (array transpose — context-sensitive)
    CTC_TRANSPOSE = auto()  # .'
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    LBRACE = auto()  # {  (cell — later)
    RBRACE = auto()  # }
    COMMA = auto()
    COLON = auto()  # 1:n , indexing ranges
    AT = auto()  # @ function handle
    TILDE = auto()  # ~ (unary not)
    AMP = auto()  # &
    PIPE = auto()  # |
    AND_AND = auto()  # &&
    OR_OR = auto()  # ||
    REL_LT = auto()
    REL_LE = auto()
    REL_GT = auto()
    REL_GE = auto()
    REL_EQ = auto()
    REL_NE = auto()
    # keywords (scanner may emit IDENT today; reserved for keyword table)
    KW_FUNCTION = auto()
    KW_IF = auto()
    KW_ELSE = auto()
    KW_ELSEIF = auto()
    KW_END = auto()
    KW_FOR = auto()
    KW_WHILE = auto()
    KW_BREAK = auto()
    KW_CONTINUE = auto()
    KW_RETURN = auto()
    KW_SWITCH = auto()
    KW_CASE = auto()
    KW_OTHERWISE = auto()
