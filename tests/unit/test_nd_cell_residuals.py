"""N-D cell residuals (#479): growth, trailing ranges, paren assign/delete, cat/reshape/permute/squeeze."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.cell_value import CellValue
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_brace_growth_into_new_pages():
    ws = _ws("c = cell(2,2); c{1,1,3} = 7; s = size(c); x = c{1,1,3}; e = isempty(c{2,2,2});")
    assert _v(ws, "s").tolist() == [[2, 2, 3]] and _v(ws, "x").item() == 7 and _v(ws, "e").item()


def test_trailing_ranges_and_csl_pack():
    ws = _ws("c = cell(2,2,2); c{1,2,2} = 5; d = c(1,:,:); s = size(d); y = d{1,2,2}; p = c{1,1,1:2}; k = class(p);")
    assert _v(ws, "s").tolist() == [[1, 2, 2]] and _v(ws, "y").item() == 5 and ws.get("k").text == "cell"


def test_paren_assign_broadcast_and_delete():
    ws = _ws("c = cell(2,2,2); c(:,:,3) = {1}; s = size(c); x = c{2,2,3}; c(:,:,1) = []; t = size(c); y = c{1,1,2};")
    assert _v(ws, "s").tolist() == [[2, 2, 3]] and _v(ws, "x").item() == 1
    assert _v(ws, "t").tolist() == [[2, 2, 2]] and _v(ws, "y").item() == 1
    with pytest.raises(EvalError, match="Conversion to cell from double is not possible"):
        _ws("c = cell(2,2,2); c(1,1,1) = 3;")


def test_shape_builtins_on_cells():
    ws = _ws("c = {1,2,3,4}; d = reshape(c,2,2); a = d{2,1}; e = cat(3, {1,2}, {3,4}); s = size(e); b = e{1,2,2};"
             " f = squeeze(cell(2,1,3)); t = size(f); g = permute({1;2}, [2 1]); u = size(g); h = fliplr({1,2,3});"
             " z = h{1}; k = cat(1, {1}, {2}); w = size(k);")
    assert _v(ws, "a").item() == 2 and _v(ws, "s").tolist() == [[1, 2, 2]] and _v(ws, "b").item() == 4
    assert _v(ws, "t").tolist() == [[2, 3]] and _v(ws, "u").tolist() == [[1, 2]] and _v(ws, "z").item() == 3
    assert _v(ws, "w").tolist() == [[2, 1]] and isinstance(ws.get("d"), CellValue)
    with pytest.raises(EvalError, match="cannot concatenate cell arrays with non-cell"):
        _ws("x = cat(1, {1}, 2);")
