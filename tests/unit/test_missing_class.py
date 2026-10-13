"""missing as its own class (#504): converts to NaN or <missing> by context."""

import numpy as np
import pytest

from openmatlab.host.display import _format_value
from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_class_and_display():
    ws = _ws("m = missing; c = class(m); i = ismissing(m); d = double(m);")
    assert ws.get("c").text == "missing" and _v(ws, "i").item() and np.isnan(_v(ws, "d")).all()
    assert _format_value(ws.get("m")) == "  missing\n\n    <missing>"


def test_numeric_context_is_nan():
    ws = _ws("x = [1 missing 3]; y = [1 2]; y(2) = missing;")
    x = _v(ws, "x")
    assert x.shape == (1, 3) and np.isnan(x[0, 1]) and x[0, 2] == 3
    assert np.isnan(_v(ws, "y")[0, 1])


def test_string_context_is_missing_string():
    ws = _ws('s = ["a" missing]; t = string(missing); u = ["a" "b"]; u(2) = missing; k = ismissing(u);')
    assert ws.get("s").data.tolist() == [["a", None]]
    assert ws.get("t").data.tolist() == [[None]]
    assert _v(ws, "k").tolist() == [[False, True]]


def test_cell_keeps_missing():
    ws = _ws("c = {1, missing}; k = class(c{2});")
    assert ws.get("k").text == "missing"
