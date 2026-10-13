"""Native sparse S\\b (#522) and the remaining compressed paths (#523)."""

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.numerics import sparse as sp
from openmatlab.numerics.ndarray_value import NDArrayValue
from openmatlab.runtime.session import Session

pytestmark = [pytest.mark.unit, pytest.mark.needs_numpy]


def _run(code, **vars_):
    s = Session.create_default()
    for k, v in vars_.items():
        s.workspace.set(k, NDArrayValue(np.asarray(v, dtype=float)))
    ReplSession(s).run_line(code)
    return s.workspace


def _g(ws, n):
    return np.asarray(ws.get(n).backend_buffer())


def _dens(code):
    before = sp.DENSIFY_COUNT[0]
    ws = _run(code)
    return ws, sp.DENSIFY_COUNT[0] - before


# --- #522 ----------------------------------------------------------------------

def test_large_solves_do_not_densify():
    code = ("n = 100000; e = ones(n, 1); D = spdiags(2*e, 0, n, n); x1 = D \\ e;"
            " L = spdiags([e 2*e], [-1 0], n, n); x2 = L \\ e; U = L'; x3 = U \\ e;"
            " T = spdiags([-e 4*e -e], [-1 0 1], n, n); x4 = T \\ e; r4 = norm(T*x4 - e, Inf);"
            " x5 = e' / T; r5 = norm(x5*T - e', Inf);")
    ws, d = _dens(code)
    assert d == 0
    assert np.allclose(_g(ws, "x1"), 0.5)
    assert _g(ws, "r4").item() < 1e-12 and _g(ws, "r5").item() < 1e-12
    x2 = _g(ws, "x2").ravel()
    assert x2[0] == 0.5 and np.isclose(x2[1], 0.25)


def test_general_pattern_uses_reordering():
    rng = np.random.default_rng(3)
    n = 3000
    p = rng.permutation(n)
    k = np.arange(n)
    I = np.r_[k, k[1:], k[:-1]] + 1
    J = np.r_[k, k[:-1], k[1:]] + 1
    V = np.r_[np.full(n, 4.0), rng.normal(size=2 * n - 2)]
    code = "S = sparse(P(I), P(J), V, n, n); b = (1:n)'; x = S \\ b; r = norm(S*x - b, Inf);"
    before = sp.DENSIFY_COUNT[0]
    ws = _run(code, P=(p + 1).reshape(1, -1), I=I.reshape(1, -1), J=J.reshape(1, -1),
              V=V.reshape(1, -1), n=[[n]])
    assert sp.DENSIFY_COUNT[0] == before and _g(ws, "r").item() < 1e-9


@pytest.mark.parametrize("seed", range(8))
def test_solve_parity_with_dense(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(1, 9))
    A = np.where(rng.random((n, n)) < 0.35, rng.normal(size=(n, n)), 0) + np.diag(rng.normal(size=n) + 3)
    A = [A, np.tril(A), np.triu(A), np.diag(np.diag(A))][seed % 4]
    B = rng.normal(size=(n, 2))
    ws = _run("x1 = sparse(A) \\ B; x2 = A \\ B; y1 = B' / sparse(A); y2 = B' / A; k = issparse(x1);",
              A=A, B=B)
    assert np.allclose(_g(ws, "x1"), _g(ws, "x2")) and np.allclose(_g(ws, "y1"), _g(ws, "y2"))
    assert not _g(ws, "k").item()


def test_singular_keeps_matlab_warning():
    from openmatlab.runtime import warnings as mw

    ws = _run("S = sparse([1 2; 2 4]); x = S \\ [1; 2]; [msg, id] = lastwarn();")
    from openmatlab.runtime.char_value import CharValue

    msg = ws.get("msg")
    assert isinstance(msg, CharValue) and "singular" in msg.text


# --- #523 ----------------------------------------------------------------------

def test_remaining_paths_do_not_densify():
    code = ("n = 100000; E = speye(n); v = E(:); a = E > 0; b = E ~= 0; c = E < 0; d = E > 2*E;"
            " m1 = mean(E); m2 = mean(E, 2); cs = cumsum(E(1:10, :)); R = reshape(E, n*10, n/10);"
            " F1 = flipud(E); F2 = fliplr(E); F3 = flip(E); C = circshift(E, 1); P = permute(E, [2 1]);"
            " Q = (2*E)^3; t = 0; for col = E(:, 1:5), t = t + nnz(col); end")
    ws, d = _dens(code)
    assert d == 0
    assert ws.get("v").shape == (10 ** 10, 1) and ws.get("v").store.nnz == 100000
    assert ws.get("a").store.nnz == 100000 and ws.get("c").store.nnz == 0 and ws.get("d").store.nnz == 0
    assert ws.get("cs").store.nnz == 55 and ws.get("R").shape == (1000000, 10000)
    assert ws.get("Q").store.data[:2].tolist() == [8, 8] and _g(ws, "t").item() == 5
    assert ws.get("F1").store.rows[0] == 99999


@pytest.mark.parametrize("seed", range(5))
def test_remaining_paths_parity(seed):
    rng = np.random.default_rng(seed)
    m, n = rng.integers(2, 6, 2)
    A = np.where(rng.random((m, n)) < 0.5, rng.integers(-3, 4, (m, n)), 0).astype(float)
    Bm = np.where(rng.random((m, n)) < 0.5, rng.integers(-3, 4, (m, n)), 0).astype(float)
    Q = np.where(rng.random((m, m)) < 0.5, rng.integers(-2, 3, (m, m)), 0).astype(float)
    exprs = ["X > 0", "X < 1", "X ~= Y", "X > Y", "X == 2", "1 < X", "mean(X)", "mean(X, 2)",
             "cumsum(X)", "cumsum(X, 2)", f"reshape(X, {n}, {m})", f"reshape(X, [1 {m * n}])",
             "flipud(X)", "fliplr(X)", "flip(X)", "flip(X, 2)", "circshift(X, 1)",
             "circshift(X, [1 -1])", "circshift(X, 2, 2)", "permute(X, [2 1])", "Z^3", "Z^1"]
    for e in exprs:
        code = (f"X = sparse(A); Y = sparse(B); Z = sparse(Q); r1 = full({e}); s1 = issparse({e});"
                f" X = A; Y = B; Z = Q; r2 = {e};")
        ws = _run(code, A=A, B=Bm, Q=Q)
        r1, r2 = _g(ws, "r1"), _g(ws, "r2")
        assert r1.shape == r2.shape and np.allclose(r1, r2), e
        assert _g(ws, "s1").item(), e
    ws = _run("X = sparse(A); t = []; for c = X, t = [t full(sum(c))]; end; u = sum(A);", A=A)
    assert np.allclose(_g(ws, "t"), _g(ws, "u"))
