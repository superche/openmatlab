"""Compressed sparse storage (Epic #520; #515, #516, #517): O(nnz) memory, native
kernels and indexing that never densify, randomized parity with the dense path."""

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
        s.workspace.set(k, NDArrayValue(np.asarray(v)))
    ReplSession(s).run_line(code)
    return s.workspace


def _dens(fn):
    before = sp.DENSIFY_COUNT[0]
    out = fn()
    return out, sp.DENSIFY_COUNT[0] - before


# --- #515: container, construction, queries -------------------------------------

def test_storage_is_compressed():
    ws, d = _dens(lambda: _run("S = sparse([1 0 2; 0 0 3]);"))
    st = ws.get("S").store
    assert st.rows.tolist() == [0, 0, 1] and st.indptr.tolist() == [0, 1, 1, 3]
    assert st.data.tolist() == [1, 2, 3] and d == 0


def test_huge_construction_and_queries_do_not_densify():
    code = ("S = sparse(100000, 100000); E = speye(100000); A = spalloc(100000, 100000, 10);"
            " T = sparse([1 99999 5], [2 100000 5], [4 5 6], 100000, 100000);"
            " D = spdiags([1:100000]', 0, 100000, 100000);"
            " n1 = nnz(E); n2 = nzmax(T); z = size(S); v = nonzeros(T); [i, j, x] = find(T);"
            " k = find(T); s = issparse(E); c = class(E); e = isempty(S); ne = numel(S); E;")
    ws, d = _dens(lambda: _run(code))
    assert d == 0
    g = lambda n: np.asarray(ws.get(n).backend_buffer())
    assert g("n1").item() == 100000 and g("n2").item() == 3 and g("z").tolist() == [[100000, 100000]]
    assert g("v").ravel().tolist() == [4, 6, 5] and g("i").ravel().tolist() == [1, 5, 99999]
    assert g("j").ravel().tolist() == [2, 5, 100000] and g("x").ravel().tolist() == [4, 6, 5]
    assert g("k").ravel().tolist() == [100001, 400005, 100000 * 99999 + 99999]
    assert ws.get("D").store.nnz == 100000 and g("ne").item() == 1e10


def test_display_reads_compressed_arrays():
    from openmatlab.host.display import _format_value

    ws = _run("E = speye(100000);")
    text, d = _dens(lambda: _format_value(ws.get("E")))
    assert d == 0 and "(100000,100000)" in text


# --- #516: kernels ----------------------------------------------------------------

def test_huge_kernels_do_not_densify():
    code = ("n = 100000; E = speye(n); x = ones(n, 1); y = E*x; w = x'*E; F = E + E; G = E - 2*E;"
            " H = E .* E; K = 3*E; L = -E; M = E'; P = E*E; Q = abs(L); R = L.^2; U = E./2;"
            " s1 = sum(E); s2 = sum(E, 2); mx = max(L); W = E .* 5;")
    ws, d = _dens(lambda: _run(code))
    assert d == 0
    for n in "FGHKLMPQRUW":
        assert sp.is_sparse(ws.get(n)), n
    assert ws.get("G").store.data[:3].tolist() == [-1, -1, -1]
    assert np.asarray(ws.get("y").backend_buffer()).sum() == 100000
    assert ws.get("mx").store.nnz == 0  # max(-I) over columns is 0 (implicit zeros)


@pytest.mark.parametrize("seed", range(6))
def test_randomized_parity_with_dense(seed):
    rng = np.random.default_rng(seed)
    m, n = rng.integers(1, 7, 2)
    A = np.where(rng.random((m, n)) < 0.4, rng.integers(-5, 6, (m, n)), 0).astype(float)
    B = np.where(rng.random((m, n)) < 0.4, rng.integers(-5, 6, (m, n)), 0).astype(float)
    C = rng.integers(-3, 4, (n, 3)).astype(float)
    Dn = rng.integers(1, 4, (m, n)).astype(float)  # nonzero divisor
    exprs = ["X*C", "X'*X", "X+Y", "X-Y", "X.*Y", "X.*Dn", "X./Dn", "2.5*X", "-X", "X'", "X.'",
             "X.^2", "abs(X)", "sum(X)", "sum(X,2)", "max(X)", "min(X)", "max(X,[],2)",
             "X(end,:)", "X(:,1)", "X(:)", "X([1 1],:)", "[X Y; Y X]", "round(X/3)", "X*X'"]
    for e in exprs:
        code = (f"X = sparse(A); Y = sparse(B); r1 = full({e}); s1 = issparse({e});"
                f" X = A; Y = B; r2 = {e};")
        ws = _run(code, A=A, B=B, C=C, Dn=Dn)
        r1, r2 = (np.asarray(ws.get(k).backend_buffer()) for k in ("r1", "r2"))
        assert r1.shape == r2.shape and np.allclose(r1, r2), e
    # assignment / deletion parity
    for stmt in ["X(1,1) = 9;", "X(:,1) = 0;", "X(end+1, end+2) = 4;", "X(1,:) = [];",
                 "X(:,end) = [];", "X(3) = [];", "X(A ~= 0) = 7;", "X(m*n+2) = 1;"]:
        code = f"X = sparse(A); {stmt} r1 = full(X); s1 = issparse(X); X = A; {stmt} r2 = X;"
        ws = _run(code, A=A, m=np.array([[float(m)]]), n=np.array([[float(n)]]))
        r1, r2 = (np.asarray(ws.get(k).backend_buffer()) for k in ("r1", "r2"))
        assert r1.shape == r2.shape and np.allclose(r1, r2), stmt
        assert bool(np.asarray(ws.get("s1").backend_buffer()).item()), stmt


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_inf_nan_operands_keep_dense_semantics():
    ws = _run("S = sparse([1 0; 0 2]); a = full(S*Inf); b = full(S.*[Inf 1; 1 1]); c = full(S./0);")
    g = lambda n: np.asarray(ws.get(n).backend_buffer())
    assert np.isnan(g("a")[0, 1]) and np.isinf(g("a")[0, 0])  # 0*Inf = NaN everywhere
    assert np.isinf(g("b")[0, 0]) and g("b")[1, 0] == 0
    assert np.isnan(g("c")[0, 1]) and np.isinf(g("c")[0, 0])  # 0/0 = NaN


# --- #517: indexing, assignment, concatenation -----------------------------------

def test_huge_indexing_and_assignment_do_not_densify():
    code = ("n = 100000; S = sparse(n, n); S(5, 7) = 3; S(n, n) = 4; S(2, :) = 0; a = S(5, 7);"
            " b = S(n, [1 n]); c = S(1:10, 7); S(3, 1:3) = [1 2 3]; S(:, 2) = []; T = [S; S];"
            " k = S(5 + 6*n - n); S(n, n + 5) = 1;")
    ws, d = _dens(lambda: _run(code))
    assert d == 0
    S = ws.get("S").store
    assert S.shape == (100000, 100005) and S.nnz == 5
    assert ws.get("T").store.shape == (200000, 99999)
    assert ws.get("a").store.data.tolist() == [3] and ws.get("b").store.data.tolist() == [4]


def test_colon_reshape_is_sparse():
    ws = _run("S = sparse([1 0; 0 2]); v = S(:);")
    assert sp.is_sparse(ws.get("v")) and ws.get("v").shape == (4, 1)


def test_index_errors_match_dense():
    from openmatlab.runtime.evaluator import EvalError

    for code in ["S = sparse(3,3); S(4,1)", "S = sparse(3,3); S(10)", "S = sparse(3,3); S(0)",
                 "S = sparse(3,3); S(1:2, 1:2) = [1 2 3]"]:
        with pytest.raises(EvalError):
            _run(code)


def test_sprand_parity():
    np.random.seed(1)
    code = ("S = sprand(30, 20, 0.15); F = full(S); x = (1:20)';"
            " d1 = norm(S*x - F*x); d2 = norm(full(S'*S) - F'*F, 1); d3 = norm(full(S + 2*S) - 3*F, 1);"
            " d4 = norm(full(sum(S)) - sum(F)); d5 = norm(full(max(S, [], 2)) - max(F, [], 2));"
            " d6 = norm(full(S(3:7, [2 9 9])) - F(3:7, [2 9 9]), 1); n = nnz(S);")
    ws = _run(code)
    for k in ("d1", "d2", "d3", "d4", "d5", "d6"):
        assert np.asarray(ws.get(k).backend_buffer()).item() < 1e-12, k
    assert np.asarray(ws.get("n").backend_buffer()).item() == 90
