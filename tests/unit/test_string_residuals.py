"""String residuals (#483): missing/ismissing, sort/unique, split of columns, sprintf/compose,
regexp family, extract/insert/pad/reverse, num2str/str2double."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.char_value import CharValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session
from openmatlab.runtime.string_array import StringArray

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _r(code):
    return _ws("r = " + code + ";").get("r")


def _g(v):
    return v.data.tolist() if isinstance(v, StringArray) else [[v.text]]


def _n(v):
    return np.asarray(v.backend_buffer()).tolist()


def test_missing_and_ismissing():
    assert _g(_r("string(missing)")) == [[None]]
    assert _n(_r('ismissing(["a" missing "c"])')) == [[False, True, False]]
    assert _n(_r("ismissing([1 NaN 3])")) == [[False, True, False]]
    assert _n(_r("ismissing({1})")) == [[False]]


def test_sort_and_unique_strings():
    ws = _ws('[t, i] = sort(["b" "a" missing "c"]); d = sort(["b"; "a"; "c"], "descend"); m = sort(["b" "a"; "a" "c"]);'
             ' [u, ia, ic] = unique(["b" "a" "b"]);')
    assert _g(ws.get("t")) == [["a", "b", "c", None]] and _n(ws.get("i")) == [[2, 1, 4, 3]]
    assert _g(ws.get("d")) == [["c"], ["b"], ["a"]] and _g(ws.get("m")) == [["a", "a"], ["b", "c"]]
    assert _g(ws.get("u")) == [["a", "b"]] and _n(ws.get("ia")) == [[2], [1]] and _n(ws.get("ic")) == [[2], [1], [2]]
    assert _n(_r("sort([3 1 2])")) == [[1, 2, 3]]  # numeric sort unchanged


def test_split_string_column():
    assert _g(_r('split(["a b"; "c d"])')) == [["a", "b"], ["c", "d"]]
    with pytest.raises(EvalError, match="different number of delimiters"):
        _r('split(["a b"; "c"])')
    # #503: a 1xN row now splits to 1xNxk (it used to raise the old "column vector" limitation)
    assert _r('split(["a b" "c d"])').shape == (1, 2, 2)


@pytest.mark.parametrize("code,want", [
    ("sprintf('%d-%s|', 1, 'ab', 2, 'c')", "1-ab|2-c|"),
    ("sprintf('%.2f', pi)", "3.14"),
    ("sprintf('%d', 1.5)", "1.500000e+00"),
    ("sprintf('%-4d|%5s', 7, 'ab')", "7   |   ab"),
    ("sprintf('%d,', [1 2 3])", "1,2,3,"),
    ("sprintf('a\\tb\\n')", "a\tb\n"),
    ("sprintf('100%%')", "100%"),
    ("sprintf('%x %o %e', 255, 8, 12345.678)", "ff 10 1.234568e+04"),
    ("sprintf('%g %g', 0.1, 1e10)", "0.1 1e+10"),
    ("sprintf('%c%c', 72, 105)", "Hi"),
    ("sprintf('%d %d', 1)", "1 "),
    ("sprintf('%f', NaN)", "NaN"),
])
def test_sprintf(code, want):
    v = _r(code)
    assert type(v) is CharValue and v.text == want


def test_sprintf_string_format_and_compose():
    assert _g(_r('sprintf("x=%g", 0.1)')) == [["x=0.1"]]
    assert _g(_r('compose("%d items", [1 2 3])')) == [["1 items", "2 items", "3 items"]]
    assert _g(_r('compose("%s=%d", ["a" "b"], [1 2])')) == [["a=1", "b=2"]]
    with pytest.raises(EvalError, match="not defined for 'cell'"):
        _r("sprintf('%d', {1})")


def test_regexp_outputs():
    m = _r(r"regexp('ab12cd345', '\d+', 'match')")
    assert isinstance(m, CellValue) and [x.text for x in m.rows[0]] == ["12", "345"]
    assert _n(_r("regexp('abcb', 'b')")) == [[2, 4]]
    ws = _ws(r"[s, e] = regexp('abcb', 'b'); t = regexp('k=v', '(\w)=(\w)', 'tokens'); o = regexp('a1b2', '\d', 'match', 'once'); p = regexp('a,b', ',', 'split');")
    assert _n(ws.get("s")) == [[2, 4]] and _n(ws.get("e")) == [[2, 4]]
    assert [x.text for x in ws.get("t").rows[0][0].rows[0]] == ["k", "v"]
    assert ws.get("o").text == "1" and [x.text for x in ws.get("p").rows[0]] == ["a", "b"]
    assert _g(_r('regexp("a1b22", "\\d+", "match")')) == [["1", "22"]]
    assert _r("regexpi('ABC', 'b', 'match', 'once')").text == "B"
    names = _r(r"regexp('k=v', '(?<key>\w)=(?<val>\w)', 'names')")
    # #504: 'names' is now a struct (was a 2xN {name; value} cell before structs existed)
    assert names.matlab_class() == "struct" and names.fields == ("key", "val")
    assert names.get("key").text == "k" and names.get("val").text == "v"
    with pytest.raises(EvalError, match="invalid expression"):
        _r("regexp('a', '(')")


def test_regexprep():
    assert _r(r"regexprep('hello world', '(\w+) (\w+)', '$2 $1')").text == "world hello"
    assert _r("regexprep('aaa', 'a', 'b', 'once')").text == "baa"
    assert _g(_r('regexprep(["a1" "b2"], "\\d", "#")')) == [["a#", "b#"]]
    assert _r("regexprep('ABC', 'b', 'x', 'ignorecase')").text == "AxC"


@pytest.mark.parametrize("code,want", [
    ('extractBetween("a[bc]d", "[", "]")', "bc"),
    ("extractAfter('key=val', '=')", "val"),
    ("extractBefore('key=val', '=')", "key"),
    ("extractAfter('abcdef', 2)", "cdef"),
    ("extractBetween('abcdef', 2, 4)", "bcd"),
    ('insertAfter("ab", "a", "-")', "a-b"),
    ("insertBefore('ab', 'b', '+')", "a+b"),
    ("pad('ab', 5, 'left')", "   ab"),
    ("pad('ab', 5)", "ab   "),
    ("pad('ab', 6, 'both', '*')", "**ab**"),
    ('reverse("abc")', "cba"),
])
def test_extract_insert_pad_reverse(code, want):
    assert _g(_r(code)) == [[want]]


def test_pad_to_longest():
    assert _g(_r('pad(["a" "abc"])')) == [["a  ", "abc"]]


@pytest.mark.parametrize("code,want", [
    ("num2str(pi)", "3.1416"), ("num2str(42)", "42"), ("num2str(3.14159, 3)", "3.14"),
    ("num2str(-7)", "-7"), ("num2str(NaN)", "NaN"), ("num2str(true)", "1"), ("num2str('ab')", "ab"),
    ("num2str(pi, '%10.4f')", "    3.1416"), ("num2str(int8(5))", "5"),
])
def test_num2str_scalars(code, want):
    assert _r(code).text == want


def test_num2str_integer_rows():
    assert _r("num2str([1 2 3])").text == "1  2  3"
    assert _r("num2str([1 10; 2 3])").rows == (" 1  10", " 2   3")


def test_str2double():
    got = np.asarray(_r('str2double(["1.5" "x" "1e3" "-Inf"])').backend_buffer())
    assert got[0, 0] == 1.5 and np.isnan(got[0, 1]) and got[0, 2] == 1000 and got[0, 3] == -np.inf
    assert _n(_r("str2double('  -2 ')")) == [[-2]]
    assert np.isnan(_n(_r("str2double({'3','a'})"))[0][1]) and _n(_r("str2double({'3','a'})"))[0][0] == 3
    assert np.isnan(_n(_r("str2double(5)"))[0][0]) and _n(_r("str2double('1,000')")) == [[1000]]


def test_double_quoted_literal_has_no_backslash_escapes():
    # MATLAB: "\d" is two characters; "" inside "..." is one quote (lexer fix found via #483)
    assert _r('strlength("\\d")').backend_buffer().item() == 2
    assert _r('"say ""hi"""').text == 'say "hi"'
    assert _r('""').text == ""
