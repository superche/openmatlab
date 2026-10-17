"""funm / logm and the complex Schur form (C-E5 #765 T2): own examples, checked against identities."""

from __future__ import annotations

import numpy as np
import pytest

from openmatlab.host.repl import ReplSession
from openmatlab.libs.matfun import schur_complex

pytestmark = [pytest.mark.unit]


def ev(code, name="r"):
    s = ReplSession()
    s.run_line(code)
    return np.asarray(s.session.workspace.get(name).backend_buffer())


@pytest.mark.parametrize("n,cplx", [(1, 0), (3, 0), (6, 1), (10, 0)])
def test_schur_complex_is_unitary_triangular(n, cplx):
    rng = np.random.default_rng(n)
    a = rng.standard_normal((n, n)) + (1j * rng.standard_normal((n, n)) if cplx else 0)
    u, t = schur_complex(a)
    np.testing.assert_allclose(u @ t @ u.conj().T, a, atol=1e-12)
    np.testing.assert_allclose(u.conj().T @ u, np.eye(n), atol=1e-12)
    assert np.all(np.tril(t, -1) == 0)


def test_funm_matches_expm_and_trig_identities():
    np.testing.assert_allclose(ev("A = [1 2; 0.5 -1]; r = funm(A, @exp) - expm(A);"), np.zeros((2, 2)), atol=1e-12)
    np.testing.assert_allclose(ev("X = [0 1; -2 3]; r = funm(X, @sin)^2 + funm(X, @cos)^2;"), np.eye(2), atol=1e-12)
    # a defective matrix: one Jordan block, so the Taylor branch is taken
    np.testing.assert_allclose(ev("r = funm([1 1; 0 1], @exp);"), np.e * np.array([[1, 1], [0, 1]]), atol=1e-12)
    # clustered eigenvalues (within TolBlk) plus the Parlett recurrence between blocks
    np.testing.assert_allclose(ev("A = [1 1 0; 0 1.02 1; 0 0 4]; r = funm(A, @exp) - expm(A);"),
                               np.zeros((3, 3)), atol=1e-11)


def test_funm_user_function_and_outputs():
    np.testing.assert_allclose(ev("r = funm([2 1; 0 3], @(x, k) exp(x));"), ev("r = expm([2 1; 0 3]);"), atol=1e-12)
    s = ReplSession()
    s.run_line("[F, flag, o] = funm(diag([1 2]), @sinh); t = o.terms; c = class(funm(single(2), @exp));")
    w = s.session.workspace
    assert np.asarray(w.get("flag").backend_buffer()).item() == 0
    np.testing.assert_array_equal(np.asarray(w.get("t").backend_buffer()), [[1, 1]])
    assert w.get("c").text == "single"
    assert ev("r = funm([], @exp);").shape == (0, 0)


def test_logm_inverts_expm():
    np.testing.assert_allclose(ev("A = [1 2; 0.3 4]; r = expm(logm(A)) - A;"), np.zeros((2, 2)), atol=1e-12)
    np.testing.assert_allclose(ev("r = logm([1 1; 0 1]);"), [[0, 1], [0, 0]], atol=1e-14)
    np.testing.assert_allclose(ev("r = logm(5);"), [[np.log(5)]])
    r = ev("r = logm([-1 0; 0 2]);")  # a negative eigenvalue: complex, non-principal warning
    np.testing.assert_allclose(r, np.diag([np.log(1) + 1j * np.pi, np.log(2)]), atol=1e-14)
