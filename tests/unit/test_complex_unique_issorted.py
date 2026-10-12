"""Complex unique / issorted order by |z| then angle (#452)."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _ws(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_complex_unique_order_and_indices():
    ws = _ws("[u,ia,ic] = unique([2i 1 -1 2i 1]);")
    assert _v(ws, "u").tolist() == [[1, -1, 2j]]
    assert _v(ws, "ia").reshape(-1).tolist() == [2, 3, 1]
    assert _v(ws, "ic").reshape(-1).tolist() == [3, 1, 2, 3, 1]
    ws = _ws("u = unique([3+4i; 5; -5]);")
    assert _v(ws, "u").reshape(-1).tolist() == [5, 3 + 4j, -5]


def test_complex_issorted():
    for code, want in [("issorted([1 -1 1i])", 0), ("issorted([1 1i -1 2])", 1),
                       ("issorted([2 1i],'descend')", 1), ("issorted([1i -1],'descend')", 0),
                       ("issorted([1 NaN*1i])", 0)]:
        assert _v(_ws("r = " + code + ";"), "r").item() == want, code
