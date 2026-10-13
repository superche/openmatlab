"""Sparse residuals (#488): S.^0 (full), for over sparse, sparse solve, spdiags/spalloc/sprand/spfun."""

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


def _v(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def _sp(ws, n):
    return bool(getattr(ws.get(n), "issparse", False))


def test_power_zero_is_full_ones():
    # #488 corner case: kept as full (0.^0 fills every entry), matching the existing
    # propagation test in test_sparse.py.
    ws = _ws("T = sparse([1 0; 0 2]) .^ 0;")
    assert not _sp(ws, "T") and _v(ws, "T").tolist() == [[1, 1], [1, 1]]


def test_for_over_sparse_columns_are_sparse():
    ws = _ws("k = []; n = []; for c = sparse([1 0; 0 2]), k(end+1) = issparse(c); n(end+1) = nnz(c); end")
    assert _v(ws, "k").tolist() == [[1, 1]] and _v(ws, "n").tolist() == [[1, 1]]


def test_sparse_solve_sparsity():
    ws = _ws("S = sparse([2 0; 0 4]); X = S \\ S; y = S \\ [2; 4]; Y = S / S; I = inv(S);")
    assert _sp(ws, "X") and _sp(ws, "Y") and _sp(ws, "I") and not _sp(ws, "y")
    assert _v(ws, "y").ravel().tolist() == [1, 1]
    np.testing.assert_allclose(_v(ws, "I"), [[0.5, 0], [0, 0.25]])


def test_spdiags_create_matches_matlab_doc():
    ws = _ws("S = spdiags([1 2 3; 4 5 6; 7 8 9], [-1 0 1], 3, 3); W = spdiags([1 2 3; 4 5 6]', [0 1], 3, 4);"
             " D = spdiags([1; 2; 3], 0, 3, 3); C = spdiags(5, 1, 3, 3);")
    assert _sp(ws, "S")
    assert _v(ws, "S").tolist() == [[2, 6, 0], [1, 5, 9], [0, 4, 8]]
    assert _v(ws, "W").tolist() == [[1, 4, 0, 0], [0, 2, 5, 0], [0, 0, 3, 6]]
    assert _v(ws, "D").tolist() == [[1, 0, 0], [0, 2, 0], [0, 0, 3]]
    assert _v(ws, "C").tolist() == [[0, 5, 0], [0, 0, 5], [0, 0, 0]]


def test_spdiags_extract():
    ws = _ws("A = [1 2 0; 3 4 5; 0 6 7]; [B, d] = spdiags(A); B0 = spdiags(A, 0);")
    assert _v(ws, "B").tolist() == [[3, 1, 0], [6, 4, 2], [0, 7, 5]]
    assert _v(ws, "d").ravel().tolist() == [-1, 0, 1]
    assert _v(ws, "B0").ravel().tolist() == [1, 4, 7]


def test_spalloc_sprand_spfun():
    ws = _ws("Z = spalloc(2, 3, 5); R = sprand(4, 5, 0.5); P = sprand(sparse([1 0; 0 1]));"
             " F = spfun(@exp, sparse([0 1; 2 0]));")
    assert _sp(ws, "Z") and _v(ws, "Z").shape == (2, 3) and not _v(ws, "Z").any()
    r = _v(ws, "R")
    assert _sp(ws, "R") and np.count_nonzero(r) == 10 and ((r >= 0) & (r < 1)).all()
    p = _v(ws, "P")
    assert p[0, 1] == 0 and p[1, 0] == 0
    np.testing.assert_allclose(_v(ws, "F"), [[0, np.e], [np.exp(2), 0]])
    assert _sp(ws, "F")


def test_residual_errors():
    for code in ("x = sprand(2, 2, 2);", "x = spfun(1, sparse(1));", "x = spdiags([1 2], [0 1 2], 3, 3);"):
        with pytest.raises(EvalError):
            _ws(code)
