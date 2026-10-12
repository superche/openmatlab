"""for-loop iterates columns (#471); isequal (#472)."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]
R = "A = reshape(1:8, 2, 2, 2);"


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_for_iterates_columns_471():
    ws = _ws("k=0; S=zeros(2,0); for c=[1 2;3 4], k=k+1; S=[S c]; end; s=size(c);")
    assert _v(ws, "S").tolist() == [[1, 2], [3, 4]] and _v(ws, "s").tolist() == [[2, 1]]
    assert _v(_ws("n=0; for c=zeros(0,3), n=n+1; end"), "n").item() == 3
    assert _v(_ws("n=0; for c=[], n=n+1; end"), "n").item() == 0
    assert _v(_ws("n=0; for c=ones(2,2,3), n=n+1; end"), "n").item() == 6
    ws = _ws("t=0; for c=1:4, t=t+c; end; for q=int8([1 2]), end; k=class(q);")
    assert _v(ws, "t").item() == 10 and ws.get("k").text == "int8"


def test_isequal_472():
    for code, want in [("isequal([1 2],[1 2])", 1), ("isequal([1 2],[1;2])", 0),
                       ("isequal(int8(3),3,3)", 1), ("isequal(NaN,NaN)", 0),
                       ("isequal({1,'ab'},{1,'ab'})", 1), ("isequal({1,'ab'},{1,'ac'})", 0),
                       ("isequal('ab','ab')", 1), ("isequal({1},1)", 0)]:
        ws = _ws("r = " + code + ";")
        assert ws.get("r").matlab_class() == "logical" and _v(ws, "r").item() == want, code
    with pytest.raises(Exception, match="at least two"):
        _ws("isequal(1)")
