"""N-D string arrays and split of rows (#503)."""

import io

import numpy as np
import pytest

from openmatlab.host.display import ConsoleDisplay
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


def test_split_row_and_matrix_go_to_third_dim():
    ws = _ws('s = split(["a b" "c d"]); z = size(s); m = split(["a b" "c d"; "e f" "g h"]); zm = size(m);'
             " c = split([\"a b\"; \"c d\"]); zc = size(c);")
    assert _v(ws, "z").tolist() == [[1, 2, 2]] and _v(ws, "zm").tolist() == [[2, 2, 2]]
    assert _v(ws, "zc").tolist() == [[2, 2]]
    g = ws.get("s").data
    assert g[0, :, 0].tolist() == ["a", "c"] and g[0, :, 1].tolist() == ["b", "d"]
    assert ws.get("m").data[1, 1, 1] == "h"


def test_split_inconsistent_counts():
    with pytest.raises(EvalError, match="Element 2 .* different number of delimiters"):
        _ws('s = split(["a b" "c"]);')


def test_strings_nd_index_assign_and_methods():
    ws = _ws('t = strings(1, 2, 2); n = numel(t); t(1, 2, 2) = "z"; p = t(:, :, 2); q = t(:); l = strlength(t);'
             ' u = upper(t); e = t == "z"; w = strings([2 1 3]); zw = size(w);')
    assert _v(ws, "n").item() == 4 and ws.get("p").data.tolist() == [["", "z"]]
    assert ws.get("q").shape == (4, 1) and ws.get("q").data[3, 0] == "z"
    assert _v(ws, "l").shape == (1, 2, 2) and _v(ws, "l")[0, 1, 1] == 1
    assert ws.get("u").data[0, 1, 1] == "Z" and _v(ws, "e")[0, 1, 1]
    assert _v(ws, "zw").tolist() == [[2, 1, 3]]


def test_trailing_singleton_dims_drop():
    ws = _ws("t = strings(2, 2, 1); z = size(t);")
    assert _v(ws, "z").tolist() == [[2, 2]]


def test_nd_display_pages():
    s = Session.create_default()
    ReplSession(s).run_line('t = split(["a b" "c d"]);')
    buf = io.StringIO()
    ConsoleDisplay(stream=buf).show(s.workspace.get("t"), name="t")
    out = buf.getvalue()
    assert "1x2x2 string array" in out and 't(:,:,1) =\n\n    "a"    "c"' in out and 't(:,:,2) =\n\n    "b"    "d"' in out
