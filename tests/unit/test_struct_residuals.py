"""#508: disp, isrow/iscolumn/isvector/isscalar/ismatrix, deal and cs-list multi-assign,
struct2cell/cell2struct, structfun/arrayfun, N-D struct arrays, field summaries, undefined-name growth."""

import subprocess
import sys

import numpy as np
import pytest

from openmatlab.host.display import _format_value
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def _out(code):
    return subprocess.run([sys.executable, "-m", "openmatlab", "-e", code],
                          capture_output=True, text=True, check=True).stdout


def test_disp():
    assert _out("disp('hi')") == "hi\n"
    assert _out('disp("s")') == "s\n"
    assert _out("disp([])") == ""
    assert _out("s.a = 1; s.b = 'x'; disp(s)") == "    a: 1\n    b: 'x'\n"
    assert _out("disp([1 2; 3 4])") == "   1   2\n   3   4\n"
    assert "ans" not in _out("disp(5)")


def test_shape_predicates():
    ws = _ws("a = [isrow([1 2]) iscolumn([1; 2]) isvector(5) isscalar(7) ismatrix(ones(2,2,2))"
             " isvector(zeros(1, 0)) isrow('abc') isscalar(struct('a', {1, 2}))];")
    assert _v(ws, "a").tolist() == [[True, True, True, True, False, False, True, False]]


def test_deal_and_cs_list_multi_assign():
    ws = _ws("[a, b] = deal(1, 2); [c, d] = deal(7); s = struct('f', {1, 2}); [x, y] = s.f;"
             " k = {4, 5}; [p, q] = k{:}; [s.f] = deal(8, 9); v = [s.f]; [s.f] = deal(0); w = [s.f];"
             " z = cell(1, 2); [z{:}] = deal(3); zz = [z{:}]; [t.x, m(2)] = deal(1, 2);")
    assert [_v(ws, n).item() for n in "abcdxypq"] == [1, 2, 7, 7, 1, 2, 4, 5]
    assert _v(ws, "v").tolist() == [[8, 9]] and _v(ws, "w").tolist() == [[0, 0]]
    assert _v(ws, "zz").tolist() == [[3, 3]] and _v(ws, "m").tolist() == [[0, 2]]
    assert ws.get("t").fields == ("x",)
    with pytest.raises(EvalError, match="number of outputs"):
        _ws("[a, b, c] = deal(1, 2);")


def test_struct2cell_cell2struct():
    ws = _ws("c = struct2cell(struct('a', 1, 'b', 'x')); n = size(c); d = size(struct2cell(struct('a', {1, 2, 3})));"
             " s = cell2struct({1; 'x'}, {'a', 'b'}, 1); t = cell2struct({1, 'x'; 2, 'y'}, {'n', 's'}, 2); tn = size(t);")
    assert _v(ws, "n").tolist() == [[2, 1]] and _v(ws, "d").tolist() == [[1, 1, 3]]
    assert ws.get("s").fields == ("a", "b") and ws.get("s").get("b").text == "x"
    assert _v(ws, "tn").tolist() == [[2, 1]] and ws.get("t").get("s", 1).text == "y"
    with pytest.raises(EvalError, match="Number of field names"):
        _ws("s = cell2struct({1, 2}, {'a'}, 2);")


def test_structfun_arrayfun():
    ws = _ws("v = structfun(@(x) x * 2, struct('a', 1, 'b', 3)); u = structfun(@(x) [x x], struct('a', 1), 'UniformOutput', false);"
             " q = arrayfun(@(x) x^2, [1 2; 3 4]); c = arrayfun(@(x) 1:x, [1 2], 'UniformOutput', false);"
             " s = struct('a', {1, 2}); e = arrayfun(@(t) t.a * 10, s); [m, i] = arrayfun(@max, [1 5]);"
             " p = arrayfun(@(x, y) x + y, [1 2], [10 20]); l = arrayfun(@(x) x > 1, [1 2]);")
    assert _v(ws, "v").tolist() == [[2], [6]] and _v(ws, "q").tolist() == [[1, 4], [9, 16]]
    assert np.asarray(ws.get("u").get("a").backend_buffer()).tolist() == [[1, 1]]
    assert ws.get("c").shape == (1, 2) and _v(ws, "e").tolist() == [[10, 20]]
    assert _v(ws, "m").tolist() == [[1, 5]] and _v(ws, "p").tolist() == [[11, 22]]
    assert _v(ws, "l").dtype == bool
    with pytest.raises(EvalError, match="UniformOutput"):
        _ws("x = arrayfun(@(x) [x x], [1 2]);")


def test_nd_struct_arrays():
    ws = _ws("s(2, 2, 2).a = 1; n = size(s); k = numel(s); t = struct('a', {1, 2}); t(1, 1, 2) = t(1); m = size(t);"
             " v = s(2, 2, 2).a;")
    assert _v(ws, "n").tolist() == [[2, 2, 2]] and _v(ws, "k").item() == 8
    assert _v(ws, "m").tolist() == [[1, 2, 2]] and _v(ws, "v").item() == 1
    assert _format_value(ws.get("s")).startswith("  2\u00d72\u00d72 struct array with fields:")
    with pytest.raises(EvalError, match="Transpose on ND"):
        _ws("s(1, 1, 2).a = 1; t = s';")


def test_field_row_summary_short_per_element():
    ws = _ws("s.w = [1.5 2]; s.i = int8([1 2]); s.b = [123456.5 1];")
    out = _format_value(ws.get("s"))
    assert "w: [1.5000 2]" in out and "i: [1 2]" in out and "b: [1.2346e+05 1]" in out


def test_indexed_assignment_creates_variable():
    ws = _ws("z(3) = 1; w{2} = 1; u(2) = {1}; v(2) = \"x\"; t(2) = struct('a', 1);")
    assert _v(ws, "z").tolist() == [[0, 0, 1]] and ws.get("w").shape == (1, 2)
    assert ws.get("u").matlab_class() == "cell" and ws.get("v").data.tolist() == [[None, "x"]]
    assert ws.get("t").shape == (1, 2)
