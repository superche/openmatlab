"""N-D cell arrays: cell(m,n,p), size/ndims/numel, c{i,j,k} read/assign, c(i,j,k), display (#444)."""

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


def test_cell_nd_constructor_and_size():
    ws = _ws("c = cell(2,2,2); s = size(c); n = ndims(c); k = numel(c); d = cell([1 2 3]); t = size(d);"
             " e = cell(2,2,1); u = size(e); m = size(c, 3);")
    assert _v(ws, "s").tolist() == [[2, 2, 2]] and _v(ws, "n").item() == 3 and _v(ws, "k").item() == 8
    assert _v(ws, "t").tolist() == [[1, 2, 3]] and _v(ws, "u").tolist() == [[2, 2]]
    assert _v(ws, "m").item() == 2


def test_cell_nd_brace_read_assign_and_linear():
    ws = _ws("c = cell(2,2,2); c{1,2,2} = 5; c{2,1,1} = 'a'; a = c{1,2,2}; b = c{7}; c{2,end,end} = 9; z = c{8};"
             " s = size(c);")
    assert _v(ws, "a").item() == 5 and _v(ws, "b").item() == 5 and _v(ws, "z").item() == 9
    assert _v(ws, "s").tolist() == [[2, 2, 2]]


def test_cell_nd_paren_page_and_fold():
    ws = _ws("c = cell(2,2,2); c{1,1,2} = 4; d = c(:,:,2); s = size(d); x = d{1,1}; y = c{1,3};")
    assert _v(ws, "s").tolist() == [[2, 2]] and _v(ws, "x").item() == 4 and _v(ws, "y").item() == 4


def test_cell_nd_display_labels():
    ws = _ws("c = cell(1,1,2); c{1,1,2} = 3;")
    assert _format_value(ws.get("c")).splitlines() == [
        "{1×1×2 cell}", "  (1,1,1) = [](0x0)", "  (1,1,2) = 3"]


def test_cell_nd_errors():
    with pytest.raises(EvalError, match="Index in position 3 exceeds array bounds"):
        _ws("c = cell(2,2,2); x = c{1,1,3};")
    # trailing ranges were rejected until #479; they now select (see test_nd_cell_residuals.py)
    ws = _ws("c = cell(2,2,2); x = c(1,1,1:2); s = size(x);")
    assert _v(ws, "s").tolist() == [[1, 1, 2]]
    with pytest.raises(EvalError, match="positive integers"):
        _ws("c = cell(2,2,2); x = c{1,1,0};")
