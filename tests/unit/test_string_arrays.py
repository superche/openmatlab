"""String arrays (#459) and string/text methods (#460) — Epic #482."""

import numpy as np
import pytest

from openmatlab.host.display import _format_value
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.char_value import CharValue, StringValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session
from openmatlab.runtime.string_array import StringArray

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def _g(ws, n):
    v = ws.get(n)
    return v.data.tolist() if isinstance(v, StringArray) else [[v.text]]


# ----- #459 construction / queries -----

def test_bracket_construction_and_shape():
    ws = _ws('a = ["a" "bc"]; b = ["a"; "b"]; c = ["a" \'xy\' 3]; e = ["a" [] "b"]; m = ["a" "b"; "c" "d"];'
             ' sa = size(a); sb = size(b); n = numel(m); k = class(a); i = isstring(m); z = isempty(a);')
    assert _g(ws, "a") == [["a", "bc"]] and _g(ws, "b") == [["a"], ["b"]]
    assert _g(ws, "c") == [["a", "xy", "3"]] and _g(ws, "e") == [["a", "b"]]
    assert _v(ws, "sa").tolist() == [[1, 2]] and _v(ws, "sb").tolist() == [[2, 1]] and _v(ws, "n").item() == 4
    assert ws.get("k").text == "string" and _v(ws, "i").item() and not _v(ws, "z").item()


def test_strings_and_string_conversion():
    ws = _ws("a = strings(2,1); b = strings(0,3); c = string({'a','bb'}); d = string([1 2.5]); e = strings;"
             " f = string(['ab';'cd']); sb = size(b); y = isempty(b);")
    assert _g(ws, "a") == [[""], [""]] and _v(ws, "sb").tolist() == [[0, 3]] and _v(ws, "y").item()
    assert _g(ws, "c") == [["a", "bb"]] and _g(ws, "d") == [["1", "2.5"]]
    assert isinstance(ws.get("e"), StringValue) and ws.get("e").text == ""
    assert _g(ws, "f") == [["ab"], ["cd"]]


def test_single_element_is_a_string_scalar():
    ws = _ws('s = ["a" "b"]; t = s(2); u = [s(1)];')
    assert isinstance(ws.get("t"), StringValue) and ws.get("t").text == "b"
    assert isinstance(ws.get("u"), StringValue)


# ----- #459 indexing / assignment -----

def test_indexing_forms():
    ws = _ws('s = ["a" "b" "c"]; a = s(2:3); b = s(end); c = s(:); d = s([true false true]); m = ["a" "b"; "c" "d"];'
             ' e = m(2,:); f = m(:,1); g = s{2};')
    assert _g(ws, "a") == [["b", "c"]] and _g(ws, "b") == [["c"]] and _g(ws, "c") == [["a"], ["b"], ["c"]]
    assert _g(ws, "d") == [["a", "c"]] and _g(ws, "e") == [["c", "d"]] and _g(ws, "f") == [["a"], ["c"]]
    assert type(ws.get("g")) is CharValue and ws.get("g").text == "b"


def test_assignment_growth_missing_and_delete():
    ws = _ws('s = ["a" "b"]; s(2) = "x"; t = "a"; t(3) = "c"; u = ["a" "b" "c"]; u(2) = []; w = ["a" "b"]; w(2) = \'yz\';'
             ' v = ["a" "b"]; v(2) = 7; q = ["a" "b"]; q{3} = \'c\'; r = ["a" "b"]; r(:) = []; sr = size(r);')
    assert _g(ws, "s") == [["a", "x"]] and _g(ws, "t") == [["a", None, "c"]]
    assert _g(ws, "u") == [["a", "c"]] and _g(ws, "w") == [["a", "yz"]] and _g(ws, "v") == [["a", "7"]]
    assert _g(ws, "q") == [["a", "b", "c"]] and _v(ws, "sr").tolist() == [[0, 0]]


def test_value_semantics_on_copy():
    ws = _ws('a = ["x" "y"]; b = a; b(1) = "z";')
    assert _g(ws, "a") == [["x", "y"]] and _g(ws, "b") == [["z", "y"]]


def test_index_errors():
    with pytest.raises(EvalError, match="Index must not exceed 2"):
        _ws('s = ["a" "b"]; x = s(5);')
    with pytest.raises(EvalError, match="Conversion to string from cell is not possible"):
        _ws('s = ["a" "b"]; s(2) = {1};')
    with pytest.raises(EvalError, match="must select one element"):
        _ws('s = ["a" "b"]; x = s{:};')
    with pytest.raises(EvalError, match="missing string"):
        _ws('s = "a"; s(3) = "c"; x = s{2};')


# ----- #459 elementwise ops / conversions -----

def test_plus_and_comparisons_broadcast():
    ws = _ws('s = ["a" "b"]; p = s + "x"; q = "<" + s; e = s == "a"; n = s ~= ["a" "c"]; c = s == \'b\';'
             ' t = "a"; t(3) = "c"; m = t == "a"; k = t ~= "zz"; j = t + "!";')
    assert _g(ws, "p") == [["ax", "bx"]] and _g(ws, "q") == [["<a", "<b"]]
    assert _v(ws, "e").tolist() == [[True, False]] and _v(ws, "n").tolist() == [[False, True]]
    assert _v(ws, "c").tolist() == [[False, True]]
    assert _v(ws, "m").tolist() == [[True, False, False]] and _v(ws, "k").tolist() == [[True, True, True]]
    assert _g(ws, "j") == [["a!", None, "c!"]]
    with pytest.raises(EvalError, match="incompatible sizes"):
        _ws('x = ["a" "b"] + ["a" "b" "c"];')
    with pytest.raises(EvalError, match="not supported for operands of type 'string'"):
        _ws('x = ["a" "b"] - 1;')


def test_transpose_char_cellstr_strlength_isequal_for():
    ws = _ws('s = ["ab" "c"]; t = s\'; st = size(t); c = char(s); l = strlength(s); k = cellstr(s);'
             ' e = isequal(s, ["ab" "c"]); f = isequal(s, ["ab" "d"]); out = ""; for w = s, out = out + w; end')
    assert _v(ws, "st").tolist() == [[2, 1]] and ws.get("c").rows == ("ab", "c ")
    assert _v(ws, "l").tolist() == [[2, 1]] and isinstance(ws.get("k"), CellValue)
    assert _v(ws, "e").item() and not _v(ws, "f").item() and ws.get("out").text == "abc"


def test_display():
    ws = _ws('s = ["a" "bcd"; "ef" "g"]; t = "a"; t(3) = "c"; e = strings(0,3); c = {["a" "b"]};')
    assert _format_value(ws.get("s")) == '  2×2 string array\n\n    "a"     "bcd"\n    "ef"    "g"'
    assert _format_value(ws.get("t")) == '  1×3 string array\n\n    "a"    <missing>    "c"'
    assert _format_value(ws.get("e")) == "  0×3 empty string array"
    assert _format_value(ws.get("c")).splitlines()[1] == "  (1,1) = [1×2 string]"


# ----- #460 methods -----

@pytest.mark.parametrize("code,want", [
    ('upper(["ab" "c"])', [["AB", "C"]]),
    ('lower("AbC")', [["abc"]]),
    ('strip("  a  ")', [["a"]]),
    ('strip("xxaxx", "both", "x")', [["a"]]),
    ('strip("  a  ", "left")', [["a  "]]),
    ('strip("  a  ", "right")', [["  a"]]),
    ('strtrim(["  a" "b  "])', [["a", "b"]]),
    ('replace("aXbX", "X", "-")', [["a-b-"]]),
    ('replace(["aX" "bY"], ["X" "Y"], "_")', [["a_", "b_"]]),
    ('split("a b  c")', [["a"], ["b"], ["c"]]),
    ('split("a,,b", ",")', [["a"], ["b"]]),
    ('split("a,,b", ",", "CollapseDelimiters", false)', [["a"], [""], ["b"]]),
    ('split("a-b_c", ["-" "_"])', [["a"], ["b"], ["c"]]),
    ('join(["a" "b" "c"], "-")', [["a-b-c"]]),
    ('join(["a" "b"])', [["a b"]]),
    ('join(["a" "b"; "c" "d"], ",")', [["a,b"], ["c,d"]]),
])
def test_string_methods_return_strings(code, want):
    assert _g(_ws("r = " + code + ";"), "r") == want


@pytest.mark.parametrize("code,want", [
    ("upper('ab')", "AB"), ("lower('AB')", "ab"), ("strtrim(' x ')", "x"), ("strip(' x ')", "x"),
    ("strrep('aXb', 'X', 'yy')", "ayyb"), ("replace('aXb', 'X', 'y')", "ayb"), ("join({'a','b'}, ',')", "a,b"),
])
def test_char_in_char_out(code, want):
    v = _ws("r = " + code + ";").get("r")
    assert type(v) is CharValue and v.text == want


def test_cellstr_in_cell_out_and_split_char():
    ws = _ws("a = upper({'ab', 'c'}); b = split('a-b', '-');")
    assert isinstance(ws.get("a"), CellValue) and [x.text for x in ws.get("a").rows[0]] == ["AB", "C"]
    assert isinstance(ws.get("b"), CellValue) and [r[0].text for r in ws.get("b").rows] == ["a", "b"]


@pytest.mark.parametrize("code,want", [
    ('contains(["abc" "xyz"], "b")', [[True, False]]),
    ('contains("abc", ["x" "c"])', [[True]]),
    ('contains("ABC", "b", "IgnoreCase", true)', [[True]]),
    ("contains({'ab', 'cd'}, 'd')", [[False, True]]),
    ('startsWith("abc", "ab")', [[True]]),
    ('startsWith(["abc" "bc"], "b")', [[False, True]]),
    ('endsWith(["abc" "c"], "c")', [[True, True]]),
    ('endsWith("abc", "B", "IgnoreCase", true)', [[False]]),
    ('strcmp("a", \'a\')', [[True]]),
    ('strcmp(["a" "b"], "a")', [[True, False]]),
    ("strcmp({'a','b'}, {'a','c'})", [[True, False]]),
    ("strcmpi('ABC', 'abc')", [[True]]),
    ("strcmp(1, 'a')", [[False]]),
    ("strcmp('a', 'ab')", [[False]]),
])
def test_logical_methods(code, want):
    ws = _ws("r = " + code + ";")
    assert ws.get("r").matlab_class() == "logical" and _v(ws, "r").tolist() == want


def test_missing_propagates_through_methods():
    ws = _ws('t = "a"; t(3) = "c"; u = upper(t); c = contains(t, "a"); l = strlength(t);')
    assert _g(ws, "u") == [["A", None, "C"]] and _v(ws, "c").tolist() == [[True, False, False]]
    assert np.isnan(_v(ws, "l")[0, 1])


def test_method_errors():
    with pytest.raises(EvalError, match="First argument must be text"):
        _ws("x = upper(3);")
    with pytest.raises(EvalError, match="same size or either one can be a scalar"):
        _ws('x = strcmp(["a" "b"], ["a" "b" "c"]);')
    with pytest.raises(EvalError, match="side must be"):
        _ws('x = strip("a", "middle");')
