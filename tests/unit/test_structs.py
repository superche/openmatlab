"""Structs (Epic #506): fields, dynamic names, struct arrays, field functions, cs-lists, display."""

import numpy as np
import pytest

from openmatlab.host.display import _format_value
from openmatlab.host.repl import ReplSession
from openmatlab.lang.parser import parse
from openmatlab.lang import ast_nodes as ast
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_parser_field_forms():
    st = parse("s.a.b(2) = 1")[0]
    assert isinstance(st, ast.ChainAssign)
    e = parse("x = s.(n)")[0].value
    assert isinstance(e, ast.FieldExpr) and e.name is None
    # decimals and dot operators are unaffected
    assert parse("q = [a .5]")[0].value.rows[0][1].value == 0.5
    assert isinstance(parse("y = a.'")[0].value, ast.TransposeExpr)
    assert parse("z = b.^2")[0].value.op == ".^"


def test_field_create_read_nested_dynamic():
    ws = _ws("s.a = 1; s.b = 'hi'; s.n.m.k = 3; f = 'dyn'; s.(f) = 7; a = s.a; k = s.n.m.k; d = s.dyn;"
             " g = s.('a'); c = class(s);")
    assert _v(ws, "a").item() == 1 and _v(ws, "k").item() == 3 and _v(ws, "d").item() == 7
    assert _v(ws, "g").item() == 1 and ws.get("c").text == "struct"
    assert ws.get("s").fields == ("a", "b", "n", "dyn")


def test_mixed_chains():
    ws = _ws("s.v = [1 2]; s.v(end+1) = 9; s.c{3} = 'x'; c = {}; c{2}.x = 4; q = c{2}.x; x = []; x.y = 1;"
             " w = s.v; n = numel(s.c);")
    assert _v(ws, "w").tolist() == [[1, 2, 9]] and _v(ws, "n").item() == 3
    assert _v(ws, "q").item() == 4 and ws.get("x").fields == ("y",)


def test_struct_arrays_grow_delete_concat():
    ws = _ws("s(3).a = 5; z = size(s); e = isempty(s(1).a); s(2).b = 'k'; f = fieldnames(s);"
             " t = s([1 3]); s(1) = []; m = size(s); u = [t t]; r = size(u'); s(end+1) = s(1); p = numel(s);")
    assert _v(ws, "z").tolist() == [[1, 3]] and _v(ws, "e").item()
    assert [x.text for x in ws.get("f").rows[0]] + [x.text for x in ws.get("f").rows[1]] == ["a", "b"]
    assert _v(ws, "m").tolist() == [[1, 2]] and _v(ws, "r").tolist() == [[4, 1]] and _v(ws, "p").item() == 3
    assert ws.get("t").shape == (1, 2)


def test_struct_function_builds_arrays():
    ws = _ws("s = struct('a', {1, 2, 3}, 'b', 'same'); n = size(s); b = s(3).b; c = struct('x', {{1, 2}});"
             " k = class(c.x); e = struct('a', {}); en = size(e); z = struct(); nf = numel(fieldnames(z));")
    assert _v(ws, "n").tolist() == [[1, 3]] and ws.get("b").text == "same"
    assert ws.get("k").text == "cell" and _v(ws, "en").tolist() == [[0, 0]] and _v(ws, "nf").item() == 0
    with pytest.raises(EvalError, match="dimensions"):
        _ws("s = struct('a', {1, 2}, 'b', {1, 2, 3});")


def test_cs_lists():
    ws = _ws("s = struct('a', {4, 5, 6}); v = [s.a]; c = {s.a}; m = max([s(1:2).a]); first = s.a;"
             " mx = max(s(1:2).a);")
    assert _v(ws, "v").tolist() == [[4, 5, 6]] and ws.get("c").shape == (1, 3)
    assert _v(ws, "m").item() == 5 and _v(ws, "first").item() == 4 and _v(ws, "mx").item() == 5


def test_cs_list_statement_shows_each_ans():
    import subprocess
    import sys

    out = subprocess.run([sys.executable, "-m", "openmatlab", "-e", "s = struct('a', {1, 2}); s.a"],
                         capture_output=True, text=True, check=True).stdout
    assert out.count("ans =") == 2 and "1" in out and "2" in out


def test_field_functions():
    ws = _ws("s = struct('b', 1, 'a', 2); i = isfield(s, 'a'); j = isfield(s, {'a', 'zz'}); r = rmfield(s, 'a');"
             " t = setfield(s, 'c', 'd', 5); g = getfield(t, 'c', 'd'); is = isstruct(s); no = isstruct(1);"
             " [o, p] = orderfields(s); q = orderfields(s, {'b', 'a'}); w = orderfields(s, [2 1]);"
             " e = isequal(s, struct('a', 2, 'b', 1));")
    assert _v(ws, "i").item() and _v(ws, "j").tolist() == [[True, False]]
    assert ws.get("r").fields == ("b",) and _v(ws, "g").item() == 5
    assert _v(ws, "is").item() and not _v(ws, "no").item()
    assert ws.get("o").fields == ("a", "b") and _v(ws, "p").ravel().tolist() == [2, 1]
    assert ws.get("q").fields == ("b", "a") and ws.get("w").fields == ("a", "b")
    assert _v(ws, "e").item()
    with pytest.raises(EvalError, match="doesn't exist"):
        _ws("r = rmfield(struct('a', 1), 'b');")


def test_for_loop_over_struct_array():
    ws = _ws("s = struct('a', {1, 2, 3}); t = 0; for e = s, t = t + e.a; end")
    assert _v(ws, "t").item() == 6


def test_errors():
    cases = {
        "s.a = 1; x = s.b;": 'Unrecognized field name "b"',
        "x = 5; y = x.a;": "Dot indexing is not supported",
        "x = 5; x.a = 1;": "dot indexing is not supported",
        "s = struct('a', {1, 2}); s.a = 3;": "Scalar structure required",
        "s.('1bad') = 1;": "Invalid field name",
        "s = struct('a', 1); s(2) = struct('b', 1);": "dissimilar structures",
        "s.a = 1; t = [s 1];": "non-struct",
    }
    for code, msg in cases.items():
        with pytest.raises(EvalError, match=msg):
            _ws(code)


def test_display():
    ws = _ws("s.a = 1; s.bcd = 'hi'; s.v = [1 2 3]; s.m = ones(2); s.c = {1, 2}; s.n.x = 1; s.e = [];"
             " s.t = \"str\"; t = struct('a', {1, 2}); e = struct('a', {}); z = struct();")
    assert _format_value(ws.get("s")) == "\n".join([
        "  struct with fields:", "",
        "      a: 1", "    bcd: 'hi'", "      v: [1 2 3]", "      m: [2\u00d72 double]",
        "      c: {1\u00d72 cell}", "      n: [1\u00d71 struct]", "      e: []", '      t: "str"',
    ])
    assert _format_value(ws.get("t")) == "  1\u00d72 struct array with fields:\n\n    a"
    assert _format_value(ws.get("e")) == "  0\u00d70 empty struct array with fields:\n\n    a"
    assert _format_value(ws.get("z")) == "  struct with no fields."


def test_regexp_names_struct():  # #504
    ws = _ws("t = regexp('ab12', '(?<w>[a-z]+)(?<d>\\d+)', 'names'); w = t.w;"
             " u = regexp('a1 b2', '(?<l>[a-z])(?<n>\\d)', 'names'); n = size(u); n2 = u(2).n;"
             " x = regexp('xyz', '(?<n>\\d)', 'names'); xs = size(x);")
    assert ws.get("w").text == "ab" and _v(ws, "n").tolist() == [[1, 2]] and ws.get("n2").text == "2"
    assert _v(ws, "xs").tolist() == [[0, 0]]


def test_empty_linear_growth_is_row():
    ws = _ws("x = []; x(3) = 1; n = size(x);")
    assert _v(ws, "n").tolist() == [[1, 3]]
