"""Multi-row char matrices: ['ab';'cd'], char(...) padding, double() (Issue #427)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _num(ws, n):
    return np.asarray(ws.get(n).backend_buffer()).tolist()


def test_vertical_concat_builds_matrix():
    ws = _ws("x = ['ab'; 'cd']; s = size(x); n = numel(x);")
    assert ws.get("x").rows == ("ab", "cd")
    assert _num(ws, "s") == [[2, 2]] and _num(ws, "n") == [[4]]


def test_mixed_horizontal_rows():
    ws = _ws("x = ['a' 'b'; 'c' 'd'];")
    assert ws.get("x").rows == ("ab", "cd")


def test_ragged_rows_error():
    with pytest.raises(EvalError, match="Dimensions of arrays being concatenated"):
        _ws("x = ['ab'; 'c'];")


def test_char_pads_with_blanks():
    ws = _ws("x = char('a', 'bcd'); s = size(x); y = char({'hi', 'there'});")
    assert ws.get("x").rows == ("a  ", "bcd")
    assert _num(ws, "s") == [[2, 3]]
    assert ws.get("y").rows == ("hi   ", "there")


def test_char_from_codes_and_double_roundtrip():
    ws = _ws("x = char([72 105]); d = double(['ab'; 'cd']);")
    assert ws.get("x").rows == ("Hi",)
    assert _num(ws, "d") == [[97, 98], [99, 100]]


def test_display_rows(capsys):
    _ws("x = ['ab'; 'cd']")
    assert "x =\n\nab\ncd\n" in capsys.readouterr().out


def test_empty_char_shapes():
    """'' is 0×0. Indexing, char(), and blanks(0) keep 1×0 and 0×N (#1058)."""
    from openmatlab.host.display import _format_value
    from openmatlab.runtime.char_value import CharValue

    assert CharValue("").shape == (0, 0)
    assert CharValue(rows=("",)).shape == (1, 0)
    assert CharValue(rows=(), ncols=3).shape == (0, 3)
    assert CharValue("") != CharValue(rows=("",))
    assert CharValue(rows=(), ncols=2) != CharValue(rows=(), ncols=3)

    ws = _ws(
        "x = 'abc'; r = x(:,[]); c = x([],:); z = x([],[]);"
        "y = ['ab'; 'cd']; rr = y(:,[]); cc = y([],:);"
        "a = char(zeros(1,0)); b = char(zeros(0,3)); d = char(zeros(2,0)); e = char(zeros(0,0));"
        "t = r'; u = cc';"
        "h = [r r]; p = ['abc' r]; q = [cc cc]; v = [cc; cc];"
        "g = blanks(0); n = numel(r); ir = isrow(r); ic = iscolumn(char(zeros(0,1)));"
        "dr = double(b); back = char(dr);"
        "same = isequal(r, r); diff0 = isequal(r, ''); diffw = isequal(b, char(zeros(0,2)));"
        "up = upper(g); tr = strtrim(g); sp = strtrim('   ');"
    )
    assert ws.get("r").matlab_class() == "char" and ws.get("r").shape == (1, 0)
    assert ws.get("c").shape == (0, 3) and ws.get("z").shape == (0, 0)
    assert ws.get("rr").shape == (2, 0) and ws.get("cc").shape == (0, 2)
    assert ws.get("a").shape == (1, 0) and ws.get("b").shape == (0, 3)
    assert ws.get("d").shape == (2, 0) and ws.get("e").shape == (0, 0)
    assert ws.get("t").shape == (0, 1) and ws.get("u").shape == (2, 0)
    assert ws.get("h").shape == (1, 0) and ws.get("p").text == "abc" and ws.get("p").shape == (1, 3)
    assert ws.get("q").shape == (0, 4) and ws.get("v").shape == (0, 2)
    assert ws.get("g").shape == (1, 0) and _num(ws, "n") == [[0]]
    assert _num(ws, "ir") == [[True]] and _num(ws, "ic") == [[True]]
    assert np.asarray(ws.get("dr").backend_buffer()).shape == (0, 3)
    assert ws.get("back").shape == (0, 3)
    assert _num(ws, "same") == [[True]] and _num(ws, "diff0") == [[False]] and _num(ws, "diffw") == [[False]]
    assert ws.get("up").shape == (1, 0) and ws.get("tr").shape == (1, 0) and ws.get("sp").shape == (0, 0)
    assert _format_value(ws.get("r")) == "  1\u00d70 empty char array"
    assert _format_value(ws.get("b")) == "  0\u00d73 empty char array"
    assert _format_value(ws.get("e")) == "  0\u00d70 empty char array"


def test_empty_char_save_load(tmp_path):
    m = tmp_path / "empty_char.mat"
    ws = _ws(f"a = char(zeros(0,3)); b = 'abc'(:,[]); save('{m}'); clear a b; load('{m}');")
    assert ws.get("a").shape == (0, 3) and ws.get("b").shape == (1, 0)
