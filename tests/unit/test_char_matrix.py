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
