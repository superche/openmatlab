"""classdef file parser (M8 Object system).

A class file is a structured container of ordinary MATLAB code. The parser keeps
that structure (header, properties/methods/events/enumeration blocks, each with
attributes) and reuses the statement/function parser for method bodies and the
expression parser for property defaults and enumeration arguments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from openmatlab.lang.ast_nodes import Expr, FunctionDef
from openmatlab.lang.lexer import tokenize
from openmatlab.lang.parser import ParseError, Parser
from openmatlab.lang.tokens import TokenType

BLOCKS = ("properties", "methods", "events", "enumeration")


@dataclass
class PropDecl:
    name: str
    default: Optional[Expr]
    attrs: Dict[str, object]


@dataclass
class MethodDecl:
    defn: FunctionDef
    attrs: Dict[str, object]


@dataclass
class EnumDecl:
    name: str
    args: Tuple[Expr, ...]


@dataclass
class ClassDefNode:
    name: str
    supers: Tuple[str, ...]
    attrs: Dict[str, object]
    props: List[PropDecl] = field(default_factory=list)
    methods: List[MethodDecl] = field(default_factory=list)
    events: List[Tuple[str, Dict[str, object]]] = field(default_factory=list)
    enums: List[EnumDecl] = field(default_factory=list)


def is_classdef_source(text: str) -> bool:
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        return s.split()[0].split("(")[0] == "classdef"
    return False


def _parse_attr_text(text: str) -> Dict[str, object]:
    """'Access = private, Constant, ~Hidden' -> {'access': 'private', 'constant': True, 'hidden': False}."""
    out: Dict[str, object] = {}
    depth, cur, parts = 0, "", []
    for ch in text:
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if "=" in p:
            k, v = p.split("=", 1)
            v = v.strip().strip("'\"")
            out[k.strip().lower()] = {"true": True, "false": False}.get(v.lower(), v)
        elif p.startswith("~"):
            out[p[1:].strip().lower()] = False
        else:
            out[p.lower()] = True
    return out


class ClassParser(Parser):
    def __init__(self, source: str) -> None:
        super().__init__(tokenize(source, commands=True))
        self.source = source

    # -- helpers ---------------------------------------------------------------
    def _raw_until(self, closer: TokenType) -> str:
        """Collect token text inside a balanced (...) attribute list; current is after '('."""
        depth, out = 0, []
        while True:
            t = self.current()
            if t.type == TokenType.EOF:
                raise ParseError("Unterminated attribute list", t.line, t.column)
            if t.type == closer and depth == 0:
                self.advance()
                return " ".join(out)
            if t.type in (TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET):
                depth += 1
            elif t.type in (TokenType.RPAREN, TokenType.RBRACE, TokenType.RBRACKET):
                depth -= 1
            v = t.value
            if t.type == TokenType.CHAR:
                v = "'" + v + "'"
            elif t.type == TokenType.QUESTION:
                v = "?"
            out.append(str(v))
            self.advance()

    def _attrs(self) -> Dict[str, object]:
        if self.current().type == TokenType.LPAREN:
            self.advance()
            return _parse_attr_text(self._raw_until(TokenType.RPAREN).replace(" = ", "=").replace("? ", "?"))
        return {}

    def _skip_line(self) -> None:
        while self.current().type not in (TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.EOF):
            self.advance()

    def _seps(self) -> None:
        while self.current().type in (TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.COMMA):
            self.advance()

    def _block_kw(self) -> Optional[str]:
        t = self.current()
        if t.type == TokenType.IDENT and t.value in BLOCKS:
            return t.value
        if t.type == TokenType.COMMAND:
            word = json.loads(t.value)[0]
            if word in BLOCKS:
                return word
        return None

    # -- top level -------------------------------------------------------------
    def parse_class(self) -> ClassDefNode:
        self.skip_newlines()
        t = self.current()
        if t.type == TokenType.COMMAND:
            raw = json.loads(t.value)[2]
            self.advance()
            node = self._header(raw[len("classdef"):])
        elif t.type == TokenType.IDENT and t.value == "classdef":
            # classdef (Attr) Name < Super: collect the raw line
            start = self.pos
            self.advance()
            pieces = []
            while self.current().type not in (TokenType.NEWLINE, TokenType.EOF):
                tok = self.advance()
                pieces.append("?" if tok.type == TokenType.QUESTION else str(tok.value))
            node = self._header(" ".join(pieces))
            del start
        else:
            raise ParseError("Expected classdef", t.line, t.column)
        self._seps()
        while True:
            self._seps()
            t = self.current()
            if t.type == TokenType.KW_END:
                self.advance()
                break
            if t.type == TokenType.EOF:
                raise ParseError("Expected end to close classdef", t.line, t.column)
            kw = self._block_kw()
            if kw is None:
                raise ParseError(f"Unexpected {t.value!r} in classdef {node.name}", t.line, t.column)
            if t.type == TokenType.COMMAND:  # e.g. "methods" parsed as a command line (no attrs)
                raw = json.loads(t.value)[2]
                self.advance()
                attrs = _parse_attr_text(raw[len(kw):].strip().strip("()"))
            else:
                self.advance()
                attrs = self._attrs()
            getattr(self, "_block_" + kw)(node, attrs)
        self._seps()
        # local functions after the classdef end are allowed (MATLAB)
        while self.current().type == TokenType.KW_FUNCTION:
            node.methods.append(MethodDecl(self.parse_function_def(), {"_local": True}))
            self._seps()
        if self.current().type != TokenType.EOF:
            t = self.current()
            raise ParseError("Unexpected content after classdef end", t.line, t.column)
        return node

    def _header(self, raw: str) -> ClassDefNode:
        raw = raw.strip()
        attrs: Dict[str, object] = {}
        if raw.startswith("("):
            depth = 0
            for i, ch in enumerate(raw):
                depth += ch == "("
                depth -= ch == ")"
                if depth == 0:
                    attrs = _parse_attr_text(raw[1:i])
                    raw = raw[i + 1:].strip()
                    break
        name, _, sup = raw.partition("<")
        supers = tuple(s.strip().replace(" ", "") for s in sup.split("&") if s.strip())
        return ClassDefNode(name=name.strip(), supers=supers, attrs=attrs)

    # -- blocks ------------------------------------------------------------------
    def _block_properties(self, node: ClassDefNode, attrs) -> None:
        while True:
            self._seps()
            t = self.current()
            if t.type == TokenType.KW_END:
                self.advance()
                return
            if t.type == TokenType.COMMAND:  # "x double" style line
                word, _args, raw = json.loads(t.value)
                self.advance()
                default = None
                if "=" in raw:
                    default = Parser(tokenize(raw.split("=", 1)[1], commands=False)).parse_expression()
                node.props.append(PropDecl(word, default, dict(attrs)))
                continue
            if t.type != TokenType.IDENT:
                raise ParseError("Expected a property name", t.line, t.column)
            name = self.advance().value
            default = None
            depth = 0
            while True:
                c = self.current()
                if depth == 0 and c.type == TokenType.ASSIGN:
                    self.advance()
                    default = self.parse_expression()
                    break
                if depth == 0 and c.type in (TokenType.NEWLINE, TokenType.SEMICOLON, TokenType.COMMA,
                                             TokenType.KW_END, TokenType.EOF):
                    break
                if c.type in (TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET):
                    depth += 1
                elif c.type in (TokenType.RPAREN, TokenType.RBRACE, TokenType.RBRACKET):
                    depth -= 1
                self.advance()  # size / class / validator spec: accepted, not enforced
            node.props.append(PropDecl(name, default, dict(attrs)))

    def _block_methods(self, node: ClassDefNode, attrs) -> None:
        while True:
            self._seps()
            t = self.current()
            if t.type == TokenType.KW_END:
                self.advance()
                return
            if t.type == TokenType.KW_FUNCTION:
                node.methods.append(MethodDecl(self.parse_function_def(), dict(attrs)))
                continue
            if t.type == TokenType.EOF:
                raise ParseError("Expected end to close methods", t.line, t.column)
            self._skip_line()  # signature only (abstract or defined in a separate file)

    def _block_events(self, node: ClassDefNode, attrs) -> None:
        while True:
            self._seps()
            t = self.current()
            if t.type == TokenType.KW_END:
                self.advance()
                return
            if t.type != TokenType.IDENT:
                raise ParseError("Expected an event name", t.line, t.column)
            node.events.append((self.advance().value, dict(attrs)))

    def _block_enumeration(self, node: ClassDefNode, attrs) -> None:
        while True:
            self._seps()
            t = self.current()
            if t.type == TokenType.KW_END:
                self.advance()
                return
            if t.type == TokenType.COMMAND:
                word, args, raw = json.loads(t.value)
                self.advance()
                rest = raw[len(word):].strip()
                exprs: Tuple[Expr, ...] = ()
                if rest.startswith("("):
                    p = Parser(tokenize(word + rest, commands=False)).parse_expression()
                    exprs = tuple(getattr(p, "indices", getattr(p, "args", ())))
                node.enums.append(EnumDecl(word, exprs))
                continue
            if t.type != TokenType.IDENT:
                raise ParseError("Expected an enumeration member", t.line, t.column)
            name = self.advance().value
            exprs = ()
            if self.current().type == TokenType.LPAREN:
                self.advance()
                exprs = tuple(self._parse_arg_list(TokenType.RPAREN))
                self.expect(TokenType.RPAREN)
            node.enums.append(EnumDecl(name, exprs))


def parse_classdef(source: str) -> ClassDefNode:
    return ClassParser(source).parse_class()
