"""Indexed array assignment A(i)=v (Issue #116)."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.lang.ast_nodes import ArrayAssign
from openmatlab.lang.parser import parse
from openmatlab.runtime.evaluator import EvalError
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _g(code: str, name: str) -> np.ndarray:
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return np.asarray(s.workspace.get(name).backend_buffer())


def test_parse_array_assign():
    assert isinstance(parse("A(1,2) = 5")[0], ArrayAssign)


def test_assign_subscript():
    out = _g("A = [1 2; 3 4]; A(2,1) = 9; B = A;", "B")
    assert np.array_equal(out, [[1, 2], [9, 4]])


def test_assign_linear_column_major():
    # A = [1 2; 3 4] linear: 1→1, 2→3, 3→2, 4→4
    out = _g("A = [1 2; 3 4]; A(2) = 8; B = A;", "B")
    assert np.array_equal(out, [[1, 2], [8, 4]])


def test_assign_row_vector():
    out = _g("v = [1 2 3]; v(2) = 5; w = v;", "w")
    assert np.array_equal(out, [[1, 5, 3]])


def test_read_after_write():
    s = Session.create_default()
    r = ReplSession(s)
    r.run_line("A = zeros(2); A(1,1) = 3; x = A(1,1);")
    assert float(s.workspace.get("x").backend_buffer().reshape(-1)[0]) == 3


def test_oob_grows():
    """EPIC-021 / #119: OOB assign grows with zero fill (was error in Epic #8)."""
    s = Session.create_default()
    ReplSession(s).run_line("A = [1 2]; A(5) = 1;")
    import numpy as np
    assert np.asarray(s.workspace.get("A").backend_buffer()).tolist() == [
        [1.0, 2.0, 0.0, 0.0, 1.0]
    ]


def test_cell_assign_still_works():
    s = Session.create_default()
    ReplSession(s).run_line("c = {1, 2}; c{1} = 7;")
    assert float(s.workspace.get("c").get(0, 0).backend_buffer().reshape(-1)[0]) == 7
