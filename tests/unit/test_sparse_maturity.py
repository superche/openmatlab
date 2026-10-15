"""Sparse maturity (Epic #631 / #527): mostly-true results stay sparse; kron stays sparse."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.numerics import sparse as sp
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code):
    s = Session.create_default()
    ReplSession(s).run_line(code)
    return s.workspace


def _g(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def test_mostly_true_relational_and_not_stay_sparse():
    before = sp.DENSIFY_COUNT[0]
    ws = _run("S = speye(3); a = S == 0; b = ~S; c = S <= 0.5; "
              "na = nnz(a); nb = nnz(b); nc = nnz(c); "
              "ka = issparse(a); kb = issparse(b); kc = issparse(c);")
    assert sp.DENSIFY_COUNT[0] == before
    assert all(_g(ws, k).item() for k in ("ka", "kb", "kc"))
    assert _g(ws, "na").item() == 6 and _g(ws, "nb").item() == 6 and _g(ws, "nc").item() == 6
    np.testing.assert_array_equal(_g(ws, "a"), [[0, 1, 1], [1, 0, 1], [1, 1, 0]])
    np.testing.assert_array_equal(_g(ws, "b"), _g(ws, "a"))


def test_kron_sparse_stays_sparse():
    before = sp.DENSIFY_COUNT[0]
    ws = _run("A = sparse([4 1 0; 1 4 1; 0 1 4]); K = kron(speye(2), A); "
              "k = issparse(K); n = nnz(K); f = full(K(1:3, 1:3));")
    assert sp.DENSIFY_COUNT[0] == before
    assert _g(ws, "k").item() and _g(ws, "n").item() == 14
    np.testing.assert_allclose(_g(ws, "f"), [[4, 1, 0], [1, 4, 1], [0, 1, 4]])


def test_sparse_times_full_kron():
    ws = _run("K = kron(speye(2), [1 2; 3 4]); k = issparse(K); f = full(K);")
    assert _g(ws, "k").item()
    np.testing.assert_allclose(_g(ws, "f"),
                               [[1, 2, 0, 0], [3, 4, 0, 0], [0, 0, 1, 2], [0, 0, 3, 4]])


def test_large_tridiagonal_solve():
    before = sp.DENSIFY_COUNT[0]
    ws = _run("n = 2000; T = spdiags([ones(n,1) 4*ones(n,1) ones(n,1)], -1:1, n, n); "
              "yy = T \\ ones(n, 1); ok = abs(yy(1000) - 1/6) < 1e-10; "
              "kt = issparse(T); nt = nnz(T); kx = issparse(yy);")
    assert sp.DENSIFY_COUNT[0] == before
    assert _g(ws, "ok").item() and _g(ws, "kt").item() and not _g(ws, "kx").item()
    assert _g(ws, "nt").item() == 5998
